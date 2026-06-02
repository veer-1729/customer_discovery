#!/usr/bin/env bash
# Vendor markdown-only outreach skills from upstream repos (pinned commits).
# Re-run to refresh; update PIN_* vars and skills/ATTRIBUTION.md after verifying changes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_ROOT="${ROOT}/.cursor/skills"

# Pinned commits (main at install time — update when re-vendoring)
PIN_COREY="${PIN_COREY:-7f4af1ea8e78}"
PIN_BRIAN="${PIN_BRIAN:-f36b34fc539a}"
PIN_REZVANI="${PIN_REZVANI:-2aea89df63a7}"

fetch() {
  local url="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  curl -fsSL "$url" -o "$dest"
  echo "  fetched $(basename "$dest")"
}

echo "Vendoring outreach skills into ${SKILLS_ROOT}"

# --- coreyhaines31/marketingskills: cold-email ---
COREY_BASE="https://raw.githubusercontent.com/coreyhaines31/marketingskills/${PIN_COREY}/skills/cold-email"
fetch "${COREY_BASE}/SKILL.md" "${SKILLS_ROOT}/cold-email/SKILL.md"
for ref in benchmarks follow-up-sequences frameworks personalization subject-lines; do
  fetch "${COREY_BASE}/references/${ref}.md" "${SKILLS_ROOT}/cold-email/references/${ref}.md"
done

# --- BrianRWagner/ai-marketing-claude-code-skills: cold-outreach-sequence ---
BRIAN_BASE="https://raw.githubusercontent.com/BrianRWagner/ai-marketing-claude-code-skills/${PIN_BRIAN}/cold-outreach-sequence"
fetch "${BRIAN_BASE}/SKILL.md" "${SKILLS_ROOT}/cold-outreach-sequence/SKILL.md"

# --- alirezarezvani/claude-skills: cold-email (rewrite skill) ---
REZVANI_BASE="https://raw.githubusercontent.com/alirezarezvani/claude-skills/${PIN_REZVANI}/marketing-skill/skills/cold-email"
fetch "${REZVANI_BASE}/SKILL.md" "${SKILLS_ROOT}/cold-email-rewrite/SKILL.md"
for ref in deliverability-guide follow-up-playbook frameworks; do
  fetch "${REZVANI_BASE}/references/${ref}.md" "${SKILLS_ROOT}/cold-email-rewrite/references/${ref}.md"
done

echo "Done. Run safety grep (see .cursor/skills/README.md) before committing."
