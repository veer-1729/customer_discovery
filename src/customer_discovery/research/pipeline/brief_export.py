from __future__ import annotations

import csv
import re
from pathlib import Path

from customer_discovery.models.final import FinalBrief
from customer_discovery.models.premium import PremiumBrief
from customer_discovery.models.signals import EvidenceBackedSignal

BRIEF_COLUMNS = [
    "rank",
    "company_id",
    "company_name",
    "website",
    "final_score",
    "confidence",
    "final_stage",
    "fit_label",
    "manual_review_required",
    "summary",
    "draft_file",
]


def _brief_filename(rank: int | None, company_id: str) -> str:
    r = rank if rank is not None else 0
    safe_id = re.sub(r"[^\w.-]", "_", company_id)
    return f"{r:03d}_{safe_id}.md"


def _bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items if x)


def _render_signals(title: str, signals: list[EvidenceBackedSignal]) -> list[str]:
    if not signals:
        return []
    lines = ["", f"## {title}", ""]
    for s in signals:
        claim = (s.claim or "").strip() or "(no claim text)"
        ids = ", ".join(s.evidence_ids) if s.evidence_ids else "none"
        lines.append(f"- {claim}")
        lines.append(f"  - evidence: `{ids}`")
    return lines


def render_final_brief(b: FinalBrief) -> str:
    lines = [
        f"# {b.company_name}",
        "",
        f"- **Rank:** {b.rank}",
        f"- **Score:** {b.final_score} ({b.confidence})",
        f"- **Stage:** {b.final_stage}",
        f"- **Fit:** {b.fit_label}",
        f"- **Manual review:** {b.manual_review_required}",
        f"- **Website:** {b.website or ''}",
        "",
        "## Summary",
        "",
        (b.summary or "").strip(),
    ]
    lines.extend(_render_signals("Positive signals", b.positive_signals))
    lines.extend(_render_signals("Negative signals", b.negative_signals))

    if b.likely_pain_points:
        lines.extend(["", "## Likely pain points", ""])
        lines.extend(f"- {x}" for x in b.likely_pain_points)

    if b.disqualifiers:
        lines.extend(["", "## Disqualifiers", ""])
        lines.extend(f"- {x}" for x in b.disqualifiers)

    if b.best_contact_persona:
        lines.extend(["", "## Best contact persona", "", b.best_contact_persona])
    if b.personalized_hook:
        lines.extend(["", "## Hook", "", b.personalized_hook.strip()])
    if b.suggested_discovery_question:
        lines.extend(["", "## Discovery question", "", b.suggested_discovery_question.strip()])

    if b.evidence_ids_used:
        lines.extend(["", "## Evidence IDs used", "", ", ".join(f"`{e}`" for e in b.evidence_ids_used)])

    if b.important_urls:
        lines.extend(["", "## URLs", ""])
        for u in b.important_urls:
            mark = " *(used)*" if u.used_in_reasoning else ""
            lines.append(f"- [{u.source_type}]({u.url}){mark}")
            if u.why_important:
                lines.append(f"  - {u.why_important}")

    return "\n".join(lines) + "\n"


def render_premium_brief(b: PremiumBrief) -> str:
    lines = [
        f"# {b.company_name} (premium)",
        "",
        f"- **Score:** {b.premium_score} ({b.confidence})",
        f"- **Fit:** {b.fit_label}",
        f"- **Website:** {b.website or ''}",
        "",
        "## Summary",
        "",
        (b.summary or "").strip(),
    ]
    if b.icp_fit_summary:
        lines.extend(["", "## ICP fit", "", b.icp_fit_summary.strip()])
    if b.why_product_might_apply:
        lines.extend(["", "## Why product might apply", "", b.why_product_might_apply.strip()])

    lines.extend(_render_signals("Positive signals", b.positive_signals))
    lines.extend(_render_signals("Negative signals", b.negative_signals))

    if b.likely_pain_points:
        lines.extend(["", "## Likely pain points", ""])
        lines.extend(f"- {x}" for x in b.likely_pain_points)

    if b.disqualifiers:
        lines.extend(["", "## Disqualifiers", ""])
        lines.extend(f"- {x}" for x in b.disqualifiers)

    if b.best_contact_persona:
        lines.extend(["", "## Best contact persona", "", b.best_contact_persona])
    if b.personalized_hook:
        lines.extend(["", "## Hook", "", b.personalized_hook.strip()])
    if b.discovery_question:
        lines.extend(["", "## Discovery question", "", b.discovery_question.strip()])

    if b.review_warnings:
        lines.extend(["", "## Review warnings", ""])
        lines.extend(f"- {x}" for x in b.review_warnings)

    if b.url_notes:
        lines.extend(["", "## URL notes", ""])
        for u in b.url_notes:
            lines.append(f"- [{u.url}]({u.url})")
            if u.why_important:
                lines.append(f"  - {u.why_important}")

    return "\n".join(lines) + "\n"


def _load_ranks(leads_csv: Path | None) -> dict[str, int]:
    if not leads_csv or not leads_csv.exists():
        return {}
    ranks: dict[str, int] = {}
    with leads_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = (row.get("company_id") or "").strip()
            if not cid:
                continue
            try:
                ranks[cid] = int(row.get("rank") or 0)
            except ValueError:
                pass
    return ranks


def _write_index_readme(
    path: Path,
    *,
    title: str,
    rows: list[tuple[int | None, str, str, str, str]],
) -> None:
    """rows: rank, company_name, extra_col, draft_rel_path"""
    lines = [
        f"# {title}",
        "",
        f"{len(rows)} companies. Open a draft file to read the full brief.",
        "",
        "| Rank | Company | | Draft |",
        "| ---: | --- | --- | --- |",
    ]
    for rank, name, extra, draft_rel in rows:
        r = rank if rank is not None else ""
        lines.append(f"| {r} | {name} | {extra} | [{draft_rel}]({draft_rel}) |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_research_briefs(
    output_dir: Path,
    finals: list[FinalBrief],
    premiums: list[PremiumBrief] | None = None,
    *,
    leads_csv: Path | None = None,
    top_n: int | None = None,
) -> dict[str, Path]:
    ranks = _load_ranks(leads_csv)

    def _rank(b: FinalBrief) -> int:
        if b.rank is not None:
            return b.rank
        return ranks.get(b.company_id, 9999)

    sorted_finals = sorted(finals, key=_rank)
    if top_n:
        sorted_finals = sorted_finals[:top_n]

    briefs_dir = output_dir / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    index_rows: list[tuple[int | None, str, str, str]] = []

    for b in sorted_finals:
        rank = _rank(b) if _rank(b) != 9999 else b.rank
        name = _brief_filename(rank, b.company_id)
        rel = f"briefs/{name}"
        (briefs_dir / name).write_text(render_final_brief(b), encoding="utf-8")
        extra = f"score {b.final_score}, {b.fit_label}"
        index_rows.append((rank, b.company_name, extra, rel))

    readme_path = output_dir / "README.md"
    _write_index_readme(readme_path, title="Research briefs", rows=index_rows)

    paths: dict[str, Path] = {"briefs_dir": briefs_dir, "readme": readme_path}

    if premiums:
        premium_dir = output_dir / "briefs_premium"
        premium_dir.mkdir(parents=True, exist_ok=True)
        sorted_prem = sorted(premiums, key=lambda b: ranks.get(b.company_id, 9999))
        if top_n:
            sorted_prem = sorted_prem[:top_n]
        for b in sorted_prem:
            name = _brief_filename(ranks.get(b.company_id), b.company_id)
            (premium_dir / name).write_text(render_premium_brief(b), encoding="utf-8")
        paths["premium_dir"] = premium_dir

    return paths
