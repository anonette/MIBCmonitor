#!/usr/bin/env python3
"""
MIBC cN1 cM0 evidence research agent.

Ingests papers/trials, scores fit against target patient profile,
maintains evidence_registry.csv, and prints comparison tables.

Usage:
  python scripts/research_agent.py --list
  python scripts/research_agent.py --compare
  python scripts/research_agent.py --source <url_or_file> [--compile-wiki]
  python scripts/research_agent.py --watch-trials
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "evidence_registry.csv"
RAW_DIR = ROOT / "raw" / "bladder-cancer"
WIKI_COMPARISON = ROOT / "wiki" / "bladder-cancer" / "cn1-mibc-evidence-comparison.md"

TARGET_PROFILE = {
    "histology": "muscle-invasive urothelial carcinoma high grade",
    "stage": "cT2 cN1 cM0",
    "features": ["L1 lymphovascular invasion", "PET-positive external iliac node"],
    "intent": "perioperative systemic therapy before radical cystectomy",
    "exclude_settings": ["metastatic maintenance", "adjuvant-only post RC without neoadjuvant debate"],
}

NCT_IDS = [
    "NCT05239624",  # EV-ECLIPSE
    "NCT04223856",  # EV-302
    "NCT03924895",  # KEYNOTE-905
    "NCT03732677",  # NIAGARA
    "NCT04700124",  # EV-304
    "NCT02632409",  # CheckMate 274
    "NCT03244384",  # AMBASSADOR
]


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    with REGISTRY.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_registry(rows: list[dict]) -> None:
    if not rows:
        return
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def cmd_list() -> None:
    rows = sorted(load_registry(), key=lambda r: (-int(r.get("fit_score", 0) or 0), r.get("priority", "99")))
    print(f"\n{'Pri':<4} {'Study':<28} {'N':>6} {'cN+/cN1':>8} {'Tier':<6} {'Score':>5}  Setting")
    print("-" * 95)
    for r in rows:
        setting = (r.get("setting", "") or "").encode("ascii", "replace").decode("ascii")
        print(
            f"{r.get('priority','-'):<4} {r.get('study_id','')[:28]:<28} "
            f"{r.get('total_n',''):>6} {r.get('cn1_or_cn_plus_n',''):>8} "
            f"{r.get('fit_tier',''):<6} {r.get('fit_score',''):>5}  "
            f"{setting[:40]}"
        )
    print(f"\nTarget profile: {TARGET_PROFILE['stage']} | {TARGET_PROFILE['intent']}\n")


def cmd_compare() -> None:
    rows = load_registry()
    perioperative = [r for r in rows if r.get("fit_tier", "").startswith(("A", "B"))]
    print("\n=== PATIENT COUNT COMPARISON: cN1 cM0 Perioperative-Relevant Evidence ===\n")
    print(f"{'Study':<32} {'Total N':>8} {'cN1/cN+ n':>10} {'% trial':>8} {'Tier':<5} {'Score':>5}")
    print("-" * 72)
    for r in sorted(perioperative, key=lambda x: -int(x.get("fit_score", 0) or 0)):
        total = r.get("total_n", "")
        cn = r.get("cn1_or_cn_plus_n", "")
        pct = r.get("match_pct", "")
        print(
            f"{r.get('study_id','')[:32]:<32} {str(total):>8} {str(cn):>10} "
            f"{str(pct):>7}% {r.get('fit_tier',''):<5} {r.get('fit_score',''):>5}"
        )

    print("\n=== KEY FINDING ===")
    eclipse = next((r for r in rows if "ECLIPSE" in r.get("study_id", "")), None)
    ev302 = next((r for r in rows if "EV-302" in r.get("study_id", "")), None)
    niagara = next((r for r in rows if "NIAGARA" in r.get("study_id", "")), None)
    k905 = next((r for r in rows if "905" in r.get("study_id", "")), None)

    if eclipse:
        print(f"- EV-ECLIPSE: only trial DESIGNED for node-positive perioperative EV+pembro (n~{eclipse.get('total_n')})")
    if ev302:
        print(f"- EV-302 LN-only (n={ev302.get('cn1_or_cn_plus_n')}): strongest EV+pembro efficacy but METASTATIC setting")
    if niagara:
        print(f"- NIAGARA cN1 (n={niagara.get('cn1_or_cn_plus_n')}): approved perioperative alt; cN1 subgroup NS")
    if k905:
        print(f"- KEYNOTE-905 cN1 (n~{k905.get('cn1_or_cn_plus_n')}): perioperative phase 3 but cisplatin-INELIGIBLE population")
    ev304 = next((r for r in rows if "EV-304" in r.get("study_id", "") or "B15" in r.get("study_id", "")), None)
    if ev304:
        print(f"- EV-304/KEYNOTE-B15 (n={ev304.get('total_n')}): perioperative EV+pembro vs GC in CISPLATIN-ELIGIBLE MIBC")
    zargar = next((r for r in rows if "Zargar" in r.get("study_id", "")), None)
    if zargar:
        print(f"- Zargar-Shoshtar (n={zargar.get('cn1_or_cn_plus_n')}): retrospective cN+ NAC, 48% pN0 rate")
    print()


def fetch_url(url: str) -> str:
    req = Request(url, headers={"User-Agent": "MIBC-Research-Agent/1.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "source"


def cmd_source(source: str, compile_wiki: bool) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    if source.startswith("http"):
        content = fetch_url(source)
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.I)
        title = title_match.group(1).strip() if title_match else "web-source"
        raw_path = RAW_DIR / f"{today}-{slugify(title)}.md"
        raw_path.write_text(
            f"# {title}\n\n**Source URL:** {source}\n**Collected:** {today}\n**Published:** Unknown\n\n---\n\n{content[:50000]}\n",
            encoding="utf-8",
        )
        print(f"Ingested URL → {raw_path}")
    else:
        src_path = Path(source)
        if not src_path.exists():
            print(f"File not found: {source}", file=sys.stderr)
            sys.exit(1)
        raw_path = RAW_DIR / f"{today}-{src_path.stem}.md"
        raw_path.write_text(
            f"**Source file:** {src_path}\n**Collected:** {today}\n\n---\n\n{src_path.read_text(encoding='utf-8')}",
            encoding="utf-8",
        )
        print(f"Copied → {raw_path}")

    extracted = extract_trial_fields(raw_path.read_text(encoding="utf-8"))
    if extracted:
        print("\nExtracted fields:")
        print(json.dumps(extracted, indent=2))
        append_or_update_registry(extracted)
    else:
        print("\nNo structured trial fields extracted. Review raw file manually.")

    if compile_wiki:
        print(f"\nWiki compile requested — update {WIKI_COMPARISON} manually or via Gabriel pipeline.")


def extract_trial_fields(text: str) -> dict | None:
    """Rule-based extraction; upgrade with GABRIEL extract() when OPENAI_API_KEY set."""
    nct = re.search(r"(NCT\d{8})", text)
    n_enroll = re.search(r"(?:Enrollment|participants|randomized)[:\s]+(\d[\d,]*)", text, re.I)
    cn1 = re.search(r"(?:cN1|N1 disease|node.?positive)[^\d]*(\d+)", text, re.I)

    if not (nct or n_enroll):
        return None

    try:
        import os
        if os.environ.get("OPENAI_API_KEY"):
            return extract_with_gabriel(text)
    except ImportError:
        pass

    return {
        "nct_id": nct.group(1) if nct else "",
        "total_n": n_enroll.group(1).replace(",", "") if n_enroll else "",
        "cn1_or_cn_plus_n": cn1.group(1) if cn1 else "",
        "study_id": nct.group(1) if nct else "unknown",
        "source_note": "rule-based extraction — verify manually",
    }


def extract_with_gabriel(text: str) -> dict:
    import gabriel

    prompt = (
        "Extract clinical trial fields for muscle-invasive bladder cancer evidence registry. "
        "Return JSON with: study_id, nct_id, phase, setting, total_n, cn1_or_cn_plus_n, "
        "treatment, key_outcome, fit_tier (A/B/C/D), fit_score (0-100), limitation_for_patient."
    )
    result = gabriel.extract(
        text[:12000],
        attributes=["study_id", "nct_id", "phase", "setting", "total_n", "cn1_or_cn_plus_n",
                    "treatment", "key_outcome", "fit_tier", "fit_score", "limitation_for_patient"],
        instructions=prompt,
    )
    return dict(result) if result else {}


def append_or_update_registry(fields: dict) -> None:
    rows = load_registry()
    nct = fields.get("nct_id", "")
    study = fields.get("study_id", "")
    for r in rows:
        if nct and r.get("nct_id") == nct:
            r.update({k: str(v) for k, v in fields.items() if v})
            save_registry(rows)
            print(f"Updated registry entry: {r.get('study_id')}")
            return
    print("New study detected — add full row to evidence_registry.csv manually after verification.")


def cmd_watch_trials() -> None:
    print("\nClinicalTrials.gov status check:\n")
    for nct in NCT_IDS:
        try:
            url = f"https://clinicaltrials.gov/api/v2/studies/{nct}?format=json"
            data = json.loads(fetch_url(url))
            proto = data.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            title = ident.get("briefTitle", nct)
            overall = status.get("overallStatus", "unknown")
            enrollment = design.get("enrollmentInfo", {}).get("count", "?")
            print(f"  {nct}: {overall} | N≈{enrollment} | {title[:60]}")
        except Exception as e:
            print(f"  {nct}: fetch failed ({e})")


def main() -> None:
    parser = argparse.ArgumentParser(description="MIBC cN1 evidence research agent")
    parser.add_argument("--list", action="store_true", help="List registry by fit score")
    parser.add_argument("--compare", action="store_true", help="Print patient-count comparison")
    parser.add_argument("--source", type=str, help="Ingest URL or file path")
    parser.add_argument("--compile-wiki", action="store_true", help="Trigger wiki compile after ingest")
    parser.add_argument("--watch-trials", action="store_true", help="Refresh trial status from ClinicalTrials.gov")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.compare:
        cmd_compare()
    elif args.source:
        cmd_source(args.source, args.compile_wiki)
    elif args.watch_trials:
        cmd_watch_trials()
    else:
        parser.print_help()
        print("\nRecommended first run: python scripts/research_agent.py --compare")


if __name__ == "__main__":
    main()
