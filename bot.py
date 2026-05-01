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

# ====================== AI RESİM ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    prompt = " ".join(message.text.split()[1:]) if len(message.text.split()) > 1 else "Kürdistan direnişi"
    bot.reply_to(message, "🖼️ AI resim üretiliyor yoldaş...")

    try:
        images = [
            "https://picsum.photos/id/1015/1024/1024",
            "https://picsum.photos/id/133/1024/1024",
            "https://picsum.photos/id/201/1024/1024",
        ]
        bot.send_photo(message.chat.id, random.choice(images),
                      caption=f"🖼️ {prompt}\n🚩 Berxwedan Serxwebûn!")
    except:
        bot.reply_to(message, "🖼️ Resim üretilemedi.")

# ====================== YOUTUBE ŞARKI İNDİR ======================
@bot.message_handler(commands=['sarki'])
def download_song(message):
    if len(message.text.split()) < 2:
        return bot.reply_to(message, "❌ YouTube linki gir!\n`/sarki https://youtube.com/watch?v=...`")

    url = message.text.split(maxsplit=1)[1]
    bot.reply_to(message, "🎵 Şarkı indiriliyor...")

    try:
        filename = f"devrim_{random.randint(1000,9999)}.mp3"
        subprocess.run(['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '-o', filename, url], 
                       check=True, timeout=150)
        
        with open(filename, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, caption="🎵 İndirildi! 🔥 Berxwedan!")
        os.remove(filename)
    except:
        bot.reply_to(message, "❌ İndirme başarısız. Linki kontrol et.")

# ====================== ESKİ KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* \nDireniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim'])
def mod_help(message):
    if not is_admin(message): return
    text = """🚩 **Berxwedan Bot Komutları**

• `/airesim <prompt>` → AI resim
• `/sarki <youtube link>` → Şarkı indir
• `/muzik` → Rastgele müzik
• `/resim` → Direniş resmi
• `/tagall` → Grubu etiketle

**Moderasyon:** `/ban`, `/mute`, `/kick`, `/warn` vb."""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Yetkin yok.")
    target = get_target(message)
    if not target: return bot.reply_to(message, "Reply ver veya ID gir.")
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
    bot.reply_to(message, f"👢 {target.first_name} atıldı.")

@bot.message_handler(commands=['warn'])
def warn(message):
    if not is_admin(message): return
    target = get_target(message)
    if not target: return
    user_warnings[target.id] = user_warnings.get(target.id, 0) + 1
    w = user_warnings[target.id]
    bot.reply_to(message, f"⚠️ {target.first_name} uyarıldı ({w}/3)")
    if w >= 3:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 {target.first_name} banlandı (3 uyarı)!")

@bot.message_handler(commands=['muzik'])
def send_music(message):
    music_list = ["https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"]
    try:
        bot.send_audio(message.chat.id, random.choice(music_list), caption="🎵 Devrimci marş! 🔥")
    except:
        bot.reply_to(message, "Müzik gönderilemedi.")

@bot.message_handler(commands=['resim'])
def send_image(message):
    try:
        bot.send_photo(message.chat.id, "https://picsum.photos/id/1015/800/600", 
                      caption="🌟 Kürdistan direnişi sürüyor! 🚩")
    except:
        bot.reply_to(message, "Resim gönderilemedi.")

@bot.message_handler(commands=['tagall', 'etiket'])
def tagall(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Sadece admin kullanabilir.")
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

# ====================== ANA SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return

    user_id = message.chat.id
    if user_id not in user_histories:
        user_histories[user_id] = []

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
    full_messages.append({"role": "user", "content": message.text})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_messages,
            temperature=0.85,
            max_tokens=1024,
        )
        reply = completion.choices[0].message.content

        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        bot.reply_to(message, reply)
    except:
        bot.reply_to(message, "Yoldaş, bir hata oluştu.")

print("🚩 Berxwedan Bot TAM AKTİF!")
bot.infinity_polling()
