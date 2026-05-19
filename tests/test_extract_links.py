from __future__ import annotations

from customer_discovery.research.fetch import extract_links, fetch_dedup_key


def test_extract_links_includes_hash_fragments():
    html = """
    <html><body>
      <nav>
        <a href="#services">Services</a>
        <a href="/#pricing">Pricing</a>
        <a href="/team">Team</a>
      </nav>
    </body></html>
    """
    links = extract_links(html, "https://acme.com/")
    urls = {u for u, _ in links}
    assert "https://acme.com#services" in urls or "https://acme.com/#services" in urls
    assert any("pricing" in u for u in urls)
    assert "https://acme.com/team" in urls


def test_fetch_dedup_key_ignores_fragment():
    assert fetch_dedup_key("https://acme.com/") == fetch_dedup_key("https://acme.com/#services")
