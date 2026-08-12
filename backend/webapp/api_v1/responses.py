from flask import Response, jsonify

from backend.webapp.api_v1.context import request_id, server_time


API_VERSION = "v1"


def _finalize(response: Response) -> Response:
    response.headers["X-Request-ID"] = request_id()
    response.headers["Cache-Control"] = "no-store"
    return response


def success(data: object, status: int = 200) -> Response:
    response = jsonify({
        "data": data,
        "request_id": request_id(),
        "server_time": server_time(),
        "api_version": API_VERSION,
    })
    response.status_code = status
    return _finalize(response)


def failure(
    code: str,
    message: str,
    status: int,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> Response:
    error: dict[str, object] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if details is not None:
        error["details"] = details
    response = jsonify({
        "error": error,
        "request_id": request_id(),
        "server_time": server_time(),
        "api_version": API_VERSION,
    })
    response.status_code = status
    return _finalize(response)
