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

if __name__ == "__main__":
    seed()
