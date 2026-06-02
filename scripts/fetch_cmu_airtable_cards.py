#!/usr/bin/env python3
"""Export company rows from the public CMU Airtable shared view by opening each record card.

This is intended for shared views where the gallery/grid rows omit fields like
Company website / LinkedIn / employees, but those fields are visible inside the
record detail card.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


DEFAULT_URL = "https://airtable.com/appoCn0JyaYH2Pbab/shrpqgg6AsoRH8JbD?jrprS=allRecords"

# Field labels as displayed in the record card UI.
KNOWN_FIELDS = {
    "Company Name": "Company Name",
    "Company Description": "Company Description",
    "Company location:": "Company location:",
    "Company website:": "Company website:",
    "LinkedIn:": "LinkedIn:",
    "Name of CMU affiliated founder:": "Name of CMU affiliated founder:",
    "Company founded in:": "Company founded in:",
    "Verticals": "Verticals",
    "Number of employees:": "Number of employees:",
    "Are there any open positions on your team?": "Are you currently hiring?",
    "What employment positions are open on your team?": "What employment positions are you hiring for?",
    "Company has licensed CMU IP.": "Company has licensed CMU IP.",
    "Fundraising round:": "Fundraising round:",
    "CMU Programming:": "CMU Programming:",
}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def parse_record_card(text: str) -> dict[str, str]:
    """Parse a record card's innerText into a flat dict keyed by Airtable column label."""
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    out: dict[str, str] = {}

    # First non-empty line is the record title / company name.
    if lines:
        out["Company Name"] = _clean(lines[0])

    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        # Normalize some labels that appear without trailing colon in the UI.
        label = raw
        if label in KNOWN_FIELDS:
            key = KNOWN_FIELDS[label]
            i += 1
            vals: list[str] = []
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt in KNOWN_FIELDS:
                    break
                # Some values are shown as URLs without scheme.
                vals.append(nxt)
                i += 1
            out[key] = "\n".join(v.strip() for v in vals if v.strip())
            continue
        i += 1

    return out


def scrape_view(*, url: str, max_cards: int | None, timeout_ms: int) -> list[dict[str, str]]:
    # record_id -> {scrollTop: int}
    records: dict[str, dict[str, int]] = {}

    def collect_visible(page) -> None:
        batch = page.evaluate(
            """() => {
              const g = document.querySelector('.ReactVirtualized__Grid');
              const scrollTop = g ? g.scrollTop : 0;
              return [...document.querySelectorAll('[data-rowid]')].map(el => ({
                id: el.getAttribute('data-rowid'),
                scrollTop,
              }));
            }"""
        )
        for item in batch:
            rid = item.get("id")
            if not rid:
                continue
            # Keep the first scrollTop where we saw this row id.
            if rid not in records:
                records[rid] = {"scrollTop": int(item.get("scrollTop") or 0)}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(7000)

        # Discover row ids by scrolling the virtualized grid.
        stale = 0
        last_scroll_top: int | None = None
        for _ in range(2400):
            before = len(records)
            collect_visible(page)
            if len(records) == before:
                stale += 1
            else:
                stale = 0
            scroll_top = page.evaluate(
                """() => {
                  const g = document.querySelector('.ReactVirtualized__Grid');
                  if (!g) return null;
                  g.scrollTop += 450;
                  return g.scrollTop;
                }"""
            )
            page.wait_for_timeout(200)
            if scroll_top is None:
                break
            if last_scroll_top is not None and scroll_top == last_scroll_top:
                stale += 1
            last_scroll_top = scroll_top
            if stale >= 25:
                break
            if max_cards is not None and len(records) >= max_cards:
                break

        row_ids = list(records.keys())
        if max_cards is not None:
            row_ids = row_ids[:max_cards]

        # Click each row and parse the record card.
        rows_out: list[dict[str, str]] = []
        for rid in row_ids:
            # The row element can be unmounted by virtualization; jump to its scrollTop first.
            target_top = (records.get(rid) or {}).get("scrollTop", 0)
            page.evaluate(
                """(top) => {
                  const g = document.querySelector('.ReactVirtualized__Grid');
                  if (g) g.scrollTop = top;
                }""",
                target_top,
            )
            page.wait_for_timeout(250)

            # Now the element should be mounted.
            loc = page.locator(f'[data-rowid="{rid}"]')
            if loc.count() == 0:
                # One more nudge (some rows appear slightly after the recorded top)
                page.evaluate(
                    """() => {
                      const g = document.querySelector('.ReactVirtualized__Grid');
                      if (g) g.scrollTop += 250;
                    }"""
                )
                page.wait_for_timeout(250)
                loc = page.locator(f'[data-rowid="{rid}"]')
                if loc.count() == 0:
                    continue
            try:
                loc.first.click(timeout=timeout_ms)
            except Exception:
                # Sometimes another element intercepts; try a DOM click.
                page.evaluate(
                    """(rid) => {
                      const el = document.querySelector(`[data-rowid="${rid}"]`);
                      if (el) el.click();
                    }""",
                    rid,
                )
            page.wait_for_timeout(800)
            dlg_text = page.evaluate(
                """() => { const dlg = document.querySelector('[role=dialog]'); return dlg ? dlg.innerText : null; }"""
            )
            if dlg_text:
                row = parse_record_card(dlg_text)
                row["record_id"] = rid
                rows_out.append(row)
            # Close the card (Escape works for this UI).
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)

        browser.close()
        return rows_out


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
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout-ms", type=int, default=120_000)
    args = ap.parse_args()

    rows = scrape_view(url=args.url, max_cards=args.limit, timeout_ms=args.timeout_ms)
    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()

