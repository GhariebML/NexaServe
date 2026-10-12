import hashlib
import json
import unittest

from scripts.reconcile_content_approval_decisions import compute_current_content_hash
from scripts.build_source_provenance_review import content_hash as provenance_content_hash
from scripts.convert_faqs_to_json import compute_content_hash
from scripts.stale_faq_hash_audit import (
    approval_hash_is_stale,
    canonical_faq_hash,
    canonical_json_hash,
)


class StaleFaqHashAuditTests(unittest.TestCase):
    def test_unchanged_helper_content_matches_source_specific_fallback(self):
        record = {"question": "  توجيه داخلي  ", "answer": "", "content": "توجيه داخلي"}
        original = hashlib.sha256("توجيه داخلي||توجيه داخلي".encode("utf-8")).hexdigest()
        reconciler_hash = compute_current_content_hash("FAQs/converted/faqs.json", record, "FAQs/DEPI HELPER.xlsx")
        manifest_hash = provenance_content_hash(record["question"], record["answer"], record["content"], True)
        self.assertEqual(reconciler_hash, original)
        self.assertEqual(manifest_hash, original)

    def test_material_question_or_answer_change_changes_hash(self):
        original = compute_current_content_hash(
            "FAQs/converted/faqs.json",
            {"question": "Question", "answer": "Original answer", "content": "Original answer"},
            "FAQs/FAQ LMS-English Exam.pdf",
        )
        changed = compute_current_content_hash(
            "FAQs/converted/faqs.json",
            {"question": "Question", "answer": "Changed answer", "content": "Changed answer"},
            "FAQs/FAQ LMS-English Exam.pdf",
        )
        self.assertNotEqual(original, changed)

    def test_pdf_converter_hash_label_differs_from_persisted_question(self):
        answer = "synthetic extracted answer"
        legacy_hash = compute_content_hash("Synthetic topic label", answer, answer)
        persisted_hash = compute_current_content_hash(
            "FAQs/converted/faqs.json",
            {"question": "Synthetic generated question?", "answer": answer, "content": answer},
            "FAQs/FAQ LMS-English Exam.pdf",
        )
        self.assertNotEqual(legacy_hash, persisted_hash)

    def test_arabic_unicode_nfc_is_explicit_and_reproducible(self):
        composed = "آ"
        decomposed = "\u0627\u0653"
        self.assertNotEqual(
            canonical_faq_hash(composed, "إجابة"),
            canonical_faq_hash(decomposed, "إجابة"),
        )
        self.assertEqual(
            canonical_faq_hash(composed, "إجابة", unicode_form="NFC"),
            canonical_faq_hash(decomposed, "إجابة", unicode_form="NFC"),
        )

    def test_json_serialization_key_order_and_whitespace_do_not_change_fingerprint(self):
        compact = json.loads('{"source":"عربي","row":10}')
        spaced_reordered = json.loads(' { "row" : 10, "source" : "عربي" } ')
        self.assertEqual(
            canonical_json_hash(compact),
            canonical_json_hash(spaced_reordered),
        )

    def test_stale_approval_detection_blocks_changed_or_missing_hash(self):
        approved_hash = "a" * 64
        self.assertFalse(approval_hash_is_stale(approved_hash, approved_hash))
        self.assertTrue(approval_hash_is_stale(approved_hash, "b" * 64))
        self.assertTrue(approval_hash_is_stale(approved_hash, None))

        from scripts.validate_content_approval_ledger import evaluate_entries
        entry = {
            "source_dataset": "synthetic.json",
            "source_record_id": "synthetic-1",
            "content_hash_at_decision": approved_hash,
            "decision": "APPROVED_INTERNAL_DEPI_GUIDANCE",
            "evidence_reference": "OWNER_APPROVAL:SYNTHETIC",
            "reviewer_role": "Authorized DEPI Content Owner",
        }
        stale, invalid = evaluate_entries([entry], {("synthetic.json", "synthetic-1"): "b" * 64})
        self.assertEqual(len(stale), 1)
        self.assertEqual(invalid, [])


if __name__ == "__main__":
    unittest.main()
