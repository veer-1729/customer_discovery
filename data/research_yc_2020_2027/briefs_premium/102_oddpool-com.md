# Oddpool (premium)

- **Score:** 85 (high)
- **Fit:** strong_candidate
- **Website:** https://www.oddpool.com

## Summary

Oddpool is a B2B service offering prediction market data aggregation across platforms like Kalshi and Polymarket through comprehensive APIs. Its strength lies in streamlining data normalization and integration across disparate exchanges, catering to traders and quantitative teams. The presence of detailed API documentation and real-time data capabilities aligns well with small software engineering teams focused on production-critical environments, making it a strong fit for an AI-driven incident RCA tool like Emergent Delta.

## ICP fit

Oddpool offers prediction market data aggregation through APIs, which is ideal for small engineering teams needing AI-assisted incident RCA solutions. They demonstrate necessary public API maturity, production integration challenges, and an absence of a large SRE team which aligns with Emergent Delta's target customer base.

## Why product might apply

The company's focus on real-time data aggregation and API-driven services fits Emergent Delta's ideal ICP profile for production-critical and API-reliant businesses with an engineering team likely in the size range of 5 to 50 personnel, lacking a dedicated large-scale SRE operation.

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

## URL notes

- [https://www.oddpool.com](https://www.oddpool.com)
- [https://docs.oddpool.com](https://docs.oddpool.com)
