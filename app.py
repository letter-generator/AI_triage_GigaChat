import ast
import json
import traceback
from datetime import datetime
from typing import Optional

import requests
import streamlit as st

try:
    from classifier.retrieval import retrieve_similar_goals
except Exception:
    def retrieve_similar_goals(*args, **kwargs):
        return []

from classifier.model_or import classify_with_openrouter
from classifier.model_toxicity import analyze_toxicity
from database import (
    create_session,
    delete_session,
    export_session_messages,
    get_all_sessions,
    get_messages,
    init_db,
    rename_session,
    save_message,
)
from supabase_client import get_unprocessed_prompts, save_classification_result


# ---------- CSS ----------
def load_css():
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css()
init_db()


# ---------- Инициализация состояния ----------
if "current_session_id" not in st.session_state:
    sessions = get_all_sessions()
    st.session_state.current_session_id = sessions[0][0] if sessions else create_session()

if "sessions_list" not in st.session_state:
    st.session_state.sessions_list = get_all_sessions()

if "messages_cache" not in st.session_state:
    st.session_state.messages_cache = {}

if "gigachat_token" not in st.session_state:
    st.session_state.gigachat_token = None

if "gigachat_api_key" not in st.session_state:
    st.session_state.gigachat_api_key = ""

# Дефолты для модели — чтобы не было NameError вне sidebar
if "openrouter_model" not in st.session_state:
    st.session_state.openrouter_model = "google/gemini-2.0-flash-exp:free"

if "gigachat_version" not in st.session_state:
    st.session_state.gigachat_version = "GigaChat 1.0.0"


def refresh_sessions():
    st.session_state.sessions_list = get_all_sessions()


def switch_chat(session_id):
    st.session_state.current_session_id = session_id
    st.rerun()


def create_new_chat():
    new_id = create_session()
    refresh_sessions()
    st.session_state.current_session_id = new_id
    st.rerun()


def delete_chat(sid):
    delete_session(sid)
    refresh_sessions()
    if st.session_state.current_session_id == sid:
        sessions = st.session_state.sessions_list
        st.session_state.current_session_id = (
            sessions[0][0] if sessions else create_session()
        )
    st.rerun()


def rename_current_chat(new_name):
    rename_session(st.session_state.current_session_id, new_name)
    refresh_sessions()
    st.rerun()


# ---------- Токен GigaChat ----------
def get_gigachat_token(auth_key: str) -> Optional[str]:
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Authorization": f"Basic {auth_key}",
        "RqUID": "6f0b1291-c7f3-43d6-8b9e-6f2b4d4e6f8a",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        st.error(f"Ошибка получения токена GigaChat: {e}")
        return None


def ensure_token() -> Optional[str]:
    if not st.session_state.gigachat_token:
        with st.spinner("Получение токена GigaChat..."):
            token = get_gigachat_token(st.session_state.gigachat_api_key)
        if token:
            st.session_state.gigachat_token = token
        else:
            st.error("Не удалось получить токен GigaChat. Проверьте API-ключ.")
            return None
    return st.session_state.gigachat_token


def refresh_token() -> Optional[str]:
    with st.spinner("Обновление токена GigaChat..."):
        token = get_gigachat_token(st.session_state.gigachat_api_key)
    if token:
        st.session_state.gigachat_token = token
        return token
    st.error("Не удалось обновить токен GigaChat.")
    return None


# ---------- Синхронный вызов GigaChat (для пакетной обработки) ----------
def call_gigachat_sync(prompt: str) -> str:
    token = ensure_token()
    if not token:
        return ""
    messages = [{"role": "user", "content": prompt}]
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "GigaChat",
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 401:
            new_token = refresh_token()
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(url, headers=headers, json=payload, verify=False)
            else:
                return ""
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"Ошибка при вызове GigaChat: {e}")
        return ""


# ---------- Потоковый вызов GigaChat (для интерактивного режима) ----------
def gigachat_stream(messages: list, access_token: str):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "GigaChat",
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    try:
        response = requests.post(
            url, headers=headers, json=payload, stream=True, verify=False
        )
        if response.status_code == 401:
            yield ("", False, True)
            return
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                content = (
                    chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                )
                if content:
                    yield (content, False, False)
            except json.JSONDecodeError:
                continue
    except Exception as e:
        yield (f"Ошибка при вызове GigaChat: {e}", True, False)


def call_gigachat(api_messages: list) -> tuple:
    token = ensure_token()
    if not token:
        return "", False

    response_placeholder = st.empty()
    full_response = ""

    def _do_stream(tok):
        nonlocal full_response
        full_response = ""
        for chunk, is_error, need_reauth in gigachat_stream(api_messages, tok):
            if need_reauth:
                return "REAUTH"
            if is_error:
                st.error(chunk)
                return "ERROR"
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")
        return "OK"

    result = _do_stream(token)

    if result == "REAUTH":
        new_token = refresh_token()
        if not new_token:
            response_placeholder.markdown("Не удалось обновить токен GigaChat.")
            return "", False
        result = _do_stream(new_token)

    if result == "ERROR":
        response_placeholder.markdown(full_response or "Ошибка при получении ответа.")
        return full_response, False

    if not full_response.strip():
        response_placeholder.markdown("Нет ответа от GigaChat.")
        return "", False

    response_placeholder.markdown(full_response)
    return full_response, True


# ---------- Вспомогательная функция парсинга ID ----------
def parse_id_list(raw: str) -> list:
    """Парсит строку вида '5,12,34-56' в список целых чисел."""
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part.count("-") == 1 and not part.startswith("-"):
            try:
                start, end = map(int, part.split("-"))
                result.extend(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                result.append(int(part))
            except ValueError:
                pass
    return result


# ---------- Боковая панель ----------
with st.sidebar:
    st.header("☰ История чатов")
    if st.button("✚ Новый чат", use_container_width=True):
        create_new_chat()
    st.markdown("---")

    for sid, name, start_time in st.session_state.sessions_list:
        is_active = sid == st.session_state.current_session_id
        display_name = f"▸ {name}" if is_active else name
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(display_name, key=f"chat_{sid}", use_container_width=True):
                switch_chat(sid)
        with col2:
            if st.button("🗑", key=f"del_{sid}", help="Удалить чат"):
                delete_chat(sid)

    st.markdown("---")
    df_exp = export_session_messages(st.session_state.current_session_id)
    if not df_exp.empty:
        csv_data = df_exp.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⭳ CSV",
            data=csv_data,
            file_name=(
                f"chat_{st.session_state.current_session_id[:8]}"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            ),
            mime="text/csv",
        )
    else:
        st.info("Нет данных для экспорта")

    st.markdown("---")
    st.header("Автоматическая обработка")

    openrouter_model = st.text_input(
        "Модель OpenRouter",
        value=st.session_state.openrouter_model,
        help="Название модели для классификатора",
    )
    gigachat_version = st.text_input(
        "Версия GigaChat",
        value=st.session_state.gigachat_version,
        help="Версия модели GigaChat",
    )
    # Сохраняем чтобы использовать вне sidebar
    st.session_state.openrouter_model = openrouter_model
    st.session_state.gigachat_version = gigachat_version

    # ---------- Фильтры ----------
    with st.expander("Фильтры", expanded=False):

        # — Даты —
        st.caption("ПЕРИОД")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            date_from = st.date_input("Дата от", value=None)
        with col_d2:
            date_to = st.date_input("Дата до", value=None)
        st.markdown(
            "<div style='display:flex;gap:8px;margin-top:-8px;"
            "font-size:0.72rem;color:rgba(150,170,210,0.6)'>"
            "<span style='flex:1;text-align:center'>Дата от</span>"
            "<span style='flex:1;text-align:center'>Дата до</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)

        # — Фильтр по ID —
        st.caption("ФИЛЬТР ПО ID")
        id_filter_type = st.radio(
            "id_type", ["Диапазон", "Список"], horizontal=True, label_visibility="collapsed"
        )
        if id_filter_type == "Диапазон":
            col_id1, col_id2 = st.columns(2)
            with col_id1:
                id_from = st.number_input("ID от", min_value=1, value=None, step=1,
                                          label_visibility="collapsed")
            with col_id2:
                id_to = st.number_input("ID до", min_value=1, value=None, step=1,
                                        label_visibility="collapsed")
            st.markdown(
                "<div style='display:flex;gap:8px;margin-top:-8px;"
                "font-size:0.72rem;color:rgba(150,170,210,0.6)'>"
                "<span style='flex:1;text-align:center'>ID от</span>"
                "<span style='flex:1;text-align:center'>ID до</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            id_list = None
        else:
            id_list_input = st.text_input(
                "id_list_raw",
                placeholder="5, 12, 34-56",
                help="Отдельные ID и диапазоны через дефис",
                label_visibility="collapsed",
            )
            id_list = parse_id_list(id_list_input) if id_list_input else []
            id_from = None
            id_to = None

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)

        # — Тип мутации —
        st.caption("ТИП МУТАЦИИ")
        mutation_types = [
            "",
            "contextual_obfuscation",
            "role_play_virtualization",
            "multi_step_escalation",
            "linguistic_obfuscation",
            "token_smuggling",
            "system_mode",
            "hypothetical_scenario",
        ]
        mutation_type = st.selectbox(
            "mutation", mutation_types, index=0, label_visibility="collapsed"
        )

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)

        # — Статус и метка —
        st.caption("СТАТУС ОБРАБОТКИ")
        processed_status = st.selectbox(
            "status",
            ["unprocessed", "processed", "all"],
            format_func=lambda x: {
                "unprocessed": "Только необработанные",
                "processed":   "Только обработанные",
                "all":         "Все",
            }[x],
            index=0,
            label_visibility="collapsed",
        )

        label_filter = None
        if processed_status != "unprocessed":
            st.caption("МЕТКА КЛАССИФИКАЦИИ")
            label_filter = st.selectbox(
                "label",
                [None, 0, 1, -1],
                format_func=lambda x: {
                    None: "Все",
                    0:    "Хорошие (label=0)",
                    1:    "Плохие  (label=1)",
                    -1:   "Ошибки  (label=-1)",
                }[x],
                index=0,
                label_visibility="collapsed",
            )

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)

        # — Лимит и сортировка —
        st.caption("ЛИМИТ И СОРТИРОВКА")
        limit = st.number_input(
            "Максимум промтов", min_value=1, max_value=1000, value=None, step=1
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            order_by = st.selectbox(
                "order_by", ["id", "created_at"], index=0, label_visibility="collapsed"
            )
        with col_s2:
            order_direction = st.selectbox(
                "order_dir",
                ["asc", "desc"],
                format_func=lambda x: "↑ Возр." if x == "asc" else "↓ Убыв.",
                index=0,
                label_visibility="collapsed",
            )
        st.markdown(
            "<div style='display:flex;gap:8px;margin-top:-8px;"
            "font-size:0.72rem;color:rgba(150,170,210,0.6)'>"
            "<span style='flex:1;text-align:center'>Поле</span>"
            "<span style='flex:1;text-align:center'>Порядок</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ---------- Кнопка запуска ----------
    if st.button("  ▶  ", use_container_width=True):
        filter_params = {
            "processed_status": processed_status,
            "order_by": order_by,
            "order_direction": order_direction,
        }
        if date_from:
            filter_params["date_from"] = date_from.isoformat()
        if date_to:
            filter_params["date_to"] = date_to.isoformat()
        if mutation_type:
            filter_params["mutation_type"] = mutation_type
        if limit:
            filter_params["limit"] = limit
        if id_from:
            filter_params["id_from"] = id_from
        if id_to:
            filter_params["id_to"] = id_to
        if id_list:
            filter_params["id_list"] = id_list
        if label_filter is not None:
            filter_params["label_filter"] = label_filter

        with st.spinner("Загрузка промтов..."):
            prompts = get_unprocessed_prompts(**filter_params)

        if not prompts:
            st.info("Нет промтов для обработки (с учётом фильтров).")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            successful = []
            failed = []
            stats = {
                "total": len(prompts),
                "success": 0,
                "errors": 0,
                "label_0": 0,
                "label_1": 0,
                "label_minus1": 0,
            }

            for i, p in enumerate(prompts):
                status_text.text(
                    f"Обработка {i + 1}/{stats['total']}: "
                    f"ID {p['id']} — {p['mutated_prompt'][:60]}..."
                )
                response_text = call_gigachat_sync(p["mutated_prompt"])
                progress = (i + 1) / stats["total"]

                if not response_text:
                    failed.append(f"ID {p['id']}: {p['mutated_prompt'][:50]}... (нет ответа)")
                    stats["errors"] += 1
                    progress_bar.progress(progress)
                    continue

                toxicity = analyze_toxicity(response_text)
                context = f"Результат анализа токсичности: {toxicity.get('explanation', '')}"
                similar = retrieve_similar_goals(p["mutated_prompt"], k=3)

                label, reason = classify_with_openrouter(
                    p["mutated_prompt"],
                    response_text,
                    similar,
                    api_key=st.session_state.get("openrouter_api_key", ""),
                    context=context,
                    model_name=st.session_state.openrouter_model,
                )

                save_classification_result(
                    prompt_id=p["id"],
                    mutated_prompt=p["mutated_prompt"],
                    gigachat_response=response_text,
                    label=label,
                    reason=reason,
                    toxicity_details=toxicity,
                    classifier_model=st.session_state.openrouter_model,
                    gigachat_model_version=st.session_state.gigachat_version,
                )

                successful.append(
                    f"ID {p['id']}: {p['mutated_prompt'][:50]}... (метка {label})"
                )
                stats["success"] += 1
                if label == 0:
                    stats["label_0"] += 1
                elif label == 1:
                    stats["label_1"] += 1
                else:
                    stats["label_minus1"] += 1
                progress_bar.progress(progress)

            status_text.text("Обработка завершена!")
            st.success(f"Обработано: {stats['success']} из {stats['total']}")
            if stats["errors"]:
                st.info(f"Ошибок: {stats['errors']}")
            st.markdown("---")
            st.subheader("Распределение меток")
            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                st.metric("✓ 0", stats["label_0"])
            with col_l2:
                st.metric("⚠ 1", stats["label_1"])
            with col_l3:
                st.metric("⍰ -1", stats["label_minus1"])

            with st.expander("Подробности"):
                if successful:
                    st.write("Успешно:")
                    for item in successful:
                        st.write(f"- {item}")
                if failed:
                    st.write("Ошибки:")
                    for item in failed:
                        st.write(f"- {item}")


# ---------- Основная область ----------
st.title("AI-агентная система red teaming и контроль ответов LLM GigaChat")
st.write("Выберите чат слева или создайте новый. Все диалоги сохраняются.")

# ---------- Загрузка сообщений текущей сессии ----------
if st.session_state.current_session_id not in st.session_state.messages_cache:
    msgs = get_messages(st.session_state.current_session_id)
    formatted = []
    for (
        user_prompt, assistant_response, label, reason,
        toxicity_details, classifier_model, gigachat_model_version, ts
    ) in msgs:
        formatted.append({"role": "user", "content": user_prompt})
        tox = None
        if toxicity_details:
            try:
                tox = ast.literal_eval(toxicity_details)
            except Exception:
                tox = None
        formatted.append({
            "role": "assistant",
            "content": assistant_response,
            "label": label,
            "reason": reason,
            "toxicity": tox,
            "classifier_model": classifier_model,
            "gigachat_model_version": gigachat_model_version,
        })
    st.session_state.messages_cache[st.session_state.current_session_id] = formatted

# ---------- Отображение истории ----------
for message in st.session_state.messages_cache[st.session_state.current_session_id]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            msg_label = message.get("label")
            msg_reason = message.get("reason", "не указана")
            if msg_label == 1:
                st.warning(f"⚠ Подозрительный ответ\n\nПричина: {msg_reason}")
            elif msg_label == 0:
                st.success(f"✓ Валидный ответ\n\nПричина: {msg_reason}")
            elif msg_label is not None:
                st.info(f"⍰ Оценка не определена\n\n{msg_reason}")

            tox = message.get("toxicity")
            if tox and isinstance(tox, dict):
                explanation = tox.get("explanation", "")
                if tox.get("label", 0) != 0:
                    st.error(f"**Анализ токсичности.** {explanation}")
                else:
                    st.success(f"**Анализ токсичности.** {explanation}")

# ---------- Поля ввода ключей ----------
gigachat_api_key = st.text_input(
    "GigaChat API Key",
    type="password",
    value="MDE5YmMwODYtMjM0MC03NWU2LThiZWQtYWM4M2RhNGQ4N2UxOjY0MDlhNjgxLWU3ZjktNGNmYi04MDkzLWQyMTkyODBkNjM4NA==",
    key="gigachat_key_input",
)

openrouter_api_key = st.text_input(
    "OpenRouter API Key",
    type="password",
    value="",
    help="Необходим для классификации через OpenRouter",
    key="openrouter_key_input",
)

if not gigachat_api_key:
    st.info("Введите API-ключ GigaChat")
    st.stop()

if not openrouter_api_key:
    st.info("Введите API-ключ OpenRouter")
    st.stop()

st.session_state.openrouter_api_key = openrouter_api_key

if gigachat_api_key != st.session_state.gigachat_api_key:
    st.session_state.gigachat_api_key = gigachat_api_key
    st.session_state.gigachat_token = None

# ---------- Поле ввода нового сообщения ----------
if prompt := st.chat_input("Введите сообщение..."):
    current_cache = st.session_state.messages_cache[st.session_state.current_session_id]

    current_cache.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    api_messages = [
        {"role": m["role"], "content": m["content"]} for m in current_cache
    ]

    with st.chat_message("assistant"):
        full_response, success = call_gigachat(api_messages)

    if not success or not full_response.strip():
        current_cache.pop()
        st.warning("Не удалось получить ответ от GigaChat.")
        st.stop()

    # Анализ токсичности
    toxicity = {"label": None, "explanation": "Анализ не выполнен"}
    try:
        with st.spinner("Анализ токсичности"):
            toxicity = analyze_toxicity(full_response)
    except Exception as e:
        st.warning(f"Анализ токсичности не выполнен: {e}")

    context = f"Результат анализа токсичности: {toxicity.get('explanation', '')}"

    # Классификатор
    label, reason = None, "Классификатор не отработал"
    try:
        with st.spinner("Оценка ответа классификатором"):
            similar = retrieve_similar_goals(prompt, k=3)
            label, reason = classify_with_openrouter(
                prompt,
                full_response,
                similar,
                api_key=openrouter_api_key,
                context=context,
                model_name=st.session_state.openrouter_model,
            )
    except Exception as e:
        st.warning(f"Классификатор не отработал: {e}")
        st.error(traceback.format_exc())

    # Сохранение в кэш
    current_cache.append({
        "role": "assistant",
        "content": full_response,
        "label": label,
        "reason": reason,
        "toxicity": toxicity,
        "classifier_model": st.session_state.openrouter_model,
        "gigachat_model_version": st.session_state.gigachat_version,
    })

    # Сохранение в БД
    save_message(
        session_id=st.session_state.current_session_id,
        user_prompt=prompt,
        assistant_response=full_response,
        label=label,
        reason=reason,
        toxicity_details=toxicity,
        classifier_model=st.session_state.openrouter_model,
        gigachat_model_version=st.session_state.gigachat_version,
    )

    # Вывод результатов
    if label == 1:
        st.warning(f"⚠ Подозрительный ответ\n\nПричина: {reason}")
    elif label == 0:
        st.success(f"✓ Валидный ответ\n\nПричина: {reason}")
    elif label is not None:
        st.info(f"⍰ Оценка не определена\n\n{reason}")

    if isinstance(toxicity, dict):
        explanation = toxicity.get("explanation", "")
        if toxicity.get("label", 0) != 0:
            st.error(f"**Анализ токсичности.** {explanation}")
        else:
            st.success(f"**Анализ токсичности.** {explanation}")

    st.rerun()