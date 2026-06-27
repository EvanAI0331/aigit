## Purpose

Specify Strategist Agent output.

## Contract

All natural-language string values must be written in Simplified Chinese. Keep enum-like action_type and priority tokens, repository names, technology names, and machine-readable identifiers unchanged.

Return:

```json
{
  "next_actions": [
    {
      "action_type": "mvp_prd",
      "title": "",
      "description": "",
      "priority": "high",
      "evidence_required": "what structured evidence must be recorded: evidence_type, signal_strength, customer_count, payment_signal, or negative_reason"
    }
  ]
}
```
