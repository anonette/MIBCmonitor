#!/usr/bin/env python3
"""Add patient_match and subgroup_outcomes to all trials in trials.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_FILE = ROOT / "data" / "trials.json"

# patient_match keyed by trial id
PATIENT_MATCH: dict[str, dict] = {
    "ev-eclipse": {
        "match_type": "by_design",
        "staging_basis": "clinical_cN1_M0",
        "n_like_profile": 23,
        "n_label": "cN1–N3 cM0, perioperative before RC",
        "pct_of_trial": 100,
        "certainty": "high",
        "certainty_label": "By trial design",
        "what_we_know": [
            "Only prospective trial built for node-positive MIBC with EV+pembro before cystectomy",
            "Allows cT2–T4 N1–N3 M0; cisplatin-eligible and -ineligible",
            "Primary endpoint pCR; recruiting, no published efficacy yet",
        ],
        "what_we_dont_know": [
            "Exact cN1-only count vs cN2/N3",
            "External iliac node subset",
            "EFS/OS in node-positive cohort",
        ],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": None, "orr": None},
    },
    "ev-304": {
        "match_type": "published_eligible",
        "staging_basis": "clinical_cN1_M0",
        "n_like_profile": 40,
        "n_label": "cN1 M0 included (~5% estimated; not yet reported)",
        "pct_of_trial": 5,
        "certainty": "moderate",
        "certainty_label": "Estimated — subgroup n pending",
        "what_we_know": [
            "Phase 3 perioperative EV+pembro vs GC in cisplatin-ELIGIBLE MIBC",
            "Eligibility: T2–T4aN0M0 or T1–T4aN1M0",
            "Overall n=808: EFS HR 0.53, pCR 55.8% vs 32.5%",
            "Benefits reported consistent across pre-specified subgroups including stage",
        ],
        "what_we_dont_know": [
            "Exact cN1 patient count and dedicated cN1 EFS/OS/pCR",
            "pN0 rate in cN1 subset",
        ],
        "outcomes_in_subgroup": {
            "pcr": "55.8% overall (cN1 subgroup pending)",
            "pn0_rate": None,
            "efs_hr": 0.53,
            "os_hr": 0.65,
            "orr": None,
        },
    },
    "ev-302": {
        "match_type": "wrong_setting",
        "staging_basis": "metastatic_LN_only",
        "n_like_profile": 207,
        "n_label": "LN-only metastatic/unresectable (not perioperative cN1 M0)",
        "pct_of_trial": 23,
        "certainty": "high",
        "certainty_label": "Published subgroup",
        "what_we_know": [
            "207 patients with lymph-node-only advanced disease",
            "ORR 77.5% vs 53.4%; PFS HR 0.47; OS HR 0.51",
            "Strongest EV+pembro vs chemo data in nodal urothelial cancer",
        ],
        "what_we_dont_know": [
            "Applicability to curative perioperative cN1 M0 pathway",
            "pN0 or pCR after cystectomy — wrong treatment paradigm",
        ],
        "outcomes_in_subgroup": {
            "pcr": None,
            "pn0_rate": None,
            "efs_hr": None,
            "os_hr": 0.51,
            "orr": "77.5%",
        },
    },
    "niagara": {
        "match_type": "published_subgroup",
        "staging_basis": "clinical_cN1",
        "n_like_profile": 58,
        "n_label": "cN1 at baseline (cisplatin-eligible perioperative)",
        "pct_of_trial": 5.5,
        "certainty": "high",
        "certainty_label": "Published cN1 subgroup",
        "what_we_know": [
            "Approved perioperative durvalumab + GC; n=1063 total",
            "cN1 subgroup n=58: EFS HR 0.75 (95% CI 0.22–1.64) — not significant",
            "Overall EFS HR 0.68, pCR 37.3% vs 27.5%",
        ],
        "what_we_dont_know": [
            "Powered cN1 benefit — CI crosses 1",
            "pN0 rate specifically in cN1 patients",
        ],
        "outcomes_in_subgroup": {
            "pcr": "37.3% overall",
            "pn0_rate": None,
            "efs_hr": 0.75,
            "os_hr": None,
            "orr": None,
        },
    },
    "keynote-905": {
        "match_type": "published_subgroup",
        "staging_basis": "clinical_cN1_M0",
        "n_like_profile": 17,
        "n_label": "T1–T4aN1 (4.9%); cisplatin-INELIGIBLE population",
        "pct_of_trial": 4.9,
        "certainty": "low",
        "certainty_label": "Tiny cN1 subset; wrong population if cis-fit",
        "what_we_know": [
            "Phase 3 perioperative EV+pembro vs RC alone in cis-ineligible MIBC",
            "Overall EFS HR 0.40, pCR 57.1%",
            "~17 cN1 patients — insufficient for subgroup conclusions",
        ],
        "what_we_dont_know": [
            "cN1-specific EFS, pCR, pN0",
            "Applicability if patient is cisplatin-eligible",
        ],
        "outcomes_in_subgroup": {
            "pcr": "57.1% overall",
            "pn0_rate": None,
            "efs_hr": 0.4,
            "os_hr": 0.5,
            "orr": None,
        },
    },
    "swog-8710": {
        "match_type": "none",
        "staging_basis": "clinical_cN0_only",
        "n_like_profile": 0,
        "n_label": "cN0 only — no node-positive patients enrolled",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "Zero match by design",
        "what_we_know": [
            "Foundational NAC RCT in MIBC (MVAC → RC)",
            "Established OS benefit for NAC in N0 MIBC",
        ],
        "what_we_dont_know": [
            "Any direct evidence for cN1 M0 — not enrolled",
        ],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": None, "orr": None},
    },
    "ba06": {
        "match_type": "none",
        "staging_basis": "clinical_cN0_only",
        "n_like_profile": 0,
        "n_label": "N0 only",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "Zero match",
        "what_we_know": ["Second foundational NAC trial (CMV); n=976 N0"],
        "what_we_dont_know": ["cN+ outcomes"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": None, "orr": None},
    },
    "nac-meta": {
        "match_type": "indirect",
        "staging_basis": "mixed_MIBC",
        "n_like_profile": None,
        "n_label": "Meta-analysis — cN+ not isolated",
        "pct_of_trial": None,
        "certainty": "low",
        "certainty_label": "Indirect",
        "what_we_know": ["OS HR ~0.82–0.87 for NAC in MIBC broadly"],
        "what_we_dont_know": ["Dedicated cN1 M0 perioperative counts"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": "0.82-0.87", "orr": None},
    },
    "ev-103-k": {
        "match_type": "wrong_setting",
        "staging_basis": "metastatic",
        "n_like_profile": 0,
        "n_label": "Metastatic cis-ineligible — not perioperative cN1",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "Background only",
        "what_we_know": ["Led to EV-302; ORR 64.5% in la/mUC"],
        "what_we_dont_know": ["Perioperative cN1 relevance"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": None, "orr": "64.5%"},
    },
    "checkmate-274": {
        "match_type": "wrong_timing",
        "staging_basis": "pathologic_pN1",
        "n_like_profile": 143,
        "n_label": "pN1 after surgery (adjuvant, not neoadjuvant)",
        "pct_of_trial": 20,
        "certainty": "high",
        "certainty_label": "Adjuvant setting",
        "what_we_know": [
            "Adjuvant nivolumab post-RC; DFS HR 0.70",
            "143 patients with pN1 at surgery",
        ],
        "what_we_dont_know": [
            "Neoadjuvant cN1 M0 pathway — different clinical question",
        ],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": None, "dfs_hr": 0.7},
    },
    "ambassador": {
        "match_type": "wrong_timing",
        "staging_basis": "pathologic_pN_plus",
        "n_like_profile": None,
        "n_label": "pN+ eligible post-surgery; exact pN1 n not in primary",
        "pct_of_trial": None,
        "certainty": "moderate",
        "certainty_label": "Adjuvant only",
        "what_we_know": ["Adjuvant pembrolizumab; DFS benefit in high-risk MIBC"],
        "what_we_dont_know": ["Exact pN1 count; neoadjuvant cN1 data"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": None, "dfs_hr": "~benefit"},
    },
    "zargar-shoshtar-2016": {
        "match_type": "retrospective_cn_plus",
        "staging_basis": "clinical_cN1_M0",
        "n_like_profile": 304,
        "n_label": "All cN1–N3 M0; cN1-specific pN0 56%",
        "pct_of_trial": 100,
        "certainty": "moderate",
        "certainty_label": "Retrospective — standard chemo",
        "what_we_know": [
            "304 clinically node-positive patients; induction MVAC/GC → RC",
            "48% overall pN0; 56% in cN1 subgroup",
            "Median OS longer in downstaged patients",
        ],
        "what_we_dont_know": [
            "Randomized comparison; EV+pembro outcomes",
            "External iliac node subset",
        ],
        "outcomes_in_subgroup": {
            "pcr": "14.5%",
            "pn0_rate": "56% in cN1",
            "efs_hr": None,
            "os_hr": None,
            "orr": None,
        },
    },
    "hermans-cn-plus-659": {
        "match_type": "retrospective_cn_plus",
        "staging_basis": "clinical_cN_plus_M0",
        "n_like_profile": 659,
        "n_label": "cN+ M0 population-based cohort",
        "pct_of_trial": 100,
        "certainty": "moderate",
        "certainty_label": "Retrospective population data",
        "what_we_know": [
            "NAC associated with lower death risk (HR 0.47) in cN+ MIBC",
            "cN1: 3-year OS 66% with NAC vs 37% upfront RC",
        ],
        "what_we_dont_know": ["RCT-level evidence; modern IO/EV regimens"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": 0.47, "orr": None},
    },
    "cn-plus-radiologic-130": {
        "match_type": "retrospective_cn_plus",
        "staging_basis": "clinical_cN_plus",
        "n_like_profile": 130,
        "n_label": "Clinically node-positive MIBC",
        "pct_of_trial": 100,
        "certainty": "moderate",
        "certainty_label": "Retrospective",
        "what_we_know": [
            "40.8% pN0 after induction chemo vs 11.1% surgery alone",
            "Median OS 12.8 y if pN0 vs 1.9 y if residual pN+",
        ],
        "what_we_dont_know": ["EV+pembro; prospective validation"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": "40.8%", "efs_hr": None, "os_hr": None, "orr": None},
    },
    "ncdb-cn-plus-491": {
        "match_type": "retrospective_cn_plus",
        "staging_basis": "clinical_cN1_N3_M0",
        "n_like_profile": 491,
        "n_label": "cTany N1–N3 M0 with NAC + RC",
        "pct_of_trial": 100,
        "certainty": "moderate",
        "certainty_label": "NCDB retrospective",
        "what_we_know": ["35% ypN0 at RC; 5-year OS 34% overall"],
        "what_we_dont_know": ["cN1-only breakdown; modern perioperative IO"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": "35%", "efs_hr": None, "os_hr": None, "orr": None},
    },
    "pure-01": {
        "match_type": "wrong_population",
        "staging_basis": "clinical_cN0",
        "n_like_profile": 0,
        "n_label": "Predominantly cN0; not designed for cN+",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "Wrong population",
        "what_we_know": [
            "Neoadjuvant pembro monotherapy; pCR 42%",
            "ypN+ patients: 5-y OS only 41.9% — nodal response critical",
        ],
        "what_we_dont_know": ["cN1 perioperative pembro efficacy"],
        "outcomes_in_subgroup": {"pcr": "42%", "pn0_rate": None, "efs_hr": None, "os_hr": None, "orr": None},
    },
    "abacus": {
        "match_type": "none",
        "staging_basis": "clinical_cN0",
        "n_like_profile": 0,
        "n_label": "cN0 cis-ineligible only",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "No node-positive patients",
        "what_we_know": ["Atezo neoadjuvant; pCR 31%"],
        "what_we_dont_know": ["cN1 relevance"],
        "outcomes_in_subgroup": {"pcr": "31%", "pn0_rate": None, "efs_hr": None, "os_hr": None, "orr": None},
    },
    "checkmate-901-ln-only": {
        "match_type": "wrong_setting",
        "staging_basis": "metastatic_LN_only",
        "n_like_profile": 110,
        "n_label": "LN-only metastatic (nivo+GC)",
        "pct_of_trial": 18,
        "certainty": "moderate",
        "certainty_label": "Metastatic — superseded by EV-302",
        "what_we_know": ["LN-only: PFS HR 0.38, OS HR 0.58 with nivo+GC"],
        "what_we_dont_know": ["Perioperative curative pathway"],
        "outcomes_in_subgroup": {"pcr": None, "pn0_rate": None, "efs_hr": None, "os_hr": 0.58, "orr": None},
    },
    "javelin-100": {
        "match_type": "wrong_setting",
        "staging_basis": "metastatic",
        "n_like_profile": 0,
        "n_label": "Metastatic maintenance — not perioperative cN1",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "Wrong setting",
        "what_we_know": ["Maintenance avelumab post-platinum"],
        "what_we_dont_know": ["cN1 M0 perioperative relevance"],
        "outcomes_in_subgroup": {},
    },
    "checkmate-901": {
        "match_type": "wrong_setting",
        "staging_basis": "metastatic",
        "n_like_profile": 0,
        "n_label": "Advanced/metastatic overall",
        "pct_of_trial": 0,
        "certainty": "high",
        "certainty_label": "Wrong setting",
        "what_we_know": ["1L metastatic chemo-IO trial"],
        "what_we_dont_know": ["Perioperative cN1"],
        "outcomes_in_subgroup": {},
    },
}


def build_subgroup_panel(trial: dict, pm: dict) -> dict:
    """Structured panel for trial detail UI."""
    eff = trial.get("efficacy") or {}
    panel = {
        "headline": pm.get("n_label", ""),
        "certainty": pm.get("certainty"),
        "certainty_label": pm.get("certainty_label"),
        "n_like_profile": pm.get("n_like_profile"),
        "pct_of_trial": pm.get("pct_of_trial"),
        "staging_basis": pm.get("staging_basis"),
        "outcomes": pm.get("outcomes_in_subgroup", {}),
        "what_we_know": pm.get("what_we_know", []),
        "what_we_dont_know": pm.get("what_we_dont_know", []),
    }
    if eff.get("ln_only_subgroup"):
        panel["published_subgroup"] = eff["ln_only_subgroup"]
    if eff.get("cn1_subgroup"):
        panel["published_subgroup"] = eff["cn1_subgroup"]
    if eff.get("pn0_rate_pct") or eff.get("cn1_pn0_rate_pct"):
        panel["nodal_outcomes"] = {
            k: eff[k]
            for k in eff
            if "pn0" in k or "pcr" in k or "ypN" in k
        }
    return panel


def main() -> None:
    data = json.loads(TRIALS_FILE.read_text(encoding="utf-8"))
    for trial in data["trials"]:
        tid = trial["id"]
        if tid not in PATIENT_MATCH:
            print(f"Warning: no patient_match for {tid}")
            continue
        pm = PATIENT_MATCH[tid]
        trial["patient_match"] = pm
        trial["subgroup_outcomes"] = build_subgroup_panel(trial, pm)
    data["meta"]["version"] = "1.3"
    data["meta"]["updated"] = "2026-06-07"
    data["meta"]["patient_match_enriched"] = True
    TRIALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Enriched {len(PATIENT_MATCH)} trials in {TRIALS_FILE}")


if __name__ == "__main__":
    main()
