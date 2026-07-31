"""Feedback endpoint for creating GitHub issues."""
import os
import json
import logging
import urllib.request
import urllib.error
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
feedback_bp = Blueprint("feedback", __name__)

@feedback_bp.route("/api/feedback", methods=["POST"])
def feedback_api():
    data = request.get_json(silent=True) or {}
    feedback_text = data.get("comment", "").strip()
    page_url = data.get("url", "unknown page")
    
    if not feedback_text:
        return jsonify({"error": "No feedback provided"}), 400

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN not set in environment.")
        return jsonify({"error": "Server misconfigured. Cannot create issue."}), 500

    repo = "justinpeterman-droid/prison-policy-ai"
    api_url = f"https://api.github.com/repos/{repo}/issues"
    
    # Format the issue body
    issue_title = f"User Feedback from {page_url}"
    issue_body = f"**Page:** `{page_url}`\\n\\n**Feedback/Improvement:**\\n{feedback_text}"
    
    payload = json.dumps({
        "title": issue_title,
        "body": issue_body,
        "labels": ["feedback"]
    }).encode("utf-8")
    
    req = urllib.request.Request(api_url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {github_token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return jsonify({"success": True, "issue_url": res_data.get("html_url")})
    except urllib.error.HTTPError as e:
        logger.error(f"GitHub API error: {e.code} {e.read().decode('utf-8')}")
        return jsonify({"error": "Failed to submit feedback to GitHub."}), 500
    except Exception as e:
        logger.exception("Unexpected error submitting feedback")
        return jsonify({"error": "An unexpected error occurred."}), 500
