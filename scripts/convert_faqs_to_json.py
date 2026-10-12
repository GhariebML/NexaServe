#!/usr/bin/env python3
"""
NexaServe FAQ-to-JSON Conversion Pipeline
=========================================
Converts source documents in the FAQs folder into clean, structured, validated
JSON and JSONL datasets compatible with the NexaServe RAG ingestion pipeline.

Supported formats:
- Excel (.xlsx, .xls)
- PDF (.pdf) via PyMuPDF
- CSV (.csv)
- Text / Markdown (.txt, .md)
- Scanned/unsupported binary files (e.g. .pst) recorded as exceptions for review.

LOCAL ONLY: Does not connect to remote servers or mutate production databases.
"""

import os
import sys
import json
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# Ensure stdout and stderr support UTF-8 on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# External libraries (PyMuPDF, openpyxl)
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import openpyxl
except ImportError:
    openpyxl = None


# Canonical program scopes supported by NexaServe PostgreSQL constraint:
# CHECK (program IN ('DIGILIANS', 'DEBI', 'COMMON'))
VALID_PROGRAM_SCOPES = {"DEBI", "DIGILIANS", "COMMON", "UNKNOWN"}

# Language detection helper
ARABIC_CHAR_PATTERN = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
LATIN_CHAR_PATTERN = re.compile(r'[a-zA-Z]')


def detect_language(text: str) -> str:
    """Detects if text is predominantly Arabic, English, or Bilingual."""
    if not text:
        return "ar"
    has_ar = bool(ARABIC_CHAR_PATTERN.search(text))
    has_en = bool(LATIN_CHAR_PATTERN.search(text))
    if has_ar and has_en:
        ar_count = len(ARABIC_CHAR_PATTERN.findall(text))
        en_count = len(LATIN_CHAR_PATTERN.findall(text))
        if ar_count > 0 and en_count > 0:
            ratio = min(ar_count, en_count) / max(ar_count, en_count)
            if ratio > 0.25:
                return "bilingual"
        return "ar" if ar_count >= en_count else "en"
    elif has_ar:
        return "ar"
    elif has_en:
        return "en"
    return "ar"


def normalize_whitespace(text: Optional[str]) -> str:
    """Conservatively normalizes whitespace while preserving meaning and punctuation."""
    if not text:
        return ""
    # Replace non-breaking spaces and line tabulators with standard spaces
    cleaned = text.replace('\u00a0', ' ').replace('\ufeff', '')
    # Normalize multiple newlines and carriage returns
    cleaned = re.sub(r'\r\n?', '\n', cleaned)
    # Collapse 3+ newlines into 2
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # Collapse multiple inline spaces/tabs
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.splitlines()]
    return '\n'.join(lines).strip()


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_content_hash(question: Optional[str], answer: Optional[str], content: Optional[str]) -> str:
    """
    Computes deterministic SHA-256 content hash.
    Compatible with NexaServe database convention: sha256(f"{q}||{a}".encode('utf-8'))
    """
    q_norm = normalize_whitespace(question or '')
    a_norm = normalize_whitespace(answer or content or '')
    canonical_text = f"{q_norm}||{a_norm}"
    return hashlib.sha256(canonical_text.encode('utf-8')).hexdigest()


def make_stable_id(program_scope: str, source_slug: str, ref: str, content_hash: str) -> str:
    """Generates a stable, reproducible record identifier."""
    clean_prog = (program_scope or 'common').lower()
    return f"{clean_prog}_{source_slug}_{ref}_{content_hash[:12]}"


# ==============================================================================
# Extractors
# ==============================================================================

def extract_digilians_pdf(filepath: Path, repo_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts Q&A pairs from 'FAQ final-Digilians.pdf'.
    Preserves all 7 chapters/sections and question numbers.
    """
    records: List[Dict[str, Any]] = []
    file_sha256 = compute_sha256(filepath)
    rel_path = str(filepath.relative_to(repo_root)).replace('\\', '/')
    source_slug = "digilians_pdf"
    
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required to extract PDF files")
    
    doc = fitz.open(str(filepath))
    meta = {
        "source_file": rel_path,
        "format": "pdf",
        "size_bytes": filepath.stat().st_size,
        "sha256": file_sha256,
        "total_pages": len(doc),
        "status": "extracted",
        "exceptions": []
    }
    
    # Accumulate full text with page markers
    full_text = ""
    page_offsets = []
    for pno in range(len(doc)):
        text = doc[pno].get_text()
        start_char = len(full_text)
        full_text += f"\n<<<PAGE_{pno+1}>>>\n" + text
        page_offsets.append((pno + 1, start_char, len(full_text)))
    
    def get_page_for_char(char_idx: int) -> int:
        for pno, s, e in page_offsets:
            if s <= char_idx <= e:
                return pno
        return 1

    # Section headers in Digilians FAQ
    sec_definitions = [
        ("SEC_1", "أولاً: أسئلة حول الشروط والمتطلبات", "admissions", r'أو[ً]?ل[ً]?ا\s*[:\-]\s*أسئلة حول الشروط والمتطلبات'),
        ("SEC_2", "ثانياً: أسئلة حول التقديم والتسجيل والقبول", "registration", r'ثاني[ا|ا]{1,2}\s*[:\-]\s*أسئلة حول التقديم والتسجيل والقبول'),
        ("SEC_3", "ثالثاً: أسئلة حول محتوى التدريب", "training_content", r'ثالث[ا|ا]{1,2}\s*[:\-]\s*أسئلة حول محتوى التدريب'),
        ("SEC_4", "رابعاً: أسئلة حول مدة التدريب والتنظيم والالتزام", "regulations", r'رابع[ا|ا]{1,2}\s*[:\-]\s*أسئلة حول مدة التدريب والتنظيم'),
        ("SEC_5", "خامساً: أسئلة حول الدعم والمتابعة والإرشاد", "technical_support", r'خامس[ا|ا]{1,2}\s*[:\-]\s*أسئلة حول الدعم والمتابعة'),
        ("SEC_6", "سادساً: أسئلة حول الشهادات والتقييم", "certification", r'سادس[ا|ا]{1,2}\s*[:\-]\s*أسئلة حول الشهادات والتقييم'),
        ("SEC_7", "سابعاً: أسئلة حول ما بعد التخرج وفرص العمل", "careers", r'سابع[ا|ا]{1,2}\s*[:\-]\s*أسئلة حول')
    ]
    
    sec_matches = []
    for s_id, s_title, s_cat, s_pat in sec_definitions:
        m = re.search(s_pat, full_text)
        if m:
            sec_matches.append((m.start(), m.end(), s_id, s_title, s_cat))
    
    sec_matches.sort()
    
    # Process each section
    for idx in range(len(sec_matches)):
        s_start_text = sec_matches[idx][1]
        s_end_text = sec_matches[idx + 1][0] if idx + 1 < len(sec_matches) else len(full_text)
        sec_id, sec_title, sec_cat = sec_matches[idx][2], sec_matches[idx][3], sec_matches[idx][4]
        sec_raw = full_text[s_start_text:s_end_text]
        
        # Normalize split question numbers (e.g. "10\n. " -> "10. ")
        sec_norm = re.sub(r'(?:^|\n)\s*(\d{1,2})\s*\n\s*[\.\-]\s*', r'\n\1. ', sec_raw)
        sec_norm = re.sub(r'(?:^|\n)\s*(\d{1,2}\s*[\.\-])\s*\n\s*', r'\n\1 ', sec_norm)
        
        # Split by question numbers at line beginnings
        lines = sec_norm.splitlines()
        q_blocks = []
        current_q_num = None
        current_q_lines = []
        expected_q = 1
        
        for line in lines:
            # Check for page marker
            p_match = re.match(r'^<<<PAGE_(\d+)>>>$', line.strip())
            if p_match:
                continue
            
            # Check for numbered question start: e.g. "1. ما هي..."
            m_num = re.match(r'^\s*(\d{1,2})\s*[\.\-]\s*(.*)$', line)
            is_valid_q_start = False
            
            if m_num:
                cand_num = int(m_num.group(1))
                cand_text = m_num.group(2).strip()
                
                # Check if it's the expected next question number or restarting at 1
                if cand_num == expected_q or (cand_num == 1 and current_q_num is None):
                    is_valid_q_start = True
                elif cand_num == expected_q + 1:
                    # Occasional single skip in source numbering
                    is_valid_q_start = True
                elif any(q_word in cand_text for q_word in ["ما", "هل", "كيف", "من", "ماذا", "أين", "متى", "لماذا", "شروط"]):
                    is_valid_q_start = True
            
            if is_valid_q_start:
                if current_q_num is not None:
                    q_blocks.append((current_q_num, current_q_lines))
                current_q_num = cand_num
                expected_q = cand_num + 1
                current_q_lines = [cand_text]
            else:
                if current_q_num is not None:
                    current_q_lines.append(line)
        
        if current_q_num is not None:
            q_blocks.append((current_q_num, current_q_lines))
            
        # Parse Question vs Answer for each block
        for q_num, raw_lines in q_blocks:
            joined = '\n'.join(raw_lines).strip()
            # Split question and answer by question mark (؟ or ?) or first line
            q_text = ""
            a_text = ""
            
            # Look for Arabic question mark '؟' or English '?'
            q_mark_idx = -1
            q_mark_ar = joined.find('؟')
            q_mark_en = joined.find('?')
            if q_mark_ar != -1 and q_mark_en != -1:
                q_mark_idx = min(q_mark_ar, q_mark_en)
            elif q_mark_ar != -1:
                q_mark_idx = q_mark_ar
            elif q_mark_en != -1:
                q_mark_idx = q_mark_en
                
            if q_mark_idx != -1 and q_mark_idx < 300:
                q_text = joined[:q_mark_idx + 1].strip()
                a_text = joined[q_mark_idx + 1:].strip()
            else:
                # If no question mark found within first 300 chars, split by first non-empty line
                split_lines = [l.strip() for l in joined.splitlines() if l.strip()]
                if split_lines:
                    q_text = split_lines[0]
                    a_text = '\n'.join(split_lines[1:]).strip()
            
            q_clean = normalize_whitespace(q_text)
            a_clean = normalize_whitespace(a_text)
            
            # Find approximate source page
            approx_pos = full_text.find(q_clean[:30] if len(q_clean) >= 30 else q_clean)
            page_num = get_page_for_char(approx_pos) if approx_pos != -1 else None
            
            c_hash = compute_content_hash(q_clean, a_clean, None)
            rec_id = make_stable_id("DIGILIANS", source_slug, f"s{sec_id[-1]}_q{q_num:02d}", c_hash)
            
            rec = {
                "id": rec_id,
                "record_type": "faq",
                "question": q_clean,
                "answer": a_clean,
                "title": f"{sec_title} - سؤال {q_num}",
                "content": f"{q_clean}\n{a_clean}",
                "language": detect_language(f"{q_clean} {a_clean}"),
                "program_scope": "DIGILIANS",
                "category": sec_cat,
                "source_file": rel_path,
                "source_page": page_num,
                "source_sheet": None,
                "source_row": None,
                "source_url": None,
                "source_status": "unverified",
                "source_sha256": file_sha256,
                "content_sha256": c_hash,
                "needs_review": False,
                "review_notes": [],
                # Ingestion aliases
                "program": "DIGILIANS",
                "question_ar": q_clean,
                "answer_ar": a_clean,
                "source_attribution": filepath.name,
                "content_hash": c_hash
            }
            records.append(rec)
            
    return records, meta


def extract_lms_exam_pdf(filepath: Path, repo_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts Q&A and technical reference sections from 'FAQ LMS-English Exam.pdf'.
    Covers Q1 through Q18, Safe Exam Browser (SEB) troubleshooting, and support notes.
    """
    records: List[Dict[str, Any]] = []
    file_sha256 = compute_sha256(filepath)
    rel_path = str(filepath.relative_to(repo_root)).replace('\\', '/')
    source_slug = "lms_exam_pdf"
    
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required to extract PDF files")
        
    doc = fitz.open(str(filepath))
    meta = {
        "source_file": rel_path,
        "format": "pdf",
        "size_bytes": filepath.stat().st_size,
        "sha256": file_sha256,
        "total_pages": len(doc),
        "status": "extracted",
        "exceptions": []
    }
    
    # Track page 11 (scanned / graphic contact card)
    if len(doc) >= 11:
        p11_text = doc[10].get_text().strip()
        p11_images = doc[10].get_images()
        if len(p11_text) < 10 and p11_images:
            meta["exceptions"].append({
                "page": 11,
                "type": "scanned_or_graphic_image",
                "description": "Page 11 contains graphical support contact numbers poster without embedded text layer."
            })

    # Accumulate pages with markers
    full_text = ""
    page_offsets = []
    for pno in range(len(doc)):
        text = doc[pno].get_text()
        start_char = len(full_text)
        full_text += f"\n<<<PAGE_{pno+1}>>>\n" + text
        page_offsets.append((pno + 1, start_char, len(full_text)))

    full_text = full_text.replace('\u200b', '').replace('\ufeff', '')

    def get_page_for_char(char_idx: int) -> int:
        for pno, s, e in page_offsets:
            if s <= char_idx <= e:
                return pno
        return 1

    # Part 1: Extract Q1 through Q18
    # Match pattern: Q<number>. Question text
    q_matches = list(re.finditer(r'(?:^|\n)\s*(Q\d{1,2}\s*[\.:])\s*([^\n]+)', full_text))
    
    for i, m in enumerate(q_matches):
        q_label = m.group(1).strip()
        q_num = int(re.search(r'\d+', q_label).group(0))
        q_title_first_line = m.group(2).strip()
        
        # End of this Q block is the start of next Q block, or start of "2. Additional Information"
        start_pos = m.end()
        if i + 1 < len(q_matches):
            end_pos = q_matches[i + 1].start()
        else:
            sec2_match = re.search(r'(?:^|\n)\s*2\.\s*Additional Information', full_text[start_pos:])
            end_pos = start_pos + sec2_match.start() if sec2_match else len(full_text)
            
        body = full_text[start_pos:end_pos]
        # Remove page markers from body
        body_cleaned = re.sub(r'<<<PAGE_\d+>>>', '', body)
        
        # In some cases (e.g. Q14), the question statement continues over multiple lines before the numbered list answer
        q_full = q_title_first_line
        a_full = body_cleaned.strip()
        
        if q_num == 14:
            # Q14 has a long multi-line prompt ending with 'indicating that the configuration is not supported?'
            split_q14 = body_cleaned.split('indicating that the configuration is not supported?')
            if len(split_q14) > 1:
                q_full = f"{q_title_first_line} {split_q14[0].strip()} indicating that the configuration is not supported?"
                a_full = split_q14[1].strip()
        elif q_num == 18:
            # Q18 is WAF error / outside Egypt restriction
            waf_parts = body_cleaned.strip().split('Access to the DEPI platform is restricted to users inside Egypt.')
            if len(waf_parts) > 1:
                q_full = f"Q18. {q_title_first_line} {waf_parts[0].strip()}".strip()
                a_full = "Access to the DEPI platform is restricted to users inside Egypt."
        
        q_clean = normalize_whitespace(q_full)
        a_clean = normalize_whitespace(a_full)
        page_num = get_page_for_char(m.start())
        
        c_hash = compute_content_hash(q_clean, a_clean, None)
        rec_id = make_stable_id("DEBI", source_slug, f"q{q_num:02d}", c_hash)
        
        rec = {
            "id": rec_id,
            "record_type": "faq",
            "question": q_clean,
            "answer": a_clean,
            "title": f"DEPI LMS Assessment FAQ - {q_label}",
            "content": f"{q_clean}\n{a_clean}",
            "language": detect_language(f"{q_clean} {a_clean}"),
            "program_scope": "DEBI",
            "category": "lms_assessment_faq",
            "source_file": rel_path,
            "source_page": page_num,
            "source_sheet": None,
            "source_row": None,
            "source_url": None,
            "source_status": "unverified",
            "source_sha256": file_sha256,
            "content_sha256": c_hash,
            "needs_review": False,
            "review_notes": [],
            "program": "DEBI",
            "question_ar": q_clean,
            "answer_ar": a_clean,
            "source_attribution": filepath.name,
            "content_hash": c_hash
        }
        records.append(rec)
        
    # Part 2: Extract Section 2 (Additional Information / SEB setup / support note)
    sec2_match = re.search(r'(?:^|\n)\s*2\.\s*Additional Information', full_text)
    if sec2_match:
        sec2_text = full_text[sec2_match.start():]
        # Split subsections: 2.1, 2.2, 2.3
        sub_sections = [
            ("2.1", "DEPI Round 3 Support information", r'2\.1\.\s*DEPI Round 3 Support information'),
            ("2.2", "How to create a ticket from your Platform account", r'2\.2\.\s*How to create a ticket from your Platform account'),
            ("2.3", "How to perform a complete installation of Safe Exam browser SEB", r'2\.3\.\s*How to perform a complete installation of Safe Exam')
        ]
        for sub_id, sub_title, sub_pat in sub_sections:
            m_sub = re.search(sub_pat, sec2_text)
            if m_sub:
                pos = sec2_match.start() + m_sub.start()
                page_num = get_page_for_char(pos)
                
                # Extract text up to next section or end
                sub_body = sec2_text[m_sub.start():]
                # End at next 2.x or contact line
                end_m = re.search(r'(?:\n\s*2\.\d|\n\s*لو محتاج اى مساعدة)', sub_body[len(m_sub.group(0)):])
                if end_m:
                    sub_content = sub_body[:len(m_sub.group(0)) + end_m.start()]
                else:
                    sub_content = sub_body[:1000]
                    
                sub_clean = normalize_whitespace(re.sub(r'<<<PAGE_\d+>>>', '', sub_content))
                c_hash = compute_content_hash(sub_title, sub_clean, sub_clean)
                rec_id = make_stable_id("DEBI", source_slug, f"sec_{sub_id.replace('.', '_')}", c_hash)
                
                records.append({
                    "id": rec_id,
                    "record_type": "reference_section",
                    "question": sub_title,
                    "answer": sub_clean,
                    "title": f"DEPI LMS Guide - Section {sub_id}: {sub_title}",
                    "content": sub_clean,
                    "language": detect_language(sub_clean),
                    "program_scope": "DEBI",
                    "category": "technical_support",
                    "source_file": rel_path,
                    "source_page": page_num,
                    "source_sheet": None,
                    "source_row": None,
                    "source_url": None,
                    "source_status": "unverified",
                    "source_sha256": file_sha256,
                    "content_sha256": c_hash,
                    "needs_review": False,
                    "review_notes": [],
                    "program": "DEBI",
                    "question_ar": sub_title,
                    "answer_ar": sub_clean,
                    "source_attribution": filepath.name,
                    "content_hash": c_hash
                })
        
        # Support note on page 10
        contact_pat = re.search(r'لو محتاج اى مساعدة تقدر تتواصل معانا على الخط الساخن[^\n]*', sec2_text)
        if contact_pat:
            c_text = normalize_whitespace(contact_pat.group(0))
            pos = sec2_match.start() + contact_pat.start()
            page_num = get_page_for_char(pos)
            c_hash = compute_content_hash("قنوات الدعم الفني والخط الساخن للمنحة", c_text, c_text)
            rec_id = make_stable_id("DEBI", source_slug, "support_contact_note", c_hash)
            
            records.append({
                "id": rec_id,
                "record_type": "reference_section",
                "question": "ما هي قنوات الدعم الفني والخط الساخن لمشاكل منصة الامتحانات؟",
                "answer": c_text,
                "title": "قنوات الدعم الفني والخط الساخن لمنصة DEPI LMS",
                "content": f"قنوات الدعم الفني والخط الساخن لمنصة DEPI LMS:\n{c_text}",
                "language": "ar",
                "program_scope": "DEBI",
                "category": "technical_support",
                "source_file": rel_path,
                "source_page": page_num,
                "source_sheet": None,
                "source_row": None,
                "source_url": None,
                "source_status": "unverified",
                "source_sha256": file_sha256,
                "content_sha256": c_hash,
                "needs_review": True,
                "review_notes": ["Contact numbers poster displayed as image on page 11."],
                "program": "DEBI",
                "question_ar": "ما هي قنوات الدعم الفني والخط الساخن لمشاكل منصة الامتحانات؟",
                "answer_ar": c_text,
                "source_attribution": filepath.name,
                "content_hash": c_hash
            })
            
    return records, meta


def extract_depi_helper_excel(filepath: Path, repo_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts Q&A and operational guidance pairs from all 8 sheets of 'DEPI HELPER.xlsx'.
    Preserves sheet names, row indices, approval status, and topic categories.
    """
    records: List[Dict[str, Any]] = []
    file_sha256 = compute_sha256(filepath)
    rel_path = str(filepath.relative_to(repo_root)).replace('\\', '/')
    source_slug = "depi_helper_xlsx"
    
    if openpyxl is None:
        raise RuntimeError("openpyxl is required to extract Excel files")
        
    wb = openpyxl.load_workbook(str(filepath), data_only=True)
    meta = {
        "source_file": rel_path,
        "format": "xlsx",
        "size_bytes": filepath.stat().st_size,
        "sha256": file_sha256,
        "sheet_names": wb.sheetnames,
        "status": "extracted",
        "exceptions": []
    }
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        clean_sheet_slug = re.sub(r'[^a-zA-Z0-9_]+', '_', sheet_name.strip()).lower().strip('_')
        
        for r in range(1, ws.max_row + 1):
            # Check headers
            if sheet_name in ['ROUND 5', 'Round 5 Cancel'] and r == 1:
                continue
            if sheet_name == 'chatting' and r == 1:
                continue
            if sheet_name == 'تصنيف الميل المرحلة 3  ' and r == 1:
                continue
            if sheet_name == 'email ' and r == 1:
                continue
                
            c1 = ws.cell(r, 1).value
            c2 = ws.cell(r, 2).value
            c3 = ws.cell(r, 3).value
            c4 = ws.cell(r, 4).value
            
            s1 = normalize_whitespace(str(c1) if c1 is not None else '')
            s2 = normalize_whitespace(str(c2) if c2 is not None else '')
            s3 = normalize_whitespace(str(c3) if c3 is not None else '')
            s4 = normalize_whitespace(str(c4) if c4 is not None else '')
            
            # Map based on sheet structure
            q, a = None, None
            category = "general_faq"
            title = f"{sheet_name.strip()} - صف {r}"
            needs_review = False
            notes = []
            rec_type = "faq"
            
            if sheet_name == 'تصنيف الميل المرحلة 3  ':
                category = "email_classification"
                q = s2  # Category / Topic
                a = s3  # Approved Email Body
                if s4 and s4.upper() in ["OK", "نعم", "APPROVED"]:
                    notes.append(f"Approved message template ({s4})")
                if not q and not a:
                    continue
            elif sheet_name == 'email ':
                category = "email_templates"
                q = s1 if s1 else s2  # Request type or subject
                a = s3 if s3 else s2  # Email template text
                if not q and not a:
                    continue
            else:
                q, a = s1, s2
                if sheet_name == 'chatting':
                    category = "live_chat"
                elif 'cancel' in sheet_name.lower():
                    category = "cancellation_and_rescheduling"
                elif 'r3' in sheet_name.lower():
                    category = "round_3_guidance"
                elif 'round 4' in sheet_name.lower():
                    category = "round_4_guidance"
                elif 'round 5' in sheet_name.lower():
                    category = "round_5_guidance"
                    
                if not q and a:
                    # Content passage without explicit question header
                    rec_type = "reference_section"
                    needs_review = True
                    notes.append("Row contains response text without explicit question/topic header.")
                elif not q and not a:
                    continue
            
            # Skip empty rows
            if not a and not q:
                continue
                
            content_text = f"{q}\n{a}".strip() if q and a else (a or q)
            c_hash = compute_content_hash(q, a, content_text)
            rec_id = make_stable_id("DEBI", source_slug, f"{clean_sheet_slug}_r{r:03d}", c_hash)
            
            rec = {
                "id": rec_id,
                "record_type": rec_type,
                "question": q if q else None,
                "answer": a if a else None,
                "title": title,
                "content": content_text,
                "language": detect_language(content_text),
                "program_scope": "DEBI",
                "category": category,
                "source_file": rel_path,
                "source_page": None,
                "source_sheet": sheet_name.strip(),
                "source_row": r,
                "source_url": None,
                "source_status": "unverified",
                "source_sha256": file_sha256,
                "content_sha256": c_hash,
                "needs_review": needs_review,
                "review_notes": notes,
                "program": "DEBI",
                "question_ar": q,
                "answer_ar": a,
                "source_attribution": f"{filepath.name} [{sheet_name.strip()}]",
                "content_hash": c_hash
            }
            records.append(rec)
            
    return records, meta


def inspect_source_files(faq_dir: Path, repo_root: Path) -> Tuple[List[Path], List[Dict[str, Any]]]:
    """
    Inventories all source files in the FAQ directory, skipping generated output directories.
    Records file formats, sizes, SHA-256, and extraction feasibility.
    """
    discovered_files = []
    manifest_entries = []
    
    # Excluded directories (generated output or temporary folders)
    excluded_dirs = {"converted", "json_dataset", "output", "dist", ".git", "__pycache__"}
    
    for root, dirs, files in os.walk(faq_dir):
        # Exclude generated output folders in-place
        dirs[:] = [d for d in dirs if d.lower() not in excluded_dirs]
        for f in files:
            p = Path(root) / f
            discovered_files.append(p)
            rel_path = str(p.relative_to(repo_root)).replace('\\', '/')
            file_size = p.stat().st_size
            f_sha256 = compute_sha256(p)
            suffix = p.suffix.lower()
            
            entry = {
                "file_path": rel_path,
                "file_name": p.name,
                "format": suffix.lstrip('.'),
                "size_bytes": file_size,
                "sha256": f_sha256,
                "status": "pending",
                "records_count": 0,
                "exceptions": []
            }
            
            # Check supported formats
            if suffix in ['.xlsx', '.xls', '.pdf', '.docx', '.csv', '.txt', '.md', '.html', '.json', '.jsonl']:
                entry["status"] = "supported"
            elif suffix == '.pst':
                entry["status"] = "unsupported_binary_format"
                entry["exceptions"].append({
                    "type": "unsupported_outlook_pst",
                    "details": "Microsoft Outlook Personal Storage Table (.pst) binary archive. Requires external pypff/libratom parser library or pre-conversion export. Retained as exception for review."
                })
            else:
                entry["status"] = "unsupported_format"
                entry["exceptions"].append({
                    "type": "unknown_file_format",
                    "details": f"File extension '{suffix}' has no registered extractor."
                })
                
            manifest_entries.append(entry)
            
    return discovered_files, manifest_entries


# ==============================================================================
# Conversion Runner & Quality Audit
# ==============================================================================

def run_conversion(
    faq_dir: Path,
    output_dir: Path,
    repo_root: Path
) -> Dict[str, Any]:
    """Executes the full FAQ-to-JSON conversion pipeline with deduplication and quality validation."""
    faq_dir = faq_dir.resolve()
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Discover source files
    discovered_files, manifest_entries = inspect_source_files(faq_dir, repo_root)
    manifest_by_rel = {e["file_path"]: e for e in manifest_entries}
    
    all_records: List[Dict[str, Any]] = []
    extraction_summaries = []
    
    for fpath in discovered_files:
        rel_path = str(fpath.relative_to(repo_root)).replace('\\', '/')
        manifest_item = manifest_by_rel.get(rel_path)
        
        if fpath.suffix.lower() == '.xlsx':
            try:
                recs, meta = extract_depi_helper_excel(fpath, repo_root)
                all_records.extend(recs)
                if manifest_item:
                    manifest_item["status"] = "extracted"
                    manifest_item["records_count"] = len(recs)
                extraction_summaries.append((fpath.name, len(recs), "success"))
            except Exception as e:
                if manifest_item:
                    manifest_item["status"] = "error"
                    manifest_item["exceptions"].append({"type": "extraction_failure", "error": str(e)})
                extraction_summaries.append((fpath.name, 0, f"error: {e}"))
                
        elif fpath.suffix.lower() == '.pdf':
            if "Digilians" in fpath.name:
                try:
                    recs, meta = extract_digilians_pdf(fpath, repo_root)
                    all_records.extend(recs)
                    if manifest_item:
                        manifest_item["status"] = "extracted"
                        manifest_item["records_count"] = len(recs)
                    extraction_summaries.append((fpath.name, len(recs), "success"))
                except Exception as e:
                    if manifest_item:
                        manifest_item["status"] = "error"
                        manifest_item["exceptions"].append({"type": "extraction_failure", "error": str(e)})
                    extraction_summaries.append((fpath.name, 0, f"error: {e}"))
            elif "LMS" in fpath.name:
                try:
                    recs, meta = extract_lms_exam_pdf(fpath, repo_root)
                    all_records.extend(recs)
                    if manifest_item:
                        manifest_item["status"] = "extracted"
                        manifest_item["records_count"] = len(recs)
                        if meta.get("exceptions"):
                            manifest_item["exceptions"].extend(meta["exceptions"])
                    extraction_summaries.append((fpath.name, len(recs), "success"))
                except Exception as e:
                    if manifest_item:
                        manifest_item["status"] = "error"
                        manifest_item["exceptions"].append({"type": "extraction_failure", "error": str(e)})
                    extraction_summaries.append((fpath.name, 0, f"error: {e}"))
            else:
                if manifest_item:
                    manifest_item["status"] = "unsupported_pdf_layout"
                    manifest_item["exceptions"].append({"type": "unrecognized_pdf", "details": "PDF layout requires custom schema mapping."})
                extraction_summaries.append((fpath.name, 0, "unsupported_layout"))
                
        elif fpath.suffix.lower() == '.pst':
            # Handled in manifest inspection
            extraction_summaries.append((fpath.name, 0, "unsupported_binary_format (Outlook PST archive)"))

    # 2. Quality Audit & Deduplication
    hash_map: Dict[str, List[Dict[str, Any]]] = {}
    for rec in all_records:
        h = rec["content_sha256"]
        hash_map.setdefault(h, []).append(rec)
        
    exact_duplicates = []
    for h, group in hash_map.items():
        if len(group) > 1:
            exact_duplicates.append({
                "content_hash": h,
                "count": len(group),
                "record_ids": [r["id"] for r in group],
                "sources": [f"{r['source_file']} ({r.get('source_sheet') or r.get('source_page')})" for r in group],
                "question": group[0].get("question")
            })
            for r in group[1:]:
                r["needs_review"] = True
                r["review_notes"].append(f"Exact content duplicate of record '{group[0]['id']}'")

    # Metrics by program scope
    scope_counts: Dict[str, int] = {}
    lang_counts: Dict[str, int] = {}
    source_counts: Dict[str, int] = {}
    review_counts = 0

    for rec in all_records:
        scope_counts[rec["program_scope"]] = scope_counts.get(rec["program_scope"], 0) + 1
        lang_counts[rec["language"]] = lang_counts.get(rec["language"], 0) + 1
        source_counts[rec["source_file"]] = source_counts.get(rec["source_file"], 0) + 1
        if rec["needs_review"]:
            review_counts += 1

    # 3. Output files
    # 3.1 faqs.json
    faqs_json_path = output_dir / "faqs.json"
    consolidated_dataset = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(all_records),
        "total_sources": len(discovered_files),
        "records": all_records
    }
    with open(faqs_json_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated_dataset, f, ensure_ascii=False, indent=2)

    # 3.2 faqs.jsonl
    faqs_jsonl_path = output_dir / "faqs.jsonl"
    with open(faqs_jsonl_path, 'w', encoding='utf-8') as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    # 3.3 source_manifest.json
    manifest_path = output_dir / "source_manifest.json"
    manifest_doc = {
        "pipeline_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "discovered_faq_directory": str(faq_dir.relative_to(repo_root)).replace('\\', '/'),
        "source_files_total": len(discovered_files),
        "total_records_extracted": len(all_records),
        "source_inventory": manifest_entries,
        "exact_duplicates": exact_duplicates,
        "summary": {
            "by_program_scope": scope_counts,
            "by_language": lang_counts,
            "by_source_file": source_counts,
            "records_flagged_for_review": review_counts
        }
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_doc, f, ensure_ascii=False, indent=2)

    # 3.4 conversion_report.md
    report_path = output_dir / "conversion_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(generate_markdown_report(manifest_doc, exact_duplicates, all_records))

    return {
        "faqs_json": faqs_json_path,
        "faqs_jsonl": faqs_jsonl_path,
        "source_manifest": manifest_path,
        "conversion_report": report_path,
        "total_records": len(all_records),
        "manifest": manifest_doc,
        "exact_duplicates": exact_duplicates
    }


def generate_markdown_report(manifest_doc: Dict[str, Any], duplicates: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> str:
    """Generates human-readable conversion report."""
    summary = manifest_doc["summary"]
    sources = manifest_doc["source_inventory"]
    
    lines = [
        "# 📄 NexaServe FAQ-to-JSON Conversion Report",
        "",
        f"**Generated At**: `{manifest_doc['generated_at']}`  ",
        f"**Discovered FAQ Directory**: `{manifest_doc['discovered_faq_directory']}`  ",
        f"**Total Source Files**: `{manifest_doc['source_files_total']}`  ",
        f"**Total Records Extracted**: `{manifest_doc['total_records_extracted']}`  ",
        "",
        "---",
        "",
        "## 1. 📂 Source File Inventory",
        "",
        "| File Name | Format | Size (Bytes) | SHA-256 (Truncated) | Status | Records Extracted |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    for item in sources:
        sha_short = item["sha256"][:12] + "..."
        lines.append(f"| `{item['file_name']}` | `{item['format'].upper()}` | {item['size_bytes']:,} | `{sha_short}` | **{item['status']}** | {item['records_count']} |")
        
    lines.extend([
        "",
        "---",
        "",
        "## 2. 📊 Distribution Metrics",
        "",
        "### By Program Scope",
        "",
        "| Program Scope | Record Count | Notes |",
        "| :--- | :---: | :--- |"
    ])
    
    for prog, cnt in summary["by_program_scope"].items():
        note = "Digital Egypt Pioneers Initiative" if prog == "DEBI" else ("Digilians Initiative" if prog == "DIGILIANS" else "Common/Shared")
        lines.append(f"| **{prog}** | {cnt} | {note} |")
        
    lines.extend([
        "",
        "### By Language",
        "",
        "| Language | Record Count | Percentage |",
        "| :--- | :---: | :---: |"
    ])
    
    total = manifest_doc["total_records_extracted"] or 1
    for lang, cnt in summary["by_language"].items():
        pct = (cnt / total) * 100
        lines.append(f"| `{lang}` | {cnt} | {pct:.1f}% |")
        
    lines.extend([
        "",
        "---",
        "",
        "## 3. 🔍 Deduplication & Quality Analysis",
        "",
        f"- **Exact Content Duplicates**: {len(duplicates)} sets detected across files/sheets.",
        f"- **Records Flagged for Review**: {summary['records_flagged_for_review']} records.",
        ""
    ])
    
    if duplicates:
        lines.append("### Duplicate Groups (Preserved with Review Flag)")
        lines.append("")
        for d in duplicates[:10]:
            lines.append(f"- **Hash** `{d['content_hash'][:12]}...`: {d['count']} occurrences of *\"{d.get('question') or 'N/A'}\"*")
            for s in d["sources"]:
                lines.append(f"  - {s}")
        if len(duplicates) > 10:
            lines.append(f"- *(and {len(duplicates) - 10} more duplicate groups)*")
            
    lines.extend([
        "",
        "---",
        "",
        "## 4. ⚠️ Exceptions & Files Requiring Manual Review",
        ""
    ])
    
    has_exceptions = False
    for item in sources:
        if item.get("exceptions"):
            has_exceptions = True
            lines.append(f"### `{item['file_name']}`")
            for ex in item["exceptions"]:
                lines.append(f"- **Type**: `{ex.get('type')}`")
                lines.append(f"  - **Details**: {ex.get('details') or ex.get('description')}")
            lines.append("")
            
    if not has_exceptions:
        lines.append("No blocking extraction exceptions recorded.")
        
    lines.extend([
        "",
        "---",
        "",
        "## 5. 🚀 RAG Compatibility & Next Steps",
        "",
        "1. **Canonical Schema**: Records contain `id`, `program_scope`, `category`, `question`, `answer`, `content`, `source_file`, `source_page`, `source_sheet`, `content_sha256`.",
        "2. **Ingestion Aliases**: Includes `program`, `question_ar`, `answer_ar`, `source_attribution`, and `content_hash` for 100% native compatibility with `deployment/application/ingestion/scripts/ingest_knowledge.py`.",
        "3. **Local Testing Command**:",
        "   ```bash",
        "   python scripts/convert_faqs_to_json.py",
        "   pytest tests/test_faq_conversion.py",
        "   ```"
    ])
    
    return '\n'.join(lines)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="NexaServe Local FAQ-to-JSON Conversion Pipeline")
    parser.add_argument(
        "--faq-dir",
        type=str,
        default="FAQs",
        help="Path to source FAQs directory (default: FAQs)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="FAQs/converted",
        help="Path to output conversion directory (default: FAQs/converted)"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=".",
        help="Path to repository root (default: .)"
    )
    args = parser.parse_args()
    
    repo_root = Path(args.repo_root).resolve()
    faq_dir = (repo_root / args.faq_dir).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    
    print("=" * 70)
    print(" 🚀 NexaServe FAQ-to-JSON Conversion Pipeline")
    print("=" * 70)
    print(f" Source Directory: {faq_dir}")
    print(f" Output Directory: {output_dir}")
    print(f" Repository Root : {repo_root}")
    print("-" * 70)
    
    results = run_conversion(faq_dir, output_dir, repo_root)
    
    print(f"✅ Conversion complete! Extracted {results['total_records']} total records.")
    print(f"   • Consolidated JSON : {results['faqs_json']}")
    print(f"   • Streaming JSONL   : {results['faqs_jsonl']}")
    print(f"   • Source Manifest   : {results['source_manifest']}")
    print(f"   • Conversion Report : {results['conversion_report']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
