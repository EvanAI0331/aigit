from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from aigithub_radar.harness.contracts import VALID_STATUSES


DEFAULT_THEMES = [
    "AI agent",
    "workflow automation",
    "AI video",
    "ComfyUI",
    "RAG",
    "local LLM",
    "knowledge base",
    "browser automation",
    "data dashboard",
    "AI coding",
    "n8n",
    "low-code",
    "AI CRM",
    "AI sales",
    "YouTube automation",
    "short video automation",
    "AI image workflow",
    "open-source analytics",
    "monitoring dashboard",
]


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists themes (
                  theme text primary key,
                  active integer not null default 1,
                  last_used_at text
                );
                create table if not exists runs (
                  id integer primary key,
                  run_name text,
                  status text not null,
                  plan_json text,
                  started_at text default current_timestamp,
                  finished_at text,
                  error text
                );
                create table if not exists run_events (
                  id integer primary key,
                  run_id integer not null,
                  event_type text not null,
                  subject text,
                  payload_json text,
                  created_at text default current_timestamp,
                  foreign key(run_id) references runs(id)
                );
                create table if not exists agent_invocations (
                  id integer primary key,
                  run_id integer,
                  agent text not null,
                  input_json text not null,
                  output_json text,
                  status text not null,
                  error text,
                  created_at text default current_timestamp,
                  completed_at text
                );
                create table if not exists repos (
                  id integer primary key,
                  full_name text unique not null,
                  url text not null,
                  description text,
                  stars integer,
                  forks integer,
                  language text,
                  license text,
                  topics text,
                  pushed_at text,
                  readme text,
                  detected_stack text,
                  updated_at text default current_timestamp
                );
                create table if not exists opportunities (
                  id integer primary key,
                  title text not null,
                  source_repo integer not null,
                  repo_url text not null,
                  theme text,
                  status text not null,
                  commercial_score integer default 0,
                  validation_score integer default 0,
                  risk_score integer default 0,
                  priority text default 'watch',
                  created_at text default current_timestamp,
                  updated_at text default current_timestamp,
                  foreign key(source_repo) references repos(id)
                );
                create table if not exists analyses (
                  id integer primary key,
                  opportunity_id integer not null,
                  problem text,
                  target_users text,
                  user_pain text,
                  why_hard_to_use text,
                  missing_middle_tool text,
                  localization_opportunity text,
                  template_opportunity text,
                  service_opportunity text,
                  saas_opportunity text,
                  raw_json text not null,
                  created_at text default current_timestamp
                );
                create table if not exists validations (
                  id integer primary key,
                  opportunity_id integer not null,
                  problem_hypothesis text,
                  customer_discovery_plan text,
                  demand_signal text,
                  competition_signal text,
                  monetization_signal text,
                  pmf_vs_hype_check text,
                  seven_day_mvp_test text,
                  agentic_ops_fit text,
                  security_scope_risk text,
                  license_check text,
                  saturation_check text,
                  verdict text,
                  reason text,
                  raw_json text not null,
                  created_at text default current_timestamp
                );
                create table if not exists next_actions (
                  id integer primary key,
                  opportunity_id integer not null,
                  action_type text not null,
                  title text not null,
                  description text,
                  priority text,
                  status text default 'open',
                  result_note text,
                  created_at text default current_timestamp,
                  updated_at text default current_timestamp,
                  completed_at text
                );
                """
            )
            self._migrate_validations(conn)
            self._migrate_next_actions(conn)
            for theme in DEFAULT_THEMES:
                conn.execute("insert or ignore into themes(theme) values (?)", (theme,))

    def create_run(self, run_name: str | None = None) -> int:
        with self.connect() as conn:
            cur = conn.execute("insert into runs(run_name, status) values (?, 'RUNNING')", (run_name,))
            return int(cur.lastrowid)

    def attach_run_plan(self, run_id: int, run_name: str, plan: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "update runs set run_name = ?, plan_json = ? where id = ?",
                (run_name, json.dumps(plan, ensure_ascii=False), run_id),
            )

    def finish_run(self, run_id: int, status: str, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "update runs set status = ?, error = ?, finished_at = current_timestamp where id = ?",
                (status, error, run_id),
            )

    def add_event(self, run_id: int, event_type: str, subject: str | None = None, payload: dict | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into run_events(run_id, event_type, subject, payload_json) values (?, ?, ?, ?)",
                (run_id, event_type, subject, json.dumps(payload or {}, ensure_ascii=False)),
            )

    def start_agent_invocation(self, run_id: int, agent: str, payload: dict) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "insert into agent_invocations(run_id, agent, input_json, status) values (?, ?, ?, 'RUNNING')",
                (run_id, agent, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def finish_agent_invocation(self, invocation_id: int, output: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "update agent_invocations set output_json = ?, status = 'SUCCEEDED', completed_at = current_timestamp where id = ?",
                (json.dumps(output, ensure_ascii=False), invocation_id),
            )

    def fail_agent_invocation(self, invocation_id: int, error: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "update agent_invocations set status = 'FAILED', error = ?, completed_at = current_timestamp where id = ?",
                (error, invocation_id),
            )

    def latest_run_snapshot(self) -> dict:
        with self.connect() as conn:
            run = conn.execute("select * from runs order by id desc limit 1").fetchone()
            if run is None:
                return {}
            events = conn.execute(
                "select event_type, subject, payload_json, created_at from run_events where run_id = ? order by id desc limit 20",
                (run["id"],),
            ).fetchall()
            invocations = conn.execute(
                "select agent, status, error, created_at, completed_at from agent_invocations where run_id = ? order by id asc",
                (run["id"],),
            ).fetchall()
        return {
            "run": dict(run),
            "events": [dict(row) for row in events],
            "agent_invocations": [dict(row) for row in invocations],
        }

    def next_themes(self, limit: int) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute("select theme from themes where active = 1 order by coalesce(last_used_at, '') asc, theme asc limit ?", (limit,)).fetchall()
            themes = [row["theme"] for row in rows]
            for theme in themes:
                conn.execute("update themes set last_used_at = current_timestamp where theme = ?", (theme,))
            return themes

    def upsert_repo(self, repo: dict) -> int:
        with self.connect() as conn:
            conn.execute(
                """
                insert into repos(full_name, url, description, stars, forks, language, license, topics, pushed_at, readme)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(full_name) do update set
                  url=excluded.url, description=excluded.description, stars=excluded.stars,
                  forks=excluded.forks, language=excluded.language, license=excluded.license,
                  topics=excluded.topics, pushed_at=excluded.pushed_at, readme=excluded.readme,
                  updated_at=current_timestamp
                """,
                (
                    repo["full_name"],
                    repo["url"],
                    repo.get("description", ""),
                    repo.get("stars", 0),
                    repo.get("forks", 0),
                    repo.get("language"),
                    repo.get("license"),
                    json.dumps(repo.get("topics", []), ensure_ascii=False),
                    repo.get("pushed_at"),
                    repo.get("readme", ""),
                ),
            )
            return int(conn.execute("select id from repos where full_name = ?", (repo["full_name"],)).fetchone()["id"])

    def repo_for_opportunity(self, opportunity_id: int) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                """
                select o.id as opportunity_id, o.status as opportunity_status, o.commercial_score,
                       o.validation_score, o.priority, r.*
                from opportunities o
                join repos r on r.id = o.source_repo
                where o.id = ?
                """,
                (opportunity_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError(f"opportunity not found: {opportunity_id}")
        item = dict(row)
        try:
            item["topics"] = json.loads(item.get("topics") or "[]")
        except json.JSONDecodeError:
            item["topics"] = []
        return item

    def revalidation_candidates(self, limit: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                select o.id as opportunity_id, o.status as opportunity_status, o.commercial_score,
                       o.validation_score, o.priority, r.*
                from opportunities o
                join repos r on r.id = o.source_repo
                where o.status in ('WATCHLIST','ANALYZED','VALIDATED','HOLD')
                order by o.updated_at asc
                limit ?
                """,
                (limit,),
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

    def latest_analysis_bundle(self, opportunity_id: int) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                "select raw_json from analyses where opportunity_id = ? order by id desc limit 1",
                (opportunity_id,),
            ).fetchone()
        if row is None:
            return {"analysis": {}, "pain": {}, "business": {}}
        try:
            return json.loads(row["raw_json"])
        except json.JSONDecodeError:
            return {"analysis": {}, "pain": {}, "business": {}}

    def action_summary(self, opportunity_id: int) -> dict:
        with self.connect() as conn:
            rows = conn.execute(
                "select status, count(*) as n from next_actions where opportunity_id = ? group by status",
                (opportunity_id,),
            ).fetchall()
        return {row["status"]: row["n"] for row in rows}

    def create_opportunity(self, repo_id: int, repo: dict, status: str) -> None:
        self._assert_status(status)
        with self.connect() as conn:
            conn.execute(
                """
                insert into opportunities(title, source_repo, repo_url, status)
                select ?, ?, ?, ?
                where not exists (select 1 from opportunities where source_repo = ?)
                """,
                (repo["full_name"], repo_id, repo["url"], status, repo_id),
            )

    def ensure_opportunity(self, repo_id: int, repo: dict) -> int:
        self.create_opportunity(repo_id, repo, "SCREENED")
        with self.connect() as conn:
            return int(conn.execute("select id from opportunities where source_repo = ?", (repo_id,)).fetchone()["id"])

    def save_analysis(self, opportunity_id: int, analysis: dict, pain: dict, business: dict) -> None:
        raw = {"analysis": analysis, "pain": pain, "business": business}
        with self.connect() as conn:
            conn.execute(
                """
                insert into analyses(opportunity_id, problem, target_users, user_pain, why_hard_to_use,
                missing_middle_tool, localization_opportunity, template_opportunity, service_opportunity,
                saas_opportunity, raw_json)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_id,
                    analysis.get("problem"),
                    analysis.get("target_users"),
                    pain.get("user_pain"),
                    pain.get("why_hard_to_use"),
                    pain.get("missing_middle_tool"),
                    pain.get("localization_opportunity"),
                    business.get("template_opportunity"),
                    business.get("service_opportunity"),
                    business.get("saas_opportunity"),
                    json.dumps(raw, ensure_ascii=False),
                ),
            )
            conn.execute("update opportunities set status = 'ANALYZED', updated_at = current_timestamp where id = ?", (opportunity_id,))

    def save_validation(self, opportunity_id: int, validation: dict) -> None:
        self._assert_founder_playbook_validation(validation)
        with self.connect() as conn:
            conn.execute(
                """
                insert into validations(opportunity_id, problem_hypothesis, customer_discovery_plan,
                demand_signal, competition_signal, monetization_signal, pmf_vs_hype_check,
                seven_day_mvp_test, agentic_ops_fit, security_scope_risk, license_check,
                saturation_check, verdict, reason, raw_json)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_id,
                    validation.get("problem_hypothesis"),
                    validation.get("customer_discovery_plan"),
                    validation.get("demand_signal"),
                    validation.get("competition_signal"),
                    validation.get("monetization_signal"),
                    validation.get("pmf_vs_hype_check"),
                    validation.get("seven_day_mvp_test"),
                    validation.get("agentic_ops_fit"),
                    validation.get("security_scope_risk"),
                    validation.get("license_check"),
                    validation.get("saturation_check"),
                    validation.get("verdict"),
                    validation.get("reason"),
                    json.dumps(validation, ensure_ascii=False),
                ),
            )
            conn.execute("update opportunities set status = 'VALIDATED', validation_score = ?, updated_at = current_timestamp where id = ?", (int(validation.get("validation_score", 0)), opportunity_id))

    def update_opportunity_score(self, opportunity_id: int, score: int, status: str) -> None:
        self._assert_status(status)
        priority = "focus" if score >= 80 else "watch" if score >= 65 else "reject"
        with self.connect() as conn:
            conn.execute(
                "update opportunities set commercial_score = ?, status = ?, priority = ?, updated_at = current_timestamp where id = ?",
                (score, status, priority, opportunity_id),
            )

    def update_opportunity_status(self, opportunity_id: int, status: str) -> None:
        self._assert_status(status)
        with self.connect() as conn:
            conn.execute("update opportunities set status = ?, updated_at = current_timestamp where id = ?", (status, opportunity_id))

    def save_next_actions(self, opportunity_id: int, actions: dict) -> None:
        rows = actions.get("next_actions")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("strategist_agent must return non-empty next_actions")
        with self.connect() as conn:
            for action in rows:
                conn.execute(
                    "insert into next_actions(opportunity_id, action_type, title, description, priority) values (?, ?, ?, ?, ?)",
                    (opportunity_id, action["action_type"], action["title"], action.get("description", ""), action.get("priority", "medium")),
                )

    def create_next_action(self, opportunity_id: int, action: dict) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "insert into next_actions(opportunity_id, action_type, title, description, priority, status) values (?, ?, ?, ?, ?, 'open')",
                (
                    opportunity_id,
                    action.get("action_type", "manual"),
                    action["title"],
                    action.get("description", ""),
                    action.get("priority", "medium"),
                ),
            )
            return int(cur.lastrowid)

    def update_next_action(self, action_id: int, status: str, result_note: str | None = None) -> None:
        if status not in {"open", "done", "closed"}:
            raise ValueError(f"invalid action status: {status}")
        completed_expr = "current_timestamp" if status in {"done", "closed"} else "null"
        with self.connect() as conn:
            conn.execute(
                f"update next_actions set status = ?, result_note = coalesce(?, result_note), updated_at = current_timestamp, completed_at = {completed_expr} where id = ?",
                (status, result_note, action_id),
            )

    def next_actions(self, opportunity_id: int | None = None, limit: int = 100) -> list[dict]:
        where = ""
        params: tuple = (limit,)
        if opportunity_id is not None:
            where = "where n.opportunity_id = ?"
            params = (opportunity_id, limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                select n.*, o.title as opportunity_title, r.full_name
                from next_actions n
                join opportunities o on o.id = n.opportunity_id
                join repos r on r.id = o.source_repo
                {where}
                order by case n.status when 'open' then 0 when 'done' then 1 else 2 end,
                         n.updated_at desc
                limit ?
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _assert_status(status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid opportunity status: {status}")

    @staticmethod
    def _migrate_validations(conn: sqlite3.Connection) -> None:
        existing = {row["name"] for row in conn.execute("pragma table_info(validations)").fetchall()}
        columns = {
            "problem_hypothesis": "text",
            "customer_discovery_plan": "text",
            "pmf_vs_hype_check": "text",
            "seven_day_mvp_test": "text",
            "agentic_ops_fit": "text",
            "security_scope_risk": "text",
        }
        for name, column_type in columns.items():
            if name not in existing:
                conn.execute(f"alter table validations add column {name} {column_type}")

    @staticmethod
    def _migrate_next_actions(conn: sqlite3.Connection) -> None:
        existing = {row["name"] for row in conn.execute("pragma table_info(next_actions)").fetchall()}
        columns = {
            "result_note": "text",
            "updated_at": "text",
            "completed_at": "text",
        }
        for name, column_type in columns.items():
            if name not in existing:
                conn.execute(f"alter table next_actions add column {name} {column_type}")
        if "updated_at" not in existing:
            conn.execute("update next_actions set updated_at = coalesce(created_at, current_timestamp)")

    @staticmethod
    def _assert_founder_playbook_validation(validation: dict) -> None:
        required = [
            "problem_hypothesis",
            "customer_discovery_plan",
            "demand_signal",
            "competition_signal",
            "monetization_signal",
            "pmf_vs_hype_check",
            "seven_day_mvp_test",
            "agentic_ops_fit",
            "security_scope_risk",
            "license_check",
            "saturation_check",
            "verdict",
            "validation_score",
            "founder_playbook_score",
            "reason",
        ]
        missing = [key for key in required if validation.get(key) in (None, "")]
        if missing:
            raise RuntimeError(f"validator_agent missing Founder Playbook fields: {', '.join(missing)}")
