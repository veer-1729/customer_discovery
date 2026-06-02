from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from customer_discovery.outreach.config import project_root

_MAX_SKILL_CHARS = 6000


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :].lstrip()
    return text


def _read_skill_file(root: Path, *parts: str) -> str:
    path = root.joinpath(*parts)
    if not path.exists():
        return ""
    body = _strip_frontmatter(path.read_text(encoding="utf-8"))
    if len(body) > _MAX_SKILL_CHARS:
        body = body[:_MAX_SKILL_CHARS] + "\n\n[... truncated for token budget ...]"
    return body.strip()


def load_outreach_copy_system_prompt(cfg: dict[str, Any] | None = None) -> str:
    """Load cold-email skill markdown into the outreach LLM system prompt."""
    if cfg is None:
        from customer_discovery.outreach.config import load_outreach_config

        cfg = load_outreach_config()

    cg = cfg.get("copy_guidelines") or {}
    if not cg.get("enabled", True):
        return ""

    root = project_root()
    skill_dir = cg.get("skill_dir", ".cursor/skills")
    skill_root = Path(skill_dir)
    if not skill_root.is_absolute():
        skill_root = root / skill_root

    chunks: list[str] = []
    for rel in (
        ("cold-email", "SKILL.md"),
        ("cold-email", "LOCAL-OVERLAY.md"),
        ("cold-outreach-sequence", "LOCAL-OVERLAY.md"),
    ):
        content = _read_skill_file(skill_root, *rel)
        if content:
            chunks.append(f"### {rel[0]}/{rel[1]}\n\n{content}")

    if not chunks:
        return ""

    return (
        "\n\n---\n\n## Copy guidelines (from project skills)\n\n"
        + "\n\n".join(chunks)
    )


OUTREACH_SYSTEM_BASE = """You prepare outreach drafts for B2B customer discovery.
Rules:
- Direct, technical, not salesy (see product.outreach_tone).
- Use only facts from the research summary and evidence; do not invent customers or features.
- If contact.name is set, use it in the greeting; otherwise use role-based greeting without inventing a name.
- email_body: about 120-180 words, one clear discovery_question at the end.
- linkedin_connection_note: MUST be at most linkedin_max_chars characters.
- Polish seed_hook if provided; do not contradict it.
- Customer discovery mode: learn about their workflow; do not pitch the product unless product context explicitly asks you to sell.
Output valid JSON only."""


def build_outreach_system_prompt(cfg: dict[str, Any] | None = None) -> str:
    return OUTREACH_SYSTEM_BASE + load_outreach_copy_system_prompt(cfg)
