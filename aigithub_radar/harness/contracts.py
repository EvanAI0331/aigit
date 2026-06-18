from __future__ import annotations

from dataclasses import dataclass


VALID_STATUSES = {
    "DISCOVERED",
    "SCREENED",
    "ANALYZED",
    "VALIDATED",
    "APPROVED",
    "EXPERIMENTING",
    "ACTION_PENDING",
    "ACTION_VALIDATED",
    "WATCHLIST",
    "HOLD",
    "STORED",
    "NEXT_ACTION_CREATED",
    "REJECTED_LICENSE_RISK",
    "REJECTED_LOW_DEMAND",
    "REJECTED_NO_BUSINESS_MODEL",
    "REJECTED_TOO_HARD_TO_PACKAGE",
    "REJECTED_TOO_GENERIC",
    "REJECTED_ALREADY_SATURATED",
}

APPROVAL_THRESHOLD = 80
WATCH_THRESHOLD = 65

AGENT_REQUIRED_OUTPUT_FIELDS = {
    "orchestrator_agent": [
        "run_name",
        "selected_themes",
        "repos_per_theme",
        "deep_limit",
        "validate_limit",
        "gate_sequence",
        "evidence_requirements",
        "reason",
    ],
    "scout_agent": ["search_queries", "reason"],
    "repo_analyst": [
        "problem",
        "target_users",
        "repo_type",
        "technical_stack",
        "deploy_difficulty",
        "maintenance_state",
        "license_risk",
        "evidence_notes",
    ],
    "pain_finder": [
        "user_pain",
        "why_hard_to_use",
        "missing_middle_tool",
        "localization_opportunity",
        "template_gap",
        "service_gap",
        "pain_strength",
    ],
    "business_designer": [
        "best_path",
        "not_recommended",
        "reason",
        "mvp_form",
        "estimated_price",
        "template_opportunity",
        "service_opportunity",
        "saas_opportunity",
        "judgment_score",
    ],
    "validator_agent": [
        "problem_hypothesis",
        "customer_discovery_plan",
        "demand_signal",
        "competition_signal",
        "monetization_signal",
        "pmf_vs_hype_check",
        "seven_day_mvp_test",
        "agentic_ops_fit",
        "security_scope_risk",
        "license_check",
        "saturation_check",
        "verdict",
        "validation_score",
        "founder_playbook_score",
        "reason",
    ],
    "strategist_agent": ["next_actions"],
}


@dataclass(frozen=True)
class LoopSummary:
    scanned_themes: list[str]
    discovered: int
    screened: int
    analyzed: int
    validated: int
    approved: int

    def to_text(self) -> str:
        return "\n".join(
            [
                "今日开源商业机会报告",
                f"今日扫描主题: {', '.join(self.scanned_themes)}",
                f"发现项目: {self.discovered}",
                f"初筛通过: {self.screened}",
                f"深度分析: {self.analyzed}",
                f"验证通过: {self.validated}",
                f"重点机会: {self.approved}",
            ]
        )
