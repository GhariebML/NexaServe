import requests

# Test the NEW /api/embed endpoint (Ollama v0.34+)
print("Testing /api/embed (new endpoint)...")
r = requests.post('http://localhost:11434/api/embed', json={
    'model': 'nomic-embed-text',
    'input': 'test embedding for DEPI initiative'
})
data = r.json()
print(f"Status: {r.status_code}")
if 'embeddings' in data:
    emb = data['embeddings'][0]
    print(f"Embedding length: {len(emb)}")
    print(f"First 5 values: {emb[:5]}")
elif 'embedding' in data:
    emb = data['embedding']
    print(f"Embedding length: {len(emb)}")
    print(f"First 5 values: {emb[:5]}")
else:
    print(f"Response: {data}")
