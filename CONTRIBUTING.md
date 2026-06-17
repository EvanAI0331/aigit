# Contributing

Contributions should preserve the core architecture: LLM agents make core judgments through specs and skills; scripts collect evidence, validate contracts, persist state, and execute workflow transitions.

## Good First Contributions

- Add evidence collectors.
- Improve frontend API integration and dashboard states.
- Add validation fields to specs and contracts.
- Add report formats.
- Improve documentation and launch examples.

## Rules

- Do not commit `.env`, database files, compiled specs, logs, or provider keys.
- Do not replace agent judgment with hardcoded keyword routing.
- Do not add silent fallback or fake success states.
- Every new agent must have a role spec, execution spec, output spec, and skill.
- Constraints belong in specs; tactics and capabilities belong in skills.

## Local Checks

```bash
python3 -m compileall aigithub_radar
python3 -m aigithub_radar.cli compile-specs
```

Real agent execution also requires valid provider keys in `.env`.
