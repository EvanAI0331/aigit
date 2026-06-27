from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

from aigithub_radar.harness.loop import OpportunityLoop
from aigithub_radar.harness.llm import GPTAgentLLMClient, OrchestratorLLMClient, WorkerLLMClient, load_env_file
from aigithub_radar.harness.spec_compiler import SpecCompiler
from aigithub_radar.harness.specx_adapter import SpecXAdapter
from aigithub_radar.storage.db import Database
from aigithub_radar.storage.reports import today_report


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "radar.sqlite3"


def main() -> None:
    parser = argparse.ArgumentParser(prog="aigithub-radar")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")
    sub.add_parser("compile-specs")
    sub.add_parser("check-llms")

    run_once = sub.add_parser("run-once")
    run_once.add_argument("--theme-limit", type=int, default=3)
    run_once.add_argument("--repos-per-theme", type=int, default=20)
    run_once.add_argument("--deep-limit", type=int, default=2)
    run_once.add_argument("--validate-limit", type=int, default=1)

    monitor_once = sub.add_parser("market-monitor-once")
    monitor_once.add_argument("--theme-limit", type=int, default=8)
    monitor_once.add_argument("--repos-per-theme", type=int, default=20)

    ops_loop = sub.add_parser("ops-loop")
    ops_loop.add_argument("--interval-hours", type=float, default=12)
    ops_loop.add_argument("--theme-limit", type=int, default=3)
    ops_loop.add_argument("--repos-per-theme", type=int, default=20)
    ops_loop.add_argument("--deep-limit", type=int, default=2)
    ops_loop.add_argument("--validate-limit", type=int, default=1)
    ops_loop.add_argument("--no-immediate", action="store_true")

    monitor_loop = sub.add_parser("market-monitor-loop")
    monitor_loop.add_argument("--interval-hours", type=float, default=1)
    monitor_loop.add_argument("--theme-limit", type=int, default=8)
    monitor_loop.add_argument("--repos-per-theme", type=int, default=20)
    monitor_loop.add_argument("--no-immediate", action="store_true")

    sub.add_parser("report-today")
    sub.add_parser("latest-run")

    args = parser.parse_args()

    if args.command == "init-db":
        Database(DB_PATH).init()
        print(f"initialized {DB_PATH}")
        return

    if args.command == "compile-specs":
        load_env_file(ROOT / ".env")
        plan_path = SpecXAdapter(ROOT).compile_contract()
        compiler = SpecCompiler(ROOT)
        compiled = compiler.compile_all()
        print(f"compiled SpecX plan: {plan_path}")
        print(f"compiled {len(compiled)} agent specs")
        return

    if args.command == "check-llms":
        load_env_file(ROOT / ".env")
        results = {}
        for name, client_factory in {"orchestrator": OrchestratorLLMClient, "worker": WorkerLLMClient, "gpt_agent": GPTAgentLLMClient}.items():
            try:
                results[name] = client_factory().complete_json(
                    "Return strict JSON only. Do not include markdown.",
                    f'Return exactly this JSON object with no extra text: {{"ok":true,"provider":"{name}"}}',
                )
            except Exception as exc:
                results[name] = {"ok": False, "error": str(exc)}
        print(results)
        if any(result.get("ok") is False for result in results.values()):
            raise SystemExit(1)
        return

    if args.command == "run-once":
        loop = OpportunityLoop(ROOT, DB_PATH)
        summary = loop.run_once(
            theme_limit=args.theme_limit,
            repos_per_theme=args.repos_per_theme,
            deep_limit=args.deep_limit,
            validate_limit=args.validate_limit,
        )
        print(summary.to_text())
        return

    if args.command == "market-monitor-once":
        loop = OpportunityLoop(ROOT, DB_PATH)
        result = loop.run_market_monitor(theme_limit=args.theme_limit, repos_per_theme=args.repos_per_theme)
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "ops-loop":
        interval_seconds = int(args.interval_hours * 60 * 60)
        if interval_seconds <= 0:
            raise SystemExit("--interval-hours must be positive")
        loop = OpportunityLoop(ROOT, DB_PATH)
        print(f"ops loop interval: {args.interval_hours:g}h ({interval_seconds}s)")
        if args.no_immediate:
            print(f"first run scheduled after {args.interval_hours:g}h")
            time.sleep(interval_seconds)
        while True:
            started = datetime.now().isoformat(timespec="seconds")
            print(f"[{started}] ops loop run started")
            try:
                summary = loop.run_once(
                    theme_limit=args.theme_limit,
                    repos_per_theme=args.repos_per_theme,
                    deep_limit=args.deep_limit,
                    validate_limit=args.validate_limit,
                )
                print(summary.to_text())
            except Exception as exc:
                print(f"ops loop run failed: {exc}")
            print(f"next ops loop run in {args.interval_hours:g}h")
            time.sleep(interval_seconds)

    if args.command == "market-monitor-loop":
        interval_seconds = int(args.interval_hours * 60 * 60)
        if interval_seconds <= 0:
            raise SystemExit("--interval-hours must be positive")
        loop = OpportunityLoop(ROOT, DB_PATH)
        print(f"market monitor interval: {args.interval_hours:g}h ({interval_seconds}s)")
        if args.no_immediate:
            print(f"first market monitor run scheduled after {args.interval_hours:g}h")
            time.sleep(interval_seconds)
        while True:
            started = datetime.now().isoformat(timespec="seconds")
            print(f"[{started}] market monitor run started")
            try:
                result = loop.run_market_monitor(theme_limit=args.theme_limit, repos_per_theme=args.repos_per_theme)
                print(f"candidate themes: {', '.join(result.get('candidate_themes') or [])}")
            except Exception as exc:
                print(f"market monitor run failed: {exc}")
            print(f"next market monitor run in {args.interval_hours:g}h")
            time.sleep(interval_seconds)

    if args.command == "report-today":
        db = Database(DB_PATH)
        print(today_report(db))
        return

    if args.command == "latest-run":
        import json

        db = Database(DB_PATH)
        db.init()
        print(json.dumps(db.latest_run_snapshot(), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
