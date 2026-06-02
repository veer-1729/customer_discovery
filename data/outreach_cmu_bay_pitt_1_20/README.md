# Outreach packs (readable)

10 entries from **`outreach_packs.jsonl`** — hooks, email/LinkedIn drafts,
value props, and outreach contact info. (Not the same as `outreach_queue.csv`.)

| Rank | Company | Ready | Read pack |
| ---: | --- | :---: | --- |
| 1 | Leanmcp | yes | [packs/001_leanmcp-com.md](packs/001_leanmcp-com.md) |
| 2 | Rockfish Data | yes | [packs/002_rockfish-ai.md](packs/002_rockfish-ai.md) |
| 3 | Wood Wide AI, Inc. | yes | [packs/003_woodwide-ai.md](packs/003_woodwide-ai.md) |
| 4 | ApertureData | yes | [packs/004_aperturedata-io.md](packs/004_aperturedata-io.md) |
| 5 | Vortex | yes | [packs/005_vortexsoftware-com.md](packs/005_vortexsoftware-com.md) |
| 6 | Civys | yes | [packs/006_civys-vercel-app.md](packs/006_civys-vercel-app.md) |
| 7 | FlowState AI | yes | [packs/007_flowstatehq-com.md](packs/007_flowstatehq-com.md) |
| 8 | Impulse AI | yes | [packs/008_impulselabs-ai.md](packs/008_impulselabs-ai.md) |
| 9 | WuKong AI, Inc | yes | [packs/009_wukongai-io.md](packs/009_wukongai-io.md) |
| 10 | RapidEye | yes | [packs/010_rapideyeinspections-com.md](packs/010_rapideyeinspections-com.md) |

## Files

- **`packs/`** — one markdown file per `outreach_packs.jsonl` row (start here)
- `outreach_packs.xlsx` — same data in Excel
- `outreach_review.csv` — short index only
- `outreach_queue.csv` — flat send queue (subset of columns)
- `outreach_packs.jsonl` — source JSONL

Regenerate: `customer-discovery outreach export --output-dir data/outreach_cmu_bay_pitt_1_20`
