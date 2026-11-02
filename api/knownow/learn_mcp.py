"""Minimal client for the Microsoft Learn MCP Server.

The server speaks MCP over "streamable HTTP": JSON-RPC 2.0 requests POSTed to
one URL, answered either as JSON or as a server-sent-event stream. This client
uses only the standard library so it has no SDK version to keep in step with.

Tools used:
  microsoft_docs_search(query) -> excerpts with title and URL
  microsoft_docs_fetch(url)    -> one full page as markdown
"""
from __future__ import annotations

import itertools
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "knownow", "version": "1.0"}


class McpError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    content: str


def parse_sse(body: str) -> list[dict]:
    """Extract JSON-RPC messages from a text/event-stream body."""
    messages: list[dict] = []
    data_lines: list[str] = []
    for line in body.splitlines() + [""]:
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line == "" and data_lines:
            try:
                messages.append(json.loads("\n".join(data_lines)))
            except ValueError:
                log.warning("Skipping malformed SSE event")
            data_lines = []
    return messages


def normalize_search_result(result: dict) -> list[SearchHit]:
    """Turn a tools/call result into search hits. Accepts the shapes the server
    has used: structuredContent, a JSON array in text, or {"results": [...]}."""
    candidates: list = []
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        candidates = structured.get("results") or structured.get("items") or []
    elif isinstance(structured, list):
        candidates = structured
    if not candidates:
        for block in result.get("content") or []:
            if block.get("type") != "text":
                continue
            text = block.get("text", "")
            try:
                parsed = json.loads(text)
            except ValueError:
                candidates.append({"title": "", "content": text, "url": ""})
                continue
            if isinstance(parsed, dict):
                parsed = parsed.get("results") or parsed.get("items") or [parsed]
            if isinstance(parsed, list):
                candidates.extend(parsed)
    hits: list[SearchHit] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        url = item.get("contentUrl") or item.get("url") or item.get("link") or ""
        hits.append(
            SearchHit(
                title=str(item.get("title", "")).strip(),
                url=str(url).strip(),
                content=str(item.get("content") or item.get("text") or "").strip(),
            )
        )
    return [h for h in hits if h.content or h.url]


def result_text(result: dict) -> str:
    return "\n".join(
        b.get("text", "") for b in result.get("content") or [] if b.get("type") == "text"
    ).strip()


class LearnMcpClient:
    def __init__(self, url: str, timeout: float = 60.0) -> None:
        self.url = url
        self.timeout = timeout
        self._session_id: str | None = None
        self._ids = itertools.count(1)
        self._initialized = False

    # -- transport -----------------------------------------------------------
    def _post(self, payload: dict) -> dict | None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
            "User-Agent": "KnowNow/1.0",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                session = resp.headers.get("Mcp-Session-Id")
                if session:
                    self._session_id = session
                body = resp.read().decode("utf-8", errors="replace")
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            raise McpError(f"Learn MCP HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise McpError(f"Learn MCP unreachable: {exc.reason}") from exc

        if "id" not in payload or not body.strip():
            return None  # notification
        messages = parse_sse(body) if "text/event-stream" in ctype else [json.loads(body)]
        for msg in messages:
            if msg.get("id") == payload["id"]:
                if "error" in msg:
                    raise McpError(f"Learn MCP error: {msg['error']}")
                return msg.get("result", {})
        raise McpError("Learn MCP returned no response for the request")

    def _request(self, method: str, params: dict) -> dict:
        result = self._post({"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params})
        return result or {}

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO},
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._initialized = True

    def call_tool(self, name: str, arguments: dict) -> dict:
        self._ensure_initialized()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise McpError(f"{name} failed: {result_text(result)[:300]}")
        return result

    # -- tools ---------------------------------------------------------------
    def search(self, query: str) -> list[SearchHit]:
        return normalize_search_result(self.call_tool("microsoft_docs_search", {"query": query}))

    def fetch(self, url: str) -> str:
        return result_text(self.call_tool("microsoft_docs_fetch", {"url": url}))
