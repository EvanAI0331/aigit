# AIGitHub Commercial Radar

[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![Agent Harness](https://img.shields.io/badge/Agent%20Harness-Spec%20%2B%20Skill%20Driven-ff7a00.svg)](AGENTS.md)

> A strict agent-loop system that continuously scans GitHub and turns open-source activity into validated commercial opportunity signals.

OpenSource Opportunity Agent: a continuous agent loop that scans GitHub, analyzes open-source projects, validates commercial opportunity, stores qualified opportunities, and creates next actions.

This system is not a user-search tool. The operator runs the harness; the harness orchestrates role-specific LLM agents and evidence scripts.

## Why Star This Repo

- Find open-source projects that can become real commercial products.
- Study a strict LLM-agent harness where agents must have role specs, execution specs, output specs, and skills.
- Reuse the validation loop for founder discovery, repo analysis, pain mining, business design, and go-to-market next actions.
- Track how evidence scripts and LLM agents can cooperate without turning the agent into a hardcoded keyword bot.

## What It Does

```text
GitHub signals -> LLM scout -> evidence collection -> repo analysis
  -> pain discovery -> business design -> founder-style validation
  -> approval/rejection -> next action plan
```

The loop is designed for founders, indie hackers, product strategists, and AI-agent builders who want a repeatable way to discover software business opportunities from open-source momentum.

## Principles

- Core opportunity judgment is LLM/agent driven.
- Scripts collect facts, enforce contracts, persist state, and execute workflow transitions.
- No hardcoded keyword routing, fake success state, or silent fallback.
- An agent is only valid when it has a role spec, execution spec, output spec, and skill.
- If specs are not compiled, or the LLM provider is missing, the loop fails closed.

## Quick Start

Clone and configure:

```bash
git clone https://github.com/EvanAI0331/aigit.git
cd aigit
cp .env.example .env
```

Fill `.env` with your own provider keys. Never commit `.env`.

Run one scan:

```bash
python3 -m aigithub_radar.cli init-db
python3 -m aigithub_radar.cli compile-specs
python3 -m aigithub_radar.cli run-once --theme-limit 3 --repos-per-theme 20 --deep-limit 2 --validate-limit 1
python3 -m aigithub_radar.cli report-today
```

Run continuously every 12 hours:

```bash
python3 -m aigithub_radar.cli ops-loop --interval-hours 12 --theme-limit 3 --repos-per-theme 20 --deep-limit 2 --validate-limit 1
```

Run the local frontend/backend:

```bash
python3 -m aigithub_radar.server
```

Open `http://127.0.0.1:8028`.

Required for real agent execution:

```bash
export AIGITHUB_ORCHESTRATOR_API_KEY=...
export AIGITHUB_ORCHESTRATOR_BASE_URL=...
export AIGITHUB_ORCHESTRATOR_MODEL=...
export AIGITHUB_ORCHESTRATOR_DISABLE_THINKING=true

export AIGITHUB_WORKER_API_KEY=...
export AIGITHUB_WORKER_BASE_URL=...
export AIGITHUB_WORKER_MODEL=...
```

The orchestrator/scout agents use the orchestrator LLM endpoint. The remaining agents use the worker LLM endpoint. Both endpoints must be OpenAI-compatible chat completion APIs.

Optional for GitHub rate limits:

```bash
export GITHUB_TOKEN=...
```

## Agent Roles

| Agent | Responsibility |
| --- | --- |
| `orchestrator_agent` | Plans the run and enforces the ops sequence. |
| `scout_agent` | Uses LLM judgment to generate GitHub search themes and queries. |
| `repo_analyst` | Converts repository evidence into adoption, activity, license, and packaging analysis. |
| `pain_finder` | Extracts likely user pain and buyer urgency. |
| `business_designer` | Designs commercial packaging, pricing, channels, and MVP tests. |
| `validator_agent` | Runs the founder-style validation gate and rejects weak opportunities. |
| `strategist_agent` | Creates next actions only after approval. |

## Workflow

```text
theme pool
  -> scout agent
  -> github evidence scripts
  -> repo analyst agent
  -> pain finder agent
  -> business designer agent
  -> validator agent
  -> scoring harness
  -> database
  -> strategist agent
```

Statuses:

```text
DISCOVERED -> SCREENED -> ANALYZED -> VALIDATED -> APPROVED -> STORED -> NEXT_ACTION_CREATED
```

Rejected statuses:

```text
REJECTED_LICENSE_RISK
REJECTED_LOW_DEMAND
REJECTED_NO_BUSINESS_MODEL
REJECTED_TOO_HARD_TO_PACKAGE
REJECTED_TOO_GENERIC
REJECTED_ALREADY_SATURATED
```

## Spec Contract

Specs live in `specs/agents`. Skills live in `skills/agents`.

`python3 -m aigithub_radar.cli compile-specs` first validates, verifies, and compiles `specx/contracts/opportunity_agent_loop.json` through the SpecX plugin CLI, then validates every agent has:

- role spec
- execution spec
- output spec
- skill file

The compiler writes `build/specx/opportunity_agent_loop.plan.json` and `build/compiled_specs/*.compiled.json`. The loop refuses to run without these compiled artifacts.

The current SpecX plugin release provides skills and CLI validation/compilation, not live MCP execution tools. The project uses that CLI directly through `aigithub_radar/harness/specx_adapter.py`.

## Distribution

- Star the repo if you care about strict LLM-agent harnesses for business discovery.
- Share the launch copy in [docs/PROMOTION.md](docs/PROMOTION.md).
- Use [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md) to publish on GitHub, Hacker News, X, LinkedIn, Reddit, Product Hunt, and AI-builder communities.
- Open issues for new collectors, validation gates, agent roles, and frontend dashboards.
