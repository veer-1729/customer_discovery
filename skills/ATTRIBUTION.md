# Skill attribution

Vendored markdown-only copies. Full licenses remain with upstream repos.

| Local path | Upstream repo | Upstream path | Pinned ref | License |
|------------|---------------|---------------|------------|---------|
| `.cursor/skills/cold-email/` | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | `skills/cold-email/` | `7f4af1ea8e78` | See upstream LICENSE |
| `.cursor/skills/cold-outreach-sequence/` | [BrianRWagner/ai-marketing-claude-code-skills](https://github.com/BrianRWagner/ai-marketing-claude-code-skills) | `cold-outreach-sequence/` | `f36b34fc539a` | See upstream repo |
| `.cursor/skills/cold-email-rewrite/` | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | `marketing-skill/skills/cold-email/` | `2aea89df63a7` | MIT |

## Not copied (by design)

- coreyhaines: `evals/`, `tools/`, root `*.sh`
- Brian: `SKILL-OC.md` (OpenClaw variant)
- rezvani: `scripts/email_sequence_analyzer.py` and other automation

## Local additions (not upstream)

- `.cursor/skills/*/LOCAL-OVERLAY.md` — customer-discovery constraints
- `.cursor/skills/customer-discovery-outreach/` — router skill
- `.cursor/skills/README.md` — routing and testing
- `skills/demo-prompts/` — demo prompts

Install script: `scripts/vendor_outreach_skills.sh`
