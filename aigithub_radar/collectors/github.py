from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.error
import urllib.request


class GitHubCollector:
    api = "https://api.github.com"

    def __init__(self) -> None:
        self.last_rate_limit: dict[str, str] = {}

    def search_repositories(self, query: str, per_page: int) -> list[dict]:
        params = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": per_page})
        payload = self._get(f"/search/repositories?{params}")
        return [self._repo(item) for item in payload.get("items", [])]

    def enrich_repository(self, repo: dict) -> dict:
        full_name = repo["full_name"]
        detail = self._get(f"/repos/{full_name}")
        enriched = self._repo(detail)
        enriched["readme"] = self._readme(full_name)
        return enriched

    def commercial_signals(self, repo: dict) -> dict:
        # Evidence-only collector. Business interpretation belongs to validator_agent.
        full_name = repo["full_name"]
        issues = self._get(f"/search/issues?{urllib.parse.urlencode({'q': f'repo:{full_name} is:issue', 'per_page': 1})}")
        return {
            "open_issues_count": repo.get("open_issues_count"),
            "issue_search_total": issues.get("total_count", 0),
            "stars": repo.get("stars"),
            "forks": repo.get("forks"),
            "license": repo.get("license"),
            "pushed_at": repo.get("pushed_at"),
            "topics": repo.get("topics", []),
            "note": "External market search connectors can be added here; this script only collects evidence.",
        }

    def _readme(self, full_name: str) -> str:
        try:
            payload = self._get(f"/repos/{full_name}/readme")
        except RuntimeError:
            return ""
        content = payload.get("content", "")
        if not content:
            return ""
        return base64.b64decode(content).decode("utf-8", errors="replace")[:20000]

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.api}{path}", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                self._capture_rate_limit(resp.headers)
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._capture_rate_limit(exc.headers)
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub HTTP {exc.code}: {body[:500]}") from exc

    def _capture_rate_limit(self, headers) -> None:
        self.last_rate_limit = {
            "limit": headers.get("X-RateLimit-Limit", ""),
            "remaining": headers.get("X-RateLimit-Remaining", ""),
            "reset": headers.get("X-RateLimit-Reset", ""),
            "resource": headers.get("X-RateLimit-Resource", ""),
            "used": headers.get("X-RateLimit-Used", ""),
        }

    @staticmethod
    def _headers() -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "aigithub-commercial-radar"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _repo(item: dict) -> dict:
        return {
            "full_name": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description") or "",
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "language": item.get("language"),
            "license": (item.get("license") or {}).get("spdx_id"),
            "topics": item.get("topics", []),
            "pushed_at": item.get("pushed_at"),
            "open_issues_count": item.get("open_issues_count", 0),
            "readme": item.get("readme", ""),
        }
