# ResaleIQ — Smart Online Resale Marketplace

A moderated marketplace for buying and selling second-hand products in Bangladesh, with an
AI-assisted price estimator.

**Stack:** Vue.js 3 (Vite, Vue Router, Pinia) · Python Flask REST API · SQLite (SQLAlchemy) · Google Gemini (optional)

## Features

- Register, log in, profile, change password, password reset
- Sell items with up to 6 photos (validated, resized and stored on the server)
- Every new or edited listing is reviewed by an administrator (approve / reject with reason)
- Search, category chips, filters (price, condition, location) and sorting
- Listing details with photo gallery, seller info and rating, wishlist and report button
- **Buying:** Buy now, Make an offer (at least 50% of the asking price) or add to cart and check out
- **Orders:** seller accepts or declines; an accepted item is *reserved*; seller marks it shipped / handed over;
  buyer confirms receipt and the item becomes *sold*. Either side can cancel before hand-over
- **Payments:** cash on delivery, or bKash / Nagad paid directly to the seller with a transaction ID that the
  seller confirms (ResaleIQ never holds money)
- **Ratings and reviews:** buyers rate the seller (1–5 stars) after a completed order; ratings show on listings
  and seller profiles
- Buyer–seller messaging per listing, unread badges, in-app notifications
- Seller dashboard: listings by status, views, mark as sold, sales value
- Admin panel: review queue, all orders (with cancel), reports, users (block / unblock), categories, activity log
- AI price estimate (min / recommended / max in BDT with reasons). Uses Google Gemini when a key is
  configured, otherwise a built-in rule-based estimator (depreciation + similar listings)

## Project structure

```
ResaleIQ/
├── backend/                 Flask API
│   ├── app/
│   │   ├── __init__.py      app factory, creates the database on start
│   │   ├── config.py        settings from backend/.env
│   │   ├── models.py        15 SQLAlchemy tables
│   │   ├── security.py      JWT login tokens, login/admin decorators
│   │   ├── images.py        safe photo upload (Pillow)
│   │   ├── services/pricing.py  Gemini + rule-based price estimator
│   │   ├── services/orders.py   order rules (offers, reservation, cancellation)
│   │   ├── routes/          auth, users, listings, wishlist, orders + cart, messages, notifications, admin, ai
│   │   └── seed.py          default categories, first admin, demo data
│   ├── tests/               pytest tests
│   ├── run.py               entry point
│   └── requirements.txt
└── frontend/                Vue app
    ├── src/
    │   ├── views/           pages (home, listing, sell, dashboard, messages, admin, ...)
    │   ├── components/      navbar, listing card, image picker, price estimator, ...
    │   ├── stores/          Pinia stores (auth, toasts)
    │   ├── api.js           Axios client
    │   └── router.js        routes + login/admin guards
    └── vite.config.js       dev proxy to Flask
```

## Run it locally

You need **Python 3.11+** and **Node.js 20+**. No Docker or database server is needed.

### 1. Backend (terminal 1)

Windows:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

The API runs at http://127.0.0.1:8000. On first start it creates `backend/instance/resaleiq.db`,
the default categories and an admin account.

Optional — add demo sellers, 12 demo listings, a finished sale with a review and a waiting offer:

```bash
flask --app run seed-demo
```

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api` and `/uploads` to Flask, so no extra setup is needed.

### Accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@resaleiq.local` | `Admin@12345` (set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env` before first run to change) |
| Demo sellers (after `seed-demo`) | `rahim@demo.resaleiq`, `nusrat@demo.resaleiq`, `tanvir@demo.resaleiq` | `Demo@12345` |

Change the admin password after the first login (Profile → Change password).

### Start again with an empty database

Stop the backend, delete `backend/instance/` and `backend/uploads/`, and start it again.

## AI price estimation (Google Gemini)

Without a key the app uses the rule-based estimator and labels results "Rule-based estimate".
To enable AI:

1. Create a key at Google AI Studio.
2. In `backend/.env` set:
   ```
   GEMINI_API_KEY=your-key
   GEMINI_MODEL=gemini-2.5-flash
   ```
3. Restart the backend. Results are now labelled "AI estimate". If Gemini fails or returns invalid
   data, the app automatically falls back to the rule-based estimate.

The key stays on the server and is never sent to the browser.

## Tests

```bash
cd backend
.venv\Scripts\activate        # or: source .venv/bin/activate
python -m pytest
```

37 tests cover authentication, listing upload and validation, ownership rules, admin approval,
search filters, wishlist, reports, messaging, notifications, both price estimators, and the full
order flow (offers, cart checkout, reservation, cancellation, payments, reviews, admin cancel).

## Deployment

SQLite and uploaded photos need a disk that survives restarts, so the **backend cannot run on Vercel**.
Host the frontend on Vercel and the backend on PythonAnywhere (or Render with a persistent disk).

### Backend on PythonAnywhere (free)

1. Upload the project (e.g. `git clone`) to `/home/<username>/ResaleIQ`.
2. In a Bash console: `cd ResaleIQ/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Create `backend/.env`:
   ```
   APP_ENV=production
   SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
   CORS_ORIGINS=https://<your-app>.vercel.app
   FRONTEND_URL=https://<your-app>.vercel.app
   ADMIN_EMAIL=<your admin email>
   ADMIN_PASSWORD=<a strong password>
   GEMINI_API_KEY=<optional>
   ```
4. Web tab → Add a new web app → Manual configuration → set the virtualenv to `/home/<username>/ResaleIQ/backend/.venv`.
5. Edit the WSGI file:
   ```python
   import sys
   sys.path.insert(0, '/home/<username>/ResaleIQ/backend')
   from run import app as application
   ```
6. Reload. Check `https://<username>.pythonanywhere.com/api/health`.

Note: free PythonAnywhere accounts can only reach an allow-list of external sites. If Gemini calls are
blocked there, estimates fall back to the rule-based estimator.

### Frontend on Vercel

1. Import the GitHub repo in Vercel and set **Root Directory** to `frontend` (framework: Vite).
2. Add the environment variable `VITE_API_URL=https://<username>.pythonanywhere.com`.
3. Deploy. `frontend/vercel.json` already makes page refreshes work on every route.
