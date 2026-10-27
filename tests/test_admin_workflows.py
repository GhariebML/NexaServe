"""Static checks for the n8n admin workflows 09 (automation rules), 10 (agent management) and 11 (KB admin)."""
import json
import re
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[1] / "infra" / "n8n" / "workflows"
ADMIN = ["09_automation_rules.json", "10_agent_management.json", "11_kb_admin.json"]


def _workflow(name):
    return json.loads((WORKFLOWS / name).read_text(encoding="utf-8"))


def _node(wf, name):
    return next(n for n in wf["nodes"] if n["name"] == name)


def _targets(wf, source):
    return [[c["node"] for c in branch] for branch in wf["connections"][source]["main"]]


@pytest.mark.parametrize("filename", ADMIN)
def test_postgres_nodes_use_the_canonical_credential(filename):
    for n in _workflow(filename)["nodes"]:
        if n["type"] == "n8n-nodes-base.postgres":
            assert n["credentials"]["postgres"]["id"] == "CS_PG_FINAL_01", n["name"]
            assert "credentials" not in n["parameters"], f"{n['name']}: credential must not live under parameters"


@pytest.mark.parametrize("filename", ADMIN)
def test_queries_never_interpolate_request_data(filename):
    for n in _workflow(filename)["nodes"]:
        if n["type"] == "n8n-nodes-base.postgres":
            query = n["parameters"]["query"]
            assert "{{" not in query, f"{n['name']}: request data must be passed as $n parameters"
            placeholders = set(re.findall(r"\$(\d+)", query))
            if placeholders:
                assert n["parameters"]["options"]["queryReplacement"].startswith("={{ ["), n["name"]
                assert all(re.search(rf"\${p}::text", query) for p in placeholders), f"{n['name']}: cast parameters to text"


def test_automation_rules_use_a_supported_schedule_trigger():
    wf = _workflow("09_automation_rules.json")
    types = {n["type"] for n in wf["nodes"]}
    assert "n8n-nodes-base.scheduleTrigger" in types
    assert "n8n-nodes-base.cronTrigger" not in types
    assert "n8n-nodes-base.respondToWebhook" not in types  # nothing to respond to in a scheduled run


@pytest.mark.parametrize("filename,actions", [
    ("10_agent_management.json", ["register", "status", "assign", "performance"]),
    ("11_kb_admin.json", ["create", "update", "search"]),
])
def test_switch_rules_have_operators_and_an_unsupported_branch(filename, actions):
    router = _node(_workflow(filename), "Route Action")
    assert router["typeVersion"] >= 3
    rules = router["parameters"]["rules"]["values"]
    assert [r["conditions"]["conditions"][0]["rightValue"] for r in rules] == actions
    assert all(r["conditions"]["conditions"][0]["operator"]["operation"] == "equals" for r in rules)
    assert router["parameters"]["options"]["fallbackOutput"] == "extra"


def test_agent_management_routes_each_action_to_its_node():
    wf = _workflow("10_agent_management.json")
    assert _targets(wf, "Route Action") == [["AGENT - Register"], ["AGENT - Update Status"], ["AGENT - Get Available"],
                                            ["AGENT - Performance"], ["Respond Unsupported Action"]]


def test_kb_admin_routes_each_action_to_its_node():
    wf = _workflow("11_kb_admin.json")
    assert _targets(wf, "Route Action") == [["KB - Create"], ["Respond Update Not Supported"], ["KB - Search"],
                                            ["Respond Unsupported Action"]]
    create = _node(wf, "KB - Create")["parameters"]["query"]
    assert "FALSE" in create and "pending review" in create  # drafts stay inactive until approved
    assert "embedding" not in _node(wf, "KB - Search")["parameters"]["query"]


@pytest.mark.parametrize("filename", ["10_agent_management.json", "11_kb_admin.json"])
def test_admin_webhooks_require_the_service_token(filename):
    hook = next(n for n in _workflow(filename)["nodes"] if n["type"] == "n8n-nodes-base.webhook")
    assert hook["parameters"]["authentication"] == "headerAuth"
    assert hook["credentials"]["httpHeaderAuth"]["id"] == "CS_WA_BRIDGE_CRED_01"
