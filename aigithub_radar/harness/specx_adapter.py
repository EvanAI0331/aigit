from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


class SpecXAdapter:
    def __init__(self, root: Path):
        self.root = root
        self.contract_path = root / "specx" / "contracts" / "opportunity_agent_loop.json"
        self.plan_path = root / "build" / "specx" / "opportunity_agent_loop.plan.json"
        configured_cli = os.environ.get("SPECX_CLI_PATH", "").strip()
        self.plugin_cli = Path(configured_cli) if configured_cli else None

    def compile_contract(self) -> Path:
        if self.plugin_cli is None or not self.plugin_cli.exists():
            raise RuntimeError("SpecX CLI is missing; set SPECX_CLI_PATH in .env")
        self._run("validate")
        self._run("verify")
        compiled = self._run("compile")
        self.plan_path.parent.mkdir(parents=True, exist_ok=True)
        self.plan_path.write_text(json.dumps(compiled["result"], ensure_ascii=False, indent=2), encoding="utf-8")
        return self.plan_path

    def assert_plan(self) -> None:
        if not self.plan_path.exists():
            raise RuntimeError("SpecX execution plan missing; run compile-specs")
        plan = json.loads(self.plan_path.read_text(encoding="utf-8"))
        if plan.get("status") != "compiled":
            raise RuntimeError("SpecX execution plan is not compiled")

    def _run(self, command: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(self.plugin_cli), command, str(self.contract_path)],
            check=False,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stdout.strip() or proc.stderr.strip())
        payload = json.loads(proc.stdout)
        if payload.get("ok") is not True:
            raise RuntimeError(json.dumps(payload, ensure_ascii=False))
        return payload
