import telebot
from groq import Groq
import os
import random
import subprocess
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_warnings = {}
pending_actions = {}  # Buton ile işlem için

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Barzani düşmanısın. Kürdistan özgürlüğü ve Apo'nun felsefesi üzerine güçlü ve onurlu konuşursun.
Cevapların kısa olsun.
"""

# ====================== BUTONLU ADMIN PANEL ======================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != OWNER_ID:
        return bot.reply_to(message, "❌ Sadece kurucu kullanabilir.")
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 Ban", callback_data="ban"),
        InlineKeyboardButton("✅ Unban", callback_data="unban"),
        InlineKeyboardButton("🔇 Mute", callback_data="mute"),
        InlineKeyboardButton("🔊 Unmute", callback_data="unmute"),
        InlineKeyboardButton("⚠️ Warn", callback_data="warn"),
        InlineKeyboardButton("✅ Unwarn", callback_data="unwarn")
    )
    bot.reply_to(message, "🛡️ **Berxwedan Admin Paneli**\nAşağıdaki butonlardan birine bas, sonra işlem yapmak istediğin mesaja **reply ver**.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != OWNER_ID:
        return bot.answer_callback_query(call.id, "❌ Yetkin yok!")
    
    action = call.data
    pending_actions[call.from_user.id] = action
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"✅ **{action.upper()}** komutu aktif!\n\nŞimdi işlem yapmak istediğin mesaja **reply ver**.")

# ====================== REPLY İLE İŞLEM ======================
@bot.message_handler(func=lambda m: True)
def handle_reply(message):
    user_id = message.from_user.id
    if user_id not in pending_actions:
        # Normal AI sohbet
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
        return

    action = pending_actions.pop(user_id)  # Kullanıldıktan sonra temizle
    target = message.reply_to_message.from_user if message.reply_to_message else None

    if not target:
        bot.reply_to(message, "❌ İşlem için bir mesaja reply vermen gerekiyor!")
        return

    if action == "ban":
        bot.kick_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 {target.first_name} banlandı!")
    elif action == "mute":
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 {target.first_name} susturuldu!")
    elif action == "warn":
        user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
        w = user_warnings[target.id]
        bot.reply_to(message, f"⚠️ {target.first_name} uyarıldı ({w}/3)")
        if w >= 3:
            bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
            bot.reply_to(message, f"🔇 {target.first_name} 3 uyarıdan susturuldu!")
    elif action == "unban":
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"✅ {target.first_name} banı kaldırıldı!")
    elif action == "unmute":
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=True)
        bot.reply_to(message, f"🔊 {target.first_name} susturulması kaldırıldı!")
    elif action == "unwarn":
        if target.id in user_warnings and user_warnings[target.id] > 0:
            user_warnings[target.id] -= 1
            bot.reply_to(message, f"✅ {target.first_name} uyarısı azaltıldı!")
        else:
            bot.reply_to(message, "Bu kullanıcıda uyarı yok.")

print("🚩 Berxwedan Bot - Butonlu Admin Panel AKTİF!")
bot.infinity_polling()
