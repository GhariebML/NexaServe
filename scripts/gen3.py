import json, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'infra', 'n8n', 'workflows')

def node(node_id, name, node_type, position, parameters):
    return {'id': node_id, 'name': name, 'type': node_type, 'typeVersion': 2,
            'position': position, 'parameters': parameters}

def branch(node_name):
    """Create a single branch containing one node"""
    return [{'node': node_name, 'type': 'main', 'index': 0}]

def main_conn(*node_names):
    """Create main connections with proper bracket structure"""
    return {'main': [branch(n) for n in node_names]}

def save_wf(filename, wf_id, name, nodes, connections):
    wf = {'id': wf_id, 'name': name, 'active': True, 'nodes': nodes,
          'connections': connections, 'settings': {'executionOrder': 'v1'},
          'staticData': None, 'pinData': {}, 'versionId': '', 'triggerCount': 1}
    path = os.path.join(BASE, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print('Created: ' + path)

# 10 Agent Management
nodes = []
nodes.append(node('n1', 'Webhook: Agent APIs', 'n8n-nodes-base.webhook', [100, 300],
    {'httpMethod': 'POST', 'path': 'agent-manage', 'responseMode': 'responseNode'}))
nodes.append(node('n2', 'Route Action', 'n8n-nodes-base.switch', [340, 300],
    {'rules': {'values': [
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'register'}]}},
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'status'}]}},
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'assign'}]}},
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'performance'}]}}
    ], 'fallbackOutput': 4}}))
nodes.append(node('n3a', 'AGENT - Register', 'n8n-nodes-base.postgres', [580, 50],
    {'operation': 'executeQuery',
     'query': "INSERT INTO agents (name, email, role, team) VALUES ('{{ $json.body?.name }}', '{{ $json.body?.email }}', '{{ $json.body?.role || \"tier1\" }}', 'DEPI Support') RETURNING *;",
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(node('n3b', 'AGENT - Update Status', 'n8n-nodes-base.postgres', [580, 200],
    {'operation': 'executeQuery',
     'query': "UPDATE agents SET status = '{{ $json.body?.status }}', updated_at = NOW() WHERE email = '{{ $json.body?.email }}';",
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(node('n3c', 'AGENT - Get Available', 'n8n-nodes-base.postgres', [580, 350],
    {'operation': 'executeQuery',
     'query': "SELECT * FROM agents WHERE status = 'available' ORDER BY RANDOM() LIMIT 1;",
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes.append(node('n4', 'Respond Agent', 'n8n-nodes-base.respondToWebhook', [820, 300],
    {'respondWith': 'json', 'responseBody': '={ $json }'}))

conns = {}
conns['Webhook: Agent APIs'] = {'main': [[{'node': 'Route Action', 'type': 'main', 'index': 0}]]}
conns['Route Action'] = main_conn('AGENT - Register', 'AGENT - Update Status', 'AGENT - Get Available', 'Respond Agent')
conns['AGENT - Register'] = main_conn('Respond Agent')
conns['AGENT - Update Status'] = main_conn('Respond Agent')
conns['AGENT - Get Available'] = main_conn('Respond Agent')

save_wf('10_agent_management.json', 'CSWF000000000012', '10_Agent Management API', nodes, conns)

# 11 KB Admin
nodes2 = []
nodes2.append(node('n1', 'Webhook: KB Admin', 'n8n-nodes-base.webhook', [100, 300],
    {'httpMethod': 'POST', 'path': 'kb-admin', 'responseMode': 'responseNode'}))
nodes2.append(node('n2', 'Route Action', 'n8n-nodes-base.switch', [340, 300],
    {'rules': {'values': [
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'create'}]}},
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'update'}]}},
        {'conditions': {'options': {'caseSensitive': False}, 'conditions': [{'leftValue': '={{ $json.body?.action }}', 'rightValue': 'search'}]}}
    ], 'fallbackOutput': 3}}))
nodes2.append(node('n3a', 'KB - Create', 'n8n-nodes-base.postgres', [580, 100],
    {'operation': 'executeQuery',
     'query': 'INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar, keywords_ar, is_active) VALUES (\'{{ $json.body?.category || "general" }}\', \'{{ ($json.body?.question || \'\').replace(/\'/g, "\'\'") }}\', \'{{ ($json.body?.answer || \'\').replace(/\'/g, "\'\'") }}\', ARRAY[\'general\'], \'{{ ($json.body?.question_ar || \'\').replace(/\'/g, "\'\'") }}\', \'{{ ($json.body?.answer_ar || \'\').replace(/\'/g, "\'\'") }}\', ARRAY[\'general\'], TRUE) RETURNING *;',
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes2.append(node('n3b', 'KB - Search', 'n8n-nodes-base.postgres', [580, 300],
    {'operation': 'executeQuery',
     'query': 'SELECT * FROM knowledge_base WHERE is_active = TRUE AND (question ILIKE \'%{{ $json.body?.query || \'\' }}%\' OR answer ILIKE \'%{{ $json.body?.query || \'\' }}%\') LIMIT 20;',
     'credentials': {'postgres': {'id': 'CS_PG_CRED_01', 'name': 'CustomerService Postgres'}}}))
nodes2.append(node('n4', 'Respond KB', 'n8n-nodes-base.respondToWebhook', [820, 300],
    {'respondWith': 'json', 'responseBody': '={ $json }'}))

conns2 = {}
conns2['Webhook: KB Admin'] = {'main': [[{'node': 'Route Action', 'type': 'main', 'index': 0}]]}
conns2['Route Action'] = main_conn('KB - Create', 'KB - Search', 'Respond KB')
conns2['KB - Create'] = main_conn('Respond KB')
conns2['KB - Search'] = main_conn('Respond KB')

save_wf('11_kb_admin.json', 'CSWF000000000013', '11_KB Admin', nodes2, conns2)

print('Agent + KB workflows done!')
