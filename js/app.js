import { getBotResponse, saveMessages, loadMessages, clearSavedMessages } from './api.js';
import { ChatUI } from './ui.js';

class ChatApp {
    constructor() {
        this.initializeElements();
        this.ui = new ChatUI(
            this.messagesContainer,
            this.typingIndicator,
            this.messageInput,
            this.sendBtn,
            this.clearBtn
        );
        
        this.isProcessing = false;
        this.messages = [];
        
        this.init();
    }

    initializeElements() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearChatBtn');
        this.messageForm = document.getElementById('messageForm');
    }

    init() {
        this.loadChatHistory();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Отправка сообщения
        this.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSendMessage();
        });

        // Очистка чата
        this.clearBtn.addEventListener('click', () => {
            this.handleClearChat();
        });

        // Отправка по Enter (Shift+Enter для новой строки не нужен, т.к. у нас input)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!this.isProcessing && this.ui.getInputText()) {
                    this.handleSendMessage();
                }
            }
        });

        // Валидация при вводе
        this.messageInput.addEventListener('input', () => {
            const text = this.ui.getInputText();
            if (text.length > 500) {
                this.messageInput.style.borderColor = 'var(--error-color)';
            } else {
                this.messageInput.style.borderColor = 'var(--border-color)';
            }
        });
    }

    async handleSendMessage() {
        const userMessage = this.ui.getInputText();
        
        if (!this.ui.validateInput(userMessage) || this.isProcessing) {
            return;
        }

        // Добавляем сообщение пользователя
        this.ui.addMessage(userMessage, 'user');
        this.messages.push({ text: userMessage, sender: 'user', timestamp: Date.now() });
        this.ui.clearInput();
        
        // Блокируем ввод
        this.isProcessing = true;
        this.ui.setInputEnabled(false);
        
        // Показываем индикатор печатания
        this.ui.showTypingIndicator(true);
        
        try {
            // Получаем ответ от бота
            const botResponse = await getBotResponse(userMessage);
            
            // Добавляем ответ бота
            this.ui.addMessage(botResponse, 'bot');
            this.messages.push({ text: botResponse, sender: 'bot', timestamp: Date.now() });
            
            // Сохраняем сообщения
            saveMessages(this.messages);
        } catch (error) {
            this.ui.showError(error.message);
            
            // Добавляем сообщение об ошибке
            const errorMessage = 'Произошла ошибка при получении ответа. Пожалуйста, попробуйте позже.';
            this.ui.addMessage(errorMessage, 'bot');
            this.messages.push({ text: errorMessage, sender: 'bot', timestamp: Date.now() });
        } finally {
            // Скрываем индикатор и разблокируем ввод
            this.ui.showTypingIndicator(false);
            this.isProcessing = false;
            this.ui.setInputEnabled(true);
        }
    }

    handleClearChat() {
        if (this.messages.length === 0) return;
        
        if (confirm('Вы уверены, что хотите очистить историю чата?')) {
            this.ui.clearMessages();
            this.messages = [];
            clearSavedMessages();
            
            // Добавляем приветственное сообщение
            const welcomeMessage = 'Чат очищен. Чем могу помочь?';
            this.ui.addMessage(welcomeMessage, 'bot');
            this.messages.push({ text: welcomeMessage, sender: 'bot', timestamp: Date.now() });
            saveMessages(this.messages);
        }
    }

    loadChatHistory() {
        const savedMessages = loadMessages();
        
        if (savedMessages.length > 0) {
            this.messages = savedMessages;
            this.ui.addMessages(savedMessages);
        } else {
            // Приветственное сообщение для нового чата
            const welcomeMessage = 'Здравствуйте! Я виртуальный помощник TechSupport. Задайте мне вопрос о товарах, гарантии, доставке или оплате.';
            this.ui.addMessage(welcomeMessage, 'bot');
            this.messages.push({ text: welcomeMessage, sender: 'bot', timestamp: Date.now() });
            saveMessages(this.messages);
        }
        
        this.ui.scrollToBottom();
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});