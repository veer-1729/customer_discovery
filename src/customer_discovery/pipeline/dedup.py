from __future__ import annotations

from customer_discovery.models.company import CompanyRecord
from customer_discovery.pipeline.normalize import normalize_name, normalize_record


def _dedup_key(record: CompanyRecord) -> str:
    r = normalize_record(record)
    if r.website:
        from customer_discovery.pipeline.normalize import normalize_domain

        domain = normalize_domain(str(r.website))
        if domain:
            return f"domain:{domain}"
    return f"name:{normalize_name(r.name)}"


def merge_records(existing: CompanyRecord, incoming: CompanyRecord) -> CompanyRecord:
    """Merge two records for the same dedup key; prefer non-null, union lists."""
    base = normalize_record(existing)
    new = normalize_record(incoming)

    def pick(a, b):
        return a if a is not None else b

    industries = sorted(set(base.industry) | set(new.industry))
    team_by_name = {t.name.lower(): t for t in base.team}
    for t in new.team:
        key = t.name.lower()
        if key not in team_by_name:
            team_by_name[key] = t

    raw = dict(base.raw)
    raw.setdefault("_provenance", [])
    if isinstance(raw["_provenance"], list):
        raw["_provenance"].append(
            {"source": new.source, "source_url": str(new.source_url) if new.source_url else None}
        )

    merged = CompanyRecord(
        id=base.id,
        name=base.name,
        website=pick(base.website, new.website),
        description=pick(base.description, new.description) or pick(new.description, base.description),
        industry=industries,
        batch=pick(base.batch, new.batch),
        program=pick(base.program, new.program),
        source=base.source,
        source_url=pick(base.source_url, new.source_url),
        team=list(team_by_name.values()),
        links=base.links if base.links.model_dump(exclude_none=True) else new.links,
        raw={**new.raw, **raw},
        scraped_at=min(base.scraped_at, new.scraped_at),
    )
    return normalize_record(merged)


class DedupIndex:
    def __init__(self, existing: list[CompanyRecord] | None = None) -> None:
        self._by_key: dict[str, CompanyRecord] = {}
        if existing:
            for rec in existing:
                self.add(rec)

    def add(self, record: CompanyRecord) -> CompanyRecord:
        key = _dedup_key(record)
        if key in self._by_key:
            self._by_key[key] = merge_records(self._by_key[key], record)
        else:
            self._by_key[key] = normalize_record(record)
        return self._by_key[key]

    def values(self) -> list[CompanyRecord]:
        return list(self._by_key.values())

    def __len__(self) -> int:
        return len(self._by_key)
