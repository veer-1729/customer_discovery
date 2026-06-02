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


def test_parse_cli_filter_field_with_trailing_colon():
    c = parse_cli_filter("Company location:::contains:Pittsburgh")
    assert c.field == "Company location:"
    assert c.operator == "contains"
    assert c.value == "Pittsburgh"


def test_scrape_preset_bay_pittsburgh():
    from customer_discovery.sources.airtable import load_cmu_config
    from customer_discovery.sources.cmu_filters import load_scrape_preset

    cfg = load_scrape_preset(load_cmu_config(), "bay_pittsburgh_1_30")
    assert cfg is not None
    assert cfg.employee_size_range == (1, 30)
    assert cfg.conjunction == "or"
    row = {
        "Company location:": "Pittsburgh, PA",
        "Number of employees:": "11-20",
    }
    assert cfg.apply_to_row(row)
    row_bay = {
        "Company location:": "Bay Area, CA",
        "Number of employees:": "1-10",
    }
    assert cfg.apply_to_row(row_bay)
    row_nyc = {
        "Company location:": "New York, NY",
        "Number of employees:": "1-10",
    }
    assert not cfg.apply_to_row(row_nyc)


def test_from_url_roundtrip():
    url = (
        "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?"
        "filterContains_Verticals=AI%2FML&jrprS=allRecords"
    )
    cfg = CMUFilterConfig.from_url(url)
    assert len(cfg.conditions) == 1
    assert cfg.conditions[0].field == "Verticals"
