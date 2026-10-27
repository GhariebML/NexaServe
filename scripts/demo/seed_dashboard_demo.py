"""Seeds realistic, clearly-tagged DEMO activity so the dashboard shows a working DEPI service.

Every seeded row is tagged and removable (``--remove``):
  customers.metadata.demo = true, conversations/messages/tickets via those customers,
  agents.metadata.demo = true, audit_logs.payload.demo = true, agent_performance.notes = 'demo-seed'.

Customer replies come from the live DEPI knowledge base (curated pack + official FAQs), so the
conversations read like real traffic. Phone numbers use the +20 0 prefix, which cannot exist in
Egypt, and customers have no WhatsApp id, so nothing can ever be delivered to a seeded customer.

Usage:  python scripts/demo/seed_dashboard_demo.py [--days 45] [--customers 420] [--remove]
"""
import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "infra" / "knowledge" / "depi_knowledge_pack_r5.json"
RNG = random.Random(20261027)
NOW = datetime.now(timezone.utc)
DEMO = {"demo": True, "seed": "dashboard-demo-v1"}

FIRST_M = ["أحمد", "محمد", "محمود", "مصطفى", "يوسف", "عمر", "كريم", "خالد", "إسلام", "حسام", "طارق", "عبدالرحمن", "مازن", "زياد", "أدهم", "شريف", "هشام", "أمير", "سيف", "بلال"]
FIRST_F = ["مريم", "سارة", "نور", "هبة", "آية", "ياسمين", "منة", "رنا", "فاطمة", "دينا", "سلمى", "ندى", "هاجر", "شيماء", "رحمة", "جنى", "ملك", "إسراء", "نهى", "لمياء"]
LAST = ["حسن", "إبراهيم", "عبدالله", "السيد", "علي", "مصطفى", "سالم", "فؤاد", "عادل", "سمير", "منصور", "الشريف", "رشاد", "النجار", "عثمان", "زكي", "شاكر", "فتحي", "جمال", "البنا"]
LATIN = {"أحمد": "ahmed", "محمد": "mohamed", "محمود": "mahmoud", "مصطفى": "mostafa", "يوسف": "youssef", "عمر": "omar", "كريم": "karim",
         "خالد": "khaled", "إسلام": "eslam", "حسام": "hossam", "طارق": "tarek", "عبدالرحمن": "abdelrahman", "مازن": "mazen", "زياد": "ziad",
         "أدهم": "adham", "شريف": "sherif", "هشام": "hesham", "أمير": "amir", "سيف": "seif", "بلال": "belal", "مريم": "mariam", "سارة": "sara",
         "نور": "nour", "هبة": "heba", "آية": "aya", "ياسمين": "yasmin", "منة": "menna", "رنا": "rana", "فاطمة": "fatma", "دينا": "dina",
         "سلمى": "salma", "ندى": "nada", "هاجر": "hagar", "شيماء": "shaimaa", "رحمة": "rahma", "جنى": "jana", "ملك": "malak", "إسراء": "esraa",
         "نهى": "noha", "لمياء": "lamiaa"}
GOVERNORATES = ["القاهرة"] * 6 + ["الجيزة"] * 4 + ["الإسكندرية"] * 3 + ["الدقهلية", "الشرقية", "القليوبية", "الغربية", "المنوفية", "أسيوط",
                "سوهاج", "المنيا", "بني سويف", "الفيوم", "قنا", "الأقصر", "أسوان", "بورسعيد", "الإسماعيلية", "السويس", "دمياط", "كفر الشيخ", "البحيرة"]
FACULTIES = ["هندسة", "حاسبات ومعلومات", "تجارة", "علوم", "آداب", "فنون تطبيقية", "إعلام", "حقوق", "معهد عالي للحاسبات"]

# Customer phrasings (Egyptian Arabic / English) -> knowledge pack entry.
PHRASES = [
    ("core_eligibility", "ما هي شروط الالتحاق بالمبادرة؟"), ("core_eligibility", "ايه الشروط المطلوبة عشان اقدم في رواد مصر الرقمية"),
    ("core_eligibility", "انا طالب في سنة تالتة ينفع اقدم؟"), ("core_eligibility", "انا عندي تأجيل تجنيد ينفع اقدم؟"),
    ("core_eligibility", "What are the requirements to join DEPI?"), ("core_documents", "ايه المستندات المطلوبة للخريجين؟"),
    ("core_documents", "محتاج ارفع ايه من الورق وانا لسه طالب"), ("core_cost", "هل المنحة مجانية؟"), ("core_cost", "هو في مصاريف للتسجيل؟"),
    ("core_cost", "Is DEPI free?"), ("core_duration", "مدة التدريب كام شهر؟"), ("core_duration", "هل التدريب اونلاين ولا حضوري؟"),
    ("core_duration", "How long is the program?"), ("core_attendance", "نسبة الحضور المطلوبة كام؟"), ("core_attendance", "هل التدريب بيقف وقت امتحانات الكلية؟"),
    ("core_certificate", "هل هاخد شهادة في الآخر؟"), ("core_certificate", "شروط الحصول على شهادة إتمام التدريب ايه؟"),
    ("core_locations", "هل التدريب في القاهرة بس؟"), ("core_locations", "فين أماكن التدريب في المحافظات؟"), ("core_registration", "ازاي اسجل في المبادرة؟"),
    ("core_registration", "اتأكد ازاي ان التسجيل تم بنجاح؟"), ("core_exams", "امتحان الانجليزي مدته قد ايه؟"), ("core_exams", "ايه هي اختبارات القبول؟"),
    ("core_contact", "ازاي اتواصل معاكم؟ رقم الخط الساخن"), ("core_contact", "What is the DEPI hotline number?"), ("core_overview", "ايه هي مبادرة رواد مصر الرقمية؟"),
    ("core_industry", "ما هو برنامج DEPI Industry؟"), ("core_industry", "ايه الفرق بين DEPI و DEPI Industry"), ("catalog_track", "ايه المسارات المتاحة في الدورة الخامسة؟"),
    ("catalog_track", "What tracks does DEPI offer?"), ("catalog_skills", "ايه محتوى المهارات الشخصية والعمل الحر؟"),
    ("profile:DevOps Engineer", "عايز اعرف محتوى كورس DevOps"), ("profile:React Frontend Web Developer", "ايه اللي هدرسه في مسار React Frontend؟"),
    ("profile:Full Stack .Net Web Developer", "في كورس فول ستاك دوت نت؟"), ("profile:Cross Platform Mobile App Developer", "عايز اتعلم فلاتر وتطبيقات موبايل"),
    ("profile:Software Tester", "محتوى مسار Software Testing ايه؟"), ("profile:Data Scientist", "ايه محتوى مسار Data Scientist؟"),
    ("profile:Professional Data Analyst", "في كورس Power BI متقدم؟"), ("profile:Junior Data Analyst", "انا مبتدئ في تحليل البيانات انهي مسار يناسبني؟"),
    ("profile:Cyber Security Incident Response Analyst", "عايز اشتغل SOC Analyst في كورس لده؟"),
    ("profile:Vulnerability Analyst and Penetration Tester", "في مسار اختبار اختراق Penetration Testing؟"),
    ("profile:Agentic AI and Generative AI System Developer", "ايه محتوى مسار Generative AI و Agentic AI؟"),
    ("profile:AI Automation Workflow with N8N Professional", "في كورس أتمتة باستخدام n8n؟"), ("profile:Digital Marketing Specialist", "محتوى مسار الديجيتال ماركتنج ايه؟"),
    ("profile:UI & UX Web Designer", "عايز اتعلم UI/UX و Figma"), ("profile:Odoo Application Consultant", "هل في كورس Odoo؟"),
    ("profile:SAP S/4HANA FI Consultant", "في كورس SAP Finance؟"), ("profile:Google Project Management", "في كورس ادارة مشروعات من جوجل؟"),
    ("profile:Game Developer", "في مسار لتطوير الألعاب؟"), ("profile:AI Healthcare Professional", "انا طبيب هل في مسار ذكاء اصطناعي للرعاية الصحية؟"),
    ("profile:Applied AI Agents for Legal Professional", "انا محامي ينفع اقدم في DEPI Industry؟"),
]
GREETINGS = [("السلام عليكم", "وعليكم السلام ورحمة الله، أهلاً بك في خدمة عملاء مبادرة رواد مصر الرقمية (DEPI). كيف يمكنني مساعدتك اليوم؟"),
             ("شكرا جدا", "العفو، سعداء بخدمتك. لا تتردد في التواصل معنا في أي وقت لأي استفسار عن مبادرة رواد مصر الرقمية."),
             ("Hello", "Hello and welcome to DEPI customer service. How can I help you today?")]

# (category id, category, title, customer complaint, resolution, team)
TICKET_CASES = [
    (4, "exams", "لم يصلني رابط امتحان اللغة الإنجليزية", "سجلت من أسبوع ولسه ما وصلنيش رابط امتحان الانجليزي على الإيميل ولا في صفحتي",
     "تمت مراجعة الحساب وإعادة إرسال رابط الامتحان على البريد الإلكتروني المسجل، وتأكد المتقدم من ظهوره في صفحة المستخدم.", "DEPI Citizen Support"),
    (4, "exams", "انقطاع الاتصال أثناء الامتحان التقني", "النت فصل مني وانا في نص الامتحان التقني والامتحان اتقفل، عايز فرصة تانية",
     "تم رفع الحالة للجنة الامتحانات ومراجعة سجل الجلسة، وتمت الموافقة على إعادة جدولة الامتحان مرة واحدة وإبلاغ المتقدم بالموعد الجديد.", "DEPI Specialist Support"),
    (3, "lms", "تعذر الدخول على منصة LMS", "كل ما احاول ادخل على LMS يقولي اسم المستخدم او كلمة السر غلط",
     "تم إعادة تعيين كلمة المرور وإرسال بيانات الدخول الجديدة، وتأكد المتدرب من الدخول بنجاح.", "DEPI Citizen Support"),
    (6, "technical", "خطأ في برنامج Safe Exam Browser", "برنامج SEB بيطلعلي error اول ما افتحه ومش عارف ابدأ الامتحان",
     "تم توجيه المتقدم لتحميل الإصدار الرسمي من SEB وتشغيله كمسؤول وإغلاق برامج التسجيل، وتمكن من بدء الامتحان.", "DEPI Citizen Support"),
    (1, "enrollment", "طلب تغيير المسار الوظيفي", "اخترت مسار Junior Data Analyst بالغلط وعايز اغيره لـ Data Scientist",
     "تم توضيح أن تعديل المسار متاح فقط خلال فترة التسجيل، وتم تنفيذ التعديل لأن الطلب ورد قبل إغلاق التسجيل.", "DEPI Specialist Support"),
    (1, "enrollment", "حالة الطلب تحت المراجعة منذ فترة", "حالة طلبي مكتوب عليها تحت المراجعة من اكتر من اسبوعين، هو في مشكلة؟",
     "تمت مراجعة المستندات المرفوعة ووُجد أن صورة الرقم القومي غير واضحة، وتم إرشاد المتقدم لإعادة رفعها واستكمال المراجعة.", "DEPI Citizen Support"),
    (7, "account", "طلب تعديل البريد الإلكتروني", "الإيميل اللي سجلت بيه اتقفل ومحتاج اغيره عشان توصلني الرسايل",
     "تم التحقق من هوية المتقدم وتحديث البريد الإلكتروني على الحساب.", "DEPI Citizen Support"),
    (7, "account", "خطأ في الرقم القومي المسجل", "كتبت رقم قومي غلط في رقم واحد وقت التسجيل",
     "تم استلام صورة البطاقة والتحقق منها وتصحيح الرقم القومي على الحساب.", "DEPI Specialist Support"),
    (5, "certificates", "لم أستلم شهادة إتمام التدريب", "خلصت التدريب والمشروع و3 جيجز ولسه الشهادة ما ظهرتش",
     "تم التأكد من استيفاء جميع متطلبات المسار، وإصدار الشهادة وإتاحتها في صفحة المتدرب.", "DEPI Specialist Support"),
    (2, "training", "تعارض مواعيد الجروب مع امتحانات الكلية", "مواعيد الجروب بتاعي متعارضة مع امتحانات آخر السنة",
     "تم توضيح أن التدريب يتوقف للطلاب شهراً خلال الامتحانات النهائية، وتم تأكيد الجدول المحدث مع المتدرب.", "DEPI Citizen Support"),
    (2, "training", "طلب تغيير محافظة التدريب", "انا نقلت من أسيوط للقاهرة وعايز اغير محافظة التدريب",
     "تم توضيح أن محافظة التدريب غير قابلة للتعديل بعد التسجيل وفق شروط المنحة، مع إرشاد المتدرب لخيارات الحضور المتاحة.", "DEPI Citizen Support"),
    (9, "complaint", "تأخر الرد على البريد الإلكتروني", "بعت ايميل لـ info من اكتر من اسبوع ومحدش رد عليا",
     "تم الاعتذار للمتقدم والرد على استفساره بالكامل، وتمت إحالة ملاحظة التأخير لفريق البريد الإلكتروني.", "DEPI Escalation Team"),
    (9, "complaint", "شكوى من تكرار إلغاء الجلسات", "المحاضرة الحضورية اتلغت مرتين في نفس الأسبوع من غير ما حد يبلغنا",
     "تم التواصل مع مركز التدريب وتأكيد خطة تعويض الجلسات، وإبلاغ المجموعة بالمواعيد الجديدة.", "DEPI Escalation Team"),
    (6, "technical", "الصورة الشخصية لا تظهر في الحساب", "رفعت الصورة الشخصية كذا مرة ومش بتظهر في البروفايل",
     "تم إرشاد المتقدم لرفع صورة بصيغة JPG وبحجم أقل من 2 ميجا، وظهرت الصورة بنجاح.", "DEPI Citizen Support"),
    (11, "general", "استفسار عن موعد بدء الدورة الخامسة", "امتى بالظبط هيبدأ التدريب في الدورة الخامسة؟",
     "تم إبلاغ المتقدم بأن الدورة الخامسة تمتد من يوليو حتى ديسمبر 2026، وأن موعد مجموعته سيصل عبر البريد الإلكتروني وصفحة المستخدم.", "DEPI Citizen Support"),
]
CSAT_FEEDBACK = {5: ["خدمة ممتازة وسرعة في الرد", "شكراً جداً، تم حل المشكلة بسرعة", "Excellent support, thank you!", "الموظف كان متعاون جداً"],
                 4: ["الرد كان مفيد", "تم الحل لكن استغرق بعض الوقت", "Good service", "شكراً على المتابعة"],
                 3: ["الحل مقبول", "كنت أتمنى رد أسرع"], 2: ["استغرق الحل وقتاً طويلاً"], 1: ["المشكلة لم تحل بالكامل"]}
DEMO_AGENTS = [("Mariam Adel", "mariam.adel", "tier1", "DEPI Citizen Support"), ("Youssef Samir", "youssef.samir", "tier1", "DEPI Citizen Support"),
               ("Hana Mostafa", "hana.mostafa", "tier1", "DEPI Citizen Support"), ("Ahmed Tarek", "ahmed.tarek", "tier2", "DEPI Specialist Support"),
               ("Laila Ibrahim", "laila.ibrahim", "tier2", "DEPI Specialist Support"), ("Mahmoud Nabil", "mahmoud.nabil", "supervisor", "DEPI Escalation Team")]


def connect():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            env[key.strip()] = value.strip().strip('"').strip("'")
    return psycopg2.connect(host="127.0.0.1", port=int(env.get("POSTGRES_PORT", 5432)), dbname="nexaserve_final",
                            user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"])


def remove(cur):
    cur.execute("SELECT id FROM customers WHERE metadata->>'demo' = 'true'")
    ids = [r[0] for r in cur.fetchall()]
    counts = {}
    for label, sql in [
        ("ticket_events", "DELETE FROM ticket_events WHERE ticket_id IN (SELECT id FROM tickets WHERE customer_id = ANY(%s::uuid[]))"),
        ("csat_surveys", "DELETE FROM csat_surveys WHERE customer_id = ANY(%s::uuid[])"),
        ("tickets", "DELETE FROM tickets WHERE customer_id = ANY(%s::uuid[])"),
        ("messages", "DELETE FROM messages WHERE customer_id = ANY(%s::uuid[])"),
        ("conversations", "DELETE FROM conversations WHERE customer_id = ANY(%s::uuid[])"),
        ("customers", "DELETE FROM customers WHERE id = ANY(%s::uuid[])"),
    ]:
        cur.execute(sql, ([str(i) for i in ids],))
        counts[label] = cur.rowcount
    cur.execute("DELETE FROM agent_performance WHERE notes = 'demo-seed'")
    counts["agent_performance"] = cur.rowcount
    cur.execute("DELETE FROM audit_logs WHERE payload->>'demo' = 'true'")
    counts["audit_logs"] = cur.rowcount
    cur.execute("DELETE FROM agents WHERE metadata->>'demo' = 'true'")
    counts["agents"] = cur.rowcount
    return counts


def answer_bank(cur):
    entries = {}
    for e in json.loads(PACK.read_text(encoding="utf-8"))["entries"]:
        key = e["pack_key"] if e["pack_key"].startswith("profile:") else e["category"]
        entries.setdefault(key, e)
    cur.execute("SELECT question, answer FROM knowledge_base WHERE is_active AND category = 'lms_assessment_faq' AND length(answer) > 60")
    lms = cur.fetchall()
    return entries, lms


def moment(day_offset):
    """A realistic timestamp: busier on weekdays, peaks late morning and evening (Cairo time)."""
    hour = RNG.choices(range(24), weights=[1, 1, 0, 0, 0, 0, 1, 2, 4, 6, 8, 9, 9, 8, 7, 6, 6, 7, 8, 9, 9, 8, 5, 3])[0]
    ts = (NOW - timedelta(days=day_offset)).replace(hour=hour, minute=RNG.randrange(60), second=RNG.randrange(60), microsecond=0) - timedelta(hours=2)
    return min(ts, NOW - timedelta(minutes=RNG.randrange(3, 90)))


def seed(cur, days, n_customers):
    entries, lms = answer_bank(cur)
    agent_rows = []
    for name, handle, role, team in DEMO_AGENTS:
        agent_rows.append((str(uuid.uuid4()), name, f"{handle}@depi-support.example", role, team, RNG.choice(["available", "available", "busy", "offline"]), Json(DEMO),
                           NOW - timedelta(days=days + 10)))
    execute_values(cur, "INSERT INTO agents (id, name, email, role, team, status, metadata, created_at) VALUES %s", agent_rows)
    cur.execute("SELECT id, name, team FROM agents")
    all_agents = cur.fetchall()
    by_team = {}
    for aid, name, team in all_agents:
        by_team.setdefault(team or "DEPI Citizen Support", []).append((aid, name))

    # Customers
    customers = []
    tracks = [k for k in entries if k.startswith("profile:")]
    for i in range(n_customers):
        female = RNG.random() < 0.46
        first = RNG.choice(FIRST_F if female else FIRST_M)
        last, last2 = RNG.choice(LAST), RNG.choice(LAST)
        english = RNG.random() < 0.14
        created = NOW - timedelta(days=RNG.uniform(1, days + 20))
        customers.append({
            "id": str(uuid.uuid4()), "full_name": f"{first} {last} {last2}", "created_at": created,
            "phone": f"+200{RNG.randrange(10**9, 10**10)}", "lang": "en" if english else "ar",
            "email": f"{LATIN.get(first, 'user')}.{i:04d}@example.com",
            "meta": {**DEMO, "program": "DEPI", "governorate": RNG.choice(GOVERNORATES), "faculty": RNG.choice(FACULTIES),
                     "applicant_type": RNG.choice(["student", "student", "graduate", "graduate", "graduate"]),
                     "preferred_track": RNG.choice(tracks).split(":", 1)[1], "round": "R5"},
        })
    execute_values(cur, """INSERT INTO customers (id, full_name, phone_number, email, metadata, created_at, updated_at, preferred_language, last_activity_at)
                           VALUES %s""", [(c["id"], c["full_name"], c["phone"], c["email"], Json(c["meta"]), c["created_at"], c["created_at"],
                                           c["lang"], c["created_at"]) for c in customers])

    conversations, messages, tickets, events, csat, audits, perf = [], [], [], [], [], [], []
    ticket_seq = RNG.randrange(41000, 42000)
    cur.execute("SELECT ticket_number FROM tickets")
    taken_numbers = {r[0] for r in cur.fetchall()}
    weights = [1.0 + 0.9 * (days - d) / days for d in range(days)]   # steady growth towards today
    for c in customers:
        visits = RNG.choices([1, 1, 1, 2, 2, 3, 4], k=1)[0]
        for _ in range(visits):
            d = RNG.choices(range(days), weights=[w * (0.55 if (NOW - timedelta(days=i)).weekday() in (4, 5) else 1) for i, w in enumerate(weights)])[0]
            start = max(moment(d), c["created_at"])
            if start > NOW - timedelta(minutes=2):
                start = NOW - timedelta(minutes=RNG.randrange(5, 240))
            channel = RNG.choices(["whatsapp", "webchat", "telegram"], weights=[68, 28, 4])[0]
            escalate = RNG.random() < 0.13
            conv_id = str(uuid.uuid4())
            t = start
            turns = []
            if RNG.random() < 0.35:
                turns.append(("greeting", RNG.choice(GREETINGS[:1] if c["lang"] == "ar" else GREETINGS[2:])))
            for _ in range(RNG.choices([1, 1, 2, 2, 3], k=1)[0]):
                if RNG.random() < 0.12 and lms:
                    q, a = RNG.choice(lms)
                    turns.append(("support", (q, a)))
                else:
                    key, phrase = RNG.choice([p for p in PHRASES if (p[1][0].isascii()) == (c["lang"] == "en")] or PHRASES)
                    e = entries[key]
                    turns.append(("faq", (phrase, e["answer"] if c["lang"] == "en" else e["answer_ar"])))
            if not escalate and RNG.random() < 0.3:
                turns.append(("thanks", GREETINGS[1] if c["lang"] == "ar" else ("Thank you!", "You're welcome! Feel free to reach out anytime about DEPI.")))
            intent = "faq_query"
            for kind, (q, a) in turns:
                req = f"req-demo-{uuid.uuid4().hex[:20]}"
                direct = kind in ("faq", "greeting", "thanks") and RNG.random() < 0.82
                latency = RNG.randint(700, 3200) if direct else RNG.randint(7500, 24000)
                cust_msg = (str(uuid.uuid4()), conv_id, c["id"], "customer", q, None, None, t, channel)
                t_ai = t + timedelta(milliseconds=latency)
                ai_intent = "general_support" if kind in ("greeting", "thanks") else "faq_query"
                messages.append(cust_msg)
                messages.append((str(uuid.uuid4()), conv_id, c["id"], "ai", a, ai_intent, round(RNG.uniform(0.86, 0.98) if direct else RNG.uniform(0.62, 0.9), 2), t_ai, channel))
                decision = "verified_curated_answer" if direct else RNG.choices(["grounded_llm", "verified_faq_fallback"], weights=[85, 15])[0]
                payload = {**DEMO, "request_id": req, "intent": ai_intent, "status": "success" if decision != "verified_faq_fallback" else "fallback",
                           "program": "DEPI", "locale": c["lang"], "guardrail_decision": decision, "grounded": decision != "verified_faq_fallback",
                           "llm_status": "not_needed" if direct else "succeeded", "retrieved_count": RNG.randint(3, 5), "workflow_id": "CSWF000000000001"}
                exec_id = str(RNG.randrange(20000, 99999))
                audits.append(("01_gateway_dispatcher", exec_id, "turn_completed", Json(payload), latency, t_ai, channel))
                audits.append(("SubWF 04B - Knowledge Base & FAQ", exec_id, "rag_retrieved", Json({**DEMO, "request_id": req}), RNG.randint(90, 520), t_ai, channel))
                if not direct:
                    audits.append(("SubWF 04B - Knowledge Base & FAQ", exec_id, "llm_completed", Json({**DEMO, "request_id": req, "llm_status": "succeeded"}),
                                   latency - RNG.randint(400, 1500), t_ai, channel))
                if channel == "whatsapp":
                    audits.append(("06_output_channel_dispatcher", exec_id, "message_dispatched", Json({**DEMO, "request_id": req, "channel": "whatsapp"}), None,
                                   t_ai + timedelta(seconds=1), channel))
                t = t_ai + timedelta(seconds=RNG.randint(25, 240))
            status = "closed" if t < NOW - timedelta(hours=6) else "active"
            if escalate:
                intent = "human_escalation"
                case = RNG.choice(TICKET_CASES)
                cat_id, cat, title, complaint, resolution, team = case
                ticket_seq += RNG.randint(1, 9)
                while f"TICK-{ticket_seq}" in taken_numbers:
                    ticket_seq += 1
                number = f"TICK-{ticket_seq}"
                ticket_msg_at = t
                messages.append((str(uuid.uuid4()), conv_id, c["id"], "customer", complaint, None, None, ticket_msg_at, channel))
                ack = (f"تم تسجيل طلبك برقم {number} وتحويله إلى فريق الدعم المختص، وسيتم التواصل معك في أقرب وقت."
                       if c["lang"] == "ar" else f"Your request has been registered as {number} and assigned to our support team. We will contact you shortly.")
                messages.append((str(uuid.uuid4()), conv_id, c["id"], "ai", ack, "human_escalation", 0.95, ticket_msg_at + timedelta(seconds=2), channel))
                priority = RNG.choices(["urgent", "high", "medium", "low"], weights=[7, 28, 45, 20])[0]
                sla = {"urgent": 0.5, "high": 2, "medium": 24, "low": 24}[priority]   # same SLA rule as POST /tickets
                age_h = (NOW - ticket_msg_at).total_seconds() / 3600
                if age_h < 6:
                    tstatus = RNG.choice(["open", "open", "in_progress"])
                elif age_h < 72:
                    tstatus = RNG.choices(["open", "in_progress", "resolved"], weights=[25, 40, 35])[0]
                else:
                    tstatus = RNG.choices(["open", "in_progress", "resolved", "closed"], weights=[5, 8, 60, 27])[0]
                agent_id, agent_name = RNG.choice(by_team.get(team) or by_team["DEPI Citizen Support"])
                assigned = tstatus != "open" or RNG.random() < 0.5
                first_resp = ticket_msg_at + timedelta(minutes=RNG.randint(4, int(sla * 60 * 0.7))) if assigned else None
                if first_resp and first_resp > NOW:
                    first_resp = NOW - timedelta(minutes=1)
                closed_at = None
                if tstatus in ("resolved", "closed"):
                    closed_at = min(max(ticket_msg_at + timedelta(hours=RNG.uniform(0.5, sla * 1.6)), first_resp + timedelta(minutes=10)),
                                    NOW - timedelta(minutes=5))
                tid = str(uuid.uuid4())
                score = RNG.choices([5, 4, 3, 2, 1], weights=[52, 30, 10, 5, 3])[0] if closed_at and RNG.random() < 0.7 else None
                updated = closed_at or first_resp or ticket_msg_at
                tickets.append((tid, number, c["id"], conv_id, priority, tstatus, complaint, agent_name if assigned else None, ticket_msg_at, updated, team,
                                "internal_portal", resolution if closed_at else None, ticket_msg_at + timedelta(hours=sla), cat_id,
                                agent_id if assigned else None, score, [cat, priority], first_resp, channel, title,
                                f"demo-seed:{number}", closed_at))
                events.append((tid, number, "created", "system", "NexaServe AI", None, "open", "تم إنشاء التذكرة تلقائياً من المحادثة", ticket_msg_at))
                if assigned:
                    events.append((tid, number, "assignment", "agent", "Omar Farouk", "None", agent_name, None, ticket_msg_at + timedelta(minutes=2)))
                    events.append((tid, number, "status_change", "agent", agent_name, "open", "in_progress", None, first_resp))
                    reply = "تم استلام طلبك ونعمل على مراجعته الآن، وسنوافيك بالتحديث قريباً." if c["lang"] == "ar" else "We have received your request and are reviewing it now."
                    messages.append((str(uuid.uuid4()), conv_id, c["id"], "agent", reply, None, None, first_resp, channel))
                    perf.append((agent_id, number, "agent_replied", int((first_resp - ticket_msg_at).total_seconds() * 1000), None, "demo-seed", first_resp))
                if closed_at:
                    messages.append((str(uuid.uuid4()), conv_id, c["id"], "agent", resolution, None, None, closed_at, channel))
                    events.append((tid, number, "status_change", "agent", agent_name, "in_progress", tstatus, resolution, closed_at))
                    perf.append((agent_id, number, "ticket_resolved", None, int((closed_at - ticket_msg_at).total_seconds() * 1000), "demo-seed", closed_at))
                    if score:
                        csat.append((number, conv_id, c["id"], score, RNG.choice(CSAT_FEEDBACK[score]), channel, closed_at + timedelta(minutes=RNG.randint(5, 600))))
                audits.append(("SubWF 04C - Escalation", str(RNG.randrange(20000, 99999)), "hitl_escalated",
                               Json({**DEMO, "ticket_number": number, "reason": title, "priority": priority}), None, ticket_msg_at, channel))
                status = "handed_off" if tstatus in ("open", "in_progress") else "closed"
                t = closed_at or t
            conversations.append((conv_id, c["id"], channel, status, intent, start, t if status == "closed" else None, c["lang"],
                                  bool(escalate and status == "closed")))

    execute_values(cur, """INSERT INTO conversations (id, customer_id, channel, status, current_intent, created_at, closed_at, language, satisfaction_offered)
                           VALUES %s""", conversations)
    msg_rows = []
    for mid, conv, cust, sender, content, intent, conf, at, channel in messages:
        wa = channel == "whatsapp"
        msg_rows.append((mid, conv, cust, sender, content, intent, conf, Json(DEMO), at,
                         "whatsapp" if wa else None, f"DEMO{uuid.uuid4().hex[:18].upper()}" if wa else None,
                         ("received" if sender == "customer" else RNG.choice(["read", "read", "delivered"])) if wa else None, at if wa else None))
    execute_values(cur, """INSERT INTO messages (id, conversation_id, customer_id, sender_type, content, intent, confidence, metadata, created_at,
                           provider, provider_message_id, delivery_status, delivery_updated_at) VALUES %s""", msg_rows, page_size=1000)
    execute_values(cur, """INSERT INTO tickets (id, ticket_number, customer_id, conversation_id, priority, status, reason, assigned_agent, created_at,
                           updated_at, assigned_team, escalation_channel, resolution_notes, sla_due_at, category_id, assigned_agent_id, csat_score,
                           tags, first_response_at, source_channel, title, idempotency_key, closed_at) VALUES %s""", tickets)
    execute_values(cur, """INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, old_value, new_value, message, created_at)
                           VALUES %s""", events)
    execute_values(cur, "INSERT INTO csat_surveys (ticket_number, conversation_id, customer_id, rating, feedback, channel, created_at) VALUES %s", csat)
    execute_values(cur, "INSERT INTO audit_logs (workflow_name, execution_id, event_type, payload, latency_ms, created_at, channel) VALUES %s", audits, page_size=1000)
    execute_values(cur, """INSERT INTO agent_performance (agent_id, ticket_number, event_type, response_time_ms, resolution_time_ms, notes, created_at)
                           VALUES %s""", perf)
    cur.execute("""UPDATE customers c SET
                     last_activity_at = s.last_at, updated_at = s.last_at,
                     total_tickets = COALESCE(t.n, 0), csat_avg = t.avg_csat
                   FROM (SELECT customer_id, MAX(created_at) AS last_at FROM messages GROUP BY customer_id) s
                   LEFT JOIN (SELECT customer_id, COUNT(*) AS n, ROUND(AVG(csat_score)::numeric, 2) AS avg_csat FROM tickets GROUP BY customer_id) t
                     ON t.customer_id = s.customer_id
                   WHERE c.id = s.customer_id AND c.metadata->>'demo' = 'true'""")
    return {"agents": len(agent_rows), "customers": len(customers), "conversations": len(conversations), "messages": len(msg_rows),
            "tickets": len(tickets), "ticket_events": len(events), "csat_surveys": len(csat), "audit_logs": len(audits), "agent_performance": len(perf)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--customers", type=int, default=420)
    ap.add_argument("--remove", action="store_true", help="delete all seeded demo rows and exit")
    args = ap.parse_args()
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            removed = remove(cur)
            if args.remove:
                print(json.dumps({"removed": removed}))
                return
            print(json.dumps({"replaced": removed, "seeded": seed(cur, args.days, args.customers)}))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
