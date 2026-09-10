-- ==============================================================================
-- Customer Service AI Platform - Enterprise Seed Data (Bilingual AR/EN)
-- Database: customerservice
-- ==============================================================================

-- 1. Insert Multi-Channel Customers
INSERT INTO customers (id, phone_number, email, telegram_id, whatsapp_id, full_name, preferred_language, metadata)
VALUES
    (
        'a0000000-0000-0000-0000-000000000001',
        '+966501234567',
        'abdullah.rashid@mcit.gov.sa',
        'tg_abdullah_966',
        '+966501234567',
        'Abdullah Al-Rashid',
        'ar',
        '{"vip": true, "organization": "MCIT Digital Academy", "verified": true}'::jsonb
    ),
    (
        'a0000000-0000-0000-0000-000000000002',
        '+966559876543',
        'noura.qahtani@example.com',
        'tg_noura_q',
        '+966559876543',
        'Noura Al-Qahtani',
        'ar',
        '{"vip": false, "organization": "Private Citizen", "verified": true}'::jsonb
    ),
    (
        'a0000000-0000-0000-0000-000000000003',
        '+12025550199',
        'john.smith@techvendor.com',
        'tg_john_smith',
        '+12025550199',
        'John Smith',
        'en',
        '{"vip": false, "organization": "International Tech Vendor", "verified": false}'::jsonb
    )
ON CONFLICT (phone_number) DO UPDATE
SET preferred_language = EXCLUDED.preferred_language,
    telegram_id = EXCLUDED.telegram_id,
    whatsapp_id = EXCLUDED.whatsapp_id;

-- 2. Insert Orders / Citizen Service Requests
INSERT INTO orders (order_number, customer_id, status, total_amount, currency, carrier, tracking_number, estimated_delivery, items, service_type)
VALUES
    (
        'SRV-1001',
        'a0000000-0000-0000-0000-000000000001',
        'shipped',
        0.00,
        'SAR',
        'Saudi Post (SPL)',
        'SPL-992817263',
        CURRENT_DATE + INTERVAL '2 days',
        '[{"name": "National Digital Certification Token & Smartcard", "quantity": 1, "price": 0.00}]'::jsonb,
        'Digital Identity Hardware'
    ),
    (
        'ORD-1001',
        'a0000000-0000-0000-0000-000000000001',
        'delivered',
        450.00,
        'SAR',
        'Aramex',
        'ARX-11827364',
        CURRENT_DATE - INTERVAL '3 days',
        '[{"name": "IoT Developer Kit - ESP32 MCIT Edition", "quantity": 2, "price": 225.00}]'::jsonb,
        'Hardware Procurement'
    ),
    (
        'SRV-1002',
        'a0000000-0000-0000-0000-000000000002',
        'in_review',
        0.00,
        'SAR',
        'Ministry Internal Routing',
        'REQ-88273619',
        CURRENT_DATE + INTERVAL '5 days',
        '[{"name": "Future Skills Grant Application - AI Engineering", "quantity": 1, "price": 0.00}]'::jsonb,
        'Grant Application'
    )
ON CONFLICT (order_number) DO NOTHING;

-- 3. Insert Bilingual Knowledge Base (MCIT Services, Telecom & FAQs)
INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar, keywords_ar)
VALUES
    (
        'citizen_services',
        'What is the MCIT Future Skills initiative and how do I apply?',
        'The MCIT Future Skills initiative provides accredited training and professional certifications in advanced digital fields (AI, Cloud, Cybersecurity). Saudi citizens can apply directly through the official portal using National Single Sign-On (Nafath). Applications are processed within 5 business days.',
        ARRAY['future skills', 'training', 'certification', 'apply', 'scholarship', 'ai course'],
        'ما هي مبادرة مهارات المستقبل وكيف يمكنني التقديم عليها؟',
        'مبادرة مهارات المستقبل التابعة لوزارة الاتصالات وتقنية المعلومات تهدف إلى تأهيل الكوادر الوطنية في مجالات التقنية الحديثة كالمعلوماتية والذكاء الاصطناعي والأمن السيبراني. يمكنك التقديم مباشرة عبر المنصة الوطنية الموحدة باستخدام النفاذ الوطني الموحد، وتتم معالجة الطلبات خلال 5 أيام عمل.',
        ARRAY['مهارات المستقبل', 'تدريب', 'شهادات', 'دورة', 'تقديم', 'ذكاء اصطناعي', 'نفاذ']
    ),
    (
        'telecom_regulations',
        'How can I file a formal telecommunication complaint regarding poor service or billing disputes?',
        'Under MCIT and CST regulations, you must first file a formal ticket with your service provider. If the provider fails to resolve your ticket within 5 business days, or if the resolution is unsatisfactory, you may escalate the dispute to the CST / MCIT escalation platform with your complaint reference number.',
        ARRAY['telecom', 'complaint', 'billing', 'poor service', 'cst', 'dispute', 'escalate'],
        'كيف يمكنني تقديم شكوى رسمية بشأن خدمات الاتصالات أو الفواتير؟',
        'وفقاً لأنظمة الاتصالات وتقنية المعلومات، يتعين عليك أولاً تقديم شكوى لدى مزود الخدمة الخاص بك. في حال عدم حل الشكوى خلال 5 أيام عمل أو إذا كان الحل غير مرضٍ، يمكنك تصعيد الشكوى مباشرة عبر بوابة هيئة الاتصالات والفضاء والتقنية أو منصة الشكاوى مع إرفاق رقم الشكوى المرجعي.',
        ARRAY['شكوى', 'اتصالات', 'فاتورة', 'انقطاع', 'تصعيد', 'مزود الخدمة', 'شبكة']
    ),
    (
        'digital_identity',
        'What are the requirements for issuing a Digital Signature and Certification Token?',
        'To obtain an approved National Digital Signature token, applicants must possess an active Absher/Nafath account and submit a verification request. The cryptographic smart token is dispatched via Saudi Post (SPL) within 48-72 hours of approval.',
        ARRAY['digital signature', 'token', 'smartcard', 'absher', 'nafath', 'identity', 'pki'],
        'ما هي متطلبات إصدار بطاقة أو رمز التوقيع الرقمي المعتمد؟',
        'للحصول على رمز التوقيع الرقمي الوطني المعتمد، يجب أن يكون لدى المتقدم حساب نشط ومفعل في نفاذ/أبشر، وتقديم طلب التحقق الرقمي. يتم شحن الرمز المشفر عبر البريد السعودي (سبل) خلال 48 إلى 72 ساعة من الموافقة على الطلب.',
        ARRAY['توقيع رقمي', 'توكن', 'نفاذ', 'أبشر', 'هوية رقمية', 'بطاقة ذكية']
    ),
    (
        'policies',
        'What are the official working hours and SLA response times for technical support?',
        'Our automated AI Customer Service system operates 24/7. Live human specialist support teams are available Sunday through Thursday from 8:00 AM to 5:00 PM AST. Urgent escalated tickets have a guaranteed initial response SLA of 30 minutes; standard tickets within 4 business hours.',
        ARRAY['hours', 'sla', 'response time', 'working hours', 'support team', 'turnaround'],
        'ما هي ساعات العمل الرسمية وأوقات الاستجابة المعتمدة لخدمة الدعم؟',
        'يعمل نظام المساعد الرقمي الذكي على مدار الساعة طوال أيام الأسبوع (24/7). تتواجد فرق الدعم البشري المتخصصة من الأحد إلى الخميس من الساعة 8:00 صباحاً حتى 5:00 مساءً بتوقيت مكة المكرمة. يتم الرد على البلاغات الطارئة خلال 30 دقيقة كحد أقصى، والبلاغات العادية خلال 4 ساعات عمل.',
        ARRAY['ساعات العمل', 'أوقات', 'دوام', 'استجابة', 'اتفاقية مستوى الخدمة', 'دعم فني']
    );

-- 4. Insert Sample SLA Tickets
INSERT INTO tickets (ticket_number, customer_id, priority, status, reason, assigned_team, sla_due_at)
VALUES
    (
        'TICK-8001',
        'a0000000-0000-0000-0000-000000000001',
        'high',
        'open',
        'Inquiry regarding international certification grant disbursement delay',
        'Citizen Support Tier-1',
        CURRENT_TIMESTAMP + INTERVAL '2 hours'
    )
ON CONFLICT (ticket_number) DO NOTHING;
