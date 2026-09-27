"""Export non-secret per-row provenance/embedding inventory for the forensic audit."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from db_config import get_db_connection  # noqa: E402

output = ROOT / "logs" / "runtime_forensic" / "knowledge_base_traceability.csv"
conn = get_db_connection()
try:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id,program,category,source_attribution,source_url,content_hash,
                      created_at,is_active,embedding IS NOT NULL,vector_dims(embedding),
                      question_ar,answer_ar
                 FROM knowledge_base ORDER BY id"""
        )
        rows = cur.fetchall()
finally:
    conn.close()
with output.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow([
        "id", "program", "category", "source_attribution", "source_url", "content_hash",
        "created_at", "is_active", "embedding_present", "embedding_dimensions",
        "question_ar", "answer_ar", "updated_at_column_present", "embedding_model_metadata_present",
    ])
    for row in rows:
        writer.writerow([*row, False, False])
print(f"Exported {len(rows)} KB records to {output}")
