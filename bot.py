import telebot
from groq import Groq
import os
import random
import subprocess
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}
banned_users = []

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

# ====================== AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message.text}],
            temperature=0.85,
            max_tokens=800,
        )
        bot.reply_to(message, completion.choices[0].message.content)
    except:
        bot.reply_to(message, "Yoldaş, AI yoğun. Biraz sonra tekrar dene.")

# ====================== PROFIL & UYARI ======================
@bot.message_handler(commands=['profil'])
def profil(message):
    uid = message.from_user.id
    warns = user_warnings.get(uid, 0)
    bot.reply_to(message, f"📋 **Profilin**\nAd: {message.from_user.first_name}\nUyarı: {warns}/3")

@bot.message_handler(commands=['warn'])
def warn(message):
    if not is_admin(message): return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
    w = user_warnings[target.id]
    bot.reply_to(message, f"⚠️ {target.first_name} uyarıldı ({w}/3)")
    if w >= 3:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 {target.first_name} banlandı!")

# ====================== BAN LİSTESİ ======================
@bot.message_handler(commands=['banlist'])
def banlist(message):
    if not is_admin(message): return
    if not banned_users:
        bot.reply_to(message, "Banlı kimse yok.")
    else:
        bot.reply_to(message, "🚫 Banlı Kullanıcılar:\n" + "\n".join(str(uid) for uid in banned_users))

# ====================== TAG KOMUTLARI ======================
@bot.message_handler(commands=['tagall', 'etiket'])
def tagall(message):
    if not is_admin(message): return
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

@bot.message_handler(commands=['tagadmin'])
def tagadmin(message):
    if not is_admin(message): return
    bot.reply_to(message, "👮 **Tüm Adminler Dikkat!** Direniş sürüyor! 🔥")

# ====================== HAVA DURUMU ======================
@bot.message_handler(commands=['hava'])
def hava(message):
    city = " ".join(message.text.split()[1:]).strip() or "Diyarbakir"
    try:
        # Örnek açık hava API (ücretsiz)
        url = f"http://wttr.in/{city}?format=3"
        r = requests.get(url, timeout=5)
        bot.reply_to(message, f"🌤️ **{city}**\n{r.text}")
    except:
        bot.reply_to(message, "Hava durumu şu anda alınamadı.")

# ====================== DİĞER ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 Berxwedan Bot aktif! Direniş sürüyor yoldaş! 🔥")

@bot.message_handler(commands=['mod'])
def mod_help(message):
    bot.reply_to(message, """🚩 **Komutlar:**
• /airesim → Resim
• /sarki → Şarkı
• /profil → Profil
• /tagall → Etiket
• /tagadmin → Admin etiket
• /banlist → Ban listesi
• /hava <şehir> → Hava durumu""")

print("🚩 Berxwedan Bot AKTİF!")
bot.infinity_polling()
