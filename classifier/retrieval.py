import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


_model = None
_index = None
_df = None

_doc_model = None
_doc_index = None
_doc_df = None

def _load_resources():
    global _model, _index, _df
    if _model is None:
        _model = SentenceTransformer('ai-forever/FRIDA', trust_remote_code=True)
        _index = faiss.read_index('classifier/data/goal_index.faiss')
        _df = pd.read_csv('classifier/data/labeled_data.csv')
    return _model, _index, _df

def retrieve_similar_goals(query_goal: str, k: int = 3):
    """Возвращает k наиболее похожих примеров из датасета (goal, target, label)"""
    model, index, df = _load_resources()
    query_vec = model.encode([query_goal])
    distances, indices = index.search(query_vec.astype(np.float32), k)
    examples = []
    for idx in indices[0]:
        row = df.iloc[idx]
        examples.append({
            'goal': row['Goal'],
            'target': row['Target'],
            'label': int(row['Label'])
        })
    return examples

def _load_doc_resources():
    global _doc_model, _doc_index, _doc_df
    if _doc_model is None:
        _doc_model = SentenceTransformer('ai-forever/FRIDA', trust_remote_code=True)
        _doc_index = faiss.read_index('classifier/data/doc_index.faiss')
        _doc_df = pd.read_csv('classifier/data/doc_chunks.csv', encoding='utf-8')
    return _doc_model, _doc_index, _doc_df

def retrieve_similar_chunks(query_goal: str, k: int = 2):
    """Возвращает k наиболее релевантных фрагментов документа цензурных требований"""
    model, index, df = _load_doc_resources()
    query_vec = model.encode([query_goal])
    distances, indices = index.search(query_vec.astype(np.float32), k)
    chunks = []
    for idx in indices[0]:
        if idx < len(df):
            chunks.append(df.iloc[idx]['chunk'])
    return chunks