"""Minimal GitHub REST client: fetch PR / repo files, post a PR comment."""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import quote

import requests

from .static_analyzer import SCAN_EXT

API = "https://api.github.com"
SKIP_PARTS = ("node_modules/", "vendor/", "dist/", "build/", ".min.", "/migrations/")
TARGET_RE = re.compile(
    r"^(?:https?://(?:www\.)?github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/pull/(\d+))?(?:[/?#].*)?$")


class GitHubError(Exception):
    pass


@dataclass
class GitTarget:
    owner: str
    repo: str
    pr: Optional[int] = None

    @property
    def label(self) -> str:
        return f"{self.owner}/{self.repo}" + (f"#{self.pr}" if self.pr else "")


def parse_github_target(text: str) -> GitTarget:
    m = TARGET_RE.match((text or "").strip())
    if not m:
        raise ValueError("Enter 'owner/repo' or a GitHub repository / pull-request URL.")
    return GitTarget(m.group(1), m.group(2), int(m.group(3)) if m.group(3) else None)


def added_lines(patch: Optional[str]) -> Set[int]:
    """Line numbers (in the new file) that a unified-diff patch adds."""
    lines: Set[int] = set()
    new = 0
    for row in (patch or "").splitlines():
        if row.startswith("@@"):
            m = re.search(r"\+(\d+)", row)
            new = int(m.group(1)) if m else 0
        elif row.startswith("+"):
            lines.add(new)
            new += 1
        elif row.startswith(("-", "\\")):
            continue
        else:
            new += 1
    return lines


def _wanted(path: str) -> bool:
    return path.lower().endswith(SCAN_EXT) and not any(p in path for p in SKIP_PARTS)


class GitHubClient:
    def __init__(self, token: str = "", timeout: int = 20):
        self.token = token
        self.timeout = timeout

    def _headers(self, raw: bool = False) -> dict:
        h = {
            "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "code-review-agent",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str, raw: bool = False, params: Optional[dict] = None):
        try:
            resp = requests.get(f"{API}{path}", headers=self._headers(raw), params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GitHubError(f"Could not reach GitHub: {exc}") from exc
        if resp.status_code == 404:
            raise GitHubError("Not found. The repository/PR may not exist or is private (set GITHUB_TOKEN).")
        if resp.status_code in (401, 403):
            hint = "rate limit exceeded - set GITHUB_TOKEN" if "rate limit" in resp.text.lower() else \
                "access denied - check GITHUB_TOKEN permissions"
            raise GitHubError(f"GitHub {resp.status_code}: {hint}.")
        if not resp.ok:
            raise GitHubError(f"GitHub returned HTTP {resp.status_code}.")
        return resp.text if raw else resp.json()

    def _file(self, t: GitTarget, path: str, ref: str) -> str:
        return self._get(f"/repos/{t.owner}/{t.repo}/contents/{quote(path)}", raw=True, params={"ref": ref})

    def get_pr_files(self, t: GitTarget, max_files: int, max_bytes: int
                     ) -> Tuple[Dict[str, str], Dict[str, Set[int]], List[str]]:
        notes: List[str] = []
        pr = self._get(f"/repos/{t.owner}/{t.repo}/pulls/{t.pr}")
        sha = pr["head"]["sha"]
        changed: List[dict] = []
        for page in (1, 2, 3):
            batch = self._get(f"/repos/{t.owner}/{t.repo}/pulls/{t.pr}/files",
                              params={"per_page": 100, "page": page})
            changed += batch
            if len(batch) < 100:
                break
        files: Dict[str, str] = {}
        lines: Dict[str, Set[int]] = {}
        candidates = [f for f in changed if f.get("status") != "removed" and _wanted(f["filename"])]
        if len(candidates) > max_files:
            notes.append(f"PR touches {len(candidates)} reviewable files; only the first {max_files} were reviewed.")
        for f in candidates[:max_files]:
            text = self._file(t, f["filename"], sha)
            if len(text.encode("utf-8", "ignore")) > max_bytes:
                notes.append(f"Skipped {f['filename']} (larger than {max_bytes} bytes).")
                continue
            files[f["filename"]] = text
            lines[f["filename"]] = added_lines(f.get("patch"))
        notes.append("Pull request review: only issues on lines added in this PR are reported.")
        return files, lines, notes

    def get_repo_files(self, t: GitTarget, max_files: int, max_bytes: int) -> Tuple[Dict[str, str], List[str]]:
        notes: List[str] = []
        repo = self._get(f"/repos/{t.owner}/{t.repo}")
        branch = repo["default_branch"]
        tree = self._get(f"/repos/{t.owner}/{t.repo}/git/trees/{quote(branch)}", params={"recursive": "1"})
        blobs = sorted(
            (e for e in tree.get("tree", [])
             if e["type"] == "blob" and _wanted(e["path"]) and e.get("size", 0) <= max_bytes),
            key=lambda e: e["path"])
        if len(blobs) > max_files:
            notes.append(f"Repository has {len(blobs)} reviewable files; only the first {max_files} were reviewed.")
        files = {e["path"]: self._file(t, e["path"], branch) for e in blobs[:max_files]}
        notes.append(f"Reviewed default branch '{branch}'.")
        return files, notes

    def post_comment(self, t: GitTarget, body: str) -> None:
        if not self.token:
            raise GitHubError("GITHUB_TOKEN is required to post comments.")
        try:
            resp = requests.post(f"{API}/repos/{t.owner}/{t.repo}/issues/{t.pr}/comments",
                                 headers=self._headers(), json={"body": body[:60000]}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GitHubError(f"Could not reach GitHub: {exc}") from exc
        if not resp.ok:
            raise GitHubError(f"Could not post comment (HTTP {resp.status_code}). "
                              "The token needs 'pull requests: write' permission.")
