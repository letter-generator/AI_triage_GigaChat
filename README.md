
<p align="center">
  <img src="https://img.icons8.com/color/96/000000/artificial-intelligence.png" alt="AI Logo" width="80px" height="80px">
</p>
<h1 align="center"> AI Triage GigaChat </h1>
<h3 align="center"> Система автоматической классификации ответов LLM «ГигаЧат» </h3>

<br/>

<p align="center">
  <img src="https://media.giphy.com/media/LmNwrBhejkK9EFP504/giphy.gif" alt="AI animation" width="40%" height="40%">
</p>

<h2 id="table-of-contents"> :book: Навигация</h2>

<details open="open">
  <summary>Содержание</summary>
  <ol>
    <li><a href="#about"> ➤ О проекте</a></li>
    <li><a href="#functions"> ➤ Функциональные возможности</a></li>
    <li><a href="#architecture"> ➤ Архитектура</a></li>
    <li><a href="#tech"> ➤ Стек технологий</a></li>
    <li><a href="#structure"> ➤ Структура проекта</a></li>
    <li><a href="#setup"> ➤ Установка и запуск</a></li>
    <li><a href="#config"> ➤ Конфигурация</a></li>
    <li><a href="#models"> ➤ Используемые модели</a></li>
    <li><a href="#links"> ➤ Ссылки</a></li>
    <li><a href="#contributors"> ➤ Участники</a></li>
  </ol>
</details>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="about"> :small_orange_diamond: О проекте</h2>

<p align="justify">
  Программный комплекс предназначен для автоматической оценки безопасности ответов нейросетевой модели GigaChat. Система анализирует диалоги, выделяет ответы, нарушающие цензурные требования, и предоставляет инструменты для ручной верификации.
</p>
<p align="justify">
  Частота релизов GigaChat растёт, ручная проверка ответов на соответствие нормам дорогая и не масштабируется. Разработанное решение позволяет автоматизировать обнаружение подозрительных ответов и организовать triage с участием человека-эксперта.
</p>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="functions"> :small_orange_diamond: Функциональные возможности</h2>

<ul>
  <li>Организация чата с моделью GigaChat с потоковой передачей ответов.</li>
  <li>Классификация ответов с присвоением меток «хороший» (0) или «плохой» (1).</li>
  <li>Построчное пояснение причины классификации.</li>
  <li>Анализ токсичности с использованием локальной модели Tinkoff.</li>
  <li>Поиск релевантных примеров из размеченного датасета (RAG).</li>
  <li>Поиск фрагментов документа с цензурными требованиями.</li>
  <li>Поддержка нескольких независимых диалогов (сессий).</li>
  <li>Сохранение истории диалогов в базе данных SQLite.</li>
  <li>Экспорт истории в форматах CSV, JSON, TXT, XLSX.</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="architecture"> :small_orange_diamond: Архитектура</h2>

<p align="justify">
  Система построена по модульному принципу. Взаимодействие компонентов организовано через центральный модуль <code>app.py</code>. Все зависимости вынесены в файл <code>requirements.txt</code>. Конфигурационные параметры хранятся в <code>config.py</code>.
</p>

<h3>Состав компонентов</h3>

<ul>
  <li><code>app.py</code> – управление интерфейсом пользователя, обработка запросов к GigaChat, координация работы классификаторов.</li>
  <li><code>database.py</code> – создание и обслуживание таблиц SQLite, операции с сессиями и сообщениями.</li>
  <li><code>classifier/retrieval.py</code> – поиск ближайших соседей в FAISS-индексах.</li>
  <li><code>classifier/model_vm.py</code> – отправка запросов к удалённой LLM (Ollama) и парсинг ответов.</li>
  <li><code>classifier/model_toxicity.py</code> – локальный анализ токсичности.</li>
  <li><code>classifier/build_index.py</code> – построение FAISS-индекса для размеченного датасета.</li>
  <li><code>classifier/build_index_doc.py</code> – построение FAISS-индекса для документа цензурных правил.</li>
  <li><code>style.css</code> – каскадные таблицы стилей.</li>
</ul>

<h3>Логика работы</h3>

<ol>
  <li>Пользователь вводит запрос в веб-интерфейсе.</li>
  <li>Приложение передаёт запрос в API GigaChat и получает ответ.</li>
  <li>Модуль <code>model_toxicity.py</code> анализирует ответ.</li>
  <li>Модуль <code>retrieval.py</code> извлекает из индексов три похожих примера и два релевантных фрагмента правил.</li>
  <li>Модуль <code>model_vm.py</code> формирует промпт, включающий примеры, правила и результат токсичности, и отправляет его в LLM.</li>
  <li>LLM возвращает метку и пояснение.</li>
  <li>Результат сохраняется в базе данных и отображается пользователю.</li>
</ol>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="tech"> :small_orange_diamond: Стек технологий</h2>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.56%2B-red?style=for-the-badge&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/Transformers-HuggingFace-yellow?style=for-the-badge&logo=huggingface" alt="Hugging Face">
  <img src="https://img.shields.io/badge/FAISS-Facebook-blue?style=for-the-badge&logo=facebook" alt="FAISS">
  <img src="https://img.shields.io/badge/SQLite-3-blue?style=for-the-badge&logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/Ollama-LLM-brightgreen?style=for-the-badge" alt="Ollama">
</p>

<ul>
  <li><strong>Python 3.10+</strong> – основной язык разработки</li>
  <li><strong>Streamlit</strong> – веб-интерфейс и интерактивный чат</li>
  <li><strong>GigaChat API (Сбер)</strong> – генерация ответов LLM</li>
  <li><strong>Sentence Transformers</strong> – эмбеддинги для RAG (FRIDA / rubert‑mini‑frida)</li>
  <li><strong>FAISS</strong> – индексный поиск похожих примеров и цензурных правил</li>
  <li><strong>Hugging Face Transformers</strong> – локальная модель токсичности (Tinkoff)</li>
  <li><strong>SQLite</strong> – хранение истории диалогов и сессий</li>
  <li><strong>Pandas / NumPy</strong> – обработка данных и экспорт в CSV/Excel</li>
  <li><strong>Requests / JSON</strong> – взаимодействие с внешними API</li>
  <li><strong>Ollama</strong> – локальный запуск LLM (Saiga, Qwen и др.)</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="structure"> :small_orange_diamond: Структура проекта</h2>

```
AI_triage_GigaChat/
├── app.py                      # Главное приложение Streamlit
├── database.py                 # Модели SQLite (сессии, сообщения)
├── config.py                   # Конфигурационные пути
├── style.css                   # Кастомные CSS-стили
├── requirements.txt            # Зависимости
├── README.md
├── classifier/
│   ├── retrieval.py            # RAG: поиск по индексам
│   ├── build_index.py          # Построение индекса датасета
│   ├── build_index_doc.py      # Построение индекса правил
│   ├── model_toxicity.py       # Локальная токсичность (Tinkoff)
│   ├── model_vm.py             # Классификатор через Ollama
│   ├── model_or.py             # Классификатор через OpenRouter
│   └── data/
│       ├── labeled_data.csv
│       ├── goal_index.faiss
│       ├── censorship_rules.txt
│       ├── doc_index.faiss
│       └── doc_chunks.csv
└── chat_history.db             # База данных (создаётся при первом запуске)
```

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="setup"> :small_orange_diamond: Установка и запуск</h2>

<h3>Требования к среде</h3>
<ul>
  <li>Операционная система Windows, Linux или macOS.</li>
  <li>Python версии 3.10 или выше.</li>
  <li>Установленный менеджер пакетов pip.</li>
  <li>Виртуальная машина с запущенным сервером Ollama и установленной моделью (например, <code>akdengi/saiga-llama3-8b</code>).</li>
  <li>Действующий API-ключ GigaChat (Base64 от client_id:client_secret).</li>
</ul>

<h3>Инструкция по установке</h3>

<ol>
  <li>Клонирование репозитория:
    <pre><code>git clone https://github.com/letter-generator/AI_triage_GigaChat.git
cd AI_triage_GigaChat</code></pre>
  </li>
  <li>Создание и активация виртуального окружения:
    <pre><code>python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows</code></pre>
  </li>
  <li>Установка зависимостей:
    <pre><code>pip install -r requirements.txt</code></pre>
  </li>
  <li>Подготовка данных:
    <ul>
      <li>Поместить файл <code>labeled_data.csv</code> (колонки <code>Goal</code>, <code>Target</code>, <code>Label</code>) в каталог <code>classifier/data/</code>.</li>
      <li>Поместить файл <code>censorship_rules.txt</code> в кодировке UTF-8 в тот же каталог.</li>
    </ul>
  </li>
  <li>Построение поисковых индексов:
    <pre><code>python classifier/build_index.py
python classifier/build_index_doc.py</code></pre>
  </li>
  <li>Настройка подключения к LLM:
    <ul>
      <li>В файле <code>classifier/qwen.py</code> указать значения <code>QWEN_VM_URL</code> и <code>QWEN_MODEL_NAME</code>.</li>
      <li>Убедиться, что сервер Ollama на ВМ доступен по указанному адресу и порту 11434.</li>
    </ul>
  </li>
  <li>Запуск приложения:
    <pre><code>streamlit run app.py --server.port 8501</code></pre>
  </li>
  <li>Открыть в браузере адрес <code>http://localhost:8501</code>, ввести API-ключ GigaChat и начать диалог.</li>
</ol>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="config"> :small_orange_diamond: Конфигурация</h2>

<p>
  Основные настройки расположены в файле <code>config.py</code>:
</p>
<ul>
  <li><code>BASE_DIR</code> – корневой каталог проекта.</li>
  <li><code>DATA_DIR</code> – каталог для хранения данных.</li>
  <li><code>DB_PATH</code> – путь к файлу базы данных SQLite.</li>
  <li><code>DATASET_PATH</code> – путь к размеченному датасету.</li>
  <li><code>FAISS_DIR</code> – каталог для FAISS-индексов.</li>
</ul>

<p>
  Параметры подключения к LLM задаются непосредственно в <code>classifier/qwen.py</code>:
</p>
<ul>
  <li><code>VM_URL</code> – адрес ВМ с Ollama.</li>
  <li><code>MODEL_NAME</code> – идентификатор модели.</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="models"> :small_orange_diamond: Используемые модели</h2>

<ul>
  <li><strong>Эмбеддер для RAG</strong>: <code>ai-forever/FRIDA</code> (русскоязычный). Допустима замена на <code>sergeyzh/rubert-mini-frida</code>.</li>
  <li><strong>Анализ токсичности</strong>: <code>tinkoff-ai/response-toxicity-classifier-base</code>.</li>
  <li><strong>LLM-классификатор</strong>: <code>akdengi/saiga-llama3-8b</code> (устанавливается через Ollama). Альтернативно <code>huihui_ai/qwen2.5-abliterate:7b</code>.</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="links"> :small_orange_diamond: Ссылки</h2>

<ul>
  <li><a href="https://github.com/letter-generator/AI_triage_GigaChat">GitHub-репозиторий проекта</a></li>
  <li><a href="https://developers.sber.ru/">GigaChat API (Сбер)</a></li>
  <li><a href="https://openrouter.ai/">OpenRouter – доступ к LLM</a></li>
  <li><a href="https://ollama.com/">Ollama – локальный запуск моделей</a></li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="contributors"> :small_orange_diamond: Участники</h2>

<p>
  <i>Проект выполнен студентами программы «Алгоритмы искусственного интеллекта» Института радиоэлектроники и информационных технологий — РТФ Уральского федерального университета имени Б. Н. Ельцина.</i>
</p>

<ul>
  <li><strong>Алымова Светлана Олеговна</strong> – аналитик</li>
  <li><strong>Ляпин Семён Николаевич</strong> – разработчик</li>
  <li><strong>Молчанова Полина Алексеевна</strong> – руководитель команды</li>
  <li><strong>Пластеева Ксения Евгеньевна</strong> – разработчик</li>
  <li><strong>Ступаченко Екатерина Евгеньевна</strong> – разработчик, тимлид</li>
  <li><strong>Тетенькина Екатерина Владимировна</strong> – разработчик</li>
  <li><strong>Филипович Илья Андреевич</strong> – разработчик</li>
</ul>

<p>
  <strong>Куратор проекта:</strong> Домуховский Николай Анатольевич (ПАО Сбербанк)
</p>

<p>
  <i>Учебный проект, реализованный в рамках дисциплины «Проектный практикум». Команда «Генератор букв».<br>
  Июнь 2026 г.</i>
</p>
