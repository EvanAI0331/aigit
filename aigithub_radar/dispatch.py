from __future__ import annotations

import json
import os
import subprocess
import urllib.request

from aigithub_radar.storage.db import Database


class DispatchManager:
    def __init__(self, db: Database):
        self.db = db

    def dispatch_run(self, run_id: int, summary_text: str) -> None:
        actions = [a for a in self.db.open_actions_for_dispatch(limit=20) if a.get("status") == "open"]
        subject = f"AIGitHub Radar daily report: {len(actions)} open actions"
        body = self._body(summary_text, actions)
        targets = [t.strip() for t in os.environ.get("AIGITHUB_DISPATCH_TARGETS", "local").split(",") if t.strip()]
        for target in targets:
            if target == "local":
                self._local(run_id, subject, body)
            elif target == "github_issue":
                self._github_issue(run_id, subject, body)
            else:
                self.db.record_dispatch(run_id, target, subject, body, "SKIPPED", "target is not implemented")

    @staticmethod
    def _body(summary_text: str, actions: list[dict]) -> str:
        lines = [summary_text, "", "Open actions:"]
        if not actions:
            lines.append("- none")
        for action in actions[:20]:
            lines.append(
                f"- #{action['id']} {action['full_name']}: {action['title']} "
                f"(due: {action.get('due_at') or 'unset'}, evidence: {action.get('evidence_required') or 'unset'})"
            )
        return "\n".join(lines)

    def _local(self, run_id: int, subject: str, body: str) -> None:
        try:
            subprocess.run(
                ["osascript", "-e", f'display notification {json.dumps(body[:180])} with title {json.dumps(subject[:80])}'],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.db.record_dispatch(run_id, "local", subject, body, "SENT", "macOS notification")
        except Exception as exc:
            self.db.record_dispatch(run_id, "local", subject, body, "FAILED", str(exc))

    def _github_issue(self, run_id: int, subject: str, body: str) -> None:
        repo = os.environ.get("AIGITHUB_DISPATCH_GITHUB_REPO")
        token = os.environ.get("GITHUB_TOKEN")
        if not repo or not token:
            self.db.record_dispatch(run_id, "github_issue", subject, body, "SKIPPED", "AIGITHUB_DISPATCH_GITHUB_REPO or GITHUB_TOKEN missing")
            return
        payload = json.dumps({"title": subject, "body": body, "labels": ["aigithub-radar", "ops-report"]}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "aigithub-commercial-radar",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self.db.record_dispatch(run_id, "github_issue", subject, body, "SENT", data.get("html_url"))
        except Exception as exc:
            self.db.record_dispatch(run_id, "github_issue", subject, body, "FAILED", str(exc))
