import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { extractN8nReply } from '../infra/whatsapp/n8n-response.js';

const workflow = JSON.parse(fs.readFileSync(new URL('../infra/n8n/workflows/04B_knowledge_base_faq.json', import.meta.url), 'utf8'));
const programDetector = workflow.nodes.find((node) => node.name === 'Program Detector & Query Normalizer').parameters.jsCode;

function runProgramDetector(customerMessage) {
  const execute = new Function('$input', programDetector);
  return execute({ first: () => ({ json: { customer_message: customerMessage, locale: 'ar' } }) })[0].json;
}

test('accepts a customer reply from a successful response envelope', () => {
  assert.equal(extractN8nReply(200, { status: 'completed', response: 'إجابة موثقة' }), 'إجابة موثقة');
  assert.equal(extractN8nReply(200, { final_reply: 'Reply' }), 'Reply');
  assert.equal(extractN8nReply(200, { reply: 'Reply' }), 'Reply');
});

test('does not turn n8n error messages into customer replies', () => {
  assert.equal(extractN8nReply(500, { message: 'Error in workflow' }), null);
  assert.equal(extractN8nReply(200, { message: 'Error in workflow' }), null);
  assert.equal(extractN8nReply(200, { status: 'error', response: 'Error in workflow' }), null);
  assert.equal(extractN8nReply(200, { status: 'failed', reply: 'Error in workflow' }), null);
});

test('rejects malformed and empty envelopes', () => {
  assert.equal(extractN8nReply(200, null), null);
  assert.equal(extractN8nReply(200, []), null);
  assert.equal(extractN8nReply(204, { response: '  ' }), null);
});

test('runs the RAG program detector for DEPI and Digilians queries', () => {
  const depi = runProgramDetector('ما هي المنح المتاحة في DEPI؟');
  assert.equal(depi.program_scope, 'DEBI');
  assert.equal(depi.topic_category, 'debi_benefits');

  const digilians = runProgramDetector('ما هي شروط الالتحاق بمبادرة الرواد الرقميون؟');
  assert.equal(digilians.program_scope, 'DIGILIANS');
  assert.equal(digilians.topic_category, 'depi_conditions');
});
