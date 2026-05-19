from pathlib import Path

from customer_discovery.models.final import FinalBrief
from customer_discovery.research.pipeline.brief_export import export_research_briefs, render_final_brief


def test_render_final_brief() -> None:
    text = render_final_brief(
        FinalBrief(
            company_id="acme-com",
            company_name="Acme",
            final_score=88,
            summary="Does infra tools.",
            likely_pain_points=["on-call load"],
        )
    )
    assert "Acme" in text
    assert "on-call load" in text


def test_export_research_briefs(tmp_path: Path) -> None:
    brief = FinalBrief(
        company_id="acme-com",
        company_name="Acme",
        final_score=90,
        rank=1,
    )
    paths = export_research_briefs(tmp_path, [brief])
    assert paths["readme"].exists()
    drafts = list(paths["briefs_dir"].glob("*.md"))
    assert len(drafts) == 1
