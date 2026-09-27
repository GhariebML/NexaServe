# -*- coding: utf-8 -*-
"""
Patch 04B Workflow:
1. Fix program detector: prevent 'depi' keyword from shadowing Digilians detection
2. Fix guardrail formatter: strip raw [PROGRAM] / سؤال:/إجابة: prefixes from replies
3. Increase num_predict for better LLM responses
"""
import json
import os
import re

WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "..", "infra", "n8n", "workflows", "04B_knowledge_base_faq.json")

with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
    wf = json.load(f)

for node in wf["nodes"]:
    # ================================================================
    # FIX 1: Program Detector - remove 'depi' from Digilians keywords
    # 'depi' is too broad and conflicts with 'DEBI' detection.
    # Also remove 'الرواد' (too broad, matches both programs).
    # Add more specific Digilians keywords instead.
    # ================================================================
    if node["id"] == "node-detect-program":
        js = node["parameters"]["jsCode"]
        
        # Fix Digilians keywords: remove 'depi' and 'الرواد' (too broad)
        old_digilians = "'digilians', 'الرواد الرقميون', 'رواد رقميون', 'الرواد', 'depi', 'الأكاديمية العسكرية', 'الاكاديمية العسكرية'"
        new_digilians = "'digilians', 'الرواد الرقميون', 'رواد رقميون', 'المبادرة الوطنية', 'الأكاديمية العسكرية', 'الاكاديمية العسكرية', 'national initiative'"
        js = js.replace(old_digilians, new_digilians)
        
        node["parameters"]["jsCode"] = js
        print("[PATCHED] Program Detector: removed ambiguous 'depi'/'الرواد' keywords from Digilians list")

    # ================================================================
    # FIX 2: Guardrail Formatter - strip raw RAG prefixes from replies
    # ================================================================
    if node["id"] == "node-guardrail-formatter":
        js = node["parameters"]["jsCode"]
        
        # Add prefix stripping after the reply is assembled
        old_clean = "// Clean markdown bold for WhatsApp"
        new_clean = """// Clean raw RAG prefixes that shouldn't appear in customer-facing replies
  finalReply = finalReply.replace(/\\[(?:DEBI|DIGILIANS|COMMON|GENERAL|COMPARISON)\\]\\s*/g, '');
  finalReply = finalReply.replace(/سؤال:\\s*/g, '').replace(/إجابة:\\s*/g, '');
  finalReply = finalReply.replace(/^Q:\\s*/gm, '').replace(/^A:\\s*/gm, '');
  finalReply = finalReply.replace(/---\\n?/g, '\\n');
  finalReply = finalReply.trim();

  // Clean markdown bold for WhatsApp"""
        js = js.replace(old_clean, new_clean)
        
        node["parameters"]["jsCode"] = js
        print("[PATCHED] Guardrail Formatter: added raw prefix stripping")
    
    # ================================================================
    # FIX 3: Increase LLM num_predict for fuller responses
    # ================================================================
    if node["id"] == "node-qwen-rag":
        body = node["parameters"].get("jsonBody", [""])[0]
        body = body.replace("num_predict: 220", "num_predict: 400")
        body = body.replace("num_ctx: 2048", "num_ctx: 4096")
        node["parameters"]["jsonBody"] = [body]
        print("[PATCHED] Qwen RAG: increased num_predict=400, num_ctx=4096")

with open(WORKFLOW_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("\n[OK] Workflow 04B patched successfully. Re-import to n8n to apply.")
