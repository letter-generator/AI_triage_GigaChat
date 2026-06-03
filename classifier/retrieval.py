import numpy as np
import pandas as pd
import faiss
import streamlit as st
from sentence_transformers import SentenceTransformer


@st.cache_resource(show_spinner="Загрузка модели FRIDA...")
def _load_model() -> SentenceTransformer:
    """Загружается один раз за весь жизненный цикл приложения."""
    return SentenceTransformer("sergeyzh/rubert-mini-frida", trust_remote_code=True)


@st.cache_resource(show_spinner="Загрузка индекса целей...")
def _load_goal_resources() -> tuple:
    index = faiss.read_index("classifier/data/goal_index.faiss")
    df = pd.read_csv("classifier/data/labeled_data.csv")
    return index, df


@st.cache_resource(show_spinner="Загрузка индекса документов...")
def _load_doc_resources() -> tuple:
    index = faiss.read_index("classifier/data/doc_index.faiss")
    df = pd.read_csv("classifier/data/doc_chunks.csv", encoding="utf-8")
    return index, df


def retrieve_similar_goals(query_goal: str, k: int = 3) -> list:
    """Возвращает k наиболее похожих примеров из датасета (goal, target, label)."""
    model = _load_model()
    index, df = _load_goal_resources()

    query_vec = model.encode([query_goal])
    distances, indices = index.search(query_vec.astype(np.float32), k)

    examples = []
    for idx in indices[0]:
        if idx < 0 or idx >= len(df):
            continue
        row = df.iloc[idx]
        examples.append({
            "goal": row["Goal"],
            "target": row["Target"],
            "label": int(row["Label"]),
        })
    return examples


def retrieve_similar_chunks(query_goal: str, k: int = 2) -> list:
    """Возвращает k наиболее релевантных фрагментов документа цензурных требований."""
    model = _load_model()
    index, df = _load_doc_resources()

    query_vec = model.encode([query_goal])
    distances, indices = index.search(query_vec.astype(np.float32), k)

    chunks = []
    for idx in indices[0]:
        if idx < 0 or idx >= len(df):
            continue
        chunks.append(df.iloc[idx]["chunk"])
    return chunks