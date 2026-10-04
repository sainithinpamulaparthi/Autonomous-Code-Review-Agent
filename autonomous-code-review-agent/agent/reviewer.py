"""Orchestrator: static analysis + optional SonarQube + optional LLM -> Report."""
import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set

from .config import Settings
from .github_client import GitHubClient, parse_github_target
from .llm import LLMExplainer
from .models import Issue, Report
from .sonar_client import SonarClient, SonarError
from .static_analyzer import analyze_source, make_snippet

log = logging.getLogger("reviewer")
SEV_ORDER = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}
SEV_WEIGHT = {"CRITICAL": 15, "MAJOR": 7, "MINOR": 2, "INFO": 0.5}


def score_issues(issues: Iterable[Issue]) -> int:
    return int(max(0, 100 - sum(SEV_WEIGHT.get(i.severity, 1) for i in issues)))


def verdict_for(score: int, issues: List[Issue]) -> str:
    if any(i.severity == "CRITICAL" for i in issues) or score < 50:
        return "Not ready to merge: fix critical issues first"
    if score < 80 or any(i.severity == "MAJOR" for i in issues):
        return "Needs attention before merging"
    return "Looks good"


def summarize(files: int, issues: List[Issue]) -> str:
    counts = {s: sum(1 for i in issues if i.severity == s) for s in SEV_ORDER}
    text = (f"Reviewed {files} file(s): {counts['CRITICAL']} critical, {counts['MAJOR']} major, "
            f"{counts['MINOR']} minor, {counts['INFO']} info issue(s).")
    if issues:
        top = issues[0]
        text += f" Most urgent: {top.message} at {top.file}:{top.line}."
    return text


class CodeReviewer:
    def __init__(self, settings: Settings):
        self.s = settings
        self.github = GitHubClient(settings.github_token)
        self.sonar = SonarClient(settings.sonar_url, settings.sonar_token) if settings.sonar_configured else None

    # ---------- core pipeline ----------
    def review_files(self, files: Dict[str, str], target: str, *, mode: str = "paste",
                     changed_lines: Optional[Dict[str, Set[int]]] = None, use_llm: bool = True,
                     extra_issues: Optional[List[Issue]] = None, notes: Optional[List[str]] = None,
                     simulated: bool = False) -> Report:
        notes = list(notes or [])
        issues: List[Issue] = []
        for path, src in files.items():
            found = analyze_source(path, src)
            if changed_lines is not None:
                keep = changed_lines.get(path, set())
                found = [i for i in found if i.line in keep]
            issues += found
        issues += extra_issues or []

        seen, unique = set(), []
        for i in issues:
            key = (i.file, i.line, i.message)
            if key not in seen:
                seen.add(key)
                unique.append(i)
        issues = sorted(unique, key=lambda i: (SEV_ORDER.get(i.severity, 9), i.file, i.line))
        for i in issues:
            if not i.snippet and i.file in files:
                i.snippet = make_snippet(files[i.file].splitlines(), i.line)

        llm_used = False
        if use_llm and issues:
            explainer = LLMExplainer(self.s)
            for i in issues[: self.s.llm_max_issues]:
                if not explainer.enhance(i):
                    break
            llm_used = any(i.ai_generated for i in issues)
            if explainer.note:
                notes.append(explainer.note)
            explainer.close()

        score = score_issues(issues)
        return Report(
            target=target, mode=mode, simulated=simulated, files_reviewed=len(files),
            created=datetime.now(timezone.utc).isoformat(timespec="seconds"), issues=issues, score=score,
            verdict=verdict_for(score, issues), summary=summarize(len(files), issues),
            llm_used=llm_used, notes=notes)

    # ---------- entry points ----------
    def review_github(self, target_text: str, *, use_llm: bool = True, use_sonar: bool = True) -> Report:
        t = parse_github_target(target_text)
        changed = None
        if t.pr:
            files, changed, notes = self.github.get_pr_files(t, self.s.max_files, self.s.max_file_bytes)
            mode = "github-pr"
        else:
            files, notes = self.github.get_repo_files(t, self.s.max_files, self.s.max_file_bytes)
            mode = "github-repo"
        if not files:
            notes.append("No reviewable source files were found.")

        extra: List[Issue] = []
        if use_sonar:
            if not self.sonar:
                notes.append("SonarQube not configured (set SONAR_TOKEN and SONAR_PROJECT_KEY); "
                             "built-in analyzer used.")
            elif not self.sonar.is_up():
                notes.append("SonarQube is unreachable; built-in analyzer used.")
            else:
                try:
                    extra = self.sonar.fetch_issues(self.s.sonar_project_key, only_files=files.keys())
                    notes.append(f"Merged {len(extra)} SonarQube issue(s) from project "
                                 f"'{self.s.sonar_project_key}' (results reflect its last scan).")
                except SonarError as exc:
                    notes.append(f"SonarQube error: {exc}")
        return self.review_files(files, t.label, mode=mode, changed_lines=changed, use_llm=use_llm,
                                 extra_issues=extra, notes=notes)
