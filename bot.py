import telebot
from groq import Groq
import os
import sys

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    print("❌ Token eksik!")
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

user_histories = {}

# Botun ismi (büyük-küçük harf fark etmeksizin)
BOT_TRIGGER = "berxwedan bot"

def should_reply(message):
    if message.chat.type == "private":
        return True  # Özel sohbetlerde her zaman cevap versin
    
    text = (message.text or "").lower()
    # Grupta "Berxwedan Bot" yazıldığında veya mention edildiğinde cevap versin
    if BOT_TRIGGER in text or (bot.get_me().username and bot.get_me().username.lower() in text):
        return True
    return False

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Berxwedan Bot aktif!\nNe konuşmak istersin? 🔥")

@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return  # Trigger yoksa cevap verme
    
    user_id = message.chat.id
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    messages = user_histories[user_id] + [{"role": "user", "content": message.text}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.85,
            max_tokens=1024,
        )
        reply = completion.choices[0].message.content
        
        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})
        
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]
            
        bot.reply_to(message, reply)
        
    except Exception as e:
        print(f"Hata: {e}")
        bot.reply_to(message, "Bir hata oluştu, tekrar dener misin?")

print("🚀 Berxwedan Bot çalışıyor... (Trigger: 'Berxwedan Bot')")
bot.infinity_polling()
