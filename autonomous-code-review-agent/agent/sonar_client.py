"""SonarQube Web API client (reads issues of an already-analysed project)."""
from typing import Iterable, List, Optional

import requests

from .models import Issue

SEVERITY = {"BLOCKER": "CRITICAL", "CRITICAL": "CRITICAL", "MAJOR": "MAJOR", "MINOR": "MINOR", "INFO": "INFO",
            "HIGH": "MAJOR", "MEDIUM": "MINOR", "LOW": "INFO"}
CATEGORY = {"BUG": "bug", "VULNERABILITY": "security", "SECURITY_HOTSPOT": "security", "CODE_SMELL": "quality"}


class SonarError(Exception):
    pass


class SonarClient:
    def __init__(self, base_url: str, token: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _get(self, path: str, params: Optional[dict] = None):
        try:
            resp = requests.get(f"{self.base_url}{path}", params=params, auth=(self.token, ""), timeout=self.timeout)
        except requests.RequestException as exc:
            raise SonarError(f"SonarQube unreachable: {exc}") from exc
        if resp.status_code == 401:
            raise SonarError("SonarQube rejected the token (401).")
        if not resp.ok:
            raise SonarError(f"SonarQube returned HTTP {resp.status_code}.")
        return resp.json()

    def is_up(self) -> bool:
        try:
            return self._get("/api/system/status").get("status") == "UP"
        except SonarError:
            return False

    def fetch_issues(self, project_key: str, only_files: Optional[Iterable[str]] = None) -> List[Issue]:
        wanted = set(only_files) if only_files is not None else None
        out: List[Issue] = []
        for page in range(1, 6):
            data = self._get("/api/issues/search", {"componentKeys": project_key, "resolved": "false",
                                                    "ps": 500, "p": page})
            for it in data.get("issues", []):
                path = it.get("component", "").split(":", 1)[-1]
                if wanted is not None and path not in wanted:
                    continue
                sev = it.get("severity") or (it.get("impacts") or [{}])[0].get("severity", "MINOR")
                rule = it.get("rule", "sonar")
                out.append(Issue(
                    file=path, line=it.get("line", 0) or 0, severity=SEVERITY.get(sev, "MINOR"),
                    category=CATEGORY.get(it.get("type", ""), "quality"), rule=rule,
                    message=it.get("message", ""), source="sonarqube",
                    explanation=f"Reported by SonarQube rule {rule}.",
                    suggested_fix=f"See the rule description with compliant examples: "
                                  f"{self.base_url}/coding_rules?open={rule}"))
            if page * 500 >= data.get("paging", {}).get("total", 0):
                break
        return out
