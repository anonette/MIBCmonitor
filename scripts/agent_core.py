"""
Core logic for the MIBC evidence watch agent.
Search, validate, refresh trials, merge new findings into JSON datasets.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent

try:
    from env_config import load_dotenv
    load_dotenv()
except ImportError:
    pass
DATA = ROOT / "data"
RAW = ROOT / "raw" / "bladder-cancer"
LOG_FILE = DATA / "agent_log.json"

TRIALS_FILE = DATA / "trials.json"
PAPERS_FILE = DATA / "papers_index.json"
PROFILE_FILE = DATA / "patient_profile.json"

WATCHED_NCTS = [
    "NCT05239624",  # EV-ECLIPSE
    "NCT04700124",  # EV-304
    "NCT03924895",  # KEYNOTE-905
    "NCT04223856",  # EV-302
    "NCT03732677",  # NIAGARA
    "NCT02632409",  # CheckMate 274
    "NCT03244384",  # AMBASSADOR
    "NCT03288545",  # EV-103
    "NCT02736266",  # PURE-01
]

SEARCH_QUERIES = [
    "muscle invasive bladder cancer node positive neoadjuvant",
    "enfortumab vedotin pembrolizumab muscle invasive bladder perioperative",
    "cN1 bladder cancer radical cystectomy chemotherapy",
    "urothelial carcinoma clinical node positive M0 cystectomy",
]

PUBMED_QUERY = (
    "(muscle invasive bladder cancer[Title/Abstract]) AND "
    "(node positive[Title/Abstract] OR cN1[Title/Abstract] OR lymph node[Title/Abstract]) AND "
    "(neoadjuvant[Title/Abstract] OR perioperative[Title/Abstract] OR enfortumab vedotin[Title/Abstract])"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str, timeout: int = 30) -> dict | list:
    req = Request(url, headers={"User-Agent": "MIBC-Evidence-Agent/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_text(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": "MIBC-Evidence-Agent/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def list_pending_papers() -> list[dict]:
    papers = load_json(PAPERS_FILE).get("papers", [])
    return [p for p in papers if p.get("status") == "needs_review"]


def assess_for_review(paper: dict) -> dict:
    """Human-readable scope hints for cN+ M0 perioperative review queue."""
    text = (paper.get("title") or "").lower()
    pros: list[str] = []
    cons: list[str] = []

    out_of_scope = [
        ("non-muscle-invasive", "NMIBC — outside site scope (MIBC cN+ M0 only)"),
        ("non muscle invasive", "NMIBC — outside site scope"),
        ("non-muscle invasive", "NMIBC — outside site scope"),
        ("bladder sparing", "Bladder preservation — outside site scope"),
        ("bladder preservation", "Bladder preservation — outside site scope"),
        ("active surveillance", "Bladder-sparing / surveillance pathway"),
        ("trimodality", "Trimodality bladder preservation"),
        ("her2-positive", "HER2-selected population — narrow eligibility"),
        ("her2 positive", "HER2-selected population"),
        ("intravesical", "Intravesical therapy — not systemic perioperative"),
        ("staging paradigm", "Imaging/staging study — not treatment trial"),
        ("mpmri", "Imaging staging — not treatment evidence"),
    ]
    in_scope = [
        ("node positive", "Mentions node-positive disease"),
        ("lymph node-positive", "Clinical node-positive bladder cancer"),
        ("lymph node positive", "Node-positive context"),
        ("cN1", "Mentions cN1 staging"),
        ("perioperative", "Perioperative treatment setting"),
        ("neoadjuvant", "Neoadjuvant systemic therapy"),
        ("enfortumab", "Enfortumab vedotin (EV) regimen"),
        ("pembrolizumab", "Pembrolizumab"),
        ("durvalumab", "Durvalumab"),
        ("gemcitabine", "Cisplatin-based chemotherapy context"),
        ("cystectomy", "Radical cystectomy pathway"),
        ("muscle-invasive", "Muscle-invasive bladder cancer"),
        ("muscle invasive", "Muscle-invasive bladder cancer"),
    ]

    for term, msg in out_of_scope:
        if term in text:
            cons.append(msg)
    for term, msg in in_scope:
        if term in text and msg not in pros:
            pros.append(msg)

    if paper.get("nct_id"):
        pros.append(f"Registered trial: {paper['nct_id']}")
    if paper.get("pmid"):
        pros.append(f"Published paper: PMID {paper['pmid']}")
    if paper.get("n"):
        pros.append(f"Stated enrollment: n={paper['n']}")

    score = paper.get("relevance_score") or score_relevance(paper)
    if cons and len(pros) <= 1:
        suggestion = "likely_exclude"
        verdict = "Likely exclude — weak match to cN+ M0 perioperative MIBC"
    elif any("node" in p.lower() or "cN1" in p for p in pros):
        suggestion = "strong_candidate"
        verdict = "Strong candidate — node-positive / perioperative signals"
    elif pros and cons:
        suggestion = "mixed"
        verdict = "Mixed — open source and check for cN1 M0 subgroup data"
    elif pros:
        suggestion = "worth_review"
        verdict = "Worth reviewing — perioperative MIBC relevance"
    else:
        suggestion = "unclear"
        verdict = "Unclear — read abstract before including"

    return {
        "scope_verdict": verdict,
        "suggestion": suggestion,
        "pros": pros[:6],
        "cons": cons[:6],
        "relevance_score": score,
    }


def list_pending_for_review() -> list[dict]:
    items = []
    for p in list_pending_papers():
        entry = dict(p)
        entry["review"] = assess_for_review(p)
        items.append(entry)
    return sorted(items, key=lambda x: -(x.get("relevance_score") or 0))


def approve_paper(paper_id: str) -> dict:
    """Mark paper as approved (ready for manual trials.json merge)."""
    papers_data = load_json(PAPERS_FILE)
    papers = papers_data.get("papers", [])
    for p in papers:
        if p.get("id") == paper_id:
            p["status"] = "approved"
            p["approved_at"] = utc_now()
            papers_data["papers"] = papers
            papers_data["updated"] = utc_now()[:10]
            save_json(PAPERS_FILE, papers_data)
            append_log({"type": "approve", "paper_id": paper_id, "title": p.get("title")})
            return {"ok": True, "paper_id": paper_id, "status": "approved"}
    return {"ok": False, "error": f"Paper not found: {paper_id}"}


def reject_paper(paper_id: str, reason: str = "") -> dict:
    """Mark paper as rejected (excluded from evidence set)."""
    papers_data = load_json(PAPERS_FILE)
    papers = papers_data.get("papers", [])
    for p in papers:
        if p.get("id") == paper_id:
            p["status"] = "rejected"
            p["rejected_at"] = utc_now()
            if reason:
                p["reject_reason"] = reason
            papers_data["papers"] = papers
            papers_data["updated"] = utc_now()[:10]
            save_json(PAPERS_FILE, papers_data)
            append_log({"type": "reject", "paper_id": paper_id, "title": p.get("title"), "reason": reason})
            return {"ok": True, "paper_id": paper_id, "status": "rejected"}
    return {"ok": False, "error": f"Paper not found: {paper_id}"}


def append_log(entry: dict) -> None:
    log = load_json(LOG_FILE) if LOG_FILE.exists() else {"runs": []}
    if "runs" not in log:
        log["runs"] = []
    log["runs"].insert(0, entry)
    log["runs"] = log["runs"][:50]
    save_json(LOG_FILE, log)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "study"


# --- Validation ---

def validate_datasets() -> dict:
    issues: list[dict] = []
    trials_data = load_json(TRIALS_FILE)
    papers_data = load_json(PAPERS_FILE)
    trials = trials_data.get("trials", [])
    papers = papers_data.get("papers", [])

    required_trial_fields = ["id", "study_id", "fit_tier", "fit_score", "interpretation"]
    for t in trials:
        tid = t.get("id", "?")
        for field in required_trial_fields:
            if not t.get(field):
                issues.append({"severity": "warning", "trial": tid, "message": f"Missing field: {field}"})
        if t.get("nct_id") and not t.get("source_url"):
            issues.append({"severity": "info", "trial": tid, "message": "Has NCT but no source_url"})
        raw_n = t.get("cn1_cn_plus_n")
        total = t.get("total_n")
        if raw_n and total and isinstance(raw_n, (int, float)) and isinstance(total, (int, float)):
            if raw_n > total:
                issues.append({"severity": "error", "trial": tid, "message": f"cN1 n ({raw_n}) > total_n ({total})"})

    known_ncts = {t.get("nct_id") for t in trials if t.get("nct_id")}
    known_urls = {p.get("url") for p in papers if p.get("url")}
    known_ids = {t.get("id") for t in trials} | {p.get("id") for p in papers}

    for nct in WATCHED_NCTS:
        if nct not in known_ncts:
            issues.append({"severity": "warning", "message": f"Watched NCT {nct} not in trials.json"})

    return {
        "ok": not any(i["severity"] == "error" for i in issues),
        "trial_count": len(trials),
        "paper_count": len(papers),
        "issue_count": len(issues),
        "issues": issues[:30],
        "checked_at": utc_now(),
    }


# --- ClinicalTrials.gov ---

def fetch_ctgov_study(nct_id: str) -> dict | None:
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?format=json"
        data = fetch_json(url)
        proto = data.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        conditions = proto.get("conditionsModule", {}).get("conditions", [])
        interventions = [
            i.get("name", "")
            for i in proto.get("armsInterventionsModule", {}).get("interventions", [])
        ]
        phases = design.get("phases", [])
        return {
            "nct_id": nct_id,
            "title": ident.get("briefTitle", ""),
            "status": status.get("overallStatus", "unknown"),
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "phases": phases,
            "conditions": conditions[:3],
            "interventions": interventions[:5],
            "last_update": status.get("lastUpdatePostDateStruct", {}).get("date", ""),
            "url": f"https://clinicaltrials.gov/study/{nct_id}",
        }
    except Exception as exc:
        return {"nct_id": nct_id, "error": str(exc)}


def search_ctgov(query: str, page_size: int = 15) -> list[dict]:
    params = urlencode({
        "query.term": query,
        "pageSize": page_size,
        "format": "json",
    })
    url = f"https://clinicaltrials.gov/api/v2/studies?{params}"
    try:
        data = fetch_json(url)
        results = []
        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            nct = ident.get("nctId", "")
            results.append({
                "source": "clinicaltrials.gov",
                "nct_id": nct,
                "title": ident.get("briefTitle", ""),
                "status": status.get("overallStatus", ""),
                "enrollment": design.get("enrollmentInfo", {}).get("count"),
                "phases": design.get("phases", []),
                "url": f"https://clinicaltrials.gov/study/{nct}" if nct else "",
                "query": query,
            })
        return results
    except Exception as exc:
        return [{"source": "clinicaltrials.gov", "error": str(exc), "query": query}]


# --- PubMed ---

def search_pubmed(query: str = PUBMED_QUERY, retmax: int = 15) -> list[dict]:
    try:
        search_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
            + urlencode({"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"})
        )
        search_data = fetch_json(search_url)
        ids = search_data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        summary_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
            + urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
        )
        summary_data = fetch_json(summary_url)
        result = summary_data.get("result", {})
        papers = []
        for pid in ids:
            item = result.get(pid, {})
            if not item:
                continue
            papers.append({
                "source": "pubmed",
                "pmid": pid,
                "title": item.get("title", ""),
                "journal": item.get("fulljournalname", item.get("source", "")),
                "pubdate": item.get("pubdate", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                "query": query,
            })
        return papers
    except Exception as exc:
        return [{"source": "pubmed", "error": str(exc)}]


# --- Dedup & merge ---

def existing_keys() -> set[str]:
    keys: set[str] = set()
    trials = load_json(TRIALS_FILE).get("trials", [])
    papers = load_json(PAPERS_FILE).get("papers", [])
    for t in trials:
        if t.get("nct_id"):
            keys.add(t["nct_id"].upper())
        if t.get("id"):
            keys.add(t["id"].lower())
        if t.get("study_id"):
            keys.add(re.sub(r"\W+", "", t["study_id"].lower())[:40])
    for p in papers:
        if p.get("url"):
            keys.add(p["url"].lower())
        if p.get("id"):
            keys.add(p["id"].lower())
    return keys


def is_duplicate(hit: dict, keys: set[str]) -> bool:
    nct = (hit.get("nct_id") or "").upper()
    if nct and nct in keys:
        return True
    url = (hit.get("url") or "").lower()
    if url and url in keys:
        return True
    title = re.sub(r"\W+", "", (hit.get("title") or "").lower())[:50]
    if title and title in keys:
        return True
    return False


def score_relevance(hit: dict) -> int:
    """Heuristic 0-100 relevance to cN1 cM0 perioperative MIBC."""
    text = " ".join([
        hit.get("title", ""),
        " ".join(hit.get("conditions", [])),
        " ".join(hit.get("interventions", [])),
    ]).lower()
    score = 0
    keywords = {
        "node positive": 20, "cN1": 20, "n1": 10, "perioperative": 15,
        "neoadjuvant": 15, "muscle-invasive": 15, "muscle invasive": 15,
        "enfortumab": 15, "pembrolizumab": 10, "durvalumab": 10,
        "cystectomy": 10, "urothelial": 8, "bladder": 8, "EV-": 10,
        "KEYNOTE": 8, "NIAGARA": 8,
    }
    for kw, pts in keywords.items():
        if kw.lower() in text:
            score += pts
    if hit.get("source") == "clinicaltrials.gov" and hit.get("nct_id"):
        score += 5
    return min(score, 100)


def refresh_watched_trials() -> list[dict]:
    updates = []
    trials_data = load_json(TRIALS_FILE)
    trials = trials_data.get("trials", [])
    by_nct = {t["nct_id"]: t for t in trials if t.get("nct_id")}

    for nct in WATCHED_NCTS:
        info = fetch_ctgov_study(nct)
        if not info or info.get("error"):
            updates.append({"nct_id": nct, "action": "fetch_failed", "detail": info})
            continue
        if nct in by_nct:
            t = by_nct[nct]
            changed = []
            if info.get("status") and info["status"] != t.get("status"):
                t["status"] = info["status"]
                changed.append("status")
            if info.get("enrollment") and info["enrollment"] != t.get("total_n"):
                t["total_n"] = info["enrollment"]
                changed.append("total_n")
            if changed:
                t["last_refreshed"] = utc_now()
                updates.append({"nct_id": nct, "action": "updated", "fields": changed, "info": info})
            else:
                updates.append({"nct_id": nct, "action": "unchanged", "status": info.get("status")})
        else:
            updates.append({"nct_id": nct, "action": "new_nct_not_in_dataset", "info": info})

    trials_data["meta"]["last_agent_refresh"] = utc_now()
    save_json(TRIALS_FILE, trials_data)
    return updates


def add_paper_stub(hit: dict) -> dict:
    papers_data = load_json(PAPERS_FILE)
    papers = papers_data.get("papers", [])

    pid = slugify(hit.get("title", hit.get("nct_id", "new")))
    if hit.get("pmid"):
        pid = f"pmid-{hit['pmid']}"
    elif hit.get("nct_id"):
        pid = hit["nct_id"].lower()

    entry = {
        "id": pid,
        "title": hit.get("title", "Untitled"),
        "type": "auto-discovered",
        "n": hit.get("enrollment"),
        "url": hit.get("url", ""),
        "discovered_at": utc_now(),
        "relevance_score": score_relevance(hit),
        "source": hit.get("source", "agent"),
        "status": "needs_review",
    }
    if hit.get("nct_id"):
        entry["nct_id"] = hit["nct_id"]
    if hit.get("pmid"):
        entry["pmid"] = hit["pmid"]

    papers.append(entry)
    papers_data["papers"] = papers
    papers_data["updated"] = utc_now()[:10]
    save_json(PAPERS_FILE, papers_data)

    RAW.mkdir(parents=True, exist_ok=True)
    raw_path = RAW / f"{utc_now()[:10]}-discovered-{slugify(entry['title'])}.md"
    raw_path.write_text(
        f"# {entry['title']}\n\n"
        f"**Discovered:** {entry['discovered_at']}\n"
        f"**Source:** {entry.get('source')}\n"
        f"**URL:** {entry.get('url')}\n"
        f"**Relevance score:** {entry.get('relevance_score')}\n"
        f"**Status:** needs_review\n\n"
        f"---\n\nAuto-captured by evidence watch agent. Review and merge into trials.json if confirmed relevant.\n",
        encoding="utf-8",
    )
    entry["raw"] = str(raw_path.relative_to(ROOT)).replace("\\", "/")
    return entry


def run_full_scan() -> dict:
    """Validate, search PubMed + CT.gov, refresh watched trials, add new hits."""
    started = utc_now()
    validation = validate_datasets()
    keys = existing_keys()

    new_hits: list[dict] = []
    all_search_hits: list[dict] = []

    for q in SEARCH_QUERIES:
        for hit in search_ctgov(q):
            if hit.get("error"):
                continue
            all_search_hits.append(hit)
            if not is_duplicate(hit, keys):
                hit["relevance_score"] = score_relevance(hit)
                if hit["relevance_score"] >= 25:
                    new_hits.append(hit)

    pubmed_hits = search_pubmed()
    for hit in pubmed_hits:
        if hit.get("error"):
            continue
        all_search_hits.append(hit)
        if not is_duplicate(hit, keys):
            hit["relevance_score"] = score_relevance(hit)
            if hit["relevance_score"] >= 20:
                new_hits.append(hit)

    # Deduplicate new_hits by url/nct
    seen: set[str] = set()
    unique_new: list[dict] = []
    for h in sorted(new_hits, key=lambda x: -x.get("relevance_score", 0)):
        key = (h.get("nct_id") or h.get("url") or h.get("title", "")).lower()
        if key not in seen:
            seen.add(key)
            unique_new.append(h)

    added = []
    for hit in unique_new[:10]:
        entry = add_paper_stub(hit)
        added.append(entry)
        if hit.get("url"):
            keys.add(hit["url"].lower())
        if hit.get("nct_id"):
            keys.add(hit["nct_id"].upper())

    trial_updates = refresh_watched_trials()

    report = {
        "started_at": started,
        "finished_at": utc_now(),
        "validation": validation,
        "searched_queries": SEARCH_QUERIES + [PUBMED_QUERY[:80] + "..."],
        "total_search_hits": len(all_search_hits),
        "new_candidates": len(unique_new),
        "added_to_papers_index": added,
        "trial_refresh": trial_updates,
        "summary": (
            f"Validated {validation['trial_count']} trials. "
            f"Found {len(unique_new)} new candidates, added {len(added)} to papers_index (needs_review). "
            f"Refreshed {len(trial_updates)} watched NCT IDs."
        ),
    }
    append_log({"type": "full_scan", **report})
    return report
