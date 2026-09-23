# -*- coding: utf-8 -*-
"""
Migration and Seeding script for NexaServe Unified Knowledge Base:
- مبادرة الرواد الرقميون (Digilians)
- مبادرة رواد مصر الرقمية (DEBI)
- COMMON
"""
import subprocess
import json
import sys

def run_psql(sql_commands):
    # Run through docker exec to cs-postgres
    cmd = [
        "docker", "exec", "-i", "cs-postgres",
        "psql", "-U", "postgres", "-d", "customerservice"
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    stdout, stderr = process.communicate(input=sql_commands)
    if process.returncode != 0:
        print("SQL Error:", stderr, file=sys.stderr)
        raise RuntimeError(f"psql exited with code {process.returncode}: {stderr}")
    return stdout

print("1. Running database schema alterations...")
schema_sql = """
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS program VARCHAR(20) NOT NULL DEFAULT 'DIGILIANS';
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS source_attribution TEXT;
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS chk_kb_program;
ALTER TABLE knowledge_base ADD CONSTRAINT chk_kb_program CHECK (program IN ('DIGILIANS', 'DEBI', 'COMMON'));
CREATE INDEX IF NOT EXISTS idx_kb_program_category ON knowledge_base(program, category, is_active);
"""
print(run_psql(schema_sql))

print("2. Updating existing rows to DIGILIANS...")
update_existing_sql = """
UPDATE knowledge_base
SET program = 'DIGILIANS',
    source_attribution = 'مبادرة الرواد الرقميون (Digilians)'
WHERE program IS NULL OR program = 'DIGILIANS';
"""
print(run_psql(update_existing_sql))

# Now prepare comprehensive DEBI and COMMON entries
debi_and_common_entries = [
    # --- DEBI: OVERVIEW ---
    {
        "program": "DEBI",
        "category": "debi_overview",
        "question_ar": "ما هي مبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "مبادرة رواد مصر الرقمية (DEBI - Digital Egypt Builders Initiative) هي منحة دراسية كاملة أطلقتها وزارة الاتصالات وتكنولوجيا المعلومات المصرية. تهدف المنحة إلى تمكين جيل متميز من خريجي كليات الهندسة والحاسبات في مصر من الحصول على درجة الماجستير في العلوم المهنية والتكنولوجيا المتقدمة من كبرى الجامعات الدولية المرموقة، بالتوازي مع تدريب عملي مع كبرى شركات التكنولوجيا العالمية وتطوير المهارات القيادية واللغوية.",
        "keywords_ar": ["رواد مصر الرقمية", "debi", "بناة مصر الرقمية", "ماجستير", "منحة", "وزارة الاتصالات", "تعريف", "اهداف"],
        "question": "What is the Digital Egypt Builders Initiative (DEBI)?",
        "answer": "The Digital Egypt Builders Initiative (DEBI) is a fully-funded scholarship launched by Egypt's Ministry of Communications and Information Technology (MCIT). It grants top Egyptian engineering and computer science graduates a professional Master's degree from prestigious international universities, combined with industry training from leading tech companies and leadership development.",
        "keywords": ["debi", "digital egypt builders", "overview", "masters", "mcit", "scholarship"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: ADMISSION & CONDITIONS ---
    {
        "program": "DEBI",
        "category": "debi_conditions",
        "question_ar": "ما هي شروط التقديم والقبول في مبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "شروط التقديم والقبول في مبادرة رواد مصر الرقمية (DEBI):\n1. الجنسية: مصري / مصرية فقط.\n2. المؤهل الدراسي: خريجو كليات الهندسة (أقسام: حاسبات، اتصالات، إلكترونيات، قوى/ميكاترونكس) أو كليات الحاسبات والمعلومات / الذكاء الاصطناعي.\n3. التقدير التراكمي: ألا يقل التقدير العام عن «جيد جداً» (Very Good) أو معدل تراكمي (GPA) لا يقل عن 3.0 من 4.0 (أو ما يعادله).\n4. السن: ألا يزيد سن المتقدم عن 26 عاماً (أو 27 عاماً لبعض التخصصات المحددة عند تاريخ التقديم).\n5. اللغة الإنجليزية: إتقان تام للغة الإنجليزية (الحصول على TOEFL iBT بحد أدنى 80 درجة أو IELTS أكاديمي 6.5 كحد أدنى أو اجتياز اختبارات المنحة اللغوية المؤهلة للقبول بالجامعات الأجنبية الشريكة).\n6. الموقف التجنيدي للذكور: أداء الخدمة العسكرية أو الإعفاء النهائي منها.\n7. التفرغ: التفرغ الكامل والإقامة الداخلية خلال فترة الدراسة.",
        "keywords_ar": ["شروط", "شروط التقديم", "القبول", "debi", "رواد مصر الرقمية", "تقدير", "جيد جدا", "gpa", "السن", "العمر", "تفرغ", "مؤهل"],
        "question": "What are the admission requirements for the Digital Egypt Builders Initiative (DEBI)?",
        "answer": "Admission requirements for DEBI:\n1. Egyptian citizenship only.\n2. Degree: Bachelor's in Engineering (Computers, Electronics, Communications, Mechatronics) or Computers & Artificial Intelligence / Informatics.\n3. Minimum Cumulative Grade: 'Very Good' (GPA 3.0/4.0 or above).\n4. Maximum Age: Up to 26 years old (27 for select specializations).\n5. English Proficiency: Minimum TOEFL iBT 80 or Academic IELTS 6.5+.\n6. Military status for males: Completed or exempted.\n7. Commitment: 100% full-time commitment and residency throughout the program.",
        "keywords": ["debi", "admission requirements", "eligibility", "gpa", "engineering", "toefl", "ielts", "conditions"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: DOCUMENTS ---
    {
        "program": "DEBI",
        "category": "debi_documents",
        "question_ar": "ما هي الأوراق والمستندات المطلوبة للتقديم في DEBI؟",
        "answer_ar": "المستندات الرسمية المطلوبة للتقديم في مبادرة رواد مصر الرقمية (DEBI):\n1. شهادة التخرج الرسمية موضح بها التقدير العام (ألا يقل عن جيد جداً).\n2. بيان درجات السنوات الدراسية بالكامل (Transcript).\n3. بطاقة الرقم القومي المصرية سارية المفعول.\n4. شهادة الموقف من التجنيد للذكور (أدى الخدمة أو إعفاء نهائي).\n5. شهادة إتقان اللغة الإنجليزية (TOEFL iBT أو Academic IELTS) إن وجدت.\n6. السيرة الذاتية المحدثة (CV) باللغة الإنجليزية.\n7. خطابات توصية أكاديمية (Academic Recommendation Letters).\n* ملاحظة: تُرفع المستندات إلكترونياً عبر بوابة debi.gov.eg بصيغة PDF.",
        "keywords_ar": ["اوراق", "مستندات", "مطلوبة", "debi", "رواد مصر الرقمية", "شهادة تخرج", "بيان درجات", "transcript", "توصية"],
        "question": "What documents are required to apply for DEBI?",
        "answer": "Required application documents for DEBI:\n1. Official graduation certificate showing minimum 'Very Good' grade.\n2. Complete university transcript for all academic years.\n3. Valid Egyptian National ID card.\n4. Military service certificate (completed or exempted for males).\n5. English proficiency test score (TOEFL iBT or Academic IELTS) if available.\n6. Updated English CV.\n7. Academic recommendation letters.\nAll uploaded as PDF on the official debi.gov.eg portal.",
        "keywords": ["debi", "documents", "required papers", "transcript", "graduation certificate", "recommendation"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: TRACKS ---
    {
        "program": "DEBI",
        "category": "debi_tracks",
        "question_ar": "ما هي المسارات والتخصصات المتاحة في مبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "تتضمن مبادرة رواد مصر الرقمية (DEBI) المسارات التكنولوجية المتقدمة التالية للحصول على الماجستير:\n1. الذكاء الاصطناعي وعلوم البيانات (Artificial Intelligence & Data Science)\n2. الأمن السيبراني (Cybersecurity)\n3. الروبوتات والأتمتة الذكية (Robotics & Automation)\n4. هندسة البرمجيات (Software Engineering)\n5. الفنون الرقمية والتكنولوجيا المالية (Digital Arts & FinTech)\n* يحصل الدارس في كل مسار على ماجستير علوم مهني معتمد دولياً.",
        "keywords_ar": ["مسارات", "تخصصات", "تراكات", "debi", "رواد مصر الرقمية", "ذكاء اصطناعي", "امن سيبراني", "روبوتات", "برمجيات"],
        "question": "What tracks and master's specializations are available in DEBI?",
        "answer": "DEBI offers prestigious professional Master's degree tracks in:\n1. Artificial Intelligence & Data Science\n2. Cybersecurity\n3. Robotics & Automation\n4. Software Engineering\n5. Digital Arts & FinTech\nGraduates earn a globally accredited Master of Science degree in their chosen track.",
        "keywords": ["debi", "tracks", "specializations", "master", "ai", "cybersecurity", "robotics", "software"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: PARTNER UNIVERSITIES & DEGREE ---
    {
        "program": "DEBI",
        "category": "debi_universities",
        "question_ar": "ما هي الجامعات الدولية الشريكة المانحة لشهادة الماجستير في DEBI؟",
        "answer_ar": "تتعاون مبادرة رواد مصر الرقمية (DEBI) مع كبرى الجامعات الكندية والدولية المرموقة لمنح درجة الماجستير للطلاب، ومن أبرزها:\n- جامعة أوتاوا الكندية (University of Ottawa - Canada)\n- جامعة كوينز الكندية (Queen's University - Canada)\nبالإضافة إلى نخبة من أفضل الجامعات والمؤسسات الأكاديمية العالمية. الشهادة الممنوحة هي درجة ماجستير رسمية ومعتمدة دولياً ومحلياً من المجلس الأعلى للجامعات.",
        "keywords_ar": ["جامعات", "جامعة", "اوتاوا", "كوينز", "كندا", "شهادة ماجستير", "معتمدة", "debi", "رواد مصر الرقمية", "شركاء"],
        "question": "Which international universities partner with DEBI to grant the Master's degree?",
        "answer": "DEBI partners with top-tier international and Canadian universities to grant the Master's degree, notably the University of Ottawa (Canada) and Queen's University (Canada), alongside other world-ranked academic institutions. Degrees are internationally and locally accredited by Egypt's Supreme Council of Universities.",
        "keywords": ["debi", "universities", "ottawa", "queens", "canada", "partners", "master degree"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: INDUSTRY & SOFT SKILLS PARTNERS ---
    {
        "program": "DEBI",
        "category": "debi_training",
        "question_ar": "من هم شركاء التدريب التقني والمهارات القيادية في مبادرة DEBI؟",
        "answer_ar": "تتضمن مبادرة DEBI تدريباً شاملاً مع كبرى المؤسسات العالمية:\n1. التدريب التقني الاحترافي: شركات أمازون ويب سيرفيسز (AWS)، سيسكو (Cisco)، آي بي إم (IBM)، مايكروسوفت (Microsoft)، وفيموير (VMware).\n2. المهارات القيادية والشخصية: ديل كارنيجي العالمية (Dale Carnegie) لبناء مهارات التفاوض، القيادة، والعمل الجماعي.\n3. إتقان اللغة الإنجليزية: معهد بيرلتز العالمي (Berlitz) للوصول إلى أعلى مستويات الطلاقة اللغوية.",
        "keywords_ar": ["شركاء", "تدريب", "ديل كارنيجي", "بيرلتز", "سيسكو", "مايكروسوفت", "aws", "ibm", "debi", "رواد مصر الرقمية"],
        "question": "Who are the technology and leadership training partners in DEBI?",
        "answer": "DEBI incorporates world-class industry training partners:\n1. Technology: AWS, Cisco, IBM, Microsoft, and VMware for official vendor certifications.\n2. Leadership & Soft Skills: Dale Carnegie Global for leadership, negotiation, and communication.\n3. Language: Berlitz for advanced professional English fluency.",
        "keywords": ["debi", "training partners", "cisco", "aws", "microsoft", "dale carnegie", "berlitz"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: BENEFITS & SCHOLARSHIP COVERAGE ---
    {
        "program": "DEBI",
        "category": "debi_benefits",
        "question_ar": "ما هي مزايا ومنح مبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "تشمل مزايا منحة DEBI:\n1. تمويل كامل وتغطية بنسبة 100% لمصروفات الماجستير من الجامعة الأجنبية.\n2. شهادات مهنية دولية معتمدة من كبرى شركات التكنولوجيا.\n3. مكافأة شهرية للمتدربين طوال فترة المنحة.\n4. جهاز حاسب آلي محمول (Laptop) حديث ومعدات تقنية مخصصة لكل دارس.\n5. إقامة فندقية كاملة تشمل الإعاشة والوجبات.\n6. فرص توظيف متميزة وتواصل مع كبرى الشركات الإقليمية والدولية بعد التخرج.",
        "keywords_ar": ["مزايا", "منحة", "مكافأة", "اقامة", "لابتوب", "تمويل", "debi", "رواد مصر الرقمية", "مميزات"],
        "question": "What are the benefits and coverage of the DEBI scholarship?",
        "answer": "DEBI scholarship benefits include:\n1. 100% fully covered international Master's degree tuition.\n2. International vendor certifications from leading tech companies.\n3. Monthly living allowance/stipend throughout the program.\n4. High-end modern laptop and tech equipment provided.\n5. Full residential accommodation, meals, and medical coverage.\n6. Exceptional career opportunities with top multinational tech employers.",
        "keywords": ["debi", "benefits", "stipend", "laptop", "free", "scholarship", "accommodation"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- DEBI: OFFICIAL PORTAL & REGISTRATION ---
    {
        "program": "DEBI",
        "category": "debi_registration",
        "question_ar": "ما هو الرابط الرسمي وكيفية التقديم في مبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "يتم التقديم في مبادرة رواد مصر الرقمية (DEBI) إلكترونياً وبشكل مجاني عبر الموقع الرسمي المخصص للمبادرة:\n🔗 https://debi.gov.eg\nيتم فتح باب التقديم لدفعات محددة يعلن عنها عبر الموقع الرسمي، ويقوم المتقدم بإنشاء حساب، استيفاء البيانات، ورفع المستندات الرسمية بصيغة PDF.",
        "keywords_ar": ["رابط", "موقع", "تقديم", "تسجيل", "بوابة", "لينك", "debi", "رواد مصر الرقمية", "debi.gov.eg"],
        "question": "What is the official website and application portal for DEBI?",
        "answer": "Applications for DEBI are submitted exclusively online through the official portal:\n🔗 https://debi.gov.eg\nAdmissions open in specific rounds announced on the official portal, where applicants create an account and upload required documents in PDF format.",
        "keywords": ["debi", "website", "portal", "register", "apply", "debi.gov.eg", "link"],
        "source_attribution": "مبادرة رواد مصر الرقمية (DEBI)"
    },
    # --- COMMON: COMPARISON BETWEEN DIGILIANS AND DEBI ---
    {
        "program": "COMMON",
        "category": "comparison",
        "question_ar": "ما الفرق بين مبادرة الرواد الرقميون (Digilians) ومبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "*المقارنة بين مبادرة الرواد الرقميون (Digilians) ومبادرة رواد مصر الرقمية (DEBI):* 🏛️\n\n1. *الدرجة العلمية والهدف:*\n- *مبادرة الرواد الرقميون (Digilians):* تركز على بناء المهارات التقنية التطبيقية والقيادية والتأهيل لسوق العمل، وتقدم دبلومات مهنية معتمدة من وزارة الاتصالات والأكاديمية العسكرية المصرية ومسار ماجستير للمتميزين.\n- *مبادرة رواد مصر الرقمية (DEBI):* تركز على منح درجة ماجستير علوم مهنية (Master of Science) معتمدة دولياً ومباشرة من جامعات كندية وأجنبية مرموقة (مثل University of Ottawa).\n\n2. *الفئة المستهدفة والمؤهل:*\n- *Digilians:* تقبل خريجي الكليات والمعاهد العليا والمتوسطة بمختلف التخصصات، بالإضافة لطلاب السنة النهائية (السن من 18 حتى 32 عاماً).\n- *DEBI:* مخصصة حصرياً لخريجي كليات الهندسة وكليات الحاسبات والذكاء الاصطناعي، بتقدير لا يقل عن «جيد جداً» (GPA 3.0+)، وألا يزيد السن عن 26-27 عاماً.\n\n3. *متطلبات اللغة الإنجليزية:*\n- *Digilians:* مستوى أساسي إلى متوسط (B1 كحد أدنى).\n- *DEBI:* مستوى متقدم مع اشتراط TOEFL iBT (80+) أو IELTS (6.5+) للقبول بالجامعات الأجنبية.\n\n4. *البوابة الرسمية:*\n- *Digilians:* https://www.digilians.gov.eg\n- *DEBI:* https://debi.gov.eg",
        "keywords_ar": ["فرق", "الفرق", "مقارنة", "مقارنه", "بين", "digilians", "debi", "الرواد الرقميون", "رواد مصر الرقمية", "ما الفرق"],
        "question": "What is the difference between Digilians and DEBI?",
        "answer": "*Comparison between Digital Pioneers Initiative (Digilians) and Digital Egypt Builders Initiative (DEBI):* 🏛️\n\n1. *Objective & Degree:*\n- *Digilians:* Focuses on practical workforce technology enablement and leadership skills, granting joint certifications from MCIT and the Military Academy, with pathways to diplomas and master's.\n- *DEBI:* Focuses exclusively on a fully-funded international Master of Science degree directly from prestigious global universities (e.g. University of Ottawa).\n\n2. *Target Audience & Eligibility:*\n- *Digilians:* Open to graduates of universities/institutes across diverse majors and final-year students (Age: 18 to 32 years).\n- *DEBI:* Exclusively for graduates of Faculties of Engineering and Computers & Artificial Intelligence, with minimum grade 'Very Good' (GPA 3.0+), and age up to 26-27.\n\n3. *English Requirements:*\n- *Digilians:* Basic to intermediate English proficiency (B1+ minimum).\n- *DEBI:* Advanced proficiency (TOEFL iBT 80+ or Academic IELTS 6.5+) required for university admission.\n\n4. *Official Portals:*\n- *Digilians:* https://www.digilians.gov.eg\n- *DEBI:* https://debi.gov.eg",
        "keywords": ["difference", "compare", "comparison", "digilians", "debi", "versus", "vs", "which initiative"],
        "source_attribution": "وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)"
    },
    # --- COMMON: AMBIGUITY RESOLUTION ENTRY ---
    {
        "program": "COMMON",
        "category": "disambiguation",
        "question_ar": "هل تقصد مبادرة الرواد الرقميون (Digilians) أم مبادرة رواد مصر الرقمية (DEBI)؟",
        "answer_ar": "يرجى تحديد المبادرة المعنية لاستعراض الشروط الدقيقة:\n1. *مبادرة الرواد الرقميون (Digilians):* للشباب وخريجي الجامعات وطلاب السنة النهائية (18-32 سنة).\n2. *مبادرة رواد مصر الرقمية (DEBI):* لخريجي كليات الهندسة والحاسبات بتقدير جيد جداً للحصول على الماجستير الدولي.",
        "keywords_ar": ["توضيح", "اي مبادرة", "تقصد", "digilians", "debi", "مبادرة"],
        "question": "Do you mean Digital Pioneers Initiative (Digilians) or Digital Egypt Builders Initiative (DEBI)?",
        "answer": "Please clarify which initiative you are referring to for exact requirements:\n1. *Digital Pioneers Initiative (Digilians):* For university graduates & final-year students (age 18-32).\n2. *Digital Egypt Builders Initiative (DEBI):* For Engineering and Computer Science graduates with Very Good+ grade pursuing an international Master's degree.",
        "keywords": ["clarify", "which initiative", "digilians", "debi", "disambiguate"],
        "source_attribution": "وزارة الاتصالات وتكنولوجيا المعلومات (MCIT)"
    }
]

print("3. Inserting DEBI and COMMON entries...")
# First delete any existing DEBI or comparison entries to ensure idempotency
cleanup_sql = "DELETE FROM knowledge_base WHERE program IN ('DEBI', 'COMMON');"
run_psql(cleanup_sql)

insert_statements = []
for entry in debi_and_common_entries:
    prog = entry["program"]
    cat = entry["category"]
    q_ar = entry["question_ar"].replace("'", "''")
    a_ar = entry["answer_ar"].replace("'", "''")
    clean_kws_ar = [k.replace("'", "''") for k in entry["keywords_ar"]]
    kw_ar_arr = "ARRAY[" + ",".join([f"'{k}'" for k in clean_kws_ar]) + "]::text[]"
    q_en = entry["question"].replace("'", "''")
    a_en = entry["answer"].replace("'", "''")
    clean_kws_en = [k.replace("'", "''") for k in entry["keywords"]]
    kw_en_arr = "ARRAY[" + ",".join([f"'{k}'" for k in clean_kws_en]) + "]::text[]"
    src = entry["source_attribution"].replace("'", "''")
    
    stmt = f"""
    INSERT INTO knowledge_base (program, category, question_ar, answer_ar, keywords_ar, question, answer, keywords, source_attribution, is_active)
    VALUES ('{prog}', '{cat}', '{q_ar}', '{a_ar}', {kw_ar_arr}, '{q_en}', '{a_en}', {kw_en_arr}, '{src}', TRUE);
    """
    insert_statements.append(stmt)

sql_batch = "\n".join(insert_statements)
run_psql(sql_batch)

# Verify counts per program
count_sql = "SELECT program, count(*) FROM knowledge_base GROUP BY program ORDER BY program;"
print("4. Verification of knowledge_base entries by program:")
print(run_psql(count_sql))
print("Knowledge base migration completed successfully!")
