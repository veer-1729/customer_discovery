# Changelog

## [1.0.0] - 2026-05-16

### Added

- **Part 1 — Scrape:** YC directory (Algolia) and CMU Airtable (CSV/API) sources; `CompanyRecord` JSONL output; dedup by domain; `--resume`, filters, `--founders` for YC.
- **Part 2 — Research:** Evidence collection (homepage, careers, docs, status, blog, GitHub, search fallback); signal extraction; deterministic scoring; LLM triage (all companies), critic + revision (gated), premium (top N); `top_leads.csv` and staged JSONL under `data/research/`.
- **Part 3 — Outreach:** Seed-only contact selection; email + LinkedIn drafts; `outreach_packs.jsonl` and `outreach_queue.csv`.
- **Important URLs:** Every scraped/fetched URL from evidence is included on `FinalBrief` and outreach packs.
- CLI: `customer-discovery scrape`, `research`, `outreach`, plus `stats` / `show` subcommands.
- Config: `config/product.yaml`, `config/research.yaml`, `config/outreach.yaml`, `config/icp.yaml`, source YAMLs.
- 37 automated tests.

### Notes

- LLM stages require `OPENAI_API_KEY`.
- Search fallback is optional (`TAVILY_API_KEY` or other provider per config).
- Generated data under `data/` is gitignored by default.
