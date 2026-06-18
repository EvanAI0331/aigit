from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from aigithub_radar.storage.db import Database


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "radar.sqlite3"
FRONTEND = ROOT / "frontend"


class RadarHandler(BaseHTTPRequestHandler):
    db = Database(DB_PATH)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            return
        rel = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        target = (FRONTEND / rel).resolve()
        if not str(target).startswith(str(FRONTEND.resolve())) or not target.exists() or not target.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api(parsed.path)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api_post(parsed.path)
            return
        self._json({"error": "not found"}, status=404)

    def _handle_api(self, path: str) -> None:
        self.db.init()
        if path == "/api/health":
            self._json({"ok": True, "service": "aigithub-radar"})
            return
        if path == "/api/latest-run":
            self._json(self.db.latest_run_snapshot())
            return
        if path == "/api/summary":
            self._json(self._summary())
            return
        if path == "/api/opportunities":
            self._json({"opportunities": self._opportunities()})
            return
        if path == "/api/actions":
            self._json({"actions": self.db.next_actions()})
            return
        self._json({"error": "not found"}, status=404)

    def _handle_api_post(self, path: str) -> None:
        self.db.init()
        try:
            payload = self._read_json()
            if path == "/api/actions":
                action_id = self.db.create_next_action(
                    int(payload["opportunity_id"]),
                    {
                        "action_type": payload.get("action_type", "manual"),
                        "title": payload["title"],
                        "description": payload.get("description", ""),
                        "priority": payload.get("priority", "medium"),
                        "due_at": payload.get("due_at"),
                        "evidence_required": payload.get("evidence_required", ""),
                    },
                )
                self._json({"ok": True, "action_id": action_id})
                return
            if path == "/api/actions/update":
                self.db.update_next_action(
                    int(payload["action_id"]),
                    str(payload["status"]),
                    payload.get("result_note"),
                    payload.get("evidence_type"),
                    payload.get("signal_strength"),
                )
                self._json({"ok": True})
                return
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, status=400)
            return
        self._json({"error": "not found"}, status=404)

    def _summary(self) -> dict:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                select
                  count(*) as total,
                  sum(case when status in ('APPROVED','NEXT_ACTION_CREATED','STORED') then 1 else 0 end) as focus,
                  sum(case when status in ('WATCHLIST','HOLD','VALIDATED') then 1 else 0 end) as watchlist,
                  sum(case when status like 'REJECTED_%' then 1 else 0 end) as rejected
                from opportunities
                """
            ).fetchone()
            actions = conn.execute("select count(*) as n from next_actions where status = 'open'").fetchone()
            latest = conn.execute("select status, run_name, started_at, finished_at from runs order by id desc limit 1").fetchone()
        return {
            "total_opportunities": row["total"] or 0,
            "focus": row["focus"] or 0,
            "watchlist": row["watchlist"] or 0,
            "rejected": row["rejected"] or 0,
            "open_actions": actions["n"] or 0,
            "latest_run": dict(latest) if latest else None,
        }

    def _opportunities(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                select o.id, o.title, o.repo_url, o.status, o.commercial_score,
                       o.validation_score, o.priority, o.updated_at,
                       r.full_name, r.stars, r.forks, r.license, r.language, r.topics,
                       sum(case when n.status = 'open' then 1 else 0 end) as open_actions,
                       sum(case when n.status = 'done' then 1 else 0 end) as done_actions,
                       sum(case when n.status = 'closed' then 1 else 0 end) as closed_actions
                from opportunities o
                join repos r on r.id = o.source_repo
                left join next_actions n on n.opportunity_id = o.id
                group by o.id
                order by o.commercial_score desc, o.updated_at desc
                limit 200
                """
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["topics"] = json.loads(item.get("topics") or "[]")
            except json.JSONDecodeError:
                item["topics"] = []
            result.append(item)
        return result

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (FRONTEND / rel).resolve()
        if not str(target).startswith(str(FRONTEND.resolve())) or not target.exists() or not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        print(f"[radar-server] {self.address_string()} {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8028), RadarHandler)
    print("AIGitHub Radar listening on http://127.0.0.1:8028")
    server.serve_forever()


if __name__ == "__main__":
    main()
