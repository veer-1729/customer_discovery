#!/usr/bin/env python3
"""Download CMU Startup Directory rows from the public Airtable shared grid view."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_VIEW_URL = (
    "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD"
    "?jrprS=pla7KJF9j2bFqZJ2L"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

FIELD_PATTERNS: list[tuple[str, str]] = [
    ("Company Description", r"Company Description\s*(.+?)(?:Company location:|$)"),
    ("Company location:", r"Company location:\s*([^N]+?)(?:Name of CMU|$)"),
    ("Name of CMU affiliated founder:", r"Name of CMU affiliated founder:\s*([^C]+?)(?:Company founded|$)"),
    ("Company founded in:", r"Company founded in:\s*(\d{4})"),
    ("Verticals", r"Verticals\s*(.+?)(?:Number of employees:|Are you currently hiring|$)"),
    ("Number of employees:", r"Number of employees:\s*([^A-Z\n]+?)(?:Are you currently hiring|Fundraising|$)"),
    ("Are you currently hiring?", r"Are you currently hiring\?\s*([^F]+?)(?:Fundraising|$)"),
    ("Company website:", r"Company website:\s*([^\s]+)"),
    ("LinkedIn:", r"LinkedIn:\s*([^\s]+)"),
]


def parse_card(text: str) -> dict[str, str] | None:
    match = re.match(r"^(.+?)Company Description", text, re.S)
    if not match:
        return None
    row = {"Company Name": match.group(1).strip()}
    for field, pattern in FIELD_PATTERNS:
        m = re.search(pattern, text, re.S)
        if m:
            row[field] = m.group(1).strip()
    return row


def fetch_rows(view_url: str = DEFAULT_VIEW_URL, timeout_ms: int = 120_000) -> list[dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    stale = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        page.goto(view_url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(5000)

        for _ in range(600):
            batch = page.evaluate(
                """() => [...document.querySelectorAll('[data-rowid]')].map(el => ({
                    id: el.getAttribute('data-rowid'),
                    text: el.innerText
                }))"""
            )
            before = len(records)
            for item in batch:
                row = parse_card(item["text"])
                if row:
                    records[item["id"]] = row
            if len(records) == before:
                stale += 1
            else:
                stale = 0

            at_end = page.evaluate(
                """() => {
                  const g = document.querySelector('.ReactVirtualized__Grid');
                  if (!g) return true;
                  g.scrollTop += 350;
                  return g.scrollTop + g.clientHeight >= g.scrollHeight - 2;
                }"""
            )
            page.wait_for_timeout(250)
            if at_end:
                stale += 1
            if stale >= 25:
                break

        browser.close()

    return list(records.values())


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    if not rows:
        raise RuntimeError("No rows to write")
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_VIEW_URL)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "cmu_airtable_export.csv",
    )
    args = parser.parse_args()
    rows = fetch_rows(args.url)
    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
