import telebot
import requests
import json
from typing import Dict

# Конфигурация
API_TOKEN = '8392631979:AAFy87kmPcF-BSjXOwB78eqW2mexjueizjU'  # Замените на ваш токен от BotFather
LM_STUDIO_URL = 'http://localhost:1234/v1/chat/completions'

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Хранилище контекста для каждого пользователя
user_contexts: Dict[int, list] = {}

def get_model_response(messages: list) -> str:
    """
    Отправляет запрос к локальной модели через LM Studio API
    """
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": False
    }
    
    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Ошибка API: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Ошибка: Не удалось подключиться к LM Studio. Убедитесь, что LM Studio запущен и модель загружена."
    except requests.exceptions.Timeout:
        return "Ошибка: Превышено время ожидания ответа от модели."
    except Exception as e:
        return f"Произошла непредвиденная ошибка: {str(e)}"

def update_user_context(user_id: int, role: str, content: str):
    """
    Обновляет контекст пользователя
    """
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    
    user_contexts[user_id].append({
        "role": role,
        "content": content
    })
    
    # Ограничиваем длину истории (последние 10 сообщений)
    if len(user_contexts[user_id]) > 10:
        user_contexts[user_id] = user_contexts[user_id][-10:]

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Привет! Я ваш умный Telegram бот с поддержкой контекста.\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/model - показать информацию о используемой модели\n"
        "/clear - очистить историю диалога\n\n"
        "Просто отправьте мне сообщение, и я отвечу с учётом предыдущего разговора!"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['model'])
def send_model_name(message):
    """Обработчик команды /model"""
    try:
        response = requests.get('http://localhost:1234/v1/models', timeout=10)
        if response.status_code == 200:
            model_info = response.json()
            model_name = model_info['data'][0]['id']
            bot.reply_to(message, f"Используемая модель: {model_name}")
        else:
            bot.reply_to(message, 'Не удалось получить информацию о модели.')
    except Exception as e:
        bot.reply_to(message, f'Ошибка при получении информации о модели: {str(e)}')

@bot.message_handler(commands=['clear'])
def clear_context(message):
    """Обработчик команды /clear - очистка контекста"""
    user_id = message.from_user.id
    if user_id in user_contexts:
        user_contexts[user_id] = []
    
    bot.reply_to(message, "История диалога очищена! Начинаем новый разговор.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Обновляем контекст с сообщением пользователя
    update_user_context(user_id, "user", user_message)
    
    # Получаем текущий контекст пользователя
    current_context = user_contexts.get(user_id, [])
    
    # Отправляем запрос к модели
    bot.send_chat_action(message.chat.id, 'typing')
    response_text = get_model_response(current_context)
    
    # Обновляем контекст с ответом модели
    update_user_context(user_id, "assistant", response_text)
    
    # Отправляем ответ пользователю
    bot.reply_to(message, response_text)

if __name__ == '__main__':
    print("Бот запущен...")
    print("Убедитесь, что LM Studio запущен и модель загружена")
    bot.polling(none_stop=True)