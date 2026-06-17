# Promotion Kit

## One-Line Pitch

AIGitHub Commercial Radar is a strict LLM-agent loop that scans GitHub and validates open-source projects as commercial opportunity signals.

## Short Launch Post

I open-sourced AIGitHub Commercial Radar.

It is not a search UI. It is an agent-loop system for founders and AI builders:

- scout GitHub themes with an LLM agent
- collect repository evidence with scripts
- analyze repo health, pain, packaging, and demand
- validate opportunities through a founder-style gate
- store approved opportunities and next actions

The key design principle: agents make core judgments through role specs, execution specs, output specs, and skills. Scripts collect evidence, enforce contracts, persist state, and execute workflow transitions.

Repo: https://github.com/EvanAI0331/aigit

## Long Launch Post

Most GitHub discovery tools stop at search, stars, and trending lists.

AIGitHub Commercial Radar treats GitHub as a commercial signal stream. It continuously scans repositories, sends evidence through specialized LLM agents, validates whether the opportunity has buyer pain and packaging potential, then creates next actions for founders.

The system uses seven agents:

- orchestrator
- scout
- repo analyst
- pain finder
- business designer
- validator
- strategist

Each agent has a role spec, execution spec, output spec, and skill. The harness fails closed if compiled specs or LLM providers are missing. No fake success state, no silent fallback, and no hardcoded keyword bot pretending to be an agent.

Useful for:

- founders looking for open-source business ideas
- indie hackers validating product directions
- agent engineers studying spec/skill-driven loops
- product teams tracking technical market signals

Repo: https://github.com/EvanAI0331/aigit

## README Badge Copy

Strict LLM-agent harness for discovering commercial opportunities from GitHub open-source signals.

## Suggested Social Tags

`#opensource` `#github` `#aiagents` `#indiehackers` `#startups` `#llmops` `#agenticai`

## Communities To Post

- Hacker News: Show HN
- Product Hunt
- X / Twitter
- LinkedIn founder and AI-builder posts
- Reddit: r/LocalLLaMA, r/opensource, r/SideProject, r/Entrepreneur, r/SaaS
- GitHub topic feeds: `ai-agents`, `startup-tools`, `github-analytics`
- Discord/Slack communities for indie hackers and AI agents
