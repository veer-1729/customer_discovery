# Customer Discovery

End-to-end CLI for startup lead research and outreach prep:

1. **Scrape** company lists (YC directory, CMU Airtable) → `data/companies.jsonl`
2. **Research** public evidence, score fit, rank leads → `data/research/`
3. **Outreach** generate email + LinkedIn drafts → `data/outreach/`

**CLI:** `customer-discovery` (alias `customer_discovery`). Do not use `cd` — that is the shell change-directory command.

---

## Quick start (production run)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env: set OPENAI_API_KEY (required for research + outreach)
# Optional: TAVILY_API_KEY if using search fallback in config/research.yaml

customer-discovery scrape --source yc --limit 50 --founders
customer-discovery research --limit 50 --resume
customer-discovery outreach --limit 20 --resume

customer-discovery companies stats
customer-discovery research stats
customer-discovery outreach stats
```

Review outputs: `data/research/top_leads.csv`, `data/outreach/outreach_queue.csv`.

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐     ┌─────────────────┐
│ Part 1      │     │ Part 2: research                     │     │ Part 3: outreach│
│ scrape      │────▶│ evidence → signals → triage (mini)   │────▶│ email + LinkedIn│
│ yc / cmu    │     │ → critic → premium (4o) → CSV rank   │     │ seed contacts   │
└─────────────┘     └──────────────────────────────────────┘     └─────────────────┘
 companies.jsonl         research/*.jsonl + top_leads.csv          outreach_queue.csv
```

| Config | Purpose |
|--------|---------|
| [`config/sources/yc.yaml`](config/sources/yc.yaml) | Default YC batch/region/team filters |
| [`config/sources/cmu_airtable.yaml`](config/sources/cmu_airtable.yaml) | CMU column map, views, employee buckets |
| [`config/product.yaml`](config/product.yaml) | Product name, value props, outreach tone (Emergent Delta) |
| [`config/icp.yaml`](config/icp.yaml) | ICP rubric for LLM prompts |
| [`config/research.yaml`](config/research.yaml) | Models, search provider, stage gates, paths |
| [`config/outreach.yaml`](config/outreach.yaml) | Lead gates, contact rules, outreach models |

---

## Environment variables

| Variable | Required | Used by |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes (research + outreach) | Triage, critic, premium, outreach drafts |
| `TAVILY_API_KEY` | No | Search fallback when enabled in `config/research.yaml` |
| `SERPAPI_API_KEY` / `BRAVE_SEARCH_API_KEY` / etc. | No | Alternative search providers |
| `AIRTABLE_API_KEY` | No | CMU `--api` only (CSV export needs no key) |

Load via `.env` in the project root (gitignored) or export in your shell.

---

## Data layout (gitignored)

| Path | Description |
|------|-------------|
| `data/companies.jsonl` | Normalized company records (Part 1) |
| `data/research/evidence_bundles.jsonl` | Fetched pages + coverage |
| `data/research/final_briefs.jsonl` | Best brief per company |
| `data/research/top_leads.csv` | Ranked leads for outreach gating |
| `data/outreach/outreach_packs.jsonl` | Full outreach packs |
| `data/outreach/outreach_queue.csv` | Human send queue |
| `data/raw/research/{company_id}/` | Cached HTML per fetch |
| `data/raw/outreach/{company_id}/` | LLM output cache |

Only `data/.gitkeep` is tracked; pipeline outputs stay local.

---

## Command reference

| Command | Purpose |
|---------|---------|
| `customer-discovery scrape` | Part 1: fetch companies → JSONL |
| `customer-discovery research` | Part 2: evidence, scoring, LLM funnel, ranking |
| `customer-discovery outreach` | Part 3: outreach drafts from ranked leads |
| `customer-discovery companies stats` | Summarize `companies.jsonl` |
| `customer-discovery companies export -o PATH` | Export companies to CSV |
| `customer-discovery research stats` / `research show ID` | Inspect research outputs |
| `customer-discovery outreach stats` / `outreach show ID` | Inspect outreach packs |
| `customer-discovery sources list` | List sources (`yc`, `cmu`) |
| `customer-discovery schema` | Print `CompanyRecord` JSON schema |

### Common flags (all pipelines)

| Flag | Description |
|------|-------------|
| `--limit` / `-n` | Cap companies processed this run |
| `--resume` | Skip rows already in the stage output file |
| `--dry-run` | Preview without LLM writes (research/outreach) or no scrape write |
| `--company-id` | Process a single company slug |
| `--verbose` / `-v` | Debug logging |

### `scrape` — flags that apply to every source

| Flag | Short | Description |
|------|-------|-------------|
| `--source` | `-s` | **Required.** `yc` or `cmu` |
| `--output` | `-o` | Output path (default: `data/companies.jsonl`) |
| `--limit` | `-n` | Max companies to fetch this run |
| `--resume` | | Skip companies whose `id` is already in the output file |
| `--dry-run` | | Preview filters only; **no file write** |
| `--verbose` | `-v` | Debug logging |
| `--from-url` | | Paste a pre-filtered YC or Airtable URL (see below) |

**Resume + dedup:** Companies are deduplicated by website domain (fallback: normalized name). Re-running with `--resume` skips existing IDs but still merges new sources into the same file. With `--founders`, founder pages are not re-fetched when `team` is already stored (see above).

---

## Source: YC (`--source yc`)

Uses the [YC Startup Directory](https://www.ycombinator.com/companies) Algolia API. No API key required.

### YC-only flags

| Flag | Repeatable | Description |
|------|------------|-------------|
| `--batch` | Yes | Batch name, e.g. `"Winter 2026"`, `"Summer 2025"` |
| `--region` | Yes | HQ region, e.g. `Remote`, `"United States of America"`, `India` |
| `--industry` | Yes | Industry tag, e.g. `B2B`, `Healthcare`, `Fintech` |
| `--status` | Yes | Company status, e.g. `Active`, `Acquired`, `Public`, `Inactive` |
| `--team-size-min` | | Min team size (integer). **Must use with `--team-size-max`** |
| `--team-size-max` | | Max team size (integer) |
| `--founders` | | Scrape each `/companies/{slug}` page for founder names/titles/LinkedIn (slow) |
| `--resume` | | Skip companies already in output; with `--founders`, **skip founder HTTP** when `team` is already populated |

**`--founders` + `--resume`:** Skips `/companies/{slug}` HTTP when that company already has `team` data or `raw.founders_page_fetched: true`. New companies still get founders; existing rows missing founders get **backfilled** on the next run.

**Note:** YC no longer exposes `__NEXT_DATA__`; founder names are parsed from embedded RSC JSON. If an earlier run fetched founder pages but `team` is empty in `companies.jsonl`, run once more with `--founders --resume` to backfill names—then later runs skip those HTTP calls.
| `--from-url` | | Full YC directory URL with query params (overrides default config filters) |

### Default YC filters

If you pass **no** CLI filter flags, filters load from [`config/sources/yc.yaml`](config/sources/yc.yaml) (batches, regions, team size 1–25, etc.).

**Algolia 1,000-hit cap:** `scrape --dry-run` may report ~1,700+ matches (`nbHits`), but Algolia only returns the **first 1,000** per query. With multiple batches in config, the scraper runs **one query per batch** so you get the full set (~1,715). If you previously scraped with an older build and only have 1,000 rows, run `scrape --source yc --resume` again (no `--limit`).

**CLI flags replace** the corresponding lists from the config when provided (e.g. `--batch "Winter 2026"` replaces the entire batch list, it does not add to it).

### YC filter logic

- **Multiple values for the same dimension = OR**  
  `--batch "Winter 2026" --batch "Summer 2025"` → companies in Winter 2026 **or** Summer 2025.
- **Different dimensions = AND**  
  `--batch "Winter 2026" --region Remote` → Winter 2026 **and** Remote.
- **Team size** is a numeric range on reported `team_size` (not buckets).

### YC examples

```bash
# Preview: total matches + sample facet counts (no scrape)
customer-discovery scrape --source yc --dry-run

# Full scrape with default config (~1,690 companies with current preset)
customer-discovery scrape --source yc

# Small test run
customer-discovery scrape --source yc --limit 20

# Override filters from CLI
customer-discovery scrape --source yc \
  --batch "Winter 2026" \
  --batch "Summer 2025" \
  --region Remote \
  --region "United States of America" \
  --industry B2B \
  --industry Healthcare \
  --status Active \
  --team-size-min 1 \
  --team-size-max 25

# Reproduce filters from a browser URL (copy from address bar after filtering on ycombinator.com)
customer-discovery scrape --source yc --from-url \
  "https://www.ycombinator.com/companies?batch=Winter%202025&regions=Remote&team_size=%5B%221%22%2C%2225%22%5D"

# Include founder details (one HTTP request per company — use --limit for testing)
customer-discovery scrape --source yc --founders --limit 50

# Continue a previous run without duplicating companies
customer-discovery scrape --source yc --resume

# Custom output path
customer-discovery scrape --source yc -o data/yc_only.jsonl
```

### YC `--from-url` query parameters

Parsed from the YC companies page URL:

| URL param | Maps to |
|-----------|---------|
| `batch=Winter%202026` (repeatable) | `--batch` |
| `regions=Remote` (repeatable) | `--region` |
| `industry=...` (repeatable) | `--industry` |
| `status=...` (repeatable) | `--status` |
| `team_size=["1","25"]` (JSON in URL) | `--team-size-min` / `--team-size-max` |

### Common YC industry / region values

Use exact strings from the YC sidebar (case-sensitive). Examples:

- **Industries:** `B2B`, `Consumer`, `Fintech`, `Healthcare`, `Education`, `Industrials`, …
- **Regions:** `United States of America`, `Remote`, `India`, `Europe`, `America / Canada`, …
- **Batches:** `Winter 2026`, `Summer 2025`, `Fall 2025`, `Spring 2026`, …

Run `--dry-run` to see facet counts for your current filter set.

### YC output fields

Each line in `companies.jsonl` is a `CompanyRecord` with `source: "yc"`, `program: "YC"`, plus name, website, description, industry tags, batch, `source_url` (YC page), and `raw` (status, team_size, regions, slug, etc.).

---

## Source: CMU (`--source cmu`)

[CMU Startup Directory (Airtable)](https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?jrprS=allRecords)

CMU does **not** auto-scrape the live grid. You either:

1. **CSV export** (recommended) — export from Airtable, then ingest with `--csv`
2. **Airtable API** — set `AIRTABLE_API_KEY` and `table_name` in config, use `--api`

Filters apply when building the export URL (`--dry-run`), when ingesting CSV rows, and when using the API.

### CMU-only flags

| Flag | Repeatable | Description |
|------|------------|-------------|
| `--csv` | | Path to Airtable CSV export |
| `--view` | | Preset tab: `all`, `all_companies`, `hiring`, `pittsburgh` |
| `--filter` | Yes | Field filter — see [CMU filter syntax](#cmu-filter-syntax) |
| `--filter-conjunction` | | `and` (default) or `or` — how multiple `--filter` flags combine |
| `--employees` | | Employee **range** `MIN-MAX` (e.g. `1-30`) → expands to buckets `1-10`, `11-20`, `21-30` |
| `--api` | | Fetch via Airtable REST API (needs env + config) |
| `--from-url` | | Airtable shared-view URL with filter query params |

### CMU preset views (`--view`)

Defined in [`config/sources/cmu_airtable.yaml`](config/sources/cmu_airtable.yaml):

| `--view` | Airtable tab |
|----------|----------------|
| `all` / `all_companies` | All companies |
| `hiring` | Hiring |
| `pittsburgh` | Pittsburgh, PA |

### CMU filter syntax

```text
--filter "FIELD:VALUE"                  # shorthand: contains
--filter "FIELD:operator:VALUE"         # explicit operator
--filter "FIELD WITH COLON:":operator:VALUE   # field names that end with :
```

**Field names must match Airtable column headers exactly**, including trailing colons.

Examples:

```bash
--filter "Verticals:contains:AI/ML"
--filter "Verticals:AI/ML"                              # same (contains is default)
--filter "Company location:":contains:Pittsburgh         # field name includes trailing colon
--filter "Are you currently hiring?:equals:Yes"
--filter "LinkedIn::not_empty:"                          # wrong — use below instead
--filter "LinkedIn:":not_empty:
```

#### Filterable fields (from the CMU base)

| Field name (use exactly) | Example use |
|--------------------------|-------------|
| `Company Name` | `--filter "Company Name:contains:AI"` |
| `Company Description` | `--filter "Company Description:contains:platform"` |
| `Company location:` | `--filter "Company location:":contains:Pittsburgh` |
| `Verticals` | `--filter "Verticals:contains:AI/ML"` |
| `Company website:` | `--filter "Company website:":contains:.io` |
| `LinkedIn:` | `--filter "LinkedIn:":not_empty:` |
| `Name of CMU affiliated founder:` | `--filter "Name of CMU affiliated founder:":contains:Smith` |
| `Company founded in:` | `--filter "Company founded in:":equals:2024` |
| `Are you currently hiring?` | `--filter "Are you currently hiring?:equals:Yes"` |
| `Number of employees:` | Use `--employees 1-30` (range), not a single bucket |
| `Fundraising round:` | `--filter "Fundraising round:":contains:Seed` |
| `CMU Programming:` | `--filter "CMU Programming:":contains:Swartz` |
| `Company has licensed CMU IP.` | `--filter "Company has licensed CMU IP.:equals:Yes"` |

#### Supported operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `contains` | Substring match (default) | `Verticals:contains:AI/ML` |
| `equals` | Exact match (case-insensitive) | `Company founded in::equals:2024` |
| `not_equals` | Not equal | `Verticals:not_equals:Consumer` |
| `not_contains` | Does not contain | `Company Description:not_contains:hardware` |
| `empty` | Field is blank | `LinkedIn::empty:` |
| `not_empty` | Field has a value | `Company website::not_empty:` |
| `greater` | Numeric comparison | `Company founded in::greater:2020` |
| `less` | Numeric comparison | `Company founded in::less:2023` |
| `greater_or_equal` | Numeric | |
| `less_or_equal` | Numeric | |
| `is_any_of` | Value is one of comma-separated options | `Verticals:is_any_of:AI/ML,Healthcare` |
| `has_any_of` | Same idea for multi-select style fields | |

Operators mirror [Airtable shared-view URL filters](https://support.airtable.com/shared-view-url-filters).

#### Combining filters

```bash
# AND (default): AI/ML vertical AND Pittsburgh location
customer-discovery scrape --source cmu --csv export.csv \
  --filter "Verticals:contains:AI/ML" \
  --filter "Company location:":contains:Pittsburgh

# OR: AI/ML OR Healthcare vertical
customer-discovery scrape --source cmu --csv export.csv \
  --filter "Verticals:contains:AI/ML" \
  --filter "Verticals:contains:Healthcare" \
  --filter-conjunction or
```

**Note:** `--filter-conjunction` applies to `--filter` conditions only, not to `--employees` (employee range is always OR across buckets, AND-ed with other filters).

### CMU employee size (`--employees`)

Airtable stores headcount as **buckets**, not a continuous number. Passing a range expands to every overlapping bucket:

| `--employees` | Buckets included |
|---------------|------------------|
| `1-30` | `1-10`, `11-20`, `21-30` |
| `1-10` | `1-10` |
| `11-50` | `11-20`, `21-30`, `31-50` |
| `100-600` | `101-250`, `251-500`, `500+` |

Buckets are configured in `config/sources/cmu_airtable.yaml` under `employee_size.buckets`.

### CMU examples

```bash
# Preview filters → prints filtered Airtable URL + bucket list
customer-discovery scrape --source cmu --dry-run --employees 1-30

customer-discovery scrape --source cmu --dry-run \
  --view hiring \
  --employees 1-30 \
  --filter "Verticals:contains:AI/ML"

# Ingest CSV (export from Airtable first: ⋮ → Download CSV)
customer-discovery scrape --source cmu --csv ~/Downloads/CMU\ Directory.csv

# Filter during ingest (same rules as UI filters)
customer-discovery scrape --source cmu --csv export.csv \
  --view pittsburgh \
  --employees 1-30 \
  --filter "Verticals:contains:AI/ML" \
  --filter "Are you currently hiring?:equals:Yes"

# Use filters encoded in a shared link you copied from the browser
customer-discovery scrape --source cmu --csv export.csv --from-url \
  "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?filterContains_Verticals=AI%2FML&jrprS=allRecords"

# Merge CMU into existing YC list (dedupes by domain)
customer-discovery scrape --source cmu --csv export.csv --resume

# Optional API path
export AIRTABLE_API_KEY=pat...
# Set table_name in config/sources/cmu_airtable.yaml first
customer-discovery scrape --source cmu --api --employees 1-30
```

### CMU `--from-url`

Paste an Airtable shared-view URL. Filter query params are parsed, e.g.:

- `filterContains_Verticals=AI%2FML`
- `filterEquals_Company%20location%3A=Pittsburgh%2C%20PA`
- `filterConjunction=or`
- `jrprS=...` (view id — preserved)

You still need `--csv` or `--api` for actual data unless using `--dry-run`.

### CMU API setup (optional)

1. Create a [personal access token](https://airtable.com/create/tokens) with read access to the base.
2. Add to `.env`: `AIRTABLE_API_KEY=pat...`
3. Set `table_name` in [`config/sources/cmu_airtable.yaml`](config/sources/cmu_airtable.yaml) (table name as shown in Airtable).
4. Run: `customer-discovery scrape --source cmu --api`

---

## Inspecting and exporting results

```bash
# Counts by source, batch, missing websites
customer-discovery companies stats

# Custom input file
customer-discovery companies stats -i data/yc_only.jsonl

# Export to CSV for spreadsheets
customer-discovery companies export -o data/companies.csv

customer-discovery companies export -i data/companies.jsonl -o reports/leads.csv
```

### `companies.jsonl` format

One JSON object per line (`CompanyRecord`):

| Field | Description |
|-------|-------------|
| `id` | Stable id (from domain or slugified name) |
| `name` | Company name |
| `website` | Canonical URL |
| `description` | Short description |
| `industry` | List of tags / verticals |
| `batch` | YC batch (YC only) |
| `program` | `YC`, `CMU`, etc. |
| `source` | `yc` or `cmu` |
| `source_url` | Detail page on origin site |
| `team` | List of founders (YC + `--founders` only) |
| `links` | linkedin, github, etc. |
| `raw` | Source-specific extra fields |
| `scraped_at` | UTC timestamp |

```bash
customer-discovery schema   # full JSON schema
```

---

## Configuration files

| File | Purpose |
|------|---------|
| [`config/sources/yc.yaml`](config/sources/yc.yaml) | Default YC batches, regions, team size, rate limit |
| [`config/sources/cmu_airtable.yaml`](config/sources/cmu_airtable.yaml) | CMU views, column mapping, employee buckets |
| [`config/icp.yaml`](config/icp.yaml) | ICP rubric stub for Part 2 (research) |
| [`.env.example`](.env.example) | `AIRTABLE_API_KEY`, future LLM keys |

Edit YAML defaults instead of passing long CLI flag lists. Restart not required — read on each run.

**CMU default employee range in YAML** (optional):

```yaml
filters:
  employee_size: "1-30"
```

---

## End-to-end workflows

### Workflow A: YC-only lead list

```bash
customer-discovery scrape --source yc --dry-run          # verify count
customer-discovery scrape --source yc                    # full pull
customer-discovery companies stats
customer-discovery companies export -o data/yc_leads.csv
```

### Workflow B: CMU-only with filters

```bash
customer-discovery scrape --source cmu --dry-run \
  --view hiring --employees 1-30 --filter "Verticals:contains:AI/ML"
# Open printed URL → verify in browser → Export CSV

customer-discovery scrape --source cmu --csv data/cmu_export.csv \
  --view hiring --employees 1-30 --filter "Verticals:contains:AI/ML"
```

### Workflow C: Combine YC + CMU

```bash
customer-discovery scrape --source yc
customer-discovery scrape --source cmu --csv data/cmu_export.csv --resume
# Same companies (by domain) are merged, not duplicated
customer-discovery companies stats
```

### Workflow D: Iterative YC sampling

```bash
customer-discovery scrape --source yc --limit 100
# review...
customer-discovery scrape --source yc --resume --limit 200
```

---

## Tests

```bash
pytest                    # 37 tests
pytest -v                 # verbose
pytest tests/test_outreach.py tests/test_url_catalog.py
```

Run before pushing:

```bash
pip install -e ".[dev]"
pytest -q
customer-discovery --help
```

---

## Part 2: Deep research pipeline

After scraping companies into `data/companies.jsonl`, run the multi-stage research funnel:

```
companies.jsonl → evidence → signals → triage (gpt-4o-mini, all)
  → critic + one revision (gated) → premium (gpt-4o, top N) → final_briefs + top_leads.csv
```

### Setup

```bash
cp .env.example .env
# Required for LLM stages:
export OPENAI_API_KEY=sk-...
# Optional for careers/search fallback (provider in config/research.yaml):
export TAVILY_API_KEY=tvly-...
pip install -e ".[dev]"
```

### Research flags

| Flag | Description |
|------|-------------|
| `--input` / `-i` | Companies JSONL (default `data/companies.jsonl`) |
| `--output-dir` | Default `data/research` |
| `--dry-run` | Evidence + signals only; no LLM |
| `--skip-critic` | Triage only |
| `--skip-premium` | Stop after critic/reviewed |
| `--top-n` | Premium cap (default 100) |
| `--no-fallback-search` | Disable all search API calls |
| `--estimate-cost` | Print projected LLM cost |
| `--force-refetch` | Ignore raw HTML cache |

**Search relevance:** Tavily (and other search providers) filter results to the company’s **website domain**, known **ATS** hosts (Greenhouse, Lever, Ashby, etc.), or the company’s **YC page**. Homonym domains (e.g. AquaSec vs AquaShield) and job aggregators (Indeed, LinkedIn, Internshala) are skipped.

### Verify evidence collection (link discovery + fetches)

Probe the first N companies without LLM cost:

```bash
python scripts/probe_evidence.py --limit 3
python scripts/probe_evidence.py --ids kelaicapital-com --with-search   # needs TAVILY_API_KEY
```

Shows homepage anchor counts, `known_links` buckets, each evidence URL/snippet size, coverage, and keyword signals. Flags thin SPA pages that matched only by URL path (e.g. `/careers` returning an empty shell).

### Run research

```bash
customer-discovery research --dry-run --limit 10
customer-discovery research --limit 20 --resume
customer-discovery research --estimate-cost
customer-discovery research --no-fallback-search
customer-discovery research --skip-critic --skip-premium
```

### Outputs (`data/research/`)

| File | Content |
|------|---------|
| `evidence_bundles.jsonl` | Fetched pages + coverage |
| `signals.jsonl` | Keyword signals + deterministic score |
| `triage_briefs.jsonl` | LLM triage for every company |
| `critiques.jsonl` / `reviewed_briefs.jsonl` | Critic + single revision |
| `premium_briefs.jsonl` | Top-N deep briefs |
| `final_briefs.jsonl` | Best stage per company + `important_urls` |
| `top_leads.csv` | Ranked outreach table with URL columns |

Raw HTML cache: `data/raw/research/{company_id}/`.

### Inspect results

```bash
customer-discovery research stats
customer-discovery research show acme-com
```

### Search providers

Configured in `config/research.yaml` (`search.provider`). Supported: `tavily`, `serpapi`, `brave`, `bing`, `google_cse`, `openai`. Careers search runs only after homepage/path probes fail; never scrapes Google HTML directly.

Product copy for prompts: `config/product.yaml` (Emergent Delta). ICP rubric: `config/icp.yaml`.

---

## Part 3: Outreach prep

Turn ranked leads into email + LinkedIn drafts. Contacts are **seed-only** (from `companies.jsonl` team/LinkedIn); fill gaps manually.

### Outreach flags

| Flag | Description |
|------|-------------|
| `--leads` | Default `data/research/top_leads.csv` |
| `--briefs` | Default `data/research/final_briefs.jsonl` |
| `--evidence` | Refresh `important_urls` from `evidence_bundles.jsonl` |
| `--min-score` | Gate minimum `final_score` (default 70) |
| `--top-n` | Max leads to process (default 100) |
| `--include-manual-review` | Include `manual_review_required` rows |
| `--estimate-cost` | Print projected LLM cost |
| `--force-regenerate` | Ignore resume for packs |

```bash
customer-discovery outreach --dry-run
customer-discovery outreach --limit 20 --resume
customer-discovery outreach stats
customer-discovery outreach show COMPANY_ID
```

Outputs in `data/outreach/`:

| File | Purpose |
|------|---------|
| `outreach_packs.jsonl` | Full `OutreachPack` per company |
| `outreach_queue.csv` | Spreadsheet send queue + `all_scraped_urls` |

`important_urls` on every brief/pack includes **all URLs** the evidence agent fetched (every `EvidenceItem` with a URL, plus trace-only attempts).

---

## End-to-end workflow

```bash
# 0. Setup
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # set OPENAI_API_KEY; optional TAVILY_API_KEY

# 1. Scrape companies
customer-discovery scrape --source yc --limit 50 --founders
# or: customer-discovery scrape --source cmu --csv export.csv

# 2. Research (evidence → rank)
customer-discovery research --limit 50 --resume --no-fallback-search   # no search key
# or full: customer-discovery research --limit 50 --resume

# 3. Outreach drafts
customer-discovery outreach --limit 20 --resume

# 4. Review
customer-discovery research show COMPANY_ID
customer-discovery outreach show COMPANY_ID
# Open data/outreach/outreach_queue.csv
```

---

## Production checklist

Before your first full (~1k company) run:

- [ ] `pip install -e ".[dev]"` and `pytest -q` pass
- [ ] `.env` has `OPENAI_API_KEY` (never commit `.env`)
- [ ] Customize [`config/product.yaml`](config/product.yaml) for your product
- [ ] Pilot: `scrape --limit 20` → `research --limit 20` → `outreach --limit 10`
- [ ] `research --estimate-cost` and `outreach --estimate-cost` for budget
- [ ] Use `--resume` on long runs so interruptions are recoverable
- [ ] Human-review `top_leads.csv` and `outreach_queue.csv` before sending mail
- [ ] Respect site terms and rate limits (YC Algolia, target websites, search APIs)

**Cost (rough):** ~1k companies — research triage (mini) ~$5–35; premium top 100 (4o) ~$8–50; outreach top 100 (mini) ~$1–5. Use `--dry-run` and `--limit` to control spend.

**Operational notes:**

- Search fallback disables itself if the configured API key is missing (warning in logs).
- YC `website` comes from Algolia (same as on [yc.com/companies/...](https://www.ycombinator.com/companies)); use `--founders` for named contacts in outreach.
- Outreach contacts are **seed-only**; add names/LinkedIn manually when `review_warnings` contains `no_seed_contact`.

---

## Out of scope (future work)

- Live CMU grid scrape without CSV/API
- Contact enrichment (Apollo, Hunter, etc.)
- Automated email/CRM sending

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: customer-discovery` | `source .venv/bin/activate` and `pip install -e .` |
| Shell runs `cd` instead of our CLI | Use `customer-discovery`, not `cd` |
| `OPENAI_API_KEY is required` | Set in `.env` or `export OPENAI_API_KEY=...` |
| `Missing leads file` / outreach fails | Run `customer-discovery research` first |
| `TAVILY_API_KEY` warning | Set key or use `research --no-fallback-search` |
| CMU requires `--csv` | Export CSV from Airtable or use `--api` |
| YC team size error | Pass **both** `--team-size-min` and `--team-size-max` |
| CMU filter matches nothing | Check exact field names (colons matter); try `--dry-run` |
| `--resume` adds 0 companies | All IDs already in output; normal if list unchanged. If dry-run shows ~1,700+ but file has only 1,000, upgrade and re-run `scrape --source yc --resume` (Algolia 1k cap; fixed by per-batch queries) |
| Research stuck / slow | Use `--limit`; check network; raw cache under `data/raw/research/` |
| `ready_to_send: false` in outreach | Add seed contact (`--founders` on scrape) or send manually after review |
| SSL errors on `pip install` | Use system Python certs or env-specific pip trust flags |

For help on any command:

```bash
customer-discovery scrape --help
customer-discovery companies --help
customer-discovery research --help
customer-discovery outreach --help
```
