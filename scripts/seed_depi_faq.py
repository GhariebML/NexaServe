# -*- coding: utf-8 -*-
"""
Seed DEPI FAQs into PostgreSQL knowledge_base table
"""
import subprocess
import json
import sys

faqs = [
    {
        "category": "depi_overview",
        "question_ar": "ما هي مبادرة الرواد الرقميون وما هي أهدافها؟",
        "answer_ar": "مبادرة الرواد الرقميون (DEPI) هي مبادرة وطنية أطلقتها وزارة الاتصالات وتكنولوجيا المعلومات بالتعاون مع الأكاديمية العسكرية المصرية. تهدف المبادرة إلى تطوير مهارات الشباب المصري (من 18 إلى 32 سنة) في مجالات تكنولوجيا المعلومات والاتصالات، وبناء المهارات الشخصية والقيادية واللغوية، وإبرام شراكات مع كبرى الشركات العالمية والجامعات المرموقة لتمكين الكفاءات الوطنية.",
        "keywords_ar": ["الرواد", "الرقميون", "depi", "مبادرة", "اهداف", "تعريف", "وزارة الاتصالات", "معلومات", "عن"],
        "question": "What is the Digital Pioneers Initiative (DEPI) and its objectives?",
        "answer": "The Digital Pioneers Initiative (DEPI) is a national initiative launched by Egypt's Ministry of Communications and Information Technology (MCIT) in collaboration with the Military Academy. It aims to develop Egyptian youth (18-32 years) in ICT skills, leadership, and language proficiency through global partnerships.",
        "keywords": ["depi", "digital pioneers", "objectives", "overview", "mcit"]
    },
    {
        "category": "depi_benefits",
        "question_ar": "ما هي مزايا ومنح مبادرة الرواد الرقميون؟",
        "answer_ar": "تشمل مزايا مبادرة الرواد الرقميون (DEPI):\n- شهادة معتمدة مشتركة من وزارة الاتصالات والأكاديمية العسكرية المصرية.\n- شهادات معتمدة دولياً لكل محور تدريبي ومهارة تقنية.\n- فرصة الحصول على شهادة ماجستير من جامعة أجنبية مرموقة للمقبولين في مسار الماجستير.\n- مسار تدريبي متكامل مجاني مع جوائز ومسابقات تكنولوجية للمتفوقين.\n- تدريب عملي ميداني وإقامة فندقية مجانية كاملة شاملة كافة الوجبات داخل الأكاديمية العسكرية.",
        "keywords_ar": ["مزايا", "مميزات", "منحة", "شهادة", "ماجستير", "اقامة", "وجبات", "شهادات", "جوائز"],
        "question": "What are the benefits of the Digital Pioneers Initiative?",
        "answer": "Benefits include accredited certificates from MCIT and Military Academy, international skill certs, prestigious master's degree options, free integrated training, and full free room & board accommodation.",
        "keywords": ["benefits", "perks", "master", "certificate", "accommodation", "depi"]
    },
    {
        "category": "depi_conditions",
        "question_ar": "ما هي شروط التقديم والقبول في مبادرة الرواد الرقميون؟",
        "answer_ar": "شروط التقديم في مبادرة الرواد الرقميون (DEPI):\n1. الجنسية: مصري / مصرية.\n2. السن: من 18 حتى 32 عاماً.\n3. المؤهل الدراسي: مؤهل مناسب لمسار التدريب (خريجو الكليات، المعاهد العليا، والمعاهد المتوسطة وفوق المتوسطة)، ويمكن لطلاب السنة النهائية التقديم بإفادة رسمية.\n4. الموقف التجنيدي للذكور: أدى الخدمة العسكرية أو معفى نهائياً أو مؤجل تأجيلاً سارياً.\n5. اللغة: إلمام بأساسيات اللغة الإنجليزية (بمستوى B1 كحد أدنى).\n6. التفرغ الكامل والإقامة الداخلية بالأكاديمية العسكرية بمصر الجديدة طوال فترة المسار التدريبي.",
        "keywords_ar": ["شروط", "التقديم", "القبول", "السن", "العمر", "المؤهل", "الجيش", "التجنيد", "تفرغ", "اقامة", "انجليزي", "متطلبات", "الرواد"],
        "question": "What are the admission requirements for DEPI?",
        "answer": "Requirements: Egyptian nationality, age 18-32, relevant educational qualification (final-year students eligible with official statement), military service completed/exempt/postponed for males, English B1+, and full-time residency at the Military Academy.",
        "keywords": ["requirements", "eligibility", "conditions", "age", "qualification", "military"]
    },
    {
        "category": "depi_documents",
        "question_ar": "ما هي المستندات والأوراق المطلوبة للتقديم في المبادرة؟",
        "answer_ar": "المستندات المطلوبة للتقديم:\n- صورة بطاقة الرقم القومي (سارية).\n- أصل شهادة التخرج متضمنة المواد والتقديرات (أو بيان نجاح / إفادة قيد بالسنة النهائية).\n- شهادة الموقف من التجنيد للذكور.\n- شهادة إتقان اللغة الإنجليزية (TOEFL أو IELTS إن وجدت).\n- صحيفة الحالة الجنائية (فيش وتشبيه ساري).\n* تنبيه: تُرفع جميع المستندات بصيغة PDF وبحد أقصى 2 ميجابايت للملف.",
        "keywords_ar": ["مستندات", "اوراق", "المطلوبة", "رفع", "pdf", "شهادة", "فيش", "تجنيد", "رقم قومي", "تخرج"],
        "question": "What documents are required to apply for DEPI?",
        "answer": "National ID copy, original graduation certificate with grades (or final-year enrollment proof), military status certificate, TOEFL/IELTS certificate if available, and a valid criminal record. All uploaded as PDF up to 2MB.",
        "keywords": ["documents", "papers", "national id", "graduation", "criminal record"]
    },
    {
        "category": "depi_stages",
        "question_ar": "ما هي مراحل التقديم والقبول واختبارات المبادرة؟",
        "answer_ar": "مراحل القبول تمر بـ 7 خطوات:\n1. التسجيل الإلكتروني المجاني عبر الموقع الرسمي.\n2. فحص المستندات والتحقق من الشروط.\n3. إخطار المؤهلين مبدئياً بمواعيد الاختبارات عبر البريد الإلكتروني.\n4. اختبارات القبول (تفكير منطقي، لغة إنجليزية، أساسيات رقمية، واختبار تخصصي للمسار) بالإضافة لمقابلة شخصية وكشف طبي بالأكاديمية العسكرية.\n5. إبلاغ الناجحين لحضور المحاضرة التعريفية.\n6. توقيع الإقرار واستلام أصول المستندات.\n7. التسكين وبدء الدراسة والتدريب.",
        "keywords_ar": ["مراحل", "خطوات", "القبول", "اختبارات", "كشف طبي", "مقابلة", "امتحانات", "تنسيق"],
        "question": "What are the application and admission stages for DEPI?",
        "answer": "Stages: 1. Free online registration, 2. Document verification, 3. Email notification, 4. Admission tests (logic, English, digital, track-specific) + interview + medical check at Military Academy, 5. Orientation, 6. Document submission, 7. Class distribution.",
        "keywords": ["stages", "admissions", "tests", "medical check", "interview"]
    },
    {
        "category": "depi_tracks",
        "question_ar": "ما هي المسارات والتخصصات المتاحة في مبادرة الرواد الرقميون؟",
        "answer_ar": "تضم المبادرة 6 تخصصات رئيسية:\n1. الذكاء الاصطناعي وعلوم البيانات (AI & Data Science)\n2. الأمن السيبراني (Cybersecurity)\n3. تطوير البرمجيات وهندسة النظم (Software Development)\n4. البنية التحتية الرقمية والشبكات السحابية (Digital Infrastructure & Cloud)\n5. الفنون والوسائط الرقمية (Digital Arts & Design)\n6. تصميم الدوائر الإلكترونية والنظم المدمجة (Embedded Systems & VLSI)\n* ملاحظة: يُتاح للمتقدم اختيار مسار واحد فقط تحت تخصص واحد لضمان التركيز والتميز.",
        "keywords_ar": ["تخصصات", "مسارات", "تراك", "تراكات", "مجالات", "ذكاء اصطناعي", "امن سيبراني", "برمجيات", "شبكات", "فنون", "انظمة مدمجة"],
        "question": "What tracks and specializations are available in DEPI?",
        "answer": "Tracks include: 1. AI & Data Science, 2. Cybersecurity, 3. Software Development, 4. Digital Infrastructure & Cloud, 5. Digital Arts, 6. Embedded Systems & VLSI. Candidates select one track only.",
        "keywords": ["tracks", "specializations", "ai", "cybersecurity", "software", "cloud", "embedded"]
    },
    {
        "category": "depi_registration",
        "question_ar": "كيف أقوم بالتسجيل في مبادرة الرواد الرقميون وما هو الرابط الرسمي؟",
        "answer_ar": "التسجيل مجاني تماماً وبشكل إلكتروني عبر الرابط الرسمي المعتمد:\n🔗 https://www.digilians.gov.eg/login\n\nإرشادات التسجيل:\n- يُفضل استخدام جهاز كمبيوتر للتسجيل لضمان وضوح رفع الملفات.\n- لا يعتمد القبول على أسبقية التقديم بل على الكفاءة ونتائج الاختبارات.\n- يمكن تعديل البيانات والمستندات طوال فترة فتح باب التسجيل وقبل حجز موعد الامتحان.",
        "keywords_ar": ["تسجيل", "رابط", "موقع", "لينك", "تقديم", "ازاي اقدم", "طريقة التسجيل", "مجان"],
        "question": "How do I register for DEPI and what is the official portal link?",
        "answer": "Registration is completely free online at the official portal: https://www.digilians.gov.eg/login. Desktop/laptop is recommended. Selection is based on merit, not first-come first-served.",
        "keywords": ["registration", "apply", "portal", "link", "website", "sign up"]
    },
    {
        "category": "depi_study_system",
        "question_ar": "ما هو نظام الدراسة والإقامة واللغة في المبادرة؟",
        "answer_ar": "نظام الدراسة في مبادرة الرواد الرقميون:\n- تفرغ كامل وإقامة فندقية شاملة داخل الأكاديمية العسكرية بمصر الجديدة.\n- لغة الدراسة الرسمية هي الإنجليزية مع شرح وتوضيح بالعربية.\n- التدريب مكثف يومياً طوال الأسبوع مع إجازات دورية كل أسبوعين.\n- الحضور إلزامي بنسبة لا تقل عن 85% للتمكن من الاستمرار.\n- مدة البرامج: تتراوح من 4 أشهر (دبلوم احترافي مكثف) إلى سنتين (لبرامج الماجستير).\n- إشراف ومتابعة مستمرة من مرشدين ومدربين تقنيين دوليين.",
        "keywords_ar": ["نظام الدراسة", "اقامة", "مكان", "تفرغ", "مواعيد", "اجازات", "مدة", "حضور", "غياب", "لغة الدراسة"],
        "question": "What is the study and accommodation system in DEPI?",
        "answer": "Full-time intensive study with full accommodation at the Military Academy in Heliopolis. English is the official instruction language. Mandatory 85% attendance, bi-weekly leaves, program length 4 months to 2 years.",
        "keywords": ["study system", "accommodation", "full-time", "attendance", "duration", "language"]
    },
    {
        "category": "depi_exams_seb",
        "question_ar": "ما هي متطلبات الامتحانات وحل مشاكل متصفح SEB (Safe Exam Browser) والكاميرا؟",
        "answer_ar": "إرشادات هامة لامتحانات القبول وLMS:\n1. متصفح الامتحانات الآمن SEB: يتطلب نظام Windows 10 (إصدار 1803 فأحدث) أو Windows 11.\n2. تشغيل الامتحان: لا تفتح برنامج SEB يدوياً من قائمة البرامج، بل اضغط على زر 'Launch Safe Exam Browser' من داخل صفحة الامتحان بالبوابة.\n3. الكاميرا السوداء: تأكد من إغلاق كافة البرامج والتطبيقات التي تستخدم الكاميرا (مثل Zoom، Teams)، وامنح متصفحك صلاحية الوصول للكاميرا.\n4. بيانات الدخول: تظهر بيانات LMS (اسم المستخدم وكلمة المرور) في حسابك على البوابة بعد تحديد الموعد.\n5. في حال حدوث أي عطل، تواصل فوراً عبر: info@depi.gov.eg",
        "keywords_ar": ["seb", "امتحان", "امتحانات", "safe exam browser", "كاميرا", "lms", "مشكلة", "باسورد", "رابط الامتحان", "كاميرا سوداء"],
        "question": "What are the exam requirements and troubleshooting for Safe Exam Browser (SEB)?",
        "answer": "SEB requires Windows 10 (1803+) or Windows 11. Never launch SEB manually; always click 'Launch Safe Exam Browser' from the LMS exam page. For camera issues, close background apps using webcam. Support: info@depi.gov.eg.",
        "keywords": ["seb", "exam", "safe exam browser", "camera", "troubleshooting", "lms"]
    },
    {
        "category": "depi_career_opportunities",
        "question_ar": "ما هي فرص التوظيف والعمل بعد التخرج من مبادرة الرواد؟",
        "answer_ar": "توفر المبادرة دعماً وظيفياً شاملاً للمتفوقين والخريجين:\n- ترشيح مباشر لكبرى شركات التكنولوجيا والاتصالات المحلية والدولية.\n- تدريب متخصص على كتابة السيرة الذاتية (CV) واجتياز المقابلات الشخصية.\n- جلسات إرشاد وتوجيه مهني فردية ومتابعة مستمرة بعد التخرج.\n- فرص تدريب عملي (Internships) في الوزارات والمؤسسات الشريكة.\n- دعم وتمكين رواد الأعمال والعمل الحر (Freelancing).\n- ملتقيات توظيف دورية تنظمها وزارة الاتصالات لربط الخريجين بسوق العمل.",
        "keywords_ar": ["توظيف", "شغل", "فرص عمل", "وظائف", "بعد التخرج", "سوق العمل", "انترنشيب", "شركات", "مرتبات"],
        "question": "What career and employment opportunities are available after graduating from DEPI?",
        "answer": "Direct nominations to top tech firms, CV and interview preparation, individual career mentoring, internship placements, freelancing support, and dedicated job fairs organized by MCIT.",
        "keywords": ["careers", "jobs", "employment", "internships", "placement", "freelancing"]
    },
    {
        "category": "depi_certificates",
        "question_ar": "ما هي الشهادات والاعتمادات التي يحصل عليها خريج المبادرة؟",
        "answer_ar": "يحصل المتدرب على:\n1. شهادة تخرج معتمدة مشتركة من وزارة الاتصالات وتكنولوجيا المعلومات والأكاديمية العسكرية المصرية.\n2. شهادات مهنية دولية معتمدة لكل محور تخصصي يتم اجتيازه.\n3. شهادة درجة الماجستير من جامعة أجنبية مرموقة للملتحقين بمسارات الماجستير.\n* يشترط تسليم ومناقشة مشروع التخرج بنجاح للحصول على الشهادة النهائية.",
        "keywords_ar": ["شهادات", "شهادة", "معتمدة", "ماجستير", "اعتماد", "مشروع تخرج", "اكاديمية عسكرية"],
        "question": "What certifications and credentials do DEPI graduates receive?",
        "answer": "Graduates receive a joint accredited certificate from MCIT and the Egyptian Military Academy, international specialized credentials per track, and a master's degree certificate for enrolled master's programs.",
        "keywords": ["certificates", "accreditation", "credentials", "master degree", "diploma"]
    },
    {
        "category": "depi_contact_support",
        "question_ar": "كيف يمكنني التواصل مع الدعم الفني وخدمة عملاء مبادرة الرواد الرقميون؟",
        "answer_ar": "قنوات التواصل الرسمية والدعم الفني لمبادرة DEPI:\n- البريد الإلكتروني الرسمي: info@digilians.gov.eg\n- بريد الدعم الأكاديمي والامتحانات: info@depi.gov.eg\n- خدمة عملاء الواتساب الذكية: متوفرة عبر هذه المحادثة على مدار الساعة للرد الفوري على الاستفسارات.\n- بوابة الاستفسارات: https://www.digilians.gov.eg",
        "keywords_ar": ["تواصل", "دعم", "خدمة عملاء", "ايميل", "بريد", "رقم", "خط ساخن", "مساعدة"],
        "question": "How can I contact technical support and customer service for DEPI?",
        "answer": "Official support channels: General email info@digilians.gov.eg, Exam support info@depi.gov.eg, 24/7 WhatsApp AI Customer Service, and the portal at https://www.digilians.gov.eg.",
        "keywords": ["contact", "support", "help", "email", "hotline", "customer service"]
    },
    {
        "category": "depi_withdrawal_policy",
        "question_ar": "ما هي سياسة وقواعد الانسحاب من المبادرة؟",
        "answer_ar": "سياسة الانسحاب:\nنظراً لأن منحة مبادرة الرواد الرقميون مجانية وممولة بالكامل من الدولة ذات تكلفة عالية وتفرغ كامل، لا يجوز الانسحاب بعد بدء التدريب إلا في الظروف القهرية القصوى وبموافقة خطية من إدارة المبادرة، وفي حال الانسحاب دون عذر مقبول يتحمل الطالب التكاليف والالتزامات المترتبة وفقاً للإقرار الموقع.",
        "keywords_ar": ["انسحاب", "اعتذار", "الخروج", "غرامة", "تكاليف", "اقرار", "شروط الانسحاب"],
        "question": "What is the withdrawal and cancellation policy for DEPI?",
        "answer": "Because the scholarship is fully state-funded and full-time, withdrawal after training begins is permitted only under extreme force majeure with written management approval; otherwise, full reimbursement costs apply.",
        "keywords": ["withdrawal", "cancellation", "penalty", "policy", "costs"]
    },
    {
        "category": "depi_grants",
        "question_ar": """ما هي المنح والتمويل المتاح لطلاب مبادرة الرواد الرقميون؟""",
        "answer_ar": """مبادرة الرواد الرقميون (DEPI) ممولة بالكامل من الدولة.
- لا رسوم دراسية لجميع البرامج.
- بدل إقامة يومي شامل الوجبات.
- تغطية تكاليف النقل للطلاب من خارج القاهرة.
- جوائز مالية للمتفوقين.
- دعم شراء الأجهزة التقنية للطلاب المحتاجين.""",
        "keywords_ar": ["\u0645\u0646\u062d\u0629", "\u062a\u0645\u0648\u064a\u0644", "\u0631\u0633\u0648\u0645", "\u0625\u0642\u0627\u0645\u0629", "\u0628\u062f\u0644", "\u062c\u0648\u0627\u0626\u0632", "\u0623\u062c\u0647\u0632\u0629", "\u062a\u0645\u0648\u064a\u0644"],
        "question": "What grants and funding are available for DEPI students?",
        "answer": "DEPI is fully state-funded: no tuition fees, daily meal/boarding allowance, transport coverage for non-Cairo students, cash prizes for top performers, and device support for needy students.",
        "keywords": ["grants", "funding", "scholarship", "tuition", "allowance", "prizes"]
    },
    {
        "category": "depi_lms_platform",
        "question_ar": """ما هي المنصة التعليمية (LMS) المستخدمة في DEPI؟""",
        "answer_ar": """تستخدم مبادرة الرواد الرقميون منصة LMS متكاملة تقدم:
- المحاضرات والفيديوهات التعليمية
- الواجبات والاختبارات الإلكترونية
- نظام الحضور والإجازات
- التواصل بين الطلاب والمدربين
- لوحة التحكم الشخصية لكل طالب

الدعم الفني: info@depi.gov.eg""",
        "keywords_ar": ["LMS", "\u0627\u0644\u0645\u0646\u0635\u0629 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a\u0629", "\u0627\u0644\u0645\u062d\u0627\u0636\u0631\u0627\u062a", "\u0627\u0644\u0648\u0627\u062c\u0628\u0627\u062a", "\u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a", "\u0627\u0644\u062d\u0636\u0648\u0631", "\u0627\u0644\u0625\u062c\u0627\u0632\u0627\u062a"],
        "question": "What LMS platform does DEPI use for online learning?",
        "answer": "DEPI uses a comprehensive LMS featuring video lectures, e-assessments, attendance tracking, student-instructor communication, and personal dashboards. Support: info@depi.gov.eg",
        "keywords": ["LMS", "e-learning", "platform", "video", "assessment", "attendance"]
    },
    {
        "category": "depi_international_partnerships",
        "question_ar": """ما هي الشراكات الدولية لمبادرة الرواد الرقميون؟""",
        "answer_ar": """تتعاون مبادرة DEPI مع جامعات وشركات تقنية عالمية:
- جامعات في ألمانيا وبريطانيا وكندا
- شراكات مع مايكروسوفت وغوغل وأمازون
- برامج تبادل ثقافي وتدريب مشترك
- اعتمادات دولية للشهادات
- مشاريع بحثية مشتركة""",
        "keywords_ar": ["\u0634\u0631\u0627\u0643\u0627\u062a", "\u062f\u0648\u0644\u064a\u0629", "\u062c\u0627\u0645\u0639\u0627\u062a", "\u0634\u0631\u0643\u0627\u062a", "\u062a\u0642\u0646\u064a\u0629", "\u062a\u0628\u0627\u062f\u0644", "\u0627\u0639\u062a\u0645\u0627\u062f\u0627\u062a", "\u0628\u062d\u062b"],
        "question": "What international partnerships does DEPI have?",
        "answer": "DEPI partners with universities in Germany, UK, Canada and tech companies like Microsoft, Google, and Amazon for joint programs, certifications, and research.",
        "keywords": ["partnerships", "international", "universities", "Microsoft", "Google", "certifications"]
    },
    {
        "category": "depi_evaluation_criteria",
        "question_ar": """ما هي معايير تقييم الطلاب في مبادرة الرواد الرقميون؟""",
        "answer_ar": """يتم تقييم الطلاب وفقاً لمعايير متعددة:
- الاختبارات الإلكترونية: 30%
- المشاريع التطبيقية: 30%
- الحضور والمشاركة: 15%
- الامتحان النهائي: 25%

الحد الأدنى للنجاح: 60%
التقديرات: ممتاز (90+)، جيد جداً (80+)، جيد (70+)، مقبول (60+)""",
        "keywords_ar": ["\u062a\u0642\u064a\u064a\u0645", "\u0627\u0645\u062a\u062d\u0627\u0646\u0627\u062a", "\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a", "\u0645\u0634\u0627\u0631\u064a\u0639", "\u062d\u0636\u0648\u0631", "\u062a\u0642\u062f\u064a\u0631\u0627\u062a", "\u0646\u062c\u0627\u062d", "\u062f\u0631\u062c\u0627\u062a"],
        "question": "What are the student evaluation criteria in DEPI?",
        "answer": "Evaluation: E-tests 30%, projects 30%, attendance 15%, final exam 25%. Minimum passing: 60%. Grades: Excellent (90+), Very Good (80+), Good (70+), Pass (60+).",
        "keywords": ["evaluation", "grading", "exams", "projects", "attendance", "criteria"]
    },
    {
        "category": "depi_admission_appeal",
        "question_ar": "كيف يمكنني تقديم اعتراض أو الطعن في قرار القبول؟",
        "answer_ar": "إجراءات الاعتراض على قرارات القبول في مبادرة الرواد الرقميون:\n1. تقديم اعتراض رسمي عبر البوابة الإلكترونية خلال 5 أيام عمل من إعلان النتيجة.\n2. دفع رسوم الاعتراض (تُسترد في حال إلغاء القرار).\n3. مراجعة اللجنة العليا للاعتراضات.\n4. الإخطار بالنتيجة خلال 10 أيام عمل.\n5. في حال عدم الرضا عن النتيجة، يمكن التواصل مع مكتب أمين المظالم.",
        "keywords_ar": ["اعتراض", "طعن", "قرار", "قبول", "نتيجة", "التماس", "مراجعة", "أمين مظالم"],
        "question": "How can I appeal or contest an admission decision?",
        "answer": "Appeal process: 1. Submit formal appeal via portal within 5 business days of result announcement. 2. Pay appeal fee (refunded if decision overturned). 3. Higher Appeals Committee reviews. 4. Notified within 10 business days. 5. If unsatisfied, contact the Ombudsman office.",
        "keywords": ["appeal", "contest", "admission", "decision", "result", "ombudsman"]
    },
    {
        "category": "depi_admission_deferral",
        "question_ar": "هل يمكن تأجيل التسجيل أو إعادة تفعيل الطلب؟",
        "answer_ar": "سياسة التأجيل وإعادة التفعيل:\n- يمكن تأجيل التسجيل مرة واحدة لمدة تصل إلى فصل دراسي واحد بأسباب قهرية موثقة.\n- يجب تقديم طلب التأجيل عبر البوابة مع المستندات الداعمة.\n- لا يحق تأجيل التسجيل بعد استكمال الاختبارات.\n- إعادة التفعيل تتطلب إعادة تقديم الطلب ودفع أي رسوم مستحقة.",
        "keywords_ar": ["تأجيل", "تأخير", "إعادة تفعيل", "طلب", "أسباب قهرية", "موثقة"],
        "question": "Can I defer my registration or reactivate my application?",
        "answer": "Deferral allowed once for up to one semester with documented force majeure reasons. Submit via portal with supporting documents. Cannot defer after completing exams. Reactivation requires re-application and any outstanding fees.",
        "keywords": ["defer", "postpone", "reactivate", "force majeure", "reapply"]
    },
    {
        "category": "depi_exam_appeal",
        "question_ar": "كيف يمكنني الاعتراض على نتيجة الامتحان أو طلب مراجعتها؟",
        "answer_ar": "إجراءات مراجعة نتائج الامتحانات:\n1. تقديم طلب مراجعة خلال 7 أيام عمل من إعلان النتيجة.\n2. يتم مراجعة الإجابات مقارنة بمعايير التصحيح المعتمدة.\n3. لا تُعاد تصحيح الإجابات إلا في حال وجود خطأ واضح في التصحيح.\n4. تُرد رسوم المراجعة في حال تغيير النتيجة.\n5. التواصل عبر: exam.review@depi.gov.eg",
        "keywords_ar": ["مراجعة", "النتيجة", "نتيجة", "امتحان", "اعتراض", "تصحيح", "خطأ", "رسوم", "إجابات"],
        "question": "How can I contest an exam result or request a review?",
        "answer": "Review process: 1. Submit request within 7 business days of result. 2. Answers compared against approved grading criteria. 3. Re-grading only for clear grading errors. 4. Review fee refunded if grade changes. 5. Contact: exam.review@depi.gov.eg",
        "keywords": ["review", "grade", "exam", "contest", "re-grade", "fee"]
    },
    {
        "category": "depi_exam_incident",
        "question_ar": "ماذا أفعل في حالة حدوث طارئ أو حادث أثناء الامتحان؟",
        "answer_ar": "الإبلاغ عن الحوادث أثناء الامتحانات:\n- في حال حدوث عطل فني أو طارئ أثناء الامتحان: الضغط على زر المساعدة في البوصة أو التواصل مع المشرف فوراً.\n- الإبلاغ عبر: exam.incidents@depi.gov.eg\n- توثيق الحادث بالصور أو الفيديو إن أمكن.\n- سيتم النظر في الطلب خلال 48 ساعة عمل.\n- قد يتم جدولة إعادة للامتحان المتأثر.",
        "keywords_ar": ["طوارئ", "طارئ", "حادث", "امتحان", "عطل", "إبلاغ", "مساعدة", "مشرف", "جدولة", "إعادة"],
        "question": "What should I do in an emergency or incident during an exam?",
        "answer": "Report incidents: Press help button in the exam browser or contact supervisor immediately. Email: exam.incidents@depi.gov.eg. Document with photos/video if possible. Reviewed within 48 hours. Affected exam may be rescheduled.",
        "keywords": ["emergency", "incident", "exam", "report", "supervisor", "reschedule"]
    },
    {
        "category": "depi_exam_accommodation",
        "question_ar": "هل تتوفر تسهيلات خاصة للطلاب ذوي الاحتياجات الخاصة في الامتحانات؟",
        "answer_ar": "التسهيلات الخاصة للطلاب ذوي الاحتياجات الخاصة:\n- توفير وقت إضافي (25% إضافية).\n- توفير قاعة منفصلة ومرتبة.\n- توفير أدوات مساعدة (حاسوب، قارئ شاشة).\n- توفير مترجم لغة الإشارة عند الطلب.\n- يجب تقديم طلب مسبق مع تقرير طبي معتمد قبل 14 يوم من الامتحان.\n- التواصل: accommodations@depi.gov.eg",
        "keywords_ar": ["تسهيلات", "احتياجات خاصة", "إعاقة", "إضافي", "قاعة", "مترجم", "تقرير طبي"],
        "question": "Are there special accommodations for students with disabilities during exams?",
        "answer": "Accommodations include: 25% extra time, separate quiet room, assistive devices (computer, screen reader), sign language interpreter. Submit request 14 days before exam with medical report. Contact: accommodations@depi.gov.eg",
        "keywords": ["accommodation", "disability", "extra time", "assistive", "interpreter", "medical"]
    },
    {
        "category": "depi_training_feedback",
        "question_ar": "كيف يمكنني تقديم ملاحظات أو شكوى عن جودة التدريب؟",
        "answer_ar": "تقديم ملاحظات وشكاوى جودة التدريب:\n- استمارة التقييم بعد كل مسار تدريبي عبر البوصة.\n- تقديم شكوى جودة عبر: quality@depi.gov.eg\n- الاجتماعات التقييمية الدورية مع المرشدين.\n- مدة الاستجابة: 72 ساعة عمل.\n- يمكن طلب جلسة استشارية فردية مع فريق الجودة.",
        "keywords_ar": ["ملاحظات", "جودة", "تدريب", "شكوى", "تقييم", "مرشد", "استشارة", "استجابة"],
        "question": "How can I provide feedback or file a training quality complaint?",
        "answer": "Feedback channels: Post-track evaluation form via portal, quality emails at quality@depi.gov.eg, periodic review meetings with mentors. Response within 72 hours. Individual consultation available from quality team.",
        "keywords": ["feedback", "quality", "training", "complaint", "evaluation", "mentor"]
    },
    {
        "category": "depi_training_schedule",
        "question_ar": "كيف يتم التعامل مع تعارض المواعيد أو الغياب من التدريب؟",
        "answer_ar": "سياسة التعارض والغياب:\n- تعارض المواعيد: تقديم طلب مسبق عبر البوابة مع المستندات.\n- الغياب المبرر (مواعيد طبية، عائلية): تقديم إشعار قبل 48 ساعة مع تقرير طبي أو مستند رسمي.\n- الغياب غير المبرر: يُحتسب من نسبة الحضور الإلزامية (85%).\n- التغيب المتكرر يعرض الطالب للإيقاف مؤقتاً.",
        "keywords_ar": ["تعارض", "مواعيد", "غياب", "حضور", "إلزامي", "مبرر", "غير مبرر", "إيقاف"],
        "question": "How are schedule conflicts and training absences handled?",
        "answer": "Conflicts: submit advance request via portal. Justified absence (medical/family): notify 48 hours before with documentation. Unjustified absence counts toward mandatory 85% attendance. Repeated absence leads to temporary suspension.",
        "keywords": ["conflict", "schedule", "absence", "attendance", "justified", "suspension"]
    },
    {
        "category": "depi_platform_bug",
        "question_ar": "كيف أبلغ عن خلل فني أو خطأ في المنصة الإلكترونية؟",
        "answer_ar": "الإبلاغ عن الأخطاء التقنية:\n- الإبلاغ عبر زر 'بلغ عن خطأ' الموجود في كل صفحة من البوابة.\n- البريد التقني: support@digilians.gov.eg\n- وصف الخطأ بوضوح مع لقطات شاشة إن أمكن.\n- تحديد المتصفح ونظام التشغيل المستخدم.\n- الاستجابة خلال 24 ساعة عمل.\n- تتبع حالة البلاغ عبر رقم التتبع المرفق.",
        "keywords_ar": ["خطأ", "خلل", "عطل", "تقني", "بلاغ", "دعم", "سcreenshot", "متتبع", "حالة"],
        "question": "How do I report a technical bug or error in the online platform?",
        "answer": "Report bugs: Use 'Report Error' button on every page. Email: support@digilians.gov.eg. Describe clearly with screenshots if possible. Specify browser and OS. Response within 24 hours. Track status via reference number.",
        "keywords": ["bug", "error", "technical", "report", "support", "track", "screenshot"]
    },
    {
        "category": "depi_platform_login_issues",
        "question_ar": "لا أستطيع تسجيل الدخول أو رفع المستندات على المنصة، ماذا أفعل؟",
        "answer_ar": "حلول مشاكل تسجيل الدخول والرفع:\n- كلمة المرور المنسية: اضغط 'نسيت كلمة المرور' وأدخل البريد الإلكتروني المسجل.\n- انتهاء الجلسة: أعد تسجيل الدخول وتأكد من استقرار الإنترنت.\n- عدم قبول الرفع: تأكد من صيغة PDF وحجم الملف أقل من 2 ميجابايت.\n- حاول استخدام متصفح Chrome أو Firefox أحدث إصدار.\n- إذا استمرت المشكلة: contact@digilians.gov.eg",
        "keywords_ar": ["تسجيل دخول", "دخول", "رفع", "مستندات", "كلمة مرور", "PDF", "حجم", "Chrome", "Firefox", "مشكلة"],
        "question": "I can't log in or upload documents on the platform, what should I do?",
        "answer": "Login issues: Use 'Forgot Password' with registered email. Session expired: re-login with stable internet. Upload not accepted: ensure PDF format and under 2MB. Try latest Chrome or Firefox. Persistent issues: contact@digilians.gov.eg",
        "keywords": ["login", "upload", "password", "PDF", "Chrome", "Firefox", "troubleshoot"]
    }
]

def seed():
    # Build SQL statements
    sql_lines = []
    for f in faqs:
        cat = f["category"].replace("'", "''")
        qar = f["question_ar"].replace("'", "''")
        aar = f["answer_ar"].replace("'", "''")
        qen = f["question"].replace("'", "''")
        aen = f["answer"].replace("'", "''")
        kwar_arr = "ARRAY[" + ",".join([f"'{k.replace("'", "''")}'" for k in f["keywords_ar"]]) + "]::text[]"
        kwen_arr = "ARRAY[" + ",".join([f"'{k.replace("'", "''")}'" for k in f["keywords"]]) + "]::text[]"
        
        sql = f"""
INSERT INTO knowledge_base (category, question_ar, answer_ar, keywords_ar, question, answer, keywords, is_active)
SELECT '{cat}', '{qar}', '{aar}', {kwar_arr}, '{qen}', '{aen}', {kwen_arr}, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base WHERE question_ar = '{qar}'
);
"""
        sql_lines.append(sql)

    full_sql = "\n".join(sql_lines)
    
    # Run through docker exec cs-postgres
    cmd = ["docker", "exec", "-i", "cs-postgres", "psql", "-U", "postgres", "-d", "customerservice"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    out, err = proc.communicate(input=full_sql)
    print("STDOUT:", out)
    if err:
        print("STDERR:", err)
    print(f"Successfully seeded {len(faqs)} DEPI FAQ records!")

    # Bump KB cache version for server.js
    import os
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'infra', 'whatsapp', 'KB_CACHE_VERSION')
    current = 1
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as vf:
                current = int(vf.read().strip()) or 1
        except (ValueError, IOError):
            current = 1
    new_version = current + 1
    try:
        with open(version_file, 'w') as vf:
            vf.write(str(new_version))
    except IOError:
        pass
    print(f"KB cache version bumped: {current} -> {new_version}")

if __name__ == "__main__":
    seed()
