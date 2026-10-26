"""n8n WhatsApp dispatch, lifecycle hand-off and webhook auth, checked against the workflow exports."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[1] / "infra" / "n8n" / "workflows"
NODE = shutil.which("node")
FALLBACK_ID = "a0000000-0000-0000-0000-000000000001"
UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"
UUID_C = "33333333-3333-3333-3333-333333333333"

RUNNER = r"""
const {code, item, refs} = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const $input = {first: () => ({json: item}), all: () => [{json: item}]};
const $ = (name) => ({first: () => ({json: refs[name] || {}})});
const $execution = {id: 'test'};
process.stdout.write(JSON.stringify(new Function('$input', '$', '$execution', code)($input, $, $execution)[0].json));
"""


def _workflow(name):
    return json.loads((WORKFLOWS / name).read_text(encoding="utf-8"))


def _node(workflow, name):
    return next(n for n in workflow["nodes"] if n["name"] == name)


def _run(workflow_file, node_name, item, refs=None):
    if NODE is None:
        pytest.skip("Node.js is required to execute n8n Code nodes")
    code = _node(_workflow(workflow_file), node_name)["parameters"]["jsCode"]
    result = subprocess.run([NODE, "-e", RUNNER], input=json.dumps({"code": code, "item": item, "refs": refs or {}}),
                            capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(result.stdout)


def _format(item):
    return _run("06_output_channel_dispatcher.json", "Format WhatsApp Payload", item)


# --- 06: only explicit agent replies are sent, never to a placeholder number -----------------

def test_inbound_turns_are_not_dispatched_by_n8n():
    out = _format({"channel": "whatsapp", "phone_number": "+201234567890", "final_reply": "hi"})
    assert out["dispatched"] is False


def test_explicit_dispatch_without_recipient_sends_nothing():
    out = _format({"channel": "whatsapp", "explicit_dispatch": True, "reply": "hi"})
    assert out["dispatched"] is False
    assert out["recipient"] == ""
    assert "966" not in json.dumps(out)


def test_explicit_agent_reply_is_dispatched_with_its_lifecycle_row():
    out = _format({"channel": "whatsapp", "explicit_dispatch": True, "whatsapp_id": "123@lid",
                   "phone_number": "+201234567890", "reply": "Agent answer", "lifecycle_message_id": UUID_A})
    assert out["dispatched"] is True
    assert out["recipient"] == "123@lid"
    assert out["lifecycle_message_id"] == UUID_A


def test_dispatch_node_is_only_reachable_through_the_explicit_gate():
    wf = _workflow("06_output_channel_dispatcher.json")
    targets = {c["node"] for branch in wf["connections"]["Format WhatsApp Payload"]["main"] for c in branch}
    assert "Dispatch WhatsApp Message" not in targets
    gate = wf["connections"]["Explicit Agent Dispatch?"]["main"]
    assert [c["node"] for c in gate[0]] == ["Dispatch WhatsApp Message"] and gate[1] == []
    assert not _node(wf, "Dispatch WhatsApp Message").get("disabled")


# --- 01: lifecycle hand-off is trusted only for WhatsApp with well-formed ids ------------------

def _sanitize(body):
    return _run("01_gateway_dispatcher.json", "Channel Ingress & PII Sanitizer", {"body": body})


def test_whatsapp_without_phone_gets_no_placeholder_number():
    out = _sanitize({"channel": "whatsapp", "customer_message": "hello"})
    assert out["phone_number"] == ""


def test_bridge_lifecycle_ids_are_passed_through():
    out = _sanitize({"channel": "whatsapp", "customer_message": "hello", "phone_number": "+201234567890",
                     "whatsapp_id": "123@lid", "provider_message_id": "3EB0ABC", "lifecycle_persisted": True,
                     "customer_id": UUID_A, "conversation_id": UUID_B, "inbound_message_id": UUID_C})
    assert out["lifecycle_persisted"] is True
    assert (out["lifecycle_customer_id"], out["lifecycle_conversation_id"], out["inbound_message_id"]) == (UUID_A, UUID_B, UUID_C)
    assert out["whatsapp_id"] == "123@lid" and out["provider_message_id"] == "3EB0ABC"


@pytest.mark.parametrize("override", [
    {"channel": "webchat"},
    {"customer_id": "1' OR '1'='1"},
    {"lifecycle_persisted": "true"},
])
def test_lifecycle_ids_are_rejected_unless_well_formed_whatsapp(override):
    body = {"channel": "whatsapp", "customer_message": "hello", "phone_number": "+201234567890",
            "lifecycle_persisted": True, "customer_id": UUID_A, "conversation_id": UUID_B, "inbound_message_id": UUID_C}
    body.update(override)
    out = _sanitize(body)
    assert out["lifecycle_persisted"] is False
    assert out["lifecycle_customer_id"] == "" and out["inbound_message_id"] == ""


# --- 04D: agent replies are delivered only for real WhatsApp tickets ---------------------------

def _prepare(ticket, message="Agent answer"):
    refs = {"Lookup Ticket & Customer": ticket, "Record Agent Message": {"id": UUID_A},
            "Agent Response Webhook": {"body": {"agent_message": message}}}
    return _run("04D_agent_response_bridge.json", "Prepare Agent Delivery", {}, refs)


def test_agent_reply_on_whatsapp_ticket_is_dispatched():
    out = _prepare({"ticket_id": UUID_B, "channel": "whatsapp", "whatsapp_id": "123@lid", "ticket_number": "TCK-1"})
    assert out["explicit_dispatch"] is True and out["lifecycle_message_id"] == UUID_A


@pytest.mark.parametrize("ticket", [
    {"ticket_id": FALLBACK_ID, "channel": "whatsapp", "whatsapp_id": "201000000000"},  # unknown ticket placeholder
    {"ticket_id": UUID_B, "channel": "webchat", "phone_number": "+201234567890"},
    {"ticket_id": UUID_B, "channel": "whatsapp"},  # no address
])
def test_agent_reply_is_not_dispatched_without_a_real_whatsapp_ticket(ticket):
    assert _prepare(ticket)["explicit_dispatch"] is False


def test_empty_agent_reply_is_not_dispatched():
    out = _prepare({"ticket_id": UUID_B, "channel": "whatsapp", "whatsapp_id": "123@lid"}, message="  ")
    assert out["explicit_dispatch"] is False


# --- Webhook auth and logger de-duplication (export structure) ---------------------------------

@pytest.mark.parametrize("filename", ["01_gateway_dispatcher.json", "04D_agent_response_bridge.json",
                                      "07_analytics_reporting.json", "08_csat_survey.json",
                                      "10_agent_management.json", "11_kb_admin.json"])
def test_every_webhook_requires_the_service_token(filename):
    hooks = [n for n in _workflow(filename)["nodes"] if n["type"] == "n8n-nodes-base.webhook"]
    assert hooks
    for hook in hooks:
        assert hook["parameters"].get("authentication") == "headerAuth"
        assert hook["credentials"]["httpHeaderAuth"]["id"] == "CS_WA_BRIDGE_CRED_01"


def test_logger_reuses_lifecycle_rows_instead_of_inserting_copies():
    wf = _workflow("05_conversation_logger.json")
    customer_sql = _node(wf, "Save Customer Message")["parameters"]["query"]
    assert "UPDATE messages" in customer_sql and "WHERE NOT EXISTS (SELECT 1 FROM lifecycle_row)" in customer_sql
    ai_sql = _node(wf, "Save AI Response")["parameters"]["query"]
    assert "reply_to_provider_message_id" in ai_sql and "ON CONFLICT DO NOTHING" in ai_sql


def test_session_manager_pins_lifecycle_conversation_and_excludes_current_message():
    wf = _workflow("02_customer_session.json")
    assert "pinned AS" in _node(wf, "Find or Upsert Customer")["parameters"]["query"]
    conv_sql = _node(wf, "Get or Start Conversation")["parameters"]["query"]
    assert "pinned AS" in conv_sql and "inbound_message_id" in conv_sql
