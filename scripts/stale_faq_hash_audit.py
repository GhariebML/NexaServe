"""Evidence helpers for the non-approving FAQ source-hash audit."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

try:
    from .reconcile_content_approval_decisions import normalize_faq_whitespace
except ImportError:
    from reconcile_content_approval_decisions import normalize_faq_whitespace


def canonical_faq_basis(question: Any, answer: Any, content: Any = None,
                        *, fallback_to_content: bool = False,
                        unicode_form: str | None = None) -> str:
    """Return the exact Q||A text basis, with source-specific fallback explicit.

    The legacy converter uses ``answer or content`` for DEPI HELPER Excel
    records, but other FAQ extractors hash the persisted answer field as-is.
    NFC is optional for diagnostics only and is not silently applied to legacy
    content hashes.
    """
    q = normalize_faq_whitespace(question)
    a = normalize_faq_whitespace(answer if answer else content if fallback_to_content else answer)
    if unicode_form:
        q = unicodedata.normalize(unicode_form, q)
        a = unicodedata.normalize(unicode_form, a)
    return f"{q}||{a}"


def canonical_faq_hash(question: Any, answer: Any, content: Any = None,
                       *, fallback_to_content: bool = False,
                       unicode_form: str | None = None) -> str:
    basis = canonical_faq_basis(question, answer, content,
                                fallback_to_content=fallback_to_content,
                                unicode_form=unicode_form)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def canonical_json_hash(value: Any) -> str:
    """Stable metadata fingerprint independent of object key order/spacing."""
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def approval_hash_is_stale(content_hash_at_decision: str, current_content_hash: str | None) -> bool:
    return current_content_hash is None or content_hash_at_decision != current_content_hash
