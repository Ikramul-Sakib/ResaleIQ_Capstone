import logging
import os
import secrets

import click
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from .config import Config
from .errors import register_error_handlers
from .extensions import db

WEAK_SECRETS = {"", "change-me", "dev-only-change-me"}


def _local_secret(folder: str) -> str:
    """Development convenience: create a random signing key once and keep it next to the database."""
    path = os.path.join(folder, ".secret_key")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(key)
    return key


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db_dir = "."
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
        db_file = app.config["SQLALCHEMY_DATABASE_URI"].removeprefix("sqlite:///")
        db_dir = os.path.dirname(db_file) or "."
        os.makedirs(db_dir, exist_ok=True)

    if app.config["SECRET_KEY"] in WEAK_SECRETS:
        if app.config["APP_ENV"] == "production":
            raise RuntimeError("Set a long random SECRET_KEY in backend/.env before running in production.")
        app.config["SECRET_KEY"] = _local_secret(db_dir)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    register_error_handlers(app)

    from .routes import ALL_BLUEPRINTS

    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "ai_enabled": bool(app.config["GEMINI_API_KEY"])})

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, max_age=7 * 24 * 3600)

    from .seed import seed_defaults, seed_demo

    with app.app_context():
        db.create_all()
        seed_defaults()

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Add demo sellers and listings."""
        created = seed_demo()
        click.echo(f"Added {created} demo listings." if created else "Demo data already exists.")

    return app
