"""Builds the curated DEPI knowledge pack (Round 5) from the official catalogs and FAQ facts.

The pack is the authoritative, customer-facing layer of the RAG knowledge base:
  * core_*    program facts rewritten as real customer questions (AR + EN), taken from
              depi.gov.eg FAQs/guidance pages already stored in the knowledge base;
  * catalog_* every Round 5 track and job profile with its full study plan, parsed from
              FAQs/Catal/*.md so the curriculum always matches the published catalog.

Usage:  python scripts/kb/depi_knowledge_pack.py            -> writes infra/knowledge/depi_knowledge_pack_r5.json
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "FAQs" / "Catal" / "DEPI-CATALOG-2025-R5-V1.md"
INDUSTRY = ROOT / "FAQs" / "Catal" / "DEPI-Industry-CATALOG-2025-R5-V1.md"
OUT = ROOT / "infra" / "knowledge" / "depi_knowledge_pack_r5.json"

PACK = "DEPI Knowledge Pack R5"
FAQ_URL = "https://depi.gov.eg/content/faqs"
ABOUT_URL = "https://depi.gov.eg/content/aboutdepi"
GUIDANCE_URL = "https://depi.gov.eg/StaticContent/Guidance"
CONTACT_URL = "https://depi.gov.eg/StaticContent/ContactUs"
CATALOG_SRC = "DEPI Technical Catalog - Round 5 (Jul 2026 - Dec 2026)"
INDUSTRY_SRC = "DEPI Industry Technical Catalog - Round 5"

# --- Core program facts ---------------------------------------------------------------------
# Every statement below comes from the official depi.gov.eg FAQ, About, Guidance and Contact pages.
CORE = [
    dict(key="about", category="core_overview", url=ABOUT_URL,
         q_ar="ما هي مبادرة رواد مصر الرقمية (DEPI)؟", q_en="What is the Digital Egypt Pioneers Initiative (DEPI)?",
         a_ar="مبادرة رواد مصر الرقمية (DEPI) هي منحة تدريبية مجانية أطلقتها وزارة الاتصالات وتكنولوجيا المعلومات عام 2023 في إطار رؤية مصر 2030، "
              "بهدف إعداد جيل من المتخصصين والمبدعين في التقنيات الحديثة وتمكينهم من المنافسة في سوق العمل المحلي والإقليمي والعالمي. "
              "تُنفَّذ المبادرة بالتعاون مع كبرى شركات التكنولوجيا العالمية والمحلية، وتقدم تدريباً تقنياً متخصصاً إلى جانب اللغة الإنجليزية والمهارات الشخصية ومهارات العمل الحر. "
              "وتنطلق حالياً الدورة الخامسة (يوليو - ديسمبر 2026) بسبعة مسارات تكنولوجية، بالإضافة إلى برنامج DEPI Industry للمهنيين.",
         a_en="The Digital Egypt Pioneers Initiative (DEPI) is a free training scholarship launched in 2023 by the Ministry of Communications and Information Technology (MCIT) "
              "as part of Egypt Vision 2030. It prepares a generation of specialists in modern technologies so they can compete in the local, regional and global job market. "
              "DEPI is delivered with leading global and local technology companies and combines specialised technical training with English, soft skills and freelancing skills. "
              "Round 5 runs from July to December 2026 with seven technology tracks, plus the DEPI Industry programme for professionals.",
         kw_ar=["رواد", "مصر", "الرقمية", "المبادرة", "مبادرة", "نبذة", "تعريف", "عن"], kw_en=["depi", "about", "initiative", "overview", "what"]),
    dict(key="vision", category="core_overview", url=ABOUT_URL,
         q_ar="ما هي رؤية وأهداف مبادرة رواد مصر الرقمية؟", q_en="What are the vision and goals of DEPI?",
         a_ar="رؤية المبادرة هي تحقيق الريادة المحلية والإقليمية في قطاع الاتصالات وتكنولوجيا المعلومات من خلال بناء قوة عاملة مصرية ماهرة ومبتكرة تقود مسيرة التحول الرقمي الشامل. "
              "وتهدف إلى تنمية المهارات الرقمية للشباب بما يواكب أحدث المتغيرات التكنولوجية، من خلال تدريب تطبيقي وورش عمل تقدمها شركات التكنولوجيا الشريكة.",
         a_en="DEPI's vision is local and regional leadership in ICT by building a skilled, innovative Egyptian workforce that leads comprehensive digital transformation. "
              "Its goal is to develop young people's digital skills in line with the latest technology trends through applied training and workshops delivered by partner technology companies.",
         kw_ar=["رؤية", "الرؤية", "اهداف", "الأهداف", "هدف", "رسالة"], kw_en=["vision", "goals", "mission", "objectives"]),
    dict(key="eligibility", category="core_eligibility", url=FAQ_URL,
         q_ar="ما هي شروط الالتحاق بمبادرة رواد مصر الرقمية؟", q_en="What are the eligibility requirements for DEPI?",
         a_ar="شروط التقديم ومعايير القبول:\n"
              "1. أن يكون المتقدم مصري الجنسية ومقيماً في جمهورية مصر العربية.\n"
              "2. أن يكون من طلاب أو خريجي الكليات والمعاهد العليا المصرية.\n"
              "3. اجتياز اختبار اللغة الإنجليزية بمستوى لا يقل عن المستوى الرابع، وبعض المسارات تتطلب أيضاً اجتياز اختبار تأهيل تقني.\n"
              "4. للذكور: إنهاء فترة التجنيد أو الإعفاء منها أو تأجيلها حتى يناير 2027.\n"
              "5. الموافقة على إقرار الالتزام الكامل بشروط ونظام الدراسة.\n"
              "6. توفير بريد إلكتروني ورقم هاتف محمول عليه تطبيق واتساب.\n"
              "ملاحظة: محافظة التدريب هي المحافظة التي تحضر فيها الجلسات الحضورية ولا يمكن تعديلها بعد التسجيل.",
         a_en="Applicants must:\n1. Be Egyptian and reside in Egypt.\n2. Be a student or graduate of an Egyptian faculty or higher institute.\n"
              "3. Pass the English test at level 4 or above; some tracks also require a technical qualification test.\n"
              "4. Males: have completed, been exempted from, or postponed military service until January 2027.\n"
              "5. Accept the full-commitment declaration for the study system.\n6. Provide an email address and a mobile number with WhatsApp.\n"
              "Note: the training governorate is where in-person sessions are attended and cannot be changed.",
         kw_ar=["شروط", "شرط", "الالتحاق", "التقديم", "القبول", "معايير", "اهلية", "المطلوب", "مؤهل", "التقدم"],
         kw_en=["eligibility", "requirements", "conditions", "criteria", "eligible", "apply", "admission"]),
    dict(key="who", category="core_eligibility", url=FAQ_URL,
         q_ar="من يحق له التقديم في المبادرة؟ هل يمكن للطلاب التقديم أم الخريجين فقط؟", q_en="Who can apply to DEPI? Students or graduates only?",
         a_ar="يحق التقديم لطلاب وخريجي الكليات والمعاهد العليا بالجامعات المصرية، وفقاً لمتطلبات كل مسار. ويمكن التقديم من أي مدينة في الجمهورية، "
              "مع ضرورة استيفاء جميع شروط القبول. أما برنامج DEPI Industry فيستهدف الخريجين والمهنيين ذوي الخبرة.",
         a_en="Students and graduates of Egyptian universities and higher institutes can apply, according to each track's requirements, from any city in Egypt, "
              "provided they meet all admission requirements. DEPI Industry targets graduates and experienced professionals.",
         kw_ar=["طلاب", "طالب", "خريج", "خريجين", "الخريجين", "يحق", "مين", "المؤهل", "للتدريب"], kw_en=["students", "graduates", "who"]),
    dict(key="documents", category="core_documents", url=FAQ_URL,
         q_ar="ما هي المستندات المطلوبة للتقديم في المبادرة؟", q_en="What documents are required to apply?",
         a_ar="المستندات المطلوبة:\n• للخريجين: صورة شهادة التخرج، صورة شهادة الخدمة العسكرية (للذكور)، صورة بطاقة الرقم القومي.\n"
              "• للطلاب: بيان درجات آخر سنة دراسية أو شهادة قيد أو صورة كارنيه الكلية (لحين استخراج بيان الدرجات)، وصورة بطاقة الرقم القومي.",
         a_en="Required documents:\n• Graduates: copy of the graduation certificate, military service certificate (males), and national ID.\n"
              "• Students: latest academic transcript, enrolment certificate or a copy of the college ID (until a transcript is issued), and national ID.",
         kw_ar=["المستندات", "مستندات", "الاوراق", "اوراق", "الأوراق", "شهادة", "بطاقة", "كارنيه", "رفع"], kw_en=["documents", "papers", "upload", "certificate", "id"]),
    dict(key="admission", category="core_admission", url=FAQ_URL,
         q_ar="كيف تتم عملية القبول في المبادرة؟", q_en="How does the DEPI admission process work?",
         a_ar="يتم القبول بأولوية التسجيل واجتياز اختبارات القبول، مع مراعاة تناسب البرنامج التدريبي ورغبة المتقدم مع خلفيته الدراسية والعملية. "
              "يسجل المتقدم بياناته ويرفع المستندات المطلوبة، ثم يتم التحقق من استيفاء الشروط، وبعدها يُدعى المستوفون للشروط لاستكمال مراحل التقديم بأداء اختبارات القبول "
              "(اختبار اللغة الإنجليزية، واختبار تقني لبعض المسارات).",
         a_en="Admission is based on registration priority and passing the admission tests, matching each programme to the applicant's wishes and academic/professional background. "
              "Applicants register and upload documents; eligibility is verified; eligible applicants are then invited to complete the process by taking the admission tests "
              "(English, plus a technical test for some tracks).",
         kw_ar=["القبول", "قبول", "منهجية", "مراحل", "اولوية", "اختبارات"], kw_en=["admission", "process", "selection", "priority", "steps"]),
    dict(key="cost", category="core_cost", url=FAQ_URL,
         q_ar="هل المنحة مجانية؟ هل يوجد أي مصاريف للتسجيل أو الالتحاق؟", q_en="Is DEPI free? Are there any registration fees?",
         a_ar="نعم، المنحة مجانية بالكامل ولا توجد أي مصاريف للتسجيل أو الالتحاق، ويتم توفير أدوات التدريب للمتدربين أثناء التدريب. "
              "ولا يمكن لمن لا تنطبق عليه الشروط الالتحاق مقابل سداد التكلفة، إذ يجب أن يستوفي كل ملتحق شروط التقديم كاملة.",
         a_en="Yes. The scholarship is completely free with no registration or enrolment fees, and training tools are provided during the training. "
              "Applicants who do not meet the requirements cannot join by paying; every participant must meet all requirements.",
         kw_ar=["مجانية", "مجاني", "مصاريف", "رسوم", "تكلفة", "فلوس", "سداد", "بفلوس", "ادفع"], kw_en=["free", "fees", "cost", "price", "pay", "payment"]),
    dict(key="duration", category="core_duration", url=FAQ_URL,
         q_ar="ما هي مدة الدراسة في المبادرة وما هو نظام التدريب؟", q_en="How long is the DEPI training and how is it structured?",
         a_ar="مدة المنحة ستة أشهر (الدورة الخامسة: يوليو - ديسمبر 2026):\n"
              "• 4 أشهر للمحاور الفنية والمهارات المطلوبة للعمل الحر (مهارات العمل الحر، المهارات الحياتية، واللغة الإنجليزية) بإجمالي نحو 200 ساعة، بواقع 3 ساعات لكل محاضرة.\n"
              "• شهران للإرشاد المهني (Coaching) للعمل الحر.\n"
              "ويجمع التدريب بين جلسات حضورية في مركز التدريب بالمحافظة وجلسات عن بعد.",
         a_en="The scholarship lasts six months (Round 5: July - December 2026):\n"
              "• 4 months of technical content plus freelancing skills, soft skills and English - about 200 hours, 3 hours per session.\n"
              "• 2 months of freelancing career coaching.\nTraining combines in-person sessions at the governorate training centre with remote sessions.",
         kw_ar=["مدة", "المدة", "شهور", "اشهر", "ساعات", "نظام", "الدراسة", "مواعيد", "امتى", "الدورة", "الخامسة"],
         kw_en=["duration", "long", "months", "hours", "schedule", "structure", "round"]),
    dict(key="online", category="core_duration", url=FAQ_URL,
         q_ar="هل التدريب أونلاين أم حضوري؟", q_en="Is the training online or in person?",
         a_ar="التدريب مدمج: يتضمن جلسات حضورية في مراكز التدريب بالمحافظات وجلسات عن بعد (أونلاين). ويشترط حضور 65% على الأقل من الجلسات الحضورية و65% من الجلسات عن بعد.",
         a_en="Training is blended: in-person sessions at governorate training centres plus remote (online) sessions. At least 65% attendance is required for both in-person and remote sessions.",
         kw_ar=["اونلاين", "أونلاين", "حضوري", "حضور", "بعد", "اون", "لاين"], kw_en=["online", "remote", "in-person", "offline", "onsite"]),
    dict(key="attendance", category="core_attendance", url=FAQ_URL,
         q_ar="ما هي نسبة الحضور المطلوبة لإتمام التدريب؟", q_en="What attendance rate is required?",
         a_ar="يشترط على المتدرب حضور 65% على الأقل من الجلسات الحضورية و65% من الجلسات عن بعد، في جميع محاور الدراسة: التقني (Technical) واللغة الإنجليزية والمهارات الشخصية ومهارات العمل الحر.",
         a_en="Trainees must attend at least 65% of in-person sessions and 65% of remote sessions across all study components: Technical, English, Soft skills and Freelancing skills.",
         kw_ar=["نسبة", "الحضور", "حضور", "غياب", "الغياب"], kw_en=["attendance", "absence", "percentage"]),
    dict(key="exams_period", category="core_attendance", url=FAQ_URL,
         q_ar="هل يتعارض التدريب مع امتحانات الكلية؟", q_en="Does the training pause during university exams?",
         a_ar="يتوقف التدريب للطلاب لمدة شهر واحد خلال فترة الامتحانات النهائية بالكلية، ولا يتوقف التدريب للمتقدمين من فئة الخريجين.",
         a_en="Training pauses for students for one month during final university exams; it does not pause for graduates.",
         kw_ar=["امتحانات", "الكلية", "الجامعة", "الدراسة", "يتعارض", "توقف"], kw_en=["university", "exams", "college", "pause", "conflict"]),
    dict(key="certificate", category="core_certificate", url=FAQ_URL,
         q_ar="هل يحصل المتدرب على شهادة بعد إتمام التدريب؟ وما شروطها؟", q_en="Will I get a certificate, and what are the requirements?",
         a_ar="نعم، يُمنح المتدرب شهادة إتمام التدريب وفقاً لعدد الساعات التدريبية لمساره، معتمدة من وزارة الاتصالات وتكنولوجيا المعلومات، وذلك بعد:\n"
              "• انتهاء التدريب واستيفاء كافة متطلبات المسار.\n• تنفيذ المشروع المطلوب (Capstone Project).\n"
              "• الحصول بنجاح على 3 مهام (Gigs) على الأقل من إحدى منصات العمل الحر.",
         a_en="Yes. Trainees receive an MCIT-accredited completion certificate based on the training hours of their track, after:\n"
              "• completing the training and all track requirements;\n• delivering the required capstone project;\n"
              "• successfully completing at least 3 gigs on a freelancing platform.",
         kw_ar=["شهادة", "الشهادة", "شهادات", "معتمدة", "التخرج", "جيجز", "مهام"], kw_en=["certificate", "certification", "accredited", "graduation", "gigs"]),
    dict(key="locations", category="core_locations", url=FAQ_URL,
         q_ar="أين يتم التدريب؟ هل التدريب في القاهرة فقط؟", q_en="Where does training take place? Only in Cairo?",
         a_ar="لا، يتم توفير مركز تدريب في كل محافظة تابع لها الملتحقون بالمنحة لتنفيذ التدريبات الحضورية طبقاً للخطة الزمنية لكل مجموعة. "
              "ويُعلن عن مراكز التدريب بعد انتهاء فترة التسجيل وفقاً لكثافة المسجلين في كل محافظة. ويمكن التقديم من أي مدينة في الجمهورية، "
              "مع العلم أن محافظة التدريب المختارة عند التسجيل غير قابلة للتعديل.",
         a_en="No. A training centre is provided in each governorate where participants are enrolled, following each group's schedule. "
              "Centres are announced after registration closes based on applicant density. You can apply from any city, but the training governorate chosen at registration cannot be changed.",
         kw_ar=["مكان", "اماكن", "أماكن", "القاهرة", "المحافظة", "محافظة", "المحافظات", "مركز", "مراكز", "فين", "السكن"],
         kw_en=["where", "location", "cairo", "governorate", "centre", "center", "city"]),
    dict(key="register", category="core_registration", url=GUIDANCE_URL,
         q_ar="كيف أسجل في المبادرة وما هي خطوات التسجيل؟", q_en="How do I register for DEPI?",
         a_ar="خطوات التسجيل:\n1. أنشئ حساباً على البوابة الرسمية https://depi.gov.eg وسجّل بياناتك وارفع المستندات المطلوبة.\n"
              "2. اختر مساراً وظيفياً (Job Profile) واحداً فقط، وتأكد من صحة كافة البيانات قبل الحفظ.\n"
              "3. تأكد من اكتمال التسجيل بظهور صفحة المستخدم ورقم التسجيل.\n"
              "4. انتظر رابط الامتحان على بريدك الإلكتروني وفي صفحة المستخدم.\n"
              "تنبيه: الامتحان مراقَب ومدته 45 دقيقة ولا يمكن إعادته.",
         a_en="Registration steps:\n1. Create an account at https://depi.gov.eg, enter your data and upload the required documents.\n"
              "2. Choose only one job profile and double-check all data before saving.\n3. Make sure registration is complete: your user page and registration number appear.\n"
              "4. Wait for the exam link by email and on your user page.\nNote: the exam is proctored, lasts 45 minutes and cannot be retaken.",
         kw_ar=["تسجيل", "التسجيل", "اسجل", "أسجل", "خطوات", "اقدم", "أقدم", "حساب", "رابط", "الموقع"], kw_en=["register", "registration", "sign", "steps", "apply", "portal"]),
    dict(key="register_confirm", category="core_registration", url=FAQ_URL,
         q_ar="كيف أتأكد أن التسجيل تم بنجاح؟ وكيف أعرف قبولي؟", q_en="How do I know my registration succeeded and whether I was accepted?",
         a_ar="يمكنك متابعة حالة استمارة البيانات من خلال حسابك الشخصي على الموقع، وستصلك رسالة على البريد الإلكتروني تؤكد إتمام التسجيل. "
              "ولمعرفة القبول تابع موقفك على حسابك الشخصي وأهم الأخبار على الموقع، بالإضافة إلى بريدك الإلكتروني بعد إغلاق فترة التسجيل.",
         a_en="Track your application status from your personal account on the website; you will also receive a confirmation email. "
              "For acceptance, follow your status on your account, the news on the website and your email after registration closes.",
         kw_ar=["تاكد", "تأكد", "نجاح", "قبولي", "موقف", "حالة", "النتيجة", "اعرف", "اتقبلت"], kw_en=["status", "accepted", "confirmation", "result", "success"]),
    dict(key="exam", category="core_exams", url=GUIDANCE_URL,
         q_ar="ما هي اختبارات القبول وما تعليمات الامتحان؟", q_en="What are the admission tests and exam rules?",
         a_ar="اختبارات القبول هي اختبار اللغة الإنجليزية (المستوى الرابع كحد أدنى)، واختبار تأهيل تقني لبعض المسارات كما هو موضح في الكتالوج. "
              "يصلك رابط الامتحان على بريدك الإلكتروني وفي صفحة المستخدم بعد إتمام التسجيل. الامتحان مراقَب ومدته 45 دقيقة فقط، ولا يمكن إعادته، "
              "ويُؤدّى عبر متصفح الامتحانات الآمن (Safe Exam Browser).",
         a_en="The admission tests are the English test (level 4 minimum) and, for some tracks, a technical qualification test as described in the catalog. "
              "The exam link is sent by email and shown on your user page after registration. The exam is proctored, lasts 45 minutes, cannot be retaken and runs in Safe Exam Browser.",
         kw_ar=["امتحان", "الامتحان", "اختبار", "الاختبار", "اختبارات", "انجليزي", "الانجليزية", "تقني", "مدة"], kw_en=["exam", "test", "english", "technical", "seb"]),
    dict(key="military", category="core_eligibility", url=FAQ_URL,
         q_ar="ما هو شرط التجنيد للذكور؟", q_en="What is the military service requirement for males?",
         a_ar="يجب أن يكون المتقدم من الذكور قد أنهى فترة التجنيد، أو معفى منها، أو مؤجلاً تجنيده حتى شهر يناير 2027، ويرفع الخريجون صورة شهادة الخدمة العسكرية ضمن المستندات.",
         a_en="Male applicants must have completed military service, be exempt, or have it postponed until January 2027; graduates upload their military service certificate.",
         kw_ar=["التجنيد", "تجنيد", "الجيش", "جيش", "العسكرية", "مؤجل", "تأجيل", "اعفاء"], kw_en=["military", "army", "conscription", "service"]),
    dict(key="other_scholarship", category="core_eligibility", url=FAQ_URL,
         q_ar="هل يمكنني التقديم إذا كنت ملتحقاً بمنحة أخرى؟", q_en="Can I apply if I am enrolled in another scholarship?",
         a_ar="لا يُفضَّل ذلك، لأن التدريب يتطلب التركيز والالتزام نظراً لتعدد أنشطته (تقني، لغة إنجليزية، مهارات، عمل حر).",
         a_en="It is not recommended, because the training requires focus and commitment across its many activities (technical, English, skills and freelancing).",
         kw_ar=["منحة", "اخرى", "أخرى", "منحتين", "ملتحق"], kw_en=["another", "scholarship", "other", "two"]),
    dict(key="job_profile", category="core_overview", url=FAQ_URL,
         q_ar="ما المقصود بالمسار الوظيفي (Job Profile)؟", q_en="What is a job profile in DEPI?",
         a_ar="المسار الوظيفي (Job Profile) هو مجموعة متطلبات وظيفية بأدوار محددة تخدم أهداف الهيكل التنظيمي داخل أي مؤسسة. "
              "كل مسار تكنولوجي في DEPI يضم عدة مسارات وظيفية، ولكل منها خطة دراسية تقنية تنتهي بمشروع تطبيقي، ويختار المتقدم مساراً وظيفياً واحداً فقط عند التسجيل.",
         a_en="A job profile is a set of job requirements with defined roles serving an organisation's structure. Each DEPI technology track contains several job profiles, "
              "each with a technical study plan ending in a capstone project; applicants choose exactly one job profile at registration.",
         kw_ar=["المسار", "الوظيفي", "بروفايل", "جوب", "تخصص", "اختار"], kw_en=["job", "profile", "choose"]),
    dict(key="contact", category="core_contact", url=CONTACT_URL,
         q_ar="كيف أتواصل مع فريق المبادرة؟ ما هي أرقام ووسائل التواصل؟", q_en="How can I contact DEPI support?",
         a_ar="وسائل التواصل الرسمية:\n• الخط الساخن: 15388 أو ‎+20 2 21293441 يومياً من 9 صباحاً حتى 5 مساءً طوال أيام الأسبوع.\n"
              "• البريد الإلكتروني: info@depi.gov.eg (الوسيلة الأساسية، ويتم الرد خلال 24 ساعة، ويمكن إعادة الإرسال في حال التأخر).\n"
              "• العنوان: القرية الذكية - الكيلو 28 طريق القاهرة/الإسكندرية الصحراوي - الجيزة. الصندوق البريدي 12577.\n• الموقع الرسمي: https://depi.gov.eg",
         a_en="Official contact channels:\n• Hotline: 15388 or +20 2 21293441, daily 9 am - 5 pm, all week.\n"
              "• Email: info@depi.gov.eg (primary channel, replies within 24 hours; resend if delayed).\n"
              "• Address: Smart Village, KM 28 Cairo-Alexandria Desert Road, Giza. P.O. Box 12577.\n• Website: https://depi.gov.eg",
         kw_ar=["تواصل", "التواصل", "رقم", "ارقام", "أرقام", "تليفون", "الخط", "الساخن", "ايميل", "البريد", "العنوان", "الدعم"],
         kw_en=["contact", "phone", "hotline", "email", "address", "support"]),
    dict(key="industry", category="core_industry", url=FAQ_URL,
         q_ar="ما هو برنامج DEPI Industry (مسار الصناعة)؟", q_en="What is DEPI Industry?",
         a_ar="DEPI Industry (مسار الصناعة) مسار سريع ومتخصص للمهنيين والخريجين ذوي الخبرة، يربط العاملين في القطاعات المهنية (كالتعليم والقانون والطب والبرمجة والمالية) "
              "بأحدث التقنيات في تخصصاتهم عبر التدريب العملي والإرشاد المهني ومشروعات تطبيقية بالشراكة مع شركات رائدة. "
              "مدته أربعة أشهر بحد أقصى، ويشمل المحتوى التقني ومهارات سوق العمل الحر، ولا يتضمن محتوى اللغة الإنجليزية.\n"
              "المسارات المتاحة في الدورة الخامسة:\n1. Applied AI Agents for Education and Teaching Professional\n2. Applied AI Agents for Legal Professional\n"
              "3. AI Software Professional\n4. AI Healthcare Professional\n5. Advanced Marketing Automation with AI Professional\n6. Oracle Fusion Financial Consultant",
         a_en="DEPI Industry is a fast, specialised track for experienced professionals and graduates. It connects professionals (education, law, healthcare, software, finance) "
              "with the latest technologies in their field through hands-on training, mentoring and applied projects with leading companies. It lasts up to four months and "
              "covers technical content plus freelancing/market skills, without English.\nRound 5 profiles:\n1. Applied AI Agents for Education and Teaching Professional\n"
              "2. Applied AI Agents for Legal Professional\n3. AI Software Professional\n4. AI Healthcare Professional\n5. Advanced Marketing Automation with AI Professional\n"
              "6. Oracle Fusion Financial Consultant",
         kw_ar=["الصناعة", "صناعة", "اندستري", "انداستري", "المهنيين", "خبرة", "industry"], kw_en=["industry", "professional", "professionals", "experienced"]),
    dict(key="industry_diff", category="core_industry", url=FAQ_URL,
         q_ar="ما الفرق بين برنامج DEPI الأساسي وبرنامج DEPI Industry؟", q_en="What is the difference between the main DEPI programme and DEPI Industry?",
         a_ar="البرنامج الأساسي مدته ستة أشهر ويستهدف الطلاب والخريجين، ويركز على بناء المهارات التقنية مع اللغة الإنجليزية والمهارات الشخصية والعمل الحر عبر سبعة مسارات تكنولوجية. "
              "أما DEPI Industry فمدته أربعة أشهر بحد أقصى ويستهدف المهنيين ذوي الخبرة، ويضيف بُعداً عملياً أكبر بالتركيز على التطبيقات الصناعية المتخصصة، "
              "وإشراك الشركات وخبراء الصناعة في التدريب، وحالات استخدام ومشروعات واقعية، ولا يتضمن محتوى اللغة الإنجليزية.",
         a_en="The main programme lasts six months for students and graduates and builds technical skills plus English, soft skills and freelancing across seven technology tracks. "
              "DEPI Industry lasts up to four months for experienced professionals and is more applied: sector-specific use cases, industry experts and companies in the training, "
              "and real projects, without English content.",
         kw_ar=["الفرق", "فرق", "الاساسي", "الأساسي", "التقليدية", "الصناعة"], kw_en=["difference", "main", "industry", "compare"]),
    dict(key="skills", category="catalog_skills", url=CATALOG_SRC,
         q_ar="ما هو محتوى المهارات الشخصية والعمل الحر وريادة الأعمال واللغة الإنجليزية في المبادرة؟",
         q_en="What do the soft skills, freelancing, entrepreneurship and English components cover?",
         a_ar="إلى جانب التدريب التقني، يدرس المتدربون:\n"
              "• المهارات الشخصية: التخطيط المهني، العلامة الشخصية وبناء العلاقات، التواصل والذكاء العاطفي، كتابة السيرة الذاتية ومهارات المقابلات، مهارات العرض، والإرشاد للتوظيف.\n"
              "• مهارات العمل الحر: التخطيط للعمل الحر، بناء معرض الأعمال (Portfolio)، منصات العمل الحر، التسعير وكتابة العروض، التفاوض، إنشاء الملف المهني، والإرشاد للحصول على المهام (Gigs).\n"
              "• ريادة الأعمال: أساسيات ريادة الأعمال، التفكير التصميمي، نموذج العمل التجاري (Business Model Canvas)، التسويق والتخطيط المالي للشركات الناشئة، إدارة الفريق، ومهارات العرض للمستثمرين.\n"
              "• اللغة الإنجليزية للعمل الحر: التعامل مع العملاء، كتابة العروض والتواجد على المنصات، والتواصل المهني.",
         a_en="Besides technical training, trainees study:\n• Personal skills: career planning, personal branding & networking, communication & emotional intelligence, CV writing & interviews, presentation skills, employment coaching.\n"
              "• Freelancing: planning, portfolio building, freelancing platforms, budgeting/pricing/proposals, negotiation, freelance profile kick-start, and gig coaching.\n"
              "• Entrepreneurship: fundamentals, design thinking, Business Model Canvas, startup marketing and financial planning, team management, pitching.\n"
              "• English for freelancers: client handling, proposals and platform presence, professional communication.",
         kw_ar=["مهارات", "المهارات", "سوفت", "العمل", "الحر", "فريلانس", "ريادة", "الانجليزي", "الانجليزية", "انجليزي"],
         kw_en=["soft", "skills", "freelancing", "freelance", "entrepreneurship", "english"]),
]

# --- Technology tracks ----------------------------------------------------------------------
TRACKS = {
    "SOFTWARE DEVELOPMENT TRACK": ("software", "مسار تطوير البرمجيات", "Software Development",
        "يقدم دورات في تطوير الويب (الواجهات الأمامية والخلفية)، وتطوير تطبيقات الموبايل، وDevOps، واختبار البرمجيات.",
        ["برمجة", "البرمجيات", "سوفتوير", "تطوير", "مبرمج"], ["software", "development", "programming", "developer"]),
    "DIGITAL MARKETING & ARTS TRACK": ("marketing", "مسار التسويق الرقمي والفنون الرقمية", "Digital Marketing & Arts",
        "يعلّمك صناعة المحتوى البصري والفني باستخدام الذكاء الاصطناعي والموشن جرافيك والمونتاج، وتصميم واجهات وتجربة المستخدم، واستراتيجيات التسويق الرقمي لبناء علامتك المهنية.",
        ["تسويق", "التسويق", "ماركتنج", "فنون", "ديجيتال", "تصميم", "جرافيك"], ["marketing", "digital", "arts", "design", "creative"]),
    "AI & DATA SCIENCE TRACK": ("ai", "مسار الذكاء الاصطناعي وعلوم البيانات", "AI & Data Science",
        "يركز على تطبيق علوم البيانات وتعلم الآلة والتعلم العميق ومعالجة اللغات الطبيعية والذكاء الاصطناعي التوليدي لحل مشكلات واقعية.",
        ["ذكاء", "الذكاء", "الاصطناعي", "علوم", "البيانات", "داتا", "ساينس", "تعلم", "الالة"], ["ai", "artificial", "intelligence", "data", "science", "machine", "learning"]),
    "DATA ANALYTICS TRACK": ("analytics", "مسار تحليل البيانات", "Data Analytics",
        "يهدف إلى استخراج رؤى مفيدة من البيانات لدعم اتخاذ القرار باستخدام أدوات مثل Python وSQL وPower BI وTableau.",
        ["تحليل", "البيانات", "داتا", "انالسيس", "اناليست", "محلل"], ["data", "analytics", "analysis", "analyst", "power", "bi"]),
    "INFRASTRUCTURE & SECURITY TRACK": ("security", "مسار البنية التحتية والأمن السيبراني", "Infrastructure & Security",
        "يؤهل المتدربين لحماية البيانات والأنظمة من الهجمات الإلكترونية، ويشمل الحوكمة وإدارة المخاطر، ومعيار ISO 27001، وأمن الحوسبة السحابية، والاستجابة للحوادث، واختبار الاختراق.",
        ["امن", "الأمن", "الامن", "سيبراني", "السيبراني", "سايبر", "سيكيوريتي", "البنية", "التحتية", "انفرا", "شبكات"], ["security", "cyber", "cybersecurity", "infrastructure", "infra", "network"]),
    "Management & ERP TRACK": ("erp", "مسار الإدارة وأنظمة تخطيط موارد المؤسسات (ERP)", "Management & ERP",
        "يدرس أساليب إدارة موارد الشركات بكفاءة وأتمتة العمليات باستخدام أنظمة SAP S/4HANA وOdoo، بالإضافة إلى إدارة المشروعات من Google.",
        ["ادارة", "الإدارة", "الادارة", "موارد", "اي", "ار", "بي", "ساب", "اودو", "مشروعات"], ["erp", "management", "sap", "odoo", "business", "project"]),
    "Digital Game Creation TRACK": ("games", "مسار صناعة الألعاب الرقمية", "Digital Game Creation",
        "مسار إنتاجي يؤهل المتدربين لمجال تصميم وتطوير الألعاب الاحترافي، ويجمع بين أطر تصميم الألعاب والتطبيق العملي باستخدام أدوات مثل Blender وUnity.",
        ["العاب", "الألعاب", "الالعاب", "جيمز", "جيم", "لعبة", "يونتي"], ["game", "games", "gaming", "unity", "blender"]),
}

# heading -> (track key or "industry", Arabic name, Arabic summary, extra AR keywords, extra EN keywords)
PROFILES = {
    "DevOps Engineer": ("software", "مهندس DevOps",
        "يتولى تشغيل البنية التحتية لتقنية المعلومات بسلاسة، وبناء أدوات التطوير والنشر الآلي، وأتمتة العمليات ومراقبة الأنظمة باستخدام Docker وKubernetes وJenkins وTerraform والسحابة.",
        ["ديف", "اوبس", "ديفوبس"], ["devops", "docker", "kubernetes", "jenkins", "terraform", "ansible", "cloud"]),
    "React Frontend Web Developer": ("software", "مطور واجهات ويب باستخدام React",
        "يتقن أساسيات الويب (HTML وCSS وJavaScript وTypeScript) ويتخصص في بناء تطبيقات React، مع مقدمة في Node.js وNestJS وNext.js وDocker، وينتهي بمشروع ويب متكامل.",
        ["رياكت", "ريأكت", "فرونت", "فرونت اند", "واجهات", "ويب"], ["react", "frontend", "front-end", "web", "javascript", "nextjs", "node"]),
    "Low-Code/No-Code Application Developer": ("software", "مطور تطبيقات Low-Code/No-Code",
        "يحوّل احتياجات الأعمال سريعاً إلى حلول رقمية عاملة دون الاعتماد الكبير على البرمجة التقليدية: تطبيقات وبوابات ولوحات تحكم وأتمتة وتكاملات، مع مهارات التعامل مع العملاء.",
        ["لو كود", "نو كود", "بدون برمجة"], ["low-code", "no-code", "lowcode", "nocode", "automation"]),
    "Full Stack .Net Web Developer": ("software", "مطور ويب Full Stack باستخدام .NET",
        "يبني تطبيقات ويب متكاملة قائمة على البيانات باستخدام C# و.NET Core (Web API وMVC) وSQL Server، مع واجهات HTML5 وJavaScript وCSS3.",
        ["دوت نت", "فول ستاك", "فل ستاك", "سي شارب"], [".net", "dotnet", "net", "c#", "csharp", "fullstack", "full-stack", "sql"]),
    "Go Blockchain Developer": ("software", "مطور Blockchain بلغة Go",
        "يؤهل لتطوير أنظمة خلفية موثوقة وقابلة للتوسع بلغة Go، مع أساسيات الواجهات وReact، وأساسيات وتطوير تقنية البلوك تشين.",
        ["بلوك تشين", "بلوكتشين", "جو"], ["go", "golang", "blockchain", "backend"]),
    "Cross Platform Mobile App Developer": ("software", "مطور تطبيقات موبايل متعددة المنصات",
        "يصمم ويطور تطبيقات موبايل تعمل على Android وiOS باستخدام Dart وFlutter وFirebase، مع أساسيات UX/UI ونشر التطبيقات على المتاجر.",
        ["موبايل", "تطبيقات", "فلاتر", "اندرويد", "ايفون"], ["mobile", "flutter", "dart", "android", "ios", "firebase", "app"]),
    "Software Tester": ("software", "مختبر البرمجيات (Software Tester)",
        "يضمن مطابقة البرمجيات لمعايير الجودة عبر أساسيات الاختبار وفق ISTQB، وأساليب الاختبار الثابت، وأدوات Postman وSelenium وJira، مع أساسيات Java.",
        ["تستر", "تستينج", "اختبار البرمجيات", "جودة"], ["testing", "tester", "qa", "quality", "istqb", "selenium", "postman"]),
    "Digital Marketing Specialist": ("marketing", "أخصائي التسويق الرقمي",
        "يبني ويدير حملات تسويقية حديثة: تسويق المحتوى، منصات التواصل الاجتماعي، تحسين محركات البحث SEO، التسويق بالبريد، إعلانات Google، قياس الأداء، والتسويق بالعمولة وتوزيع الميزانية.",
        ["ديجيتال ماركتنج", "سوشيال ميديا", "اعلانات"], ["marketing", "seo", "ads", "social", "media", "content"]),
    "UI & UX Web Designer": ("marketing", "مصمم واجهات وتجربة المستخدم UI/UX",
        "يصمم منتجات رقمية سهلة الاستخدام وجذابة بصرياً تلبي احتياجات المستخدم، باستخدام Photoshop وIllustrator وAdobe XD وFigma.",
        ["يو اي", "يو اكس", "واجهات", "فيجما", "تجربة المستخدم"], ["ui", "ux", "ui/ux", "figma", "design", "designer"]),
    "Motion Graphics Designer": ("marketing", "مصمم موشن جرافيك",
        "ينتج محتوى بصرياً متحركاً للإعلام الرقمي والحملات التسويقية باستخدام Illustrator وAfter Effects وElement 3D وPremiere Pro وAudition وCharacter Animator.",
        ["موشن", "جرافيك", "انيميشن", "رسوم متحركة"], ["motion", "graphics", "animation", "after", "effects"]),
    "Media Production Influencer": ("marketing", "إنتاج المحتوى الإعلامي لصناع المحتوى",
        "يؤهل لتخطيط وإنتاج ومونتاج محتوى الفيديو والوسائط المتعددة لاقتصاد صناع المحتوى باستخدام Photoshop وPremiere Pro وAfter Effects وAudition، مع مهارات التأثير.",
        ["انفلونسر", "مونتاج", "صناعة المحتوى", "فيديو", "ميديا"], ["media", "production", "influencer", "video", "editing", "content"]),
    "AI in Digital Arts": ("marketing", "الذكاء الاصطناعي في الفنون الرقمية",
        "يصنع محتوى بصرياً ومتعدد الوسائط عالي التأثير بأدوات الذكاء الاصطناعي: توليد الصور والفن الرقمي، إنتاج الفيديو السينمائي، دمج الموشن والصوت، وبناء معرض الأعمال.",
        ["فن رقمي", "توليد الصور", "ذكاء اصطناعي فني"], ["ai", "art", "arts", "digital", "image", "generation", "creative"]),
    "Agentic AI and Generative AI System Developer": ("ai", "مطور أنظمة الذكاء الاصطناعي التوليدي والوكلاء الأذكياء (Agentic AI)",
        "يتعلم أسس الذكاء الاصطناعي التوليدي والنماذج اللغوية الكبيرة (LLMs) والمحولات، وتكامل الـ APIs، والهندسة المتقدمة للأوامر، وأنظمة RAG والذاكرة، والوكلاء الأذكياء والأنظمة متعددة الوكلاء، ونشر ومراقبة التطبيقات.",
        ["جنريتف", "توليدي", "ايجنت", "وكلاء", "ال ال ام"], ["agentic", "generative", "genai", "llm", "rag", "agents", "ai"]),
    "Microsoft Machine Learning Engineer": ("ai", "مهندس تعلم الآلة من Microsoft",
        "يحوّل البيانات الخام إلى نماذج قابلة للتطبيق والتوسع باستخدام تقنيات Microsoft: Python، الإحصاء والجبر الخطي، تعلم الآلة والتعلم العميق، NLP والرؤية الحاسوبية، وAzure AI وMLOps.",
        ["ماشين ليرننج", "تعلم الالة", "مايكروسوفت", "ازور"], ["machine", "learning", "ml", "microsoft", "azure", "deep", "mlops"]),
    "Data Scientist": ("ai", "عالم بيانات (Data Scientist) - برنامج مصمم من IBM",
        "برنامج مصمم من IBM يؤهل لاستخراج قيمة من البيانات: منهجية علوم البيانات، Python وSQL، تحليل وتصور البيانات، تعلم الآلة، وأدوات MLOps.",
        ["داتا ساينتست", "داتا ساينس", "علوم البيانات", "عالم بيانات"], ["data", "scientist", "science", "ibm", "python", "sql"]),
    "Microsoft Data Engineer": ("ai", "مهندس بيانات من Microsoft",
        "يبني ويدير أنظمة بيانات حديثة تدعم التحليلات والذكاء الاصطناعي: البرمجة وقواعد البيانات SQL، خطوط البيانات، معالجة البيانات الضخمة، وشهادة Azure Data Engineer.",
        ["داتا انجنير", "هندسة البيانات", "مهندس بيانات", "بيج داتا"], ["data", "engineer", "engineering", "azure", "pipelines", "big"]),
    "AWS Machine Learning Engineer": ("ai", "مهندس تعلم الآلة على AWS",
        "يصمم ويبني وينشر حلول تعلم الآلة والذكاء الاصطناعي التوليدي على السحابة عبر برامج AWS Academy: هندسة البيانات، أسس تعلم الآلة، NLP، والذكاء الاصطناعي التوليدي.",
        ["امازون", "ايه دبليو اس"], ["aws", "amazon", "machine", "learning", "cloud", "ml"]),
    "AI Automation Workflow with N8N Professional": ("ai", "أتمتة سير العمل بالذكاء الاصطناعي باستخدام n8n",
        "يصمم سير عمل رقمي ذكي يجمع الذكاء الاصطناعي وأتمتة الأعمال باستخدام n8n: الوكلاء الأذكياء، الأتمتة المتقدمة، الربط مع Slack والويب والبريد، والأمان والحوكمة.",
        ["اتمتة", "أتمتة", "ان ايت ان", "اوتوميشن"], ["n8n", "automation", "workflow", "agents", "ai"]),
    "Professional Data Analyst": ("analytics", "محلل بيانات محترف (مستوى متوسط)",
        "برنامج متوسط المستوى لتحليل البيانات بعمق ودمج مصادر متعددة: Python، SQL المتقدم، Tableau، وPower BI (Power Query وDAX والنمذجة ولوحات التحكم)، وحوكمة البيانات.",
        ["محلل بيانات", "داتا اناليست", "باور بي اي", "تابلو"], ["data", "analyst", "power", "bi", "tableau", "sql", "python", "professional"]),
    "Junior Data Analyst": ("analytics", "محلل بيانات مبتدئ",
        "برنامج للمبتدئين لجمع البيانات وتنظيفها وتنظيمها واستخراج رؤى بسيطة: Power BI بالتفصيل، Tableau، ومقدمة في SQL وPython وحوكمة البيانات.",
        ["محلل بيانات مبتدئ", "جونيور", "باور بي اي"], ["junior", "data", "analyst", "power", "bi", "beginner"]),
    "Governance and Risk Compliance": ("security", "الحوكمة وإدارة المخاطر والامتثال (GRC)",
        "يقدم مبادئ حوكمة تقنية المعلومات وإدارة المخاطر والامتثال لمواءمة العمليات التقنية مع أهداف المؤسسة والمتطلبات التنظيمية.",
        ["حوكمة", "مخاطر", "امتثال", "جي ار سي"], ["grc", "governance", "risk", "compliance"]),
    "Information Security Compliance & ISO 27001 Specialist": ("security", "أخصائي امتثال أمن المعلومات ومعيار ISO 27001",
        "برنامج PECB ISO/IEC 27001 Lead Implementer لتأسيس وتطبيق وتحسين نظام إدارة أمن المعلومات (ISMS): متطلبات المعيار وضوابط Annex A وإدارة المخاطر والتدقيق.",
        ["ايزو", "امن المعلومات", "ايزو 27001"], ["iso", "27001", "isms", "information", "security", "compliance", "pecb"]),
    "AWS Security Cloud Computing": ("security", "أمن الحوسبة السحابية على AWS",
        "مسار تعليمي على AWS يبني أساسيات السحابة والتصميم المعماري وقدرات الأمن العملية: Cloud Practitioner، Architecting on AWS، AWS Security Essentials، وهندسة الأمن على AWS.",
        ["كلاود", "سحابة", "امازون"], ["aws", "cloud", "security", "architecture"]),
    "Cyber Security Incident Response Analyst": ("security", "محلل الاستجابة لحوادث الأمن السيبراني",
        "يستجيب للحوادث والتهديدات (التصيد، الشبكات، البريد، التنبيهات) ويحلل السجلات: أساسيات الشبكات وأنظمة التشغيل، تقنيات الهجوم، الاستجابة للحوادث والأدلة الرقمية، وعمليات SOC وSIEM.",
        ["سوك", "استجابة للحوادث", "سايبر", "امن سيبراني"], ["soc", "siem", "incident", "response", "cyber", "forensics", "security"]),
    "Vulnerability Analyst and Penetration Tester": ("security", "محلل الثغرات ومختبر الاختراق",
        "ينفذ اختبارات أمن الشبكات وفق أطر منهجية: أساسيات الشبكات، اختبار اختراق الشبكات وتطبيقات الويب وتطبيقات Android.",
        ["اختبار اختراق", "اختراق", "ثغرات", "هاكر", "بنتست"], ["penetration", "pentest", "pentester", "vulnerability", "ethical", "hacking"]),
    "SAP S/4HANA MM Consultant": ("erp", "استشاري SAP S/4HANA لإدارة المواد (MM)",
        "يغطي دورة المشتريات وإدارة المخزون كاملة على SAP S/4HANA: الشراء، استلام البضائع، مطابقة الفواتير، البيانات الرئيسية للمواد والموردين، والتكامل مع المالية.",
        ["ساب", "مشتريات", "مخازن"], ["sap", "s/4hana", "hana", "mm", "materials", "procurement"]),
    "SAP S/4HANA FI Consultant": ("erp", "استشاري SAP S/4HANA للمالية (FI)",
        "يؤهل لتهيئة العمليات المالية على SAP S/4HANA: الهيكل المؤسسي، الأستاذ العام، الحسابات الدائنة والمدينة، الأصول الثابتة، ونظرة عامة على التكاليف (CO).",
        ["ساب", "مالية", "محاسبة"], ["sap", "s/4hana", "hana", "fi", "finance", "accounting"]),
    "Odoo Application Consultant": ("erp", "استشاري تطبيقات Odoo",
        "يصمم وينفذ حلول نظام Odoo ERP: المحاسبة والمالية، المشتريات والمخازن والتصنيع، المبيعات وCRM ونقاط البيع، والموارد البشرية، مع تطبيقات الذكاء الاصطناعي في الأتمتة.",
        ["اودو", "أودو"], ["odoo", "erp", "crm", "accounting"]),
    "Google Project Management": ("erp", "إدارة المشروعات من Google",
        "يؤهل لتولي إدارة المشروعات: أساسيات إدارة المشروعات، بدء المشروع وتخطيطه، الإدارة الرشيقة (Agile)، وتطبيقات الذكاء الاصطناعي.",
        ["ادارة مشروعات", "ادارة المشاريع", "بروجكت مانجر", "جوجل"], ["google", "project", "management", "agile", "pm"]),
    "Immersive Game Designer": ("games", "مصمم الألعاب التفاعلية",
        "يتعلم خط الإنتاج البصري للألعاب الحديثة: النمذجة ثلاثية الأبعاد بـ Blender، تحسين الأصول، تنظيمها في Unity، بيئات الواقع الافتراضي، والعرض اللحظي.",
        ["تصميم العاب", "ثري دي", "بلندر"], ["game", "design", "designer", "blender", "unity", "3d", "vr"]),
    "Game Developer": ("games", "مطور الألعاب",
        "يصمم ويطور ويحسّن ويختبر ألعاب الموبايل والألعاب ثلاثية الأبعاد: أساسيات البرمجة للألعاب، تطوير الألعاب ثنائية وثلاثية الأبعاد، Android، تحسين الأداء، والربح من الألعاب.",
        ["مطور العاب", "برمجة العاب", "جيم ديفلوبر"], ["game", "developer", "development", "android", "mobile", "3d", "2d"]),
    "Applied AI Agents for Education and Teaching Professional": ("industry", "وكلاء الذكاء الاصطناعي التطبيقية للتعليم والتدريس",
        "برنامج DEPI Industry للمعلمين والتربويين لدمج أدوات الذكاء الاصطناعي في التدريس: تخطيط الدروس وإعداد المحتوى، التقييم والتعلم المخصص، وأتمتة المهام التعليمية باستخدام n8n.",
        ["معلم", "معلمين", "تعليم", "تدريس"], ["education", "teaching", "teachers", "educators", "ai", "agents"]),
    "Applied AI Agents for Legal Professional": ("industry", "وكلاء الذكاء الاصطناعي التطبيقية للمهن القانونية",
        "برنامج DEPI Industry للقانونيين لتوظيف الذكاء الاصطناعي في البحث القانوني والصياغة وإدارة المستندات والتحليل القانوني وأتمتة سير العمل والامتثال.",
        ["محامي", "محامين", "قانون", "قانوني"], ["legal", "law", "lawyers", "ai", "agents"]),
    "Oracle Fusion Financial Consultant": ("industry", "استشاري Oracle Fusion المالي",
        "برنامج DEPI Industry لتصميم وتنفيذ تطبيقات Oracle Financials: الهيكل المؤسسي، الأستاذ العام، الحسابات المدينة والدائنة، الضرائب، البنوك، والأصول الثابتة.",
        ["اوراكل", "أوراكل", "مالية"], ["oracle", "fusion", "financial", "finance", "erp"]),
    "AI Software Professional": ("industry", "محترف تطوير البرمجيات بالذكاء الاصطناعي",
        "برنامج DEPI Industry للمطورين لدمج الذكاء الاصطناعي في تطوير البرمجيات: مساعدات البرمجة، سير العمل الذكي، RAG على المستودعات، توليد الاختبارات، والتقييم والمراقبة.",
        ["مطورين", "برمجة بالذكاء الاصطناعي"], ["ai", "software", "developers", "coding", "assistants"]),
    "Advanced Marketing Automation with AI Professional": ("industry", "أتمتة التسويق المتقدمة بالذكاء الاصطناعي",
        "برنامج DEPI Industry لبناء أنظمة تسويق متكاملة مدعومة بالذكاء الاصطناعي: الاستراتيجية وأبحاث السوق، أنظمة المحتوى، تسويق الفيديو، التسويق بالأداء والتحليلات، والأتمتة وقمع المبيعات.",
        ["تسويق", "اتمتة التسويق"], ["marketing", "automation", "ai", "funnels"]),
    "AI Healthcare Professional": ("industry", "محترف الذكاء الاصطناعي في الرعاية الصحية",
        "برنامج DEPI Industry لتطبيق أنظمة الذكاء الاصطناعي في الحالات السريرية والصحية: هندسة الأوامر، بناء مساعد طبي بتقنية RAG، الـ APIs، ضوابط الأمان، والتواصل مع المرضى.",
        ["طبيب", "اطباء", "طب", "صحة", "طبي"], ["healthcare", "medical", "health", "doctors", "clinical", "ai"]),
}


def parse_catalog(path):
    """Return {heading: {"description": str, "curriculum": [..]}} for every profile in the catalog."""
    text = path.read_text(encoding="utf-8")
    out, current_track = {}, None
    for block in re.split(r"\n(?=#{2,4} )", text):
        head, _, body = block.partition("\n")
        title = re.sub(r"^#+\s*(?:\d+(?:\.\d+)*\.\s*)?", "", head).strip()
        para = " ".join(l.strip() for l in body.split("\n")
                        if l.strip() and not l.startswith("|") and not l.startswith("---")
                        and not re.match(r"^\d+\.\s", l) and "Job profiles in this track" not in l
                        and "study plan" not in l)
        rows = []
        for line in body.split("\n"):
            if line.startswith("|") and not set(line) <= set("|-: "):
                cell = line.strip().strip("|").split("|")[-1].strip()
                if cell and cell not in ("Contents", "Content", "#"):
                    rows.extend(x.strip(" •") for x in cell.split("<br>") if x.strip(" •"))
        out[title] = {"description": para.replace("**", "").strip(), "curriculum": rows}
    return out


def entry(key, category, q_ar, q_en, a_ar, a_en, kw_ar, kw_en, url, attribution):
    digest = hashlib.sha256(f"{PACK}|{key}|{q_en}|{a_en}|{a_ar}".encode("utf-8")).hexdigest()
    return {"pack_key": key, "program": "DEPI", "retrieval_scope": "DEPI_AUTHORITATIVE", "category": category,
            "question_ar": q_ar, "question": q_en, "answer_ar": a_ar, "answer": a_en,
            "keywords_ar": sorted(set(kw_ar)), "keywords": sorted({k.lower() for k in kw_en}),
            "source_url": url if url.startswith("http") else "https://depi.gov.eg",
            "source_attribution": f"{PACK} | {attribution}", "content_hash": digest}


def build():
    catalog = parse_catalog(CATALOG)
    industry = parse_catalog(INDUSTRY)
    entries = [entry(c["key"], c["category"], c["q_ar"], c["q_en"], c["a_ar"], c["a_en"], c["kw_ar"], c["kw_en"],
                     c["url"], "depi.gov.eg" if c["url"].startswith("http") else c["url"]) for c in CORE]

    by_track = {t[0]: [] for t in TRACKS.values()}
    for name, (track, name_ar, summary_ar, kw_ar, kw_en) in PROFILES.items():
        src = industry if track == "industry" else catalog
        data = src.get(name)
        if not data or not data["curriculum"]:
            raise SystemExit(f"catalog section not found or empty: {name}")
        if track != "industry":
            by_track[track].append((name, name_ar))
        plan = "\n".join(f"{i}. {c}" for i, c in enumerate(data["curriculum"], 1))
        programme_ar = "برنامج DEPI Industry" if track == "industry" else f"ضمن {next(v[1] for v in TRACKS.values() if v[0] == track)}"
        programme_en = "DEPI Industry programme" if track == "industry" else f"{next(v[2] for v in TRACKS.values() if v[0] == track)} track"
        entries.append(entry(
            f"profile:{name}", "catalog_industry_profile" if track == "industry" else "catalog_profile",
            f"ما هو مسار {name_ar} ({name}) وما محتواه التدريبي؟",
            f"What is the {name} job profile in DEPI and what does it cover?",
            f"{name_ar} ({name}) - {programme_ar}.\n{summary_ar}\n\nالخطة الدراسية التقنية:\n{plan}",
            f"{name} - {programme_en}.\n{data['description']}\n\nTechnical study plan:\n{plan}",
            kw_ar + name_ar.replace("(", " ").replace(")", " ").split(),
            kw_en + re.findall(r"[a-z0-9.#+/-]{2,}", name.lower()),
            CATALOG_SRC, INDUSTRY_SRC if track == "industry" else CATALOG_SRC))

    track_lines_ar, track_lines_en = [], []
    for heading, (key, name_ar, name_en, summary_ar, kw_ar, kw_en) in TRACKS.items():
        profiles = by_track[key]
        desc_en = catalog[heading]["description"]
        listing = "\n".join(f"{i}. {n} - {a}" for i, (n, a) in enumerate(profiles, 1))
        listing_en = "\n".join(f"{i}. {n}" for i, (n, _) in enumerate(profiles, 1))
        track_lines_ar.append(f"• {name_ar} ({name_en}): " + "، ".join(n for n, _ in profiles))
        track_lines_en.append(f"• {name_en}: " + ", ".join(n for n, _ in profiles))
        entries.append(entry(
            f"track:{key}", "catalog_track",
            f"ما هي المسارات الوظيفية في {name_ar} ({name_en})؟", f"Which job profiles are in the {name_en} track?",
            f"{name_ar} ({name_en}): {summary_ar}\n\nالمسارات الوظيفية المتاحة في الدورة الخامسة:\n{listing}",
            f"{name_en} track: {desc_en}\n\nJob profiles in Round 5:\n{listing_en}",
            kw_ar + ["مسار", "مسارات", "تراك", "تخصصات"], kw_en + ["track", "profiles"], CATALOG_SRC, CATALOG_SRC))

    entries.append(entry(
        "tracks:all", "catalog_track",
        "ما هي مسارات التدريب والتخصصات المتاحة في مبادرة رواد مصر الرقمية؟", "What tracks and specialisations does DEPI offer?",
        "تضم الدورة الخامسة (يوليو - ديسمبر 2026) سبعة مسارات تكنولوجية، يحتوي كل منها على مسارات وظيفية (Job Profiles) يختار المتقدم واحداً منها فقط:\n"
        + "\n".join(track_lines_ar)
        + "\nبالإضافة إلى برنامج DEPI Industry للمهنيين، ومحاور المهارات الشخصية والعمل الحر وريادة الأعمال واللغة الإنجليزية لجميع المتدربين."
        + "\nملاحظة: تُتاح المسارات حسب الكلية والسنة الدراسية ونوع الكلية (تخصصي أو عام)، ويمكن مراجعة البرامج المتاحة لكل كلية على موقع المبادرة https://depi.gov.eg",
        "Round 5 (July - December 2026) offers seven technology tracks, each with job profiles; applicants choose exactly one:\n"
        + "\n".join(track_lines_en)
        + "\nPlus the DEPI Industry programme for professionals, and soft skills, freelancing, entrepreneurship and English for all trainees."
        + "\nNote: available tracks depend on your faculty, study year and faculty type (specialised or general); check the programmes open to your faculty at https://depi.gov.eg",
        ["مسار", "مسارات", "المسارات", "تخصص", "تخصصات", "التخصصات", "تراكات", "التراكات", "المتاحة", "كورسات", "التدريب", "تدريب"],
        ["tracks", "track", "specializations", "specialisations", "programs", "courses", "available"], CATALOG_SRC, CATALOG_SRC))
    return entries


if __name__ == "__main__":
    pack = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"pack": PACK, "entries": pack}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(pack)} entries to {OUT.relative_to(ROOT)}")
