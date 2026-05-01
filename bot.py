import telebot
from groq import Groq
import os
import re
import random
import subprocess
from datetime import timedelta

# ====================== AYARLAR ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

# ====================== DEVRİMCİ SİSTEM PROMPT ======================
SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci ve onurlu bir botsun.
Kürdistan özgürlüğü, Abdullah Öcalan felsefesi, direniş ve yoldaşlık üzerine konuşursun.
Güçlü, cesur, yoldaşça ve motive edici bir üslubun var.
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

def should_reply(message):
    if message.chat.type == "private":
        return True
    text = (message.text or "").lower()
    return BOT_TRIGGER in text or (bot.get_me().username and bot.get_me().username.lower() in text)

def get_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    return None

# ====================== GELİŞTİRİLMİŞ AI RESİM ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    prompt = " ".join(message.text.split()[1:]).strip()
    if not prompt:
        prompt = "yakışıklı Kürt devrimci genç"

    bot.reply_to(message, "🖼️ Yakışıklı devrimci gençler çiziliyor... 🔥")

    try:
        enhanced_prompt = (
            f"{prompt}, extremely handsome young Kurdish revolutionary, "
            "sharp facial features, intense dark eyes, charismatic expression, "
            "thick black hair, strong jawline, traditional Kurdish scarf, "
            "Kurdistan mountains background, red star flag, cinematic lighting, "
            "dramatic atmosphere, highly detailed face, realistic, 8k, masterpiece"
        )

        clean = enhanced_prompt.replace(" ", "%20").replace(",", "%2C")
        seed = random.randint(100000, 999999)

        url = f"https://image.pollinations.ai/prompt/{clean}?width=1024&height=1024&seed={seed}&model=flux&safe=false&enhance=true"

        bot.send_photo(message.chat.id, url, 
                      caption=f"🖼️ **{prompt}**\n🚩 Berxwedan Serxwebûn!")
    except:
        bot.reply_to(message, "❌ Resim üretilemedi.")

# ====================== ŞARKI İNDİRME ======================
@bot.message_handler(commands=['sarki'])
def download_song(message):
    if len(message.text.split()) < 2:
        return bot.reply_to(message, "❌ YouTube linki girin.\n`/sarki https://youtube.com/...`")

    url = message.text.split(maxsplit=1)[1]
    bot.reply_to(message, "🎵 Şarkı indiriliyor...")

    try:
        filename = f"devrim_{random.randint(10000,99999)}.mp3"
        subprocess.run(['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '-o', filename, url], 
                       check=True, timeout=180)

        with open(filename, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption="🎵 Berxwedan Marşı yüklendi! 🔥")
        os.remove(filename)
    except:
        bot.reply_to(message, "❌ İndirme başarısız.")

# ====================== KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* Direniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim'])
def mod_help(message):
    if not is_admin(message):
        return bot.reply_to(message, "❌ Bu komut sadece adminler içindir.")
    
    text = """🚩 **Berxwedan Bot Komutları**

**🎨 AI & Medya**
• `/airesim <açıklama>` → Yakışıklı devrimci gençler çizer
• `/sarki <youtube link>` → Şarkı indir
• `/muzik` → Rastgele marş
• `/resim` → Klasik direniş resmi

**👥 Grup**
• `/tagall` → Herkesi etiketle

**🛡️ Moderasyon**
• `/ban`, `/mute`, `/kick`, `/warn`, `/unwarn`
• `/unban`, `/unmute`

Sadece admin ve owner kullanabilir."""
    bot.reply_to(message, text, parse_mode="Markdown")

# ====================== MODERASYON ======================
@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Yetkin yok.")
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver.")
    bot.kick_chat_member(message.chat.id, target.id)
    bot.reply_to(message, f"🚫 {target.first_name} banlandı.")

@bot.message_handler(commands=['mute'])
def mute(message):
    if not is_admin(message): return
    target = get_target(message)
    if not target: return
    bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
    bot.reply_to(message, f"🔇 {target.first_name} susturuldu.")

@bot.message_handler(commands=['kick'])
def kick(message):
    if not is_admin(message): return
    target = get_target(message)
    if not target: return
    bot.kick_chat_member(message.chat.id, target.id)
    bot.unban_chat_member(message.chat.id, target.id)
    bot.reply_to(message, f"👢 {target.first_name} at
