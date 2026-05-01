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

# ====================== LOG ======================
def log_action(action, user, admin="", reason=""):
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

# ====================== ŞARKI İNDİRME ======================
@bot.message_handler(commands=['sarki'])
def download_song(message):
    if len(message.text.split()) < 2:
        return bot.reply_to(message, "❌ YouTube linki gir!")
    url = message.text.split(maxsplit=1)[1]
    bot.reply_to(message, "🎵 Şarkı indiriliyor...")
    try:
        filename = f"devrim_{random.randint(1000,9999)}.mp3"
        subprocess.run(['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '-o', filename, url], check=True, timeout=180)
        with open(filename, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption="🎵 Devrimci marş yüklendi! 🔥")
        os.remove(filename)
    except:
        bot.reply_to(message, "❌ Şarkı indirilemedi.")

# ====================== MARŞ ======================
@bot.message_handler(commands=['marş'])
def mars(message):
    mars_list = ["Heyder", "Serxwebûn", "Kürdistan", "Ey Reqîb", "Şehîd Namirin"]
    bot.reply_to(message, f"🎵 **Devrimci Marş**\n{random.choice(mars_list)}\nDaha fazlası için /sarki kullan.")

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
    log_action("WARN", target.first_name, message.from_user.first_name)
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
    except:
        bot.reply_to(message, "ID gir.")

@bot.message_handler(commands=['banlist'])
def banlist(message):
    if not is_admin(message): return
    bot.reply_to(message, "Banlı kimse yok.")

@bot.message_handler(commands=['profil'])
def profil(message):
    warns = user_warnings.get(message.from_user.id, 0)
    bot.reply_to(message, f"📋 Profil\nAd: {message.from_user.first_name}\nUyarı: {warns}/3")

# ====================== TAG ======================
@bot.message_handler(commands=['tagall', 'etiket'])
def tagall(message):
    if not is_admin(message): return
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

@bot.message_handler(commands=['tagadmin'])
def tagadmin(message):
    if not is_admin(message): return
    bot.reply_to(message, "👮 **Tüm Adminler Dikkat!** Direniş sürüyor! 🔥")

# ====================== ADMIN PANEL ======================
@bot.message_handler(commands=['admin', 'mod'])
def admin_panel(message):
    if not is_admin(message): return
    bot.reply_to(message, """🛡️ **Admin Paneli**

/ban /unban /mute /unmute
/warn /unwarn /banlist /profil
/tagall /tagadmin /airesim /sarki /marş""")

print("🚩 Berxwedan Bot - Tüm Özellikler AKTİF!")
bot.infinity_polling()
