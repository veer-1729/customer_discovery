#!/usr/bin/env bash
# CMU Stage 3: full research (83× critic + premium) → gated outreach → export packs.
# Requires OPENAI_API_KEY with quota. Run from repo root.
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== Cost estimate ==="
customer-discovery research \
  -i data/companies_cmu_bay_pitt_1_20.jsonl \
  --output-dir data/research_cmu_bay_pitt_1_20 \
  --research-config config/research_cmu_bay_pitt.yaml \
  --estimate-cost

echo "=== Part 2: Research (Plan B search; add --no-fallback-search if credits exhaust) ==="
customer-discovery research \
  -i data/companies_cmu_bay_pitt_1_20.jsonl \
  --output-dir data/research_cmu_bay_pitt_1_20 \
  --research-config config/research_cmu_bay_pitt.yaml \
  --top-n 83 \
  --resume

echo "=== Part 3: Outreach (gated, skill-enhanced) ==="
customer-discovery outreach \
  --outreach-config config/outreach_cmu_bay_pitt.yaml \
  --leads data/research_cmu_bay_pitt_1_20/top_leads.csv \
  --briefs data/research_cmu_bay_pitt_1_20/final_briefs.jsonl \
  --companies data/companies_cmu_bay_pitt_1_20.jsonl \
  --evidence data/research_cmu_bay_pitt_1_20/evidence_bundles.jsonl \
  --output-dir data/outreach_cmu_bay_pitt_1_20 \
  --resume

echo "=== Export readable packs ==="
customer-discovery outreach export --output-dir data/outreach_cmu_bay_pitt_1_20

echo "Done. Review: data/outreach_cmu_bay_pitt_1_20/README.md"
