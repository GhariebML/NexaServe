-- ==============================================================================
-- NexaServe Customer Service AI - Comprehensive Bilingual FAQs Expansion
-- ==============================================================================

-- 1. Ensure Full-Text Search / Trigram Extension for Smarter Arabic Search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_kb_question_ar_trgm ON knowledge_base USING gin (question_ar gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_kb_answer_ar_trgm ON knowledge_base USING gin (answer_ar gin_trgm_ops);

-- 2. Insert or Update Core FAQs
INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar, keywords_ar)
VALUES
    (
        'overview_services',
        'What official services and solutions do you provide?',
        'We provide digital citizen and customer services including:
1. Future Skills Training & Professional Certification Grants.
2. National Digital Signature & Smart Token Issuance.
3. Telecommunications & Internet Service Complaint Resolution.
4. Real-time Service Request & Shipment Tracking (SPL, Aramex).
5. 24/7 AI Automated Assistance with Human Escalation Support.',
        ARRAY['services', 'offerings', 'what do you do', 'overview', 'help', 'capabilities', 'list'],
        'ما هي الخدمات والحلول المتاحة التي تقدمونها؟',
        'يسعدنا تقديم باقة متكاملة من الخدمات الرقمية المعتمدة لوزارة الاتصالات وتقنية المعلومات، وتشمل:

📌 *مبادرة مهارات المستقبل*: برامج تدريبية وتأهيلية متقدمة في الذكاء الاصطناعي، الحوسبة السحابية، والأمن السيبراني.
🔐 *التوقيع الرقمي والتوكن المشفر*: إصدار وتفعيل بطاقات ورموز الهوية الرقمية المعتمدة للأفراد والأعمال.
📡 *خدمات تنظيم الاتصالات والشكاوى*: استقبال وتصعيد شكاوى جودة الاتصالات والفواتير ومتابعتها مع المزودين.
📦 *تتبع الطلبات والمعاملات*: استعلام فوري عن حالة الشحنات والطلبات برقم الخدمة (مثل: SRV-1001).
👨‍💼 *الدعم والمساعدة المباشرة*: دعم رقمي ذكي على مدار الساعة مع إمكانية التحويل لمشرف خدمة العملاء.

هل تود الاستفسار بالتفصيل عن إحدى هذه الخدمات؟',
        ARRAY['خدمات', 'الخدمات', 'بتقدموها', 'تقدمون', 'ما هي خدماتكم', 'دليل الخدمات', 'قائمة', 'المتاحة', 'ممكن اسال', 'ايش تقدمون']
    ),
    (
        'citizen_services',
        'What is the MCIT Future Skills initiative and how do I apply?',
        'The MCIT Future Skills initiative provides accredited training and professional certifications in advanced digital fields (AI, Cloud, Cybersecurity). Saudi citizens can apply directly through the official portal using National Single Sign-On (Nafath). Applications are processed within 5 business days.',
        ARRAY['future skills', 'training', 'certification', 'apply', 'scholarship', 'ai course'],
        'ما هي مبادرة مهارات المستقبل وكيف يمكنني التقديم عليها؟',
        'مبادرة مهارات المستقبل هي إحدى المبادرات الوطنية التابعة لوزارة الاتصالات وتقنية المعلومات، وتهدف إلى تأهيل وتطوير الكوادر الوطنية في مجالات التقنية الحديثة:

🎯 *المسارات المعتمدة*:
• الذكاء الاصطناعي وعلم البيانات.
• الحوسبة السحابية وهندسة النظم.
• الأمن السيبراني وشبكات المستقبل.

📋 *طريقة وشروط التقديم*:
1. أن يكون المتقدم مواطناً/مواطنة سعودية.
2. التسجيل عبر المنصة الوطنية الموحدة باستخدام النفاذ الوطني الموحد (نفاذ).
3. تتم مراجعة ومعالجة الطلبات خلال 5 أيام عمل وإشعارك بالنتيجة عبر الرسائل.',
        ARRAY['مهارات المستقبل', 'تدريب', 'شهادات', 'دورة', 'تقديم', 'ذكاء اصطناعي', 'نفاذ', 'شروط', 'طريقة التقديم', 'مهارات']
    ),
    (
        'digital_identity',
        'What are the requirements for issuing a Digital Signature and Certification Token?',
        'To obtain an approved National Digital Signature token, applicants must possess an active Absher/Nafath account and submit a verification request. The cryptographic smart token is dispatched via Saudi Post (SPL) within 48-72 hours of approval.',
        ARRAY['digital signature', 'token', 'smartcard', 'absher', 'nafath', 'identity', 'pki'],
        'ما هي متطلبات وإجراءات إصدار رمز التوقيع الرقمي المعتمد؟',
        'للحصول على رمز التوقيع الرقمي الوطني المعتمد (Hardware Token):

📋 *المتطلبات الأساسية*:
1. حساب نشط ومفعل في منصة (أبشر / نفاذ).
2. تقديم طلب إصدار الشهادة الرقمية عبر البوابة الإلكترونية.

🚚 *الشحن والتسليم*:
• يتم تشفير الرمز وإرساله عبر البريد السعودي (سبل) خلال 48 إلى 72 ساعة عمل من تاريخ الاعتماد.
• يمكنك تتبع الشحنة فور صدورها برقم التتبع المسجل في معاملتك.',
        ARRAY['توقيع رقمي', 'توكن', 'نفاذ', 'أبشر', 'هوية رقمية', 'بطاقة ذكية', 'إصدار', 'توقيع']
    ),
    (
        'telecom_regulations',
        'How can I file a formal telecommunication complaint regarding poor service or billing disputes?',
        'Under MCIT and CST regulations, you must first file a formal ticket with your service provider. If the provider fails to resolve your ticket within 5 business days, or if the resolution is unsatisfactory, you may escalate the dispute to the CST / MCIT escalation platform with your complaint reference number.',
        ARRAY['telecom', 'complaint', 'billing', 'poor service', 'cst', 'dispute', 'escalate'],
        'كيف يمكنني تقديم شكوى رسمية بشأن خدمات الاتصالات أو الفواتير؟',
        'وفقاً للوائح التنظيمية المعتمدة من هيئة الاتصالات والفضاء والتقنية (CST):

1️⃣ *الخطوة الأولى*: تقديم بلاغ رسمي أولاً لدى مزود الخدمة الخاص بك (stc، موبايلي، زين، سلام).
2️⃣ *المهلة النظامية*: يُمنح مزود الخدمة مهلة 5 أيام عمل للرد وحل المشكلة.
3️⃣ *التصعيد*: في حال عدم الرد أو عدم الرضا عن الحل، يمكنك فوراً تصعيد الشكوى عبر بوابة الهيئة مع إرفاق الرقم المرجعي للشكوى.

هل ترغب في تسجيل تذكرة دعم أو تصعيد شكوى حالية؟',
        ARRAY['شكوى', 'اتصالات', 'فاتورة', 'انقطاع', 'تصعيد', 'مزود الخدمة', 'شبكة', 'شكاوي', 'مشكلة']
    ),
    (
        'policies',
        'What are the official working hours and SLA response times for technical support?',
        'Our automated AI Customer Service system operates 24/7. Live human specialist support teams are available Sunday through Thursday from 8:00 AM to 5:00 PM AST. Urgent escalated tickets have a guaranteed initial response SLA of 30 minutes; standard tickets within 4 business hours.',
        ARRAY['hours', 'sla', 'response time', 'working hours', 'support team', 'turnaround', 'timing'],
        'ما هي أوقات العمل الرسمية ومواعيد الاستجابة المعتمدة للدعم الفني؟',
        'نحن متواجدون لخدمتك وفق الأوقات التالية:

🤖 *المساعد الذكي (AI)*: يعمل على مدار الساعة طوال أيام الأسبوع (24/7) للإجابة اللحظية وتتبع الطلبات.
👨‍💼 *فريق خدمة العملاء والمشرفين*: متاح من الأحد إلى الخميس، من الساعة 8:00 صباحاً حتى 5:00 مساءً.

⏱️ *اتفاقيات مستوى الخدمة (SLA)*:
• التذاكر الطارئة: استجابة خلال 30 دقيقة.
• التذاكر العامة: استجابة خلال 4 ساعات عمل.',
        ARRAY['ساعات العمل', 'أوقات', 'دوام', 'استجابة', 'اتفاقية مستوى الخدمة', 'دعم فني', 'متى تعملون', 'مواعيد']
    ),
    (
        'order_tracking',
        'How can I track the status of my service request or shipment?',
        'You can track your service request directly by providing your request reference code (e.g. SRV-1001 or ORD-1001). The system will fetch real-time carrier details, delivery estimates, and current processing stage.',
        ARRAY['track', 'order', 'status', 'shipment', 'where is my order', 'delivery'],
        'كيف يمكنني متابعة وتتبع حالة طلبي أو معاملتي؟',
        'يمكنك الاستعلام عن حالة طلبك أو شحنتك فوراً بمجرد كتابة رقم الطلب في المحادثة (مثل: *SRV-1001* أو *ORD-1001*).

🔍 سيزودك النظام مباشرة بـ:
• حالة الطلب (قيد المراجعة، تم التجهيز، تم الشحن، مكتمل).
• شركة الشحن ورقم التتبع اللحظي (SPL، أرامكس).
• الموعد المتوقع للتسليم.',
        ARRAY['تتبع', 'متابعة', 'حالة الطلب', 'شحنتي', 'وين طلبي', 'استعلام', 'معاملتي']
    ),
    (
        'data_privacy',
        'How does the platform protect citizen personal data and national IDs?',
        'Our platform strictly adheres to the Saudi Personal Data Protection Law (PDPL). All sensitive personal identifiable information (PII) including Saudi National IDs, IBANs, and credit card numbers are masked in real time before storage, with complete sovereign data hosting in local PostgreSQL databases.',
        ARRAY['privacy', 'security', 'pdpl', 'national id', 'protection', 'data sovereignty'],
        'كيف تضمن المنصة حماية بياناتي الشخصية وهويتي الوطنية؟',
        'تلتزم منصتنا بأعلى معايير نظام حماية البيانات الشخصية (PDPL) والسيادة الرقمية الوطنية:

🛡️ *إخفاء البيانات الحساسة (PII Masking)*: يتم حجب أرقام الهوية الوطنية والآيبان تلقائياً واستبدالها برمز مشفر لمنع الاطلاع غير المصرح به.
🔒 *أمان البيانات وتوطينها*: جميع البيانات وسجلات التدقيق مخزنة محلياً بالكامل داخل قواعد بيانات آمنة وغير قابلة للمشاركة الخارجية.',
        ARRAY['خصوصية', 'حماية البيانات', 'هوية وطنية', 'أمان', 'سرية', 'نظام حماية البيانات']
    )
ON CONFLICT (id) DO NOTHING;
