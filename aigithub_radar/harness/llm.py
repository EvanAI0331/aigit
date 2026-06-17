from __future__ import annotations

import json
import os
import re
from pathlib import Path
import urllib.error
import urllib.request


class LLMClient:
    def complete_json(self, system: str, user: str) -> dict:
        raise NotImplementedError


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class OpenAICompatibleChatClient(LLMClient):
    def __init__(self, *, api_key_env: str, base_url_env: str, model_env: str, default_base_url: str, default_model: str, extra_body: dict | None = None) -> None:
        self.api_key_env = api_key_env
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise RuntimeError(f"{api_key_env} is required for agent execution; no fallback is allowed")
        self.base_url = os.environ.get(base_url_env, default_base_url).rstrip("/")
        self.model = os.environ.get(model_env, default_model)
        if not self.base_url:
            raise RuntimeError(f"{base_url_env} is required for agent execution; no fallback is allowed")
        if not self.model:
            raise RuntimeError(f"{model_env} is required for agent execution; no fallback is allowed")
        self.extra_body = extra_body or {}

    def complete_json(self, system: str, user: str) -> dict:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_completion_tokens": 4000,
        }
        body.update(self.extra_body)
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(exc.read().decode("utf-8")) from exc

        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return parse_json_content(str(content))


def parse_json_content(content: str) -> dict:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM returned JSON but not an object")
    return parsed


class OrchestratorLLMClient(OpenAICompatibleChatClient):
    def __init__(self) -> None:
        extra_body = {}
        disable_thinking = os.environ.get("AIGITHUB_ORCHESTRATOR_DISABLE_THINKING", "false").lower()
        if disable_thinking in {"1", "true", "yes"}:
            extra_body["enable_thinking"] = False
        super().__init__(
            api_key_env="AIGITHUB_ORCHESTRATOR_API_KEY",
            base_url_env="AIGITHUB_ORCHESTRATOR_BASE_URL",
            model_env="AIGITHUB_ORCHESTRATOR_MODEL",
            default_base_url="",
            default_model="",
            extra_body=extra_body,
        )


class WorkerLLMClient(OpenAICompatibleChatClient):
    def __init__(self) -> None:
        super().__init__(
            api_key_env="AIGITHUB_WORKER_API_KEY",
            base_url_env="AIGITHUB_WORKER_BASE_URL",
            model_env="AIGITHUB_WORKER_MODEL",
            default_base_url="",
            default_model="",
        )
