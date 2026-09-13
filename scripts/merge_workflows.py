import json
import os
import glob

WORKFLOWS_DIR = r"e:\NexaServe\infra\n8n\workflows"

# Define the logical sequence for the master workflow layout
WORKFLOW_SEQUENCE = [
    "01_gateway_dispatcher.json",
    "02_customer_session_manager.json",
    "03_ai_intent_engine.json",
    "04A_order_lookup.json",
    "04B_knowledge_base_faq.json",
    "04C_human_escalation.json",
    "04D_agent_response_bridge.json",
    "05_conversation_logger.json",
    "06_output_channel_dispatcher.json"
]

COLORS = {
    "01": 4, # Blue
    "02": 3, # Green
    "03": 6, # Purple
    "04": 2, # Orange
    "05": 5, # Red/Pink
    "06": 1, # Default
}

TITLES = {
    "01_gateway_dispatcher.json": "🚀 Gateway & Ingress\nHandles incoming webhooks, validates payload, and normalizes channels.",
    "02_customer_session_manager.json": "👤 Session & Identity\nResolves customer identity and retrieves conversation history.",
    "03_ai_intent_engine.json": "🧠 AI Intent Engine\nProcesses natural language, determines intent, and applies safeguards.",
    "04A_order_lookup.json": "📦 Order Management\nLooks up order status from the backend.",
    "04B_knowledge_base_faq.json": "📚 Knowledge Base RAG\nAnswers FAQs using retrieved context.",
    "04C_human_escalation.json": "👨‍💻 Human Escalation\nRoutes conversation to a human agent.",
    "04D_agent_response_bridge.json": "🌉 Agent Bridge\nHandles responses coming back from human agents.",
    "05_conversation_logger.json": "📝 Audit & Logging\nPersists the conversation turn into the database.",
    "06_output_channel_dispatcher.json": "📤 Egress Dispatcher\nFormats and sends the final reply back to the user's channel."
}

def merge_workflows():
    workflows = {}
    for filepath in glob.glob(os.path.join(WORKFLOWS_DIR, "*.json")):
        basename = os.path.basename(filepath)
        if basename.startswith("Master_") or basename.startswith("00_"):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            workflows[basename] = json.load(f)
            
    master = {
        "id": "MASTER_PROFESSIONAL_001",
        "name": "NexaServe - Professional Enterprise Master Workflow",
        "nodes": [],
        "connections": {},
        "settings": {"executionOrder": "v1"}
    }
    
    all_nodes = []
    all_connections = {}
    node_names = set()
    
    current_x_offset = 0
    current_y_offset = 0
    padding_x = 400
    padding_y = 300
    
    # Sort files according to the defined sequence, then remaining ones
    sorted_files = [f for f in WORKFLOW_SEQUENCE if f in workflows]
    sorted_files += [f for f in workflows.keys() if f not in sorted_files]
    
    for idx, filename in enumerate(sorted_files):
        wf_data = workflows[filename]
        nodes = wf_data.get("nodes", [])
        if not nodes:
            continue
            
        # 1. Calculate Bounding Box of the subworkflow
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        for node in nodes:
            if "position" in node:
                x, y = node["position"]
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                
        # If no positions found (unlikely), set defaults
        if min_x == float('inf'):
            min_x, max_x, min_y, max_y = 0, 400, 0, 300
            
        width = (max_x - min_x) + 400 # Add space for node width and padding
        height = (max_y - min_y) + 300
        
        # 2. Shift calculation
        # We want to layout them horizontally, wrapping after 3 workflows
        if idx % 3 == 0 and idx != 0:
            current_x_offset = 0
            current_y_offset += 1500
            
        shift_x = current_x_offset - min_x + 200 # 200px internal padding from sticky note edge
        shift_y = current_y_offset - min_y + 200
        
        # 3. Create Sticky Note
        prefix = filename[:2]
        color = COLORS.get(prefix, 1)
        title = TITLES.get(filename, filename)
        
        all_nodes.append({
            "parameters": {
                "content": f"## {title}",
                "height": height,
                "width": width,
                "color": color
            },
            "id": f"note_{filename.replace('.json', '')}",
            "name": f"Note: {filename}",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [current_x_offset, current_y_offset]
        })
        
        name_map = {}
        for node in nodes:
            original_name = node["name"]
            new_name = original_name
            if new_name in node_names:
                new_name = f"{filename[:3]} {original_name}"
            node_names.add(new_name)
            name_map[original_name] = new_name
            
            new_node = dict(node)
            new_node["name"] = new_name
            if "id" in new_node:
                new_node["id"] = f"{filename}_{new_node['id']}"
                
            if "position" in new_node:
                new_node["position"] = [new_node["position"][0] + shift_x, new_node["position"][1] + shift_y]
                
            all_nodes.append(new_node)
            
        # 4. Migrate connections
        for src_node, outputs in wf_data.get("connections", {}).items():
            new_src_node = name_map.get(src_node, src_node)
            if new_src_node not in all_connections:
                all_connections[new_src_node] = {"main": []}
                
            for output_idx, target_list in enumerate(outputs.get("main", [])):
                while len(all_connections[new_src_node]["main"]) <= output_idx:
                    all_connections[new_src_node]["main"].append([])
                    
                for target in target_list:
                    new_target_name = name_map.get(target["node"], target["node"])
                    all_connections[new_src_node]["main"][output_idx].append({
                        "node": new_target_name,
                        "type": target["type"],
                        "index": target["index"]
                    })
                    
        # Advance layout pointer
        current_x_offset += width + padding_x

    master["nodes"] = all_nodes
    master["connections"] = all_connections
    
    with open(os.path.join(WORKFLOWS_DIR, "Master_Workflow_Enterprise.json"), "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
        
    print(f"Generated Professional Layout: Master_Workflow_Enterprise.json with {len(all_nodes)} nodes.")

if __name__ == "__main__":
    merge_workflows()
