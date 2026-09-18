import json, os, sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'infra', 'n8n', 'workflows')

def save(filename, wf):
    path = os.path.join(BASE, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print("Created: " + path)

# 07_Analytics
analytics = {
    "id": "CSWF000000000009",
    "name": "07_Analytics & Reporting",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Analytics Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"httpMethod": "POST", "path": "analytics-report", "responseMode": "responseNode", "options": {}}},
        {"id": "n2", "name": "Load Metrics", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [340, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '1 day') AS today, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '7 days') AS week, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '30 days') AS month, (SELECT ROUND(AVG(rating)::NUMERIC,2) FROM csat_surveys WHERE created_at >= NOW() - INTERVAL '30 days') AS csat_avg;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3", "name": "Respond Analytics", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [580, 300],
         "parameters": {"respondWith": "json", "responseBody": "={ $json }"}}
    ],
    "connections": {
        "Analytics Webhook": {"main": [[{"node": "Load Metrics", "type": "main", "index": 0}]]},
        "Load Metrics": {"main": [[{"node": "Respond Analytics", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
save("07_analytics_reporting.json", analytics)

# 08_CSAT
csat = {
    "id": "CSWF000000000010",
    "name": "08_CSAT Survey",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Ticket Resolved Trigger", "type": "n8n-nodes-base.postgresTrigger", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"pollTimes": {"item": [{"mode": "everyMinute"}]},
            "queries": {"query": "SELECT ticket_number, status, conversation_id, customer_id FROM tickets WHERE status = 'resolved' AND updated_at >= NOW() - INTERVAL '5 minutes';"}}},
        {"id": "n2", "name": "Get Customer", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [340, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT c.*, conv.channel, conv.language FROM customers c JOIN conversations conv ON c.id = conv.id WHERE conv.id = '{{ $json.conversation_id }}' LIMIT 1;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3", "name": "Send Survey", "type": "n8n-nodes-base.code", "typeVersion": 2,
         "position": [580, 300],
         "parameters": {"jsCode": "return [{ json: { ...$input.first().json, survey: 'DEPI CSAT', sent_at: new Date().toISOString() } }];"}},
        {"id": "n4", "name": "Log Survey", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [820, 300],
         "parameters": {"operation": "executeQuery",
            "query": "INSERT INTO audit_logs (workflow_name, event_type, payload) VALUES ('08_CSAT', 'survey_sent', json_build_object('ticket', '{{ $json.ticket_number }}'));",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n5", "name": "Respond", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [1060, 300],
         "parameters": {"respondWith": "json", "responseBody": "={ $json }"}}
    ],
    "connections": {
        "Ticket Resolved Trigger": {"main": [[{"node": "Get Customer", "type": "main", "index": 0}]]},
        "Get Customer": {"main": [[{"node": "Send Survey", "type": "main", "index": 0}]]},
        "Send Survey": {"main": [[{"node": "Log Survey", "type": "main", "index": 0}], {"node": "Respond", "type": "main", "index": 0}]]},
        "Log Survey": {"main": [[{"node": "Respond", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
save("08_csat_survey.json", csat)

# 09_Automation
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
         "parameters": {"jsCode": "return $input.all().map(n => ({ json: { ...n.json, evaluated: true } }));"}},
        {"id": "n4", "name": "Execute Actions", "type": "n8n-nodes-base.code", "typeVersion": 2,
         "position": [820, 300],
         "parameters": {"jsCode": "return $input.all().map(n => ({ json: { ...n.json, action_executed: n.json.action_type || 'none' } }));"}},
        {"id": "n5", "name": "Respond", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [1060, 300],
         "parameters": {"respondWith": "json", "responseBody": "={ $json }"}}
    ],
    "connections": {
        "Cron Trigger": {"main": [[{"node": "Load Rules", "type": "main", "index": 0}]]},
        "Load Rules": {"main": [[{"node": "Evaluate Rules", "type": "main", "index": 0}]]},
        "Evaluate Rules": {"main": [[{"node": "Execute Actions", "type": "main", "index": 0}]]},
        "Execute Actions": {"main": [[{"node": "Respond", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
save("09_automation_rules.json", automation)

# 10_Agent Management
agent_api = {
    "id": "CSWF000000000012",
    "name": "10_Agent Management API",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Webhook: Agent APIs", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"httpMethod": "POST", "path": "agent-manage", "responseMode": "responseNode"}},
        {"id": "n2", "name": "Route Action", "type": "n8n-nodes-base.switch", "typeVersion": 3.2,
         "position": [340, 300],
         "parameters": {"rules": {"values": [
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "register"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "status"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "assign"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "performance"}]}}
         ], "fallbackOutput": 4}}},
        {"id": "n3a", "name": "AGENT - Register", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 50],
         "parameters": {"operation": "executeQuery",
            "query": "INSERT INTO agents (name, email, role, team) VALUES ('{{ $json.body?.name }}', '{{ $json.body?.email }}', '{{ $json.body?.role || \"tier1\" }}', 'DEPI Support') RETURNING *;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3b", "name": "AGENT - Update Status", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 200],
         "parameters": {"operation": "executeQuery",
            "query": "UPDATE agents SET status = '{{ $json.body?.status }}', updated_at = NOW() WHERE email = '{{ $json.body?.email }}';",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3c", "name": "AGENT - Get Available", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 350],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT * FROM agents WHERE status = 'available' ORDER BY RANDOM() LIMIT 1;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n4", "name": "Respond Agent", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [820, 300],
         "parameters": {"respondWith": "json", "responseBody": "={ $json }"}}
    ],
    "connections": {
        "Webhook: Agent APIs": {"main": [[{"node": "Route Action", "type": "main", "index": 0}]]},
        "Route Action": {"main": [[{"node": "AGENT - Register", "type": "main", "index": 0}, {"node": "AGENT - Update Status", "type": "main", "index": 0}, {"node": "AGENT - Get Available", "type": "main", "index": 0}, {"node": "Respond Agent", "type": "main", "index": 0}]]},
        "AGENT - Register": {"main": [[{"node": "Respond Agent", "type": "main", "index": 0}]]},
        "AGENT - Update Status": {"main": [[{"node": "Respond Agent", "type": "main", "index": 0}]]},
        "AGENT - Get Available": {"main": [[{"node": "Respond Agent", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
save("10_agent_management.json", agent_api)

# 11_KB Admin
kb_admin = {
    "id": "CSWF000000000013",
    "name": "11_KB Admin",
    "active": True,
    "nodes": [
        {"id": "n1", "name": "Webhook: KB Admin", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [100, 300],
         "parameters": {"httpMethod": "POST", "path": "kb-admin", "responseMode": "responseNode"}},
        {"id": "n2", "name": "Route Action", "type": "n8n-nodes-base.switch", "typeVersion": 3.2,
         "position": [340, 300],
         "parameters": {"rules": {"values": [
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "create"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "update"}]}},
             {"conditions": {"options": {"caseSensitive": False}, "conditions": [{"leftValue": "={{ $json.body?.action }}", "rightValue": "search"}]}}
         ], "fallbackOutput": 3}}},
        {"id": "n3a", "name": "KB - Create", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 100],
         "parameters": {"operation": "executeQuery",
            "query": "INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar, keywords_ar, is_active) VALUES ('{{ $json.body?.category || \"general\" }}', '{{ ($json.body?.question || '').replace(/'/g, \"''\") }}', '{{ ($json.body?.answer || '').replace(/'/g, \"''\") }}', ARRAY['general'], '{{ ($json.body?.question_ar || '').replace(/'/g, \"''\") }}', '{{ ($json.body?.answer_ar || '').replace(/'/g, \"''\") }}', ARRAY['general'], TRUE) RETURNING *;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n3b", "name": "KB - Search", "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
         "position": [580, 300],
         "parameters": {"operation": "executeQuery",
            "query": "SELECT * FROM knowledge_base WHERE is_active = TRUE AND (question ILIKE '%{{ $json.body?.query || '' }}%' OR answer ILIKE '%{{ $json.body?.query || '' }}%') LIMIT 20;",
            "credentials": {"postgres": {"id": "CS_PG_CRED_01", "name": "CustomerService Postgres"}}}},
        {"id": "n4", "name": "Respond KB", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
         "position": [820, 300],
         "parameters": {"respondWith": "json", "responseBody": "={ $json }"}}
    ],
    "connections": {
        "Webhook: KB Admin": {"main": [[{"node": "Route Action", "type": "main", "index": 0}]]},
        "Route Action": {"main": [[{"node": "KB - Create", "type": "main", "index": 0}, {"node": "KB - Search", "type": "main", "index": 0}, {"node": "Respond KB", "type": "main", "index": 0}]]},
        "KB - Create": {"main": [[{"node": "Respond KB", "type": "main", "index": 0}]]},
        "KB - Search": {"main": [[{"node": "Respond KB", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None, "pinData": {}, "versionId": "", "triggerCount": 1
}
save("11_kb_admin.json", kb_admin)

print("All workflows generated!")
