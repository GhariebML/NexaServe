#!/usr/bin/env python3
"""Expand DEPI FAQ with new categories."""
import subprocess
import json

new_faqs = [
    {
        "category": "depi_grants",
        "question_ar": "ما هي المنح والتمويل المتاح لطلاب مبادرة الرواد الرقميون؟",
        "answer_ar": "مبادرة الرواد الرقميون (DEPI) ممولة بالكامل من الدولة.\n- لا رسوم دراسية لجميع البرامج.\n- بدل إقامة يومي شامل الوجبات.\n- تغطية تكاليف النقل للطلاب من خارج القاهرة.\n- جوائز مالية للمتفوقين.\n- دعم شراء الأجهزة التقنية للطلاب المحتاجين.",
        "keywords_ar": ["منحة", "تمويل", "رسوم", "إقامة", "بدل", "جوائز", "أجهزة", "تمويل"],
        "question": "What grants and funding are available for DEPI students?",
        "answer": "DEPI is fully state-funded: no tuition fees, daily meal/boarding allowance, transport coverage for non-Cairo students, cash prizes for top performers, and device support for needy students.",
        "keywords": ["grants", "funding", "scholarship", "tuition", "allowance", "prizes"]
    },
    {
        "category": "depi_lms_platform",
        "question_ar": "ما هي المنصة التعليمية (LMS) المستخدمة في DEPI؟",
        "answer_ar": "تستخدم مبادرة الرواد الرقميون منصة LMS متكاملة تقدم:\n- المحاضرات والفيديوهات التعليمية\n- الواجبات والاختبارات الإلكترونية\n- نظام الحضور والإجازات\n- التواصل بين الطلاب والمدربين\n- لوحة التحكم الشخصية لكل طالب\n\nالدعم الفني: info@depi.gov.eg",
        "keywords_ar": ["LMS", "المنصة التعليمية", "المحاضرات", "الواجبات", "الاختبارات", "الحضور", "الإجازات"],
        "question": "What LMS platform does DEPI use for online learning?",
        "answer": "DEPI uses a comprehensive LMS featuring video lectures, e-assessments, attendance tracking, student-instructor communication, and personal dashboards. Support: info@depi.gov.eg",
        "keywords": ["LMS", "e-learning", "platform", "video", "assessment", "attendance"]
    },
    {
        "category": "depi_international_partnerships",
        "question_ar": "ما هي الشراكات الدولية لمبادرة الرواد الرقميون؟",
        "answer_ar": "تتعاون مبادرة DEPI مع جامعات وشركات تقنية عالمية:\n- جامعات في ألمانيا وبريطانيا وكندا\n- شراكات مع مايكروسوفت وغوغل وأمازون\n- برامج تبادل ثقافي وتدريب مشترك\n- اعتمادات دولية للشهادات\n- مشاريع بحثية مشتركة",
        "keywords_ar": ["شراكات", "دولية", "جامعات", "شركات", "تقنية", "تبادل", "اعتمادات", "بحث"],
        "question": "What international partnerships does DEPI have?",
        "answer": "DEPI partners with universities in Germany, UK, Canada and tech companies like Microsoft, Google, and Amazon for joint programs, certifications, and research.",
        "keywords": ["partnerships", "international", "universities", "Microsoft", "Google", "certifications"]
    },
    {
        "category": "depi_evaluation_criteria",
        "question_ar": "ما هي معايير تقييم الطلاب في مبادرة الرواد الرقميون؟",
        "answer_ar": "يتم تقييم الطلاب وفقاً لمعايير متعددة:\n- الاختبارات الإلكترونية: 30%\n- المشاريع التطبيقية: 30%\n- الحضور والمشاركة: 15%\n- الامتحان النهائي: 25%\n\nالحد الأدنى للنجاح: 60%\nالتقديرات: ممتاز (90+)، جيد جداً (80+)، جيد (70+)، مقبول (60+)",
        "keywords_ar": ["تقييم", "امتحانات", "اختبارات", "مشاريع", "حضور", "تقديرات", "نجاح", "درجات"],
        "question": "What are the student evaluation criteria in DEPI?",
        "answer": "Evaluation: E-tests 30%, projects 30%, attendance 15%, final exam 25%. Minimum passing: 60%. Grades: Excellent (90+), Very Good (80+), Good (70+), Pass (60+).",
        "keywords": ["evaluation", "grading", "exams", "projects", "attendance", "criteria"]
    }
]

print("Adding 4 new FAQ categories to seed_depi_faq.py...")

# Read the existing file
with open('scripts/seed_depi_faq.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the faqs list and add new entries before the closing bracket
# We'll insert new FAQ entries before the last few lines of the list
insert_text = ""
for faq in new_faqs:
    insert_text += ",\n"
    insert_text += "    {\n"
    insert_text += f'        "category": "{faq["category"]}",\n'
    insert_text += f'        "question_ar": """{faq["question_ar"]}""",\n'
    insert_text += f'        "answer_ar": """{faq["answer_ar"]}""",\n'
    insert_text += f'        "keywords_ar": {json.dumps(faq["keywords_ar"])},\n'
    insert_text += f'        "question": "{faq["question"]}",\n'
    insert_text += f'        "answer": "{faq["answer"]}",\n'
    insert_text += f'        "keywords": {json.dumps(faq["keywords"])}\n'
    insert_text += "    }"

# Find the last entry before the for loop
marker = '    },\n]\n\nfor f in faqs:'
if marker in content:
    content = content.replace(marker, '    },' + insert_text + '\n]\n\nfor f in faqs:')
    with open('scripts/seed_depi_faq.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully added new FAQ categories!")
else:
    # Try alternative marker
    marker2 = '    }\n]\n'
    if marker2 in content:
        content = content.replace(marker2, '    },' + insert_text + '\n]\n')
        with open('scripts/seed_depi_faq.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully added new FAQ categories (v2)!")
    else:
        print("Could not find insertion point. Manual update needed.")

print(f"New categories: {[f['category'] for f in new_faqs]}")
