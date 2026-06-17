from __future__ import annotations

import sys
from pathlib import Path

from aigithub_radar.cli import DB_PATH, ROOT
from aigithub_radar.harness.llm import load_env_file
from aigithub_radar.harness.loop import OpportunityLoop
from aigithub_radar.harness.spec_compiler import SpecCompiler
from aigithub_radar.harness.specx_adapter import SpecXAdapter
from aigithub_radar.server import main as server_main
from aigithub_radar.storage.db import Database


def prepare(root: Path = ROOT) -> None:
    load_env_file(root / ".env")
    Database(DB_PATH).init()
    SpecXAdapter(root).compile_contract()
    SpecCompiler(root).compile_all()


def run_web() -> None:
    prepare()
    server_main()


def run_ops() -> None:
    prepare()
    loop = OpportunityLoop(ROOT, DB_PATH)
    # Immediate run on launch, then every 12 hours inside the harness loop.
    import time
    from datetime import datetime

    interval_hours = 12
    interval_seconds = interval_hours * 60 * 60
    print(f"ops loop interval: {interval_hours}h ({interval_seconds}s)", flush=True)
    while True:
        started = datetime.now().isoformat(timespec="seconds")
        print(f"[{started}] ops loop run started", flush=True)
        try:
            summary = loop.run_once(theme_limit=3, repos_per_theme=20, deep_limit=2, validate_limit=1)
            print(summary.to_text(), flush=True)
        except Exception as exc:
            print(f"ops loop run failed: {exc}", flush=True)
        print(f"next ops loop run in {interval_hours}h", flush=True)
        time.sleep(interval_seconds)


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "web":
        run_web()
        return
    if command == "ops":
        run_ops()
        return
    raise SystemExit("usage: python -m aigithub_radar.service_entry [web|ops]")


if __name__ == "__main__":
    main()
