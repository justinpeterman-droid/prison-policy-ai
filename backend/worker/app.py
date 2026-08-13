"""Canonical private worker Flask application factory."""

import os

from flask import Flask

from backend.worker.routes import JobProcessor, create_worker_blueprint


def create_worker_app(
    *,
    processor=None,
    session_factory=None,
    report_engine=None,
    metric_sink=None,
    now=None,
    queue_name=None,
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024
    resolved = processor or JobProcessor(
        session_factory=session_factory,
        report_engine=report_engine,
        metric_sink=metric_sink,
        now=now,
    )
    resolved_queue = str(
        queue_name
        if queue_name is not None
        else os.environ.get("CLOUD_TASKS_QUEUE", "")
    ).strip()
    if not resolved_queue:
        raise RuntimeError("Cloud Tasks worker queue configuration is incomplete")
    app.register_blueprint(
        create_worker_blueprint(
            resolved,
            queue_name=resolved_queue,
        )
    )
    return app


__all__ = ["create_worker_app"]
