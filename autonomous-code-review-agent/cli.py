"""CLI: review a local folder/file or a GitHub repo/PR. Exit code 1 if critical issues are found (CI gate).

  python cli.py ./src
  python cli.py octocat/Hello-World --no-llm
  python cli.py https://github.com/owner/repo/pull/12 --json
"""
import argparse
import json
import os
import sys
from pathlib import Path

from agent.config import Settings
from agent.github_client import GitHubError
from agent.reporting import to_markdown
from agent.reviewer import CodeReviewer
from agent.static_analyzer import SCAN_EXT

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "vendor"}


def load_local(path: Path, s: Settings) -> dict:
    paths = [path] if path.is_file() else sorted(
        p for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in SCAN_EXT and not SKIP_DIRS.intersection(p.parts))
    base = path.parent if path.is_file() else path
    files = {}
    for p in paths[: s.max_files]:
        if p.stat().st_size <= s.max_file_bytes:
            files[p.relative_to(base).as_posix()] = p.read_text(encoding="utf-8", errors="replace")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Autonomous Code Review Agent")
    ap.add_argument("target", help="local path, owner/repo, or GitHub repo/PR URL")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    a = ap.parse_args()
    s = Settings.from_env()
    reviewer = CodeReviewer(s)
    try:
        if os.path.exists(a.target):
            files = load_local(Path(a.target), s)
            if not files:
                print(f"No reviewable source files found in '{a.target}'.", file=sys.stderr)
                return 2
            report = reviewer.review_files(files, a.target, mode="local", use_llm=not a.no_llm)
        else:
            report = reviewer.review_github(a.target, use_llm=not a.no_llm)
    except (ValueError, GitHubError) as exc:
        print(f"Error: {exc}\n(If you meant a local path, check that it exists.)", file=sys.stderr)
        return 2
    print(json.dumps(report.model_dump(), indent=2) if a.json else to_markdown(report))
    return 1 if any(i.severity == "CRITICAL" for i in report.issues) else 0


if __name__ == "__main__":
    sys.exit(main())
