---
name: customer-discovery-outreach
description: >-
  Route outreach copy tasks to the right cold-email skill in this repo.
  Use when drafting or rewriting customer-discovery emails or LinkedIn messages
  for B2B SaaS leads from research briefs. Reads LOCAL-OVERLAY.md for
  discovery-first rules. Routes to cold-email, cold-outreach-sequence, or
  cold-email-rewrite.
---

# Customer Discovery Outreach Router

When the user asks for outreach copy in this repo, pick a skill and **read its `SKILL.md` plus `LOCAL-OVERLAY.md`** before writing.

## Routing

| User intent | Skill directory | Route key |
|-------------|-----------------|-----------|
| One short discovery email, subject line, first touch from a brief | `.cursor/skills/cold-email/` | `cold-email` |
| Email + LinkedIn connection note + multi-touch follow-ups | `.cursor/skills/cold-outreach-sequence/` | `cold-outreach-sequence` |
| Rewrite, humanize, second pass, A/B compare, line-by-line critique | `.cursor/skills/cold-email-rewrite/` | `cold-email-rewrite` |

## Decision flow

1. **Single email or subject only** → `cold-email` (coreyhaines31/marketingskills)
2. **LinkedIn + email sequence** → `cold-outreach-sequence` (BrianRWagner)
3. **Already have a draft; needs polish or comparison** → `cold-email-rewrite` (alirezarezvani)

If unclear, default to `cold-email` for a first draft, then offer `cold-email-rewrite` for a second pass.

## Required context

Load from the repo when available:

- `config/product.yaml`
- Relevant row from `top_leads.csv` or `final_briefs.jsonl`
- Optional: `data/outreach*/packs/{company_id}.md` for examples

## Non-negotiables (all routes)

See each skill's `LOCAL-OVERLAY.md`:

- Discovery-first; no product pitch unless user asks
- Evidence-only personalization
- No shell commands, credentials, web search, or sending automation

## Invocation examples

```
Use customer-discovery-outreach to draft an email from this brief: …
```

```
Read cold-email skill + LOCAL-OVERLAY. Draft a discovery email for …
```

```
Use cold-outreach-sequence (standard mode) for LinkedIn + email from …
```

```
Rewrite this draft using cold-email-rewrite; compare to the original.
```
