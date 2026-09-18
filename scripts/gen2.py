import json, os, sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'infra', 'n8n', 'workflows')

def make_node(node_id, name, node_type, position, params):
    node = {
        'id': node_id,
        'name': name,
        'type': node_type,
        'typeVersion': 2,
        'position': position,
        'parameters': params
    }
    return node

def save_wf(filename, wf_id, name, nodes, connections):
    wf = {
        'id': wf_id,
        'name': name,
        'active': True,
        'nodes': nodes,
        'connections': connections,
        'settings': {'executionOrder': 'v1'},
        'staticData': None,
        'pinData': {},
        'versionId': '',
        'triggerCount': 1
    }
    path = os.path.join(BASE, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print('Created: ' + path)

# 07 Analytics
nodes = []
nodes.append(make_node('n1', 'Analytics Webhook', 'n8n-nodes-base.webhook', [100, 300],
    {'httpMethod': 'POST', 'path': 'analytics-report', 'responseMode': 'responseNode', 'options': {}}))
nodes.append(make_node('n2', 'Load Metrics', 'n8n-nodes-base.postgres', [340, 300],
    {'operation': 'executeQuery', 'query': "SELECT (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '1 day') AS today, (SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL '7 days') AS week;",
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(make_node('n3', 'Respond Analytics', 'n8n-nodes-base.respondToWebhook', [580, 300],
    {'respondWith': 'json', 'responseBody': '={ $json }'}))
conns = {
    'Analytics Webhook': {'main': [[{'node': 'Load Metrics', 'type': 'main', 'index': 0}]]},
    'Load Metrics': {'main': [[{'node': 'Respond Analytics', 'type': 'main', 'index': 0}]]}
}
save_wf('07_analytics_reporting.json', 'CSWF000000000009', '07_Analytics & Reporting', nodes, conns)

# 08 CSAT
nodes = []
nodes.append(make_node('n1', 'Ticket Resolved Trigger', 'n8n-nodes-base.postgresTrigger', [100, 300],
    {'pollTimes': {'item': [{'mode': 'everyMinute'}]}, 'queries': {'query': "SELECT ticket_number, status, conversation_id, customer_id FROM tickets WHERE status = 'resolved' AND updated_at >= NOW() - INTERVAL '5 minutes';"}}))
nodes.append(make_node('n2', 'Get Customer', 'n8n-nodes-base.postgres', [340, 300],
    {'operation': 'executeQuery', 'query': "SELECT c.*, conv.channel, conv.language FROM customers c JOIN conversations conv ON c.id = conv.id WHERE conv.id = '{{ $json.conversation_id }}' LIMIT 1;",
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(make_node('n3', 'Send Survey', 'n8n-nodes-base.code', [580, 300],
    {'jsCode': 'return [{ json: { ...$input.first().json, survey: "DEPI CSAT", sent_at: new Date().toISOString() } }];'}))
nodes.append(make_node('n4', 'Log Survey', 'n8n-nodes-base.postgres', [820, 300],
    {'operation': 'executeQuery', 'query': "INSERT INTO audit_logs (workflow_name, event_type, payload) VALUES ('08_CSAT', 'survey_sent', json_build_object('ticket', '{{ $json.ticket_number }}'));",
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(make_node('n5', 'Respond', 'n8n-nodes-base.respondToWebhook', [1060, 300],
    {'respondWith': 'json', 'responseBody': '={ $json }'}))
conns = {
    'Ticket Resolved Trigger': {'main': [[{'node': 'Get Customer', 'type': 'main', 'index': 0}]]},
    'Get Customer': {'main': [[{'node': 'Send Survey', 'type': 'main', 'index': 0}]]},
    'Send Survey': {'main': [[{'node': 'Log Survey', 'type': 'main', 'index': 0}], [{'node': 'Respond', 'type': 'main', 'index': 0}]]},
    'Log Survey': {'main': [[{'node': 'Respond', 'type': 'main', 'index': 0}]]}
}
save_wf('08_csat_survey.json', 'CSWF000000000010', '08_CSAT Survey', nodes, conns)

# 09 Automation
nodes = []
nodes.append(make_node('n1', 'Cron Trigger', 'n8n-nodes-base.cronTrigger', [100, 300],
    {'triggerTimes': {'item': [{'mode': 'everyXMinutes', 'minutes': 15}]}}))
nodes.append(make_node('n2', 'Load Rules', 'n8n-nodes-base.postgres', [340, 300],
    {'operation': 'executeQuery', 'query': 'SELECT * FROM automation_rules WHERE is_active = TRUE;',
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(make_node('n3', 'Evaluate Rules', 'n8n-nodes-base.code', [580, 300],
    {'jsCode': 'return $input.all().map(n => ({ json: { ...n.json, evaluated: true } }));'}))
nodes.append(make_node('n4', 'Execute Actions', 'n8n-nodes-base.code', [820, 300],
    {'jsCode': 'return $input.all().map(n => ({ json: { ...n.json, action_executed: n.json.action_type || "none" } }));'}))
nodes.append(make_node('n5', 'Respond', 'n8n-nodes-base.respondToWebhook', [1060, 300],
    {'respondWith': 'json', 'responseBody': '={ $json }'}))
conns = {
    'Cron Trigger': {'main': [[{'node': 'Load Rules', 'type': 'main', 'index': 0}]]},
    'Load Rules': {'main': [[{'node': 'Evaluate Rules', 'type': 'main', 'index': 0}]]},
    'Evaluate Rules': {'main': [[{'node': 'Execute Actions', 'type': 'main', 'index': 0}]]},
    'Execute Actions': {'main': [[{'node': 'Respond', 'type': 'main', 'index': 0}]]}
}
save_wf('09_automation_rules.json', 'CSWF000000000011', '09_Automation Rules Engine', nodes, conns)

print('Done with 3 workflows')
