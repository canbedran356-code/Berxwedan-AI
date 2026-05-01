import telebot
from groq import Groq
import os
import random
import subprocess
import re
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_warnings = {}
user_notes = {}
banned_users = set()

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Barzani düşmanısın. Kürdistan özgürlüğü ve Apo'nun felsefesi üzerine güçlü ve onurlu konuşursun.
"""

# ====================== LOG SİSTEMİ ======================
def log_action(action, target, admin, reason="", duration=None):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dur = f" | Süre: {duration}" if duration else ""
    log_text = f"[{time}] {action} | Hedef: {target} | Admin: {admin}{dur} | Sebep: {reason}"
    print(log_text)

# ====================== YARDIMCI FONKSİYONLAR ======================
def is_owner(uid):
    return uid == OWNER_ID

def is_admin(message):
    if is_owner(message.from_user.id):
        return True
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ["administrator", "creator"]
    except:
        return False

def parse_time(time_str):
    if not time_str:
        return None
    match = re.match(r'(\d+)([mhd])', time_str.lower())
    if not match:
        return None
    num, unit = match.groups()
    num = int(num)
    if unit == 'm': return timedelta(minutes=num)
    if unit == 'h': return timedelta(hours=num)
    if unit == 'd': return timedelta(days=num)
    return None

def get_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    text = message.text or ""
    # @username
    if "@" in text:
        try:
            username = text.split("@")[1].split()[0]
            return bot.get_chat(username)
        except:
            pass
    # ID
    parts = text.split()
    if len(parts) > 1 and parts[1].isdigit():
        try:
            return bot.get_chat(int(parts[1]))
        except:
            pass
    return None

# ====================== BUTONLU ADMIN PANEL ======================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Sadece kurucu kullanabilir.")
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 Ban", callback_data="ban"),
        InlineKeyboardButton("✅ Unban", callback_data="unban"),
        InlineKeyboardButton("🔇 Mute", callback_data="mute"),
        InlineKeyboardButton("🔊 Unmute", callback_data="unmute"),
        InlineKeyboardButton("⚠️ Warn", callback_data="warn"),
        InlineKeyboardButton("✅ Unwarn", callback_data="unwarn"),
        InlineKeyboardButton("👢 Kick", callback_data="kick")
    )
    bot.reply_to(message, "🛡️ **Berxwedan Admin Paneli**\nKomutları reply veya @kullanıcıadı ile kullan.", reply_markup=markup)

# ====================== MODERASYON ======================
@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_owner(message.from_user.id): return
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver, @kullanıcıadı veya ID gir.")
    time_str = message.text.split(maxsplit=2)[1] if len(message.text.split()) > 1 else None
    duration = parse_time(time_str)
    bot.kick_chat_member(message.chat.id, target.id)
    banned_users.add(target.id)
    log_action("BAN", target.first_name or target.id, message.from_user.first_name, duration=duration)
    bot.reply_to(message, f"🚫 {target.first_name or target.id} banlandı.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if not is_owner(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        bot.unban_chat_member(message.chat.id, uid)
        if uid in banned_users:
            banned_users.remove(uid)
        log_action("UNBAN", uid, message.from_user.first_name)
        bot.reply_to(message, f"✅ {uid} banı kaldırıldı.")
    except:
        bot.reply_to(message, "Kullanım: /unban <ID>")

@bot.message_handler(commands=['mute'])
def mute(message):
    if not is_owner(message.from_user.id): return
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver, @kullanıcıadı veya ID gir.")
    bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
    log_action("MUTE", target.first_name or target.id, message.from_user.first_name)
    bot.reply_to(message, f"🔇 {target.first_name or target.id} susturuldu.")

@bot.message_handler(commands=['unmute'])
def unmute(message):
    if not is_owner(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True)
        log_action("UNMUTE", uid, message.from_user.first_name)
        bot.reply_to(message, f"🔊 {uid} susturulması kaldırıldı.")
    except:
        bot.reply_to(message, "Kullanım: /unmute <ID>")

@bot.message_handler(commands=['warn'])
def warn(message):
    if not is_owner(message.from_user.id): return
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver, @kullanıcıadı veya ID gir.")
    user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
    w = user_warnings[target.id]
    log_action("WARN", target.first_name or target.id, message.from_user.first_name)
    bot.reply_to(message, f"⚠️ {target.first_name or target.id} uyarıldı ({w}/3)")
    if w >= 3:
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 {target.first_name or target.id} 3 uyarıdan susturuldu!")

@bot.message_handler(commands=['unwarn'])
def unwarn(message):
    if not is_owner(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        if uid in user_warnings:
            user_warnings[uid] -= 1
            log_action("UNWARN", uid, message.from_user.first_name)
            bot.reply_to(message, f"✅ {uid} uyarısı azaltıldı.")
    except:
        bot.reply_to(message, "Kullanım: /unwarn <ID>")

@bot.message_handler(commands=['kick'])
def kick(message):
    if not is_owner(message.from_user.id): return
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver, @kullanıcıadı veya ID gir.")
    bot.kick_chat_member(message.chat.id, target.id)
    bot.unban_chat_member(message.chat.id, target.id)
    log_action("KICK", target.first_name or target.id, message.from_user.first_name)
    bot.reply_to(message, f"👢 {target.first_name or target.id} gruptan atıldı.")

# ====================== AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if "berxwedan bot" in (message.text or "").lower():
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": message.text}],
                temperature=0.8,
                max_tokens=600,
            )
            bot.reply_to(message, completion.choices[0].message.content)
        except:
            bot.reply_to(message, "Yoldaş, AI yoğun.")

print("🚩 Berxwedan Bot - Genişletilmiş Moderasyon AKTİF!")
bot.infinity_polling()
