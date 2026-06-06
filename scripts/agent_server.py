#!/usr/bin/env python3
"""
MIBC evidence agent API server.
Local UI + REST API for Lovable live integration.

Usage:
  python scripts/agent_server.py
  python scripts/agent_server.py --port 8765 --no-browser

Lovable: set VITE_AGENT_API_URL to your public URL (ngrok) + AGENT_API_KEY in both .env files.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "scripts"))

from env_config import agent_api_key, agent_host, agent_port, cors_origins, load_dotenv  # noqa: E402

load_dotenv()

from agent_core import (  # noqa: E402
    DATA,
    append_log,
    approve_paper,
    list_pending_for_review,
    list_pending_papers,
    reject_paper,
    load_json,
    refresh_watched_trials,
    run_full_scan,
    search_ctgov,
    search_pubmed,
    validate_datasets,
)

SCAN_LOCK = threading.Lock()
LAST_RESULT: dict = {"status": "idle", "message": "Ready.", "progress": 0.0}
CORS = cors_origins()
API_KEY = agent_api_key()

# Map internal status -> Lovable contract (state: idle|running|complete|error)
_STATE_MAP = {"idle": "idle", "running": "running", "done": "complete", "error": "error", "busy": "running", "started": "running"}


def _last_run_iso() -> str | None:
    log = load_json(DATA / "agent_log.json")
    runs = log.get("runs") or []
    if not runs:
        return None
    run = runs[0]
    return run.get("finished_at") or run.get("started_at")


def _format_agent() -> dict:
    s = LAST_RESULT.get("status", "idle")
    return {
        "state": _STATE_MAP.get(s, s),
        "status": s,  # legacy
        "message": LAST_RESULT.get("message", ""),
        "progress": LAST_RESULT.get("progress", 0.0 if s == "idle" else (1.0 if s == "done" else 0.5)),
        "result": LAST_RESULT.get("result"),
    }


def _format_status_payload() -> dict:
    trials = load_json(DATA / "trials.json")
    papers = load_json(DATA / "papers_index.json")
    pending = list_pending_papers()
    return {
        "agent": _format_agent(),
        "last_run": _last_run_iso(),
        "counts": {
            "trials": len(trials.get("trials", [])),
            "papers": len(papers.get("papers", [])),
            "pending": len(pending),
        },
        # legacy fields for agentApi.ts
        "meta": trials.get("meta", {}),
        "trial_count": len(trials.get("trials", [])),
        "paper_count": len(papers.get("papers", [])),
        "pending_review_count": len(pending),
        "pending_papers": [_format_pending_item(p) for p in pending[:10]],
        "last_runs": (load_json(DATA / "agent_log.json").get("runs") or [])[:5],
    }


def _format_pending_item(p: dict) -> dict:
    raw_year = p.get("year") or (p.get("pubdate") or p.get("discovered_at") or "")[:4]
    year = int(raw_year) if str(raw_year).isdigit() else None
    return {
        "id": p.get("id", ""),
        "ref": p.get("title") or p.get("id", ""),
        "topic": p.get("type"),
        "year": year,
        "relevance_score": p.get("relevance_score"),
        "status": p.get("status", "needs_review"),
        "source_url": p.get("url"),
        "reason": p.get("source"),
    }


class AgentHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[agent] {self.address_string()} {format % args}")

    def _cors_origin(self) -> str:
        origin = self.headers.get("Origin", "")
        if CORS == "*":
            return "*"
        allowed = [o.strip() for o in CORS.split(",") if o.strip()]
        return origin if origin in allowed else (allowed[0] if allowed else "*")

    def _host_is_local(self) -> bool:
        host = (self.headers.get("Host") or "").lower()
        if host.startswith("[::1]"):
            return True
        hostname = host.rsplit(":", 1)[0].strip("[]")
        return hostname in ("127.0.0.1", "localhost", "::1")

    def _check_auth(self) -> bool:
        if not API_KEY:
            return True
        if self._host_is_local():
            return True
        provided = self.headers.get("X-API-Key", "") or self.headers.get("x-api-key", "")
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            provided = provided or auth[7:]
        return provided == API_KEY

    def _send_json(self, data: dict | list, status: int = 200) -> None:
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_index(self) -> None:
        path = WEB / "index.html"
        if not path.exists():
            self.send_error(404)
            return
        html = path.read_text(encoding="utf-8")
        # Local admin UI: auto-provide API key so localhost never shows Unauthorized
        if self._host_is_local() and API_KEY:
            inject = (
                f'<script>sessionStorage.setItem("mibc_agent_api_key",'
                f'{json.dumps(API_KEY)});</script>'
            )
            html = html.replace("</head>", inject + "\n</head>")
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _unauthorized(self) -> None:
        self._send_json({"error": "Unauthorized. Set X-API-Key header."}, 401)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/health":
            self._send_json({"ok": True})
            return

        if path in ("/", "/index.html"):
            self._send_index()
            return

        if path.startswith("/api/") and not self._check_auth():
            self._unauthorized()
            return

        if path == "/api/status":
            self._send_json(_format_status_payload())
            return

        if path == "/api/trials":
            data = load_json(DATA / "trials.json")
            # Lovable contract: array of trials; ?wrap=1 returns full file
            if urlparse(self.path).query == "wrap=1":
                self._send_json(data)
            else:
                self._send_json(data.get("trials", []))
            return

        if path == "/api/papers":
            data = load_json(DATA / "papers_index.json")
            if urlparse(self.path).query == "wrap=1":
                self._send_json(data)
            else:
                self._send_json(data.get("papers", []))
            return

        if path == "/api/pending":
            if urlparse(self.path).query == "simple=1":
                self._send_json([_format_pending_item(p) for p in list_pending_papers()])
            else:
                self._send_json(list_pending_for_review())
            return

        if path == "/api/interpretations":
            self._send_json(load_json(DATA / "interpretations.json"))
            return

        if path == "/api/patient-profile":
            self._send_json(load_json(DATA / "patient_profile.json"))
            return

        if path == "/api/glossary-pathway":
            self._send_json(load_json(DATA / "glossary_pathway.json"))
            return

        if path == "/api/patients-like-you":
            self._send_json(load_json(DATA / "patients_like_you.json"))
            return

        if path == "/api/dashboard-charts":
            self._send_json(load_json(DATA / "dashboard_charts.json"))
            return

        if path == "/api/validate":
            self._send_json(validate_datasets())
            return

        self.send_error(404)

    def do_POST(self) -> None:
        global LAST_RESULT
        path = urlparse(self.path).path

        if path == "/api/health":
            self.do_GET()
            return

        if path.startswith("/api/") and not self._check_auth():
            self._unauthorized()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            payload = {}

        if path == "/api/search":
            if not SCAN_LOCK.acquire(blocking=False):
                self._send_json({"agent": _format_agent(), "error": "Scan already running."}, 409)
                return

            def run_scan():
                global LAST_RESULT
                try:
                    LAST_RESULT = {"status": "running", "message": "Searching PubMed and ClinicalTrials.gov...", "progress": 0.2}
                    result = run_full_scan()
                    LAST_RESULT = {"status": "done", "message": result["summary"], "progress": 1.0, "result": result}
                except Exception as exc:
                    LAST_RESULT = {"status": "error", "message": str(exc), "progress": 0.0}
                    append_log({"type": "error", "error": str(exc)})
                finally:
                    SCAN_LOCK.release()

            LAST_RESULT = {"status": "running", "message": "Starting evidence search...", "progress": 0.1}
            threading.Thread(target=run_scan, daemon=True).start()
            self._send_json(_format_status_payload())
            return

        if path == "/api/refresh":
            if not SCAN_LOCK.acquire(blocking=False):
                self._send_json({"agent": _format_agent(), "error": "Agent busy."}, 409)
                return

            def run_refresh():
                global LAST_RESULT
                try:
                    LAST_RESULT = {"status": "running", "message": "Refreshing watched ClinicalTrials.gov records...", "progress": 0.3}
                    updates = refresh_watched_trials()
                    LAST_RESULT = {
                        "status": "done",
                        "message": f"Refreshed {len(updates)} watched trials.",
                        "progress": 1.0,
                        "result": {"updates": updates},
                    }
                except Exception as exc:
                    LAST_RESULT = {"status": "error", "message": str(exc), "progress": 0.0}
                    append_log({"type": "error", "error": str(exc)})
                finally:
                    SCAN_LOCK.release()

            LAST_RESULT = {"status": "running", "message": "Starting trial refresh...", "progress": 0.1}
            threading.Thread(target=run_refresh, daemon=True).start()
            self._send_json(_format_status_payload())
            return

        if path == "/api/approve":
            paper_id = payload.get("paper_id", "")
            if not paper_id:
                self._send_json({"error": "paper_id required"}, 400)
                return
            result = approve_paper(paper_id)
            if not result.get("ok"):
                self._send_json(result, 404)
                return
            papers = load_json(DATA / "papers_index.json").get("papers", [])
            paper = next((p for p in papers if p.get("id") == paper_id), {})
            self._send_json(_format_pending_item(paper))
            return

        if path == "/api/reject":
            paper_id = payload.get("paper_id", "")
            if not paper_id:
                self._send_json({"error": "paper_id required"}, 400)
                return
            reason = payload.get("reason", "")
            result = reject_paper(paper_id, reason=reason)
            self._send_json(result, 200 if result.get("ok") else 404)
            return

        if path == "/api/search-pubmed":
            q = payload.get("query", "")
            hits = search_pubmed(q) if q else search_pubmed()
            self._send_json({"hits": hits})
            return

        if path == "/api/search-ctgov":
            q = payload.get("query", "muscle invasive bladder cancer node positive")
            hits = search_ctgov(q)
            self._send_json({"hits": hits})
            return

        self.send_error(404)


def main() -> None:
    parser = argparse.ArgumentParser(description="MIBC evidence agent API server")
    parser.add_argument("--port", type=int, default=agent_port())
    parser.add_argument("--host", type=str, default=agent_host())
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    WEB.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), AgentHandler)
    local = f"http://127.0.0.1:{args.port}"
    print(f"Evidence agent API: {local}")
    print(f"  GET  /api/health   (no auth)")
    print(f"  GET  /api/status   (trials, papers, agent state)")
    print(f"  POST /api/search   (run full scan)")
    print(f"  POST /api/refresh  (update watched NCT trials)")
    print(f"  POST /api/approve  ({{\"paper_id\": \"...\"}})")
    print(f"  POST /api/reject   ({{\"paper_id\": \"...\", \"reason\": \"optional\"}})")
    print(f"  GET  /api/pending  (review queue with scope hints)")
    if API_KEY:
        print("  Auth: X-API-Key header required on /api/* (except /api/health)")
    else:
        print("  WARNING: AGENT_API_KEY not set — API is open. Add to .env for Lovable.")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(local)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
