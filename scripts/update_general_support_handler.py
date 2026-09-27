import json

file_path = "infra/n8n/workflows/01_gateway_dispatcher.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for node in data.get("nodes", []):
    if node.get("name") == "General Support Handler":
        js = """/* === ACTIVE JAVASCRIPT IMPLEMENTATION === */
const ai = $('Call SubWF 03 - AI Intent Engine').first()?.json.ai_output || {};
const norm = $('Channel Ingress & PII Sanitizer').first()?.json || {};
const isAr = norm.locale === 'ar';
const customerName = norm.full_name || '';
const rawMsg = (norm.customer_message || '').toLowerCase();
const isGreeting = ['مرحبا', 'مرحباً', 'اهلا', 'أهلا', 'سلام', 'السلام', 'صباح', 'مساء', 'hello', 'hi', 'hey'].some(w => rawMsg.includes(w));

const unsupportedAr = `عذراً، لا تتوفر معلومات حول هذا الموضوع في قاعدة المعرفة، حيث يختص نظامنا بمبادرات وزارة الاتصالات (مبادرة الرواد الرقميون Digilians ومبادرة رواد مصر الرقمية DEBI). يمكنك التواصل مع فريق الدعم للمساعدة.`;
const unsupportedEn = `Sorry, no information is available regarding this topic. Our platform is specialized in MCIT initiatives (Digilians and DEBI). Please contact the support team for assistance.`;

const welcomeAr = `أهلاً وسهلاً بك${customerName ? ' ' + customerName : ''} في منصة خدمة العملاء لمبادرة الرواد الرقميون (DEPI)! 🏛️

يسعدني مساعدتك. يمكنك الاستفسار عن أي من خدماتنا التالية:

📌 *مبادرة الرواد الرقميون (DEPI)* - برامج الماجستير والتدريب المهني
📝 *شروط التقديم والتسجيل* - الفئات المستهدفة والمستندات المطلوبة
🎓 *نظام الدراسة والامتحانات* - المنصة التعليمية والإجازات
🏆 *التخصصات المتاحة* - الذكاء الاصطناعي، الأمن السيبراني، وغيرها
⏱️ *الدعم* - مساعدة واستفسارات

ما الذي تودّ الاستفسار عنه؟`;

const welcomeEn = `Welcome${customerName ? ' ' + customerName : ''} to the DEPI AI Customer Service Platform! 🏛️

I'm here to help. You can inquire about any of our services:

📌 *Digital Pioneers Initiative (DEPI)* - Master's & Professional Training
📝 *Admissions & Registration* - Eligibility & Required Documents
🎓 *Study & Exams System* - LMS & Attendance
🏆 *Available Tracks* - AI, Cybersecurity, etc.
⏱️ *Support Team* - Help & Inquiries

What would you like to know more about?`;

const defaultReply = isGreeting ? (isAr ? welcomeAr : welcomeEn) : (isAr ? unsupportedAr : unsupportedEn);

return [{
  json: {
    status: 'general',
    intent_handled: 'general_support',
    reply: (ai.intent === 'general_support' && isGreeting) ? (ai.direct_response || (isAr ? welcomeAr : welcomeEn)) : (ai.direct_response || defaultReply)
  }
}];"""
        node["parameters"]["jsCode"] = js
        print("Updated General Support Handler!")

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Saved 01_gateway_dispatcher.json successfully!")
