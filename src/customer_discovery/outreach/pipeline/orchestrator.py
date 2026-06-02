from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.outreach import OutreachPack
from customer_discovery.outreach.agents.outreach_agent import run_outreach_agent
from customer_discovery.outreach.config import load_outreach_config
from customer_discovery.outreach.contact_selector import select_contact
from customer_discovery.outreach.pipeline.gate import gate_stats, load_gated_leads
from customer_discovery.outreach.pipeline.queue_export import write_outreach_queue
from customer_discovery.research.config import load_product_config
from customer_discovery.research.pipeline.url_catalog import build_important_urls
from customer_discovery.storage.staged_jsonl import (
    index_by_company,
    load_ids_staged,
    read_staged,
    write_staged,
)

logger = logging.getLogger(__name__)


@dataclass
class OutreachOptions:
    leads_path: Path
    briefs_path: Path
    companies_path: Path
    evidence_path: Path
    output_dir: Path
    cache_dir: Path
    min_score: int | None = None
    top_n: int | None = None
    limit: int | None = None
    company_id: str | None = None
    resume: bool = False
    dry_run: bool = False
    estimate_cost: bool = False
    include_manual_review: bool = False
    force_regenerate: bool = False
    config_path: Path | None = None


def estimate_outreach_cost(n: int, cfg: dict[str, Any]) -> dict[str, Any]:
    ce = cfg.get("cost_estimates", {})
    tin = ce.get("input_tokens", 2500)
    tout = ce.get("output_tokens", 1200)
    model = cfg.get("models", {}).get("default", "gpt-4o-mini")
    usd = n * (tin * 0.15 + tout * 0.60) / 1_000_000
    return {"companies": n, "model": model, "estimated_usd": round(usd, 2)}


class OutreachOrchestrator:
    def __init__(self, opts: OutreachOptions) -> None:
        self.opts = opts
        self.cfg = load_outreach_config(opts.config_path)
        self.product = load_product_config()
        self.packs_path = opts.output_dir / "outreach_packs.jsonl"
        self.queue_path = opts.output_dir / "outreach_queue.csv"
        self._llm = None

    def run(self) -> dict[str, Any]:
        leads = load_gated_leads(
            leads_path=self.opts.leads_path,
            briefs_path=self.opts.briefs_path,
            companies_path=self.opts.companies_path,
            cfg=self.cfg,
            min_score=self.opts.min_score,
            top_n=self.opts.top_n,
            include_manual_review=self.opts.include_manual_review,
            company_id=self.opts.company_id,
            limit=self.opts.limit,
        )
        stats = gate_stats(leads)

        if self.opts.estimate_cost:
            est = estimate_outreach_cost(len(leads), self.cfg)
            print(est)

        if self.opts.dry_run:
            print(stats)
            return stats

        bundles = (
            index_by_company(self.opts.evidence_path, EvidenceBundle)
            if self.opts.evidence_path.exists()
            else {}
        )
        pack_index: dict[str, OutreachPack] = index_by_company(self.packs_path, OutreachPack)
        if not self.opts.resume and not self.opts.force_regenerate:
            pack_index = {}
        linkedin_max = int(self.cfg.get("linkedin_max_chars", 300))
        premium_top = int(self.cfg.get("models", {}).get("premium_top_n", 0))

        for i, lead in enumerate(leads):
            if lead.company_id in pack_index and not self.opts.force_regenerate:
                continue
            brief = lead.brief
            bundle = bundles.get(lead.company_id)
            if bundle:
                brief = brief.model_copy(
                    update={
                        "important_urls": build_important_urls(
                            bundle, brief.evidence_ids_used
                        )
                    }
                )
            persona = brief.best_contact_persona
            contact = select_contact(lead.company, persona, self.cfg)
            model = self.cfg.get("models", {}).get("default", "gpt-4o-mini")
            if premium_top > 0 and i < premium_top:
                model = self.cfg.get("models", {}).get("premium_model", model)

            pack = run_outreach_agent(
                company=lead.company,
                brief=brief,
                bundle=bundle,
                contact=contact,
                llm=self._get_llm(),
                model=model,
                product=self.product,
                linkedin_max_chars=linkedin_max,
                rank=lead.rank,
                outreach_cfg=self.cfg,
            )
            pack_index[lead.company_id] = pack
            self._write_cache(lead.company_id, pack)

        all_packs = sorted(pack_index.values(), key=lambda p: p.rank or 9999)
        write_staged(self.packs_path, all_packs)
        write_outreach_queue(self.queue_path, all_packs)
        from customer_discovery.outreach.pipeline.review_export import export_outreach_review

        export_outreach_review(
            self.opts.output_dir,
            all_packs,
            briefs_path=self.opts.briefs_path,
            leads_path=self.opts.leads_path,
        )
        stats["packs_written"] = len(all_packs)
        return stats

    def _get_llm(self):
        if self._llm is None:
            from customer_discovery.llm.client import LLMClient

            self._llm = LLMClient()
        return self._llm

    def _write_cache(self, company_id: str, pack: OutreachPack) -> None:
        h = hashlib.sha256(pack.model_dump_json().encode()).hexdigest()[:12]
        path = self.opts.cache_dir / company_id / f"{h}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json.loads(pack.model_dump_json()), indent=2), encoding="utf-8")
