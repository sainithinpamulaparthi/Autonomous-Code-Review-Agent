"""Flask web app + JSON API for the Autonomous Code Review Agent."""
import hashlib
import hmac
import logging
import threading
import uuid
from collections import OrderedDict
from typing import Optional

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from agent.config import Settings
from agent.demo import run_demo
from agent.github_client import GitHubError, parse_github_target
from agent.models import Report
from agent.reporting import to_markdown
from agent.reviewer import CodeReviewer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


class ReviewInputError(Exception):
    pass


def verify_signature(secret: str, body: bytes, header: Optional[str]) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


def create_app(settings: Optional[Settings] = None) -> Flask:
    settings = settings or Settings.from_env()
    reviewer = CodeReviewer(settings)
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
    store: "OrderedDict[str, Report]" = OrderedDict()
    lock = threading.Lock()

    def save(report: Report) -> str:
        rid = uuid.uuid4().hex[:12]
        with lock:
            store[rid] = report
            while len(store) > 50:
                store.popitem(last=False)
        return rid

    def run_review(p: dict) -> Report:
        mode = p.get("mode", "paste")
        use_llm, use_sonar = bool(p.get("use_llm", True)), bool(p.get("use_sonar", True))
        if mode == "demo":
            return run_demo(reviewer)
        if mode == "github":
            try:
                report = reviewer.review_github(p.get("target", ""), use_llm=use_llm, use_sonar=use_sonar)
            except ValueError as exc:
                raise ReviewInputError(str(exc)) from exc
            if p.get("post_comment"):
                t = parse_github_target(p["target"])
                if not t.pr:
                    report.notes.append("Comment not posted: a pull-request URL is required.")
                else:
                    reviewer.github.post_comment(t, to_markdown(report))
                    report.notes.append("Summary comment posted to the pull request.")
            return report
        files = {k: v for k, v in (p.get("files") or {}).items() if isinstance(v, str) and v.strip()}
        if not files:
            raise ReviewInputError("Paste some code or upload at least one file.")
        return reviewer.review_files(files, "pasted code" if len(files) == 1 else f"{len(files)} uploaded files",
                                     mode="paste", use_llm=use_llm,
                                     notes=["SonarQube is only used for GitHub reviews."])

    def get_report(rid: str) -> Report:
        report = store.get(rid)
        if report is None:
            abort(404)
        return report

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("index.html", error="Upload too large (max 2 MB)."), 413

    @app.get("/")
    def index():
        return render_template("index.html", error=None)

    @app.get("/demo")
    def demo():
        return redirect(url_for("show_report", rid=save(run_demo(reviewer))))

    @app.post("/review")
    def review_form():
        payload = {
            "mode": request.form.get("mode", "paste"),
            "target": request.form.get("target", ""),
            "use_llm": request.form.get("use_llm") == "on",
            "use_sonar": request.form.get("use_sonar") == "on",
            "post_comment": request.form.get("post_comment") == "on",
            "files": {},
        }
        code = request.form.get("code", "")
        if code.strip():
            name = (request.form.get("filename") or "snippet.py").strip().replace("/", "_")[:80]
            payload["files"][name] = code
        for f in request.files.getlist("files"):
            if f and f.filename:
                payload["files"][f.filename.replace("\\", "/").split("/")[-1]] = \
                    f.read(settings.max_file_bytes).decode("utf-8", errors="replace")
        try:
            report = run_review(payload)
        except (ReviewInputError, GitHubError) as exc:
            return render_template("index.html", error=str(exc)), 400
        return redirect(url_for("show_report", rid=save(report)))

    @app.get("/report/<rid>")
    def show_report(rid):
        return render_template("report.html", r=get_report(rid), rid=rid)

    @app.get("/report/<rid>.json")
    def report_json(rid):
        return jsonify(get_report(rid).model_dump())

    @app.get("/report/<rid>.md")
    def report_md(rid):
        return to_markdown(get_report(rid)), 200, {"Content-Type": "text/markdown; charset=utf-8"}

    @app.post("/api/review")
    def api_review():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Send a JSON object."), 400
        try:
            report = run_review(payload)
        except ReviewInputError as exc:
            return jsonify(error=str(exc)), 400
        except GitHubError as exc:
            return jsonify(error=str(exc)), 502
        return jsonify(report.model_dump())

    @app.get("/api/health")
    def health():
        llm = {"provider": settings.llm_provider, "model": settings.model_name, "reachable": False}
        if settings.llm_provider == "ollama":
            try:
                requests.get(f"{settings.ollama_base_url}/api/tags", timeout=2).raise_for_status()
                llm["reachable"] = True
            except requests.RequestException:
                pass
        elif settings.llm_provider == "openai":
            llm["reachable"] = bool(settings.openai_api_key)
        return jsonify(
            app="ok",
            github={"token_configured": bool(settings.github_token)},
            sonarqube={"configured": settings.sonar_configured,
                       "reachable": bool(reviewer.sonar and reviewer.sonar.is_up())},
            llm=llm, demo_mode="always available")

    @app.post("/webhook")
    def webhook():
        if not settings.github_webhook_secret:
            return jsonify(error="Webhook disabled: set GITHUB_WEBHOOK_SECRET."), 503
        if not verify_signature(settings.github_webhook_secret, request.get_data(),
                                request.headers.get("X-Hub-Signature-256")):
            return jsonify(error="Invalid signature."), 401
        event = request.headers.get("X-GitHub-Event", "")
        data = request.get_json(silent=True) or {}
        if event == "ping":
            return jsonify(ok=True)
        if event != "pull_request" or data.get("action") not in ("opened", "synchronize", "reopened"):
            return jsonify(ignored=event), 200
        pr_url = f"https://github.com/{data['repository']['full_name']}/pull/{data['number']}"

        def job():
            try:
                report = reviewer.review_github(pr_url)
                save(report)
                reviewer.github.post_comment(parse_github_target(pr_url), to_markdown(report))
                log.info("Reviewed and commented on %s", pr_url)
            except Exception:
                log.exception("Webhook review failed for %s", pr_url)

        threading.Thread(target=job, daemon=True).start()
        return jsonify(accepted=pr_url), 202

    return app


app = create_app()

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
