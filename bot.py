import telebot
import os
import random
import subprocess
from openai import OpenAI
from datetime import timedelta

# ====================== AYARLAR ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Abdullah Öcalan felsefesi, direniş, yoldaşlık ve özgürlük mücadelesi üzerine güçlü, onurlu ve motive edici konuşursun.
Emperyalizme, faşizme karşı sert duruşun var.
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

# ====================== DEEPSEEK AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return

    user_id = message.chat.id
    if user_id not in user_histories:
        user_histories[user_id] = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
    messages.append({"role": "user", "content": message.text})

    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.85,
            max_tokens=1000,
        )
        reply = completion.choices[0].message.content

        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        bot.reply_to(message, reply)
    except:
        bot.reply_to(message, "Yoldaş, AI şu anda yoğun. Biraz sonra tekrar dene.")

# ====================== GELİŞMİŞ AI RESİM ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    prompt = " ".join(message.text.split()[1:]).strip()
    if not prompt:
        prompt = "devrimci Kürt gerilla"

    bot.reply_to(message, "🖼️ Devrimci sahne çiziliyor... 🔥")

    try:
        full_prompt = (
            f"{prompt}, handsome young Kurdish revolutionary, sharp jawline, intense eyes, "
            "thick black hair, proud warrior, Kurdistan mountains, red star flag, "
            "resistance atmosphere, cinematic lighting, dramatic, highly detailed, epic, 8k"
        )
        clean = full_prompt.replace(" ", "%20").replace(",", "%2C")
        seed = random.randint(100000, 999999)
        url = f"https://image.pollinations.ai/prompt/{clean}?width=1024&height=1024&seed={seed}&model=flux&enhance=true"

        bot.send_photo(message.chat.id, url, caption=f"🖼️ **{prompt}**\n🚩 Berxwedan Serxwebûn!")
    except:
        bot.reply_to(message, "❌ Resim üretilemedi.")

# ====================== ŞARKI İNDİRME ======================
@bot.message_handler(commands=['sarki'])
def download_song(message):
    if len(message.text.split()) < 2:
        return bot.reply_to(message, "❌ YouTube linki gir!\n`/sarki https://youtube.com/...`")
    
    url = message.text.split(maxsplit=1)[1]
    bot.reply_to(message, "🎵 Şarkı indiriliyor yoldaş...")
    try:
        filename = f"devrim_{random.randint(10000,99999)}.mp3"
        subprocess.run(['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '-o', filename, url], 
                       check=True, timeout=180)
        with open(filename, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption="🎵 Devrimci marş yüklendi! 🔥")
        os.remove(filename)
    except:
        bot.reply_to(message, "❌ Şarkı indirilemedi.")

# ====================== KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* Direniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim'])
def mod_help(message):
    if not is_admin(message) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Bu komut sadece adminler içindir.")
    
    text = """🚩 **Berxwedan Bot - Gelişmiş Komutlar**

**🎨 AI & Medya**
• `/airesim <prompt>` → Devrimci gerilla resmi
• `/sarki <youtube link>` → Şarkı indir
• `/muzik` → Rastgele marş

**👥 Grup**
• `/tagall` → Tüm yoldaşları etiketle

**🛡️ Moderasyon**
• `/ban` • `/mute` • `/kick` • `/warn` • `/unwarn`
• `/unban` • `/unmute`

Sadece admin ve owner kullanabilir."""
    bot.reply_to(message, text, parse_mode="Markdown")

# Moderasyon komutları (kısaltılmış)
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
        bot.reply_to(message, f"🚫 {target.first_name} banlandı!")

@bot.message_handler(commands=['muzik'])
def send_music(message):
    bot.send_audio(message.chat.id, "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", 
                  caption="🎵 Devrimci marşlar yoldaş! 🔥")

@bot.message_handler(commands=['tagall', 'etiket'])
def tagall(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Sadece admin kullanabilir.")
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

print("🚩 Berxwedan Bot - Gelişmiş Versiyon AKTİF!")
bot.infinity_polling()
