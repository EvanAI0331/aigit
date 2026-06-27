from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


AGENTS = [
    "market_monitor_agent",
    "orchestrator_agent",
    "scout_agent",
    "repo_analyst",
    "pain_finder",
    "business_designer",
    "validator_agent",
    "strategist_agent",
]

SPEC_PARTS = ["role", "execution", "output"]


@dataclass(frozen=True)
class CompiledSpec:
    agent: str
    artifact: Path


class SpecCompiler:
    """Strict local compiler adapter.

    This validates role/execution/output specs and writes immutable compiled
    artifacts consumed by the runtime. It is intentionally fail-closed so a
    missing professional compiler cannot be hidden as a successful agent run.
    """

    def __init__(self, root: Path):
        self.root = root
        self.spec_dir = root / "specs" / "agents"
        self.skill_dir = root / "skills" / "agents"
        self.out_dir = root / "build" / "compiled_specs"

    def compile_all(self) -> list[CompiledSpec]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        compiled: list[CompiledSpec] = []
        for agent in AGENTS:
            compiled.append(self.compile_agent(agent))
        return compiled

    def compile_agent(self, agent: str) -> CompiledSpec:
        payload: dict[str, object] = {"agent": agent, "specs": {}, "skill": "", "external_skills": []}
        for part in SPEC_PARTS:
            path = self.spec_dir / f"{agent}.{part}.md"
            if not path.exists():
                raise FileNotFoundError(f"missing spec: {path}")
            text = path.read_text(encoding="utf-8").strip()
            self._assert_required_sections(path, text)
            payload["specs"][part] = {"path": str(path), "sha256": self._sha(text), "text": text}

        skill_path = self.skill_dir / f"{agent}.md"
        if not skill_path.exists():
            raise FileNotFoundError(f"missing skill: {skill_path}")
        skill = skill_path.read_text(encoding="utf-8").strip()
        self._assert_required_sections(skill_path, skill)
        payload["skill"] = {"path": str(skill_path), "sha256": self._sha(skill), "text": skill}
        payload["external_skills"] = self._compile_external_skills(skill_path, skill)
        payload["compiled_by"] = "aigithub_radar.strict_spec_compiler"
        payload["runtime_contract"] = "llm_required_no_fallback"

        artifact = self.out_dir / f"{agent}.compiled.json"
        artifact.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return CompiledSpec(agent=agent, artifact=artifact)

    def assert_compiled(self) -> None:
        for agent in AGENTS:
            path = self.out_dir / f"{agent}.compiled.json"
            if not path.exists():
                raise RuntimeError(f"agent spec is not compiled: {agent}; run compile-specs")

    @staticmethod
    def _assert_required_sections(path: Path, text: str) -> None:
        required = ["## Purpose", "## Contract"]
        missing = [section for section in required if section not in text]
        if missing:
            raise ValueError(f"{path} missing sections: {', '.join(missing)}")

    @staticmethod
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _compile_external_skills(self, skill_path: Path, skill: str) -> list[dict[str, str]]:
        refs = self._external_skill_refs(skill)
        compiled: list[dict[str, str]] = []
        for ref in refs:
            path = (self.root / ref).resolve()
            if not str(path).startswith(str(self.root.resolve())):
                raise RuntimeError(f"external skill escapes project root in {skill_path}: {ref}")
            if not path.exists():
                raise FileNotFoundError(f"missing external skill referenced by {skill_path}: {ref}")
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                raise RuntimeError(f"empty external skill referenced by {skill_path}: {ref}")
            compiled.append({"path": ref, "sha256": self._sha(text), "text": text})
        return compiled

    @staticmethod
    def _external_skill_refs(skill: str) -> list[str]:
        refs: list[str] = []
        in_section = False
        for line in skill.splitlines():
            if line.strip() == "## External Skill References":
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                match = re.search(r"`([^`]+)`", line)
                if match:
                    refs.append(match.group(1))
        return refs
