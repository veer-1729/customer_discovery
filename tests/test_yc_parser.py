import json
from pathlib import Path

from customer_discovery.sources.yc import hit_to_record


def test_hit_to_record():
    fixture = Path(__file__).parent / "fixtures" / "yc" / "algolia_hit.json"
    hit = json.loads(fixture.read_text())
    record = hit_to_record(hit)
    assert record.name == "Example Corp"
    assert record.source == "yc"
    assert record.program == "YC"
    assert record.batch == "Winter 2025"
    assert "B2B" in record.industry
    assert record.website
    assert "example-corp" in str(record.source_url)
    assert record.raw["team_size"] == 12
