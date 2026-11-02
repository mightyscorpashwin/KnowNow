"""KnowNow local demo server — no Azure needed.

Serves the same /api routes as the Function App, backed by an in-memory store
with one published sample page. "Draft pages" creates demo drafts instantly so
you can try the review flow. Optionally serves the built web app too.

    python devserver.py                      # API on http://localhost:7071
    python devserver.py --web ../web/dist    # API + web on one port
    DEMO_USER=asha@contoso.com python devserver.py

Set DEMO_REVIEWER=false to see the app as a reader.

If AZURE_OPENAI_ENDPOINT is set (and `az login` has access), drafting uses the
real pipeline: Microsoft Learn MCP + Azure OpenAI.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from knownow.auth import is_reviewer, parse_principal
from knownow.catalog import Target, iter_targets
from knownow.config import load_settings
from knownow.memory_repo import InMemoryRepository
from knownow.page_schema import validate_page
from knownow.sample_pages import COMPUTE_SOURCE, demo_page

DEMO_USER = os.environ.get("DEMO_USER", "demo.reviewer@contoso.com")
DEMO_REVIEWER = os.environ.get("DEMO_REVIEWER", "true").lower() != "false"

REPO = InMemoryRepository()
SETTINGS = load_settings()
REVIEWERS = SETTINGS.reviewer_emails | ({DEMO_USER.lower()} if DEMO_REVIEWER else set())
RUNS: dict[str, dict] = {}


def demo_principal_header() -> str:
    data = {
        "identityProvider": "aad",
        "userId": "demo-user",
        "userDetails": DEMO_USER,
        "userRoles": ["anonymous", "authenticated"],
        "claims": [],
    }
    return base64.b64encode(json.dumps(data).encode()).decode()


# ---------------------------------------------------------------------------
# Drafting: demo (instant) or real (Learn MCP + Azure OpenAI)
# ---------------------------------------------------------------------------
def make_drafter():
    if SETTINGS.openai_endpoint:
        from knownow.content import generate_draft
        from knownow.drafting import make_azure_openai_client
        from knownow.learn_mcp import LearnMcpClient

        chat = make_azure_openai_client(SETTINGS.openai_endpoint, SETTINGS.openai_deployment, SETTINGS.openai_api_version)

        def real(t: Target) -> dict:
            return generate_draft(t, LearnMcpClient(SETTINGS.learn_mcp_url), chat, validate_page, SETTINGS.openai_deployment)

        return real, "azure-openai"

    def demo(t: Target) -> dict:
        time.sleep(0.6)  # make progress visible
        page = demo_page(t)
        problems = validate_page(page, [COMPUTE_SOURCE])
        return {
            "id": f"{t.page_id}--draft",
            "pageId": t.page_id,
            "topicId": t.topic_id,
            "subtopicId": t.subtopic_id,
            "areaId": t.area_id,
            "areaName": t.area_name,
            "status": "draft",
            "content": page,
            "checks": {"passed": not problems, "problems": problems},
            "generation": {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "model": "demo",
                "promptVersion": "demo",
                "query": t.query,
                "fetchedSources": [{"title": "Choose an Azure compute service", "url": COMPUTE_SOURCE}],
            },
        }

    return demo, "demo"


DRAFT, DRAFT_MODE = make_drafter()


def run_generation(run_id: str, scope: dict) -> None:
    run = RUNS[run_id]
    targets = iter_targets(REPO.ensure_catalog(), scope.get("topicId"), scope.get("subtopicId"), scope.get("areaId"))
    run["customStatus"] = {"done": 0, "total": len(targets)}
    errors, drafted, failed = [], 0, []
    for i, t in enumerate(targets, 1):
        try:
            draft = DRAFT(t)
            REPO.save_draft(draft)
            drafted += 1
            if not draft["checks"]["passed"]:
                failed.append(t.page_id)
        except Exception as exc:  # noqa: BLE001 - reported in the run summary
            errors.append({"pageId": t.page_id, "error": str(exc)[:300]})
        run["customStatus"] = {"done": i, "total": len(targets)}
    run["output"] = {"total": len(targets), "drafted": drafted, "failedChecks": failed, "errors": errors}
    run["status"] = "Completed"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    web_root: Path | None = None
    server_version = "KnowNowDemo/1.0"

    def log_message(self, fmt, *args):  # quieter log
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    # helpers
    def send_json(self, body, status: int = 200) -> None:
        data = json.dumps(body, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except ValueError:
            return {}

    def principal(self):
        return parse_principal(self.headers.get("x-ms-client-principal") or demo_principal_header())

    def reviewer(self):
        p = self.principal()
        if not is_reviewer(p, frozenset(REVIEWERS), SETTINGS.reviewer_group_id):
            self.send_json({"error": "Reviewer access required"}, 403)
            return None
        return p

    # routing
    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def route(self, method: str) -> None:
        path = unquote(urlsplit(self.path).path)
        if path.startswith("/api/"):
            return self.api(method, path[5:].rstrip("/"))
        if method == "GET" and self.web_root:
            return self.static(path)
        self.send_json({"error": "Not found"}, 404)

    def api(self, method: str, route: str) -> None:
        m = lambda pattern: re.fullmatch(pattern, route)  # noqa: E731

        if method == "GET" and route == "health":
            return self.send_json({"status": "ok", "environment": "local-demo", "drafting": DRAFT_MODE})
        if method == "GET" and route == "me":
            p = self.principal()
            return self.send_json(
                {"name": p.user_details, "isReviewer": is_reviewer(p, frozenset(REVIEWERS), SETTINGS.reviewer_group_id)}
            )
        if method == "GET" and route == "topics":
            return self.send_json(
                [
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "subtopicCount": len(t.get("subtopics", [])),
                    }
                    for t in REPO.ensure_catalog()
                ]
            )
        if method == "GET" and (g := m(r"topics/([\w-]+)")):
            topic = REPO.get_topic(g[1])
            if topic is None:
                return self.send_json({"error": "Topic not found"}, 404)
            published = {p["pageId"] for p in REPO.published_pages(g[1])}
            for sub in topic.get("subtopics", []):
                for area in sub.get("areas", []):
                    area["published"] = f"{sub['id']}--{area['id']}" in published
            return self.send_json(topic)
        if method == "GET" and (g := m(r"topics/([\w-]+)/pages/([\w-]+)")):
            page = REPO.get_page(g[1], g[2])
            if page is None or page.get("status") != "approved":
                return self.send_json({"error": "This page has not been published yet"}, 404)
            return self.send_json(page)

        # reviewer routes
        if route.startswith("admin/"):
            p = self.reviewer()
            if p is None:
                return None
            if method == "GET" and route == "admin/drafts":
                return self.send_json(REPO.list_drafts())
            if method == "GET" and (g := m(r"admin/drafts/([\w-]+)/([\w-]+)")):
                d = REPO.get_page(g[1], g[2] + "--draft")
                return self.send_json(d) if d else self.send_json({"error": "Draft not found"}, 404)
            if method == "POST" and (g := m(r"admin/drafts/([\w-]+)/([\w-]+)/(approve|reject)")):
                try:
                    if g[3] == "approve":
                        REPO.approve(g[1], g[2], p.user_details)
                    else:
                        REPO.reject(g[1], g[2], p.user_details, str(self.body().get("comment", ""))[:1000])
                except KeyError:
                    return self.send_json({"error": "Draft not found"}, 404)
                return self.send_json({"pageId": g[2], "status": "approved" if g[3] == "approve" else "rejected"})
            if method == "POST" and route == "admin/catalog/sync":
                return self.send_json({"topics": len(REPO.sync_catalog())})
            if method == "POST" and route == "admin/generate":
                body = self.body()
                scope = {k: body[k] for k in ("topicId", "subtopicId", "areaId") if body.get(k)}
                run_id = uuid.uuid4().hex
                RUNS[run_id] = {"status": "Running", "customStatus": {"done": 0, "total": 0}, "output": None}
                threading.Thread(target=run_generation, args=(run_id, scope), daemon=True).start()
                return self.send_json({"instanceId": run_id}, 202)
            if method == "GET" and (g := m(r"admin/generate/(\w+)")):
                run = RUNS.get(g[1])
                return self.send_json(run) if run else self.send_json({"error": "Run not found"}, 404)
        self.send_json({"error": "Not found"}, 404)

    def static(self, path: str) -> None:
        root = self.web_root
        target = (root / path.lstrip("/")).resolve()
        if root not in target.parents and target != root or not target.is_file():
            target = root / "index.html"  # single-page app fallback
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=7071)
    parser.add_argument("--web", type=Path, help="Folder with the built web app (web/dist)")
    args = parser.parse_args()
    if args.web:
        Handler.web_root = args.web.resolve()
    print(f"KnowNow demo on http://localhost:{args.port}  (user: {DEMO_USER}, reviewer: {DEMO_REVIEWER}, drafting: {DRAFT_MODE})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
