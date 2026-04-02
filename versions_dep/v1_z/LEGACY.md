# Архив: `versions_dep/v1_z`

**Статус:** неактуально для текущего продукта. Активный стек — **[versions_dep/v3](../v3/README.md)** (Open WebUI → orchestrator → LiteLLM). Этот каталог сохранён как исторический черновик (лендинг/описание другой архитектуры).

Ниже — исходный текст бывшего `readme.md` без правок содержания.

---

**Universal AI Chat Platform** — комплексное веб-приложение на базе OpenWebUI, объединяющее все типы взаимодействия с ИИ в одном интерфейсе.

---

## 📋 Что было реализовано:

### 🎯 **Основные возможности:**

1. **📝 Мультимодальный чат**
   - Текстовые сообщения с поддержкой Markdown
   - Голосовой ввод/вывод (STT/TTS)
   - Загрузка и анализ изображений
   - Обработка файлов (PDF, код, документы)

2. **🧠 Smart Model Router**
   - Автоматический выбор оптимальной модели под задачу
   - Поддержка GPT-4o, Claude 3.5, Llama 3.1, Gemini и других
   - Оптимизация по стоимости, скорости и качеству
   - Fallback-механизм для надежности

3. **💾 Система долгосрочной памяти**
   - Многоуровневая архитектура (рабочая → краткосрочная → долгосрочная → эпизодическая)
   - Векторное хранилище (Qdrant) для семантического поиска
   - Авто-извлечение важной информации из диалогов
   - Временное затухание и персонализация

4. **🔀 Multimodal Fusion**
   - Параллельная обработка всех модальностей
   - Единый формат сообщений (TypeScript interfaces)
   - Cross-modal attention механизм
   - Согласованные мультимедийные ответы

---

### 💻 **Технический стек:**

#### Backend (Python/FastAPI):
- ✅ Smart Router Service с классификацией задач
- ✅ Memory Manager с гибридным поиском
- ✅ MultiModal Processor для параллельной обработки
- ✅ REST API + WebSocket для real-time коммуникации
- ✅ Streaming responses (SSE)
- ✅ Полная аутентификация (JWT/OAuth2)

#### Frontend (React + TypeScript):
- ✅ UniversalMessage компонент для всех типов контента
- ✅ ChatInput с drag-and-drop, голосом, скриншотами
- ✅ Zustand state management с persistence
- ✅ WebSocket hook для real-time обновлений
- ✅ Адаптивный дизайн с современным UI

#### Infrastructure:
- ✅ Docker Compose конфигурация (6 сервисов)
- ✅ PostgreSQL + Redis + Qdrant + MinIO
- ✅ Полная документация API (REST + WebSocket)
- ✅ Инструкции по установке и развертыванию

---

### 📚 **Структура веб-страницы (13 секций):**

| # | Секция | Содержание |
|---|--------|------------|
| 1 | **Hero** | Название, описание, tech stack, CTA кнопки |
| 2 | **Overview** | Концепция, 6 ключевых фич, целевая аудитория |
| 3 | **Architecture** | Диаграмма слоев: Frontend → Backend → AI Engine → Infrastructure |
| 4 | **Smart Router** | Критерии выбора, модели (Text/Vision/Audio/Specialized), код |
| 5 | **Memory System** | 4 уровня памяти, алгоритм ранжирования, код |
| 6 | **Multimodal Integration** | Unified Message Format, pipelines, fusion процесс |
| 7 | **Backend Code** | Полный FastAPI endpoint + WebSocket handler |
| 8 | **Frontend Code** | React компоненты + Zustand store + hooks |
| 9 | **Installation** | Docker Compose + Manual setup + конфигурация |
| 10 | **API Documentation** | 8+ endpoints, WebSocket events, error codes |
| 11 | **Features & Demos** | 4 use case'а (Debugging, Analysis, Creative, Learning) |
| 12 | **Roadmap** | 4 фазы развития + Future Vision + Community requests |
| 13 | **Contributing** | Workflow, project structure, code quality, community |

---

## 🎨 **Дизайн особенности:**

✨ **Современный темный UI** с градиентными акцентами  
✨ **Полностью адаптивный** (mobile-first подход)  
✨ **Интерактивные элементы**: hover эффекты, анимации, copy-to-clipboard  
✨ **Код блоки** с подсветкой синтаксиса (JetBrains Mono)  
✨ **MathJax** поддержка для математических формул  
✨ **Smooth scroll** и fade-in анимации при прокрутке  
✨ **Custom scrollbar** стилизация  

---

## 🚀 **Как использовать:**

1. **Откройте `index.html`** в браузере — сайт полностью готов к просмотру
2. **Все секции** связаны якорями для навигации
3. **Кнопки "Copy"** в кодовых блоках работают (копируют в буфер обмена)
4. **Responsive дизайн** — проверяйте на разных устройствах

---

## 🎯 **Для целевой аудитории:**

### Python-разработчики:
- Готовый backend код (FastAPI, async/await, Pydantic)
- Интеграции с векторными БД, LLM провайдерами
- Docker конфигурации и миграции БД

### JavaScript/TypeScript-разработчики:
- Компоненты React с TypeScript
- State management (Zustand)
- Custom hooks (WebSocket, Voice Recorder, Dropzone)
- Современные паттерны и best practices

### AI Engineers:
- Smart Router архитектура
- RAG система с hybrid search
- Memory management алгоритмы
- Multimodal fusion pipeline
