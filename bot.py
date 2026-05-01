import telebot
import os
import random
import subprocess
from openai import OpenAI

# ====================== AYARLAR ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Apo'nun felsefesi, direniş ve yoldaşlık üzerine güçlü, onurlu ve motive edici konuşursun.
"""

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
        bot.reply_to(message, reply)

        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})
        
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]
    except:
        bot.reply_to(message, "Yoldaş, AI yoğun. Biraz sonra tekrar dene.")

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
        return bot.reply_to(message, "❌ YouTube linki gir!\n`/sarki https://youtube.com/...`")
    
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

# ====================== KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* Direniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim'])
def mod_help(message):
    text = """🚩 **Berxwedan Bot Komutları**

• `/airesim <prompt>` → Devrimci resim
• `/sarki <youtube link>` → Şarkı indir
• `/muzik` → Rastgele marş
• `/tagall` → Grubu etiketle
• `/ban`, `/mute`, `/kick`, `/warn` → Moderasyon"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['muzik'])
def send_music(message):
    bot.send_audio(message.chat.id, "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", 
                  caption="🎵 Devrimci marşlar yoldaş! 🔥")

@bot.message_handler(commands=['tagall', 'etiket'])
def tagall(message):
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

print("🚩 Berxwedan Bot (DeepSeek) AKTİF!")
bot.infinity_polling()
