from __future__ import annotations

from pathlib import Path

from aigithub_radar.collectors.github import GitHubCollector
from aigithub_radar.collectors.market import MarketEvidenceCollector
from aigithub_radar.harness.agent_runtime import AgentRuntime
from aigithub_radar.harness.contracts import APPROVAL_THRESHOLD, LoopSummary
from aigithub_radar.harness.llm import OrchestratorLLMClient, WorkerLLMClient, load_env_file
from aigithub_radar.harness.scoring import fact_score, opportunity_score
from aigithub_radar.harness.spec_compiler import SpecCompiler
from aigithub_radar.harness.specx_adapter import SpecXAdapter
from aigithub_radar.storage.db import Database


class OpportunityLoop:
    def __init__(self, root: Path, db_path: Path):
        self.root = root
        load_env_file(root / ".env")
        SpecXAdapter(root).assert_plan()
        SpecCompiler(root).assert_compiled()
        self.db = Database(db_path)
        self.collector = GitHubCollector()
        self.market_collector = MarketEvidenceCollector()
        orchestrator_llm = OrchestratorLLMClient()
        worker_llm = WorkerLLMClient()
        self.runtime = AgentRuntime(
            root,
            llms={"orchestrator_agent": orchestrator_llm, "scout_agent": orchestrator_llm},
            default_llm=worker_llm,
        )

    def run_once(self, theme_limit: int, repos_per_theme: int, deep_limit: int, validate_limit: int) -> LoopSummary:
        self.db.init()
        run_id = self.db.create_run()
        try:
            available_themes = self.db.next_themes(theme_limit)
            plan = self.runtime.run(
                "orchestrator_agent",
                {
                    "available_themes": available_themes,
                    "budget_caps": {
                        "theme_limit": theme_limit,
                        "repos_per_theme": repos_per_theme,
                        "deep_limit": deep_limit,
                        "validate_limit": validate_limit,
                    },
                    "constraints": {
                        "no_fake_success": True,
                        "scripts_collect_evidence_only": True,
                        "agent_decisions_require_llm": True,
                    },
                },
                run_id=run_id,
                db=self.db,
            )
            themes = self._bounded_list(plan.get("selected_themes"), available_themes, theme_limit)
            planned_repos_per_theme = self._bounded_int(plan.get("repos_per_theme"), repos_per_theme, minimum=1)
            planned_deep_limit = self._bounded_int(plan.get("deep_limit"), deep_limit, minimum=0)
            planned_validate_limit = self._bounded_int(plan.get("validate_limit"), validate_limit, minimum=0)
            self.db.attach_run_plan(run_id, str(plan.get("run_name") or f"run-{run_id}"), plan)
            self.db.add_event(run_id, "GATE_PASSED", "orchestrator_run_plan_created", plan)

            scout = self.runtime.run("scout_agent", {"themes": themes, "repos_per_theme": planned_repos_per_theme}, run_id=run_id, db=self.db)
            search_queries = scout.get("search_queries")
            if not isinstance(search_queries, list) or not search_queries:
                raise RuntimeError("scout_agent must return non-empty search_queries")

            discovered = 0
            screened_repos: list[dict] = []
            for query in search_queries:
                try:
                    repos = self.collector.search_repositories(str(query), per_page=planned_repos_per_theme)
                except Exception as exc:
                    self.db.add_event(run_id, "EVIDENCE_FAILED", "github_search", {"query": query, "error": str(exc)})
                    continue
                self.db.add_event(run_id, "EVIDENCE_COLLECTED", "github_search", {"query": query, "count": len(repos)})
                for repo in repos:
                    repo_id = self.db.upsert_repo(repo)
                    discovered += 1
                    if fact_score(repo) >= 40:
                        self.db.create_opportunity(repo_id, repo, status="SCREENED")
                        screened_repos.append(repo)

            analyzed = 0
            validated = 0
            approved = 0
            for repo in screened_repos[:planned_deep_limit]:
                try:
                    repo = self.collector.enrich_repository(repo)
                except Exception as exc:
                    self.db.add_event(run_id, "EVIDENCE_FAILED", "repo_readme", {"repo": repo.get("full_name"), "error": str(exc)})
                    continue
                self.db.add_event(run_id, "EVIDENCE_COLLECTED", "repo_readme", {"repo": repo["full_name"], "has_readme": bool(repo.get("readme"))})
                repo_id = self.db.upsert_repo(repo)
                opportunity_id = self.db.ensure_opportunity(repo_id, repo)

                analysis = self.runtime.run("repo_analyst", {"repo": repo}, run_id=run_id, db=self.db)
                pain = self.runtime.run("pain_finder", {"repo": repo, "analysis": analysis}, run_id=run_id, db=self.db)
                business = self.runtime.run("business_designer", {"repo": repo, "analysis": analysis, "pain": pain}, run_id=run_id, db=self.db)
                self.db.save_analysis(opportunity_id, analysis, pain, business)
                analyzed += 1

                if validated >= planned_validate_limit:
                    continue

                validation_evidence = {
                    "github": self.collector.commercial_signals(repo),
                    "market": self.market_collector.collect(repo, analysis, pain),
                    "actions": self.db.action_summary(opportunity_id),
                }
                self.db.add_event(run_id, "EVIDENCE_COLLECTED", "commercial_signals", {"repo": repo["full_name"], "evidence": validation_evidence})
                validation = self.runtime.run(
                    "validator_agent",
                    {"repo": repo, "analysis": analysis, "pain": pain, "business": business, "evidence": validation_evidence},
                    run_id=run_id,
                    db=self.db,
                )
                self.db.save_validation(opportunity_id, validation)
                validated += 1

                score = opportunity_score(
                    fact_score(repo),
                    int(business.get("judgment_score", 0)),
                    int(validation.get("validation_score", 0)),
                    int(validation.get("founder_playbook_score", validation.get("validation_score", 0))),
                )
                status = self._status_from_validation(score, validation)
                self.db.update_opportunity_score(opportunity_id, score, status)

                if status == "APPROVED":
                    self._create_next_actions(run_id, opportunity_id, repo, business, validation)
                    approved += 1
                elif status == "WATCHLIST" and validation.get("verdict") == "WEAK_PASS" and score >= 65:
                    self._create_next_actions(run_id, opportunity_id, repo, business, validation)

            revalidated, reapproved = self._revalidate_watchlist(run_id, planned_validate_limit)
            validated += revalidated
            approved += reapproved

            summary = LoopSummary(
                scanned_themes=themes,
                discovered=discovered,
                screened=len(screened_repos),
                analyzed=analyzed,
                validated=validated,
                approved=approved,
            )
            self.db.finish_run(run_id, "SUCCEEDED")
            return summary
        except Exception as exc:
            self.db.add_event(run_id, "RUN_FAILED", None, {"error": str(exc)})
            self.db.finish_run(run_id, "FAILED", str(exc))
            raise

    @staticmethod
    def _bounded_int(value: object, cap: int, minimum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = cap
        return max(minimum, min(parsed, cap))

    @staticmethod
    def _bounded_list(value: object, fallback: list[str], cap: int) -> list[str]:
        if not isinstance(value, list):
            return fallback[:cap]
        selected = [str(item) for item in value if str(item) in fallback]
        return (selected or fallback)[:cap]

    @staticmethod
    def _status_from_validation(score: int, validation: dict) -> str:
        verdict = validation.get("verdict")
        if score >= APPROVAL_THRESHOLD and verdict in {"PASS", "WEAK_PASS"}:
            return "APPROVED"
        if verdict == "HOLD":
            return "HOLD"
        if verdict == "WEAK_PASS":
            return "WATCHLIST"
        reject_status = validation.get("reject_status")
        if reject_status:
            return str(reject_status)
        return "REJECTED_LOW_DEMAND"

    def _create_next_actions(self, run_id: int, opportunity_id: int, repo: dict, business: dict, validation: dict) -> None:
        action_state = self.db.action_summary(opportunity_id)
        if action_state.get("open", 0) > 0:
            self.db.add_event(run_id, "ACTION_SKIPPED", "open_actions_exist", {"repo": repo.get("full_name"), "opportunity_id": opportunity_id})
            return
        actions = self.runtime.run("strategist_agent", {"repo": repo, "business": business, "validation": validation}, run_id=run_id, db=self.db)
        self.db.save_next_actions(opportunity_id, actions)
        if validation.get("verdict") == "PASS":
            self.db.update_opportunity_status(opportunity_id, "NEXT_ACTION_CREATED")
        self.db.add_event(run_id, "ACTION_CREATED", "strategist_next_actions", {"repo": repo.get("full_name"), "opportunity_id": opportunity_id, "count": len(actions.get("next_actions", []))})

    def _revalidate_watchlist(self, run_id: int, limit: int) -> tuple[int, int]:
        candidates = self.db.revalidation_candidates(max(1, limit))
        revalidated = 0
        reapproved = 0
        for candidate in candidates:
            opportunity_id = int(candidate["opportunity_id"])
            try:
                repo = self.collector.enrich_repository(candidate)
            except Exception as exc:
                self.db.add_event(run_id, "EVIDENCE_FAILED", "revalidation_repo_readme", {"repo": candidate.get("full_name"), "error": str(exc)})
                continue
            repo_id = self.db.upsert_repo(repo)
            opportunity_id = self.db.ensure_opportunity(repo_id, repo)
            bundle = self.db.latest_analysis_bundle(opportunity_id)
            analysis = bundle.get("analysis") or {}
            pain = bundle.get("pain") or {}
            business = bundle.get("business") or {}
            if not analysis or not pain or not business:
                analysis = self.runtime.run("repo_analyst", {"repo": repo, "revalidation": True}, run_id=run_id, db=self.db)
                pain = self.runtime.run("pain_finder", {"repo": repo, "analysis": analysis, "revalidation": True}, run_id=run_id, db=self.db)
                business = self.runtime.run("business_designer", {"repo": repo, "analysis": analysis, "pain": pain, "revalidation": True}, run_id=run_id, db=self.db)
                self.db.save_analysis(opportunity_id, analysis, pain, business)

            github_evidence = self.collector.commercial_signals(repo)
            market_evidence = self.market_collector.collect(repo, analysis, pain)
            action_evidence = self.db.action_summary(opportunity_id)
            evidence = {"github": github_evidence, "market": market_evidence, "actions": action_evidence, "revalidation": True}
            self.db.add_event(run_id, "EVIDENCE_COLLECTED", "revalidation_evidence", {"repo": repo["full_name"], "evidence": evidence})
            validation = self.runtime.run(
                "validator_agent",
                {"repo": repo, "analysis": analysis, "pain": pain, "business": business, "evidence": evidence, "previous_status": candidate.get("opportunity_status")},
                run_id=run_id,
                db=self.db,
            )
            self.db.save_validation(opportunity_id, validation)
            revalidated += 1
            score = opportunity_score(
                fact_score(repo),
                int(business.get("judgment_score", 0)),
                int(validation.get("validation_score", 0)),
                int(validation.get("founder_playbook_score", validation.get("validation_score", 0))),
            )
            status = self._status_from_validation(score, validation)
            self.db.update_opportunity_score(opportunity_id, score, status)
            if status == "APPROVED":
                self._create_next_actions(run_id, opportunity_id, repo, business, validation)
                reapproved += 1
            elif status == "WATCHLIST" and validation.get("verdict") == "WEAK_PASS" and score >= 65:
                self._create_next_actions(run_id, opportunity_id, repo, business, validation)
        return revalidated, reapproved
