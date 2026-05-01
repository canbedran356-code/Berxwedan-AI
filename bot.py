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

# ====================== KOMUTLAR ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 *Berxwedan Bot aktif!* Direniş sürüyor yoldaş! 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['mod', 'yardim', 'admin'])
def mod_help(message):
    bot.reply_to(message, """🚩 **Komutlar:**

• /airesim <açıklama> → AI resim
• /sarki <youtube link> → Şarkı indir
• /marş → Marş listesi
• /tagall → Grubu etiketle
• /tagadmin → Adminleri etiketle
• /profil → Profil + uyarı
• /ban, /unban, /mute, /unmute, /warn""")

@bot.message_handler(commands=['airesim'])
def airesim(message):
    prompt = " ".join(message.text.split()[1:]) or "devrimci gerilla"
    bot.reply_to(message, "🖼️ Resim üretiliyor...")
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux"
        bot.send_photo(message.chat.id, url, caption="🚩 Berxwedan!")
    except:
        bot.reply_to(message, "Resim üretilemedi.")

@bot.message_handler(commands=['sarki'])
def sarki(message):
    if len(message.text.split()) < 2:
        return bot.reply_to(message, "❌ Link gir!")
    url = message.text.split(maxsplit=1)[1]
    bot.reply_to(message, "🎵 İndiriliyor...")
    try:
        filename = f"devrim_{random.randint(1000,9999)}.mp3"
        subprocess.run(['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '-o', filename, url], check=True, timeout=180)
        with open(filename, 'rb') as f:
            bot.send_audio(message.chat.id, f, caption="🎵 Devrimci marş! 🔥")
        os.remove(filename)
    except:
        bot.reply_to(message, "İndirilemedi.")

@bot.message_handler(commands=['marş'])
def mars(message):
    bot.reply_to(message, "🎵 Heyder, Serxwebûn, Ey Reqîb... \nDaha fazlası için /sarki kullan.")

@bot.message_handler(commands=['tagall'])
def tagall(message):
    bot.reply_to(message, "🚩 **Tüm Yoldaşlar Dikkat!** Direniş sürüyor! 🔥")

@bot.message_handler(commands=['tagadmin'])
def tagadmin(message):
    bot.reply_to(message, "👮 **Adminler Dikkat!** Direniş sürüyor! 🔥")

@bot.message_handler(commands=['profil'])
def profil(message):
    bot.reply_to(message, f"📋 Profil\nAd: {message.from_user.first_name}\nID: {message.from_user.id}")

# ====================== AI SOHBET ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if "berxwedan bot" in (message.text or "").lower():
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": message.text}],
                temperature=0.85,
            )
            bot.reply_to(message, completion.choices[0].message.content)
        except:
            bot.reply_to(message, "Yoldaş, AI yoğun.")

print("🚩 Berxwedan Bot AKTİF!")
bot.infinity_polling()
