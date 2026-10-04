# 🤖 Autonomous Code Review Agent

An AI-assisted system that reviews source code, **detects** bugs / security vulnerabilities / quality problems,
**explains** each one in plain English, **prioritizes** them by severity, and **suggests fixes**.
It reviews pasted code, uploaded files, whole GitHub repositories, and GitHub pull requests.

## How it works

```
 paste / upload / GitHub repo / GitHub PR / local folder
                       │
          ┌────────────▼────────────┐
          │ Built-in static analyzer │  Python AST + JS/TS rules (21 rules total) + JS/TS + secret scan   ← always runs, offline
          └────────────┬────────────┘
   optional ───────────┤◄── SonarQube Web API issues (merged, de-duplicated)
                       │
          ┌────────────▼────────────┐
          │ Prioritize + score 0-100 │  CRITICAL > MAJOR > MINOR > INFO
          └────────────┬────────────┘
   optional ───────────┤◄── LangChain + LLM (Ollama local or OpenAI) rewrites explanation + fix for top issues
                       ▼
        Web report · JSON · Markdown · PR comment · CLI exit code (CI gate)
```

**Reliability by design:** every external piece is optional and degrades gracefully. No GitHub token → public repos
still work. SonarQube down → built-in analyzer only. LLM down or slow → the built-in rule library supplies the
explanation and fix, and the first LLM failure switches it off for the rest of that review so a report is never blocked.
Every report states which parts actually ran (see *Notes*).

## Quick start (2 minutes, nothing else needed)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                                          # open http://localhost:5000
```
Click **Run demo review**. Demo Mode needs no GitHub, SonarQube or LLM and is clearly marked as a demo in the UI.

Run the tests: `python -m unittest discover -s tests -t .`

## Optional integrations

Copy `.env.example` to `.env` and fill in only what you want.

| Feature | What to do |
|---|---|
| **Private repos / higher rate limit / PR comments** | Create a GitHub fine-grained token (Contents: read, Pull requests: write) → `GITHUB_TOKEN` |
| **Local LLM (free)** | Install [Ollama](https://ollama.com), run `ollama pull llama3.1`, keep `LLM_PROVIDER=ollama` |
| **OpenAI instead** | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=...`, optionally `LLM_MODEL=gpt-4o-mini` |
| **No LLM** | `LLM_PROVIDER=none` |
| **SonarQube** | See below |

### SonarQube
1. `docker compose --profile full up --build` (SonarQube at http://localhost:9000, login `admin`/`admin`, then change password).
   On Linux you may first need `sudo sysctl -w vm.max_map_count=262144`.
2. In SonarQube create a project and a **user token**; put `SONAR_TOKEN` and `SONAR_PROJECT_KEY` in `.env`.
3. Analyze your code with the scanner, e.g. from the repo you want reviewed:
   ```bash
   docker run --rm --network host -v "$PWD:/usr/src" -e SONAR_HOST_URL=http://localhost:9000 \
     -e SONAR_TOKEN=<token> sonarsource/sonar-scanner-cli -Dsonar.projectKey=<key>
   ```
4. Review the same repo from the app. Its open Sonar issues are merged into the report. The agent *reads* results of
   the last scan; it does not trigger scans, so re-scan after pushing changes.

### Automatic PR reviews (GitHub webhook)
Expose the app (e.g. with a tunnel or a server), then in the repo: **Settings → Webhooks → Add webhook**
- Payload URL `https://<your-host>/webhook`, content type `application/json`, event **Pull requests**
- Secret = the value of `GITHUB_WEBHOOK_SECRET` (the endpoint is disabled and rejects everything until this is set;
  every request's HMAC signature is verified)

On open / new commits / reopen, the agent reviews the PR in the background and comments the report on it.
PR reviews only report issues on **lines the PR adds**, so developers aren't blamed for old code.

## Usage

| Interface | How |
|---|---|
| Web UI | `python app.py` → http://localhost:5000 |
| CLI | `python cli.py ./src` · `python cli.py owner/repo` · `python cli.py <PR url> --json --no-llm` |
| CI gate | the CLI exits **1** if any CRITICAL issue is found, **2** on bad input, **0** otherwise |
| REST API | `POST /api/review` with `{"mode":"paste","files":{"a.py":"..."}}` or `{"mode":"github","target":"owner/repo"}` or `{"mode":"demo"}` |
| Health | `GET /api/health` |
| Docker | `docker compose up --build` (add `--profile full` for SonarQube + Ollama) |

## Project layout

```
app.py                 Flask UI + JSON API + webhook
cli.py                 command-line / CI usage
agent/static_analyzer  built-in rules (AST + regex)       agent/rules.py   severity, explanation, fix per rule
agent/sonar_client     SonarQube Web API                   agent/llm.py     LangChain explainer with timeouts + fallback
agent/github_client    repo / PR files, diff parsing, PR comments
agent/reviewer         orchestration, scoring, verdict     agent/demo.py    Demo Mode
templates/ static/     web UI                              sample_code/     intentionally flawed demo input
tests/test_agent.py    27 tests
```

## What it detects

Security: SQL injection, `eval`/`exec`, shell injection, hard-coded secrets / AWS keys, unsafe `pickle`/`yaml.load`,
weak hashes (MD5/SHA-1), disabled TLS verification, debug mode, JS `eval` and `innerHTML` (XSS).
Bugs: syntax errors, mutable default arguments, bare `except`, silently swallowed exceptions.
Quality / performance: cyclomatic complexity > 10, functions > 50 lines, unused imports, `range(len())`,
string `+=` in loops, TODO/FIXME.

## Known limitations (be upfront about these in your report/viva)

- Deep analysis is **Python only**. JS/TS get a few regex rules; other languages get secret and TODO scanning.
  Use SonarQube for broader language coverage.
- Rules are heuristic, so expect some false positives/negatives. Taint analysis (tracing user input to a sink) is not implemented.
- LLM suggestions are only as good as the chosen model and should be reviewed by a human before applying.
- Reports are stored in memory (last 50) and vanish on restart; use the JSON/Markdown download to keep one.
- GitHub reviews cap at `MAX_FILES` files of `MAX_FILE_BYTES` each to stay fast.
