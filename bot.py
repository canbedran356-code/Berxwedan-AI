import telebot
from groq import Groq
import os
import random
import subprocess
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Apo'nun felsefesi üzerine konuşursun. Kurucun Bedran Can 
"""

# ====================== ADMIN PANELİ (BUTONLU) ======================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != OWNER_ID:
        return bot.reply_to(message, "❌ Sadece kurucu kullanabilir.")
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("Ban", callback_data="ban"),
        InlineKeyboardButton("Unban", callback_data="unban"),
        InlineKeyboardButton("Mute", callback_data="mute"),
        InlineKeyboardButton("Unmute", callback_data="unmute"),
        InlineKeyboardButton("Warn", callback_data="warn"),
        InlineKeyboardButton("Unwarn", callback_data="unwarn")
    )
    bot.reply_to(message, "🛡️ **Admin Paneli**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != OWNER_ID:
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"Komut: /{call.data} - Reply ile kullan.")

# ====================== MODERASYON (REPLY İLE) ======================
@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != OWNER_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.kick_chat_member(message.chat.id, target.id)
    bot.reply_to(message, f"🚫 {target.first_name} banlandı.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id != OWNER_ID: return
    try:
        uid = int(message.text.split()[1])
        bot.unban_chat_member(message.chat.id, uid)
        bot.reply_to(message, f"✅ {uid} banı kaldırıldı.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['mute'])
def mute(message):
    if message.from_user.id != OWNER_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
    bot.reply_to(message, f"🔇 {target.first_name} susturuldu.")

@bot.message_handler(commands=['unmute'])
def unmute(message):
    if message.from_user.id != OWNER_ID: return
    try:
        uid = int(message.text.split()[1])
        bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True)
        bot.reply_to(message, f"🔊 {uid} susturulması kaldırıldı.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['warn'])
def warn(message):
    if message.from_user.id != OWNER_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
    w = user_warnings[target.id]
    bot.reply_to(message, f"⚠️ {target.first_name} uyarıldı ({w}/3)")
    if w >= 3:
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 {target.first_name} susturuldu!")

@bot.message_handler(commands=['unwarn'])
def unwarn(message):
    if message.from_user.id != OWNER_ID: return
    try:
        uid = int(message.text.split()[1])
        if uid in user_warnings:
            user_warnings[uid] -= 1
            bot.reply_to(message, f"✅ {uid} uyarısı azaltıldı.")
    except:
        bot.reply_to(message, "ID gir.")

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
        bot.send_message(message.chat.id, f"⚔️ **{member.first_name}** ayrıldı.\nDireniş devam ediyor yoldaşlar! Berxwedan! 🔥")

# ====================== AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if "berxwedan bot" in (message.text or "").lower():
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": message.text}],
                temperature=0.8,
            )
            bot.reply_to(message, completion.choices[0].message.content)
        except:
            bot.reply_to(message, "Yoldaş, AI yoğun.")

print("🚩 Berxwedan Bot AKTİF!")
bot.infinity_polling()
