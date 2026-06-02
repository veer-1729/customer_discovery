# Outreach copy skills (Cursor Agent)

Project skills for drafting and rewriting **customer-discovery** outreach copy. They do **not** replace the Python outreach pipeline (`customer-discovery outreach`); they improve interactive drafting in Cursor Agent.

## Skills

| Route key | Directory | Source | Use when |
|-----------|-----------|--------|----------|
| `cold-email` | [cold-email/](cold-email/) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | Short discovery email or subject line from a research brief |
| `cold-outreach-sequence` | [cold-outreach-sequence/](cold-outreach-sequence/) | [BrianRWagner/ai-marketing-claude-code-skills](https://github.com/BrianRWagner/ai-marketing-claude-code-skills) | LinkedIn + email multi-touch sequence |
| `cold-email-rewrite` | [cold-email-rewrite/](cold-email-rewrite/) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | Second pass: humanize, tighten, compare drafts |
| *(router)* | [customer-discovery-outreach/](customer-discovery-outreach/) | Local | Auto-pick skill from user intent |

Each vendored skill includes **`LOCAL-OVERLAY.md`** — customer-discovery rules for this repo (no pitch, evidence-only, no web search).

## How to invoke

**Router (recommended):**

```text
Use customer-discovery-outreach to draft an email from this brief: …
```

**Explicit skill:**

```text
Read .cursor/skills/cold-email/SKILL.md and LOCAL-OVERLAY.md.
Draft a short customer discovery email for …
```

**Second pass:**

```text
Rewrite this draft using cold-email-rewrite and LOCAL-OVERLAY. Compare to the original.
```

**Full sequence:**

```text
Use cold-outreach-sequence (standard mode) for email + LinkedIn from …
```

## How to test

1. Open Cursor Agent in this repo.
2. Run the demo prompt in [skills/demo-prompts/founding-engineer-incident-debug.md](../skills/demo-prompts/founding-engineer-incident-debug.md).
3. Confirm the agent reads `SKILL.md` + `LOCAL-OVERLAY.md` before writing.
4. Repeat with `cold-email-rewrite` on the same draft and compare tone/length.
5. Optional: paste context from `data/outreach_yc_pilot/packs/*.md` and compare to pipeline output.

## Re-vendor upstream updates

```bash
./scripts/vendor_outreach_skills.sh
```

Then re-run the safety grep below, restore `LOCAL-OVERLAY.md` if overwritten (script does not touch overlays), and update [skills/ATTRIBUTION.md](../skills/ATTRIBUTION.md) commit SHAs.

Pin specific commits by setting env vars before running:

```bash
PIN_COREY=7f4af1ea8e78 PIN_BRIAN=f36b34fc539a PIN_REZVANI=2aea89df63a7 ./scripts/vendor_outreach_skills.sh
```

## Safety review

Vendored content is **markdown copy guidance only**. Checked at install:

| Check | Result |
|-------|--------|
| Shell commands in skill files | None |
| Python/scripts under `.cursor/skills/` | None (rezvani `scripts/` excluded at vendor time) |
| Credential / env access | None |
| Hidden automation | None |
| External tool calls | Brian upstream mentions `web_search` — **disabled** via `LOCAL-OVERLAY.md` (use research briefs only) |

Re-verify after re-vendor:

```bash
rg -i 'web_search|bash |curl |python |OPENAI|API_KEY|\.env' .cursor/skills --glob '*.md'
```

Expected: matches only in this README, LOCAL-OVERLAY prohibitions, and Brian's upstream SKILL (overridden by overlay).

Attribution: [skills/ATTRIBUTION.md](../skills/ATTRIBUTION.md).
