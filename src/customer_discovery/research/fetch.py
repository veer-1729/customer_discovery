from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from customer_discovery.pipeline.normalize import canonicalize_website, normalize_domain


@dataclass
class FetchResult:
    url: str
    success: bool
    status_code: int | None = None
    title: str | None = None
    text: str = ""
    html: str = ""
    error: str | None = None


def extract_text(html: str, max_chars: int = 12_000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:200]
    return None


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Return (href, link_text) absolute URLs."""
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if abs_url in seen:
            continue
        seen.add(abs_url)
        text = a.get_text(strip=True)[:120]
        out.append((abs_url, text))
    return out


class PageFetcher:
    def __init__(
        self,
        *,
        timeout: float = 15.0,
        user_agent: str = "CustomerDiscoveryBot/0.1",
    ) -> None:
        self._timeout = timeout
        self._headers = {"User-Agent": user_agent}

    def fetch(self, url: str) -> FetchResult:
        url = canonicalize_website(url) or url
        try:
            with httpx.Client(
                headers=self._headers,
                follow_redirects=True,
                timeout=self._timeout,
            ) as client:
                resp = client.get(url)
                html = resp.text
                if resp.status_code >= 400:
                    return FetchResult(
                        url=str(resp.url),
                        success=False,
                        status_code=resp.status_code,
                        error=f"HTTP {resp.status_code}",
                    )
                return FetchResult(
                    url=str(resp.url),
                    success=True,
                    status_code=resp.status_code,
                    title=extract_title(html),
                    text=extract_text(html),
                    html=html,
                )
        except Exception as e:
            return FetchResult(url=url, success=False, error=str(e))


def build_url(base: str, path: str) -> str:
    base = canonicalize_website(base) or base
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def status_subdomain_url(website: str) -> str | None:
    domain = normalize_domain(website)
    if not domain:
        return None
    return f"https://status.{domain}"
