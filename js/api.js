// База данных ответов бота
const botResponses = {
    'привет': 'Здравствуйте! Чем могу помочь?',
    'здравствуйте': 'Добрый день! Какой у вас вопрос?',
    'гарантия': 'На все товары предоставляется гарантия 12 месяцев. Подробнее можно узнать на странице товара.',
    'возврат': 'Возврат возможен в течение 14 дней с момента покупки при сохранении товарного вида и упаковки.',
    'цена': 'Цены указаны на сайте. Есть ли у вас промокод?',
    'доставка': 'Доставка осуществляется курьером или в пункты выдачи. Стоимость зависит от вашего города.',
    'оплата': 'Мы принимаем карты, электронные деньги и наличные при получении.',
    'контакты': 'Наши контакты: support@techshop.ru, 8-800-123-45-67',
    'спасибо': 'Пожалуйста! Обращайтесь ещё :)',
    'пока': 'До свидания! Хорошего дня!'
};

const defaultResponse = 'Извините, я не совсем понял ваш вопрос. Пожалуйста, переформулируйте или обратитесь к оператору.';

// Имитация API запроса
export async function getBotResponse(userMessage) {
    try {
        // Имитация задержки сети
        await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 1000));
        
        // Имитация ошибки (10% вероятность для демонстрации обработки ошибок)
        if (Math.random() < 0.1) {
            throw new Error('Ошибка соединения с сервером');
        }
        
        // Поиск ответа (регистронезависимый)
        const normalizedMessage = userMessage.toLowerCase().trim();
        
        for (const [key, response] of Object.entries(botResponses)) {
            if (normalizedMessage.includes(key)) {
                return response;
            }
        }
        
        return defaultResponse;
    } catch (error) {
        console.error('API Error:', error);
        throw new Error('Не удалось получить ответ от сервера. Пожалуйста, попробуйте позже.');
    }
}

// Работа с localStorage
const STORAGE_KEY = 'chat_messages';

export function saveMessages(messages) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (error) {
        console.error('Failed to save messages:', error);
    }
}

export function loadMessages() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : [];
    } catch (error) {
        console.error('Failed to load messages:', error);
        return [];
    }
}

export function clearSavedMessages() {
    localStorage.removeItem(STORAGE_KEY);
}