from pathlib import Path

from customer_discovery.models.outreach import OutreachContact, OutreachPack
from customer_discovery.outreach.pipeline.review_export import export_outreach_review


def test_export_outreach_review(tmp_path: Path) -> None:
    pack = OutreachPack(
        company_id="acme-com",
        company_name="Acme",
        website="https://acme.com",
        rank=1,
        final_score=90,
        email_subject="Hi",
        email_body="Line one\n\nLine two",
        contact=OutreachContact(name="Ada", contact_source="seed_team"),
        ready_to_send=True,
    )
    paths = export_outreach_review(tmp_path, [pack])
    csv_text = paths["review_csv"].read_text(encoding="utf-8-sig")
    assert "Acme" in csv_text
    assert "Line one Line two" in csv_text or "Line one" in csv_text
    assert paths["review_xlsx"].exists()
    drafts = list(paths["drafts_dir"].glob("*.md"))
    assert len(drafts) == 1
    assert "Line one" in drafts[0].read_text(encoding="utf-8")
