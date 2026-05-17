from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlunparse

# Airtable shared-view URL operators (https://support.airtable.com/shared-view-url-filters)
URL_OPERATORS = {
    "equals": "filterEquals_",
    "not_equals": "filterNotEquals_",
    "contains": "filterContains_",
    "not_contains": "filterNotContains_",
    "greater": "filterGreater_",
    "greater_or_equal": "filterGreaterOrEqual_",
    "less": "filterLess_",
    "less_or_equal": "filterLessOrEqual_",
    "is_any_of": "filterIsAnyOf_",
    "is_none_of": "filterIsNoneOf_",
    "has_any_of": "filterHasAnyOf_",
    "has_all_of": "filterHasAllOf_",
    "empty": "filterEmpty_",
    "not_empty": "filterNotEmpty_",
    # generic — Airtable picks sensible default per field type
    "default": "filter_",
}

# Map URL prefix back to operator name
_PREFIX_TO_OP = {v: k for k, v in URL_OPERATORS.items()}

DEFAULT_EMPLOYEE_BUCKETS = [
    "1-10",
    "11-20",
    "21-30",
    "31-50",
    "51-100",
    "101-250",
    "251-500",
    "500+",
]


def parse_numeric_range(spec: str) -> tuple[int, int]:
    """Parse '1-30' or '11-20' into inclusive (min, max)."""
    spec = spec.strip()
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", spec)
    if not m:
        raise ValueError(f"Invalid range {spec!r}. Use format MIN-MAX, e.g. 1-30")
    lo, hi = int(m.group(1)), int(m.group(2))
    if lo > hi:
        raise ValueError(f"Invalid range {spec!r}: min must be <= max")
    return lo, hi


def parse_bucket_bounds(bucket: str) -> tuple[int, int]:
    """Parse bucket label like '1-10' or '500+' into inclusive bounds."""
    bucket = bucket.strip()
    if bucket.endswith("+"):
        lo = int(re.sub(r"[^\d]", "", bucket) or "0")
        return lo, 10**9
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", bucket)
    if not m:
        raise ValueError(f"Cannot parse employee bucket: {bucket!r}")
    return int(m.group(1)), int(m.group(2))


def buckets_for_range(
    range_min: int,
    range_max: int,
    buckets: list[str] | None = None,
) -> list[str]:
    """Return bucket labels that overlap [range_min, range_max]."""
    buckets = buckets or DEFAULT_EMPLOYEE_BUCKETS
    matched: list[str] = []
    for label in buckets:
        bmin, bmax = parse_bucket_bounds(label)
        if bmin <= range_max and bmax >= range_min:
            matched.append(label)
    return matched


@dataclass
class FilterCondition:
    field: str
    operator: str = "contains"
    value: str | None = None

    def to_url_params(self) -> list[tuple[str, str]]:
        op_prefix = URL_OPERATORS.get(self.operator, URL_OPERATORS["default"])
        key = f"{op_prefix}{self.field}"
        if self.operator in ("empty", "not_empty"):
            return [(key, "")]
        if self.value is None:
            return []
        return [(key, self.value)]

    def matches_row(self, row: dict[str, str]) -> bool:
        cell = (row.get(self.field) or "").strip()
        val = (self.value or "").strip()
        op = self.operator

        if op == "empty":
            return not cell
        if op == "not_empty":
            return bool(cell)
        if op in ("equals", "default"):
            return cell.lower() == val.lower()
        if op == "not_equals":
            return cell.lower() != val.lower()
        if op == "contains":
            return val.lower() in cell.lower()
        if op == "not_contains":
            return val.lower() not in cell.lower()
        if op == "greater":
            return _compare_numeric(cell, val) > 0
        if op == "greater_or_equal":
            return _compare_numeric(cell, val) >= 0
        if op == "less":
            return _compare_numeric(cell, val) < 0
        if op == "less_or_equal":
            return _compare_numeric(cell, val) <= 0
        if op in ("is_any_of", "has_any_of"):
            options = [v.strip().lower() for v in re.split(r"[,;|]", val) if v.strip()]
            parts = [p.strip().lower() for p in re.split(r"[,;|]", cell) if p.strip()]
            return any(o in parts or o in cell.lower() for o in options)
        if op in ("is_none_of", "has_all_of"):
            options = [v.strip().lower() for v in re.split(r"[,;|]", val) if v.strip()]
            return not any(o in cell.lower() for o in options)
        return val.lower() in cell.lower()


def _compare_numeric(cell: str, val: str) -> int:
    try:
        return (float(re.sub(r"[^\d.]", "", cell) or 0)) - (
            float(re.sub(r"[^\d.]", "", val) or 0)
        )
    except ValueError:
        return (cell > val) - (cell < val)


@dataclass
class CMUFilterConfig:
    conditions: list[FilterCondition] = field(default_factory=list)
    conjunction: str = "and"  # "and" | "or" — maps to filterConjunction=or
    employee_size_range: tuple[int, int] | None = None
    employee_size_field: str = "Number of employees:"
    employee_buckets: list[str] = field(default_factory=lambda: list(DEFAULT_EMPLOYEE_BUCKETS))

    def resolved_employee_buckets(self) -> list[str]:
        if not self.employee_size_range:
            return []
        lo, hi = self.employee_size_range
        return buckets_for_range(lo, hi, self.employee_buckets)

    def set_employee_size_range(self, spec: str) -> None:
        self.employee_size_range = parse_numeric_range(spec)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CMUFilterConfig:
        f = data.get("filters", data)
        es_cfg = data.get("employee_size", {})
        conditions = []
        for c in f.get("conditions", []):
            conditions.append(
                FilterCondition(
                    field=c["field"],
                    operator=c.get("operator", "contains"),
                    value=c.get("value"),
                )
            )
        buckets = list(es_cfg.get("buckets") or DEFAULT_EMPLOYEE_BUCKETS)
        field = es_cfg.get("field") or "Number of employees:"
        cfg = cls(
            conditions=conditions,
            conjunction=str(f.get("conjunction", "and")).lower(),
            employee_size_field=field,
            employee_buckets=buckets,
        )
        if f.get("employee_size"):
            cfg.set_employee_size_range(str(f["employee_size"]))
        return cfg

    @classmethod
    def from_url(cls, url: str) -> CMUFilterConfig:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        conditions: list[FilterCondition] = []
        conjunction = "or" if qs.get("filterConjunction", [""])[0].lower() == "or" else "and"

        for key, values in qs.items():
            if key == "filterConjunction" or key == "jrprS":
                continue
            op = "default"
            field_name = key
            for prefix, op_name in _PREFIX_TO_OP.items():
                if key.startswith(prefix):
                    op = op_name
                    field_name = key[len(prefix) :]
                    break
            for v in values:
                conditions.append(
                    FilterCondition(
                        field=unquote(field_name),
                        operator=op,
                        value=unquote(v) if v else None,
                    )
                )
        return cls(conditions=conditions, conjunction=conjunction)

    def merge_conditions(self, extra: list[FilterCondition]) -> CMUFilterConfig:
        if not extra:
            return self
        return CMUFilterConfig(
            conditions=list(self.conditions) + extra,
            conjunction=self.conjunction,
            employee_size_range=self.employee_size_range,
            employee_size_field=self.employee_size_field,
            employee_buckets=list(self.employee_buckets),
        )

    def append_to_url(self, base_url: str) -> str:
        """Build Airtable shared-view URL with filter query params."""
        parsed = urlparse(base_url)
        # Drop existing filter params; keep jrprS (view) and other non-filter keys
        qs = parse_qs(parsed.query, keep_blank_values=True)
        clean = {k: v for k, v in qs.items() if not k.startswith("filter")}
        if "filterConjunction" in clean:
            del clean["filterConjunction"]

        pairs: list[tuple[str, str]] = []
        for cond in self.conditions:
            pairs.extend(cond.to_url_params())

        for bucket in self.resolved_employee_buckets():
            pairs.append((f"filter_{self.employee_size_field}", bucket))

        if self.conjunction == "or" and len(self.conditions) > 1:
            pairs.append(("filterConjunction", "or"))

        # Flatten existing qs + new filter pairs
        all_pairs: list[tuple[str, str]] = []
        for k, vals in clean.items():
            for v in vals:
                all_pairs.append((k, v))
        all_pairs.extend(pairs)

        query = urlencode(all_pairs, quote_via=quote)
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment)
        )

    def apply_to_row(self, row: dict[str, str]) -> bool:
        if self.employee_size_range:
            allowed = {b.lower() for b in self.resolved_employee_buckets()}
            cell = (row.get(self.employee_size_field) or "").strip().lower()
            if cell not in allowed:
                return False

        if not self.conditions:
            return True
        results = [c.matches_row(row) for c in self.conditions]
        if self.conjunction == "or":
            return any(results)
        return all(results)

    def build_filter_by_formula(self) -> str | None:
        """Airtable API filterByFormula (when using API key)."""
        if not self.conditions:
            return None
        parts: list[str] = []
        emp_buckets = self.resolved_employee_buckets()
        if emp_buckets:
            fld = "{" + self.employee_size_field + "}"
            bucket_parts = [
                f"LOWER({fld}&'')=LOWER('{_escape_formula(b)}')" for b in emp_buckets
            ]
            parts.append(f"OR({', '.join(bucket_parts)})")

        for c in self.conditions:
            fld = "{" + c.field + "}"
            if c.operator == "empty":
                parts.append(f"LEN(TRIM({fld}&''))=0")
            elif c.operator == "not_empty":
                parts.append(f"LEN(TRIM({fld}&''))>0")
            elif c.operator in ("contains", "default") and c.value:
                parts.append(f"FIND(LOWER('{_escape_formula(c.value)}'), LOWER({fld}&''))")
            elif c.operator == "equals" and c.value:
                parts.append(f"LOWER({fld}&'')=LOWER('{_escape_formula(c.value)}')")
            elif c.operator == "not_equals" and c.value:
                parts.append(f"LOWER({fld}&'')!=LOWER('{_escape_formula(c.value)}')")
            elif c.value:
                parts.append(f"FIND(LOWER('{_escape_formula(c.value)}'), LOWER({fld}&''))")
        if not parts:
            return None
        joiner = ", " if self.conjunction == "and" else ", "
        fn = "AND" if self.conjunction == "and" else "OR"
        return f"{fn}({joiner.join(parts)})"


def _escape_formula(value: str) -> str:
    return value.replace("'", "\\'")


def parse_cli_filter(spec: str) -> FilterCondition:
    """Parse FIELD:OPERATOR:VALUE or FIELD:VALUE (default contains)."""
    parts = spec.split(":", 2)
    if len(parts) == 2:
        return FilterCondition(field=parts[0].strip(), operator="contains", value=parts[1].strip())
    if len(parts) == 3:
        return FilterCondition(
            field=parts[0].strip(),
            operator=parts[1].strip().lower(),
            value=parts[2].strip(),
        )
    raise ValueError(f"Invalid filter spec: {spec!r}. Use FIELD:VALUE or FIELD:operator:VALUE")
