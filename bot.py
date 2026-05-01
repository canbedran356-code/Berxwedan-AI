import telebot
from groq import Groq
import os
import re
import random
import subprocess
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Apo'nun felsefesi, direniş, yoldaşlık üzerine güçlü ve onurlu konuşursun.
"""

def is_owner(uid): return uid == OWNER_ID

def is_admin(message):
    if is_owner(message.from_user.id): return True
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ["administrator", "creator"]
    except: return False

def should_reply(message):
    if message.chat.type == "private": return True
    text = (message.text or "").lower()
    return BOT_TRIGGER in text or (bot.get_me().username and bot.get_me().username.lower() in text)

def get_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    return None

# ====================== AI SOHBET (DÜZELTİLDİ) ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return

    user_id = message.chat.id
    if user_id not in user_histories:
        user_histories[user_id] = []

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
    full_messages.append({"role": "user", "content": message.text})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_messages,
            temperature=0.85,
            max_tokens=800,          # biraz düşürdük
        )
        reply = completion.choices[0].message.content

        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 16:
            user_histories[user_id] = user_histories[user_id][-16:]

        bot.reply_to(message, reply)

    except Exception as e:
        print(f"AI Hatası: {e}")   # Railway log için
        bot.reply_to(message, "Yoldaş, Groq şu anda yoğun. Biraz sonra tekrar dene.")

# ====================== DİĞER KOMUTLAR (Kısaltıldı) ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 Berxwedan Bot aktif! Direniş sürüyor yoldaş! 🔥")

@bot.message_handler(commands=['mod'])
def mod_help(message):
    if not is_admin(message): return
    bot.reply_to(message, "Komutlar için /mod yaz.")

# AI Resim (önceki iyi hali)
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    user_input = " ".join(message.text.split()[1:]).strip() or "Kürdistan dağları"
    bot.reply_to(message, "🖼️ Resim üretiliyor...")
    try:
        enhanced = f"{user_input}, Kurdish mountains, realistic Kurdish people, traditional clothing, proud, cinematic"
        clean = enhanced.replace(" ", "%20").replace(",", "%2C")
        url = f"https://image.pollinations.ai/prompt/{clean}?width=1024&height=1024&seed={random.randint(1,999999)}&model=flux"
        bot.send_photo(message.chat.id, url, caption=f"🖼️ {user_input}\n🚩 Berxwedan!")
    except:
        bot.reply_to(message, "Resim üretilemedi.")

print("🚩 Berxwedan Bot çalışıyor...")
bot.infinity_polling()
