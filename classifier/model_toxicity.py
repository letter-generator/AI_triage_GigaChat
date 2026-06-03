import torch
import streamlit as st
from typing import Dict, Any
from transformers import AutoTokenizer, AutoModelForSequenceClassification


@st.cache_resource(show_spinner="Загрузка модели токсичности...")
def load_toxicity_model():
    """Загружается один раз за весь жизненный цикл приложения."""
    model_id = "tinkoff-ai/response-toxicity-classifier-base"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    model.eval()
    if torch.cuda.is_available():
        model.cuda()
    return model, tokenizer


def analyze_toxicity(text: str) -> Dict[str, Any]:
    """Анализирует текст и возвращает результат с пояснением."""
    model, tokenizer = load_toxicity_model()

    inputs = tokenizer(
        text,
        max_length=128,
        truncation=True,
        padding=True,
        return_tensors="pt",
    )
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    labels = {
        0: "OK - безопасно",
        1: "TOXIC - оскорбительно",
        2: "SEVERE TOXIC - сильно оскорбительно",
        3: "RISKS - чувствительные темы",
    }
    pred_id = int(probs.argmax())
    pred_label = labels[pred_id]
    confidence = probs[pred_id]

    explanation = f"Модель токсичности: {pred_label}. Уверенность: {confidence:.2%}."

    return {
        "label": pred_id,
        "label_name": pred_label,
        "confidence": float(confidence),
        "explanation": explanation,
        "all_probabilities": {labels[i]: float(p) for i, p in enumerate(probs)},
    }