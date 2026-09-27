/* === ARCHITECTURAL RESPONSE VALIDATOR & ZERO-LEAKAGE GUARDRAIL === */
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
}];