import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = "https://cmcaqqxwvmzcvrzfrsdm.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable not set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_unprocessed_prompts(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    mutation_type: Optional[str] = None,
    limit: Optional[int] = None,
    id_from: Optional[int] = None,
    id_to: Optional[int] = None,
    id_list: Optional[List[int]] = None,
    processed_status: str = "unprocessed",
    label_filter: Optional[int] = None,
    order_by: str = "id",
    order_direction: str = "asc",
) -> List[Dict[str, Any]]:
    """
    Возвращает промты из AttacksPromts с учётом всех фильтров.

    Параметры:
        date_from:        дата начала (YYYY-MM-DD) в UTC
        date_to:          дата окончания (YYYY-MM-DD) в UTC
        mutation_type:    тип мутации
        limit:            максимальное количество записей
        id_from:          минимальный ID
        id_to:            максимальный ID
        id_list:          список конкретных ID
        processed_status: "unprocessed" | "processed" | "all"
        label_filter:     0, 1, -1 — только при processed_status != "unprocessed"
        order_by:         "id" | "created_at"
        order_direction:  "asc" | "desc"
    """
    query = supabase.table("AttacksPromts").select(
        "id, mutated_prompt, mutation_type, created_at"
    )

    if date_from:
        query = query.gte("created_at", f"{date_from}T00:00:00.000Z")
    if date_to:
        query = query.lte("created_at", f"{date_to}T23:59:59.999Z")
    if mutation_type:
        query = query.eq("mutation_type", mutation_type)
    if id_from:
        query = query.gte("id", id_from)
    if id_to:
        query = query.lte("id", id_to)
    if id_list:
        query = query.in_("id", id_list)
    if limit:
        query = query.limit(limit)

    query = query.order(order_by, desc=(order_direction == "desc"))
    all_prompts = query.execute().data
    if not all_prompts:
        return []

    # Загружаем только записи по нужным ID — не тянем всю таблицу
    prompt_ids = [p["id"] for p in all_prompts]
    processed_resp = (
        supabase.table("ClassifiedResponses")
        .select("prompt_id, label, created_at")
        .in_("prompt_id", prompt_ids)
        .order("created_at", desc=True)   # сначала самые свежие
        .execute()
    )

    # При дублях берём последнюю классификацию (первая в отсортированном списке)
    processed_map: Dict[int, int] = {}
    for item in processed_resp.data:
        pid = item["prompt_id"]
        if pid not in processed_map:
            processed_map[pid] = item["label"]

    processed_ids = set(processed_map.keys())

    if processed_status == "unprocessed":
        filtered = [p for p in all_prompts if p["id"] not in processed_ids]
    elif processed_status == "processed":
        filtered = [p for p in all_prompts if p["id"] in processed_ids]
    else:
        filtered = all_prompts

    if label_filter is not None and processed_status != "unprocessed":
        filtered = [
            p for p in filtered
            if processed_map.get(p["id"]) == label_filter
        ]

    return filtered


def _serialize_toxicity(toxicity: Any) -> Any:
    """
    Приводит toxicity_details к JSON-сериализуемому типу.
    Конвертирует numpy-скаляры (float32, int64 и т.п.) в нативные Python-типы.
    """
    return json.loads(json.dumps(toxicity, default=lambda x: x.item() if hasattr(x, "item") else str(x)))


def save_classification_result(
    prompt_id: int,
    mutated_prompt: str,
    gigachat_response: str,
    label: int,
    reason: str,
    toxicity_details: Any,
    classifier_model: str,
    gigachat_model_version: str,
) -> bool:
    """
    Сохраняет результат классификации в ClassifiedResponses.
    Возвращает True при успехе, False при ошибке.
    """
    data = {
        "prompt_id": prompt_id,
        "mutated_prompt": mutated_prompt,
        "gigachat_response": gigachat_response,
        "label": label,
        "reason": reason,
        "toxicity_details": _serialize_toxicity(toxicity_details),
        "classifier_model": classifier_model,
        "gigachat_model_version": gigachat_model_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase.table("ClassifiedResponses").insert(data).execute()
        return True
    except Exception as e:
        print(f"[supabase_client] Ошибка сохранения prompt_id={prompt_id}: {e}")
        return False