"""Canonical private worker Flask application factory."""

from flask import Flask

from backend.worker.routes import JobProcessor, create_worker_blueprint


def create_worker_app(
    *, processor=None, session_factory=None, report_engine=None,
    metric_sink=None, now=None,
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024
    resolved = processor or JobProcessor(
        session_factory=session_factory,
        report_engine=report_engine,
        metric_sink=metric_sink,
        now=now,
    )
    app.register_blueprint(create_worker_blueprint(resolved))
    return app


__all__ = ["create_worker_app"]
