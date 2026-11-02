"""KnowNow API and content pipeline (Azure Functions, Python v2 model).

HTTP routes are reached through the Static Web App at /api/*, which signs the
user in with Entra ID and forwards the identity.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache

import azure.durable_functions as df
import azure.functions as func

from knownow.auth import is_reviewer, parse_principal, roles_for_login
from knownow.catalog import Target, iter_targets
from knownow.config import load_settings
from knownow.content import generate_draft
from knownow.page_schema import validate_page

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)
log = logging.getLogger("knownow")

ORCHESTRATOR = "content_refresh"
BATCH_SIZE = 4


# ---------------------------------------------------------------------------
# Shared clients (created once per worker)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def settings():
    return load_settings()


@lru_cache(maxsize=1)
def repo():
    from knownow.repository import Repository

    s = settings()
    return Repository(s.cosmos_endpoint, s.cosmos_database)


@lru_cache(maxsize=1)
def chat():
    from knownow.drafting import make_azure_openai_client

    s = settings()
    return make_azure_openai_client(s.openai_endpoint, s.openai_deployment, s.openai_api_version)


def json_response(body, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(body, default=str), status_code=status, mimetype="application/json")


def error(status: int, message: str) -> func.HttpResponse:
    return json_response({"error": message}, status)


def caller(req: func.HttpRequest):
    return parse_principal(req.headers.get("x-ms-client-principal"))


def require_reviewer(req: func.HttpRequest):
    """Return (principal, None) for a reviewer, else (None, error response)."""
    principal = caller(req)
    s = settings()
    if principal is None or not principal.is_authenticated:
        return None, error(401, "Sign in required")
    if not is_reviewer(principal, s.reviewer_emails, s.reviewer_group_id):
        return None, error(403, "Reviewer access required")
    return principal, None


# ---------------------------------------------------------------------------
# Reader endpoints
# ---------------------------------------------------------------------------
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return json_response({"status": "ok", "environment": settings().environment})


@app.route(route="me", methods=["GET"])
def me(req: func.HttpRequest) -> func.HttpResponse:
    principal = caller(req)
    if principal is None:
        return error(401, "Sign in required")
    s = settings()
    return json_response(
        {
            "name": principal.user_details,
            "isReviewer": is_reviewer(principal, s.reviewer_emails, s.reviewer_group_id),
        }
    )


@app.route(route="GetRoles", methods=["POST"])
def get_roles(req: func.HttpRequest) -> func.HttpResponse:
    """Static Web Apps 'rolesSource': adds the reviewer role at sign-in."""
    try:
        payload = req.get_json()
    except ValueError:
        payload = {}
    s = settings()
    return json_response({"roles": roles_for_login(payload or {}, s.reviewer_emails, s.reviewer_group_id)})


@app.route(route="topics", methods=["GET"])
def list_topics(req: func.HttpRequest) -> func.HttpResponse:
    topics = repo().ensure_catalog()
    return json_response(
        [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t.get("description", ""),
                "subtopicCount": len(t.get("subtopics", [])),
            }
            for t in topics
        ]
    )


@app.route(route="topics/{topicId}", methods=["GET"])
def get_topic(req: func.HttpRequest) -> func.HttpResponse:
    topic_id = req.route_params["topicId"]
    topic = repo().get_topic(topic_id)
    if topic is None:
        return error(404, "Topic not found")
    published = {p["pageId"] for p in repo().published_pages(topic_id)}
    for sub in topic.get("subtopics", []):
        for area in sub.get("areas", []):
            area["published"] = f"{sub['id']}--{area['id']}" in published
    return json_response(topic)


@app.route(route="topics/{topicId}/pages/{pageId}", methods=["GET"])
def get_page(req: func.HttpRequest) -> func.HttpResponse:
    page = repo().get_page(req.route_params["topicId"], req.route_params["pageId"])
    if page is None or page.get("status") != "approved":
        return error(404, "This page has not been published yet")
    return json_response(page)


# ---------------------------------------------------------------------------
# Reviewer endpoints
# ---------------------------------------------------------------------------
@app.route(route="admin/drafts", methods=["GET"])
def list_drafts(req: func.HttpRequest) -> func.HttpResponse:
    _, denied = require_reviewer(req)
    if denied:
        return denied
    return json_response(repo().list_drafts())


@app.route(route="admin/drafts/{topicId}/{pageId}", methods=["GET"])
def get_draft(req: func.HttpRequest) -> func.HttpResponse:
    _, denied = require_reviewer(req)
    if denied:
        return denied
    draft = repo().get_page(req.route_params["topicId"], req.route_params["pageId"] + "--draft")
    if draft is None:
        return error(404, "Draft not found")
    return json_response(draft)


@app.route(route="admin/drafts/{topicId}/{pageId}/approve", methods=["POST"])
def approve_draft(req: func.HttpRequest) -> func.HttpResponse:
    principal, denied = require_reviewer(req)
    if denied:
        return denied
    try:
        page = repo().approve(req.route_params["topicId"], req.route_params["pageId"], principal.user_details)
    except KeyError:
        return error(404, "Draft not found")
    log.info("Page %s approved by %s", page["pageId"], principal.user_details)
    return json_response({"pageId": page["pageId"], "status": "approved"})


@app.route(route="admin/drafts/{topicId}/{pageId}/reject", methods=["POST"])
def reject_draft(req: func.HttpRequest) -> func.HttpResponse:
    principal, denied = require_reviewer(req)
    if denied:
        return denied
    try:
        body = req.get_json() or {}
    except ValueError:
        body = {}
    comment = str(body.get("comment", ""))[:1000]
    try:
        repo().reject(req.route_params["topicId"], req.route_params["pageId"], principal.user_details, comment)
    except KeyError:
        return error(404, "Draft not found")
    return json_response({"pageId": req.route_params["pageId"], "status": "rejected"})


@app.route(route="admin/catalog/sync", methods=["POST"])
def sync_catalog(req: func.HttpRequest) -> func.HttpResponse:
    _, denied = require_reviewer(req)
    if denied:
        return denied
    docs = repo().sync_catalog()
    return json_response({"topics": len(docs)})


@app.route(route="admin/generate", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_generation(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    """Body: {"topicId": "...", "subtopicId": "...", "areaId": "..."} (all optional)."""
    _, denied = require_reviewer(req)
    if denied:
        return denied
    try:
        body = req.get_json() or {}
    except ValueError:
        body = {}
    scope = {k: body[k] for k in ("topicId", "subtopicId", "areaId") if body.get(k)}
    instance_id = await client.start_new(ORCHESTRATOR, None, scope)
    return json_response({"instanceId": instance_id}, 202)


@app.route(route="admin/generate/{instanceId}", methods=["GET"])
@app.durable_client_input(client_name="client")
async def generation_status(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    _, denied = require_reviewer(req)
    if denied:
        return denied
    status = await client.get_status(req.route_params["instanceId"])
    if status is None or status.runtime_status is None:
        return error(404, "Run not found")
    return json_response(
        {
            "status": status.runtime_status.value,
            "output": status.output,
            "customStatus": status.custom_status,
        }
    )


# ---------------------------------------------------------------------------
# Content pipeline (Durable Functions)
# ---------------------------------------------------------------------------
@app.timer_trigger(schedule="%CONTENT_REFRESH_SCHEDULE%", arg_name="timer", run_on_startup=False)
@app.durable_client_input(client_name="client")
async def scheduled_refresh(timer: func.TimerRequest, client: df.DurableOrchestrationClient) -> None:
    instance_id = await client.start_new(ORCHESTRATOR, None, {})
    log.info("Scheduled content refresh started: %s", instance_id)


@app.orchestration_trigger(context_name="context", orchestration=ORCHESTRATOR)
def content_refresh(context: df.DurableOrchestrationContext):
    scope = context.get_input() or {}
    targets = yield context.call_activity("list_targets", scope)
    retry = df.RetryOptions(first_retry_interval_in_milliseconds=30_000, max_number_of_attempts=3)
    results: list[dict] = []
    for start in range(0, len(targets), BATCH_SIZE):
        batch = targets[start : start + BATCH_SIZE]
        context.set_custom_status({"done": len(results), "total": len(targets)})
        tasks = [context.call_activity_with_retry("generate_page", retry, t) for t in batch]
        results.extend((yield context.task_all(tasks)))
    summary = {
        "total": len(results),
        "drafted": sum(1 for r in results if r.get("ok")),
        "failedChecks": [r["pageId"] for r in results if r.get("ok") and not r.get("checksPassed")],
        "errors": [r for r in results if not r.get("ok")],
    }
    context.set_custom_status({"done": len(results), "total": len(targets)})
    return summary


@app.activity_trigger(input_name="scope", activity="list_targets")
def list_targets(scope: dict) -> list[dict]:
    topics = repo().ensure_catalog()
    targets = iter_targets(
        topics,
        topic_id=scope.get("topicId"),
        subtopic_id=scope.get("subtopicId"),
        area_id=scope.get("areaId"),
    )
    return [t.to_dict() for t in targets]


@app.activity_trigger(input_name="target", activity="generate_page")
def generate_page(target: dict) -> dict:
    from knownow.learn_mcp import LearnMcpClient

    t = Target.from_dict(target)
    s = settings()
    try:
        draft = generate_draft(
            t,
            docs=LearnMcpClient(s.learn_mcp_url),
            chat=chat(),
            validate=validate_page,
            model_label=s.openai_deployment,
        )
    except Exception as exc:  # recorded in the run summary; retries happen first
        log.exception("Generation failed for %s", t.page_id)
        return {"pageId": t.page_id, "ok": False, "error": str(exc)[:500]}
    repo().save_draft(draft)
    _snapshot_sources(t.page_id, draft)
    return {"pageId": t.page_id, "ok": True, "checksPassed": draft["checks"]["passed"]}


def _snapshot_sources(page_id: str, draft: dict) -> None:
    """Keep a record of what the draft was built from (best effort)."""
    s = settings()
    if not s.blob_endpoint:
        return
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        blobs = BlobServiceClient(s.blob_endpoint, credential=DefaultAzureCredential())
        stamp = draft["generation"]["generatedAt"].replace(":", "-")
        blobs.get_blob_client("sources", f"{page_id}/{stamp}.json").upload_blob(
            json.dumps(draft["generation"], indent=2), overwrite=True
        )
    except Exception:
        log.warning("Could not save source snapshot for %s", page_id, exc_info=True)

