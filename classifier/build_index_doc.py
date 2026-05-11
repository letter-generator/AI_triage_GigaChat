import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import re
import os

DOC_PATH = 'classifier/data/censorship_rules.txt'
INDEX_PATH = 'classifier/data/doc_index.faiss'
CHUNKS_CSV = 'classifier/data/doc_chunks.csv'

model = SentenceTransformer('ai-forever/FRIDA', trust_remote_code=True)

if not os.path.exists(DOC_PATH):
    raise FileNotFoundError(f"Файл с правилами не найден: {DOC_PATH}")

with open(DOC_PATH, 'r', encoding='utf-8') as f:
    text = f.read()

chunks = re.split(r'(?=^## 2\.\d+)', text, flags=re.MULTILINE)
chunks = [ch.strip() for ch in chunks if ch.strip()]
embeddings = model.encode(chunks, show_progress_bar=True)
dim = embeddings.shape[1]

index = faiss.IndexFlatL2(dim)
index.add(embeddings.astype(np.float32))
faiss.write_index(index, INDEX_PATH)
print(f"Индекс сохранён в {INDEX_PATH}")

df_chunks = pd.DataFrame({'chunk': chunks})
df_chunks.to_csv(CHUNKS_CSV, index=False, encoding='utf-8')
print(f"Чанки сохранены в {CHUNKS_CSV}")