import logging

from flask import jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

log = logging.getLogger(__name__)


class ApiError(Exception):
    """An error that is safe to show to the user."""

    def __init__(self, message: str, status: int = 400, fields: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.fields = fields or {}


def error_response(message: str, status: int, fields: dict | None = None):
    body = {"error": {"message": message}}
    if fields:
        body["error"]["fields"] = fields
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error_response(error.message, error.status, error.fields)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        return error_response("The upload is too large. Each photo must be 8 MB or smaller.", 413)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        messages = {404: "Not found.", 405: "Method not allowed."}
        return error_response(messages.get(error.code, error.description or "Request failed."), error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.path, exc_info=error)
        return error_response("Something went wrong on the server. Please try again.", 500)
