from __future__ import annotations

import csv
import re
from pathlib import Path

from customer_discovery.models.outreach import OutreachPack

EXCEL_COLUMNS = [
    "rank",
    "company_id",
    "company_name",
    "website",
    "final_score",
    "confidence",
    "ready_to_send",
    "contact_persona",
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_linkedin",
    "contact_source",
    "email_subject",
    "email_body",
    "linkedin_connection_note",
    "discovery_question",
    "company_summary",
    "pain_points",
    "value_props_for_them",
    "review_warnings",
    "important_urls",
]

REVIEW_COLUMNS = [
    "rank",
    "company_id",
    "company_name",
    "website",
    "final_score",
    "confidence",
    "ready_to_send",
    "contact_name",
    "contact_title",
    "contact_linkedin",
    "contact_source",
    "email_subject",
    "email_preview",
    "draft_file",
    "review_warnings",
]


def _one_line(text: str | None, max_len: int = 200) -> str:
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text.strip())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def _draft_filename(p: OutreachPack) -> str:
    rank = p.rank if p.rank is not None else 0
    safe_id = re.sub(r"[^\w.-]", "_", p.company_id)
    return f"{rank:03d}_{safe_id}.md"


def _render_draft(p: OutreachPack) -> str:
    lines = [
        f"# {p.company_name}",
        "",
        f"- **Rank:** {p.rank}",
        f"- **Score:** {p.final_score} ({p.confidence})",
        f"- **Ready to send:** {p.ready_to_send}",
        f"- **Website:** {p.website or ''}",
        "",
        "## Contact",
        "",
    ]
    c = p.contact
    if c.name:
        lines.append(f"- **Name:** {c.name}")
    if c.title:
        lines.append(f"- **Title:** {c.title}")
    if c.persona:
        lines.append(f"- **Persona:** {c.persona}")
    if c.email:
        lines.append(f"- **Email:** {c.email}")
    if c.linkedin_url:
        lines.append(f"- **LinkedIn:** {c.linkedin_url}")
    lines.append(f"- **Source:** {c.contact_source}")
    if p.review_warnings:
        lines.extend(["", f"**Warnings:** {', '.join(p.review_warnings)}"])

    lines.extend(["", "## Email", "", f"**Subject:** {p.email_subject or ''}", ""])
    if p.email_body:
        lines.extend(["```", p.email_body.strip(), "```", ""])

    lines.extend(["", "## LinkedIn connection note", ""])
    if p.linkedin_connection_note:
        lines.append(p.linkedin_connection_note.strip())

    if p.discovery_question:
        lines.extend(["", "## Discovery question", "", p.discovery_question.strip()])

    if p.company_summary:
        lines.extend(["", "## Company summary", "", p.company_summary.strip()])

    if p.pain_points:
        lines.extend(["", "## Pain points", ""])
        lines.extend(f"- {x}" for x in p.pain_points)

    if p.value_props_for_them:
        lines.extend(["", "## Value props", ""])
        lines.extend(f"- {x}" for x in p.value_props_for_them)

    if p.important_urls:
        lines.extend(["", "## URLs", ""])
        for u in p.important_urls:
            mark = " *(used)*" if u.used_in_reasoning else ""
            lines.append(f"- [{u.source_type}]({u.url}){mark}")

    return "\n".join(lines) + "\n"


def _bullet_lines(items: list[str]) -> str:
    return "\n".join(f"• {x}" for x in items if x)


def _format_urls(p: OutreachPack) -> str:
    return "\n".join(
        f"[{u.source_type}] {u.url}" + (" *" if u.used_in_reasoning else "")
        for u in p.important_urls
    )


def _pack_excel_row(p: OutreachPack) -> dict[str, str | int | bool]:
    c = p.contact
    return {
        "rank": p.rank or "",
        "company_id": p.company_id,
        "company_name": p.company_name,
        "website": p.website or "",
        "final_score": p.final_score,
        "confidence": p.confidence,
        "ready_to_send": p.ready_to_send,
        "contact_persona": c.persona or "",
        "contact_name": c.name or "",
        "contact_title": c.title or "",
        "contact_email": c.email or "",
        "contact_linkedin": c.linkedin_url or "",
        "contact_source": c.contact_source,
        "email_subject": p.email_subject or "",
        "email_body": (p.email_body or "").strip(),
        "linkedin_connection_note": (p.linkedin_connection_note or "").strip(),
        "discovery_question": (p.discovery_question or "").strip(),
        "company_summary": (p.company_summary or "").strip(),
        "pain_points": _bullet_lines(p.pain_points),
        "value_props_for_them": _bullet_lines(p.value_props_for_them),
        "review_warnings": "; ".join(p.review_warnings),
        "important_urls": _format_urls(p),
    }


def write_outreach_excel(path: Path, packs: list[OutreachPack]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wrap = Alignment(wrap_text=True, vertical="top")
    sorted_packs = sorted(packs, key=lambda p: p.rank or 9999)

    wb = Workbook()
    ws = wb.active
    ws.title = "Outreach"

    ws.append(EXCEL_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    long_cols = {
        "email_body",
        "linkedin_connection_note",
        "company_summary",
        "pain_points",
        "value_props_for_them",
        "important_urls",
    }
    long_col_idxs = {EXCEL_COLUMNS.index(c) + 1 for c in long_cols}

    for p in sorted_packs:
        row_data = _pack_excel_row(p)
        ws.append([row_data[c] for c in EXCEL_COLUMNS])
        row_idx = ws.max_row
        for col_idx in long_col_idxs:
            ws.cell(row=row_idx, column=col_idx).alignment = wrap

    ws.freeze_panes = "A2"
    if sorted_packs:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(EXCEL_COLUMNS))}{len(sorted_packs) + 1}"

    widths = {
        "rank": 6,
        "company_id": 22,
        "company_name": 18,
        "website": 28,
        "final_score": 10,
        "confidence": 12,
        "ready_to_send": 14,
        "contact_persona": 24,
        "contact_name": 18,
        "contact_title": 22,
        "contact_email": 24,
        "contact_linkedin": 36,
        "contact_source": 14,
        "email_subject": 36,
        "email_body": 56,
        "linkedin_connection_note": 40,
        "discovery_question": 40,
        "company_summary": 48,
        "pain_points": 40,
        "value_props_for_them": 40,
        "review_warnings": 24,
        "important_urls": 48,
    }
    for idx, col_name in enumerate(EXCEL_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = widths.get(col_name, 16)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def export_outreach_review(output_dir: Path, packs: list[OutreachPack]) -> dict[str, Path]:
    """Write Excel-friendly summary CSV and per-company markdown drafts."""
    drafts_dir = output_dir / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / "outreach_review.csv"

    sorted_packs = sorted(packs, key=lambda p: p.rank or 9999)
    rows: list[dict[str, str]] = []

    for p in sorted_packs:
        draft_name = _draft_filename(p)
        draft_path = drafts_dir / draft_name
        draft_path.write_text(_render_draft(p), encoding="utf-8")
        rows.append(
            {
                "rank": str(p.rank or ""),
                "company_id": p.company_id,
                "company_name": p.company_name,
                "website": p.website or "",
                "final_score": str(p.final_score),
                "confidence": p.confidence,
                "ready_to_send": str(p.ready_to_send).lower(),
                "contact_name": p.contact.name or "",
                "contact_title": p.contact.title or "",
                "contact_linkedin": p.contact.linkedin_url or "",
                "contact_source": p.contact.contact_source,
                "email_subject": p.email_subject or "",
                "email_preview": _one_line(p.email_body),
                "draft_file": f"drafts/{draft_name}",
                "review_warnings": "; ".join(p.review_warnings),
            }
        )

    with review_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    excel_path = output_dir / "outreach_packs.xlsx"
    write_outreach_excel(excel_path, sorted_packs)

    return {
        "review_csv": review_path,
        "review_xlsx": excel_path,
        "drafts_dir": drafts_dir,
    }
