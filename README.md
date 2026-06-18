<p align="center">
  <img src="https://logo-teka.com/wp-content/uploads/2025/07/gigachat-horizontal-logo.png" alt="AI Logo" width="480px" height="270px">
  
</p>
<h1 align="center"> AI-агентная система red teaming и контроль ответов LLM «ГигаЧат» </h1>


<h2 id="table-of-contents"> Навигация</h2>

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
    <li><a href="#contributors"> ➤ Участники</a></li>
  </ol>
</details>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="about"> О проекте</h2>

<p align="justify">
  Программный комплекс предназначен для автоматической оценки безопасности ответов нейросетевой модели GigaChat. Система анализирует диалоги, выделяет ответы, нарушающие цензурные требования, и предоставляет инструменты для ручной верификации.
</p>
<p align="justify">
  Частота релизов GigaChat растёт, ручная проверка ответов на соответствие нормам дорогая и не масштабируется. Разработанное решение позволяет автоматизировать обнаружение подозрительных ответов и организовать triage с участием человека-эксперта.
</p>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="functions"> Функциональные возможности</h2>

<ul>
  <li>Организация чата с моделью GigaChat с потоковой передачей ответов.</li>
  <li>Классификация ответов с присвоением меток «хороший» (0) или «плохой» (1).</li>
  <li>Детальное пояснение причины классификации.</li>
  <li>Анализ токсичности с использованием локальной модели Tinkoff.</li>
  <li>Поиск релевантных примеров из размеченного датасета (RAG).</li>
  <li>Поиск фрагментов документа с цензурными требованиями.</li>
  <li>Поддержка нескольких независимых диалогов (сессий).</li>
  <li>Сохранение истории диалогов в базе данных SQLite.</li>
  <li>Экспорт истории в формате CSV.</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="architecture"> Архитектура</h2>

<p align="justify">
Система построена по модульному принципу. Взаимодействие компонентов организовано через центральный модуль <code>app.py</code>. Все зависимости вынесены в файл <code>requirements.txt</code>. Конфигурационные параметры хранятся в <code>config.py</code>.
</p>

<h3>Состав компонентов</h3>

<ul>
  <li><code>app.py</code> – управление интерфейсом пользователя, обработка запросов к GigaChat, координация работы классификаторов.</li>
  <li><code>database.py</code> – создание и обслуживание таблиц SQLite, операции с сессиями и сообщениями.</li>
  <li><code>classifier/retrieval.py</code> – поиск ближайших соседей в FAISS-индексах.</li>
  <li><code>classifier/model_or.py</code> – отправка запросов к LLM через OpenRouter и парсинг ответов.</li>
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
  <li>Модуль <code>model_or.py</code> формирует промпт, включающий примеры, правила и результат токсичности, и отправляет его в LLM через OpenRouter API.</li>
  <li>LLM возвращает метку и пояснение.</li>
  <li>Результат сохраняется в базе данных и отображается пользователю.</li>
</ol>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="tech"> Стек технологий</h2>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Streamlit-1.56%2B-red?style=for-the-badge&logo=streamlit&logoColor=white">
  <img src="https://img.shields.io/badge/🤗_HuggingFace-Transformers-yellow?style=for-the-badge&logo=huggingface&logoColor=black">
  <img src="https://img.shields.io/badge/OpenRouter-API-purple?style=for-the-badge&logo=openai&logoColor=white">
  <img src="https://img.shields.io/badge/GigaChat-API-green?style=for-the-badge&logo=googlechat&logoColor=white">
  <img src="https://img.shields.io/badge/FAISS-Facebook-0866FF?style=for-the-badge&logo=facebook&logoColor=white">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white">
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white">
</p>
</p>

<ul>
  <li><strong>Python 3.10+</strong> – основной язык разработки</li>
  <li><strong>Streamlit</strong> – веб-интерфейс и интерактивный чат</li>
  <li><strong>GigaChat API</strong> – генерация ответов LLM</li>
  <li><strong>OpenRouter API</strong> – доступ к LLM-классификаторам</li>
  <li><strong>Sentence Transformers</strong> –  эмбеддинги для RAG (FRIDA / rubert‑mini‑frida)</li>
  <li><strong>FAISS</strong> – индексный поиск похожих примеров и цензурных правил</li>
  <li><strong>Hugging Face Transformers</strong> – локальная модель токсичности (Tinkoff)</li>
  <li><strong>SQLite</strong> – хранение истории диалогов и сессий</li>
  <li><strong>Supabase</strong> – хранение мутированных промтов и результатов классификации (опционально)</li>
  <li><strong>Pandas / NumPy</strong> – обработка данных и экспорт в CSV/Excel</li>
  <li><strong>Requests / JSON</strong> – взаимодействие с внешними API</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="structure"> Структура проекта</h2>

```
  AI_triage_GigaChat/
  ├── app.py # Главное приложение Streamlit
  ├── database.py # Модели SQLite (сессии, сообщения)
  ├── config.py # Конфигурационные пути
  ├── style.css # Кастомные CSS-стили
  ├── requirements.txt # Зависимости
  ├── README.md
  ├── classifier/
  │ ├── retrieval.py # RAG: поиск по индексам
  │ ├── build_index.py # Построение индекса датасета
  │ ├── build_index_doc.py # Построение индекса правил
  │ ├── model_toxicity.py # Локальная токсичность (Tinkoff)
  │ ├── model_or.py # Классификатор через OpenRouter
  │ └── data/
  │ ├── labeled_data.csv
  │ ├── goal_index.faiss
  │ ├── censorship_rules.txt
  │ ├── doc_index.faiss
  │ └── doc_chunks.csv
  ├── supabase_client.py # Интеграция с Supabase (опционально)
  └── chat_history.db # База данных (создаётся при первом запуске)
```

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="setup"> Установка и запуск</h2>

<h3>Требования к среде</h3>
<ul>
  <li>Операционная система Windows, Linux или macOS.</li>
  <li>Python версии 3.10 или выше.</li>
  <li>Установленный менеджер пакетов pip.</li>
  <li>Действующий API-ключ GigaChat.</li>
  <li>Действующий API-ключ OpenRouter.</li>
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
  <li>Настройка API-ключа OpenRouter:
    <ul>
      <li>Создайте файл <code>.env</code> в корне проекта и добавьте: <code>OPENROUTER_API_KEY=ваш_ключ</code>.</li>
      <li>Либо укажите ключ непосредственно в <code>config.py</code> (не рекомендуется для публичных репозиториев).</li>
      <li>При необходимости измените используемую модель в <code>classifier/model_or.py</code> (по умолчанию <code>google/gemini-2.0-flash-exp:free</code>).</li>
    </ul>
  </li>
  <li>Запуск приложения:
    <pre><code>streamlit run app.py --server.port 8501</code></pre>
  </li>
  <li>Открыть в браузере адрес <code>http://localhost:8501</code>, ввести API-ключ GigaChat и начать диалог.</li>
</ol>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="config"> Конфигурация</h2>

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
  Параметры подключения к LLM-классификатору задаются в <code>classifier/model_or.py</code> и через переменную окружения <code>OPENROUTER_API_KEY</code>:
</p>
<ul>
  <li><code>OPENROUTER_API_KEY</code> – ключ для доступа к OpenRouter.</li>
  <li><code>MODEL_NAME</code> – идентификатор модели (например, <code>google/gemini-2.0-flash-exp:free</code>).</li>
</ul>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="models">  Используемые модели</h2>
<ul>
  <li><strong>Эмбеддер для RAG</strong>: <code>sergeyzh/rubert-mini-frida</code>. Допустима замена на <code>ai-forever/FRIDA</code>.</li>
  <li><strong>Анализ токсичности</strong>: <code>tinkoff-ai/response-toxicity-classifier-base</code>.</li>
  <li><strong>LLM-классификатор</strong>: через OpenRouter API (модель по умолчанию: <code>google/gemini-2.0-flash-exp:free</code>). При необходимости модель можно заменить в <code>model_or.py</code> на любую другую, поддерживаемую OpenRouter.</li>
</ul>


![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

<h2 id="contributors"> Участники</h2>

<p>
  <i>Проект выполнен студентами Института радиоэлектроники и информационных технологий — РТФ Уральского федерального университета имени Б. Н. Ельцина.</i>
</p>

<ul>
  <li><strong>Алымова Светлана Олеговна</strong> </li>
  <li><strong>Ляпин Семён Николаевич</strong> </li>
  <li><strong>Молчанова Полина Алексеевна</strong> </li>
  <li><strong>Пластеева Ксения Евгеньевна</strong> </li>
  <li><strong>Ступаченко Екатерина Евгеньевна</strong> </li>
  <li><strong>Тетенькина Екатерина Владимировна</strong> </li>
</ul>

<p>
  <strong>Куратор проекта:</strong> Домуховский Николай Анатольевич (ПАО Сбербанк)
  [Google](https://google.com)

</p>

[**Ссылка на презентацию**](https://canva.link/nyyi19l1yqgbi69)

<p>
  <i>Учебный проект, реализованный в рамках дисциплины «Проектный практикум». Команда «Генератор букв».<br>
  Июнь 2026 г.</i>
</p>
