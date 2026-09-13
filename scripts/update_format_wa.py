import json

path = 'infra/n8n/workflows/06_output_channel_dispatcher.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for node in data.get('nodes', []):
    if node.get('id') == 'node-format-whatsapp':
        node['parameters']['jsCode'] = "const item = $input.first()?.json || {};\nconst recipient = item.phone_number || item.channel_user_id || item.customer?.phone_number || '+966501234567';\nconst text = item.reply || item.final_reply || item.message || '';\n\nreturn [{\n  json: {\n    channel: 'whatsapp',\n    recipient: recipient,\n    dispatched: true,\n    meta_payload: {\n      messaging_product: 'whatsapp',\n      recipient_type: 'individual',\n      to: recipient.replace(/[^0-9]/g, ''),\n      type: 'text',\n      text: { body: text }\n    },\n    message: text,\n    timestamp: new Date().toISOString()\n  }\n}];"
        print('Updated node-format-whatsapp!')

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('Done!')
