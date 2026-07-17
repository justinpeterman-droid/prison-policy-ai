"""Prison Policy AI — Flask web application with simple access-code auth."""
import functools
from pathlib import Path
from flask import Flask, request, redirect, render_template, make_response

from backend.pipeline.config import ACCESS_CODE, logger

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def require_access(f):
    """Decorator: require valid access code cookie or query param."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not ACCESS_CODE:
            return f(*args, **kwargs)
        # Check cookie
        if request.cookies.get("access_code") == ACCESS_CODE:
            return f(*args, **kwargs)
        # Check query param (for bookmarkable links)
        if request.args.get("code") == ACCESS_CODE:
            resp = make_response(redirect(request.path))
            resp.set_cookie("access_code", ACCESS_CODE, max_age=60*60*24, httponly=True)
            return resp
        # Not authenticated — show login or redirect
        if request.path == "/login":
            return f(*args, **kwargs)
        return redirect(f"/login?next={request.path}")
    return wrapper


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
    @require_access
    def home():
        from flask import render_template
        return render_template("home.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            code = request.form.get("code", "")
            if code == ACCESS_CODE:
                next_url = request.args.get("next", "/")
                resp = make_response(redirect(next_url))
                resp.set_cookie("access_code", ACCESS_CODE, max_age=60*60*24, httponly=True)
                return resp
            error = "Invalid access code."
        return render_template("login.html", error=error, next=request.args.get("next", "/"))

    @app.route("/logout")
    def logout():
        resp = make_response(redirect("/login"))
        resp.delete_cookie("access_code")
        return resp

    if ACCESS_CODE:
        logger.info("Access code auth enabled")
    else:
        logger.warning("No ACCESS_CODE set — app is open to the public")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
