import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const intentWorkflow = JSON.parse(fs.readFileSync(new URL('../infra/n8n/workflows/03_ai_intent_engine.json', import.meta.url), 'utf8'));
const ragWorkflow = JSON.parse(fs.readFileSync(new URL('../infra/n8n/workflows/04B_knowledge_base_faq.json', import.meta.url), 'utf8'));

const nodeCode = (workflow, name) => workflow.nodes.find((node) => node.name === name)?.parameters?.jsCode;

function runCode(code, { input = {}, named = {} } = {}) {
  const inputApi = {
    first: () => ({ json: input }),
    all: () => Array.isArray(input) ? input.map((json) => ({ json })) : [{ json: input }],
  };
  const namedApi = (name) => ({ first: () => ({ json: named[name] || {} }) });
  return new Function('$input', '$', code)(inputApi, namedApi);
}

function runIntent(message, history = []) {
  return runCode(nodeCode(intentWorkflow, 'Build Prompt Payload'), {
    input: {
      customer_message: message,
      sanitized_message: message,
      conversation_history: history,
      locale: /[\u0600-\u06FF]/.test(message) ? 'ar' : 'en',
    },
  })[0].json;
}

function runDetector(message, history = []) {
  return runCode(nodeCode(ragWorkflow, 'Program Detector & Query Normalizer'), {
    input: { customer_message: message, locale: /[\u0600-\u06FF]/.test(message) ? 'ar' : 'en', conversation_history: history },
  })[0].json;
}

function runFormatter(message, rows, { locale = 'en', scope = 'DEBI', category = '' } = {}) {
  const detector = {
    customer_message: message,
    locale,
    program_scope: scope,
    topic_category: category,
    is_ambiguous: false,
  };
  return runCode(nodeCode(ragWorkflow, 'Format RAG Knowledge Response'), {
    input: rows,
    named: { 'Program Detector & Query Normalizer': detector },
  })[0].json;
}

function runGuardrail(ragData, modelResponse) {
  return runCode(nodeCode(ragWorkflow, 'Guardrail & Professional Formatter'), {
    input: modelResponse == null ? {} : { response: modelResponse },
    named: { 'Format RAG Knowledge Response': ragData },
  })[0].json;
}

const jobAtNasaRows = [
  {
    id: 128, program: 'DEBI', category: 'scraped_faq',
    question: 'ما هي مدة تدريب DEPI Industry؟', answer: 'المدة التدريبية للبرنامج هي أربعة أشهر بحد أقصى.',
    question_ar: 'ما هي مدة تدريب DEPI Industry؟', answer_ar: 'المدة التدريبية للبرنامج هي أربعة أشهر بحد أقصى.',
    relevance_score: 40.4157, lexical_score: 10, semantic_score: 30.4157,
    keyword_match_count: 0, content_match_count: 1,
    source_url: 'https://depi.gov.eg/content/faqs',
  },
  {
    id: 103, program: 'DEBI', category: 'scraped_faq',
    question: 'What is a Job Profile?', answer: 'A job profile describes role requirements.',
    question_ar: 'ما تعريف ال Job Profile؟', answer_ar: 'هي متطلبات وظيفية بأدوار محددة.',
    relevance_score: 32.549, lexical_score: 10, semantic_score: 22.549,
    keyword_match_count: 0, content_match_count: 1,
    source_url: 'https://depi.gov.eg/content/faqs',
  },
];

test('program FAQs mentioning tracks are never sent to order lookup', () => {
  for (const message of [
    'ايه مسارات DEPI؟',
    'ممكن أعرف التخصصات؟',
    'شروط التقديم ايه؟',
    'What are the DEPI tracks?',
    'What specializations are available?',
    'What are the admission requirements?',
  ]) {
    const result = runIntent(message);
    assert.equal(result.ai_output.intent, 'faq_query', message);
  }
});

test('real order semantics still route to order lookup', () => {
  for (const message of ['Where is my order?', 'Check my tracking number.']) {
    const result = runIntent(message);
    assert.equal(result.ai_output.intent, 'order_lookup', message);
  }
});

test('human escalation keeps precedence over other intent signals', () => {
  const result = runIntent('I am angry about my order; please connect me to a human.');
  assert.equal(result.ai_output.intent, 'human_escalation');
  assert.equal(result.ai_output.requires_human, true);
});

test('common unrelated requests receive an explicit out-of-scope response', () => {
  for (const message of [
    'What is the weather in Cairo?',
    "Who won yesterday's football match?",
    'Write me a Python script.',
  ]) {
    const result = runIntent(message);
    assert.equal(result.ai_output.intent, 'general_support');
    assert.match(result.ai_output.direct_response, /outside|only|المعلومات|يختص/i, message);
  }
});

test('RAG program resolver retains the last explicit customer program for a FAQ follow-up', () => {
  const history = [{ sender_type: 'customer', content: 'عاوز أعرف مسارات DEPI' }];
  const result = runDetector('طب والشروط؟', history);
  assert.equal(result.program_scope, 'DEBI');
  assert.equal(result.topic_category, 'debi_conditions');
  assert.equal(result.program_resolved_from_history, true);
});

test('RAG program resolver keeps DEPI context for a data-tracks follow-up', () => {
  const history = [{ sender_type: 'customer', content: 'إيه هي مبادرة DEPI؟' }];
  const result = runDetector('هل فيها مسارات للـData?', history);
  assert.equal(result.program_scope, 'DEBI');
  assert.equal(result.topic_category, 'debi_tracks');
});

test('session history is preserved across the intent workflow output', () => {
  const history = [{ sender_type: 'customer', content: 'عاوز أعرف مسارات DEPI' }];
  const build = runCode(nodeCode(intentWorkflow, 'Build Prompt Payload'), {
    input: { customer_message: 'طب والشروط؟', sanitized_message: 'طب والشروط؟', conversation_history: history, locale: 'ar' },
  })[0].json;
  assert.deepEqual(build.conversation_history, history);

  const parseNode = nodeCode(intentWorkflow, 'Parse & Validate AI Schema');
  const parsed = runCode(parseNode, {
    input: { response: JSON.stringify({ intent: 'faq_query', confidence: 0.9 }) },
    named: { 'Build Prompt Payload': build },
  })[0].json;
  assert.deepEqual(parsed.conversation_history, history);
});

test('NASA guarantee retrieval cannot pass the evidence gate on semantic similarity alone', () => {
  const result = runFormatter('Does DEPI guarantee a job at NASA?', jobAtNasaRows);
  assert.notEqual(result.action, 'ANSWER');
  assert.equal(result.evidence_supported, false);
  assert.equal(result.status, 'low_evidence');
});

test('unsupported Arabic guarantee and employment claims fail closed', () => {
  for (const message of ['هل DEPI تضمن وظيفة في ناسا؟', 'هل المبادرة تضمن التوظيف؟', 'هل DEPI تضمن منحة دراسية كاملة؟']) {
    const result = runFormatter(message, jobAtNasaRows, { locale: 'ar' });
    assert.notEqual(result.action, 'ANSWER', message);
    assert.equal(result.evidence_supported, false, message);
  }
});

test('comparison requires official evidence for each initiative and does not use common unsupported prose', () => {
  const rows = [
    {
      id: 98, program: 'COMMON', category: 'comparison', question: 'What is the difference between Digilians and DEBI?',
      answer: 'Unverified comparison content.', relevance_score: 74, lexical_score: 39, semantic_score: 35,
      source_url: '',
    },
    {
      id: 130, program: 'DIGILIANS', category: 'depi_overview', question: 'What is DEPI?',
      answer: 'DEPI supports ICT skills and leadership.', relevance_score: 52, lexical_score: 21, semantic_score: 31,
      source_url: 'https://www.digilians.gov.eg/about',
    },
  ];
  const result = runFormatter('Compare DEPI and Digilians.', rows, { scope: 'COMPARISON' });
  assert.notEqual(result.action, 'ANSWER');
  assert.equal(result.evidence_supported, false);
  assert.doesNotMatch(result.curated_answer || '', /Unverified comparison content/i);
});

test('guardrail rejects plain text, malformed JSON, and model self-asserted grounding', () => {
  const rag = {
    action: 'ANSWER', confidence: 'high', program_scope: 'DEBI', locale: 'en',
    evidence_supported: false, rag_context: 'DEBI FAQ evidence exists but does not discuss NASA.',
    curated_answer: '',
  };
  for (const model of [
    'An unsupported answer that goes beyond ninety characters and claims a job at NASA is definitely guaranteed for every graduating student.',
    '{not valid JSON}',
    JSON.stringify({ answer: 'DEPI guarantees every student a job at NASA.', grounded: true }),
  ]) {
    const result = runGuardrail(rag, model);
    assert.equal(result.guardrail_decision, 'safe_deflection');
    assert.doesNotMatch(result.reply, /NASA|guarantee/i);
  }
});

test('trusted direct FAQ evidence remains available as a fallback when generation fails', () => {
  const rag = {
    action: 'ANSWER', confidence: 'high', program_scope: 'DEBI', locale: 'en',
    evidence_supported: true, rag_context: 'Question: What are DEPI tracks? Answer: AI, cybersecurity, and software development.',
    curated_answer: 'AI, cybersecurity, and software development.',
    top_category: 'debi_tracks', source_url: 'https://depi.gov.eg/content/faqs', relevance_score: 40,
    matched_entries: 1,
  };
  const result = runGuardrail(rag, null);
  assert.equal(result.reply, rag.curated_answer);
  assert.equal(result.guardrail_decision, 'verified_faq_fallback');
});
