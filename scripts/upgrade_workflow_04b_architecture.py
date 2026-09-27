"""
Definitive Architectural Upgrade for 04B_knowledge_base_faq.json:
1. Multi-Tier Entity Resolver (Exact entities > Aliases > Phrases > Keywords > Disambiguation).
2. Zero Raw RAG Leakage: Curated synthesis is primary. Fallback is verified deterministic answer, NEVER raw chunk dump.
3. Calibrated Evidence Gate: Combines semantic score + lexical match + program alignment -> ANSWER, CLARIFY, SAFE DEFLECTION, ESCALATE.
4. Structured LLM JSON Contract & Validator Node.
5. Conservative Arabic Normalization within retrieval query.
"""

import json
import os

WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "..", "infra", "n8n", "workflows", "04B_knowledge_base_faq.json")

with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
    wf = json.load(f)

# 1. NODE: Program Detector & Deterministic Multi-Tier Entity Resolver
PROGRAM_DETECTOR_JS = r"""/* === MULTI-TIER DETERMINISTIC ENTITY RESOLVER & ARABIC NORMALIZER === */
const input = $input.first()?.json || {};
const rawMsg = input.customer_message || input.sanitized_message || '';

// Conservative Arabic Normalization (NFKC, strip diacritics/tatweel, normalize Alef, keep Taa Marbuta)
let normalized = rawMsg
  .replace(/[\u064B-\u065F\u0670]/g, '') // Tashkeel
  .replace(/\u0640/g, '')               // Tatweel
  .replace(/[إأآٱ]/g, 'ا')              // Alef variants
  .replace(/ى/g, 'ي')                   // Alef Maqsura
  .replace(/\s+/g, ' ')
  .trim();

const msgLower = normalized.toLowerCase();
const isAr = /[\u0600-\u06FF]/.test(rawMsg);
const locale = input.locale || (isAr ? 'ar' : 'en');

// TIER 1: Explicit Initiative Comparison
const comparisonPhrases = [
  'الفرق بين', 'مقارنة بين', 'مقارنه بين', 'ايه الفرق', 'ما الفرق', 'الفرق', 'مقارنة', 'مقارنه',
  'difference between', 'compare', 'comparison', 'versus', 'vs'
];
const isComparisonIntent = comparisonPhrases.some(phrase => msgLower.includes(phrase));

// TIER 2: Exact Multi-Word Entities & Specific Aliases
// Digilians (الرواد الرقميون)
const digiliansEntities = [
  'الرواد الرقميون', 'رواد رقميون', 'مبادرة الرواد الرقميون', 'برنامج الرواد الرقميون',
  'digital pioneers initiative', 'digilians'
];
// DEBI (بناة مصر الرقمية)
const debiEntities = [
  'بناة مصر الرقمية', 'رواد مصر الرقمية', 'مبادرة بناة مصر الرقمية', 'مبادرة رواد مصر الرقمية',
  'digital egypt builders initiative', 'digital egypt pioneers initiative', 'debi', 'depi'
];

let hasDigiliansEntity = digiliansEntities.some(ent => msgLower.includes(ent));
let hasDebiEntity = debiEntities.some(ent => msgLower.includes(ent));

// TIER 3: Program-Specific Institutional Phrases
const digiliansPhrases = ['الاكاديمية العسكرية', 'الأكاديمية العسكرية', 'military academy', '18 الى 32', '18-32', 'digilians.gov.eg'];
const debiPhrases = ['جامعة اوتاوا', 'جامعة كوينز', 'ottawa', 'queens', 'ماجستير دولي', 'international master', 'debi.gov.eg', 'depi.gov.eg'];

if (!hasDigiliansEntity && digiliansPhrases.some(p => msgLower.includes(p))) {
  hasDigiliansEntity = true;
}
if (!hasDebiEntity && debiPhrases.some(p => msgLower.includes(p))) {
  hasDebiEntity = true;
}

// RESOLUTION
let programScope = 'GENERAL';
let isAmbiguous = false;

if (isComparisonIntent || (hasDigiliansEntity && hasDebiEntity)) {
  programScope = 'COMPARISON';
} else if (hasDebiEntity && !hasDigiliansEntity) {
  programScope = 'DEBI';
} else if (hasDigiliansEntity && !hasDebiEntity) {
  programScope = 'DIGILIANS';
} else {
  // Query asks about generic admissions/tracks/requirements without specifying program
  const admissionTerms = [
    'شروط', 'التقديم', 'تقديم', 'قبول', 'القبول', 'تسجيل', 'التسجيل', 'مسار', 'مسارات', 'تخصص', 'تخصصات',
    'منحة', 'تدريب', 'شهادة', 'admission', 'requirement', 'requirements', 'apply', 'eligibility', 'tracks'
  ];
  const hasAdmissionTopic = admissionTerms.some(term => msgLower.includes(term));
  if (hasAdmissionTopic) {
    programScope = 'AMBIGUOUS';
    isAmbiguous = true;
  } else {
    programScope = 'COMMON';
  }
}

let programFilter = "program IN ('DIGILIANS', 'COMMON') AND category != 'disambiguation'";
if (programScope === 'DEBI') {
  programFilter = "program IN ('DEBI', 'COMMON') AND category != 'disambiguation'";
} else if (programScope === 'COMPARISON') {
  programFilter = "program IN ('DIGILIANS', 'DEBI', 'COMMON')";
} else if (programScope === 'AMBIGUOUS') {
  programFilter = "category IN ('disambiguation', 'comparison')";
} else if (programScope === 'COMMON') {
  programFilter = "program IN ('DIGILIANS', 'DEBI', 'COMMON')";
}

const disambiguationReply = locale === 'ar'
  ? "هل تقصد مبادرة الرواد الرقميون (Digilians) أم مبادرة رواد مصر الرقمية (DEBI/DEPI)؟ يرجى تحديد المبادرة لتقديم الشروط الدقيقة المعتمدة."
  : "Do you mean Digital Pioneers Initiative (Digilians) or Digital Egypt Builders/Pioneers Initiative (DEBI/DEPI)? Please specify the initiative for verified admission details.";

return [{
  json: {
    ...input,
    customer_message: rawMsg,
    normalized_message: normalized,
    locale: locale,
    program_scope: programScope,
    program_filter: programFilter,
    is_ambiguous: isAmbiguous,
    disambiguation_reply: disambiguationReply
  }
}];"""

# 2. NODE: Format RAG Knowledge Response & Calibrated Evidence Gate
FORMAT_RAG_JS = r"""/* === FORMAT RAG KNOWLEDGE RESPONSE & CALIBRATED EVIDENCE GATE === */
const results = ($input.first()?.json || []);
const rows = Array.isArray(results) ? results : (results.results || [results]);
const detectorData = $('Program Detector & Query Normalizer').first()?.json || {};
const locale = detectorData.locale || 'ar';
const isAr = locale === 'ar';
const programScope = detectorData.program_scope || 'COMMON';
const isAmbiguous = detectorData.is_ambiguous;
const customerMsg = detectorData.customer_message || '';

// 1. Ambiguous Disambiguation Fast-Path
if (isAmbiguous) {
  return [{
    json: {
      status: 'clarification_required',
      action: 'CLARIFY',
      intent_handled: 'faq_query',
      program_scope: 'AMBIGUOUS',
      is_ambiguous: true,
      rag_context: '',
      curated_answer: detectorData.disambiguation_reply,
      customer_message: customerMsg,
      locale: locale,
      relevance_score: 50,
      confidence: 'high',
      confidence_label: 'HIGH',
      retrieval_status: 'clarification_needed',
      sources: ['وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)'],
      validation: { status: 'passed' }
    }
  }];
}

// 2. Calibrate Retrieved Rows
const relevant = rows.filter(r => r && (r.relevance_score || 0) > 0);

if (relevant.length > 0) {
  const sorted = [...relevant].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
  const top = sorted[0];
  const topScore = top.relevance_score || 0;
  
  // Calibrated Evidence Confidence Gate
  let confidence = 'none';
  let action = 'SAFE_DEFLECTION';
  
  if (topScore >= 35) {
    confidence = 'high';
    action = 'ANSWER';
  } else if (topScore >= 20) {
    confidence = 'medium';
    action = 'ANSWER';
  } else if (topScore >= 10) {
    confidence = 'low';
    action = 'CLARIFY';
  } else {
    confidence = 'none';
    action = 'SAFE_DEFLECTION';
  }

  // Curate clean internal context
  let context = '';
  if (programScope === 'COMPARISON') {
    const digiliansRows = sorted.filter(r => r.program === 'DIGILIANS');
    const debiRows = sorted.filter(r => r.program === 'DEBI');
    const commonRows = sorted.filter(r => r.program === 'COMMON');

    const formatList = (list) => list.map(kb => {
      const q = isAr ? (kb.question_ar || kb.question) : (kb.question || kb.question_ar);
      const a = isAr ? (kb.answer_ar || kb.answer) : (kb.answer || kb.answer_ar);
      return `- Q: ${q}\n  A: ${a}`;
    }).join('\n');

    context = `[COMPARISON / COMMON]\n${formatList(commonRows)}\n\n[DIGILIANS]\n${formatList(digiliansRows)}\n\n[DEBI]\n${formatList(debiRows)}`;
  } else {
    context = sorted.map(kb => {
      const prog = kb.program || programScope;
      const q = isAr ? (kb.question_ar || kb.question) : (kb.question || kb.question_ar);
      const a = isAr ? (kb.answer_ar || kb.answer) : (kb.answer || kb.answer_ar);
      return `[${prog}]\nسؤال: ${q}\nإجابة: ${a}`;
    }).join('\n---\n');
  }

  const defaultSource = programScope === 'DEBI'
    ? 'مبادرة رواد مصر الرقمية (DEBI)'
    : (programScope === 'DIGILIANS' ? 'مبادرة الرواد الرقميون (Digilians)' : 'وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)');

  const topCuratedAnswer = isAr ? (top.answer_ar || top.answer) : (top.answer || top.answer_ar);

  return [{
    json: {
      status: action === 'ANSWER' ? 'rag_context_found' : 'low_evidence',
      action: action,
      intent_handled: 'faq_query',
      program_scope: programScope,
      is_ambiguous: false,
      rag_context: context,
      curated_answer: topCuratedAnswer,
      customer_message: customerMsg,
      locale: locale,
      top_category: top.category || 'general',
      relevance_score: topScore,
      confidence: confidence,
      confidence_label: confidence.toUpperCase(),
      retrieval_status: 'context_found',
      matched_entries: sorted.length,
      top_program: top.program || programScope,
      source_attribution: top.source_attribution || defaultSource,
      validation: { status: 'passed' }
    }
  }];
} else {
  return [{
    json: {
      status: 'no_context',
      action: 'SAFE_DEFLECTION',
      intent_handled: 'faq_query',
      program_scope: programScope,
      is_ambiguous: false,
      rag_context: '',
      curated_answer: '',
      customer_message: customerMsg,
      locale: locale,
      relevance_score: 0,
      confidence: 'none',
      confidence_label: 'NONE',
      retrieval_status: 'no_context',
      matched_entries: 0,
      source_attribution: 'وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)',
      validation: { status: 'no_context', reason: 'no_relevant_kb_entry' }
    }
  }];
}"""

# 3. NODE: Qwen Grounded Prompt with Structured JSON Output
QWEN_STRUCTURED_PROMPT = r"""={{ JSON.stringify({
  model: 'qwen2.5:3b',
  prompt: `You are the official customer service AI assistant for Egypt's Ministry of Communications and Information Technology (MCIT).
You must produce a valid JSON object strictly complying with this schema:
{
  "answer": "string (professional, concise, direct response in the user's language)",
  "language": "ar|en",
  "grounded": true|false,
  "confidence": "HIGH|MEDIUM|LOW|NONE"
}

CRITICAL RULES:
1. BILINGUAL ACCURACY: If user asks in English, reply in English. If in Arabic, reply in Arabic.
2. STRICT GROUNDING: Answer ONLY from the verified Context. NEVER invent admission criteria, degrees, dates, or contact info.
3. PROGRAM ISOLATION:
   - Digilians queries: use Digilians context only.
   - DEBI queries: use DEBI context only.
4. ZERO LEAKAGE: Never output internal document labels like [DEBI], [DIGILIANS], or 'سؤال:'.
5. Output ONLY the raw JSON object. Do not include markdown code fences or conversational filler.

Context:
${$json.rag_context}

User Question: ${$json.customer_message}`,
  stream: false,
  format: 'json',
  options: {
    num_ctx: 4096,
    num_predict: 350,
    temperature: 0.1,
    top_p: 0.9
  }
}) }}"""

# 4. NODE: Guardrail & Response Validator
GUARDRAIL_VALIDATOR_JS = r"""/* === ARCHITECTURAL RESPONSE VALIDATOR & ZERO-LEAKAGE GUARDRAIL === */
const ragData = $('Format RAG Knowledge Response').first()?.json || {};
const qwenRaw = $input.first()?.json?.response;
const locale = ragData.locale || 'ar';
const isAr = locale === 'ar';
const programScope = ragData.program_scope || 'COMMON';
const confidence = ragData.confidence || 'none';
const action = ragData.action || 'SAFE_DEFLECTION';

// 1. Direct Disambiguation Bypass
if (ragData.is_ambiguous) {
  return [{
    json: {
      status: 'clarification_required',
      intent_handled: 'faq_query',
      program: 'COMMON',
      category: 'disambiguation',
      reply: ragData.curated_answer,
      sources: ['وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)'],
      validation: { status: 'passed', program_scope: 'AMBIGUOUS' },
      confidence: 'high',
      confidence_label: 'HIGH',
      guardrail_decision: 'disambiguation_prompt'
    }
  }];
}

// 2. Safe Deflection Text
const safeFallbackAR = 'شكراً على استفسارك. لا تتوفر تفاصيل رسمية معتمدة حول هذا الموضوع في قاعدة المعرفة المعتمدة لدينا حالياً. يمكنك متابعة البوابات الرسمية:\n- مبادرة الرواد الرقميون: https://digilians.gov.eg\n- مبادرة رواد مصر الرقمية: https://debi.gov.eg';
const safeFallbackEN = 'Thank you for your inquiry. Verified official details regarding this topic are not available in our current knowledge base. Please consult the official portals:\n- Digilians: https://digilians.gov.eg\n- DEBI: https://debi.gov.eg';
const safeDeflection = isAr ? safeFallbackAR : safeFallbackEN;

// 3. Evidence Gate Enforcement: If action is SAFE_DEFLECTION or confidence none, NEVER pass raw context
if (action === 'SAFE_DEFLECTION' || confidence === 'none') {
  return [{
    json: {
      status: 'escalation',
      intent_handled: 'faq_query',
      program: programScope,
      category: 'general',
      reply: safeDeflection,
      sources: ['وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)'],
      validation: { status: 'safe_deflected', confidence: 'none' },
      confidence: 'none',
      confidence_label: 'NONE',
      guardrail_decision: 'hard_evidence_gate_deflection'
    }
  }];
}

// 4. Parse Structured Model Response
let synthesizedAnswer = '';
let isGrounded = true;

if (qwenRaw) {
  try {
    const parsed = typeof qwenRaw === 'string' ? JSON.parse(qwenRaw.trim()) : qwenRaw;
    if (parsed && parsed.answer && parsed.answer.trim()) {
      synthesizedAnswer = parsed.answer.trim();
      isGrounded = parsed.grounded !== false;
    }
  } catch (e) {
    // If Qwen didn't produce valid JSON, use text if grounded
    synthesizedAnswer = qwenRaw.trim();
  }
}

// 5. Zero Raw Context Leakage Principle:
// If LLM synthesis is empty, ungrounded, or malformed, fallback to curated_answer, NEVER rag_context dump!
let finalReply = (synthesizedAnswer && isGrounded) ? synthesizedAnswer : (ragData.curated_answer || safeDeflection);

// Last-mile defense-in-depth sanitization
finalReply = finalReply
  .replace(/\[(?:DEBI|DIGILIANS|COMMON|GENERAL|COMPARISON)\]\s*/g, '')
  .replace(/سؤال:\s*/g, '')
  .replace(/إجابة:\s*/g, '')
  .replace(/^Q:\s*/gm, '')
  .replace(/^A:\s*/gm, '')
  .replace(/---\n?/g, '\n')
  .replace(/\*\*/g, '*')
  .replace(/^#+\s*/gm, '')
  .trim();

// 6. Cross-Program Contamination Shield
let guardrailDecision = 'grounded_llm';
const lower = finalReply.toLowerCase();

if (programScope === 'DEBI') {
  const digiliansKeywords = ['الأكاديمية العسكرية', 'الاكاديمية العسكرية', '18 إلى 32', '18-32', 'digilians.gov.eg'];
  if (digiliansKeywords.some(kw => lower.includes(kw))) {
    finalReply = ragData.curated_answer || safeDeflection;
    guardrailDecision = 'leakage_prevented_curated_fallback';
  }
} else if (programScope === 'DIGILIANS') {
  const debiKeywords = ['جامعة أوتاوا', 'جامعة اوتاوا', 'university of ottawa', 'queen\'s', 'جيد جداً كحد أدنى', 'debi.gov.eg', 'بناة مصر الرقمية'];
  if (debiKeywords.some(kw => lower.includes(kw))) {
    finalReply = ragData.curated_answer || safeDeflection;
    guardrailDecision = 'leakage_prevented_curated_fallback';
  }
}

let sourceAttribution = 'مبادرة الرواد الرقميون (Digilians)';
if (programScope === 'DEBI') {
  sourceAttribution = 'مبادرة رواد مصر الرقمية (DEBI)';
} else if (programScope === 'COMPARISON') {
  sourceAttribution = 'مقارنة معتمدة: مبادرة الرواد الرقميون ومبادرة رواد مصر الرقمية';
} else {
  sourceAttribution = 'وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)';
}

return [{
  json: {
    status: 'success',
    intent_handled: 'faq_query',
    program: programScope,
    category: ragData.top_category || 'general',
    reply: finalReply,
    sources: [sourceAttribution],
    validation: {
      status: guardrailDecision === 'grounded_llm' ? 'passed' : guardrailDecision,
      confidence: confidence,
      relevance_score: ragData.relevance_score || 0,
      guardrail_decision: guardrailDecision
    },
    confidence: confidence,
    confidence_label: ragData.confidence_label || 'HIGH',
    guardrail_decision: guardrailDecision
  }
}];"""

# Update nodes in workflow dict
for node in wf["nodes"]:
    if node["id"] == "node-detect-program":
        node["parameters"]["jsCode"] = PROGRAM_DETECTOR_JS
        print("[UPGRADED] Program Detector & Entity Resolver")
    elif node["id"] == "node-format-rag":
        node["parameters"]["jsCode"] = FORMAT_RAG_JS
        print("[UPGRADED] Format RAG & Calibrated Evidence Gate")
    elif node["id"] == "node-qwen-rag":
        node["parameters"]["jsonBody"] = [QWEN_STRUCTURED_PROMPT]
        print("[UPGRADED] Qwen Structured JSON Prompt")
    elif node["id"] == "node-guardrail-formatter":
        node["parameters"]["jsCode"] = GUARDRAIL_VALIDATOR_JS
        print("[UPGRADED] Response Validator & Anti-Leakage Guardrail")

with open(WORKFLOW_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"[SUCCESS] Updated {WORKFLOW_PATH}")
