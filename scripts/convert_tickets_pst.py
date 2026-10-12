#!/usr/bin/env python3
"""
NexaServe Tickets PST to JSON Converter
=======================================
Extracts and structures all student/citizen customer support tickets from:
  E:\\NexaServe\\FAQs\\tickets.pst

Outputs:
  1. FAQs/converted/tickets.json   - Full structured dataset
  2. FAQs/converted/tickets.jsonl  - Line-delimited JSON stream
  3. FAQs/tickets.json             - Standalone dataset in FAQs folder
  4. FAQs/converted/tickets_manifest.json - Metadata and extraction stats
"""

import os
import sys
import json
import re
import email
import email.policy
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# Ensure UTF-8 on Windows consoles
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


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def parse_ticket_eml(eml_path: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
    """Parses a single .eml ticket email and extracts structured fields."""
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)
        
    subject = msg.get('Subject', '').strip()
    from_addr = msg.get('From', '').strip()
    to_addrs = [a.strip() for a in msg.get('To', '').split(',') if a.strip()]
    date_raw = msg.get('Date', '').strip()
    message_id = msg.get('Message-ID', '').strip()
    
    # Parse date to ISO if possible
    iso_date = None
    if msg.get('Date'):
        try:
            parsed_dt = email.utils.parsedate_to_datetime(date_raw)
            if parsed_dt:
                iso_date = parsed_dt.isoformat()
        except Exception:
            pass

    body_part = msg.get_body(preferencelist=('html', 'plain'))
    if not body_part:
        return None
        
    html_content = body_part.get_content()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract key-value pairs from <p><b>Key:</b> Value</p>
    field_map = {}
    for p_elem in soup.find_all('p'):
        b_tag = p_elem.find('b')
        if b_tag:
            k = b_tag.get_text(strip=True).rstrip(':').strip()
            v = p_elem.get_text(strip=True).replace(b_tag.get_text(strip=True), '', 1).strip()
            field_map[k] = v
            
    # Extract ticket URL
    ticket_url = None
    for a_tag in soup.find_all('a'):
        txt = a_tag.get_text(strip=True)
        if 'متابعة التذكرة' in txt:
            ticket_url = a_tag.get('href')
            break
            
    # Extract specific fields
    ticket_num = field_map.get('رقم التذكرة')
    if not ticket_num:
        m_num = re.search(r'#([0-9]+)', subject) or re.search(r'([0-9]{4,})', subject)
        if m_num:
            ticket_num = m_num.group(1)
            
    group_code = field_map.get('رقم المجموعة')
    track = field_map.get('التخصص')
    student_name = field_map.get('اسم الطالب')
    issue_type = field_map.get('نوع المشكلة')
    description = field_map.get('الوصف')
    
    import html
    if description:
        description = html.unescape(description).strip()
    if student_name:
        student_name = html.unescape(student_name).strip()
    if track:
        track = html.unescape(track).strip()
    if group_code:
        group_code = html.unescape(group_code).strip()
    subject = html.unescape(subject).strip()
    
    full_text = soup.get_text(' ', strip=True)
    full_text_norm = re.sub(r'\s+', ' ', full_text).strip()
    
    # Compute content hash
    content_basis = f"{ticket_num or ''}||{subject}||{description or ''}||{student_name or ''}"
    c_hash = hashlib.sha256(content_basis.encode('utf-8')).hexdigest()
    
    ticket_id = f"ticket_{ticket_num}" if ticket_num else f"ticket_eml_{c_hash[:10]}"
    
    return {
        "id": ticket_id,
        "ticket_number": ticket_num,
        "group_code": group_code,
        "track": track,
        "student_name": student_name,
        "issue_type": issue_type,
        "description": description,
        "ticket_url": ticket_url,
        "subject": subject,
        "from": from_addr,
        "to": to_addrs,
        "date": iso_date or date_raw,
        "date_raw": date_raw,
        "message_id": message_id,
        "program_scope": "DEBI",
        "category": "support_ticket",
        "full_text": full_text_norm,
        "content_hash": c_hash,
        "source_archive": "FAQs/tickets.pst",
        "source_item": eml_path.name
    }


def convert_tickets_pst(
    repo_root: Path,
    pst_path: Path,
    extracted_eml_dir: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """Converts extracted EML ticket files into tickets.json and tickets.jsonl."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pst_sha256 = compute_file_sha256(pst_path)
    
    eml_files = sorted(
        list(extracted_eml_dir.glob('**/*.eml')),
        key=lambda p: (len(p.stem), p.stem)
    )
    
    records: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_hashes = set()
    
    for ef in eml_files:
        ticket = parse_ticket_eml(ef, repo_root)
        if ticket:
            c_hash = ticket["content_hash"]
            if c_hash in seen_hashes:
                continue
            seen_hashes.add(c_hash)
            
            # Handle potential duplicate ticket numbers by making stable unique ID
            base_id = ticket["id"]
            if base_id in seen_ids:
                ticket["id"] = f"{base_id}_{ticket['source_item'].replace('.eml', '')}"
            seen_ids.add(ticket["id"])
            records.append(ticket)
            
    # Metrics
    tracks_dist = {}
    groups_dist = {}
    for r in records:
        trk = r.get("track") or "غير محدد"
        tracks_dist[trk] = tracks_dist.get(trk, 0) + 1
        grp = r.get("group_code") or "غير محدد"
        groups_dist[grp] = groups_dist.get(grp, 0) + 1
        
    dataset = {
        "schema_version": "1.0",
        "dataset_type": "support_tickets",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": "FAQs/tickets.pst",
        "source_file_sha256": pst_sha256,
        "source_file_size_bytes": pst_path.stat().st_size,
        "total_tickets": len(records),
        "tickets": records
    }
    
    # 1. FAQs/converted/tickets.json
    out_json_path = output_dir / "tickets.json"
    with open(out_json_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        
    # 2. FAQs/converted/tickets.jsonl
    out_jsonl_path = output_dir / "tickets.jsonl"
    with open(out_jsonl_path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            
    # 3. Direct copy in FAQs/tickets.json
    faqs_root_json = pst_path.parent / "tickets.json"
    with open(faqs_root_json, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        
    # 4. Manifest
    manifest_path = output_dir / "tickets_manifest.json"
    manifest_data = {
        "pipeline_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": "FAQs/tickets.pst",
        "source_sha256": pst_sha256,
        "size_bytes": pst_path.stat().st_size,
        "total_tickets_extracted": len(records),
        "total_eml_files": len(eml_files),
        "tracks_distribution": dict(sorted(tracks_dist.items(), key=lambda x: x[1], reverse=True)[:15]),
        "top_groups": dict(sorted(groups_dist.items(), key=lambda x: x[1], reverse=True)[:15]),
        "artifacts": [
            str(out_json_path.relative_to(repo_root)).replace('\\', '/'),
            str(out_jsonl_path.relative_to(repo_root)).replace('\\', '/'),
            str(faqs_root_json.relative_to(repo_root)).replace('\\', '/'),
            str(manifest_path.relative_to(repo_root)).replace('\\', '/')
        ]
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        
    return {
        "total_tickets": len(records),
        "json_path": out_json_path,
        "jsonl_path": out_jsonl_path,
        "faqs_path": faqs_root_json,
        "manifest_path": manifest_path
    }


def main():
    repo_root = Path(".").resolve()
    pst_path = repo_root / "FAQs" / "tickets.pst"
    eml_dir = repo_root / "scratch" / "pst_extract"
    output_dir = repo_root / "FAQs" / "converted"
    
    print("=" * 70)
    print(" 🎫 NexaServe Tickets PST to JSON Conversion Pipeline")
    print("=" * 70)
    print(f" Source PST : {pst_path}")
    print(f" Extracted  : {eml_dir}")
    print(f" Output Dir : {output_dir}")
    print("-" * 70)
    
    res = convert_tickets_pst(repo_root, pst_path, eml_dir, output_dir)
    
    print(f"✅ Conversion complete! Extracted {res['total_tickets']} support tickets.")
    print(f"   • Consolidated JSON : {res['json_path']}")
    print(f"   • Streaming JSONL   : {res['jsonl_path']}")
    print(f"   • Root FAQs JSON    : {res['faqs_path']}")
    print(f"   • Manifest          : {res['manifest_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
