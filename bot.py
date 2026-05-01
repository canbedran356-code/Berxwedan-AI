import telebot
import os
import random
import subprocess
from google import genai

# ====================== AYARLAR ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
gemini = genai.Client(api_key=GEMINI_API_KEY)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

BOT_TRIGGER = "berxwedan bot"

SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Kürdistan özgürlüğü, Apo'nun felsefesi, direniş ve yoldaşlık üzerine güçlü, onurlu ve motive edici konuşursun.
"""

# ====================== YARDIMCI FONKSİYONLAR ======================
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

# ====================== GEMINI AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if not should_reply(message):
        return

    try:
        response = gemini.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[message.text]
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        print(f"Gemini Hatası: {e}")
        bot.reply_to(message, "Yoldaş, Gemini şu anda yoğun. Biraz sonra tekrar dene.")

# ====================== DEVRİMCİ AI RESİM ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    prompt = " ".join(message.text.split()[1:]).strip()
    if not prompt:
        prompt = "devrimci Kürt gerilla"

    bot.reply_to(message, "🖼️ Devrimci gerillalar çiziliyor... 🔥")

    try:
        full_prompt = (
            f"{prompt}, handsome young Kurdish revolutionary guerrilla, "
            "sharp determined face, intense eyes, thick black hair, "
            "Kurdistan mountains, red star flag, proud warrior pose, "
            "cinematic dramatic lighting, highly detailed, realistic, epic, 8k"
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
    bot.reply_to(message, "🎵 Şarkı indiriliyor...")
    try:
        filename = f"devrim_{random.randint(1000,9999)}.mp3"
        subprocess.run(['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '-o', filename, url], 
                       check=True, timeout=180)
        with open(filename, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption="🎵 Devrimci marş yüklendi! 🔥")
        os.remove(filename)
    except:
        bot.reply_to(message, "❌ Şarkı indirilemedi.")

# ====================== DİĞER KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* Direniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim'])
def mod_help(message):
    if not is_admin(message):
        return bot.reply_to(message, "❌ Bu komut sadece adminler içindir.")
    text = """🚩 **Berxwedan Bot Komutları**

• `/airesim <açıklama>` → Devrimci gerilla resmi
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
    if not is_admin(message):
        return bot.reply_to(message, "❌ Sadece admin kullanabilir.")
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

print("🚩 Berxwedan Bot AKTİF!")
bot.infinity_polling()
