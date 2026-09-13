import json
import glob
import os

def update_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace Arabic Welcome list
    old_ar_list = """📌 *مبادرة مهارات المستقبل* - برامج تدريبية وشهادات احترافية\\n🔐 *التوقيع الرقمي والتوكن* - إصدار وتفعيل الهوية الرقمية\\n📦 *تتبع الطلبات والمعاملات* - استعلام فوري بالرقم المرجعي\\n📡 *شكاوى الاتصالات* - تقديم ومتابعة الشكاوى الرسمية\\n⏱️ *ساعات العمل والدعم الفني* - مواعيد الخدمة واتفاقيات SLA\\n🛡️ *حماية البيانات الشخصية* - سياسات الخصوصية والأمان"""
    
    new_ar_list = """📌 *مبادرة الرواد الرقميون (DEPI)* - برامج الماجستير والتدريب المهني\\n📝 *شروط التقديم والتسجيل* - الفئات المستهدفة والمستندات المطلوبة\\n🎓 *نظام الدراسة والامتحانات* - المنصة التعليمية والإجازات\\n🏆 *التخصصات المتاحة* - الذكاء الاصطناعي، الأمن السيبراني، وغيرها\\n⏱️ *الدعم الفني* - مساعدة واستفسارات"""
    
    # Replace English Welcome list
    old_en_list = """📌 *Future Skills Initiative* - Training & Professional Certifications\\n🔐 *Digital Signature & Token* - National Digital Identity Issuance\\n📦 *Order & Shipment Tracking* - Real-time Status by Reference Number\\n📡 *Telecom Complaints* - File & Track Service Provider Disputes\\n⏱️ *Working Hours & SLA* - Support Availability & Response Times\\n🛡️ *Data Privacy & Protection* - PDPL Compliance & Security"""
    
    new_en_list = """📌 *Digital Pioneers Initiative (DEPI)* - Master's & Professional Training\\n📝 *Admissions & Registration* - Eligibility & Required Documents\\n🎓 *Study & Exams System* - LMS & Attendance\\n🏆 *Available Tracks* - AI, Cybersecurity, etc.\\n⏱️ *Support* - Help & Inquiries"""

    # Replace Out of scope list
    old_out_ar = """📌 مبادرة مهارات المستقبل\\\\n🔐 التوقيع الرقمي والتوكن المشفر\\\\n📦 تتبع الطلبات والمعاملات\\\\n📡 شكاوى الاتصالات والفواتير\\\\n⏱️ ساعات العمل والدعم الفني"""
    
    new_out_ar = """📌 مبادرة الرواد الرقميون (DEPI)\\\\n📝 شروط التقديم والتسجيل\\\\n🎓 نظام الدراسة والامتحانات\\\\n🏆 التخصصات المتاحة\\\\n⏱️ الدعم الفني"""

    old_out_en = """📌 Future Skills Initiative\\\\n🔐 Digital Signature & Token\\\\n📦 Order & Shipment Tracking\\\\n📡 Telecom Complaints\\\\n⏱️ Working Hours & SLA"""
    
    new_out_en = """📌 Digital Pioneers Initiative (DEPI)\\\\n📝 Admissions & Registration\\\\n🎓 Study & Exams System\\\\n🏆 Available Tracks\\\\n⏱️ Support"""

    # Single line replaces
    old_single_ar = "مبادرة مهارات المستقبل، التوقيع الرقمي، تتبع الطلبات، شكاوى الاتصالات، أو ساعات العمل"
    new_single_ar = "مبادرة الرواد الرقميون (DEPI)، شروط التقديم، أو نظام الدراسة والامتحانات"

    content = content.replace(old_ar_list, new_ar_list)
    content = content.replace(old_en_list, new_en_list)
    content = content.replace(old_out_ar, new_out_ar)
    content = content.replace(old_out_en, new_out_en)
    content = content.replace(old_single_ar, new_single_ar)
    content = content.replace("مبادرة مهارات المستقبل", "مبادرة الرواد الرقميون (DEPI)")
    content = content.replace("لوزارة الاتصالات وتقنية المعلومات", "لمبادرة الرواد الرقميون (DEPI)")
    content = content.replace("MCIT AI Customer Service Platform", "DEPI AI Customer Service Platform")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

for json_file in glob.glob('infra/n8n/workflows/*.json'):
    update_file(json_file)
    print(f"Updated {json_file}")
