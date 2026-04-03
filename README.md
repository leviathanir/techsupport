# Чат-бот поддержки интернет-магазина

Веб-приложение с чат-ботом для технической поддержки интернет-магазина. Реализовано на FastAPI с JWT аутентификацией, WebSocket и SQLite.

## Установка и запуск

### 1. Установка зависимостей

```bash
pip install fastapi uvicorn sqlalchemy aiosqlite python-jose[cryptography] passlib[bcrypt] pydantic pytest pytest-asyncio httpx
