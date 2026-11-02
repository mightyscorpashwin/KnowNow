"""Exercises the MCP client against a local fake server speaking streamable HTTP."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from knownow.learn_mcp import LearnMcpClient, McpError, normalize_search_result, parse_sse


class FakeMcp(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeMcp.calls.append((body.get("method"), self.headers.get("Mcp-Session-Id")))
        if "id" not in body:
            self.send_response(202)
            self.end_headers()
            return
        if body["method"] == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}}
        elif body["params"]["name"] == "microsoft_docs_search":
            hits = [{"title": "Compute", "content": "excerpt", "contentUrl": "https://learn.microsoft.com/a"}]
            result = {"content": [{"type": "text", "text": json.dumps(hits)}]}
        elif body["params"]["name"] == "microsoft_docs_fetch":
            result = {"content": [{"type": "text", "text": "# Page\nBody"}]}
        else:
            result = {"content": [{"type": "text", "text": "boom"}], "isError": True}
        msg = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})
        payload = f"event: message\ndata: {msg}\n\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Mcp-Session-Id", "sess-1")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture()
def server():
    FakeMcp.calls = []
    httpd = HTTPServer(("127.0.0.1", 0), FakeMcp)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}/api/mcp"
    httpd.shutdown()


def test_search_and_fetch_round_trip(server):
    client = LearnMcpClient(server, timeout=5)
    hits = client.search("azure compute")
    assert hits[0].url == "https://learn.microsoft.com/a" and hits[0].title == "Compute"
    assert client.fetch("https://learn.microsoft.com/a").startswith("# Page")
    methods = [m for m, _ in FakeMcp.calls]
    assert methods == ["initialize", "notifications/initialized", "tools/call", "tools/call"]
    # session id echoed after initialize
    assert all(sid == "sess-1" for _, sid in FakeMcp.calls[1:])


def test_tool_error_raises(server):
    client = LearnMcpClient(server, timeout=5)
    with pytest.raises(McpError):
        client.call_tool("unknown_tool", {})


def test_parse_sse_multiple_events():
    body = 'data: {"id": 1}\n\nevent: x\ndata: {"id": 2}\n\n'
    assert [m["id"] for m in parse_sse(body)] == [1, 2]


def test_normalize_handles_shapes():
    structured = {"structuredContent": {"results": [{"title": "T", "url": "https://u", "content": "c"}]}}
    assert normalize_search_result(structured)[0].url == "https://u"
    wrapped = {"content": [{"type": "text", "text": json.dumps({"results": [{"title": "T", "contentUrl": "https://v", "content": "c"}]})}]}
    assert normalize_search_result(wrapped)[0].url == "https://v"
    plain = {"content": [{"type": "text", "text": "just text"}]}
    assert normalize_search_result(plain)[0].content == "just text"
