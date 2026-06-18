from __future__ import annotations

import json
import urllib.parse
import urllib.request


class MarketEvidenceCollector:
    """Evidence-only public market signal collector."""

    def collect(self, repo: dict, analysis: dict | None = None, pain: dict | None = None) -> dict:
        query = self._query(repo, analysis, pain)
        return {
            "query": query,
            "hacker_news": self._hacker_news(query),
            "reddit": self._reddit(query),
            "product_hunt": self._product_hunt(query),
            "youtube": self._youtube(query),
            "google_trends": self._google_trends(query),
            "x": self._x(query),
            "note": "Evidence-only collector. Validator agent interprets demand, competition, saturation, and monetization implications.",
        }

    @staticmethod
    def _query(repo: dict, analysis: dict | None, pain: dict | None) -> str:
        topics = repo.get("topics") or []
        seeds = [
            repo.get("full_name", "").split("/")[-1].replace("-", " "),
            repo.get("description", ""),
            (analysis or {}).get("problem", ""),
            (pain or {}).get("user_pain", ""),
            " ".join(topics[:4]),
        ]
        text = " ".join(str(item) for item in seeds if item).strip()
        return " ".join(text.split()[:12])

    def _hacker_news(self, query: str) -> dict:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": 5})
        payload = self._get_json(url)
        hits = payload.get("hits", []) if isinstance(payload, dict) else []
        return {
            "source": "hacker_news",
            "available": bool(payload),
            "total": payload.get("nbHits", 0) if isinstance(payload, dict) else 0,
            "items": [
                {"title": item.get("title"), "url": item.get("url"), "points": item.get("points"), "created_at": item.get("created_at")}
                for item in hits[:5]
            ],
        }

    def _reddit(self, query: str) -> dict:
        url = "https://www.reddit.com/search.json?" + urllib.parse.urlencode({"q": query, "sort": "relevance", "limit": 5})
        payload = self._get_json(url)
        children = (((payload or {}).get("data") or {}).get("children") or []) if isinstance(payload, dict) else []
        return {
            "source": "reddit",
            "available": bool(payload),
            "total": len(children),
            "items": [
                {
                    "title": (child.get("data") or {}).get("title"),
                    "subreddit": (child.get("data") or {}).get("subreddit"),
                    "score": (child.get("data") or {}).get("score"),
                    "url": "https://www.reddit.com" + str((child.get("data") or {}).get("permalink", "")),
                }
                for child in children[:5]
            ],
        }

    def _product_hunt(self, query: str) -> dict:
        return {
            "source": "product_hunt",
            "available": False,
            "query_url": "https://www.producthunt.com/search?q=" + urllib.parse.quote_plus(query),
            "note": "Public search page recorded for follow-up; API connector not configured.",
        }

    def _youtube(self, query: str) -> dict:
        return {
            "source": "youtube",
            "available": False,
            "query_url": "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query),
            "note": "Public query URL recorded for follow-up; API connector not configured.",
        }

    def _google_trends(self, query: str) -> dict:
        return {
            "source": "google_trends",
            "available": False,
            "query_url": "https://trends.google.com/trends/explore?q=" + urllib.parse.quote_plus(query),
            "note": "Trend query URL recorded for follow-up; API connector not configured.",
        }

    def _x(self, query: str) -> dict:
        return {
            "source": "x",
            "available": False,
            "query_url": "https://x.com/search?q=" + urllib.parse.quote_plus(query) + "&src=typed_query",
            "note": "Public query URL recorded for follow-up; API connector not configured.",
        }

    @staticmethod
    def _get_json(url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "aigithub-commercial-radar"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"error": str(exc)}
