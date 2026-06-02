# Customer Discovery Overlay — cold-outreach-sequence

Read this file **after** `SKILL.md` when building sequences in the **customer_discovery** repo.

## Context sources (this repo)

- `config/product.yaml` — ICP and tone
- Research briefs and evidence (paths in `cold-email/LOCAL-OVERLAY.md`)
- Existing outreach packs under `data/outreach*/`

## Replace upstream research steps

The upstream skill suggests `web_search(...)` before writing. **Do not run web search.**

Instead, use only:

- Signals from Part 2 research (careers, docs, on-call, status page, hiring)
- Company description and founder/team from scrape data
- Hooks and pain points from `final_briefs.jsonl` or outreach packs

If research signals are thin, assign **Tier 3** and say so — do not fabricate news or LinkedIn activity.

## Customer discovery mode

- Connection request and emails: **discovery-first**, no product pitch unless asked
- LinkedIn connection note: **≤300 characters** (matches `config/outreach.yaml`)
- First message: soft question about their workflow, not a demo ask
- Follow-ups: new angle from evidence, never "just checking in"

## Prohibited actions

- No shell commands, scripts, or credential access
- No automated sending or CRM integration
- No live web search — evidence from repo files only
