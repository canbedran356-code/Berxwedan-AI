import telebot
from groq import Groq
import os
import random
import subprocess

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Apo'nun felsefesi, direniş ve yoldaşlık üzerine güçlü konuşursun.
"""

def is_admin(message):
    if message.from_user.id == OWNER_ID:
        return True
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ["administrator", "creator"]
    except:
        return False

# ====================== ADMIN PANEL ======================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message):
        return bot.reply_to(message, "❌ Sadece admin kullanabilir.")
    text = """🛡️ **Admin Paneli**

`/ban <reply>` → Banla
`/unban <ID>` → Ban kaldır
`/mute <reply>` → Sustur
`/unmute <ID>` → Susturmayı kaldır
`/warn <reply>` → Uyarı ver (3 uyarı = mute)
`/unwarn <ID>` → Uyarı kaldır
`/banlist` → Ban listesi"""
    bot.reply_to(message, text)

# ====================== MODERASYON ======================
@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_admin(message): return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.kick_chat_member(message.chat.id, target.id)
    bot.reply_to(message, f"🚫 {target.first_name} banlandı.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if not is_admin(message): return
    try:
        uid = int(message.text.split()[1])
        bot.unban_chat_member(message.chat.id, uid)
        bot.reply_to(message, f"✅ {uid} banı kaldırıldı.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['mute'])
def mute(message):
    if not is_admin(message): return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
    bot.reply_to(message, f"🔇 {target.first_name} susturuldu.")

@bot.message_handler(commands=['unmute'])
def unmute(message):
    if not is_admin(message): return
    try:
        uid = int(message.text.split()[1])
        bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True)
        bot.reply_to(message, f"🔊 {uid} susturulması kaldırıldı.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['warn'])
def warn(message):
    if not is_admin(message): return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return bot.reply_to(message, "Reply ver.")
    user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
    w = user_warnings[target.id]
    bot.reply_to(message, f"⚠️ {target.first_name} uyarıldı ({w}/3)")
    if w >= 3:
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 {target.first_name} 3 uyarıdan susturuldu!")

@bot.message_handler(commands=['unwarn'])
def unwarn(message):
    if not is_admin(message): return
    try:
        uid = int(message.text.split()[1])
        if uid in user_warnings:
            user_warnings[uid] -= 1
            bot.reply_to(message, f"✅ {uid} uyarısı azaltıldı.")
        else:
            bot.reply_to(message, "Uyarı yok.")
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['banlist'])
def banlist(message):
    if not is_admin(message): return
    bot.reply_to(message, "Banlı kimse yok.")

# ====================== ŞARKI İNDİRME (İsim ile) ======================
@bot.message_handler(commands=['sarki'])
def sarki(message):
    query = " ".join(message.text.split()[1:]).strip()
    if not query:
        return bot.reply_to(message, "❌ Şarkı ismi veya link gir!")
    bot.reply_to(message, f"🎵 '{query}' aranıyor...")
    try:
        # İsim ile arama + indirme
        filename = f"devrim_{random.randint(1000,9999)}.mp3"
        subprocess.run(['yt-dlp', f"ytsearch:{query}", '--extract-audio', '--audio-format', 'mp3', '-o', filename], check=True, timeout=120)
        with open(filename, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption=f"🎵 {query} - Berxwedan!")
        os.remove(filename)
    except:
        bot.reply_to(message, "❌ Şarkı bulunamadı veya indirilemedi.")

# ====================== DİĞER ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 Berxwedan Bot aktif! Direniş sürüyor yoldaş! 🔥")

@bot.message_handler(commands=['mod'])
def mod(message):
    bot.reply_to(message, "Admin paneli için /admin yaz.")

print("🚩 Berxwedan Bot AKTİF!")
bot.infinity_polling()
