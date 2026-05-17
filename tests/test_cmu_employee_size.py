import pytest

from customer_discovery.sources.cmu_filters import (
    buckets_for_range,
    CMUFilterConfig,
    parse_numeric_range,
)


def test_parse_numeric_range():
    assert parse_numeric_range("1-30") == (1, 30)


def test_buckets_for_range_1_30():
    buckets = buckets_for_range(1, 30)
    assert buckets == ["1-10", "11-20", "21-30"]


def test_buckets_for_range_single_bucket():
    assert buckets_for_range(5, 8) == ["1-10"]
    assert buckets_for_range(15, 18) == ["11-20"]


def test_buckets_for_range_includes_open_ended():
    assert "500+" in buckets_for_range(400, 600)


def test_apply_to_row_employee_filter():
    cfg = CMUFilterConfig()
    cfg.set_employee_size_range("1-30")
    assert cfg.apply_to_row({"Number of employees:": "11-20"})
    assert not cfg.apply_to_row({"Number of employees:": "51-100"})


def test_url_params_repeat_buckets():
    cfg = CMUFilterConfig()
    cfg.set_employee_size_range("1-30")
    url = cfg.append_to_url(
        "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?jrprS=allRecords"
    )
    assert "filter_Number%20of%20employees%3A=1-10" in url
    assert "filter_Number%20of%20employees%3A=11-20" in url
    assert "filter_Number%20of%20employees%3A=21-30" in url


def test_invalid_range_raises():
    with pytest.raises(ValueError):
        parse_numeric_range("30-1")
