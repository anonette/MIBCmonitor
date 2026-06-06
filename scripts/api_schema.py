"""API response normalization and envelope contract (v1.5)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

API_VERSION = "1.5"
LEGACY_SUNSET = "2026-09-01"
DEPRECATED_FIELDS_REMOVAL = "2026-09-01"

MATCH_TYPE_LABELS = {
    "by_design": "Trial built for node-positive M0",
    "published_subgroup": "Published cN1/cN+ subgroup",
    "published_eligible": "cN1 allowed; subgroup n pending",
    "retrospective_cn_plus": "Retrospective cN+ series",
    "wrong_setting": "Metastatic — wrong clinical pathway",
    "wrong_timing": "Adjuvant pN+ — after surgery",
    "wrong_population": "Wrong population (e.g. cis-unfit only)",
    "none": "No node-positive patients",
    "indirect": "Meta-analysis / indirect",
}

MATCH_TYPES = frozenset(MATCH_TYPE_LABELS.keys())

COPY_STRIP_DASHBOARD_KEYS = frozenset({
    "page_intro",
    "profile_reminder",
    "question",
    "what_it_shows",
    "takeaway",
    "caveats",
    "color_meaning",
})

COPY_STRIP_INTERPRETATION_KEYS = frozenset({
    "ui_copy",
    "talking_points_for_oncologist",
})


def file_updated_at(path: Path) -> str:
    if path.exists():
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_etag(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.md5(raw).hexdigest()  # noqa: S324 — weak hash ok for cache revalidation


def envelope(data: object, source: str, path: Path, count: int | None = None, **meta_extra: object) -> dict:
    """source = logical resource name (trials, papers, …), not filename."""
    if count is None:
        count = infer_count(data)
    body = {
        "data": data,
        "meta": {
            "updated_at": file_updated_at(path),
            "source": source,
            "api_version": API_VERSION,
            "count": count,
        },
    }
    body["meta"]["etag"] = compute_etag(body)
    body["meta"].update(meta_extra)
    return body


def infer_count(data: object) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return len(data["items"])
        if "charts" in data and isinstance(data["charts"], list):
            return len(data["charts"])
        if "glossary" in data and isinstance(data.get("glossary"), list):
            steps = len((data.get("pathway") or {}).get("steps") or [])
            return len(data["glossary"]) + steps
        if "tumor_board_questions" in data:
            n = len(data.get("tumor_board_questions") or [])
            n += len(data.get("sections") or [])
            return n or 1
        if data.get("id") == "target-patient" or "clinical_stage" in data:
            return 1
    return 0


def list_data(items: list, kind: str, legacy_key: str | None = None, **extra: object) -> dict:
    """Canonical list shape: { kind, items, ...extra }."""
    payload: dict = {"kind": kind, "items": items, **extra}
    if legacy_key:
        payload[legacy_key] = items
    return payload


def object_data(kind: str, obj: dict, **extra: object) -> dict:
    return {"kind": kind, "object": obj, **extra}


def empty_efficacy() -> dict:
    return {"primary": [], "subgroups": []}


def _fallback_patient_match(trial: dict) -> dict:
    n = trial.get("cn1_cn_plus_n")
    total = trial.get("total_n") or 0
    pct = round(100 * n / total, 1) if n and total else None
    return {
        "match_type": "none",
        "staging_basis": None,
        "n_like_profile": n if n else 0,
        "pct_of_trial": pct,
        "certainty": "low",
        "certainty_label": "Not enriched",
        "what_we_know": [],
        "what_we_dont_know": [],
        "outcomes_in_subgroup": {},
    }


def normalize_trial(trial: dict, include_deprecated: bool = True) -> dict:
    t = dict(trial)
    if t.get("phase") is not None:
        t["phase"] = str(t["phase"])

    eff = t.get("efficacy")
    if eff is None:
        t["efficacy"] = empty_efficacy()
    elif isinstance(eff, dict):
        t["efficacy"] = {
            "primary": eff.get("primary") or [],
            "subgroups": eff.get("subgroups") or [],
            **{k: v for k, v in eff.items() if k not in ("primary", "subgroups")},
        }

    treatment = t.get("treatment")
    if isinstance(treatment, dict):
        treatment = dict(treatment)
        if treatment.get("comparator") and not treatment.get("control"):
            treatment["control"] = treatment["comparator"]
        elif not include_deprecated and "comparator" in treatment:
            del treatment["comparator"]
        t["treatment"] = treatment

    pm = t.get("patient_match")
    if not pm:
        pm = _fallback_patient_match(t)
    else:
        pm = dict(pm)
        if pm.get("pct_of_trial") is None and pm.get("pct") is not None:
            pm["pct_of_trial"] = pm["pct"]
        if not include_deprecated and "pct" in pm:
            del pm["pct"]
    t["patient_match"] = pm
    return t


def normalize_trials_payload(raw: dict, include_deprecated: bool = True) -> dict:
    file_meta = dict(raw.get("meta") or {})
    trials = [normalize_trial(t, include_deprecated) for t in raw.get("trials", [])]
    categories = raw.get("categories") or []
    return {"trials": trials, "categories": categories, "meta": file_meta}


def normalize_paper(paper: dict, include_deprecated: bool = True) -> dict:
    p = dict(paper)
    p["ref"] = p.get("ref") or p.get("title") or p.get("id", "")
    p["topic"] = p.get("topic") or p.get("type")
    if p.get("year") is None:
        for field in ("year", "pubdate", "discovered_at"):
            val = p.get(field)
            if val and str(val)[:4].isdigit():
                p["year"] = int(str(val)[:4])
                break
    p["source_url"] = p.get("source_url") or p.get("url")
    if not include_deprecated:
        p.pop("type", None)
    return p


def normalize_papers_payload(raw: dict, include_deprecated: bool = True) -> dict:
    updated = raw.get("updated") or raw.get("updated_at")
    papers = [normalize_paper(p, include_deprecated) for p in raw.get("papers", [])]
    return {"papers": papers, "updated": updated}


def normalize_patients_like_you(raw: dict, include_deprecated: bool = True) -> dict:
    rows = []
    for row in raw.get("rows", []):
        r = dict(row)
        if r.get("pct_of_trial") is None and r.get("pct") is not None:
            r["pct_of_trial"] = r["pct"]
        if not include_deprecated:
            r.pop("pct", None)
        rows.append(r)
    extra = {k: v for k, v in raw.items() if k != "rows"}
    return list_data(
        rows,
        "patients_like_you",
        legacy_key="rows" if include_deprecated else None,
        **extra,
    )


def strip_dashboard_copy(raw: dict) -> dict:
    out = {k: v for k, v in raw.items() if k not in ("page_intro", "profile_reminder")}
    legend = raw.get("legend")
    if legend:
        out["legend"] = {k: v for k, v in legend.items() if k in ("fit_tier", "hr_note", "certainty_note")}
    charts = []
    for ch in raw.get("charts", []):
        c = {k: v for k, v in ch.items() if k not in COPY_STRIP_DASHBOARD_KEYS}
        charts.append(c)
    out["charts"] = charts
    return out


def strip_interpretation_copy(raw: dict) -> dict:
    return {k: v for k, v in raw.items() if k not in COPY_STRIP_INTERPRETATION_KEYS}
