import telebot
import os
import random
import subprocess
from google import genai

# ====================== AYARLAR ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
gemini = genai.Client(api_key=GEMINI_API_KEY)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Apo'nun felsefesi, direniş ve yoldaşlık üzerine güçlü ve onurlu konuşursun.
"""

# ====================== YARDIMCI ======================
def is_admin(message):
    if message.from_user.id == OWNER_ID:
        return True
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ["administrator", "creator"]
    except:
        return False

def should_reply(message):
    if message.chat.type == "private":
        return True
    text = (message.text or "").lower()
    return BOT_TRIGGER in text or (bot.get_me().username and bot.get_me().username.lower() in text)

# ====================== GEMINI AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return

    try:
        response = gemini.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[message.text]
        )
        reply = response.text
        bot.reply_to(message, reply)
    except:
        bot.reply_to(message, "Yoldaş, AI şu anda yoğun. Biraz sonra tekrar dene.")

# ====================== AI RESİM ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    prompt = " ".join(message.text.split()[1:]).strip() or "devrimci Kürt gerilla"
    bot.reply_to(message, "🖼️ Devrimci gerillalar çiziliyor... 🔥")

    try:
        full_prompt = f"{prompt}, handsome young Kurdish revolutionary, sharp face, intense eyes, Kurdistan mountains, red star flag, cinematic, highly detailed"
        clean = full_prompt.replace(" ", "%20").replace(",", "%2C")
        url = f"https://image.pollinations.ai/prompt/{clean}?width=1024&height=1024&seed={random.randint(1,999999)}&model=flux"
        bot.send_photo(message.chat.id, url, caption=f"🖼️ {prompt}\n🚩 Berxwedan!")
    except:
        bot.reply_to(message, "Resim üretilemedi.")

# ====================== DİĞER KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 Berxwedan Bot aktif! Direniş sürüyor yoldaş! 🔥")

@bot.message_handler(commands=['mod'])
def mod_help(message):
    if not is_admin(message): return
    bot.reply_to(message, "Komutlar: /airesim, /sarki, /muzik, /tagall, /ban, /mute, /kick, /warn")

print("🚩 Berxwedan Bot aktif!")
bot.infinity_polling()
