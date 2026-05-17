from customer_discovery.sources.cmu_filters import CMUFilterConfig, FilterCondition, parse_cli_filter


def test_append_to_url_contains_filter():
    cfg = CMUFilterConfig(
        conditions=[
            FilterCondition(field="Verticals", operator="contains", value="AI/ML"),
        ]
    )
    base = "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?jrprS=allRecords"
    url = cfg.append_to_url(base)
    assert "filterContains_Verticals=AI%2FML" in url
    assert "jrprS=allRecords" in url


def test_apply_to_row_and_conjunction():
    cfg = CMUFilterConfig(
        conditions=[
            FilterCondition(field="Verticals", operator="contains", value="AI"),
            FilterCondition(field="Company location:", operator="contains", value="Pittsburgh"),
        ],
        conjunction="and",
    )
    row = {"Verticals": "AI/ML", "Company location:": "Pittsburgh, PA"}
    assert cfg.apply_to_row(row)
    row_fail = {"Verticals": "Healthcare", "Company location:": "Pittsburgh, PA"}
    assert not cfg.apply_to_row(row_fail)


def test_parse_cli_filter():
    c = parse_cli_filter("Verticals:contains:AI/ML")
    assert c.field == "Verticals"
    assert c.operator == "contains"
    assert c.value == "AI/ML"


def test_from_url_roundtrip():
    url = (
        "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?"
        "filterContains_Verticals=AI%2FML&jrprS=allRecords"
    )
    cfg = CMUFilterConfig.from_url(url)
    assert len(cfg.conditions) == 1
    assert cfg.conditions[0].field == "Verticals"
