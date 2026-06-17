from __future__ import annotations


def fact_score(repo: dict) -> int:
    score = 0
    score += min(int(repo.get("stars") or 0) // 100, 25)
    score += min(int(repo.get("forks") or 0) // 25, 10)
    if repo.get("license"):
        score += 15
    if repo.get("readme"):
        score += 15
    if repo.get("pushed_at"):
        score += 15
    if repo.get("topics"):
        score += 10
    if repo.get("language"):
        score += 10
    return min(score, 100)


def opportunity_score(facts: int, judgment: int, validation: int, founder_playbook: int | None = None) -> int:
    validation_component = validation
    if founder_playbook is not None:
        validation_component = round(validation * 0.5 + founder_playbook * 0.5)
    return round(facts * 0.3 + judgment * 0.4 + validation_component * 0.3)
