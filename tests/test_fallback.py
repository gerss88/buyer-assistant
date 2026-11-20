import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from conftest import run_cli


REQUEST = {
    "messages": [{
        "role": "user",
        "text": "Стол не шире метра, кресло и лампа. Таганрог. До 15 000 ₽ за всё.",
    }]
}


class _Handler(BaseHTTPRequestHandler):
    response_body = b""
    status = 200

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.response_body)

    def log_message(self, *_args):
        pass


def _run_with_api(body, status=200):
    _Handler.response_body = body
    _Handler.status = status
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return run_cli(REQUEST, env={
            "LLM_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
            "LLM_MODEL": "test-model",
            "LLM_API_KEY": "test-key",
            "LLM_TIMEOUT_SECONDS": "2",
        })
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_http_error_falls_back_to_regex():
    completed = _run_with_api(b'{"error":"unavailable"}', status=503)
    output = json.loads(completed.stdout)
    assert output["status"] == "ok"
    assert output["options"][0]["listing_ids"] == ["demo-1-1-10", "demo-1-2-05", "demo-1-3-04"]


def test_network_error_falls_back_to_regex():
    completed = run_cli(REQUEST, env={
        "LLM_BASE_URL": "http://127.0.0.1:1/v1",
        "LLM_MODEL": "test-model",
        "LLM_API_KEY": "test-key",
        "LLM_TIMEOUT_SECONDS": "1",
    })
    output = json.loads(completed.stdout)
    assert output["status"] == "ok"
    assert output["options"][0]["listing_ids"] == ["demo-1-1-10", "demo-1-2-05", "demo-1-3-04"]


def test_invalid_model_json_falls_back_to_regex():
    response = json.dumps({"choices": [{"message": {"content": "not json"}}]}).encode()
    completed = _run_with_api(response)
    output = json.loads(completed.stdout)
    assert output["status"] == "ok"
    assert output["options"][0]["listing_ids"] == ["demo-1-1-10", "demo-1-2-05", "demo-1-3-04"]


def test_invalid_model_structure_falls_back_to_regex():
    content = json.dumps({
        "city_id": "not-a-city",
        "budget_rub": 15000,
        "categories": ["table", "chair", "lamp"],
        "constraints": {},
        "missing": [],
    })
    response = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
    completed = _run_with_api(response)
    output = json.loads(completed.stdout)
    assert output["status"] == "ok"
    assert output["options"][0]["listing_ids"] == ["demo-1-1-10", "demo-1-2-05", "demo-1-3-04"]
