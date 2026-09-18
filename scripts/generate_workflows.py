#!/usr/bin/env python3
"""Generate NexaServe workflow JSONs with proper UTF-8 encoding."""
import json, os, sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'infra', 'n8n', 'workflows')

def gen_id():
    return "CSWF" + "".join(str(ord(c) % 10) for c in "000000000000")

# Simple minimal valid workflows for the new features
workflows = []

# 1. Analytics workflow
analytics = {
    "id": "CSWF000000000009",
    "name": "07_Analytics & Reporting",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Analytics Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"httpMethod": "POST", "path": "analytics-report", "responseMode": "responseNode"}},
        {"id": "n2", "name": "Load Metrics", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [340, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '1 day') AS today, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '7 days') AS week, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '30 days') AS month, (SELECT ROUND(AVG(rating)::NUMERIC,2) FROM csat_surveys WHERE created_at >= NOW() - INTERVAL '30 days') AS csat_avg, (SELECT COUNT(*) FROM tickets WHERE status = 'resolved' AND created_at >= NOW() - INTERVAL '30 days') AS resolved_30d, (SELECT COUNT(*) FROM tickets WHERE status = 'open') AS open_tickets;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3", "name": "Respond Analytics", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [580, 300],
         "parameters": {"respondWith": "json", "responseBody": "={{ $json }}"}}
    ],
    "connections": {
        "Analytics Webhook": {"main": [[{"node": "Load Metrics", "type": "main", "index": 0}]]},
        "Load Metrics": {"main": [[{"node": "Respond Analytics", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
workflows.append(analytics)

# 2. CSAT workflow  
csat = {
    "id": "CSWF000000000010",
    "name": "08_CSAT Survey",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Ticket Resolved Trigger", "type": "n8n-nodes-base.postgresTrigger", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"pollTimes": {"item": [{"mode": "everyMinute"}]},
            "queries": {"query": "SELECT ticket_number, status, conversation_id, customer_id FROM tickets WHERE status = 'resolved' AND updated_at >= NOW() - INTERVAL '5 minutes';"}}},
        {"id": "n2", "name": "Get Customer Info", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [340, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT c.*, conv.channel, conv.language FROM customers c JOIN conversations conv ON c.id = conv.id WHERE conv.id = '{{ $json.conversation_id }}' LIMIT 1;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3", "name": "Send Survey", "type": "n8n-nodes-base.code", "typeVersion": 2,
         "position": [580, 300],
         "parameters": {"jsCode": "return [{json: {...$input.first().json, survey_message: 'DEPI Satisfaction Survey: Rate 1-5', survey_sent_at: new Date().toISOString()}}];"}},
        {"id": "n4", "name": "Log Survey", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [820, 300],
         "parameters": {"operation": "executeQuery",
            "query": "INSERT INTO audit_logs (workflow_name, event_type, channel, payload) VALUES ('08_CSAT', 'survey_sent', '{{ $json.channel }}', json_build_object('ticket', '{{ $json.ticket_number }}'));",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n5", "name": "Respond", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [1060, 300],
         "parameters": {"respondWith": "json", "responseBody": "={{ $json }}"}}
    ],
    "connections": {
        "Ticket Resolved Trigger": {"main": [[{"node": "Get Customer Info", "type": "main", "index": 0}]]},
        "Get Customer Info": {"main": [[{"node": "Send Survey", "type": "main", "index": 0}]]},
        "Send Survey": {"main": [[{"node": "Log Survey", "type": "main", "index": 0}], {"node": "Respond", "type": "main", "index": 0}]]},
        "Log Survey": {"main": [[{"node": "Respond", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
workflows.append(csat)

# 3. Automation Rules
automation = {
    "id": "CSWF000000000011",
    "name": "09_Automation Rules Engine",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Cron Trigger", "type": "n8n-nodes-base.cronTrigger", "typeVersion": 1.2,
         "position": [100, 300],
         "parameters": {"triggerTimes": {"item": [{"mode": "everyXMinutes", "minutes": 15}]}}},
        {"id": "n2", "name": "Load Rules", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [340, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT * FROM automation_rules WHERE is_active = TRUE;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3", "name": "Evaluate Rules", "type": "n8n-nodes-base.code", "typeVersion": 2,
         "position": [580, 300],
         "parameters": {"jsCode": "const rules = $input.all().map(n => n.json);\nreturn rules.map(r => ({ json: { ...r, evaluated: true, eval_time: new Date().toISOString() } }));"}},
        {"id": "n4", "name": "Execute Actions", "type": "n8n-nodes-base.code", "typeVersion": 2,
         "position": [820, 300],
         "parameters": {"jsCode": "const rules = $input.all().map(n => n.json);\nreturn rules.map(r => ({ json: { ...r, action_executed: r.action_type || 'none', details: 'Action processed: ' + (r.action_type || 'unknown') } }));"}},
        {"id": "n5", "name": "Log & Respond", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [1060, 300],
         "parameters": {"respondWith": "json", "responseBody": "={{ JSON.stringify({ processed: $input.all().length, results: $input.all().map(n => n.json) }) }}"}}
    ],
    "connections": {
        "Cron Trigger": {"main": [[{"node": "Load Rules", "type": "main", "index": 0}]]},
        "Load Rules": {"main": [[{"node": "Evaluate Rules", "type": "main", "index": 0}]]},
        "Evaluate Rules": {"main": [[{"node": "Execute Actions", "type": "main", "index": 0}]]},
        "Execute Actions": {"main": [[{"node": "Log & Respond", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
workflows.append(automation)

# 4. Agent Management API
agent_api = {
    "id": "CSWF000000000012",
    "name": "10_Agent Management API",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Webhook: Agent APIs", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"httpMethod": "POST", "path": "agent-manage", "responseMode": "responseNode"}},
        {"id": "n2", "name": "Route Agent Action", "type": "n8n-nodes-base.switch", "typeVersion": 3.2,
         "position": [340, 300],
         "parameters": {"rules": {"values": [
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "register"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "status"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "assign"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "performance"}]}}
         ], "fallbackOutput": 4}}},
        {"id": "n3a", "name": "AGENT - Register", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 100],
         "parameters": {"operation": "executeQuery",
            "query": "INSERT INTO agents (name, email, role, team) VALUES ('{{ $json.body?.name }}', '{{ $json.body?.email }}', '{{ $json.body?.role || \"tier1\" }}', 'DEPI Support') RETURNING *;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3b", "name": "AGENT - Update Status", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 200],
         "parameters": {"operation": "executeQuery",
            "query": "UPDATE agents SET status = '{{ $json.body?.status }}', updated_at = NOW() WHERE email = '{{ $json.body?.email }}';",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3c", "name": "AGENT - Get Available", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT * FROM agents WHERE status = 'available' ORDER BY RANDOM() LIMIT 1;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3d", "name": "AGENT - Get Performance", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 400],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT a.name, a.role, COUNT(t.id) as tickets, ROUND(AVG(cs.rating)::NUMERIC,2) as csat FROM agents a LEFT JOIN tickets t ON t.assigned_agent_id = a.id LEFT JOIN csat_surveys cs ON cs.ticket_number = t.ticket_number GROUP BY a.id, a.name, a.role;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n4", "name": "Respond Agent API", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [820, 300],
         "parameters": {"respondWith": "json", "responseBody": "={{ $json }}"}}
    ],
    "connections": {
        "Webhook: Agent APIs": {"main": [[{"node": "Route Agent Action", "type": "main", "index": 0}]]},
        "Route Agent Action": {"main": [[{"node": "AGENT - Register", "type": "main", "index": 0}, {"node": "AGENT - Update Status", "type": "main", "index": 0}, {"node": "AGENT - Get Available", "type": "main", "index": 0}, {"node": "AGENT - Get Performance", "type": "main", "index": 0}, {"node": "Respond Agent API", "type": "main", "index": 0}]]},
        "AGENT - Register": {"main": [[{"node": "Respond Agent API", "type": "main", "index": 0}]]},
        "AGENT - Update Status": {"main": [[{"node": "Respond Agent API", "type": "main", "index": 0}]]},
        "AGENT - Get Available": {"main": [[{"node": "Respond Agent API", "type": "main", "index": 0}]]},
        "AGENT - Get Performance": {"main": [[{"node": "Respond Agent API", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
workflows.append(agent_api)

# 5. KB Admin
kb_admin_wf = {
    "id": "CSWF000000000013",
    "name": "11_KB Admin",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Webhook: KB Admin", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"httpMethod": "POST", "path": "kb-admin", "responseMode": "responseNode"}},
        {"id": "n2", "name": "KB - Route Action", "type": "n8n-nodes-base.switch", "typeVersion": 3.2,
         "position": [340, 300],
         "parameters": {"rules": {"values": [
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "create"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "update"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "search"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "versions"}]}}
         ], "fallbackOutput": 4}}},
        {"id": "n3a", "name": "KB - Create", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 100],
         "parameters": {"operation": "executeQuery",
            "query": "INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar, keywords_ar, is_active) VALUES ('{{ $json.body?.category || \"general\" }}', '{{ ($json.body?.question || '').replace(/'/g, \"''\") }}', '{{ ($json.body?.answer || '').replace(/'/g, \"''\") }}', ARRAY['general'], '{{ ($json.body?.question_ar || '').replace(/'/g, \"''\") }}', '{{ ($json.body?.answer_ar || '').replace(/'/g, \"''\") }}', ARRAY['general'], TRUE) RETURNING *;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3b", "name": "KB - Update", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 200],
         "parameters": {"operation": "executeQuery",
            "query": "UPDATE knowledge_base SET question = COALESCE('{{ ($json.body?.question || '').replace(/'/g, \"''\") }}', question), answer = COALESCE('{{ ($json.body?.answer || '').replace(/'/g, \"''\") }}', answer) WHERE id = '{{ $json.body?.id }}' RETURNING *;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3c", "name": "KB - Search", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT * FROM knowledge_base WHERE is_active = TRUE AND (question ILIKE '%{{ $json.body?.query || '' }}%' OR answer ILIKE '%{{ $json.body?.query || '' }}%') ORDER BY created_at DESC LIMIT 20;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n4", "name": "Respond KB", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [820, 300],
         "parameters": {"respondWith": "json", "responseBody": "={{ $json }}"}}
    ],
    "connections": {
        "Webhook: KB Admin": {"main": [[{"node": "KB - Route Action", "type": "main", "index": 0}]]},
        "KB - Route Action": {"main": [[{"node": "KB - Create", "type": "main", "index": 0}, {"node": "KB - Update", "type": "main", "index": 0}, {"node": "KB - Search", "type": "main", "index": 0}, {"node": "Respond KB", "type": "main", "index": 0}]]},
        "KB - Create": {"main": [[{"node": "Respond KB", "type": "main", "index": 0}]]},
        "KB - Update": {"main": [[{"node": "Respond KB", "type": "main", "index": 0}]]},
        "KB - Search": {"main": [[{"node": "Respond KB", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
workflows.append(kb_admin_wf)

# Save all
for wf in workflows:
    filename = wf["name"].replace(" ", "_").lower().replace("&", "and")
    filename = "07_analytics_reporting.json" if "07" in wf["name"] else filename
    filename = "08_csat_survey.json" if "08" in wf["name"] else filename
    filename = "09_automation_rules.json" if "09" in wf["name"] else filename
    filename = "10_agent_management.json" if "10" in wf["name"] else filename
    filename = "11_kb_admin.json" if "11" in wf["name"] else filename
    path = os.path.join(BASE, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print(f"Generated: {path}")

print("Done!")
