from __future__ import annotations

import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
import yaml

from customer_discovery.models.company import company_json_schema
from customer_discovery.pipeline.scrape import default_output_path, run_scrape
from customer_discovery.sources import get_source, list_sources
from customer_discovery.sources.yc import (
    algolia_facet_summary,
    load_yc_config,
)
from customer_discovery.sources.yc_filters import YCFilterConfig
from customer_discovery.sources.cmu_filters import CMUFilterConfig, FilterCondition, parse_cli_filter
from customer_discovery.sources.airtable import cmu_dry_run, load_cmu_config

# Register sources
import customer_discovery.sources.yc  # noqa: F401
import customer_discovery.sources.airtable  # noqa: F401

app = typer.Typer(help="Customer discovery: company sourcing and outreach prep")
sources_app = typer.Typer(help="List data sources")
companies_app = typer.Typer(help="Inspect company list output")
app.add_typer(sources_app, name="sources")
app.add_typer(companies_app, name="companies")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _build_yc_filters(
    from_url: Optional[str],
    batches: list[str],
    regions: list[str],
    industries: list[str],
    statuses: list[str],
    team_size: Optional[tuple[int, int]],
    query: Optional[str],
) -> YCFilterConfig:
    if from_url:
        cfg = YCFilterConfig.from_url(from_url)
    else:
        cfg = YCFilterConfig.from_dict(load_yc_config())

    return cfg.merge_overrides(
        batches=batches or None,
        regions=regions or None,
        industries=industries or None,
        statuses=statuses or None,
        team_size=team_size,
        query=query,
    )


@app.command()
def scrape(
    source: str = typer.Option(..., "--source", "-s", help="Source id: yc, cmu"),
    output: Path = typer.Option(default_output_path(), "--output", "-o"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n"),
    resume: bool = typer.Option(False, "--resume", help="Skip companies already in output"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview filters (no write)"),
    founders: bool = typer.Option(False, "--founders", help="Scrape YC founder pages (slow)"),
    from_url: Optional[str] = typer.Option(
        None, "--from-url", help="Paste filtered YC or Airtable shared-view URL"
    ),
    batch: list[str] = typer.Option([], "--batch", help="YC batch filter (repeatable)"),
    region: list[str] = typer.Option([], "--region", help="YC HQ region filter (repeatable)"),
    industry: list[str] = typer.Option([], "--industry", help="YC industry filter (repeatable)"),
    status: list[str] = typer.Option([], "--status", help="YC status filter (repeatable)"),
    team_size_min: Optional[int] = typer.Option(None, "--team-size-min"),
    team_size_max: Optional[int] = typer.Option(None, "--team-size-max"),
    csv_path: Optional[Path] = typer.Option(None, "--csv", help="CSV path for cmu source"),
    view: Optional[str] = typer.Option(
        None, "--view", help="CMU preset view: all, hiring, pittsburgh"
    ),
    filter_spec: list[str] = typer.Option(
        [],
        "--filter",
        help='CMU filter: FIELD:VALUE or FIELD:operator:VALUE (e.g. "Verticals:contains:AI/ML")',
    ),
    filter_conjunction: str = typer.Option(
        "and", "--filter-conjunction", help="CMU filters: and or or"
    ),
    use_api: bool = typer.Option(False, "--api", help="CMU: fetch via Airtable API (needs API key)"),
    employees: Optional[str] = typer.Option(
        None,
        "--employees",
        help='CMU employee-size range, e.g. "1-30" (includes buckets 1-10, 11-20, 21-30)',
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape companies from a source into data/companies.jsonl."""
    _setup_logging(verbose)

    team_size = None
    if team_size_min is not None and team_size_max is not None:
        team_size = (team_size_min, team_size_max)
    elif team_size_min is not None or team_size_max is not None:
        typer.echo("Provide both --team-size-min and --team-size-max", err=True)
        raise typer.Exit(1)

    if source == "yc":
        filter_config = _build_yc_filters(
            from_url, batch, region, industry, status, team_size, None
        )
        if dry_run:
            _yc_dry_run(filter_config)
            return

        yc_cfg = load_yc_config()
        source_options = {
            "filter_config": filter_config,
            "fetch_founders": founders or yc_cfg.get("fetch_founders", False),
            "rate_limit_rps": yc_cfg.get("rate_limit_rps", 1.5),
            "program": yc_cfg.get("program", "YC"),
        }
    elif source == "cmu":
        filter_config = _build_cmu_filters(
            from_url, filter_spec, filter_conjunction, employees
        )
        if dry_run:
            _cmu_dry_run(filter_config, view)
            return
        source_options = {
            "filter_config": filter_config,
            "csv_path": csv_path,
            "use_api": use_api,
            "view": view,
        }
    else:
        source_options = {}

    adapter = get_source(source)
    stats = asyncio.run(
        run_scrape(
            adapter,
            output=output,
            limit=limit,
            resume=resume,
            source_options=source_options,
        )
    )
    typer.echo(
        f"Done. Total in {output}: {stats['total']} "
        f"(added {stats['added_this_run']}, skipped {stats['skipped_resume']})"
    )


def _build_cmu_filters(
    from_url: Optional[str],
    filter_specs: list[str],
    conjunction: str,
    employees: Optional[str],
) -> CMUFilterConfig:
    if from_url and "airtable.com" in from_url:
        cfg = CMUFilterConfig.from_url(from_url)
        base = load_cmu_config()
        es = base.get("employee_size", {})
        cfg.employee_buckets = list(es.get("buckets") or cfg.employee_buckets)
        cfg.employee_size_field = es.get("field") or cfg.employee_size_field
    else:
        cfg = CMUFilterConfig.from_dict(load_cmu_config())

    if employees:
        cfg.set_employee_size_range(employees)

    extra = [parse_cli_filter(s) for s in filter_specs]
    cfg = cfg.merge_conditions(extra)
    if conjunction.lower() in ("and", "or"):
        cfg.conjunction = conjunction.lower()
    return cfg


def _cmu_dry_run(filter_config: CMUFilterConfig, view: Optional[str]) -> None:
    info = cmu_dry_run(filter_config, view)
    typer.echo("CMU filter configuration:")
    typer.echo(f"  view: {info['view']}")
    typer.echo(f"  conditions: {info['conditions']}")
    typer.echo(f"  conjunction: {info['conjunction']}")
    typer.echo(f"  API key set: {info['has_api_key']}")
    if info.get("filter_by_formula"):
        typer.echo(f"  filterByFormula: {info['filter_by_formula']}")
    typer.echo("\nOpen this URL in a browser (filters applied):")
    typer.echo(f"  {info['filtered_url']}")
    typer.echo(
        "\nThen export CSV from that view and run:\n"
        "  customer-discovery scrape --source cmu --csv path/to/export.csv"
    )
    if filter_config.employee_size_range:
        lo, hi = filter_config.employee_size_range
        buckets = filter_config.resolved_employee_buckets()
        typer.echo(f"\nEmployee size {lo}–{hi} → buckets: {', '.join(buckets)}")
    if filter_config.conditions:
        typer.echo("\nFilters (also applied when ingesting CSV):")
        for c in filter_config.conditions:
            typer.echo(f"  - {c.field} {c.operator} {c.value!r}")


def _yc_dry_run(filter_config: YCFilterConfig) -> None:
    from customer_discovery.sources.yc import HEADERS

    typer.echo("YC filter configuration:")
    typer.echo(f"  batches: {len(filter_config.batches)} selected")
    typer.echo(f"  regions: {filter_config.regions}")
    typer.echo(
        f"  team_size: {filter_config.team_size_min}–{filter_config.team_size_max}"
    )
    params = filter_config.build_algolia_params()
    typer.echo(f"  facetFilters: {params.get('facetFilters', 'none')}")
    typer.echo(f"  numericFilters: {params.get('numericFilters', 'none')}")

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        summary = algolia_facet_summary(client, filter_config)

    typer.echo(f"\nTotal companies matching filters: {summary['nbHits']}")
    facets = summary.get("facets", {})
    for facet_name in ("batch", "industries", "regions"):
        facet_vals = facets.get(facet_name, {})
        if facet_vals:
            typer.echo(f"\nTop {facet_name} (sample):")
            for key, count in sorted(facet_vals.items(), key=lambda x: -x[1])[:12]:
                typer.echo(f"  {key}: {count}")


@sources_app.command("list")
def sources_list() -> None:
    """List registered company sources."""
    for sid in list_sources():
        typer.echo(sid)


@companies_app.command("stats")
def companies_stats(
    input: Path = typer.Option(default_output_path(), "--input", "-i"),
) -> None:
    """Summarize companies.jsonl."""
    from customer_discovery.storage.jsonl import read_jsonl

    if not input.exists():
        typer.echo(f"No file at {input}")
        raise typer.Exit(1)

    records = read_jsonl(input)
    by_source: dict[str, int] = {}
    by_batch: dict[str, int] = {}
    missing_website = 0
    for r in records:
        by_source[r.source] = by_source.get(r.source, 0) + 1
        if r.batch:
            by_batch[r.batch] = by_batch.get(r.batch, 0) + 1
        if not r.website:
            missing_website += 1

    typer.echo(f"Total: {len(records)}")
    typer.echo(f"Missing website: {missing_website}")
    typer.echo("By source:")
    for k, v in sorted(by_source.items()):
        typer.echo(f"  {k}: {v}")
    typer.echo("By batch (top 15):")
    for k, v in sorted(by_batch.items(), key=lambda x: -x[1])[:15]:
        typer.echo(f"  {k}: {v}")


@companies_app.command("export")
def companies_export(
    input: Path = typer.Option(default_output_path(), "--input", "-i"),
    output: Path = typer.Option(..., "--output", "-o"),
    format: str = typer.Option("csv", "--format", "-f"),
) -> None:
    """Export companies.jsonl to CSV."""
    from customer_discovery.storage.jsonl import read_jsonl

    records = read_jsonl(input)
    if format != "csv":
        typer.echo("Only csv format supported", err=True)
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "name",
                "website",
                "description",
                "batch",
                "program",
                "source",
                "source_url",
                "industry",
            ],
        )
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "id": r.id,
                    "name": r.name,
                    "website": str(r.website) if r.website else "",
                    "description": r.description or "",
                    "batch": r.batch or "",
                    "program": r.program or "",
                    "source": r.source,
                    "source_url": str(r.source_url) if r.source_url else "",
                    "industry": "; ".join(r.industry),
                }
            )
    typer.echo(f"Exported {len(records)} rows to {output}")


@app.command("schema")
def schema_export(
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Print or write CompanyRecord JSON schema."""
    schema = company_json_schema()
    text = yaml.dump(schema, default_flow_style=False)
    if output:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"Wrote schema to {output}")
    else:
        typer.echo(text)


if __name__ == "__main__":
    app()
