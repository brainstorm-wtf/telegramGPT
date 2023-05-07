import openai
import telebot
import time
import re
from datetime import datetime, timedelta, timezone
from telebot import types

# OpenAI API key to access chatGPT backend, insert key in <...>
APIKEY = "<OPENAI-API-KEY>"
# Telegram API token to access the TG bot, insert token in <...>
TELEGRAM_TOKEN = "<TELEGRAM-API-TOKEN>"

openai.api_key = APIKEY
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Store conversation history, message count, and user languages
conversations = {}
message_count = {}
user_languages = {}

def language_switch_keyboard():
    language_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    russian_option = types.KeyboardButton("🇷🇺 Русский")
    english_option = types.KeyboardButton("🇺🇸 English")
    language_markup.add(russian_option, english_option)
    return language_markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id in conversations:
        del conversations[chat_id]

    bot.send_message(chat_id, "Привет! Я - ваш ChatGPT-бот. Выберите свой язык \n Hello! I'm your ChatGPT bot. Choose your language", reply_markup=language_switch_keyboard())

@bot.message_handler(func=lambda message: message.text in ["🇷🇺 Русский", "🇺🇸 English"])
def handle_language_switch(message):
    chat_id = message.chat.id
    if message.text == "🇷🇺 Русский":
        user_languages[chat_id] = "Russian"
        bot.send_message(chat_id, "Язык изменён на русский. Теперь введите сообщение, и я отвечу.", reply_markup=language_switch_keyboard())
    elif message.text == "🇺🇸 English":
        user_languages[chat_id] = "English"
        bot.send_message(chat_id, "Language set to English. Just type a message, and I'll respond.", reply_markup=language_switch_keyboard())

@bot.message_handler(func=lambda m: True)
def chat_gpt(message):
    chat_id = message.chat.id
    user_input = message.text

    if chat_id not in conversations:
        conversations[chat_id] = []
        message_count[chat_id] = {"count": 0, "reset_time": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)}

    if message_count[chat_id]["count"] >= 10:
        if datetime.now(timezone.utc) >= message_count[chat_id]["reset_time"]:
            message_count[chat_id]["count"] = 0
            message_count[chat_id]["reset_time"] = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            bot.reply_to(message, "You've reached your daily limit of 6 questions. Please wait till midnight for a reset.")
            return

    conversations[chat_id].append({"role": "user", "content": user_input})
    message_count[chat_id]["count"] += 1

    # Show the typing indicator
    bot.send_chat_action(chat_id, "typing")

    output = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversations[chat_id]
    )

    response = output['choices'][0]['message']['content']

    # Add assistant message to the conversation history
    conversations[chat_id].append({"role": "assistant", "content": response})

    # Split the response into smaller chunks
    response_chunks = re.split(r'(?<=[.!?]) +', response)

    # Send the first chunk
    sent_message = bot.reply_to(message, response_chunks[0])

    # Send the remaining chunks
    for i, chunk in enumerate(response_chunks[1:]):
        # Show the typing action only if it's not the last chunk
        if i < len(response_chunks) - 2:
            bot.send_chat_action(chat_id, "typing")

        time.sleep(min(0.5, len(chunk) * 0.01))  # Adjust the typing speed (seconds per character)
        sent_message = bot.edit_message_text(chat_id=chat_id, message_id=sent_message.message_id, text=sent_message.text + ' ' + chunk)

bot.polling()

