"""Demo Mode: no GitHub / SonarQube / LLM needed. Always clearly labelled as simulated."""
from pathlib import Path
from typing import List

from .models import Issue, Report
from .reviewer import CodeReviewer

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_code"


def _find_line(src: str, needle: str) -> int:
    for n, row in enumerate(src.splitlines(), 1):
        if needle in row:
            return n
    return 1


def run_demo(reviewer: CodeReviewer) -> Report:
    files = {f"demo/{p.name}": p.read_text(encoding="utf-8") for p in sorted(SAMPLE_DIR.glob("*")) if p.is_file()}
    py = files["demo/vulnerable_app.py"]
    simulated: List[Issue] = [
        Issue(file="demo/vulnerable_app.py", line=_find_line(py, "tmp = 1"), severity="MINOR", category="quality",
              rule="python:S1481 (simulated)", message="Remove the unused local variable 'tmp'.",
              source="sonarqube (simulated)", explanation="Simulated SonarQube finding for demonstration only.",
              suggested_fix="Delete the unused variable."),
        Issue(file="demo/vulnerable_app.py", line=_find_line(py, "def calculate_discount"), severity="MAJOR",
              category="quality", rule="python:S3776 (simulated)",
              message="Refactor this function to reduce its Cognitive Complexity.",
              source="sonarqube (simulated)", explanation="Simulated SonarQube finding for demonstration only.",
              suggested_fix="Extract nested branches into helper functions."),
    ]
    return reviewer.review_files(
        files, "demo/sample-project", mode="demo", use_llm=False, extra_issues=simulated, simulated=True,
        notes=["DEMO MODE: the code is a built-in sample. The built-in analyzer really ran on it, but "
               "SonarQube findings are simulated and no GitHub or LLM calls were made."])
