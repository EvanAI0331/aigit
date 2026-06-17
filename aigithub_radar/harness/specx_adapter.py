from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PLUGIN_CLI = Path("/Users/xin/.codex/plugins/cache/xin-local-plugins/specx-codex-plugin/0.1.0/scripts/specx_cli.py")


class SpecXAdapter:
    def __init__(self, root: Path):
        self.root = root
        self.contract_path = root / "specx" / "contracts" / "opportunity_agent_loop.json"
        self.plan_path = root / "build" / "specx" / "opportunity_agent_loop.plan.json"

    def compile_contract(self) -> Path:
        if not PLUGIN_CLI.exists():
            raise RuntimeError(f"SpecX CLI is missing: {PLUGIN_CLI}")
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
            [sys.executable, str(PLUGIN_CLI), command, str(self.contract_path)],
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

