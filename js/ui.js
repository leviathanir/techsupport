export class ChatUI {
    constructor(messagesContainer, typingIndicator, messageInput, sendBtn, clearBtn) {
        this.messagesContainer = messagesContainer;
        this.typingIndicator = typingIndicator;
        this.messageInput = messageInput;
        this.sendBtn = sendBtn;
        this.clearBtn = clearBtn;
    }

    // Добавление сообщения в чат
    addMessage(text, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);
        
        const textElement = document.createElement('div');
        textElement.classList.add('message-text');
        textElement.textContent = text;
        
        const timeElement = document.createElement('div');
        timeElement.classList.add('message-time');
        timeElement.textContent = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageElement.appendChild(textElement);
        messageElement.appendChild(timeElement);
        
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    // Добавление нескольких сообщений (для загрузки истории)
    addMessages(messages) {
        messages.forEach(msg => this.addMessage(msg.text, msg.sender));
    }

    // Очистка чата
    clearMessages() {
        this.messagesContainer.innerHTML = '';
    }

    // Прокрутка вниз
    scrollToBottom() {
        const chatMain = document.querySelector('.chat-main');
        chatMain.scrollTop = chatMain.scrollHeight;
    }

    // Показать/скрыть индикатор печатания
    showTypingIndicator(show) {
        if (show) {
            this.typingIndicator.classList.add('visible');
        } else {
            this.typingIndicator.classList.remove('visible');
        }
        this.scrollToBottom();
    }

    // Блокировка/разблокировка ввода
    setInputEnabled(enabled) {
        this.messageInput.disabled = !enabled;
        this.sendBtn.disabled = !enabled;
        
        if (enabled) {
            this.messageInput.focus();
        }
    }

    // Получение текста из поля ввода
    getInputText() {
        return this.messageInput.value.trim();
    }

    // Очистка поля ввода
    clearInput() {
        this.messageInput.value = '';
    }

    // Валидация формы
    validateInput(text) {
        if (!text || text.length === 0) {
            this.showError('Поле не может быть пустым');
            return false;
        }
        
        if (text.length > 500) {
            this.showError('Сообщение слишком длинное (максимум 500 символов)');
            return false;
        }
        
        return true;
    }

    // Показать ошибку
    showError(message) {
        // Создаем временное уведомление об ошибке
        const errorElement = document.createElement('div');
        errorElement.classList.add('error-toast');
        errorElement.textContent = message;
        errorElement.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--error-color);
            color: white;
            padding: 12px 24px;
            border-radius: var(--border-radius-md);
            box-shadow: var(--shadow-lg);
            animation: slideIn 0.3s ease;
            z-index: 1000;
        `;
        
        document.body.appendChild(errorElement);
        
        setTimeout(() => {
            errorElement.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => errorElement.remove(), 300);
        }, 3000);
    }
}