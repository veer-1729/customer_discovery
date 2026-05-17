# Customer Discovery Lead Research Automation

Turn broad company lists (YC, CMU, etc.) into a normalized `data/companies.jsonl` for downstream research and outreach (Parts 2–3 planned).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

**CLI name:** `customer-discovery` (alias: `customer_discovery`).  
Not `cd` — that conflicts with the shell “change directory” command.

```bash
customer-discovery --help
customer-discovery scrape --help
```

---

## Command reference

| Command | Purpose |
|---------|---------|
| `customer-discovery scrape` | Fetch companies from a source → `data/companies.jsonl` |
| `customer-discovery companies stats` | Summarize the JSONL file |
| `customer-discovery companies export -o PATH` | Export JSONL to CSV |
| `customer-discovery sources list` | List sources (`yc`, `cmu`) |
| `customer-discovery schema` | Print `CompanyRecord` JSON schema |
| `customer-discovery schema -o path.yaml` | Write schema to a file |

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

**Resume + dedup:** Companies are deduplicated by website domain (fallback: normalized name). Re-running with `--resume` skips existing IDs but still merges new sources into the same file.

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
| `--from-url` | | Full YC directory URL with query params (overrides default config filters) |

### Default YC filters

If you pass **no** CLI filter flags, filters load from [`config/sources/yc.yaml`](config/sources/yc.yaml) (batches, regions, team size 1–25, etc.).

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
pytest
pytest -v tests/test_cmu_filters.py tests/test_cmu_employee_size.py
```

---

## What is not built yet (Parts 2–3)

- Deep company research / ICP scoring (`ResearchBrief`)
- Personalized outreach generation (`OutreachPack`)
- Live CMU grid scrape without CSV/API

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: customer-discovery` | `source .venv/bin/activate` and `pip install -e .` |
| Shell runs `cd` instead of our CLI | Use `customer-discovery`, not `cd` |
| CMU requires `--csv` | Export CSV from Airtable or use `--api` |
| YC team size error | Pass **both** `--team-size-min` and `--team-size-max` |
| CMU filter matches nothing | Check exact field names (colons matter); try `--dry-run` |
| `--resume` adds 0 companies | All IDs already in output; normal if list unchanged |
| SSL errors on `pip install` | Use system Python certs or `pip install --trusted-host` (env-specific) |

For help on any command:

```bash
customer-discovery scrape --help
customer-discovery companies --help
```
