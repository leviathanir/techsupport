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

### 2. Запуск приложения
