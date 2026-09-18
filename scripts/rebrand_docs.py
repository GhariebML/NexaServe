import os

REPLACEMENTS = [
    ("Ministry of Communications and Information Technology (MCIT), Kingdom of Saudi Arabia", "Ministry of Communications and Information Technology, Egypt"),
    ("Kingdom of Saudi Arabia", "Arab Republic of Egypt"),
    ("NexaServe MCIT Enterprise AI Customer Service Platform", "NexaServe DEPI AI Customer Service Platform"),
    ("MCIT Enterprise AI Customer Service Platform", "DEPI AI Customer Service Platform"),
    ("MCIT Enterprise AI Customer Service System", "DEPI AI Customer Service System"),
    ("MCIT AI Customer Service Platform", "DEPI AI Customer Service Platform"),
    ("MCIT AI Customer Service System", "DEPI AI Customer Service System"),
    ("MCIT Tier-2 Support Specialists", "DEPI Tier-2 Support Specialists"),
    ("MCIT Tier-2 Support", "DEPI Tier-2 Support"),
    ("MCIT Citizen Escalations Team", "DEPI Citizen Escalations Team"),
    ("MCIT Citizen Customer Service Notification", "DEPI Citizen Customer Service Notification"),
    ("MCIT Customer Support", "DEPI Customer Support"),
    ("MCIT Official Knowledge Base", "DEPI Official Knowledge Base"),
    ("Internal -- MCIT Confidential", "Internal -- DEPI Confidential"),
    ("MCIT Confidential", "DEPI Confidential"),
    ("Saudi Post (SPL)", "البريد المصري"),
    ("Saudi Post", "البريد المصري"),
    ("SPL-", "EMS-"),
    ("Future Skills Initiative", "Digital Pioneers Initiative (DEPI)"),
    ("Saudi National IDs", "Egyptian National IDs"),
    ("Saudi IBANs", "Egyptian IBANs"),
    ("Saudi National ID", "Egyptian National ID"),
    ("Saudi IBAN", "Egyptian IBAN"),
    ("SAUDI_NATIONAL_ID_MASKED", "EGYPTIAN_NATIONAL_ID_MASKED"),
    ("SAUDI_IBAN_MASKED", "EGYPTIAN_IBAN_MASKED"),
    ("// Saudi National ID", "// Egyptian National ID"),
    ("// Saudi IBAN", "// Egyptian IBAN"),
    ("mcit_enterprise_architecture.png", "depi_enterprise_architecture.png"),
    ("mcit_pipeline_flow.png", "depi_pipeline_flow.png"),
    ("test-mcit-enterprise", "test-depi-enterprise"),
    ("sdaia.gov.sa", "depi.gov.eg"),
    ("mcit.gov.sa", "digilians.gov.eg"),
    ("https://sdaia.gov.sa", "https://depi.gov.eg"),
    ("https://mcit.gov.sa", "https://digilians.gov.eg"),
    ("Aramex", "بريد مصر"),
    ("SPL", "EMS"),
    ("Fahad Al-Harbi", "Karim Hassan"),
    ("Abdullah Rashid", "Karim Hassan"),
    ("abdullah.rashid@mcit.gov.sa", "karim.hassan@digilians.gov.eg"),
    ("Future Skills", "Digital Pioneers Initiative (DEPI)"),
    ("مبادرة مهارات المستقبل", "مبادرة الرواد الرقميون (DEPI)"),
    ("Saudi_welcome_list_ar", "DEPI_welcome_list_ar"),
    ("Saudi_welcome_list_en", "DEPI_welcome_list_en"),
    ("test-mcit", "test-depi"),
    ("MCIT", "DEPI"),
]

DOC_FILES = [
    "README.md",
    "docs/NEXASERVE_SYSTEM_REPORT.md",
    "docs/SYSTEM_WORKFLOW_NODES_REPORT.md",
    "docs/python_equivalents.py",
    "docs/troubleshooting.md",
    "docs/architecture.md",
]

print("Documentation rebranding: Saudi MCIT -> DEPI/Egypt")
print("=" * 60)

for filepath in DOC_FILES:
    if not os.path.exists(filepath):
        print("  SKIP (not found): {}".format(filepath))
        continue
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    original = content
    for old, new in REPLACEMENTS:
        if old in content:
            content = content.replace(old, new)
    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        changes = []
        for old, new in REPLACEMENTS:
            if old in original and new in content:
                changes.append("'{}' -> '{}'".format(old[:35], new[:35]))
        print("  UPDATED: {} ({} changes)".format(filepath, len(changes)))
    else:
        print("  NO CHANGES: {}".format(filepath))

print("\nDone!")