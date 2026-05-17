from __future__ import annotations

import re
from urllib.parse import urlparse

from customer_discovery.models.company import CompanyRecord, slugify


def normalize_domain(url: str) -> str | None:
    if not url or not url.strip():
        return None
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        parsed = urlparse(u)
    except Exception:
        return None
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def canonicalize_website(url: str | None) -> str | None:
    if not url:
        return None
    u = str(url).strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    parsed = urlparse(u)
    host = parsed.hostname or ""
    if not host:
        return None
    path = parsed.path.rstrip("/") if parsed.path and parsed.path != "/" else ""
    return f"https://{host.lower()}{path}"


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def normalize_record(record: CompanyRecord) -> CompanyRecord:
    data = record.model_dump()
    if data.get("website"):
        data["website"] = canonicalize_website(str(data["website"]))
    data["id"] = CompanyRecord.make_id(record.name, data.get("website"))
    data["industry"] = sorted({i.strip() for i in data.get("industry", []) if i and i.strip()})
    if data.get("name"):
        data["name"] = record.name.strip()
    return CompanyRecord(**data)
