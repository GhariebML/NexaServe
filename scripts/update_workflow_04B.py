import json
import os

file_path = os.path.join("..", "infra", "n8n", "workflows", "04B_knowledge_base_faq.json")

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Create the new Generate Embedding node
embedding_node = {
    "id": "node-generate-embedding",
    "name": "Generate Embedding",
    "type": "n8n-nodes-base.httpRequest",
    "position": [430, 300],
    "parameters": {
        "url": "http://host.docker.internal:11434/api/embed",
        "method": "POST",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: 'nomic-embed-text', input: $('Program Detector & Query Normalizer').first().json.cleaned_message || $('Program Detector & Query Normalizer').first().json.customer_message }) }}"
    },
    "typeVersion": 4.2
}

# Insert into nodes
# Find index of Query Bilingual Knowledge Base
kb_index = -1
for i, n in enumerate(data["nodes"]):
    if n["name"] == "Query Bilingual Knowledge Base":
        kb_index = i
        break

if kb_index != -1:
    data["nodes"].insert(kb_index, embedding_node)
    
    # Update the query inside the kb node
    query_str = """=WITH words AS (
  SELECT lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) AS word
  FROM unnest(string_to_array('{{ ($('Program Detector & Query Normalizer').first().json.cleaned_message || $('Program Detector & Query Normalizer').first().json.customer_message || "").replace(/'/g, "''") }}', ' ')) w
  WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2
), scored AS (
  SELECT id, program, category, question, answer, question_ar, answer_ar, source_attribution,
    (SELECT count(*) * 10 FROM words WHERE question_ar ILIKE '%' || word || '%' OR question ILIKE '%' || word || '%')
    + (SELECT count(*) * 5 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw = word) OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw = word))
    + (SELECT count(*) * 2 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%' || word || '%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%' || word || '%'))
    + (SELECT count(*) FROM words WHERE answer_ar ILIKE '%' || word || '%' OR answer ILIKE '%' || word || '%') AS lexical_score,
    (1 - (embedding <=> '[{{ $json.embeddings[0].join(",") }}]')) * 50 AS semantic_score,
    (SELECT count(*) FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%' || word || '%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%' || word || '%')) AS keyword_match_count,
    (SELECT count(*) FROM words WHERE question_ar ILIKE '%' || word || '%' OR answer_ar ILIKE '%' || word || '%') AS content_match_count
  FROM knowledge_base
  WHERE is_active = TRUE AND {{ $('Program Detector & Query Normalizer').first().json.program_filter }}
)
SELECT id, program, category, question, answer, question_ar, answer_ar, source_attribution, (lexical_score + COALESCE(semantic_score, 0)) as relevance_score, keyword_match_count, content_match_count
FROM scored
WHERE (lexical_score + COALESCE(semantic_score, 0)) > 30
ORDER BY relevance_score DESC, keyword_match_count DESC, id ASC
LIMIT 5;"""
    
    data["nodes"][kb_index + 1]["parameters"]["query"] = query_str
    
# Update connections
connections = data["connections"]
if "Program Detector & Query Normalizer" in connections:
    connections["Program Detector & Query Normalizer"]["main"] = [[{"node": "Generate Embedding", "type": "main", "index": 0}]]

connections["Generate Embedding"] = {
    "main": [
        [
            {
                "node": "Query Bilingual Knowledge Base",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Updated 04B workflow!")
