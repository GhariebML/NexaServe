import json

with open("infra/n8n/workflows/04D_agent_response_bridge.json") as f:
    wf04d = json.load(f)

# Remove old nodes first, keep only the webhook and respond nodes
keep_names = {"Agent Response Webhook", "Respond to Agent"}
wf04d["nodes"] = [n for n in wf04d["nodes"] if n["name"] in keep_names]
wf04d["connections"] = {}

nodes = wf04d["nodes"]
max_x = 160

# Node 1: Agent Response Webhook (keep as is)
webhook = nodes[0]

# Node 2: Auto-Assign Agent
auto_assign = {
    "id": "node-auto-assign",
    "name": "Auto-Assign Agent",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 220, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=SELECT id, name, email, role, team FROM agents WHERE status = 'available' ORDER BY (SELECT count(*) FROM tickets t WHERE t.assigned_agent_id = agents.id AND t.status NOT IN ('resolved', 'closed')) ASC, id ASC LIMIT 1;"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    },
    "notesInFlow": True,
    "notes": "Assigns ticket to next available agent by workload."
}

# Node 3: Lookup Ticket & Customer (modified to include auto-assigned agent info)
lookup = {
    "id": "node-lookup-ticket",
    "name": "Lookup Ticket & Customer",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 440, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=WITH found AS (\n  SELECT t.id AS ticket_id, t.ticket_number, t.status AS ticket_status, t.conversation_id, t.customer_id,\n         c.full_name, c.phone_number, c.telegram_id, c.whatsapp_id, c.email,\n         COALESCE(conv.channel, 'webchat') AS channel, COALESCE(conv.language, 'ar') AS language\n  FROM tickets t\n  JOIN customers c ON t.customer_id = c.id\n  LEFT JOIN conversations conv ON t.conversation_id = conv.id\n  WHERE t.ticket_number = '{{ ($json.body?.ticket_number || $json.ticket_number || '').replace(/'/g, \"''\") }}'\n  LIMIT 1\n),\nfallback AS (\n  SELECT 'a0000000-0000-0000-0000-000000000001'::uuid AS ticket_id,\n         '{{ ($json.body?.ticket_number || $json.ticket_number || 'TICK-1001').replace(/'/g, \"''\") }}' AS ticket_number,\n         'open' AS ticket_status,\n         'a0000000-0000-0000-0000-000000000001'::uuid AS conversation_id,\n         'a0000000-0000-0000-0000-000000000001'::uuid AS customer_id,\n         'DEPI Citizen' AS full_name,\n         '+201000000000' AS phone_number,\n         'citizen_user' AS telegram_id,\n         '201000000000' AS whatsapp_id,\n         'citizen@digilians.gov.eg' AS email,\n         'webchat' AS channel,\n         'ar' AS language\n  WHERE NOT EXISTS (SELECT 1 FROM found)\n)\nSELECT found.*, COALESCE(found.assigned_agent_id, 'a0000000-0000-0000-0000-000000000001'::uuid) AS assigned_agent_id, COALESCE(found.category_id, 11) AS category_id FROM (SELECT * FROM found UNION ALL SELECT * FROM fallback) found;"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    }
}

# Node 4: Update Ticket Status (now includes assigned_agent_id from auto-assign)
update_ticket = {
    "id": "node-update-ticket",
    "name": "Update Ticket Status in Postgres",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 660, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=UPDATE tickets\nSET status = CASE WHEN '{{ ($('Agent Response Webhook').first().json.body?.action || $('Agent Response Webhook').first().json.action) }}' = 'resolve' THEN 'resolved' ELSE 'in_progress' END,\n    assigned_agent = '{{ ($('Agent Response Webhook').first().json.body?.agent_name || $('Agent Response Webhook').first().json.agent_name || 'Support Agent').replace(/'/g, \"''\") }}',\n    assigned_agent_id = COALESCE('{{ ($('Auto-Assign Agent').first().json.body?.id || $('Auto-Assign Agent').first().json.id || 'a0000000-0000-0000-0000-000000000001') }}'::uuid, assigned_agent_id),\n    resolution_notes = '{{ ($('Agent Response Webhook').first().json.body?.agent_message || $('Agent Response Webhook').first().json.agent_message || '').replace(/'/g, \"''\") }}',\n    updated_at = CURRENT_TIMESTAMP\nWHERE ticket_number = '{{ $('Lookup Ticket & Customer').first().json.ticket_number }}';"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    }
}

# Node 5: Track First Response
track = {
    "id": "node-track-first-response",
    "name": "Track First Response Time",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 880, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=UPDATE tickets SET first_response_at = CURRENT_TIMESTAMP WHERE ticket_number = '{{ $('Lookup Ticket & Customer').first().json.ticket_number }}' AND first_response_at IS NULL RETURNING ticket_number, first_response_at;"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    },
    "notesInFlow": True,
    "notes": "Records first agent response timestamp. Idempotent."
}

# Node 6: Record Agent Message
record_msg = {
    "id": "node-insert-agent-msg",
    "name": "Record Agent Message",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 1100, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=INSERT INTO messages (conversation_id, customer_id, sender_type, content, intent)\nVALUES (\n  '{{ $('Lookup Ticket & Customer').first().json.conversation_id || 'a0000000-0000-0000-0000-000000000001' }}'::uuid,\n  '{{ $('Lookup Ticket & Customer').first().json.customer_id || 'a0000000-0000-0000-0000-000000000001' }}'::uuid,\n  'agent',\n  '{{ ($('Agent Response Webhook').first().json.body?.agent_message || $('Agent Response Webhook').first().json.agent_message || '').replace(/'/g, \"''\") }}',\n  'agent_direct_response'\n);"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    }
}

# Node 7: Audit Agent Action (keep)
audit = {
    "id": "node-audit-agent",
    "name": "Audit Agent Action",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 1320, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=INSERT INTO audit_logs (workflow_name, event_type, channel, payload)\nVALUES (\n  '04D_agent_response_bridge',\n  'agent_replied',\n  '{{ $('Lookup Ticket & Customer').first().json.channel || 'webchat' }}',\n  json_build_object(\n    'ticket_number', '{{ $('Lookup Ticket & Customer').first().json.ticket_number }}',\n    'agent', '{{ $('Agent Response Webhook').first().json.body?.agent_name || $('Agent Response Webhook').first().json.agent_name }}',\n    'action', '{{ $('Agent Response Webhook').first().json.body?.action || $('Agent Response Webhook').first().json.action }}',\n    'assigned_agent_id', '{{ ($('Auto-Assign Agent').first().json.body?.id || $('Auto-Assign Agent').first().json.id) }}'\n  )\n);"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    }
}

# Node 8: Log Performance Metrics
log_perf = {
    "id": "node-log-performance",
    "name": "Log Performance Metrics",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [max_x + 1540, 300],
    "parameters": {
        "operation": "executeQuery",
        "query": "=INSERT INTO agent_performance (agent_id, ticket_number, event_type, notes)\nSELECT\n  '{{ ($('Auto-Assign Agent').first().json.body?.id || $('Auto-Assign Agent').first().json.id || 'a0000000-0000-0000-0000-000000000001') }}'::uuid,\n  '{{ $('Lookup Ticket & Customer').first().json.ticket_number }}'::varchar,\n  'agent_replied',\n  json_build_object(\n    'action', '{{ $('Agent Response Webhook').first().json.body?.action || $('Agent Response Webhook').first().json.action }}',\n    'agent_message_length', length('{{ ($('Agent Response Webhook').first().json.body?.agent_message || $('Agent Response Webhook').first().json.agent_message || '') }}')\n  )::text\nWHERE '{{ ($('Auto-Assign Agent').first().json.body?.id || $('Auto-Assign Agent').first().json.id) }}' IS NOT NULL\n  AND '{{ ($('Auto-Assign Agent').first().json.body?.id || $('Auto-Assign Agent').first().json.id) }}' != 'a0000000-0000-0000-0000-000000000001';\n"
    },
    "credentials": {
        "postgres": {
            "id": "CS_PG_CRED_01",
            "name": "CustomerService Postgres"
        }
    },
    "notesInFlow": True,
    "notes": "Logs agent response event with metadata to agent_performance table."
}

# Node 9: Respond to Agent (keep)
respond = nodes[1]
respond["position"] = [max_x + 1920, 300]

# Assemble nodes
wf04d["nodes"] = [webhook, auto_assign, lookup, update_ticket, track, record_msg, audit, log_perf, respond]

# Assemble connections (sequential chain)
wf04d["connections"] = {
    "Agent Response Webhook": {
        "main": [[{"node": "Auto-Assign Agent", "type": "main", "index": 0}]]
    },
    "Auto-Assign Agent": {
        "main": [[{"node": "Lookup Ticket & Customer", "type": "main", "index": 0}]]
    },
    "Lookup Ticket & Customer": {
        "main": [[{"node": "Update Ticket Status in Postgres", "type": "main", "index": 0}]]
    },
    "Update Ticket Status in Postgres": {
        "main": [[{"node": "Track First Response Time", "type": "main", "index": 0}]]
    },
    "Track First Response Time": {
        "main": [[{"node": "Record Agent Message", "type": "main", "index": 0}]]
    },
    "Record Agent Message": {
        "main": [[{"node": "Audit Agent Action", "type": "main", "index": 0}]]
    },
    "Audit Agent Action": {
        "main": [[{"node": "Log Performance Metrics", "type": "main", "index": 0}]]
    },
    "Log Performance Metrics": {
        "main": [[{"node": "Respond to Agent", "type": "main", "index": 0}]]
    }
}

with open("infra/n8n/workflows/04D_agent_response_bridge.json", "w") as f:
    json.dump(wf04d, f, indent=2, ensure_ascii=False)

print("04D enhanced successfully")
print(f"Total nodes: {len(wf04d['nodes'])}")
for i, n in enumerate(wf04d["nodes"]):
    print(f"  {i+1}. {n['name']} at {n['position']}")
