import os
from supabase import create_client
from datetime import datetime
from typing import List, Dict, Any, Optional

# Загрузка переменных окружения из .env файла 
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
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    query = supabase.table("AttacksPromts").select("id, mutated_prompt, mutation_type, created_at")
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)
    if mutation_type:
        query = query.eq("mutation_type", mutation_type)
    if limit:
        query = query.limit(limit)
    all_prompts = query.execute().data
    if not all_prompts:
        return []
    processed_resp = supabase.table("ClassifiedResponses").select("prompt_id").execute()
    processed_ids = {item["prompt_id"] for item in processed_resp.data}
    return [p for p in all_prompts if p["id"] not in processed_ids]


def save_classification_result(
    prompt_id: int,
    mutated_prompt: str,
    gigachat_response: str,
    label: int,
    reason: str,
    toxicity_details: Any,
    classifier_model: str,
    gigachat_model_version: str
) -> None:
    data = {
        "prompt_id": prompt_id,
        "mutated_prompt": mutated_prompt,
        "gigachat_response": gigachat_response,
        "label": label,
        "reason": reason,
        "toxicity_details": toxicity_details,
        "classifier_model": classifier_model,
        "gigachat_model_version": gigachat_model_version,
        "created_at": datetime.now().isoformat()
    }
    supabase.table("ClassifiedResponses").insert(data).execute()