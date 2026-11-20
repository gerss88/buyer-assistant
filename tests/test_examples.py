import json

from jsonschema import validate

from conftest import ROOT, run_cli


RESPONSE_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "required": ["status", "options"],
            "additionalProperties": False,
            "properties": {
                "status": {"const": "ok"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["listing_ids", "total_rub", "explanation"],
                        "additionalProperties": False,
                        "properties": {
                            "listing_ids": {"type": "array", "items": {"type": "string"}},
                            "total_rub": {"type": "integer", "minimum": 1},
                            "explanation": {"type": "string"},
                        },
                    },
                },
            },
        },
        {
            "type": "object",
            "required": ["status", "questions"],
            "additionalProperties": False,
            "properties": {
                "status": {"const": "clarify"},
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["field", "text"],
                        "additionalProperties": False,
                        "properties": {"field": {"type": "string"}, "text": {"type": "string"}},
                    },
                },
            },
        },
        {
            "type": "object",
            "required": ["status", "message"],
            "additionalProperties": False,
            "properties": {"status": {"const": "no_match"}, "message": {"type": "string"}},
        },
    ],
}


def test_all_organizer_request_examples_have_contract_responses():
    requests = sorted(ROOT.glob("examples/**/request.json"))
    assert requests, "No request.json examples found"
    for request_path in requests:
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
        completed = run_cli(request_data)
        response = json.loads(completed.stdout)
        validate(instance=response, schema=RESPONSE_SCHEMA)

        expected_response_path = request_path.with_name("response.json")
        if expected_response_path.exists():
            expected = json.loads(expected_response_path.read_text(encoding="utf-8"))
            assert response["status"] == expected["status"], request_path
            if expected["status"] == "clarify":
                assert [item["field"] for item in response["questions"]] == [
                    item["field"] for item in expected["questions"]
                ]


def test_gitignore_excludes_local_secrets_and_virtualenv():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored
    assert ".env.local" in ignored
    assert ".venv/" in ignored
