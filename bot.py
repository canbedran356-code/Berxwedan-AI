import telebot
from groq import Groq
import os

# ================== TOKEN'LAR ==================
TELEGRAM_TOKEN = "BURAYA_TELEGRAM_TOKENINI_YAPISTIR"

# Groq API Key'ini .env dosyasına koy (daha güvenli!)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")   # .env dosyasından okunacak

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY bulunamadı! .env dosyası oluştur.")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

user_histories = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
                     "✅ AI Sohbet Botu aktif!\n"
                     "Merhaba! Ne konuşmak istersin? 😊")

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_id = message.chat.id
    user_input = message.text

    if user_id not in user_histories:
        user_histories[user_id] = []
    
    messages = user_histories[user_id] + [{"role": "user", "content": user_input}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.85,
            max_tokens=1024,
        )
        response = completion.choices[0].message.content
        
        user_histories[user_id].append({"role": "user", "content": user_input})
        user_histories[user_id].append({"role": "assistant", "content": response})
        
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]
            
        bot.send_message(message.chat.id, response)
        
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Hata oluştu. Tekrar dene.")

print("🚀 Bot çalışıyor...")
bot.infinity_polling()
