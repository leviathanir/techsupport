# Чат-бот поддержки интернет-магазина

Веб-приложение с чат-ботом для технической поддержки интернет-магазина. Реализовано на FastAPI с JWT аутентификацией, WebSocket и SQLite.

## Установка и запуск

### 1. Установка зависимостей

```bash
pip install fastapi uvicorn sqlalchemy aiosqlite python-jose[cryptography] passlib[bcrypt] pydantic pytest pytest-asyncio httpx
```
### 2. Запуск приложения

```bash
python app.py
```
Сервер запустится на http://127.0.0.1:8000

### 3. Документация API

Swagger UI: http://127.0.0.1:8000/docs
ReDoc: http://127.0.0.1:8000/redoc

## Примеры запросов

### Регистрация

```bash
curl -X POST "http://127.0.0.1:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "alice123"}'
```

### Логин

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "alice123"}'
```

### Создание сессии

```bash
curl -X POST "http://127.0.0.1:8000/chat/session" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Отправка сообщения

```bash
curl -X POST "http://127.0.0.1:8000/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "text": "Как оформить заказ?"}'
```

### Получение истории

```bash
curl -X GET "http://127.0.0.1:8000/chat/history/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### WebSocket подключение

```bash
const ws = new WebSocket("ws://127.0.0.1:8000/ws/chat/1?token=YOUR_TOKEN_HERE");

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};

ws.send(JSON.stringify({text: "Вопрос о доставке"}));
```

### Запуск тестов

```bash
pytest app.py -v
```

## Инструкция по запуску

1. Сохраните код в файл `app.py`
2. Сохраните README в файл `README.md`
3. Установите зависимости:
```bash
pip install fastapi uvicorn sqlalchemy aiosqlite python-jose[cryptography] passlib[bcrypt] pydantic pytest pytest-asyncio httpx
```
4. Запустите приложение:
```bash
python app.py
```
5. Откройте браузер и перейдите на http://127.0.0.1:8000/docs
