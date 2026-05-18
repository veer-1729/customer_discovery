from customer_discovery.llm.validate import clamp_score
from customer_discovery.research.agents.premium import PremiumLLMOutput


def test_clamp_score():
    assert clamp_score(150) == 100
    assert clamp_score(-5) == 0
    assert clamp_score("72") == 72
    assert clamp_score("nope", default=40) == 40


def test_premium_output_clamps_score():
    out = PremiumLLMOutput.model_validate({"premium_score": 150, "summary": "x"})
    assert out.premium_score == 100
