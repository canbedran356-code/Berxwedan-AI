import telebot
from groq import Groq
import os
import random
import subprocess

# ====================== AYARLAR ======================
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
Kürdistan özgürlüğü, Abdullah Öcalan felsefesi, direniş ve yoldaşlık üzerine güçlü, onurlu ve motive edici konuşursun.
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

# ====================== DEVRİMCİ AI RESİM (GÜÇLENDİRİLDİ) ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    user_prompt = " ".join(message.text.split()[1:]).strip()
    if not user_prompt:
        user_prompt = "devrimci Kürt gerilla"

    bot.reply_to(message, "🖼️ Devrimci gerillalar çiziliyor yoldaş... 🔥")

    try:
        # Çok daha güçlü devrimci prompt
        full_prompt = (
            f"{user_prompt}, handsome young Kurdish revolutionary guerrilla, "
            "sharp and determined face, intense eyes, thick hair, red star flag, "
            "Kurdistan mountains background, resistance atmosphere, "
            "proud warrior pose, cinematic dramatic lighting, "
            "revolutionary spirit, highly detailed, realistic, epic, 8k, masterpiece"
        )

        clean_prompt = full_prompt.replace(" ", "%20").replace(",", "%2C")
        seed = random.randint(100000, 999999)

        image_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1024&seed={seed}&model=flux&safe=false&enhance=true"

        bot.send_photo(
            message.chat.id, 
            image_url,
            caption=f"🖼️ **{user_prompt}**\n🚩 Berxwedan Serxwebûn! 🔥"
        )
    except Exception:
        bot.reply_to(message, "❌ Resim üretilemedi. Tekrar dene.")

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
        return bot.reply_to(message, "❌ Sadece admin kullanabilir.")
    text = """🚩 **Berxwedan Bot Komutları**

**🎨 AI Resim**
• `/airesim <açıklama>` → Devrimci gerilla çizer

**🎵 Medya**
• `/sarki <youtube link>` → Şarkı indir
• `/muzik` → Rastgele marş

**👥 Grup**
• `/tagall` → Herkesi etiketle

**🛡️ Moderasyon**
• `/ban` `/mute` `/kick` `/warn` `/unwarn`

Sadece admin/owner kullanabilir."""
    bot.reply_to(message, text, parse_mode="Markdown")

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

# ====================== ANA SOHBET ======================
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
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.85,
            max_tokens=900,
        )
        reply = completion.choices[0].message.content

        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 18:
            user_histories[user_id] = user_histories[user_id][-18:]

        bot.reply_to(message, reply)
    except:
        bot.reply_to(message, "Yoldaş, Groq yoğun. Biraz sonra tekrar dene.")

print("🚩 Berxwedan Bot - Devrimci Mod AKTİF!")
bot.infinity_polling()
