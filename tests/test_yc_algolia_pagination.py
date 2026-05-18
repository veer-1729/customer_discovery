"""YC Algolia retrieval is capped at 1000 hits per query; we split by batch."""

from unittest.mock import MagicMock, patch

from customer_discovery.sources.yc import plan_algolia_queries
from customer_discovery.sources.yc_filters import YCFilterConfig


def test_plan_splits_when_multiple_batches():
    fc = YCFilterConfig(batches=["Winter 2026", "Summer 2025"], regions=["United States of America"])
    client = MagicMock()
    subs = plan_algolia_queries(client, fc)
    assert len(subs) == 2
    assert subs[0].batches == ["Winter 2026"]
    assert subs[1].batches == ["Summer 2025"]
    client.post.assert_not_called()


@patch("customer_discovery.sources.yc.algolia_query")
def test_plan_splits_by_region_when_over_cap(mock_query):
    mock_query.return_value = {
        "nbHits": 1500,
        "hits": [{}] * 1000,
        "nbPages": 1,
    }
    fc = YCFilterConfig(
        batches=["Winter 2026"],
        regions=["United States of America", "India"],
    )
    subs = plan_algolia_queries(MagicMock(), fc)
    assert len(subs) == 2
    assert subs[0].regions == ["United States of America"]
    assert subs[1].regions == ["India"]


@patch("customer_discovery.sources.yc.algolia_query")
def test_plan_single_query_when_under_cap(mock_query):
    mock_query.return_value = {
        "nbHits": 165,
        "hits": [{}] * 165,
        "nbPages": 1,
    }
    fc = YCFilterConfig(batches=["Winter 2026"], regions=["United States of America"])
    subs = plan_algolia_queries(MagicMock(), fc)
    assert subs == [fc]
