from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


class MarketEvidenceCollector:
    """Evidence-only public market signal collector."""

    def collect_topic_signals(self) -> dict:
        """Collect public market signals for theme discovery.

        This method intentionally does not choose themes. It gathers evidence
        from public feeds/pages so market_monitor_agent can decide.
        """
        trends = self._google_trending_daily(limit=20)
        trend_titles = [item.get("title", "") for item in trends.get("items", [])[:6] if item.get("title")]
        youtube_queries = trend_titles[:4]
        return {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "hacker_news_recent": self._hacker_news_recent(),
                "hacker_news_ask": self._hacker_news_recent(tags="ask_hn"),
                "reddit_communities": self._reddit_communities(),
                "product_hunt": self._product_hunt_home(),
                "google_trends": trends,
                "youtube": self._youtube_queries(youtube_queries),
                "x": self._x_queries(trend_titles[:5]),
            },
            "note": "Evidence-only market monitoring. market_monitor_agent selects themes; scripts must not decide opportunity themes.",
        }

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

    def _hacker_news_recent(self, tags: str = "story") -> dict:
        since = int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp())
        url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(
            {"tags": tags, "hitsPerPage": 25, "numericFilters": f"created_at_i>{since}"}
        )
        payload = self._get_json(url)
        hits = payload.get("hits", []) if isinstance(payload, dict) else []
        return {
            "source": f"hacker_news_{tags}",
            "available": bool(payload) and "error" not in payload,
            "total": payload.get("nbHits", 0) if isinstance(payload, dict) else 0,
            "items": [
                {
                    "title": item.get("title") or item.get("story_title"),
                    "url": item.get("url") or item.get("story_url"),
                    "points": item.get("points"),
                    "comments": item.get("num_comments"),
                    "created_at": item.get("created_at"),
                }
                for item in hits[:25]
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

    def _reddit_communities(self) -> dict:
        communities = [
            "artificial",
            "LocalLLaMA",
            "selfhosted",
            "SaaS",
            "startups",
            "nocode",
            "MachineLearning",
            "webdev",
        ]
        groups = []
        for community in communities:
            url = f"https://www.reddit.com/r/{community}/hot.json?" + urllib.parse.urlencode({"limit": 8})
            payload = self._get_json(url)
            children = (((payload or {}).get("data") or {}).get("children") or []) if isinstance(payload, dict) else []
            groups.append(
                {
                    "community": community,
                    "available": bool(children),
                    "items": [
                        {
                            "title": (child.get("data") or {}).get("title"),
                            "score": (child.get("data") or {}).get("score"),
                            "comments": (child.get("data") or {}).get("num_comments"),
                            "url": "https://www.reddit.com" + str((child.get("data") or {}).get("permalink", "")),
                        }
                        for child in children[:8]
                    ],
                }
            )
        return {"source": "reddit_communities", "available": any(group["available"] for group in groups), "groups": groups}

    def _product_hunt(self, query: str) -> dict:
        url = "https://www.producthunt.com/search?q=" + urllib.parse.quote_plus(query)
        html = self._get_text(url)
        return {
            "source": "product_hunt",
            "available": bool(html) and "error" not in html[:80].lower(),
            "query_url": url,
            "items": self._html_titles(html, limit=5),
        }

    def _product_hunt_home(self) -> dict:
        url = "https://www.producthunt.com/"
        html = self._get_text(url)
        return {
            "source": "product_hunt_home",
            "available": bool(html) and not html.startswith("error:"),
            "query_url": url,
            "items": self._html_titles(html, limit=25),
        }

    def _youtube(self, query: str) -> dict:
        url = "https://www.youtube.com/feeds/videos.xml?search_query=" + urllib.parse.quote_plus(query)
        text = self._get_text(url)
        items = self._rss_items(text, limit=5)
        return {
            "source": "youtube",
            "available": bool(items),
            "query_url": "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query),
            "items": items,
        }

    def _youtube_queries(self, queries: list[str]) -> dict:
        rows = []
        for query in queries:
            rows.append({"query": query, **self._youtube(query)})
        return {"source": "youtube_queries", "available": any(row.get("available") for row in rows), "queries": rows}

    def _google_trends(self, query: str) -> dict:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        text = self._get_text(url)
        items = [item for item in self._rss_items(text, limit=25) if self._matches(query, item.get("title", ""))][:5]
        return {
            "source": "google_trends",
            "available": bool(text),
            "query_url": "https://trends.google.com/trends/explore?q=" + urllib.parse.quote_plus(query),
            "items": items,
        }

    def _google_trending_daily(self, limit: int = 25) -> dict:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        text = self._get_text(url)
        return {
            "source": "google_trends_daily",
            "available": bool(text) and not text.startswith("error:"),
            "query_url": url,
            "items": self._rss_items(text, limit=limit),
        }

    def _x(self, query: str) -> dict:
        url = "https://x.com/search?q=" + urllib.parse.quote_plus(query) + "&src=typed_query"
        html = self._get_text(url)
        return {
            "source": "x",
            "available": bool(html) and "error" not in html[:80].lower(),
            "query_url": url,
            "items": self._html_titles(html, limit=5),
        }

    def _x_queries(self, queries: list[str]) -> dict:
        rows = []
        for query in queries:
            rows.append({"query": query, **self._x(query)})
        return {"source": "x_queries", "available": any(row.get("available") for row in rows), "queries": rows}

    @staticmethod
    def _get_json(url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "aigithub-commercial-radar"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _get_text(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 aigithub-commercial-radar"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            return f"error: {exc}"

    @staticmethod
    def _rss_items(text: str, limit: int) -> list[dict]:
        if not text or text.startswith("error:"):
            return []
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        result = []
        for item in root.findall(".//item")[:limit]:
            result.append(
                {
                    "title": (item.findtext("title") or "").strip(),
                    "url": (item.findtext("link") or "").strip(),
                    "published": (item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}published") or "").strip(),
                }
            )
        if result:
            return result
        ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
        for entry in root.findall(".//atom:entry", ns)[:limit]:
            link = entry.find("atom:link", ns)
            result.append(
                {
                    "title": (entry.findtext("atom:title", default="", namespaces=ns) or "").strip(),
                    "url": link.get("href") if link is not None else "",
                    "published": (entry.findtext("atom:published", default="", namespaces=ns) or "").strip(),
                }
            )
        return result

    @staticmethod
    def _html_titles(html: str, limit: int) -> list[dict]:
        if not html or html.startswith("error:"):
            return []
        titles = []
        for match in re.finditer(r"<title[^>]*>(.*?)</title>|<h[12][^>]*>(.*?)</h[12]>", html, flags=re.I | re.S):
            raw = match.group(1) or match.group(2) or ""
            title = re.sub(r"<[^>]+>", "", raw)
            title = re.sub(r"\s+", " ", title).strip()
            if title and title not in titles:
                titles.append(title)
            if len(titles) >= limit:
                break
        return [{"title": title} for title in titles]

    @staticmethod
    def _matches(query: str, text: str) -> bool:
        words = {word.lower() for word in re.findall(r"[a-zA-Z0-9]{4,}", query)}
        target = text.lower()
        return any(word in target for word in words)
