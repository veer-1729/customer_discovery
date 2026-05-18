from __future__ import annotations

from typing import Any


# USD per 1M tokens (approximate; update as pricing changes)
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.0},
}


def _critic_call_count(n_companies: int, cfg: dict[str, Any]) -> int:
    stage = cfg.get("stages", {}).get("critic", {})
    top_n = stage.get("top_n")
    if top_n is not None:
        min_score = int(stage.get("min_score", 60))
        # Upper bound: at most top_n companies with score >= min_score get critic+revision
        return min(int(top_n), n_companies) * 2
    return int(n_companies * 0.3) * 2


def estimate_run_cost(
    n_companies: int,
    cfg: dict[str, Any],
    *,
    skip_critic: bool = False,
    skip_premium: bool = False,
    critic_fraction: float = 0.3,
) -> dict[str, Any]:
    ce = cfg.get("cost_estimates", {})
    models = cfg.get("models", {})
    stages = cfg.get("stages", {})
    premium_top = stages.get("premium", {}).get("top_n", 100)

    triage_in = ce.get("triage_input_tokens", 3500)
    triage_out = ce.get("triage_output_tokens", 800)
    critic_in = ce.get("critic_input_tokens", 4000)
    critic_out = ce.get("critic_output_tokens", 600)
    premium_in = ce.get("premium_input_tokens", 8000)
    premium_out = ce.get("premium_output_tokens", 2000)

    fast = models.get("fast_model", "gpt-4o-mini")
    premium_model = models.get("premium_model", "gpt-4o")

    triage_calls = n_companies
    if skip_critic:
        critic_calls = 0
    elif cfg.get("stages", {}).get("critic", {}).get("top_n") is not None:
        critic_calls = _critic_call_count(n_companies, cfg)
    else:
        critic_calls = int(n_companies * critic_fraction) * 2
    premium_calls = 0 if skip_premium else min(premium_top, n_companies)

    def cost(model: str, calls: int, tin: int, tout: int) -> float:
        p = PRICING.get(model, PRICING["gpt-4o-mini"])
        return calls * (tin * p["input"] + tout * p["output"]) / 1_000_000

    triage_usd = cost(fast, triage_calls, triage_in, triage_out)
    critic_usd = cost(fast, critic_calls, critic_in, critic_out) if critic_calls else 0
    premium_usd = cost(premium_model, premium_calls, premium_in, premium_out) if premium_calls else 0

    return {
        "companies": n_companies,
        "triage_calls": triage_calls,
        "critic_calls": critic_calls,
        "premium_calls": premium_calls,
        "estimated_usd": {
            "triage": round(triage_usd, 2),
            "critic": round(critic_usd, 2),
            "premium": round(premium_usd, 2),
            "total": round(triage_usd + critic_usd + premium_usd, 2),
        },
    }
