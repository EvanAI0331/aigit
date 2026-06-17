from __future__ import annotations

from aigithub_radar.storage.db import Database


def today_report(db: Database) -> str:
    with db.connect() as conn:
        stats = conn.execute(
            """
            select
              count(*) as total,
              sum(case when status in ('SCREENED','ANALYZED','VALIDATED','APPROVED','STORED','NEXT_ACTION_CREATED') then 1 else 0 end) as screened,
              sum(case when status in ('VALIDATED','APPROVED','STORED','NEXT_ACTION_CREATED') then 1 else 0 end) as validated,
              sum(case when status in ('APPROVED','STORED','NEXT_ACTION_CREATED') then 1 else 0 end) as approved
            from opportunities
            where date(created_at) = date('now')
            """
        ).fetchone()
        best = conn.execute(
            """
            select title, repo_url, commercial_score, status
            from opportunities
            order by commercial_score desc, updated_at desc
            limit 5
            """
        ).fetchall()

    lines = [
        "今日开源商业机会报告",
        f"发现项目: {stats['total'] or 0}",
        f"初筛通过: {stats['screened'] or 0}",
        f"验证通过: {stats['validated'] or 0}",
        f"重点机会: {stats['approved'] or 0}",
        "高分机会:",
    ]
    for row in best:
        lines.append(f"- {row['title']} | {row['commercial_score']} | {row['status']} | {row['repo_url']}")
    return "\n".join(lines)

