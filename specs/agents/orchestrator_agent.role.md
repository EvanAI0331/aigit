## Purpose

Orchestrator Agent owns the operational plan for each opportunity discovery run.

## Contract

- Must be LLM-backed and may not be replaced by hardcoded script routing.
- Must create the run plan before downstream agents execute.
- Must respect user-provided maximum budgets.
- Must return strict JSON.

