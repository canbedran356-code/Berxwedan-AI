import telebot
from groq import Groq
import os
import sys

# Railway'de .env yerine doğrudan environment variable okuyoruz
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_TOKEN bulunamadı!")
    sys.exit(1)
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY bulunamadı!")
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

user_histories = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Bot aktif!\nMerhaba, ne konuşmak istersin? 😊")

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.chat.id
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    messages = user_histories[user_id] + [{"role": "user", "content": message.text}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.8,
            max_tokens=1024,
        )
        reply = completion.choices[0].message.content
        
        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})
        
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]
            
        bot.reply_to(message, reply)
        
    except Exception as e:
        print(f"Hata: {e}")   # Railway log'larda görebilmen için
        bot.reply_to(message, "Bir hata oluştu, lütfen tekrar dene.")

print("🚀 Bot başarıyla başladı...")
bot.infinity_polling()
