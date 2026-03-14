# Task 3: The System Agent — Implementation Plan

## Overview

В этой задаче нужно добавить инструмент `query_api` в агента из Task 2, чтобы он мог делать запросы к работающему бэкенду и отвечать на вопросы о системных фактах и данных.

## Plan

### 1. Tool Schema: `query_api`

Добавлю функцию `query_api` со следующей сигнатурой:

```python
def query_api(method: str, path: str, body: dict | None = None) -> dict:
    """
    Call the LMS backend API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API path (e.g., "/items/", "/analytics/completion-rate?lab=lab-01")
        body: Optional JSON body for POST/PUT requests
    
    Returns:
        dict with "status_code" and "body" (parsed JSON response)
    """
```

**Формат возврата:**
```json
{
  "status_code": 200,
  "body": {...}
}
```

### 2. Authentication

- Использовать `LMS_API_KEY` из переменных окружения (читается из `.env.docker.secret`)
- Передавать в заголовке: `Authorization: Bearer <LMS_API_KEY>`
- Базовый URL API брать из `AGENT_API_BASE_URL` (по умолчанию `http://localhost:42002`)

### 3. Environment Variables

Агент должен читать все конфигурации из переменных окружения:

| Variable             | Purpose                              | Default                    |
| -------------------- | ------------------------------------ | -------------------------- |
| `LLM_API_KEY`        | LLM provider API key                 | (required)                 |
| `LLM_API_BASE`       | LLM API endpoint URL                 | (required)                 |
| `LLM_MODEL`          | Model name                           | (required)                 |
| `LMS_API_KEY`        | Backend API key for `query_api` auth | (required)                 |
| `AGENT_API_BASE_URL` | Base URL for `query_api`             | `http://localhost:42002`   |

### 4. System Prompt Update

Обновлю системный промпт, чтобы LLM понимал, когда использовать какой инструмент:

- **`read_file`** — для чтения файлов из wiki и исходного кода
- **`list_files`** — для поиска файлов в проекте
- **`query_api`** — для запросов к работающему API (получить данные, статус-коды, проверить ошибки)

Пример промпта:
> "Ты — ассистент для работы с проектом Learning Management Service. Используй инструменты:
> - `read_file` для чтения файлов документации и исходного кода
> - `list_files` для поиска файлов в проекте
> - `query_api` для запросов к API бэкенда (получение данных, проверка статус-кодов, отладка ошибок)
> 
> Для вопросов о данных в БД используй `query_api`. Для вопросов о структуре проекта — `read_file` или `list_files`."

### 5. Интеграция в агентский цикл

Агентский цикл остаётся тем же — просто добавляется новый инструмент в список доступных `tools` при вызове LLM.

### 6. Тестирование

Запущу `uv run run_eval.py` и буду исправлять ошибки итеративно.

---

## Benchmark Results

**Initial score:** Не удалось запустить — LLM API (`10.93.26.109:42005`) недоступен из текущей сети.

**Implementation status:**
- ✅ `query_api` инструмент реализован
- ✅ Аутентификация через `LMS_API_KEY` из переменных окружения
- ✅ Чтение конфигурации из `.env.agent.secret` и `.env.docker.secret`
- ✅ System prompt обновлён
- ✅ 4 теста реализации инструментов проходят
- ✅ 2 регрессионных теста добавлены
- ✅ Документация `AGENT.md` написана (>200 слов)
- ⏳ Benchmark не запущен из-за недоступности LLM API

**Iteration strategy:**
1. Запустить benchmark когда LLM API станет доступен
2. Прочитать feedback для первого проваленного вопроса
3. Исправить причину (tool description, system prompt, implementation)
4. Повторить

## Notes

Для полного прохождения benchmark требуется:
1. Доступ к университетскому LLM API (`10.93.26.109:42005`)
2. Запущенный бэкенд (через `docker-compose up`)
3. Инициализированная база данных с тестовыми данными

---

## Implementation Notes

- Бэкенд использует Caddy на порту 42002 (из `.env.docker.secret`)
- API endpoints: `/items/`, `/analytics/scores`, `/analytics/completion-rate`, `/analytics/top-learners`, и т.д.
- Все endpoints требуют аутентификацию через `Authorization: Bearer <LMS_API_KEY>`
