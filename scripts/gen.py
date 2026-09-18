import json, os, base64, zlib

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'infra', 'n8n', 'workflows')

# Base64-encoded compressed JSON for each workflow to avoid syntax issues
# We'll build them programmatically

def save(filename, obj):
    path = os.path.join(BASE, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print("Created: " + path)

# Build workflows one field at a time to avoid syntax issues
wf1 = {}
wf1['id'] = 'CSWF000000000009'
wf1['name'] = '07_Analytics & Reporting'
wf1['active'] = True
wf1['nodes'] = []
n1 = {}
n1['id'] = 'n1'
n1['name'] = 'Analytics Webhook'
n1['type'] = 'n8n-nodes-base.webhook'
n1['typeVersion'] = 2
n1['position'] = [100, 300]
n1['parameters'] = {'httpMethod': 'POST', 'path': 'analytics-report', 'responseMode': 'responseNode', 'options': {}}
wf1['nodes'].append(n1)
n2 = {}
n2['id'] = 'n2'
n2['name'] = 'Load Metrics'
n2['type'] = 'n8n-nodes-base.postgres'
n2['typeVersion'] = 2.5
n2['position'] = [340, 300]
n2['parameters'] = {'operation': 'executeQuery', 'query': "SELECT (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '1 day') AS today, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '7 days') AS week, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '30 days') AS month, (SELECT ROUND(AVG(rating)::NUMERIC,2) FROM csat_surveys WHERE created_at >= NOW() - INTERVAL '30 days') AS csat_avg;", 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf1['nodes'].append(n2)
n3 = {}
n3['id'] = 'n3'
n3['name'] = 'Respond Analytics'
n3['type'] = 'n8n-nodes-base.respondToWebhook'
n3['typeVersion'] = 1.1
n3['position'] = [580, 300]
n3['parameters'] = {'respondWith': 'json', 'responseBody': '={ $json }'}
wf1['nodes'].append(n3)
wf1['connections'] = {
    'Analytics Webhook': {'main': [[{'node': 'Load Metrics', 'type': 'main', 'index': 0}]]},
    'Load Metrics': {'main': [[{'node': 'Respond Analytics', 'type': 'main', 'index': 0}]]}
}
wf1['settings'] = {'executionOrder': 'v1'}
wf1['staticData'] = None
wf1['pinData'] = {}
wf1['versionId'] = ''
wf1['triggerCount'] = 1
save('07_analytics_reporting.json', wf1)

# CSAT
wf2 = {}
wf2['id'] = 'CSWF000000000010'
wf2['name'] = '08_CSAT Survey'
wf2['active'] = True
wf2['nodes'] = []
n1 = {}
n1['id'] = 'n1'
n1['name'] = 'Ticket Resolved Trigger'
n1['type'] = 'n8n-nodes-base.postgresTrigger'
n1['typeVersion'] = 2
n1['position'] = [100, 300]
n1['parameters'] = {'pollTimes': {'item': [{'mode': 'everyMinute'}]}, 'queries': {'query': "SELECT ticket_number, status, conversation_id, customer_id FROM tickets WHERE status = 'resolved' AND updated_at >= NOW() - INTERVAL '5 minutes';"}}
wf2['nodes'].append(n1)
n2 = {}
n2['id'] = 'n2'
n2['name'] = 'Get Customer'
n2['type'] = 'n8n-nodes-base.postgres'
n2['typeVersion'] = 2.5
n2['position'] = [340, 300]
n2['parameters'] = {'operation': 'executeQuery', 'query': "SELECT c.*, conv.channel, conv.language FROM customers c JOIN conversations conv ON c.id = conv.id WHERE conv.id = '{{ $json.conversation_id }}' LIMIT 1;", 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf2['nodes'].append(n2)
n3 = {}
n3['id'] = 'n3'
n3['name'] = 'Send Survey'
n3['type'] = 'n8n-nodes-base.code'
n3['typeVersion'] = 2
n3['position'] = [580, 300]
n3['parameters'] = {'jsCode': 'return [{ json: { ...$input.first().json, survey: \"DEPI CSAT\", sent_at: new Date().toISOString() } }];'}
wf2['nodes'].append(n3)
n4 = {}
n4['id'] = 'n4'
n4['name'] = 'Log Survey'
n4['type'] = 'n8n-nodes-base.postgres'
n4['typeVersion'] = 2.5
n4['position'] = [820, 300]
n4['parameters'] = {'operation': 'executeQuery', 'query': "INSERT INTO audit_logs (workflow_name, event_type, payload) VALUES ('08_CSAT', 'survey_sent', json_build_object('ticket', '{{ $json.ticket_number }}'));", 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf2['nodes'].append(n4)
n5 = {}
n5['id'] = 'n5'
n5['name'] = 'Respond'
n5['type'] = 'n8n-nodes-base.respondToWebhook'
n5['typeVersion'] = 1.1
n5['position'] = [1060, 300]
n5['parameters'] = {'respondWith': 'json', 'responseBody': '={ $json }'}
wf2['nodes'].append(n5)
wf2['connections'] = {
    'Ticket Resolved Trigger': {'main': [[{'node': 'Get Customer', 'type': 'main', 'index': 0}]]},
    'Get Customer': {'main': [[{'node': 'Send Survey', 'type': 'main', 'index': 0}]]},
    'Send Survey': {'main': [[{'node': 'Log Survey', 'type': 'main', 'index': 0}], {'node': 'Respond', 'type': 'main', 'index': 0}]]},
    'Log Survey': {'main': [[{'node': 'Respond', 'type': 'main', 'index': 0}]]}
}
wf2['settings'] = {'executionOrder': 'v1'}
wf2['staticData'] = None
wf2['pinData'] = {}
wf2['versionId'] = ''
wf2['triggerCount'] = 1
save('08_csat_survey.json', wf2)

# Automation
wf3 = {}
wf3['id'] = 'CSWF000000000011'
wf3['name'] = '09_Automation Rules Engine'
wf3['active'] = True
wf3['nodes'] = []
n1 = {}
n1['id'] = 'n1'
n1['name'] = 'Cron Trigger'
n1['type'] = 'n8n-nodes-base.cronTrigger'
n1['typeVersion'] = 1.2
n1['position'] = [100, 300]
n1['parameters'] = {'triggerTimes': {'item': [{'mode': 'everyXMinutes', 'minutes': 15}]}}
wf3['nodes'].append(n1)
n2 = {}
n2['id'] = 'n2'
n2['name'] = 'Load Rules'
n2['type'] = 'n8n-nodes-base.postgres'
n2['typeVersion'] = 2.5
n2['position'] = [340, 300]
n2['parameters'] = {'operation': 'executeQuery', 'query': 'SELECT * FROM automation_rules WHERE is_active = TRUE;', 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf3['nodes'].append(n2)
n3 = {}
n3['id'] = 'n3'
n3['name'] = 'Evaluate Rules'
n3['type'] = 'n8n-nodes-base.code'
n3['typeVersion'] = 2
n3['position'] = [580, 300]
n3['parameters'] = {'jsCode': 'return $input.all().map(n => ({ json: { ...n.json, evaluated: true } }));'}
wf3['nodes'].append(n3)
n4 = {}
n4['id'] = 'n4'
n4['name'] = 'Execute Actions'
n4['type'] = 'n8n-nodes-base.code'
n4['typeVersion'] = 2
n4['position'] = [820, 300]
n4['parameters'] = {'jsCode': 'return $input.all().map(n => ({ json: { ...n.json, action_executed: n.json.action_type || \"none\" } }));'}
wf3['nodes'].append(n4)
n5 = {}
n5['id'] = 'n5'
n5['name'] = 'Respond'
n5['type'] = 'n8n-nodes-base.respondToWebhook'
n5['typeVersion'] = 1.1
n5['position'] = [1060, 300]
n5['parameters'] = {'respondWith': 'json', 'responseBody': '={ $json }'}
wf3['nodes'].append(n5)
wf3['connections'] = {
    'Cron Trigger': {'main': [[{'node': 'Load Rules', 'type': 'main', 'index': 0}]]},
    'Load Rules': {'main': [[{'node': 'Evaluate Rules', 'type': 'main', 'index': 0}]]},
    'Evaluate Rules': {'main': [[{'node': 'Execute Actions', 'type': 'main', 'index': 0}]]},
    'Execute Actions': {'main': [[{'node': 'Respond', 'type': 'main', 'index': 0}]]}
}
wf3['settings'] = {'executionOrder': 'v1'}
wf3['staticData'] = None
wf3['pinData'] = {}
wf3['versionId'] = ''
wf3['triggerCount'] = 1
save('09_automation_rules.json', wf3)

# Agent Management
wf4 = {}
wf4['id'] = 'CSWF000000000012'
wf4['name'] = '10_Agent Management API'
wf4['active'] = True
wf4['nodes'] = []
n1 = {}
n1['id'] = 'n1'
n1['name'] = 'Webhook: Agent APIs'
n1['type'] = 'n8n-nodes-base.webhook'
n1['typeVersion'] = 2
n1['position'] = [100, 300]
n1['parameters'] = {'httpMethod': 'POST', 'path': 'agent-manage', 'responseMode': 'responseNode'}
wf4['nodes'].append(n1)
n2 = {}
n2['id'] = 'n2'
n2['name'] = 'Route Action'
n2['type'] = 'n8n-nodes-base.switch'
n2['typeVersion'] = 3.2
n2['position'] = [340, 300]
n2['parameters'] = {'rules': {'values': [{'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'register'}]}}, {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'status'}]}}, {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'assign'}]}}, {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'performance'}]}}], 'fallbackOutput': 4}}
wf4['nodes'].append(n2)
n3a = {}
n3a['id'] = 'n3a'
n3a['name'] = 'AGENT - Register'
n3a['type'] = 'n8n-nodes-base.postgres'
n3a['typeVersion'] = 2.5
n3a['position'] = [580, 50]
n3a['parameters'] = {'operation': 'executeQuery', 'query': 'INSERT INTO agents (name, email, role, team) VALUES (\'{{ $json.body?.name }}\', \'{{ $json.body?.email }}\', \'{{ $json.body?.role || "tier1" }}\', \'DEPI Support\') RETURNING *;', 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf4['nodes'].append(n3a)
n3b = {}
n3b['id'] = 'n3b'
n3b['name'] = 'AGENT - Update Status'
n3b['type'] = 'n8n-nodes-base.postgres'
n3b['typeVersion'] = 2.5
n3b['position'] = [580, 200]
n3b['parameters'] = {'operation': 'executeQuery', 'query': "UPDATE agents SET status = '{{ $json.body?.status }}', updated_at = NOW() WHERE email = '{{ $json.body?.email }}';", 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf4['nodes'].append(n3b)
n3c = {}
n3c['id'] = 'n3c'
n3c['name'] = 'AGENT - Get Available'
n3c['type'] = 'n8n-nodes-base.postgres'
n3c['typeVersion'] = 2.5
n3c['position'] = [580, 350]
n3c['parameters'] = {'operation': 'executeQuery', 'query': "SELECT * FROM agents WHERE status = 'available' ORDER BY RANDOM() LIMIT 1;", 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf4['nodes'].append(n3c)
n4 = {}
n4['id'] = 'n4'
n4['name'] = 'Respond Agent'
n4['type'] = 'n8n-nodes-base.respondToWebhook'
n4['typeVersion'] = 1.1
n4['position'] = [820, 300]
n4['parameters'] = {'respondWith': 'json', 'responseBody': '={ $json }'}
wf4['nodes'].append(n4)
wf4['connections'] = {
    'Webhook: Agent APIs': {'main': [[{'node': 'Route Action', 'type': 'main', 'index': 0}]]},
    'Route Action': {'main': [[{'node': 'AGENT - Register', 'type': 'main', 'index': 0}], {'node': 'AGENT - Update Status', 'type': 'main', 'index': 0}], [{'node': 'AGENT - Get Available', 'type': 'main', 'index': 0}], [{'node': 'Respond Agent', 'type': 'main', 'index': 0}]]},
    'AGENT - Register': {'main': [[{'node': 'Respond Agent', 'type': 'main', 'index': 0}]]},
    'AGENT - Update Status': {'main': [[{'node': 'Respond Agent', 'type': 'main', 'index': 0}]]},
    'AGENT - Get Available': {'main': [[{'node': 'Respond Agent', 'type': 'main', 'index': 0}]]}
}
wf4['settings'] = {'executionOrder': 'v1'}
wf4['staticData'] = None
wf4['pinData'] = {}
wf4['versionId'] = ''
wf4['triggerCount'] = 1
save('10_agent_management.json', wf4)

# KB Admin
wf5 = {}
wf5['id'] = 'CSWF000000000013'
wf5['name'] = '11_KB Admin'
wf5['active'] = True
wf5['nodes'] = []
n1 = {}
n1['id'] = 'n1'
n1['name'] = 'Webhook: KB Admin'
n1['type'] = 'n8n-nodes-base.webhook'
n1['typeVersion'] = 2
n1['position'] = [100, 300]
n1['parameters'] = {'httpMethod': 'POST', 'path': 'kb-admin', 'responseMode': 'responseNode'}
wf5['nodes'].append(n1)
n2 = {}
n2['id'] = 'n2'
n2['name'] = 'Route Action'
n2['type'] = 'n8n-nodes-base.switch'
n2['typeVersion'] = 3.2
n2['position'] = [340, 300]
n2['parameters'] = {'rules': {'values': [{'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'create'}]}}, {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'update'}]}}, {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'search'}]}}], 'fallbackOutput': 3}}
wf5['nodes'].append(n2)
n3a = {}
n3a['id'] = 'n3a'
n3a['name'] = 'KB - Create'
n3a['type'] = 'n8n-nodes-base.postgres'
n3a['typeVersion'] = 2.5
n3a['position'] = [580, 100]
n3a['parameters'] = {'operation': 'executeQuery', 'query': 'INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar, keywords_ar, is_active) VALUES (\'{{ $json.body?.category || "general" }}\', \'{{ ($json.body?.question || \'\').replace(/\'/g, "\'\'") }}\', \'{{ ($json.body?.answer || \'\').replace(/\'/g, "\'\'") }}\', ARRAY[\'general\'], \'{{ ($json.body?.question_ar || \'\').replace(/\'/g, "\'\'") }}\', \'{{ ($json.body?.answer_ar || \'\').replace(/\'/g, "\'\'") }}\', ARRAY[\'general\'], TRUE) RETURNING *;', 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf5['nodes'].append(n3a)
n3b = {}
n3b['id'] = 'n3b'
n3b['name'] = 'KB - Search'
n3b['type'] = 'n8n-nodes-base.postgres'
n3b['typeVersion'] = 2.5
n3b['position'] = [580, 300]
n3b['parameters'] = {'operation': 'executeQuery', 'query': 'SELECT * FROM knowledge_base WHERE is_active = TRUE AND (question ILIKE \'%{{ $json.body?.query || \'\' }}%\' OR answer ILIKE \'%{{ $json.body?.query || \'\' }}%\') LIMIT 20;', 'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}
wf5['nodes'].append(n3b)
n4 = {}
n4['id'] = 'n4'
n4['name'] = 'Respond KB'
n4['type'] = 'n8n-nodes-base.respondToWebhook'
n4['typeVersion'] = 1.1
n4['position'] = [820, 300]
n4['parameters'] = {'respondWith': 'json', 'responseBody': '={ $json }'}
wf5['nodes'].append(n4)
wf5['connections'] = {
    'Webhook: KB Admin': {'main': [[{'node': 'Route Action', 'type': 'main', 'index': 0}]]},
    'Route Action': {'main': [[{'node': 'KB - Create', 'type': 'main', 'index': 0}], {'node': 'KB - Search', 'type': 'main', 'index': 0}, {'node': 'Respond KB', 'type': 'main', 'index': 0}]]},
    'KB - Create': {'main': [[{'node': 'Respond KB', 'type': 'main', 'index': 0}]]},
    'KB - Search': {'main': [[{'node': 'Respond KB', 'type': 'main', 'index': 0}]]}
}
wf5['settings'] = {'executionOrder': 'v1'}
wf5['staticData'] = None
wf5['pinData'] = {}
wf5['versionId'] = ''
wf5['triggerCount'] = 1
save('11_kb_admin.json', wf5)

print("All workflows generated!")
