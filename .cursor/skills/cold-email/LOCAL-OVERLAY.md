# Customer Discovery Overlay — cold-email

Read this file **after** `SKILL.md` when drafting outreach in the **customer_discovery** repo.

## Context sources (this repo)

- `config/product.yaml` — product name, ICP, tone (`outreach_tone: direct, technical, not salesy`)
- Research briefs: `data/research*/final_briefs.jsonl`, `top_leads.csv`
- Evidence: `data/research*/evidence_bundles.jsonl`
- Existing drafts: `data/outreach*/packs/*.md`, `outreach_packs.jsonl`

Do **not** require upstream `product-marketing.md` or `marketing-context.md`.

## Customer discovery mode

- **Goal:** learn how they handle production incidents, on-call, deploys — not sell.
- **Do not pitch** Emergent Delta or product features unless the user explicitly asks.
- End with **one open discovery question** (low-friction, reply-friendly).
- Use only facts from provided research; never invent customers, funding, or features.

## Format constraints (match pipeline)

- Email body: ~120–180 words
- Subject: short, internal-looking (see upstream subject-line guidance)
- Plain text; no HTML, logos, or multiple links

## Prohibited actions

- No shell commands, scripts, or credential access
- No `web_search` or live prospect research — use supplied briefs only
- Do not send email or automate outreach
