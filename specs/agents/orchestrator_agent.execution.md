## Purpose

Define how Orchestrator Agent plans one radar loop.

## Contract

- Read available themes, user budget caps, current date, and system constraints.
- Choose themes for the run.
- Set search, deep-analysis, and validation budgets within caps.
- Define gate sequence and evidence requirements for commercial opportunity discovery.
- Gate names and criteria must focus on repository evidence, adoption pain, business path, Founder Playbook validation, and next-action readiness.
- Every ops cycle must include a re-evaluation lane for old `WATCHLIST`, `ANALYZED`, `VALIDATED`, or `HOLD` opportunities after fresh discovery.
- Re-evaluation must require fresh repository evidence, public market evidence, and action-state evidence before validator re-runs.
- Every ops cycle must also promote a bounded batch of old `SCREENED` backlog items into deep analysis, prioritizing high-evidence repositories that have waited longest.
- Use `EXPERIMENTING`, `ACTION_PENDING`, and `ACTION_VALIDATED` as live workflow states, not final success states.
- Require dispatch of each completed run report and new/open action summary to a configured outlet; skipped outlets must be recorded as skipped, not successful.
- Require governance evidence for GitHub rate limits, failed evidence queries, agent latency, timeout count, and explicit cost availability.
- Do not frame the run as codebase replication, local deployment validation, or generic software refactor.
- Explain why this run plan is appropriate.
- Do not perform repository analysis, business design, or validation.
