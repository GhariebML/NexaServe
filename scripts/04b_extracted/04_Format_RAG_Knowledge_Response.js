/* === FORMAT RAG KNOWLEDGE RESPONSE & CALIBRATED EVIDENCE GATE === */
const inputItems = $input.all().map(item => item.json || {});
const rows = inputItems.flatMap(item => Array.isArray(item) ? item : (Array.isArray(item.results) ? item.results : [item]));
const detectorData = $('Program Detector & Query Normalizer').first()?.json || {};
const locale = detectorData.locale || 'ar';
const isAr = locale === 'ar';
const programScope = detectorData.program_scope || 'COMMON';
const isAmbiguous = detectorData.is_ambiguous;
const topicCategory = detectorData.topic_category || '';
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

  // Score alone is not evidence: require meaningful lexical/keyword overlap or
  // an explicit deterministic topic-category match. This prevents model fallback
  // from turning a nearby but unrelated result into a factual answer.
  const lexicalEvidence = Number(top.lexical_score || 0) >= 15;
  const keywordEvidence = Number(top.keyword_match_count || 0) >= 1 && Number(top.content_match_count || 0) >= 2;
  const explicitTopicEvidence = Boolean(topicCategory) && top.category === topicCategory;
  if (!lexicalEvidence && !keywordEvidence && !explicitTopicEvidence) {
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
    context = sorted.slice(0, 3).map(kb => {
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
      source_url: top.source_url || null,
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
}