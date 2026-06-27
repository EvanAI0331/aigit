## Purpose

Extract dynamic opportunity themes from multi-platform market monitoring evidence.

## Contract

- Treat scripts as evidence collectors only.
- Select themes by triangulating multiple weak signals, not by copying trending titles.
- Give weight to GitHub platform heat when recent repositories show strong stars, recent updates, or repeated categories.
- Give weight to Chinese market evidence from 小红书、抖音、头条、视频号、微信公众号、闲鱼、B站、V2EX when the evidence includes buyer language, workaround sharing, repeated demand, tutorials, selling behavior, or concrete tool-seeking.
- Mark unavailable domestic platforms explicitly as missing evidence; do not infer demand from a failed collector.
- Convert noisy market text into productizable discovery themes such as workflows, buyer pains, integration gaps, automation needs, monitoring needs, compliance needs, data pipelines, vertical tools, or developer operations.
- Favor themes that are likely to have open-source repositories on GitHub and a commercial packaging gap.
- Penalize themes that are only celebrity/news/entertainment/trading chatter unless they reveal a repeated tool need.
- Keep candidate themes short enough for GitHub search expansion.
- Include rejected topics when they are hot but unsuitable.
- Demand score should reflect buyer pain or workflow need.
- Heat score should reflect cross-platform attention, recency, and discussion volume.
- Confidence should reflect source diversity and evidence quality.

## External Skill References

- `skills/external/agency-agents/product-trend-researcher.md`
