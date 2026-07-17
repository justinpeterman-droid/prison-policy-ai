"""Prison Policy AI — Flask web application."""
from pathlib import Path
from flask import Flask

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    # Routes
    from backend.webapp.routes.chat import chat_bp
    from backend.webapp.routes.reports import reports_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def home():
        from flask import render_template
        return render_template("home.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
