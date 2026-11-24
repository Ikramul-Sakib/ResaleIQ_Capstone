"""Resale price estimation.

Two estimators share one result format:
* ``rule_based_estimate`` - always available, uses depreciation, condition and
  similar listings already on ResaleIQ.
* ``gemini_estimate`` - asks Google Gemini for an estimate when GEMINI_API_KEY is set.

``estimate_price`` tries Gemini first (if configured) and falls back to the rules,
and every result says which estimator produced it.
"""

import json
import logging
import re
import statistics

import requests

from ..errors import ApiError
from ..models import CONDITIONS, Category, Listing

log = logging.getLogger(__name__)

# Share of the original price an item typically keeps in each condition (before age).
CONDITION_FACTORS = {"new": 0.92, "like_new": 0.80, "good": 0.67, "fair": 0.52, "poor": 0.35}
MIN_VALUE_SHARE = 0.08  # never estimate below 8% of the original price
MAX_PRICE = 50_000_000
STOP_WORDS = {"the", "and", "for", "with", "used", "sale", "good", "new", "condition", "original"}


class AIUnavailable(Exception):
    """Gemini could not produce a usable estimate."""


def _round_price(value: float) -> int:
    if value < 1_000:
        step = 10
    elif value < 10_000:
        step = 50
    elif value < 100_000:
        step = 100
    else:
        step = 500
    return max(step, int(round(value / step) * step))


def _tokens(*texts: str | None) -> set[str]:
    words = set()
    for text in texts:
        for word in re.findall(r"[a-z0-9]+", (text or "").lower()):
            if len(word) >= 3 and word not in STOP_WORDS:
                words.add(word)
    return words


def find_comparables(category_id: int, title: str, brand: str | None, model: str | None, exclude_id=None, limit=10):
    """Approved or sold listings in the same category that share words with this item."""
    wanted = _tokens(title, brand, model)
    query = Listing.query.filter(Listing.category_id == category_id, Listing.status.in_(("approved", "sold")))
    if exclude_id:
        query = query.filter(Listing.id != exclude_id)
    candidates = query.order_by(Listing.created_at.desc()).limit(300).all()

    scored = []
    for listing in candidates:
        overlap = len(wanted & _tokens(listing.title, listing.brand, listing.model))
        if wanted and overlap == 0:
            continue
        price = listing.sold_price if listing.status == "sold" and listing.sold_price else listing.price
        scored.append(
            (
                overlap,
                {
                    "title": listing.title,
                    "price": price,
                    "condition": listing.condition,
                    "status": listing.status,
                },
            )
        )
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def rule_based_estimate(inputs: dict, category: Category, comparables: list[dict]) -> dict | None:
    """Return an estimate, or None when there is not enough information."""
    original = inputs.get("original_price")
    age_months = inputs.get("age_months") or 0
    condition = inputs["condition"]
    explanation = []

    formula_value = None
    if original:
        keep = CONDITION_FACTORS[condition]
        age_factor = (1 - category.depreciation_rate) ** (age_months / 12)
        formula_value = max(original * keep * age_factor, original * MIN_VALUE_SHARE)
        explanation.append(
            f"In {CONDITIONS[condition].lower()} condition, items like this usually keep about "
            f"{keep:.0%} of their original price."
        )
        if age_months:
            explanation.append(
                f"{age_months} months of use in {category.name} (about {category.depreciation_rate:.0%} "
                f"value lost per year) lowers the value by about {1 - age_factor:.0%}."
            )

    prices = [item["price"] for item in comparables if item["price"]]
    market_value = statistics.median(prices) if prices else None
    if market_value is not None:
        explanation.append(
            f"{len(prices)} similar listing{'s' if len(prices) != 1 else ''} on ResaleIQ "
            f"{'have' if len(prices) != 1 else 'has'} a median price of BDT {int(market_value):,}."
        )

    if formula_value is None and market_value is None:
        return None
    if formula_value is None:
        recommended = market_value
    elif market_value is None:
        recommended = formula_value
    else:
        weight = 0.5 if len(prices) >= 3 else 0.25
        recommended = formula_value * (1 - weight) + market_value * weight
        explanation.append(f"The estimate blends the depreciation formula with market prices ({weight:.0%} market).")

    spread = 0.12 if len(prices) >= 3 else 0.18
    rec = _round_price(recommended)
    low = min(rec, _round_price(recommended * (1 - spread)))
    high = max(rec, _round_price(recommended * (1 + spread)))
    return {
        "min_price": low,
        "recommended_price": rec,
        "max_price": high,
        "explanation": explanation,
        "confidence": "medium" if len(prices) >= 3 else "low",
    }


def _build_prompt(inputs: dict, category: Category, comparables: list[dict], baseline: dict | None) -> str:
    item = {
        "title": inputs["title"],
        "category": category.name,
        "brand": inputs.get("brand"),
        "model": inputs.get("model"),
        "condition": CONDITIONS[inputs["condition"]],
        "original_purchase_price_bdt": inputs.get("original_price"),
        "age_months": inputs.get("age_months"),
        "seller_notes": inputs.get("description"),
    }
    lines = [
        "You are the pricing assistant of ResaleIQ, a second-hand marketplace in Bangladesh.",
        "Estimate a fair resale price in Bangladeshi Taka (BDT) for the item below, as it would sell "
        "today on the Bangladeshi second-hand market.",
        "Consider brand, model, condition, age, typical depreciation and the comparable listings.",
        "",
        "Item: " + json.dumps(item, ensure_ascii=False),
        "Comparable ResaleIQ listings: " + json.dumps(comparables, ensure_ascii=False),
    ]
    if baseline:
        lines.append(
            f"A simple depreciation formula suggests about BDT {baseline['recommended_price']:,}; "
            "use it only as a reference."
        )
    lines += [
        "",
        "Reply with JSON only, exactly in this shape:",
        '{"min_price": 0, "recommended_price": 0, "max_price": 0, '
        '"confidence": "low|medium|high", "explanation": ["short reason", "..."]}',
        "Rules: whole numbers in BDT; min_price <= recommended_price <= max_price; "
        "3 to 5 explanation points, each under 25 words, written for the seller.",
    ]
    return "\n".join(lines)


def _parse_ai_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    data = json.loads(cleaned)
    try:
        low, rec, high = (int(round(float(data[key]))) for key in ("min_price", "recommended_price", "max_price"))
    except (KeyError, TypeError, ValueError) as error:
        raise AIUnavailable("AI response is missing prices") from error
    if not (0 < low <= rec <= high <= MAX_PRICE):
        raise AIUnavailable("AI prices are not in a valid order")
    explanation = [str(point)[:300] for point in (data.get("explanation") or []) if str(point).strip()][:6]
    confidence = data.get("confidence") if data.get("confidence") in ("low", "medium", "high") else "medium"
    return {
        "min_price": low,
        "recommended_price": rec,
        "max_price": high,
        "explanation": explanation or ["Estimated by AI from the product details."],
        "confidence": confidence,
    }


def gemini_estimate(config, inputs, category, comparables, baseline) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config['GEMINI_MODEL']}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": _build_prompt(inputs, category, comparables, baseline)}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    try:
        response = requests.post(
            url,
            headers={"x-goog-api-key": config["GEMINI_API_KEY"], "Content-Type": "application/json"},
            json=body,
            timeout=config["GEMINI_TIMEOUT_SECONDS"],
        )
    except requests.RequestException as error:
        raise AIUnavailable(f"Could not reach Gemini: {error.__class__.__name__}") from error
    if response.status_code != 200:
        raise AIUnavailable(f"Gemini returned HTTP {response.status_code}: {response.text[:300]}")
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_ai_json(text)
    except AIUnavailable:
        raise
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise AIUnavailable("Gemini returned an unexpected response") from error


def estimate_price(config, inputs: dict, category: Category) -> dict:
    comparables = find_comparables(
        category.id, inputs["title"], inputs.get("brand"), inputs.get("model"), exclude_id=inputs.get("listing_id")
    )
    baseline = rule_based_estimate(inputs, category, comparables)

    notice = None
    if config["GEMINI_API_KEY"]:
        try:
            result = gemini_estimate(config, inputs, category, comparables, baseline)
            return {**result, "source": "ai", "model": config["GEMINI_MODEL"], "comparables_count": len(comparables)}
        except AIUnavailable as error:
            log.warning("AI price estimate failed, using rule-based estimate: %s", error)
            notice = "The AI service is unavailable right now, so this is a rule-based estimate."
    else:
        notice = "AI is not configured yet, so this is a rule-based estimate."

    if baseline is None:
        raise ApiError(
            "Enter the original purchase price so a resale price can be estimated.",
            422,
            {"original_price": "Original purchase price is needed for an estimate."},
        )
    return {**baseline, "source": "rules", "notice": notice, "comparables_count": len(comparables)}
