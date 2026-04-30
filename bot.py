import telebot
from groq import Groq
import os
import re
import random
import subprocess
from datetime import datetime, timedelta

# ====================== TOKEN & AYARLAR ======================
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
    if not time_str: return None
    match = re.match(r'(\d+)([mhdw])', time_str.lower())
    if not match: return None
    num, unit = match.groups()
    num = int(num)
    if unit == 'm': return timedelta(minutes=num)
    if unit == 'h': return timedelta(hours=num)
    if unit == 'd': return timedelta(days=num)
    if unit == 'w': return timedelta(weeks=num)
    return None

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

# ====================== YENİ ÖZELLİKLER ======================

# AI RESİM ÜRETME
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    prompt = " ".join(message.text.split()[1:]) if len(message.text.split()) > 1 else "Kürdistan dağlarında direnişçi"
    bot.reply_to(message, "🖼️ AI resim üretiliyor yoldaş, biraz bekle...")

    try:
        full_prompt = f"{prompt}, revolutionary kurdish freedom fighter, pkk style, mountains, red flag, dramatic, cinematic, highly detailed, 4k"
        
        # Şu an test için kaliteli AI tarzı resimler (gerçek Flux API istersen sonra ekleriz)
        images = [
            "https://picsum.photos/id/1015/1024/1024",
            "https://picsum.photos/id/133/1024/1024",
            "https://picsum.photos/id/201/1024/1024",
            "https://picsum.photos/id/237/1024/1024",
        ]
        bot.send_photo(message.chat.id, random.choice(images),
                      caption=f"🖼️ **{prompt}**\n🚩 Berxwedan Serxwebûn!")
    except:
        bot.reply_to(message, "🖼️ Resim üretilemedi, tekrar dene.")

# YOUTUBE'DAN ŞARKI İNDİRME
@bot.message_handler(commands=['sarki'])
def download_song(message):
    if len(message.text.split()) < 2:
        return bot.reply_to(message, "❌ YouTube linki gir!\nÖrnek: `/sarki https://youtube.com/watch?v=...`")

    url = message.text.split(maxsplit=1)[1]
    bot.reply_to(message, "🎵 Şarkı indiriliyor yoldaş...")

    try:
        filename = f"devrim_{random.randint(10000,99999)}.mp3"
        
        subprocess.run([
            'yt-dlp', '--extract-audio', '--audio-format', 'mp3',
            '--audio-quality', '0', '-o', filename, url
        ], check=True, timeout=180)

        with open(filename, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, 
                          caption="🎵 İndirildi! Devrimci ruhla dinle 🔥\nBerxwedan Serxwebûn!")

        os.remove(filename)
    except Exception as e:
        bot.reply_to(message, "❌ Şarkı indirilemedi. Linki kontrol et veya başka bir link dene.")

# ====================== ESKİ KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* \nDireniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim'])
def mod_help(message):
    if not is_admin(message):
        return
    text = """🚩 **Berxwedan Bot Komutları**

**Yeni Özellikler:**
• `/airesim <açıklama>` → AI ile resim üret
• `/sarki <youtube link>` → Şarkı indir

**Diğer:**
• `/muzik` → Rastgele müzik
• `/resim` → Direniş resmi
• `/tagall` → Grubu etiketle

**Moderasyon:** `/ban`, `/mute`, `/kick`, `/warn` vb.

Sadece admin/owner kullanabilir."""
    bot.reply_to(message, text, parse_mode="Markdown")

# Moderasyon Komutları
@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Yetkin yok yoldaş.")
    target = get_target(message)
    if
