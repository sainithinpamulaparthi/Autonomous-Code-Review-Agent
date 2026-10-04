import hashlib
import hmac
import json
import unittest
from pathlib import Path
from unittest import mock

from agent.config import Settings
from agent.github_client import GitHubClient, GitTarget, added_lines, parse_github_target
from agent.llm import LLMExplainer, parse_json_reply
from agent.reviewer import CodeReviewer
from agent.sonar_client import SonarClient
from agent.static_analyzer import analyze_source
from app import create_app

SAMPLE = Path(__file__).resolve().parent.parent / "sample_code"
NO_LLM = Settings(llm_provider="none")


class AnalyzerTests(unittest.TestCase):
    def test_sample_triggers_expected_rules(self):
        rules = {i.rule for i in analyze_source("vulnerable_app.py", (SAMPLE / "vulnerable_app.py").read_text())}
        expected = {"SECRET", "PY-SQLI", "PY-EVAL", "PY-SHELL", "PY-WEAKHASH", "PY-TLS", "PY-MUTABLE-DEFAULT",
                    "PY-BARE-EXCEPT", "PY-SWALLOW", "PY-RANGELEN", "PY-STRCONCAT", "PY-COMPLEXITY",
                    "PY-UNUSED-IMPORT", "PY-DEBUG"}
        self.assertTrue(expected <= rules, f"missing: {expected - rules}")

    def test_js_rules(self):
        rules = {i.rule for i in analyze_source("ui.js", (SAMPLE / "ui.js").read_text())}
        self.assertTrue({"JS-EVAL", "JS-INNERHTML", "TODO"} <= rules)

    def test_clean_code_has_no_issues(self):
        src = "import os\n\n\ndef home():\n    return os.environ.get('HOME', '')\n"
        self.assertEqual(analyze_source("ok.py", src), [])

    def test_safe_patterns_not_flagged(self):
        src = ("import ast, subprocess\n"
               "def f(c, x):\n"
               "    c.execute('SELECT * FROM t WHERE id = ?', (x,))\n"
               "    subprocess.run(['ls'], check=True)\n"
               "    return ast.literal_eval(x), eval('1+1')\n")
        self.assertEqual([i.rule for i in analyze_source("safe.py", src)], [])

    def test_syntax_error_reported(self):
        issues = analyze_source("bad.py", "def broken(:\n    pass\n")
        self.assertEqual(issues[0].rule, "PY-SYNTAX")

    def test_secret_detection_handles_prefixed_names(self):
        src = (SAMPLE / "vulnerable_app.py").read_text()
        lines = {i.line for i in analyze_source("v.py", src) if i.rule == "SECRET"}
        n_pw = next(n for n, row in enumerate(src.splitlines(), 1) if "DB_PASSWORD" in row)
        self.assertEqual(lines, {n_pw, n_pw + 1})  # DB_PASSWORD and API_KEY
        flagged = analyze_source("c.py", "token_type = 'Bearer'\nmy_secret = 'abcdef123'\n"
                                         "cfg = {'password': 'hunter22x'}\n")
        self.assertEqual(sorted(i.line for i in flagged), [2, 3])

    def test_placeholder_secret_ignored(self):
        self.assertEqual(analyze_source("c.py", "api_key = 'your_api_key_here'\n"), [])

    def test_every_issue_has_explanation_and_fix(self):
        for i in analyze_source("vulnerable_app.py", (SAMPLE / "vulnerable_app.py").read_text()):
            self.assertTrue(i.explanation and i.suggested_fix and i.snippet, i.rule)


class VerdictTests(unittest.TestCase):
    def test_major_issue_is_never_looks_good(self):
        r = CodeReviewer(NO_LLM).review_files({"a.py": "import hashlib\nhashlib.md5(b'x')\n"}, "t", use_llm=False)
        self.assertGreaterEqual(r.score, 80)
        self.assertEqual(r.verdict, "Needs attention before merging")

    def test_critical_blocks_and_clean_passes(self):
        bad = CodeReviewer(NO_LLM).review_files({"a.py": "def f(x):\n    return eval(x)\n"}, "t", use_llm=False)
        self.assertTrue(bad.verdict.startswith("Not ready"))
        good = CodeReviewer(NO_LLM).review_files({"a.py": "x = 1\n"}, "t", use_llm=False)
        self.assertEqual((good.score, good.verdict), (100, "Looks good"))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        import contextlib, io, sys, cli
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["cli.py", *argv]), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err), mock.patch.dict("os.environ", {"LLM_PROVIDER": "none"}):
            code = cli.main()
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(str(SAMPLE), "--no-llm")[0], 1)       # critical issues -> CI fails
        code, out, _ = self.run_cli(str(SAMPLE / "ui.js"), "--json", "--no-llm")
        self.assertEqual(json.loads(out)["mode"], "local")
        code, _, err = self.run_cli("definitely not a path or repo")
        self.assertEqual(code, 2)
        self.assertIn("Error", err)


class GitHubTests(unittest.TestCase):
    def test_parse_targets(self):
        self.assertEqual(parse_github_target("octocat/Hello-World"), GitTarget("octocat", "Hello-World", None))
        self.assertEqual(parse_github_target("https://github.com/o/r.git").repo, "r")
        self.assertEqual(parse_github_target("https://github.com/o/r/pull/12/files").pr, 12)
        with self.assertRaises(ValueError):
            parse_github_target("not a repo")

    def test_added_lines(self):
        patch = "@@ -1,3 +1,4 @@\n a\n+b\n c\n+d\n@@ -10,2 +11,3 @@\n x\n-y\n+z\n w"
        self.assertEqual(added_lines(patch), {2, 4, 12})

    def test_pr_flow_only_reports_changed_lines(self):
        code = "import os\n\n\ndef run(x):\n    return eval(x)\n"
        patch = "@@ -3,0 +4,2 @@\n+def run(x):\n+    return eval(x)"

        def fake_get(url, **kw):
            r = mock.Mock(status_code=200, ok=True)
            if url.endswith("/pulls/5"):
                r.json.return_value = {"head": {"sha": "abc"}}
            elif url.endswith("/pulls/5/files"):
                r.json.return_value = [{"filename": "a.py", "status": "modified", "patch": patch}]
            else:
                r.text = code
            return r

        with mock.patch("agent.github_client.requests.get", side_effect=fake_get):
            report = CodeReviewer(NO_LLM).review_github("o/r/pull/5", use_llm=False)
        rules = {i.rule for i in report.issues}
        self.assertIn("PY-EVAL", rules)
        self.assertNotIn("PY-UNUSED-IMPORT", rules)  # line 1 was not added in the PR
        self.assertEqual(report.mode, "github-pr")

    def test_http_errors_become_friendly(self):
        from agent.github_client import GitHubError
        resp = mock.Mock(status_code=404, ok=False, text="")
        with mock.patch("agent.github_client.requests.get", return_value=resp):
            with self.assertRaises(GitHubError):
                GitHubClient().get_repo_files(GitTarget("o", "r"), 5, 1000)


class SonarTests(unittest.TestCase):
    def test_issue_mapping_and_filtering(self):
        payload = {"issues": [
            {"component": "proj:src/a.py", "line": 7, "severity": "BLOCKER", "type": "VULNERABILITY",
             "rule": "python:S2077", "message": "SQL injection"},
            {"component": "proj:src/other.py", "line": 1, "severity": "MINOR", "type": "CODE_SMELL",
             "rule": "python:S1", "message": "x"}], "paging": {"total": 2}}
        resp = mock.Mock(status_code=200, ok=True)
        resp.json.return_value = payload
        with mock.patch("agent.sonar_client.requests.get", return_value=resp):
            issues = SonarClient("http://s", "tok").fetch_issues("proj", only_files=["src/a.py"])
        self.assertEqual(len(issues), 1)
        self.assertEqual((issues[0].severity, issues[0].category, issues[0].line), ("CRITICAL", "security", 7))


class LLMTests(unittest.TestCase):
    def test_parse_json_reply(self):
        self.assertEqual(parse_json_reply('```json\n{"explanation": "e", "fixed_code": "c"}\n```')["explanation"], "e")
        self.assertEqual(parse_json_reply("no json here"), {})

    def test_disabled_provider_falls_back(self):
        ex = LLMExplainer(NO_LLM)
        self.assertFalse(ex.enabled)

    def test_unreachable_ollama_falls_back(self):
        import requests
        with mock.patch("agent.llm.requests.get", side_effect=requests.ConnectionError("down")):
            ex = LLMExplainer(Settings(llm_provider="ollama"))
        self.assertFalse(ex.enabled)
        self.assertIn("unavailable", ex.note)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app(NO_LLM).test_client()

    def test_index_and_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        data = self.client.get("/api/health").get_json()
        self.assertEqual(data["app"], "ok")

    def test_demo_flow_is_labelled_simulated(self):
        resp = self.client.get("/demo", follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("DEMO MODE", html)
        self.assertIn("sonarqube (simulated)", html)

    def test_paste_review_and_exports(self):
        resp = self.client.post("/review", data={"mode": "paste", "filename": "x.py",
                                                 "code": "def f(x):\n    return eval(x)\n"})
        self.assertEqual(resp.status_code, 302)
        rid = resp.headers["Location"].rsplit("/", 1)[-1]
        report = self.client.get(f"/report/{rid}.json").get_json()
        self.assertEqual(report["issues"][0]["rule"], "PY-EVAL")
        self.assertFalse(report["simulated"])
        self.assertIn("PY-EVAL", self.client.get(f"/report/{rid}.md").get_data(as_text=True))

    def test_html_is_escaped(self):
        resp = self.client.post("/review", data={"mode": "paste", "filename": "x.py",
                                                 "code": "x = '<script>alert(1)</script>'; eval(x)\n"},
                                follow_redirects=True)
        self.assertNotIn("<script>alert(1)</script>", resp.get_data(as_text=True))

    def test_empty_input_rejected(self):
        self.assertEqual(self.client.post("/review", data={"mode": "paste", "code": " "}).status_code, 400)

    def test_api_review(self):
        resp = self.client.post("/api/review", json={"mode": "paste", "files": {"a.py": "try:\n  pass\nexcept:\n  pass\n"}})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("PY-BARE-EXCEPT", {i["rule"] for i in resp.get_json()["issues"]})
        self.assertEqual(self.client.post("/api/review", data="nope").status_code, 400)

    def test_unknown_report_404(self):
        self.assertEqual(self.client.get("/report/doesnotexist").status_code, 404)

    def test_webhook_security(self):
        self.assertEqual(self.client.post("/webhook", data="{}").status_code, 503)  # no secret configured
        c = create_app(Settings(llm_provider="none", github_webhook_secret="s3cret")).test_client()
        self.assertEqual(c.post("/webhook", data="{}", headers={"X-Hub-Signature-256": "sha256=bad"}).status_code, 401)
        body = json.dumps({"zen": "hi"}).encode()
        sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
        ok = c.post("/webhook", data=body, headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": "ping",
                                                    "Content-Type": "application/json"})
        self.assertEqual(ok.status_code, 200)


if __name__ == "__main__":
    unittest.main()
