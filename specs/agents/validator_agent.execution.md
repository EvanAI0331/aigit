## Purpose

Define commercial validation behavior.

## Contract

- Validate GitHub heat, demand signal, competition signal, monetization signal, Chinese market gap, packaging difficulty, license risk, and saturation.
- For re-evaluation, compare fresh evidence against prior status and decide whether the opportunity should upgrade, remain watched, hold, or reject.
- Treat completed action evidence as stronger than raw GitHub heat when it shows customer discovery, payment intent, or failed demand.
- Use action fields `evidence_type`, `signal_strength`, `result_note`, `due_at`, and `evidence_required` to decide whether an opportunity is still experimenting, action-validated, or should be downgraded.
- Use external market evidence from public sources only as evidence; do not assume demand from links without content signals.
- Apply the Founder Playbook validation frame:
  - problem hypothesis: what painful workflow or business outcome is being tested;
  - customer discovery: who would be interviewed or observed, and what evidence would prove pain;
  - competitive landscape: existing tools, services, templates, courses, and substitutes;
  - PMF vs hype: separate durable usage or willingness to pay from GitHub/social excitement;
  - MVP exit criteria: what can be shipped or tested within 7 days;
  - launch operating system: whether the opportunity can become agentic workflows instead of relying on founder attention;
  - security/scope debt: whether an AI-generated MVP can stay narrow and safe enough to avoid early technical debt.
- Commercial validation is not local deployment validation.
- PASS requires strong evidence across problem pain, buyer specificity, competitive gap, monetization, packaging, and license acceptability.
- WEAK_PASS requires a concrete validation experiment and must not be stored as a finished opportunity without next evidence.
- If rejecting, choose a precise reject_status.
