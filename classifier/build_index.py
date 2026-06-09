import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

df = pd.read_csv('classifier/data/labeled_data_090626.csv')
model = SentenceTransformer('sergeyzh/rubert-mini-frida', trust_remote_code=True)
embeddings = model.encode(df['Goal'].tolist(), show_progress_bar=True)
dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(embeddings.astype(np.float32))
faiss.write_index(index, 'classifier/data/goal_index.faiss')
print("Индекс FAISS сохранён.")