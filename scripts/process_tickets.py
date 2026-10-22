import json
import re
import os
import sys
from pathlib import Path
from collections import Counter, defaultdict
import uuid
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

# --- Configuration ---
prepared_dir = Path(r'E:\NexaServe\FAQs\New Fiels\JSON\prepared')
review_dir = prepared_dir / 'review'
review_dir.mkdir(parents=True, exist_ok=True)

source_tickets_file = prepared_dir / 'tickets_pending_schema_review.json'
prepared_tickets_output_file = prepared_dir / 'tickets_import_ready.json'
quarantined_tickets_report_file = review_dir / 'quarantined_tickets_report.json'
validation_report_file = review_dir / 'ticket_validation_report.md'

PRIORITY_MAP = {'عادي': 'medium', 'منخفض': 'low', 'مرتفع': 'high', 'عاجل': 'urgent'}
STATUS_MAP = {'مفتوحة': 'open', 'قيد التعيين': 'assigned', 'قيد التنفيذ': 'in_progress', 'تم الحل': 'resolved', 'مغلقة': 'closed'}

# --- Helper Functions ---
def safe_get(data, keys, default=None):
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys:
        if isinstance(data, dict) and key in data and data[key] not in [None, '']:
            return data[key]
    return default

def normalize_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', str(text))
    return text.strip()

# --- Main Processing ---

print('Starting ticket data preparation...')

if not source_tickets_file.exists():
    print(f'Error: Source file {source_tickets_file} not found.')
    sys.exit(1)

with open(source_tickets_file, 'r', encoding='utf-8') as f:
    root_data = json.load(f)

source_records = root_data.get('records', []) if isinstance(root_data, dict) else root_data

print(f'Loaded {len(source_records)} source ticket records.')

processed_records = []
quarantined_records = []
processed_ticket_numbers = set()

# --- Processing Loop ---
for i, record in enumerate(source_records):
    original_ref = f'record_{i}'
    quarantine_reasons = []

    # Handle inconsistent structure: try source_data first, then top-level
    data = record.get('source_data', record) if isinstance(record, dict) else {}

    # Extract ticket_number
    ticket_num_raw = safe_get(data, ['رقم التذكرة', 'ticket_number'])
    ticket_num = normalize_text(ticket_num_raw) if ticket_num_raw is not None else None

    if not ticket_num:
        quarantine_reasons.append('Missing or empty ticket_number')
    elif ticket_num in processed_ticket_numbers:
        quarantine_reasons.append(f'Duplicate ticket_number: {ticket_num}')
    else:
        processed_ticket_numbers.add(ticket_num)

    # Extract reason
    reason = normalize_text(safe_get(data, ['الشكوى', 'تفاصيل الشكوى', 'subject', 'description']))
    if not reason:
        quarantine_reasons.append('Missing subject/description')

    # customer_id: Missing (quarantine)
    customer_id = None
    quarantine_reasons.append('Missing customer_id (required, no DB relationship)')

    # Status/Priority mapping
    status_raw = safe_get(data, ['الحالة', 'status'])
    priority_raw = safe_get(data, ['الأولوية', 'priority'])

    mapped_status = STATUS_MAP.get(status_raw) if status_raw in STATUS_MAP else None
    mapped_priority = PRIORITY_MAP.get(priority_raw) if priority_raw in PRIORITY_MAP else None

    if not mapped_status: quarantine_reasons.append(f'Unrecognized or missing status: {status_raw}')
    if not mapped_priority: quarantine_reasons.append(f'Unrecognized or missing priority: {priority_raw}')

    mapped_assigned_team = safe_get(data, ['القسم (المرحلة)', 'assigned_team'])
    if not mapped_assigned_team: quarantine_reasons.append('Missing assigned_team')

    # Timestamps
    created_at_raw = safe_get(data, ['تاريخ الإنشاء', 'created_at'])
    mapped_created_at = None
    if created_at_raw:
        try:
            dt = datetime.strptime(str(created_at_raw), '%Y-%m-%d %H:%M:%S')
            mapped_created_at = dt.replace(tzinfo=timezone.utc).isoformat()
        except: quarantine_reasons.append(f'Invalid created_at: {created_at_raw}')

    if quarantine_reasons:
        quarantined_records.append({
            'original_reference': original_ref,
            'ticket_number': ticket_num or 'N/A',
            'reason_for_quarantine': ', '.join(quarantine_reasons),
            'source_summary': {'ticket_number': ticket_num, 'status': status_raw}
        })
    else:
        processed_records.append({
            'ticket_number': ticket_num, 'customer_id': customer_id, 'priority': mapped_priority,
            'status': mapped_status, 'reason': reason, 'assigned_team': mapped_assigned_team,
            'created_at': mapped_created_at
        })

print(f'Processed: {len(processed_records)}, Quarantined: {len(quarantined_records)}.')

with open(prepared_tickets_output_file, 'w', encoding='utf-8') as f:
    json.dump(processed_records, f, ensure_ascii=False, indent=2)
with open(quarantined_tickets_report_file, 'w', encoding='utf-8') as f:
    json.dump(quarantined_records, f, ensure_ascii=False, indent=2)

print('Outputs written.')
