## Purpose

Specify Repo Analyst output.

## Contract

All natural-language string values must be written in Simplified Chinese. Keep enum-like status tokens, repository names, technology names, license identifiers, and machine-readable identifiers unchanged.

Return:

```json
{
  "problem": "",
  "target_users": "",
  "repo_type": "",
  "technical_stack": "",
  "deploy_difficulty": "A|B|C|D",
  "maintenance_state": "active|unclear|stale",
  "license_risk": "low|medium|high|unknown",
  "evidence_notes": []
}
```
