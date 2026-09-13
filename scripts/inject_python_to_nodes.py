"""
Inject Python equivalents into n8n workflow Code Nodes.
This script embeds the Python equivalent code as a prominent, professional bilingual header
inside each Code node's jsCode parameter, and adds notesInFlow to the node.
"""

import os
import json
import glob
import re

WORKFLOWS_DIR = r"e:\NexaServe\infra\n8n\workflows"
PYTHON_EQUIV_FILE = r"e:\NexaServe\docs\python_equivalents.py"

# Read the Python equivalents file
with open(PYTHON_EQUIV_FILE, "r", encoding="utf-8") as f:
    py_content = f.read()

# Map node names to their Python function definitions in python_equivalents.py
NODE_PYTHON_MAP = {
    "Channel Ingress & PII Sanitizer": "channel_ingress_and_pii_sanitizer",
    "General Support Handler": "general_support_handler",
    "Assemble Response & Metrics": "assemble_response_and_metrics",
    "Compile Session Context": "compile_session_context",
    "Guardrails & Safety Filter": "guardrails_safety_filter",
    "Build Prompt Payload": "build_prompt_payload",
    "Parse & Validate AI Schema": "parse_and_validate_ai_schema",
    "Format Order Response": "format_order_response",
    "Format RAG Knowledge Response": "format_rag_knowledge_response",
    "Guardrail & Professional Formatter": "guardrail_and_professional_formatter",
    "Format Escalation Notice": "format_escalation_notice",
    "Return Log Confirmation": "return_log_confirmation",
    "Format WhatsApp Payload": "format_whatsapp_payload",
    "Format Telegram Payload": "format_telegram_payload",
    "Format Email Payload": "format_email_payload",
    "Format Webchat Payload": "format_webchat_payload",
}

def extract_function_code(func_name: str, full_text: str) -> str:
    """Extract function definition and body from full_text."""
    pattern = rf"(def {func_name}\b.*?)(?=\ndef |\Z)"
    match = re.search(pattern, full_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def update_workflow(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        wf = json.load(f)

    modified = False
    for node in wf.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.code":
            continue

        node_name = node.get("name", "")
        # Match node name (support prefix if any)
        matched_fn = None
        for base_name, fn_name in NODE_PYTHON_MAP.items():
            if base_name in node_name:
                matched_fn = fn_name
                break

        if not matched_fn:
            continue

        py_func = extract_function_code(matched_fn, py_content)
        if not py_func:
            continue

        params = node.setdefault("parameters", {})
        current_js = params.get("jsCode", "")

        # Clean any existing injected header
        if "PYTHON EQUIVALENT" in current_js:
            parts = current_js.split("/* === ACTIVE JAVASCRIPT IMPLEMENTATION === */")
            if len(parts) > 1:
                current_js = parts[1].strip()

        header = (
            "/* ==========================================================================\n"
            "   🐍 PYTHON ALTERNATIVE / البديل البرمجي بلغة بايثون لنفس المهمة\n"
            "   --------------------------------------------------------------------------\n"
            "   This node is documented in both Python and JavaScript.\n"
            "   Below is the production-grade Python function equivalent:\n\n"
            f"{py_func}\n"
            "   ========================================================================== */\n\n"
            "/* === ACTIVE JAVASCRIPT IMPLEMENTATION === */\n"
        )

        params["jsCode"] = header + current_js
        node["notesInFlow"] = True
        node["notes"] = f"🐍 Python & ⚡ JS Dual-Language Node\nEquivalent: {matched_fn}()"
        modified = True

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
        print(f"Updated: {os.path.basename(file_path)}")

def main():
    for filepath in glob.glob(os.path.join(WORKFLOWS_DIR, "*.json")):
        basename = os.path.basename(filepath)
        if basename.startswith("Master_"):
            continue
        update_workflow(filepath)

if __name__ == "__main__":
    main()
