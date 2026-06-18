## Purpose

Validate business viability using evidence.

## Contract

- Score validation_score from 0 to 100.
- Use a Founder Playbook validation lens:
  - start from a falsifiable problem hypothesis, not a product idea;
  - require a customer discovery path before calling demand real;
  - map competitors and substitutes before calling a market empty;
  - distinguish product-market-fit evidence from early hype;
  - prefer narrow MVPs with clear 7-day exit criteria;
  - reward opportunities that can turn founder attention into agentic workflows;
  - penalize broad AI-generated MVPs with security, scope, or maintenance debt.
- Missing external demand evidence should cap score unless GitHub and buyer pain are unusually strong.
- During re-evaluation, explicitly consider:
  - whether GitHub evidence improved or decayed;
  - whether external market mentions show real buyer language, competitor saturation, or only hype;
  - whether open/done/closed next actions add proof or invalidate the opportunity.
- Completed customer discovery or payment-test actions can raise confidence; closed actions with negative result notes should reduce confidence.
- Positive action signal_strength above 50 can justify ACTION_VALIDATED when problem and monetization evidence are coherent.
- Stale open actions should reduce urgency and may keep the opportunity in EXPERIMENTING instead of APPROVED.
- Negative signal_strength below -30 should push toward HOLD or REJECT unless other evidence is strong.
- External market sources may include Hacker News, Reddit, Product Hunt query pages, YouTube query pages, Google Trends query pages, and X query pages. Interpret them conservatively.
- Missing customer discovery plan should cap validation_score at 70.
- Hype-only evidence should cap validation_score at 60.
- No clear buyer should cap validation_score at 55.
- License risk can force REJECTED_LICENSE_RISK.
- Saturated generic ideas should become REJECTED_ALREADY_SATURATED.
- reject_status is required when verdict is REJECT. For PASS, WEAK_PASS, or HOLD, leave it empty.
- No deployment test is required.

## Scoring Rubric

- problem_hypothesis: 0-15
- customer_discovery_plan: 0-15
- competitive_landscape_gap: 0-15
- monetization_signal: 0-15
- pmf_vs_hype_check: 0-15
- seven_day_mvp_test: 0-10
- agentic_ops_fit: 0-10
- license_and_scope_safety: 0-5

Set founder_playbook_score to the sum. validation_score may differ only when GitHub/license evidence strongly changes risk.

## External Skill References

- `skills/external/agency-agents/testing-reality-checker.md`
- `skills/external/agency-agents/testing-evidence-collector.md`
- `skills/external/agency-agents/sales-discovery-coach.md`
- `skills/external/agency-agents/sales-pipeline-analyst.md`
- `skills/external/agency-agents/finance-investment-researcher.md`
