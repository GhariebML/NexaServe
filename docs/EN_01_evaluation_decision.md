# EN_01 Evaluation Decision & Root Cause Analysis

## Executive Summary
During the frozen golden test evaluation (frozen dataset v1: 36 cases), test case `EN_01` was the sole failure (35/36 passed, 97.2%). 

- **Test ID**: `EN_01`
- **Query**: `"What is the Digital Egypt Pioneers Initiative?"`
- **Target Program**: `DEPI` (stored as `DEBI` in the official database)
- **Expected Behavior**: `answer` (answerable: true)
- **Required Keywords**: `["Digital", "Egypt"]`
- **Forbidden Terms**: `["[DEBI]", "[DIGILIANS]", "سؤال:", "إجابة:"]`

## 1. Original Expectation vs Observed Behavior

### Frozen Expectation (Source of Truth)
The test case asserts that a citizen asking in English about the "Digital Egypt Pioneers Initiative" should receive an informative answer describing the initiative, containing the words "Digital" and "Egypt", and must not contain raw prompt leakage, internal brackets, or raw database artifacts.

### Pre-Fix Observed Behavior
- **Response**: `"Welcome to the DEPI Customer Service platform. How may we assist you today?"`
- **Status**: `FAIL` (Missing required terms: "Digital", "Egypt")
- **Latency**: 25,510 ms
- **Classified Intent**: `general_support` (fallback greeting)

## 2. Root Cause Investigation

The investigation verified that **the system response was genuinely incorrect**, not the test expectation:

1. **Missing Intent Keywords in Pre-Classifier**:
   In `infra/n8n/workflows/03_ai_intent_engine.json`, the node `Build Prompt Payload` defines a deterministic keyword pre-classifier `faqKeywords`. While Arabic stems like `رواد` and abbreviations like `debi` were present, English initiative terms `initiative`, `initiatives`, `pioneers`, and `depi` were absent.
2. **LLM Fallback & Latency**:
   Because `faqKeywords` did not match, the query fell through to Ollama LLM intent classification (`qwen2.5:3b`), taking ~25 seconds under heavy load and either misclassifying or timing out into the default fallback `general_support`.
3. **General Support Greeting**:
   In `01_gateway_dispatcher.json`, queries classified as `general_support` bypass the RAG pipeline entirely and receive a static greeting template, failing to provide the substantive overview requested by the user.
4. **Knowledge Base Alignment**:
   In `04B_knowledge_base_faq.json`, the entity resolver already properly resolves `'digital egypt pioneers initiative'` to `DEBI`. In the database, KB entry ID 90 (`"What is the Digital Egypt Builders Initiative (DEBI)?"`) contains full verified MCIT scholarship information with lexical score 58 and high confidence.

## 3. Engineering Fix Applied

The frozen test suite was **NOT modified**. The system was repaired to address the genuine routing bug:

1. **Intent Pre-Classifier Updated**:
   In `03_ai_intent_engine.json` (`Build Prompt Payload`):
   Added `'initiative'`, `'initiatives'`, `'pioneers'`, `'pioneer'`, `'depi'`, `'builders'`, `'builder'` to `faqKeywords`.
2. **Heuristic Fail-Safe Synchronized**:
   In `03_ai_intent_engine.json` (`Parse & Validate AI Schema`):
   Added the same initiative identifiers to `isFaq`.
3. **Workflow Deployed**:
   Exported and re-imported into `cs-n8n` under project `xkUEnhvpIvkLo6BO`, published `CSWF000000000003`, and restarted n8n container.

## 4. Post-Fix Verification

Direct test of query `"What is the Digital Egypt Pioneers Initiative?"` against live endpoint `http://localhost:5678/webhook/customer-service`:

- **HTTP Status**: `200 OK`
- **Classified Intent**: `faq_query` (Confidence: 0.90)
- **Response**:
  > "The Digital Egypt Builders Initiative (DEBI) is a fully-funded scholarship launched by Egypt's Ministry of Communications and Information Technology (MCIT). It grants top Egyptian engineering and computer science graduates a professional Master's degree from prestigious international universities, combined with industry training from leading tech companies and leadership development."
- **Contains 'Digital'**: `PASS`
- **Contains 'Egypt'**: `PASS`
- **Forbidden tokens check**: `PASS` (0 forbidden tokens found)
- **Latency**: 3,192 ms (improved from 25,510 ms)

## 5. Engineering Conclusion

- **Defect Classification**: Genuine system defect in intent pre-classification keyword table.
- **Evaluation Validity**: The frozen test expectation was completely appropriate, fair, and semantically sound.
- **Resolution**: System corrected at the root cause. The golden dataset remains 100% frozen and immutable.
