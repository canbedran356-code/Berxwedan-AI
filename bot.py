import telebot
from groq import Groq
import os
import random
import subprocess
import requests
from datetime import datetime

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
Kürdistan özgürlüğü, Apo'nun felsefesi, direniş ve yoldaşlık üzerine güçlü ve onurlu konuşursun.
"""

# ====================== LOG SİSTEMİ ======================
def log_action(action, user, admin, reason=""):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time}] {action} | Kullanıcı: {user} | Admin: {admin} | Sebep: {reason}")

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

def get_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    return None

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
            max_tokens=900,
        )
        bot.reply_to(message, completion.choices[0].message.content)
    except:
        bot.reply_to(message, "Yoldaş, AI yoğun. Biraz sonra tekrar dene.")

# ====================== HOŞGELDİN & GÜLE GÜLE ======================
@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for member in message.new_chat_members:
        if member.id != bot.get_me().id:
            bot.send_message(message.chat.id, f"🌟 Hoş geldin **{member.first_name}**!\nDevrimci saflara katıldın. Berxwedan Serxwebûn! 🚩")

@bot.message_handler(content_types=['left_chat_member'])
def goodbye(message):
    member = message.left_chat_member
    if member.id != bot.get_me().id:
        bot.send_message(message.chat.id, f"⚔️ **{member.first_name}** ayrıldı.\nDireniş devam ediyor! Berxwedan! 🔥")

# ====================== MODERASYON ======================
@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_admin(message): return
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.kick_chat_member(message.chat.id, target.id)
    log_action("BAN", target.first_name, message.from_user.first_name)
    bot.reply_to(message, f"🚫 {target.first_name} banlandı.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if not is_admin(message): return
    try:
        uid = int(message.text.split()[1])
        bot.unban_chat_member(message.chat.id, uid)
        log_action("UNBAN", uid, message.from_user.first_name)
        bot.reply_to(message, f"✅ {uid} banı kaldırıldı.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['mute'])
def mute(message):
    if not is_admin(message): return
    target = get_target(message)
    if not target: return
    bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
    log_action("MUTE", target.first_name, message.from_user.first_name)
    bot.reply_to(message, f"🔇 {target.first_name} susturuldu.")

@bot.message_handler(commands=['unmute'])
def unmute(message):
    if not is_admin(message): return
    try:
        uid = int(message.text.split()[1])
        bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True)
        log_action("UNMUTE", uid, message.from_user.first_name)
        bot.reply_to(message, f"🔊 {uid} susturulması kaldırıldı.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['warn'])
def warn(message):
    if not is_admin(message): return
    target = get_target(message)
    if not target: return
    user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
    w = user_warnings[target.id]
    log_action("WARN", target.first_name, message.from_user.first_name, f"{w}. uyarı")
    bot.reply_to(message, f"⚠️ {target.first_name} uyarıldı ({w}/3)")
    if w >= 3:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 {target.first_name} banlandı!")

@bot.message_handler(commands=['unwarn'])
def unwarn(message):
    if not is_admin(message): return
    try:
        uid = int(message.text.split()[1])
        if uid in user_warnings:
            user_warnings[uid] -= 1
            log_action("UNWARN", uid, message.from_user.first_name)
            bot.reply_to(message, f"✅ {uid} uyarısı azaltıldı.")
        else:
            bot.reply_to(message, "Uyarı yok.")
    except:
        bot.reply_to(message, "ID gir.")

# ====================== DİĞER KOMUTLAR ======================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message): return
    text = """🛡️ **Admin Paneli**

`/ban` `/unban` `/mute` `/unmute`
`/warn` `/unwarn`
`/banlist` `/profil`
`/tagall` `/tagadmin`
`/marş` `/hava` `/cevir` `/oyun`"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['marş'])
def mars(message):
    marşlar = ["Heyder", "Kürdistan", "Serxwebûn", "Ey Reqîb"]
    bot.reply_to(message, f"🎵 **Devrimci Marşlar**\n• {random.choice(marşlar)}\nDaha fazlası için /sarki kullan.")

@bot.message_handler(commands=['hava'])
def hava(message):
    city = " ".join(message.text.split()[1:]).strip() or "Diyarbakir"
    try:
        r = requests.get(f"http://wttr.in/{city}?format=3", timeout=5)
        bot.reply_to(message, f"🌤️ **{city}**\n{r.text}")
    except:
        bot.reply_to(message, "Hava durumu alınamadı.")

@bot.message_handler(commands=['tagall'])
def tagall(message):
    if not is_admin(message): return
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

@bot.message_handler(commands=['tagadmin'])
def tagadmin(message):
    if not is_admin(message): return
    bot.reply_to(message, "👮 **Tüm Adminler Dikkat!** Direniş sürüyor! 🔥")

print("🚩 Berxwedan Bot AKTİF!")
bot.infinity_polling()
