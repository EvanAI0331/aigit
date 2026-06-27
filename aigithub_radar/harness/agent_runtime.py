from __future__ import annotations

import json
from pathlib import Path
import time

from aigithub_radar.harness.contracts import AGENT_REQUIRED_OUTPUT_FIELDS
from aigithub_radar.harness.llm import LLMClient


class AgentRuntime:
    def __init__(self, root: Path, llms: dict[str, LLMClient], default_llm: LLMClient):
        self.root = root
        self.llms = llms
        self.default_llm = default_llm
        self.compiled_dir = root / "build" / "compiled_specs"

    def run(self, agent: str, payload: dict, *, run_id: int | None = None, db=None) -> dict:
        invocation_id = db.start_agent_invocation(run_id, agent, payload) if db is not None and run_id is not None else None
        compiled = self._load(agent)
        system = "\n\n".join(
            [
                compiled["specs"]["role"]["text"],
                compiled["specs"]["execution"]["text"],
                compiled["specs"]["output"]["text"],
                compiled["skill"]["text"],
                self._external_skill_text(compiled),
            ]
        )
        user = json.dumps(payload, ensure_ascii=False, indent=2)
        started = time.monotonic()
        try:
            result = self.llms.get(agent, self.default_llm).complete_json(system=system, user=user, response_schema=self._response_schema(agent))
            if not isinstance(result, dict):
                raise RuntimeError(f"{agent} returned non-object JSON")
            self._assert_output_contract(agent, result)
            if invocation_id is not None:
                db.finish_agent_invocation(invocation_id, result, int((time.monotonic() - started) * 1000))
            return result
        except Exception as exc:
            if invocation_id is not None:
                db.fail_agent_invocation(invocation_id, str(exc), int((time.monotonic() - started) * 1000))
            raise

    def _load(self, agent: str) -> dict:
        path = self.compiled_dir / f"{agent}.compiled.json"
        if not path.exists():
            raise RuntimeError(f"compiled spec missing for {agent}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _external_skill_text(compiled: dict) -> str:
        external = compiled.get("external_skills") or []
        if not external:
            return ""
        blocks = ["# Loaded External Skills\nThese external skills are mandatory context for this run. Apply only the relevant role capabilities; do not relabel scripts as agents."]
        for item in external:
            blocks.append(f"## External Skill: {item['path']}\n\n{item['text']}")
        return "\n\n".join(blocks)

    @staticmethod
    def _assert_output_contract(agent: str, result: dict) -> None:
        required = AGENT_REQUIRED_OUTPUT_FIELDS.get(agent, [])
        missing = [field for field in required if result.get(field) in (None, "")]
        if missing:
            raise RuntimeError(f"{agent} missing required output fields: {', '.join(missing)}")
        if agent == "validator_agent" and result.get("verdict") == "REJECT" and not result.get("reject_status"):
            raise RuntimeError("validator_agent must return reject_status when verdict is REJECT")

    @staticmethod
    def _response_schema(agent: str) -> dict | None:
        required = AGENT_REQUIRED_OUTPUT_FIELDS.get(agent)
        if not required:
            return None
        array_fields = {
            "selected_themes",
            "candidate_themes",
            "demand_signals",
            "heat_signals",
            "rejected_topics",
            "gate_sequence",
            "evidence_requirements",
            "best_path",
            "not_recommended",
            "evidence_notes",
            "search_queries",
            "next_actions",
        }
        integer_fields = {
            "repos_per_theme",
            "deep_limit",
            "validate_limit",
            "demand_score",
            "heat_score",
            "confidence",
            "pain_strength",
            "judgment_score",
            "validation_score",
            "founder_playbook_score",
        }
        properties: dict[str, dict] = {}
        schema_required = list(required)
        if agent == "validator_agent" and "reject_status" not in schema_required:
            schema_required.append("reject_status")
        for field in schema_required:
            if field in array_fields:
                properties[field] = {"type": "array", "items": {"type": "string"}}
            elif field in integer_fields:
                properties[field] = {"type": "integer"}
            else:
                properties[field] = {"type": "string"}
        return {
            "name": f"{agent}_output",
            "schema": {
                "type": "object",
                "properties": properties,
                "required": schema_required,
                "additionalProperties": False,
            },
        }
