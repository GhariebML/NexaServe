import json
import glob
import os

Saudi_Arabic_phrases = [
    "مبادرة مهارات المستقبل",
    "لوزارة الاتصالات وتقنية المعلومات",
    "وزارة الاتصالات وتقنية المعلومات",
    "وزارة الاتصالات",
    "السعودية",
    "السعودي",
    "المملكة العربية السعودية",
    "هيئة الاتصالات والفضاء والتقنية",
    "CST",
    "Nafath",
    "نفاذ",
    "أبشر",
    "Absher",
    "Saudi Post",
    "SPL",
    "Aramex",
]

Egyptian_phrases = {
    "مبادرة مهارات المستقبل": "مبادرة الرواد الرقميون (DEPI)",
    "لوزارة الاتصالات وتقنية المعلومات": "لوزارة الاتصالات وتكنولوجيا المعلومات",
    "وزارة الاتصالات وتقنية المعلومات": "وزارة الاتصالات وتكنولوجيا المعلومات",
    "وزارة الاتصالات": "وزارة الاتصالات وتكنولوجيا المعلومات",
    "السعودية": "مصر",
    "السعودي": "المصري",
    "المملكة العربية السعودية": "جمهورية مصر العربية",
    "هيئة الاتصالات والفضاء والتقنية": "هيئة تنظيم الاتصالات ومعلومات",
    "CST": "ECTA",
    "Nafath": "البطاقة الرقمية الموحدة",
    "نفاذ": "البطاقة الرقمية الموحدة",
    "أبشر": "أبشر (منصة الهوية الرقمية)",
    "Absher": "أبشر (منصة الهوية الرقمية)",
    "Saudi Post": "البريد المصري",
    "SPL": "البريد المصري",
    "Aramex": "أرامكس / البريد المصري",
}

English_phrases = {
    "MCIT AI Customer Service Platform": "DEPI AI Customer Service Platform",
    "MCIT Citizen Support Tier-1": "DEPI Citizen Support Tier-1",
    "MCIT": "DEPI",
    "Future Skills": "Digital Pioneers Initiative (DEPI)",
    "Future Skills Initiative": "Digital Pioneers Initiative (DEPI)",
    "mcit.gov.sa": "digilians.gov.eg",
    "abdullah.rashid@mcit.gov.sa": "info@digilians.gov.eg",
    "Saudi Post (SPL)": "البريد المصري",
    "Aramex": "أرامكس",
    "SPL-": "EMS-",
    "Ministry of Communications and Information Technology (MCIT)": "Ministry of Communications and Information Technology (MCIT) in collaboration with the Military Academy",
}

Saudi_single_arabic = [
    "مبادرة مهارات المستقبل، التوقيع الرقمي، تتبع الطلبات، شكاوى الاتصالات، أو ساعات العمل",
]
New_arabic_single = [
    "مبادرة الرواد الرقميون (DEPI)، شروط التقديم، نظام الدراسة والامتحانات، التخصصات، أو الدعم الفني",
]

Saudi_welcome_list_ar = """📌 *مبادرة مهارات المستقبل* - برامج تدريبية وشهادات احترافية\\n🔐 *التوقيع الرقمي والتوكن* - إصدار وتفعيل الهوية الرقمية\\n📦 *تتبع الطلبات والمعاملات* - استعلام فوري بالرقم المرجعي\\n📡 *شكاوى الاتصالات* - تقديم ومتابعة الشكاوى الرسمية\\n⏱️ *ساعات العمل والدعم الفني* - مواعيد الخدمة واتفاقيات SLA\\n🛡️ *حماية البيانات الشخصية* - سياسات الخصوصية والأمان"""
New_welcome_list_ar = """📌 *مبادرة الرواد الرقميون (DEPI)* - برامج الماجستير والتدريب المهني\\n📝 *شروط التقديم والتسجيل* - الفئات المستهدفة والمستندات المطلوبة\\n🎓 *نظام الدراسة والامتحانات* - المنصة التعليمية والإجازات\\n🏆 *التخصصات المتاحة* - الذكاء الاصطناعي، الأمن السيبراني، وغيرها\\n⏱️ *الدعم الفني* - مساعدة واستفسارات"""

Saudi_welcome_list_en = """📌 *Future Skills Initiative* - Training & Professional Certifications\\n🔐 *Digital Signature & Token* - National Digital Identity Issuance\\n📦 *Order & Shipment Tracking* - Real-time Status by Reference Number\\n📡 *Telecom Complaints* - File & Track Service Provider Disputes\\n⏱️ *Working Hours & SLA* - Support Availability & Response Times\\n🛡️ *Data Privacy & Protection* - PDPL Compliance & Security"""
New_welcome_list_en = """📌 *Digital Pioneers Initiative (DEPI)* - Master's & Professional Training\\n📝 *Admissions & Registration* - Eligibility & Required Documents\\n🎓 *Study & Exams System* - LMS & Attendance\\n🏆 *Available Tracks* - AI, Cybersecurity, etc.\\n⏱️ *Support* - Help & Inquiries"""


def update_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    changes_made = []

    for old, new in Egyptian_phrases.items():
        if old in content:
            content = content.replace(old, new)
            changes_made.append(f"Replaced: {old} -> {new[:50]}...")

    for old, new in English_phrases.items():
        if old in content:
            content = content.replace(old, new)
            changes_made.append(f"Replaced EN: {old} -> {new[:50]}...")

    if old_ar_list := Saudi_welcome_list_ar:
        if old_ar_list in content:
            content = content.replace(old_ar_list, New_welcome_list_ar)
            changes_made.append("Replaced Arabic welcome list")

    if old_en_list := Saudi_welcome_list_en:
        if old_en_list in content:
            content = content.replace(old_en_list, New_welcome_list_en)
            changes_made.append("Replaced English welcome list")

    for old, new in zip(Saudi_single_arabic, New_arabic_single):
        if old in content:
            content = content.replace(old, new)
            changes_made.append(f"Replaced single AR line")

    for phrase in Saudi_Arabic_phrases:
        if phrase in content and phrase not in ["Nafath", "أبشر", "Absher", "CST", "Saudi Post", "SPL", "Aramex"]:
            if phrase in Egyptian_phrases:
                pass
            elif phrase == "مبادرة مهارات المستقبل":
                pass
            elif phrase == "لوزارة الاتصالات وتقنية المعلومات":
                pass
            elif phrase == "وزارة الاتصالات وتقنية المعلومات":
                pass

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return changes_made

total_changes = 0
for json_file in glob.glob('infra/n8n/workflows/*.json'):
    changes = update_file(json_file)
    total_changes += len(changes)
    print(f"Updated {json_file}: {len(changes)} changes")

print(f"\nTotal changes: {total_changes}")
