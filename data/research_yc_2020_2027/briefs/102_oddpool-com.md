# Oddpool

- **Rank:** None
- **Score:** 85 (high)
- **Stage:** premium
- **Fit:** strong_candidate
- **Manual review:** False
- **Website:** https://www.oddpool.com

## Summary

Oddpool is a B2B service offering prediction market data aggregation across platforms like Kalshi and Polymarket through comprehensive APIs. Its strength lies in streamlining data normalization and integration across disparate exchanges, catering to traders and quantitative teams. The presence of detailed API documentation and real-time data capabilities aligns well with small software engineering teams focused on production-critical environments, making it a strong fit for an AI-driven incident RCA tool like Emergent Delta.

## Positive signals

- Oddpool has substantive API documentation and integration capabilities.
  - evidence: `ev_ef449766d052, ev_29622382a3ed`
- Their service is critical for B2B market operations, aligning with production-critical criteria.
  - evidence: `ev_ef449766d052, ev_34500829050b`
- There is on-call language present, indicative of operational readiness.
  - evidence: `ev_5476355429cf`
- Oddpool does not have a large dedicated SRE team, suitable for Emergent Delta's profile focus.
  - evidence: `ev_34500829050b`
- Focus on API-driven data solutions is ideal for B2B integrations.
  - evidence: `ev_ef449766d052`

## Likely pain points

- Need for improved data normalization across different prediction markets
- Challenges managing disparate APIs from various exchanges
- Potential operational inefficiencies in real-time data aggregation

## Best contact persona

CTO or Head of Engineering

## Hook

Given your current efforts in streamlining prediction market data through APIs, how are you managing incident root-cause analysis amidst API integrations?

## Discovery question

How does your team currently manage real-time incident analysis across your API integrations?

## Evidence IDs used

`ev_ef449766d052`, `ev_34500829050b`, `ev_29622382a3ed`, `ev_5476355429cf`

## URLs

- [docs](https://docs.oddpool.com)
- [fallback_page](https://docs.oddpool.com/llms.txt) *(used)*
  - Fetched from search result for additional context.
- [homepage](https://www.oddpool.com) *(used)*
- [fallback_page](https://www.oddpool.com/changelog)
  - Fetched from search result for additional context.
- [search_result](https://www.oddpool.com/explore/fed-rates)
  - Discovered via web search fallback.
- [careers](https://www.oddpool.com/explore/recession)
  - Contains hiring/on-call/reliability signals.
- [fallback_page](https://www.oddpool.com/fed-market-watch)
  - Fetched from search result for additional context.
- [search_result](https://www.oddpool.com/fed-rate-cut-count)
  - Discovered via web search fallback.
- [fallback_page](https://www.oddpool.com/institutional) *(used)*
  - Fetched from search result for additional context.
- [fallback_page](https://www.oddpool.com/pricing)
  - Fetched from search result for additional context.
- [fallback_page](https://www.oddpool.com/sign-in)
  - Fetched from search result for additional context.
- [fallback_page](https://www.oddpool.com/terms)
  - Fetched from search result for additional context.
- [fallback_page](https://www.oddpool.com/whales)
  - Fetched from search result for additional context.
- [seed_metadata](https://www.ycombinator.com/companies/oddpool) *(used)*
  - Source list metadata (YC/CMU).
