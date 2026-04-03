"""
Чат-бот поддержки интернет-магазина
FastAPI приложение с WebSocket, JWT аутентификацией, SQLAlchemy и тестами
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, relationship, Session as SyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
import pytest
from pytest_asyncio import fixture as async_fixture
from httpx import AsyncClient, ASGITransport
import uvicorn
from typing import List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
SECRET_KEY = "your-secret-key-change-in-production-123456789"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# База данных (SQLite для простоты)
DATABASE_URL = "sqlite+aiosqlite:///./chatbot.db"
sync_database_url = "sqlite:///./chatbot.db"

# Pydantic схемы
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    
    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class MessageRequest(BaseModel):
    session_id: int
    text: str = Field(..., min_length=1, max_length=1000)
    
    @field_validator('text')
    @classmethod
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message text cannot be empty')
        return v.strip()

class MessageResponse(BaseModel):
    id: int
    session_id: int
    sender: str
    text: str
    timestamp: datetime

class SessionCreate(BaseModel):
    pass

class SessionResponse(BaseModel):
    id: int
    user_id: Optional[int]
    created_at: datetime
    messages: List[MessageResponse] = []

# SQLAlchemy модели
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), nullable=False)  # 'user' или 'bot'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")

# Логика бота (обработка по ключевым словам)
class SupportBot:
    KEYWORDS = {
        r'заказ|оформлен|купить|покупка': 'Как оформить заказ? 🛒\n1. Добавьте товары в корзину\n2. Перейдите в корзину\n3. Нажмите "Оформить заказ"\n4. Заполните данные доставки\n5. Оплатите заказ\n\nНужна помощь на любом этапе? Напишите "помощь"!',
        
        r'доставк|отправк|почт|сдэк|курьер': 'Вопросы доставки 📦\nМы доставляем заказы:\n• Курьером по городу - 1-2 дня\n• Почтой России - 3-7 дней\n• СДЭК - 2-5 дней\n\nОтследить заказ можно по номеру в личном кабинете.',
        
        r'оплат|карт|налич|перевод|терминал': 'Способы оплаты 💳\nДоступны:\n• Банковские карты (Visa, Mastercard, МИР)\n• Наличные при получении\n• SberPay, YooMoney\n• Оплата частями\n\nВсе способы безопасны и защищены!',
        
        r'возврат|обмен|брак|гарантия': 'Возврат и гарантия 🔄\n• Товар можно вернуть в течение 14 дней\n• Брак обмениваем за наш счет\n• Гарантия на технику - 12 месяцев\n\nДля возврата обратитесь в поддержку с номером заказа.',
        
        r'статус заказ|где заказ|трек': 'Проверка статуса заказа 📍\nЧтобы узнать статус, сообщите номер заказа. Я помогу отследить!\n\nПример: "Заказ №12345"',
        
        r'скидк|акци|бонус|промокод': 'Акции и скидки 🎉\n• Приветственная скидка 10% на первый заказ\n• Бонусы за отзывы\n• Сезонные распродажи до 50%\n• Бесплатная доставка от 3000₽\n\nСледите за новостями в рассылке!',
        
        r'как связаться|оператор|человек|поддержка|помощь': 'Связь с оператором 👨‍💻\nНаши операторы работают 24/7:\n• Телефон: 8-800-123-45-67\n• Email: support@shop.ru\n• Telegram: @shop_support\n\nИли просто опишите проблему - я постараюсь помочь!'
    }
    
    DEFAULT_RESPONSE = "🤖 Спасибо за ваше сообщение! Я - бот поддержки интернет-магазина.\n\nЧем могу помочь?\n• Оформить заказ\n• Узнать о доставке\n• Способы оплаты\n• Возврат товара\n• Статус заказа\n• Акции и скидки\n• Связаться с оператором\n\nПросто напишите вопрос, и я отвечу!"
    
    @classmethod
    def get_response(cls, message: str) -> str:
        """Получить ответ бота на основе ключевых слов"""
        message_lower = message.lower()
        
        for pattern, response in cls.KEYWORDS.items():
            if re.search(pattern, message_lower):
                logger.info(f"Matched pattern: {pattern}")
                return response
        
        logger.info("No pattern matched, using default response")
        return cls.DEFAULT_RESPONSE

# FastAPI приложение
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Запуск
    logger.info("Starting application...")
    async_engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_local = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    app.state.async_session_local = async_session_local
    
    yield
    
    # Остановка
    logger.info("Shutting down application...")
    await async_engine.dispose()

app = FastAPI(
    title="Чат-бот поддержки интернет-магазина",
    description="API для общения с ботом технической поддержки",
    version="1.0.0",
    lifespan=lifespan
)

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Вспомогательные функции
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    async_session: AsyncSession = None
) -> User:
    """Получить текущего пользователя из JWT токена"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if async_session is None:
        async_session = app.state.async_session_local()
    
    result = await async_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

async def get_db():
    """Получить сессию базы данных"""
    async_session = app.state.async_session_local()
    try:
        yield async_session
    finally:
        await async_session.close()

# Эндпоинты API
@app.post("/auth/register", response_model=Token, tags=["auth"])
async def register(user_data: UserRegister, async_session: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    logger.info(f"Registering user: {user_data.username}")
    
    # Проверка существования пользователя
    result = await async_session.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Создание пользователя
    hashed_password = get_password_hash(user_data.password)
    user = User(username=user_data.username, hashed_password=hashed_password)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Создание токена
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token, tags=["auth"])
async def login(user_data: UserLogin, async_session: AsyncSession = Depends(get_db)):
    """Авторизация пользователя"""
    logger.info(f"Login attempt: {user_data.username}")
    
    result = await async_session.execute(
        select(User).where(User.username == user_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/chat/session", response_model=SessionResponse, tags=["chat"])
async def create_session(
    current_user: User = Depends(get_current_user),
    async_session: AsyncSession = Depends(get_db)
):
    """Создать новую сессию чата"""
    logger.info(f"Creating new session for user {current_user.id}")
    
    new_session = Session(user_id=current_user.id)
    async_session.add(new_session)
    await async_session.commit()
    await async_session.refresh(new_session)
    
    return SessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        created_at=new_session.created_at,
        messages=[]
    )

@app.post("/chat/message", response_model=MessageResponse, tags=["chat"])
async def send_message(
    message_req: MessageRequest,
    current_user: User = Depends(get_current_user),
    async_session: AsyncSession = Depends(get_db)
):
    """Принять сообщение пользователя и вернуть ответ бота"""
    logger.info(f"User {current_user.id} sent message to session {message_req.session_id}")
    
    # Проверка существования сессии и принадлежности пользователю
    result = await async_session.execute(
        select(Session).where(Session.id == message_req.session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to this user"
        )
    
    # Сохранение сообщения пользователя
    user_msg = Message(
        session_id=message_req.session_id,
        sender="user",
        text=message_req.text
    )
    async_session.add(user_msg)
    
    # Получение ответа бота
    bot_response_text = SupportBot.get_response(message_req.text)
    
    # Сохранение сообщения бота
    bot_msg = Message(
        session_id=message_req.session_id,
        sender="bot",
        text=bot_response_text
    )
    async_session.add(bot_msg)
    await async_session.commit()
    await async_session.refresh(bot_msg)
    
    logger.info(f"Bot response sent for session {message_req.session_id}")
    return MessageResponse(
        id=bot_msg.id,
        session_id=bot_msg.session_id,
        sender=bot_msg.sender,
        text=bot_msg.text,
        timestamp=bot_msg.timestamp
    )

@app.get("/chat/history/{session_id}", response_model=SessionResponse, tags=["chat"])
async def get_history(
    session_id: int,
    current_user: User = Depends(get_current_user),
    async_session: AsyncSession = Depends(get_db)
):
    """Получить историю диалога по ID сессии"""
    logger.info(f"Getting history for session {session_id}, user {current_user.id}")
    
    result = await async_session.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to this user"
        )
    
    # Получение сообщений
    messages_result = await async_session.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp)
    )
    messages = messages_result.scalars().all()
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        created_at=session.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                text=msg.text,
                timestamp=msg.timestamp
            )
            for msg in messages
        ]
    )

# WebSocket для реального времени
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: int,
    token: str = None
):
    """WebSocket соединение для чата с проверкой JWT токена"""
    await websocket.accept()
    logger.info(f"WebSocket connection attempt for session {session_id}")
    
    # Проверка JWT токена
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    async_session = app.state.async_session_local()
    
    try:
        # Проверка сессии и прав доступа
        result = await async_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session or session.user_id != user_id:
            await websocket.close(code=1008, reason="Session access denied")
            return
        
        logger.info(f"WebSocket connected for user {user_id}, session {session_id}")
        
        # Отправка истории сообщений при подключении
        history_result = await async_session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        history = history_result.scalars().all()
        
        for msg in history:
            await websocket.send_json({
                "type": "history",
                "sender": msg.sender,
                "text": msg.text,
                "timestamp": msg.timestamp.isoformat()
            })
        
        # Обработка входящих сообщений
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "").strip()
            
            if not user_text:
                await websocket.send_json({
                    "type": "error",
                    "message": "Message cannot be empty"
                })
                continue
            
            # Сохранение сообщения пользователя
            user_msg = Message(
                session_id=session_id,
                sender="user",
                text=user_text
            )
            async_session.add(user_msg)
            
            # Получение ответа бота
            bot_response = SupportBot.get_response(user_text)
            
            # Сохранение ответа бота
            bot_msg = Message(
                session_id=session_id,
                sender="bot",
                text=bot_response
            )
            async_session.add(bot_msg)
            await async_session.commit()
            
            # Отправка ответа клиенту
            await websocket.send_json({
                "type": "message",
                "sender": "bot",
                "text": bot_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"WebSocket message processed for session {session_id}")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        await async_session.close()

# Тесты
@pytest.fixture
async def async_client():
    """Создание асинхронного клиента для тестов"""
    # Создание тестовой БД
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_test_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Создание таблиц
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    app.state.async_session_local = async_test_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    await test_engine.dispose()

@async_fixture
async def auth_client(async_client):
    """Клиент с авторизацией"""
    # Регистрация
    await async_client.post("/auth/register", json={
        "username": "testuser",
        "password": "testpass123"
    })
    
    # Логин
    response = await async_client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    
    token = response.json()["access_token"]
    async_client.headers["Authorization"] = f"Bearer {token}"
    
    return async_client

@pytest.mark.asyncio
async def test_create_session(auth_client):
    """Тест создания сессии"""
    response = await auth_client.post("/chat/session")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["user_id"] is not None
    assert "created_at" in data

@pytest.mark.asyncio
async def test_send_and_save_messages(auth_client):
    """Тест отправки сообщения и сохранения обоих сообщений"""
    # Создание сессии
    session_resp = await auth_client.post("/chat/session")
    session_id = session_resp.json()["id"]
    
    # Отправка сообщения
    response = await auth_client.post("/chat/message", json={
        "session_id": session_id,
        "text": "Как оформить заказ?"
    })
    
    assert response.status_code == 200
    bot_msg = response.json()
    assert bot_msg["sender"] == "bot"
    assert "заказ" in bot_msg["text"].lower()
    
    # Проверка истории
    history_resp = await auth_client.get(f"/chat/history/{session_id}")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history["messages"]) == 2  # user + bot
    assert history["messages"][0]["sender"] == "user"
    assert history["messages"][1]["sender"] == "bot"

@pytest.mark.asyncio
async def test_get_history(auth_client):
    """Тест получения истории переписки"""
    # Создание сессии и отправка сообщений
    session_resp = await auth_client.post("/chat/session")
    session_id = session_resp.json()["id"]
    
    await auth_client.post("/chat/message", json={
        "session_id": session_id,
        "text": "Вопрос о доставке"
    })
    
    await auth_client.post("/chat/message", json={
        "session_id": session_id,
        "text": "Спасибо за помощь"
    })
    
    # Получение истории
    response = await auth_client.get(f"/chat/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 4  # 2 user + 2 bot
    
    # Проверка порядка сообщений
    assert data["messages"][0]["sender"] == "user"
    assert data["messages"][1]["sender"] == "bot"
    assert data["messages"][2]["sender"] == "user"
    assert data["messages"][3]["sender"] == "bot"

def run_migrations():
    """Применение миграций (упрощенная версия без Alembic)"""
    from sqlalchemy import create_engine
    engine = create_engine(sync_database_url)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

# Запуск приложения
if __name__ == "__main__":
    # Инициализация БД
    run_migrations()
    
    # Запуск сервера
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )