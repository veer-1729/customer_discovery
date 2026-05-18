from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.critique import AdvisorCritique, ReviewedBrief
from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.final import FinalBrief
from customer_discovery.models.premium import PremiumBrief
from customer_discovery.models.signals import SignalRecord
from customer_discovery.models.triage import TriageBrief
from customer_discovery.research.agents.critic import run_critic, run_revision, should_run_critic
from customer_discovery.research.tools.search_fallback import SearchFallbackTool
from customer_discovery.research.agents.evidence_collector import collect_evidence
from customer_discovery.research.agents.fit_scorer import score_fit
from customer_discovery.research.agents.premium import run_premium
from customer_discovery.research.agents.signal_extractor import extract_signals
from customer_discovery.research.agents.triage import run_triage
from customer_discovery.research.config import load_icp_config, load_product_config, load_research_config
from customer_discovery.research.evidence_quality import qualifies_for_premium_llm
from customer_discovery.research.pipeline.cost_estimate import estimate_run_cost
from customer_discovery.research.pipeline.final_selector import select_final_brief
from customer_discovery.research.pipeline.ranker import write_top_leads_csv
from customer_discovery.storage.jsonl import read_jsonl
from customer_discovery.storage.staged_jsonl import (
    append_staged,
    index_by_company,
    load_ids_staged,
)

logger = logging.getLogger(__name__)


@dataclass
class ResearchOptions:
    input_path: Path
    output_dir: Path
    raw_cache_dir: Path
    limit: int | None = None
    company_id: str | None = None
    resume: bool = False
    dry_run: bool = False
    skip_critic: bool = False
    skip_premium: bool = False
    top_n: int = 100
    no_fallback_search: bool = False
    force_refetch: bool = False
    force_search: bool = False
    estimate_cost: bool = False
    verbose: bool = False


@dataclass
class ResearchStats:
    processed: int = 0
    evidence: int = 0
    signals: int = 0
    triage: int = 0
    critic: int = 0
    reviewed: int = 0
    premium: int = 0
    final: int = 0


class ResearchOrchestrator:
    def __init__(self, opts: ResearchOptions) -> None:
        self.opts = opts
        self.cfg = load_research_config()
        self.product = load_product_config()
        self.icp = load_icp_config()
        self.paths = {
            "evidence": opts.output_dir / "evidence_bundles.jsonl",
            "signals": opts.output_dir / "signals.jsonl",
            "triage": opts.output_dir / "triage_briefs.jsonl",
            "critiques": opts.output_dir / "critiques.jsonl",
            "reviewed": opts.output_dir / "reviewed_briefs.jsonl",
            "premium": opts.output_dir / "premium_briefs.jsonl",
            "final": opts.output_dir / "final_briefs.jsonl",
            "csv": opts.output_dir / "top_leads.csv",
        }
        self.stats = ResearchStats()
        self._llm = None

    def _companies(self) -> list[CompanyRecord]:
        records = read_jsonl(self.opts.input_path)
        if self.opts.company_id:
            records = [r for r in records if r.id == self.opts.company_id]
        if self.opts.limit:
            records = records[: self.opts.limit]
        return records

    def run(self) -> ResearchStats:
        companies = self._companies()
        if self.opts.estimate_cost:
            est = estimate_run_cost(
                len(companies),
                self.cfg,
                skip_critic=self.opts.skip_critic,
                skip_premium=self.opts.skip_premium,
            )
            logger.info("Cost estimate: %s", est)
            print(est)

        SearchFallbackTool.configure(
            self.cfg,
            enabled=not self.opts.no_fallback_search,
            state_dir=self.opts.output_dir,
            force_search=self.opts.force_search,
        )

        for company in companies:
            if self._should_stop_on_search_exhausted():
                logger.warning("Stopping research run: search credits exhausted")
                break
            self._process_company(company)

        self._finalize_all(companies)
        return self.stats

    def _process_company(self, company: CompanyRecord) -> None:
        cid = company.id
        if self.opts.resume and cid in load_ids_staged(self.paths["evidence"], EvidenceBundle):
            logger.debug("Resume skip evidence %s", cid)
        else:
            bundle = collect_evidence(
                company,
                self.cfg,
                raw_cache_dir=self.opts.raw_cache_dir,
                search_enabled=not self.opts.no_fallback_search,
                force_refetch=self.opts.force_refetch,
                search_state_dir=self.opts.output_dir,
                force_search=self.opts.force_search,
            )
            append_staged(self.paths["evidence"], bundle)
            self.stats.evidence += 1

        bundle = index_by_company(self.paths["evidence"], EvidenceBundle).get(cid)
        if not bundle:
            return

        if not (self.opts.resume and cid in load_ids_staged(self.paths["signals"], SignalRecord)):
            signals = extract_signals(
                bundle,
                industries=company.industry,
                company_description=company.description,
            )
            det = score_fit(signals, bundle, company)
            rec = SignalRecord(
                company_id=cid,
                signals=signals,
                deterministic_score=det.score,
                positive_rules=det.positive_rules,
                negative_rules=det.negative_rules,
            )
            append_staged(self.paths["signals"], rec)
            self.stats.signals += 1

        if self.opts.dry_run:
            self.stats.processed += 1
            return

        signal_rec = index_by_company(self.paths["signals"], SignalRecord).get(cid)
        if not signal_rec:
            return
        signals = signal_rec.signals
        from customer_discovery.models.scoring import DeterministicFitScore

        det = DeterministicFitScore(
            company_id=cid,
            score=signal_rec.deterministic_score,
            positive_rules=signal_rec.positive_rules,
            negative_rules=signal_rec.negative_rules,
        )

        triage_map = index_by_company(self.paths["triage"], TriageBrief)
        if cid not in triage_map:
            llm = self._get_llm()
            triage = run_triage(
                company,
                bundle,
                signals,
                det,
                llm=llm,
                model=self.cfg.get("models", {}).get("fast_model", "gpt-4o-mini"),
                product=self.product,
                icp=self.icp,
                blend_cfg=self.cfg.get("scoring", {}).get("triage_blend"),
            )
            append_staged(self.paths["triage"], triage)
            self.stats.triage += 1
        else:
            triage = triage_map[cid]

        if (
            not self.opts.skip_critic
            and self._critic_top_n() is None
        ):
            reviewed_map = index_by_company(self.paths["reviewed"], ReviewedBrief)
            if should_run_critic(triage, self.cfg) and cid not in reviewed_map:
                llm = self._get_llm()
                model = self.cfg.get("models", {}).get("critic_model", "gpt-4o-mini")
                critique = run_critic(triage, llm=llm, model=model)
                append_staged(self.paths["critiques"], critique)
                reviewed = run_revision(
                    triage, critique, llm=llm, model=model, coverage=bundle.coverage
                )
                append_staged(self.paths["reviewed"], reviewed)
                self.stats.critic += 1
                self.stats.reviewed += 1

        self.stats.processed += 1

    def _finalize_all(self, companies: list[CompanyRecord]) -> None:
        if self.opts.dry_run:
            return

        bundles = index_by_company(self.paths["evidence"], EvidenceBundle)
        triage_map = index_by_company(self.paths["triage"], TriageBrief)
        reviewed_map = index_by_company(self.paths["reviewed"], ReviewedBrief)
        premium_map = index_by_company(self.paths["premium"], PremiumBrief)

        if not self.opts.skip_critic and self._critic_top_n() is not None:
            self._run_critic_stage(companies, triage_map, bundles)

        reviewed_map = index_by_company(self.paths["reviewed"], ReviewedBrief)

        if not self.opts.skip_premium:
            self._run_premium_stage(companies, bundles, triage_map, reviewed_map, premium_map)

        premium_map = index_by_company(self.paths["premium"], PremiumBrief)
        final_briefs: list[FinalBrief] = []
        for company in companies:
            cid = company.id
            bundle = bundles.get(cid)
            if not bundle:
                continue
            triage = triage_map.get(cid)
            reviewed = reviewed_map.get(cid)
            premium = premium_map.get(cid)
            try:
                fb = select_final_brief(cid, bundle, triage, reviewed, premium)
            except ValueError:
                continue
            final_briefs.append(fb)

        existing_final = load_ids_staged(self.paths["final"], FinalBrief) if self.opts.resume else set()
        for fb in final_briefs:
            if fb.company_id not in existing_final:
                append_staged(self.paths["final"], fb)
                self.stats.final += 1

        all_final = list(index_by_company(self.paths["final"], FinalBrief).values())
        write_top_leads_csv(self.paths["csv"], all_final, bundles)

    def _critic_top_n(self) -> int | None:
        stage = self.cfg.get("stages", {}).get("critic", {})
        top_n = stage.get("top_n")
        return int(top_n) if top_n is not None else None

    def _should_stop_on_search_exhausted(self) -> bool:
        if self.opts.no_fallback_search:
            return False
        if not self.cfg.get("search", {}).get("stop_run_on_exhausted", False):
            return False
        return SearchFallbackTool.search_exhausted()

    def _run_critic_stage(
        self,
        companies: list[CompanyRecord],
        triage_map: dict[str, TriageBrief],
        bundles: dict[str, EvidenceBundle],
    ) -> None:
        top_n = self._critic_top_n()
        if top_n is None:
            return

        stage = self.cfg.get("stages", {}).get("critic", {})
        min_score = int(stage.get("min_score", 60))
        reviewed_map = index_by_company(self.paths["reviewed"], ReviewedBrief)

        eligible: list[tuple[int, CompanyRecord, TriageBrief]] = []
        for company in companies:
            triage = triage_map.get(company.id)
            if not triage or triage.triage_score < min_score:
                continue
            eligible.append((triage.triage_score, company, triage))

        eligible.sort(key=lambda x: -x[0])
        selected = eligible[:top_n]

        llm = self._get_llm()
        model = self.cfg.get("models", {}).get("critic_model", "gpt-4o-mini")

        for _, company, triage in selected:
            cid = company.id
            if cid in reviewed_map:
                continue
            bundle = bundles.get(cid)
            if not bundle:
                continue
            critique = run_critic(triage, llm=llm, model=model)
            append_staged(self.paths["critiques"], critique)
            reviewed = run_revision(
                triage, critique, llm=llm, model=model, coverage=bundle.coverage
            )
            append_staged(self.paths["reviewed"], reviewed)
            self.stats.critic += 1
            self.stats.reviewed += 1

    def _run_premium_stage(
        self,
        companies: list[CompanyRecord],
        bundles: dict[str, EvidenceBundle],
        triage_map: dict[str, TriageBrief],
        reviewed_map: dict[str, ReviewedBrief],
        premium_map: dict[str, PremiumBrief],
    ) -> None:
        stage = self.cfg.get("stages", {}).get("premium", {})
        min_score = stage.get("min_score", 70)
        top_n = self.opts.top_n or stage.get("top_n", 100)

        candidates: list[tuple[int, CompanyRecord, TriageBrief | ReviewedBrief]] = []
        for company in companies:
            cid = company.id
            if cid in premium_map:
                continue
            reviewed = reviewed_map.get(cid)
            triage = triage_map.get(cid)
            brief: TriageBrief | ReviewedBrief | None = reviewed or triage
            if not brief:
                continue
            score = reviewed.reviewed_score if reviewed else triage.triage_score  # type: ignore[union-attr]
            critiques = index_by_company(self.paths["critiques"], AdvisorCritique)
            crit = critiques.get(cid)
            advance = crit.should_advance_to_premium if crit else False
            if score < min_score and not advance:
                continue
            sig_rec = index_by_company(self.paths["signals"], SignalRecord).get(cid)
            bundle = bundles.get(cid)
            if not sig_rec or not bundle:
                continue
            if not qualifies_for_premium_llm(bundle, sig_rec.signals):
                logger.debug(
                    "Skip premium %s (evidence quality / hardware gate)",
                    cid,
                )
                continue
            candidates.append((score, company, brief))

        candidates.sort(key=lambda x: -x[0])
        llm = self._get_llm()
        model = self.cfg.get("models", {}).get("premium_model", "gpt-4o")
        for _, company, brief in candidates[:top_n]:
            bundle = bundles.get(company.id)
            if not bundle:
                continue
            sig_rec = index_by_company(self.paths["signals"], SignalRecord).get(company.id)
            if not sig_rec:
                continue
            if not qualifies_for_premium_llm(bundle, sig_rec.signals):
                continue
            from customer_discovery.models.scoring import DeterministicFitScore

            det = DeterministicFitScore(
                company_id=company.id,
                score=sig_rec.deterministic_score,
                positive_rules=sig_rec.positive_rules,
                negative_rules=sig_rec.negative_rules,
            )
            premium = run_premium(
                company,
                bundle,
                sig_rec.signals,
                det,
                brief,
                llm=llm,
                model=model,
                product=self.product,
                icp=self.icp,
            )
            append_staged(self.paths["premium"], premium)
            self.stats.premium += 1

    def _get_llm(self):
        if self._llm is None:
            from customer_discovery.llm.client import LLMClient

            self._llm = LLMClient()
        return self._llm
