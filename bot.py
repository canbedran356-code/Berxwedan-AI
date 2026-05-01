import telebot
from groq import Groq
import os
import random
import subprocess
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
    log_text = f"[{time}] {action} | Kullanıcı: {user} | Admin: {admin} | Sebep: {reason}"
    print(log_text)
    # İstersen gruba da log atabiliriz: bot.send_message(chat_id, log_text)

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
    elif len(message.text.split()) > 1:
        try:
            uid = int(message.text.split()[1])
            return bot.get_chat_member(message.chat.id, uid).user
        except:
            return None
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

# ====================== ADMIN PANEL ======================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message):
        return bot.reply_to(message, "❌ Sadece admin kullanabilir.")
    text = """🛡️ **Berxwedan Admin Paneli**

`/ban <reply>` → Banla
`/unban <ID>` → Ban kaldır
`/mute <reply>` → Sustur
`/unmute <ID>` → Susturmayı kaldır
`/warn <reply>` → Uyarı ver
`/unwarn <ID>` → Uyarı kaldır
`/banlist` → Ban listesi
`/profil` → Profil"""
    bot.reply_to(message, text, parse_mode="Markdown")

# ====================== MODERASYON ======================
@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Yetkin yok.")
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.kick_chat_member(message.chat.id, target.id)
    log_action("BAN", target.first_name, message.from_user.first_name)
    bot.reply_to(message, f"🚫 **{target.first_name}** banlandı.")

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
    bot.reply_to(message, f"🔇 **{target.first_name}** susturuldu.")

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
    bot.reply_to(message, f"⚠️ **{target.first_name}** uyarıldı ({w}/3)")
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
            if user_warnings[uid] <= 0:
                del user_warnings[uid]
            log_action("UNWARN", uid, message.from_user.first_name)
            bot.reply_to(message, f"✅ {uid} uyarısı azaltıldı.")
        else:
            bot.reply_to(message, "Bu kullanıcıda uyarı yok.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['banlist'])
def banlist(message):
    if not is_admin(message): return
    bot.reply_to(message, "🚫 Banlı kimse yok." if not user_warnings else f"Banlılar: {list(user_warnings.keys())}")

@bot.message_handler(commands=['profil'])
def profil(message):
    uid = message.from_user.id
    warns = user_warnings.get(uid, 0)
    bot.reply_to(message, f"📋 **Profilin**\nAd: {message.from_user.first_name}\nUyarı: {warns}/3")

print("🚩 Berxwedan Bot - Tam Moderasyon AKTİF!")
bot.infinity_polling()
