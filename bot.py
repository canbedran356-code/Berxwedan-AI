import telebot
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    print("❌ Token'lar eksik!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

user_histories = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ AI Bot aktif!\nNe konuşmak istersin? 🚀")

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
            temperature=0.85,
            max_tokens=1000,
        )
        reply = completion.choices[0].message.content
        
        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})
        
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]
            
        bot.reply_to(message, reply)
        
    except Exception as e:
        bot.reply_to(message, "Bir hata oluştu, lütfen tekrar dene.")

print("🚀 AI Bot Railway'de çalışıyor...")
bot.infinity_polling()
