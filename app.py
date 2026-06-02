import streamlit as st
import requests
import json
from typing import Optional
from datetime import datetime
import ast


try:
    from classifier.retrieval import retrieve_similar_goals
except Exception:
    def retrieve_similar_goals(*args, **kwargs):
        return []

from classifier.model_or import classify_with_openrouter
from classifier.model_toxicity import analyze_toxicity
from database import (
    init_db, create_session, delete_session, rename_session,
    get_all_sessions, get_messages, save_message, export_session_messages
)

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
        st.session_state.current_session_id = sessions[0][0] if sessions else create_session()
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


# ---------- Вызов GigaChat ----------
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
        response = requests.post(url, headers=headers, json=payload, stream=True, verify=False)

        if response.status_code == 401:
            yield ("", False, True)  # сигнал: токен истёк
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
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
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


# ---------- Боковая панель ----------
with st.sidebar:
    st.header("☰ История чатов")
    if st.button("✚ Новый чат", use_container_width=True):
        create_new_chat()
    st.markdown("---")

    for sid, name, start_time in st.session_state.sessions_list:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(name, key=f"chat_{sid}", use_container_width=True):
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
            file_name=f"chat_{st.session_state.current_session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Нет данных для экспорта")

# ---------- Основная область ----------
st.title("AI-агентная система red teaming и контроль ответов LLM GigaChat")
st.write("Выберите чат слева или создайте новый. Все диалоги сохраняются.")

# ---------- Загрузка сообщений текущей сессии ----------
if st.session_state.current_session_id not in st.session_state.messages_cache:
    msgs = get_messages(st.session_state.current_session_id)
    formatted = []
    for user_prompt, assistant_response, label, reason, toxicity_details, ts in msgs:
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
        })
    st.session_state.messages_cache[st.session_state.current_session_id] = formatted

# ---------- Отображение истории ----------
for message in st.session_state.messages_cache[st.session_state.current_session_id]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            label = message.get("label")
            reason = message.get("reason", "не указана")
            if label == 1:
                st.warning(f"⚠ **Подозрительный ответ**\n\nПричина: {reason}")
            elif label == 0:
                st.success(f"✓ **Валидный ответ**\n\nПричина: {reason}")
            elif label is not None:
                st.info(f"⍰ Оценка не определена\n\n{reason}")

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
    key="openrouter_key_input"
)

if not gigachat_api_key:
    st.info("Пожалуйста, введите API-ключ GigaChat для продолжения.", icon="🔑")
    st.stop()

if not openrouter_api_key:
    st.info("Пожалуйста, введите API-ключ OpenRouter для классификатора.", icon="🔑")
    st.stop()

# Сбрасываем токен при смене ключа GigaChat
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
        {"role": m["role"], "content": m["content"]}
        for m in current_cache
    ]

    with st.chat_message("assistant"):
        full_response, success = call_gigachat(api_messages)

    if not success or not full_response.strip():
        current_cache.pop()
        st.warning("Не удалось получить ответ от GigaChat. Попробуйте ещё раз.")
        st.stop()

    # Анализ токсичности
    toxicity = {"label": None, "explanation": "Анализ не выполнен"}
    try:
        with st.spinner("Анализ токсичности..."):
            toxicity = analyze_toxicity(full_response)
    except Exception as e:
        st.warning(f"Анализ токсичности не выполнен: {e}")

    context = f"Результат анализа токсичности: {toxicity.get('explanation', '')}"

    # Классификатор
    label, reason = None, "Классификатор не отработал"
    try:
        with st.spinner("Оценка ответа классификатором (OpenRouter)..."):
            similar = retrieve_similar_goals(prompt, k=3)
            label, reason = classify_with_openrouter(
                prompt, full_response, similar,
                api_key=openrouter_api_key,
                context=context
            )
    except Exception as e:
        st.warning(f"Классификатор не отработал: {e}")
        st.error(traceback.format_exc())

    # Сохранение
    current_cache.append({
        "role": "assistant",
        "content": full_response,
        "label": label,
        "reason": reason,
        "toxicity": toxicity,
    })

    save_message(
        session_id=st.session_state.current_session_id,
        user_prompt=prompt,
        assistant_response=full_response,
        label=label,
        reason=reason,
        toxicity_details=toxicity,
    )

    # Вывод результатов
    if label == 1:
        st.warning(f"⚠ **Подозрительный ответ**\n\nПричина: {reason}")
    elif label == 0:
        st.success(f"✓ **Валидный ответ**\n\nПричина: {reason}")
    elif label is not None:
        st.info(f"⍰ Оценка не определена\n\n{reason}")

    if isinstance(toxicity, dict):
        explanation = toxicity.get("explanation", "")
        if toxicity.get("label", 0) != 0:
            st.error(f"**Анализ токсичности.** {explanation}")
        else:
            st.success(f"**Анализ токсичности.** {explanation}")

    st.rerun()