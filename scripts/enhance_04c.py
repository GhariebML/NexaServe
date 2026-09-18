import json

with open("infra/n8n/workflows/04C_human_escalation.json", encoding="utf-8") as f:
    wf04c = json.load(f)

nodes = wf04c["nodes"]

# Check if already enhanced
if any(n["name"] == "Categorize Ticket" for n in nodes):
    print("04C already enhanced, skipping")
    import sys
    sys.exit(0)

trigger = next(n for n in nodes if n["name"] == "Execute Workflow Trigger")
create_ticket = next(n for n in nodes if n["name"] == "Create SLA Ticket in Postgres")
update_conv = next(n for n in nodes if n["name"] == "Mark Conversation Handed Off")
agent_notify = next(n for n in nodes if n["name"] == "Dispatch Agent Notification & Audit")
format_ticket = next(n for n in nodes if n["name"] == "Format Escalation Notice")

# Shift positions for existing nodes after insertion point
update_conv["position"] = [820, 300]
agent_notify["position"] = [1040, 300]
format_ticket["position"] = [1260, 300]

# Check if already enhanced
if any(n["name"] == "Categorize Ticket" for n in nodes):
    print("04C already enhanced, skipping")
    import sys
    sys.exit(0)

with open("scripts/categorize_code.js", encoding="utf-8") as f:
    js_code = f.read()

categorize = {
    "id": "node-categorize-ticket",
    "name": "Categorize Ticket",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [380, 300],
    "parameters": {
        "jsCode": js_code,
        "notesInFlow": True,
        "notes": "Categorizes ticket based on customer message keywords. Maps to ticket_categories table."
    }
}

create_ticket_mod = dict(create_ticket)
create_ticket_mod["position"] = [600, 300]
create_ticket_mod["parameters"]["query"] = "=INSERT INTO tickets (ticket_number, customer_id, conversation_id, priority, status, reason, assigned_team, escalation_channel, sla_due_at, category_id)\nVALUES (\n  'TICK-' || floor(random() * 90000 + 10000)::text,\n  '{{ ($json.customer && $json.customer.id && $json.customer.id !== \"null\") ? $json.customer.id : \"a0000000-0000-0000-0000-000000000001\" }}'::uuid,\n  '{{ ($json.conversation && $json.conversation.id && $json.conversation.id !== \"null\") ? $json.conversation.id : \"a0000000-0000-0000-0000-000000000001\" }}'::uuid,\n  '{{ $json.ai_output?.sentiment === 'angry' ? 'urgent' : 'high' }}',\n  'open',\n  '{{ ($json.customer_message || 'Citizen requested specialist assistance').replace(/'/g, \"''\") }}',\n  'DEPI Citizen Escalations Team',\n  '{{ $json.channel || 'webchat' }}',\n  CURRENT_TIMESTAMP + (CASE WHEN '{{ $json.ai_output?.sentiment }}' = 'angry' THEN INTERVAL '30 minutes' ELSE INTERVAL '2 hours' END),\n  (SELECT id FROM ticket_categories WHERE name = '{{ ($('Categorize Ticket').first().json.category_id || 'general') }}' LIMIT 1)\n)\nRETURNING ticket_number, priority, status, sla_due_at, created_at, category_id;"

agent_notify_mod = dict(agent_notify)
agent_notify_mod["position"] = [1040, 300]
agent_notify_mod["parameters"]["query"] = "=INSERT INTO audit_logs (workflow_name, event_type, channel, payload)\nVALUES (\n  'SubWF 04C - Escalation',\n  'hitl_escalated',\n  '{{ $('Execute Workflow Trigger').first().json.channel || 'webchat' }}',\n  json_build_object(\n    'ticket_number', '{{ $('Create SLA Ticket in Postgres').first().json.ticket_number }}',\n    'priority', '{{ $('Create SLA Ticket in Postgres').first().json.priority }}',\n    'sla_due_at', '{{ $('Create SLA Ticket in Postgres').first().json.sla_due_at }}',\n    'category_id', '{{ $('Create SLA Ticket in Postgres').first().json.category_id }}',\n    'customer', '{{ $('Execute Workflow Trigger').first().json.customer?.full_name }}',\n    'channel_user_id', '{{ $('Execute Workflow Trigger').first().json.channel_user_id }}'\n  )\n);"

wf04c["nodes"] = [trigger, categorize, create_ticket_mod, update_conv, agent_notify_mod, format_ticket]

wf04c["connections"] = {
    "Execute Workflow Trigger": {
        "main": [[{"node": "Categorize Ticket", "type": "main", "index": 0}]]
    },
    "Categorize Ticket": {
        "main": [[{"node": "Create SLA Ticket in Postgres", "type": "main", "index": 0}]]
    },
    "Create SLA Ticket in Postgres": {
        "main": [[{"node": "Mark Conversation Handed Off", "type": "main", "index": 0}]]
    },
    "Mark Conversation Handed Off": {
        "main": [[{"node": "Dispatch Agent Notification & Audit", "type": "main", "index": 0}]]
    },
    "Dispatch Agent Notification & Audit": {
        "main": [[{"node": "Format Escalation Notice", "type": "main", "index": 0}]]
    }
}

with open("infra/n8n/workflows/04C_human_escalation.json", "w", encoding="utf-8") as f:
    json.dump(wf04c, f, indent=2, ensure_ascii=False)

print("04C enhanced successfully")
print("Total nodes: {}".format(len(wf04c["nodes"])))
for i, n in enumerate(wf04c["nodes"]):
    print("  {}. {} at {}".format(i+1, n["name"], n["position"]))
