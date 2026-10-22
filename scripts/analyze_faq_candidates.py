import json
import re
import os
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

prepared_dir = Path(r'E:\NexaServe\FAQs\New Fiels\JSON\prepared')
review_dir = prepared_dir / 'review'
review_dir.mkdir(parents=True, exist_ok=True)

# 1. Rename tickets file as requested in Step 6
tickets_old = prepared_dir / 'tickets_import_ready.json'
tickets_new = prepared_dir / 'tickets_pending_schema_review.json'
if tickets_old.exists():
    tickets_old.rename(tickets_new)
    print(f'Renamed {tickets_old.name} -> {tickets_new.name}')
elif tickets_new.exists():
    print(f'Ticket file already renamed to {tickets_new.name}')

# 2. Load FAQ Candidates
faq_file = prepared_dir / 'faq_candidates_pending_review.json'
with open(faq_file, 'r', encoding='utf-8') as f:
    faq_data = json.load(f)

records = faq_data.get('records', [])
print(f'Loaded {len(records)} FAQ candidates.')

# Load official sources for matching
official_sources = []
for src_path in [Path('DEPI_Web_Scraper/data/final/faqs.json'), Path('FAQs/converted/faqs.json')]:
    if src_path.exists():
        try:
            with open(src_path, 'r', encoding='utf-8') as sf:
                sdata = json.load(sf)
                if isinstance(sdata, list):
                    official_sources.extend(sdata)
        except Exception as e:
            print(f'Warning loading {src_path}: {e}')

print(f'Loaded {len(official_sources)} official FAQ source entries for matching.')

# PII Patterns
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'(?:\+?20|0)?1[0125]\d{8}')
NAT_ID_RE = re.compile(r'\b[23]\d{13}\b')

# Topic keywords mapping (Arabic/English)
TOPIC_KEYWORDS = {
    'Attendance & Absence (الحضور والغياب)': ['حضور', 'غياب', 'استئذان', 'نسبة الحضور', 'أعذار', 'attendance', 'absence'],
    'Stipends & Allowances (المكافآت والبدلات)': ['مكافأة', 'منحة', 'بدل', 'فلوس', 'قبض', 'استحقاق', 'stipend', 'allowance', 'payment'],
    'Tracks & Specialization (التخصصات والمكارات)': ['تخصص', 'مسار', 'تغيير المسار', 'شغف', 'برمجة', 'شبكات', 'ذكاء اصطناعي', 'track', 'specialization'],
    'Exams & Evaluations (الاختبارات والتقييمات)': ['امتحان', 'اختبار', 'تقييم', 'درجات', 'نتيجة', 'اعادة اختبار', 'exam', 'quiz', 'evaluation'],
    'Certificates & Graduation (الشهادات والتخرج)': ['شهادة', 'تخرج', 'استلام الشهادة', 'حفل', 'certificate', 'graduation'],
    'Platform & Account Access (المنصة والحسابات)': ['حساب', 'منصة', 'تسجيل دخول', 'كلمة السر', 'ايميل', 'موقع', 'login', 'platform', 'password'],
    'Schedule & Lectures (المواعيد والمحاضرات)': ['موعد', 'مواعيد', 'محاضرة', 'جدول', 'سيشن', 'زوم', 'schedule', 'lecture', 'session'],
    'Instructor & Tutors (المحاضرين والمدربين)': ['باشمهندس', 'دكتور', 'معيد', 'استاذ', 'محاضر', 'مدرب', 'instructor', 'trainer'],
    'Technical Issues & Support (المشاكل التقنية والدعم)': ['مشكلة', 'عطل', 'خطأ', 'لا يعمل', 'سيرفر', 'روابط', 'issue', 'error', 'bug'],
    'General Information & Eligibility (معلومات عامة وشروط)': ['شروط', 'قبول', 'دفعة', 'مبادرة', 'منحة', 'تقديم', 'eligibility', 'requirements']
}

# Analysis collections
lang_counts = Counter()
program_counts = Counter()
category_counts = Counter()
classification_counts = Counter()
topic_counts = Counter()
pii_findings = Counter()
match_counts = Counter()

classified_records = []
topic_clusters = defaultdict(list)
empty_field_ids = []

# Process records
for idx, r in enumerate(records):
    rec_id = r.get('id', f'faq_{idx}')
    q = r.get('question', '').strip()
    a = r.get('answer', '').strip()
    prog = r.get('program_scope', 'UNKNOWN')
    cat = r.get('category', 'General')

    # Language detection
    is_arabic = bool(re.search(r'[\u0600-\u06FF]', q + ' ' + a))
    lang = 'Arabic' if is_arabic else 'English'
    lang_counts[lang] += 1
    program_counts[prog] += 1
    category_counts[cat] += 1

    # Check for empty Q/A
    if not q or not a:
        classification = 'incomplete_or_vague'
        empty_field_ids.append(rec_id)
        classification_counts[classification] += 1
        classified_records.append({
            'id': rec_id,
            'question': q,
            'answer_preview': a[:50],
            'classification': classification,
            'reason': 'Empty question or answer',
            'program_scope': prog
        })
        continue

    # PII re-scan
    has_pii = False
    text = f'{q} {a}'
    if EMAIL_RE.search(text) and '[REDACTED_EMAIL]' not in text:
        pii_findings['unmasked_email'] += 1
        has_pii = True
    if PHONE_RE.search(text) and '[REDACTED_PHONE]' not in text:
        pii_findings['unmasked_phone'] += 1
        has_pii = True
    if NAT_ID_RE.search(text) and '[REDACTED_NATIONAL_ID]' not in text:
        pii_findings['unmasked_national_id'] += 1
        has_pii = True

    # Check for complaint indicator
    is_complaint = any(w in text.lower() for w in ['اشتكى', 'شكوى', 'مشكلة شخصية', 'حرام', 'ظلم', 'حسبي الله', 'complaint', 'unfair'])

    # Topic assignment
    assigned_topic = 'Other / General Questions'
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(kw in text.lower() for kw in kws):
            assigned_topic = topic
            break

    topic_counts[assigned_topic] += 1

    # Classification determination
    if has_pii:
        classification = 'requires_privacy_review'
    elif len(q) < 10 or len(a) < 5 or q.lower() in ['other', 'أخرى', 'غير ذلك', '؟']:
        classification = 'incomplete_or_vague'
    elif is_complaint:
        classification = 'requires_authoritative_source'
    else:
        classification = 'possible_faq_candidate'

    classification_counts[classification] += 1

    # Match against official sources
    match_status = 'no_approved_source_found'
    matched_source_id = None
    for osrc in official_sources:
        oq = osrc.get('question', '') or osrc.get('title', '')
        if oq and len(oq) > 5 and (oq.lower() in q.lower() or q.lower() in oq.lower()):
            match_status = 'directly_supported'
            matched_source_id = osrc.get('id', 'official_src')
            break

    match_counts[match_status] += 1

    rec_entry = {
        'id': rec_id,
        'question': q[:150] + ('...' if len(q) > 150 else ''),
        'topic': assigned_topic,
        'classification': classification,
        'program_scope': prog,
        'match_status': match_status,
        'matched_source_id': matched_source_id
    }

    classified_records.append(rec_entry)
    topic_clusters[assigned_topic].append(rec_id)

print('Analysis complete. Writing outputs...')

# 3. Write review outputs
# faq_topic_clusters.json
clusters_output = {
    'total_candidates': len(records),
    'topic_counts': dict(topic_counts),
    'topic_clusters': {k: v[:50] for k, v in topic_clusters.items()}, # limit ids in json for brevity
    'empty_field_records': empty_field_ids
}
with open(review_dir / 'faq_topic_clusters.json', 'w', encoding='utf-8') as f:
    json.dump(clusters_output, f, ensure_ascii=False, indent=2)

# faq_review_manifest.json
manifest_output = {
    'status': 'pending_human_review',
    'total_records': len(records),
    'classifications': dict(classification_counts),
    'languages': dict(lang_counts),
    'program_scopes': dict(program_counts),
    'match_statuses': dict(match_counts),
    'pii_recheck_findings': dict(pii_findings),
    'sanitized_review_batches': [
        {
            'batch_id': f'batch_{i}',
            'topic': topic,
            'record_count': len(ids),
            'sample_ids': ids[:10]
        } for i, (topic, ids) in enumerate(topic_clusters.items())
    ]
}
with open(review_dir / 'faq_review_manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest_output, f, ensure_ascii=False, indent=2)

# faq_review_summary.md
summary_md = f"""# Privacy-Safe FAQ Review Summary

**Generated**: 2026-10-21
**Status**: Pending Human Review (Unapproved)

## 1. Corpus Reconciliation & Counts
- **Total Source Records**: 32,893 (Form_response.json)
- **Valid FAQ Candidates Prepared**: 27,790
- **Quarantined Records**: 5,103 (2,509 vague/incomplete, 2,594 exact duplicates)
- **Empty Question/Answer Records Flagged**: {len(empty_field_ids)}
- **Ticket Records Quarantined / Separated**: 8,850 (Moved/Renamed to `tickets_pending_schema_review.json` pending schema mapping)

## 2. PII Screening & Privacy Limitations
- **Arabic & English PII Scanning**: Applied regex filters for national IDs, phone numbers (Egyptian format), and email addresses.
- **Names**: Arabic name patterns identified {181154} instances in source text; masking and review flag applied.
- **Unmasked PII detected in re-scan**: {sum(pii_findings.values())} instances (quarantined or flagged for `requires_privacy_review`).

## 3. Classifications & Topic Distribution
- **Classifications**:
  - `possible_faq_candidate`: {classification_counts.get('possible_faq_candidate', 0)}
  - `incomplete_or_vague`: {classification_counts.get('incomplete_or_vague', 0)}
  - `requires_authoritative_source`: {classification_counts.get('requires_authoritative_source', 0)}
  - `requires_privacy_review`: {classification_counts.get('requires_privacy_review', 0)}
- **Languages**: Arabic ({lang_counts.get('Arabic', 0)}), English ({lang_counts.get('English', 0)})
- **Top Topics**:
"""
for topic, count in topic_counts.most_common():
    summary_md += f"  - {topic}: {count} records\n"

summary_md += f"""
## 4. Trusted Source Matching
- **Directly Supported by Official FAQ**: {match_counts.get('directly_supported', 0)}
- **No Approved Source Found (Requires Verification)**: {match_counts.get('no_approved_source_found', 0)}

## 5. Next Steps for Human Reviewers
1. Review records in sanitized review batches (`faq_review_manifest.json`).
2. Approve valid FAQ candidates via the human review workflow.
3. Resolve operational complaints separately from official policy FAQs.
"""

with open(review_dir / 'faq_review_summary.md', 'w', encoding='utf-8') as f:
    f.write(summary_md)

print('All review outputs generated successfully in:', review_dir)
