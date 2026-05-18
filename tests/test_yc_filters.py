import json

from customer_discovery.sources.yc_filters import YCFilterConfig, yc_batches_for_year_range


def test_from_url_parses_batches_and_regions():
    url = (
        "https://www.ycombinator.com/companies?"
        "batch=Winter%202025&batch=Summer%202024&"
        "regions=Remote&regions=India&"
        "team_size=%5B%221%22%2C%2225%22%5D"
    )
    cfg = YCFilterConfig.from_url(url)
    assert "Winter 2025" in cfg.batches
    assert "Summer 2024" in cfg.batches
    assert "Remote" in cfg.regions
    assert cfg.team_size_min == 1
    assert cfg.team_size_max == 25


def test_build_algolia_facet_filters_or_within_group():
    cfg = YCFilterConfig(
        batches=["Winter 2026", "Summer 2025"],
        regions=["Remote"],
        team_size_min=1,
        team_size_max=25,
    )
    params = cfg.build_algolia_params()
    facet = json.loads(params["facetFilters"])
    assert ["batch:Winter 2026", "batch:Summer 2025"] in facet
    assert ["regions:Remote"] in facet
    numeric = json.loads(params["numericFilters"])
    assert "team_size>=1" in numeric
    assert "team_size<=25" in numeric


def test_yc_batches_for_year_range():
    batches = yc_batches_for_year_range(2020, 2027)
    assert batches[0] == "Winter 2027"
    assert "Winter 2020" in batches
    assert "Summer 2020" in batches
    assert "Spring 2025" in batches
    assert "Fall 2025" in batches
    assert "Spring 2024" not in batches
    assert len(batches) == 22


def test_merge_overrides_replaces_batches():
    cfg = YCFilterConfig(batches=["Winter 2020"])
    merged = cfg.merge_overrides(batches=["Winter 2026"])
    assert merged.batches == ["Winter 2026"]
