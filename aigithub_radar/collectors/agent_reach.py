from __future__ import annotations

import json
import shutil
import subprocess
import urllib.parse
import urllib.request


class AgentReachEvidenceCollector:
    """Best-effort evidence bridge for Agent-Reach style platform monitoring.

    The bridge uses public APIs and local CLI/MCP tools when they are installed.
    It never treats an unavailable platform as successful evidence.
    """

    def collect(self) -> dict:
        return {
            "source": "agent_reach_bridge",
            "github_hot": self._github_hot(),
            "v2ex": self._v2ex_hot(),
            "youtube": self._youtube_search(),
            "bilibili": self._bilibili_search(),
            "xiaohongshu": self._xiaohongshu(),
            "douyin": self._douyin(),
            "wechat": self._wechat(),
            "toutiao": self._domain_probe("toutiao", "site:toutiao.com AI 工具 OR 开源 OR 自动化"),
            "shipinhao": self._domain_probe("shipinhao", "site:channels.weixin.qq.com AI 工具 OR 开源 OR 自动化"),
            "xianyu": self._domain_probe("xianyu", "site:goofish.com AI 工具 OR 自动化 OR 本地部署"),
            "note": "Agent-Reach bridge. Scripts gather platform evidence/status only; market_monitor_agent interprets themes.",
        }

    def _github_hot(self) -> dict:
        queries = [
            "AI agent stars:>100 pushed:>2026-01-01",
            "LLM evaluation stars:>50 pushed:>2026-01-01",
            "local LLM GPU stars:>50 pushed:>2026-01-01",
            "WebGPU LLM stars:>50 pushed:>2026-01-01",
            "workflow automation AI stars:>50 pushed:>2026-01-01",
        ]
        rows = []
        gh = shutil.which("gh")
        for query in queries:
            if gh:
                result = self._run(
                    [
                        gh,
                        "search",
                        "repos",
                        query,
                        "--sort",
                        "stars",
                        "--limit",
                        "5",
                        "--json",
                        "fullName,description,stargazersCount,updatedAt,url",
                    ],
                    timeout=20,
                )
                items = self._json_list(result.get("stdout", ""))
                rows.append({"query": query, "available": result["ok"], "items": items[:5], "error": result.get("error")})
            else:
                rows.append({"query": query, "available": False, "items": [], "error": "gh CLI not installed"})
        return {"source": "github_hot", "available": any(row["available"] for row in rows), "queries": rows}

    def _v2ex_hot(self) -> dict:
        data = self._get_json("https://www.v2ex.com/api/topics/hot.json")
        items = []
        if isinstance(data, list):
            for item in data[:20]:
                items.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "node": (item.get("node") or {}).get("title"),
                        "replies": item.get("replies"),
                        "created": item.get("created"),
                    }
                )
        return {"source": "v2ex_hot", "available": bool(items), "items": items, "error": None if items else data.get("error") if isinstance(data, dict) else None}

    def _youtube_search(self) -> dict:
        if not shutil.which("yt-dlp"):
            return {"source": "youtube_agent_reach", "available": False, "items": [], "error": "yt-dlp not installed"}
        queries = ["AI agent evaluation", "local LLM GPU setup", "WebGPU LLM"]
        rows = []
        for query in queries:
            result = self._run(["yt-dlp", "--dump-json", f"ytsearch5:{query}"], timeout=25)
            items = []
            for line in result.get("stdout", "").splitlines():
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                items.append(
                    {
                        "title": payload.get("title"),
                        "url": payload.get("webpage_url"),
                        "channel": payload.get("channel"),
                        "view_count": payload.get("view_count"),
                        "upload_date": payload.get("upload_date"),
                    }
                )
            rows.append({"query": query, "available": bool(items), "items": items[:5], "error": result.get("error") if not items else None})
        return {"source": "youtube_agent_reach", "available": any(row["available"] for row in rows), "queries": rows}

    def _bilibili_search(self) -> dict:
        queries = ["AI agent 评测", "本地大模型 GPU", "WebGPU 大模型"]
        rows = []
        for query in queries:
            url = "https://api.bilibili.com/x/web-interface/search/all/v2?" + urllib.parse.urlencode({"keyword": query, "page": 1})
            payload = self._get_json(url)
            items = []
            if isinstance(payload, dict) and payload.get("code") == 0:
                for group in ((payload.get("data") or {}).get("result") or []):
                    for item in group.get("data") or []:
                        title = item.get("title")
                        if title:
                            items.append(
                                {
                                    "title": _strip_html(str(title)),
                                    "url": item.get("arcurl") or item.get("url"),
                                    "type": group.get("result_type"),
                                    "play": item.get("play"),
                                    "favorites": item.get("favorites"),
                                    "pubdate": item.get("pubdate"),
                                }
                            )
            rows.append({"query": query, "available": bool(items), "items": items[:8], "error": payload.get("error") if isinstance(payload, dict) else None})
        return {"source": "bilibili_search", "available": any(row["available"] for row in rows), "queries": rows}

    def _xiaohongshu(self) -> dict:
        if not shutil.which("xhs"):
            return {"source": "xiaohongshu", "available": False, "items": [], "error": "xhs CLI not installed; run xhs login after installation"}
        queries = ["AI工具", "本地大模型", "自动化工具"]
        rows = []
        for query in queries:
            result = self._run(["xhs", "search", query], timeout=25)
            rows.append({"query": query, "available": result["ok"], "raw": _truncate(result.get("stdout", ""), 4000), "error": result.get("error")})
        return {"source": "xiaohongshu", "available": any(row["available"] for row in rows), "queries": rows}

    def _douyin(self) -> dict:
        if not shutil.which("mcporter"):
            return {"source": "douyin", "available": False, "items": [], "error": "mcporter not installed"}
        config = self._run(["mcporter", "config", "list"], timeout=8)
        if "douyin" not in config.get("stdout", ""):
            return {"source": "douyin", "available": False, "items": [], "error": "douyin MCP not configured in mcporter"}
        tools = self._run(["mcporter", "list", "douyin"], timeout=15)
        return {
            "source": "douyin",
            "available": tools["ok"],
            "items": [],
            "tool_status": _truncate(tools.get("stdout", ""), 2000),
            "error": None if tools["ok"] else tools.get("error"),
            "note": "Current Agent-Reach Douyin channel supports video parsing, not global keyword search.",
        }

    def _wechat(self) -> dict:
        if not shutil.which("mcporter"):
            return {"source": "wechat", "available": False, "items": [], "error": "mcporter not installed"}
        config = self._run(["mcporter", "config", "list"], timeout=8)
        if "exa" not in config.get("stdout", "").lower():
            return {"source": "wechat", "available": False, "items": [], "error": "Exa MCP not configured for WeChat article search"}
        query = 'exa.web_search_exa(query: "AI agent 评测 site:mp.weixin.qq.com", numResults: 5, includeDomains: ["mp.weixin.qq.com"])'
        result = self._run(["mcporter", "call", query], timeout=25)
        return {"source": "wechat", "available": result["ok"], "raw": _truncate(result.get("stdout", ""), 4000), "error": result.get("error")}

    def _domain_probe(self, source: str, query: str) -> dict:
        url = "https://s.jina.ai/?" + urllib.parse.urlencode({"q": query})
        result = self._get_text(url, timeout=12)
        ok = bool(result) and not result.startswith("error:")
        return {
            "source": source,
            "available": ok,
            "query_url": url,
            "items": _title_lines(result, limit=8) if ok else [],
            "error": None if ok else result,
            "note": "Generic web-search probe for platforms without configured Agent-Reach search channel.",
        }

    @staticmethod
    def _run(cmd: list[str], timeout: int) -> dict:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": "", "error": str(exc)}
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "error": None if proc.returncode == 0 else _truncate((proc.stderr or proc.stdout or "").strip(), 1000),
        }

    @staticmethod
    def _json_list(raw: str) -> list[dict]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return payload if isinstance(payload, list) else []

    @staticmethod
    def _get_json(url: str) -> dict | list:
        req = urllib.request.Request(url, headers={"User-Agent": "aigithub-radar-agent-reach"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _get_text(url: str, timeout: int) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "aigithub-radar-agent-reach"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            return f"error: {exc}"


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text).strip()


def _title_lines(text: str, limit: int) -> list[dict]:
    rows = []
    for line in text.splitlines():
        clean = line.strip(" #*-")
        if len(clean) >= 6:
            rows.append({"title": clean})
        if len(rows) >= limit:
            break
    return rows


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "...[truncated]"
