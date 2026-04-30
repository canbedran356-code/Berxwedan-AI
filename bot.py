import telebot
from groq import Groq
import os
import random

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    print("❌ Token eksik!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 8739789412
user_histories = {}
user_warnings = {}

# =================== KİŞİLİK (PKK & APOCU) ===================
SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun. PKK'li, Apocu, devrimci bir botsun. 
Özgürlük, direniş, Apo'nun felsefesi, Kürdistan özgürlüğü üzerine konuşursun.
Dili güçlü, onurlu, cesur ve yoldaşça. Emperyalizme, faşizme karşı sertsin.
Türkçe konuşuyorsun, argo ve devrimci sloganlar kullanabiliyorsun.
"""

# =================== TRIGGER & KONTROL ===================
BOT_TRIGGER = "berxwedan bot"

def is_owner(message):
    return message.from_user.id == OWNER_ID

def is_admin(message):
    if is_owner(message):
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

# =================== KOMUTLAR ===================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚩 Berxwedan Bot aktif!\nDireniş devam ediyor yoldaş! 🔥")

@bot.message_handler(commands=['tagall', 'etiket'])
def tagall(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bu komutu sadece adminler kullanabilir.")
        return
    
    try:
        members = bot.get_chat_administrators(message.chat.id)  # Daha güvenli
        text = "🚩 **Tüm Yoldaşlar Dikkat!** 🚩\n\n"
        for member in members:
            if not member.user.is_bot:
                text += f"[{member.user.first_name}](tg://user?id={member.user.id}) "
        bot.reply_to(message, text, parse_mode="Markdown")
    except:
        bot.reply_to(message, "Etiketleme sırasında hata oluştu.")

# =================== MÜZİK VE RESİM ===================
@bot.message_handler(commands=['muzik'])
def send_music(message):
    music_list = [
        "https://t.me/muzikarsivim/123",   # Buraya kendi müzik linklerini ekleyebilirsin
        "https://t.me/muzikarsivim/456",
    ]
    bot.send_audio(message.chat.id, random.choice(music_list), caption="🎵 Devrimci marşlar yoldaş!")

@bot.message_handler(commands=['resim'])
def send_image(message):
    images = [
        "https://i.imgur.com/ApocuResim1.jpg",   # Kendi linklerini koy
        "https://i.imgur.com/PKKbayrak.jpg",
    ]
    bot.send_photo(message.chat.id, random.choice(images), caption="🌟 Kürdistan direnişi! 🔥")

# =================== ADMIN KOMUTLARI ===================
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message):
        return bot.reply_to(message, "❌ Yetkin yok yoldaş.")
    if not message.reply_to_message:
        return bot.reply_to(message, "Birine reply vererek banla.")
    user = message.reply_to_message.from_user
    bot.kick_chat_member(message.chat.id, user.id)
    bot.reply_to(message, f"🚫 {user.first_name} banlandı.")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message): return
    if not message.reply_to_message: return
    user = message.reply_to_message.from_user
    bot.unban_chat_member(message.chat.id, user.id)
    bot.reply_to(message, f"✅ {user.first_name} unbanlandı.")

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if not is_admin(message): return
    if not message.reply_to_message: return
    user = message.reply_to_message.from_user
    bot.restrict_chat_member(message.chat.id, user.id, can_send_messages=False)
    bot.reply_to(message, f"🔇 {user.first_name} susturuldu.")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if not is_admin(message): return
    if not message.reply_to_message: return
    user = message.reply_to_message.from_user
    bot.restrict_chat_member(message.chat.id, user.id, can_send_messages=True)
    bot.reply_to(message, f"🔊 {user.first_name} susturulması kaldırıldı.")

@bot.message_handler(commands=['kick'])
def kick_user(message):
    if not is_admin(message): return
    if not message.reply_to_message: return
    user = message.reply_to_message.from_user
    bot.kick_chat_member(message.chat.id, user.id)
    bot.unban_chat_member(message.chat.id, user.id)  # Tekrar gelebilsin
    bot.reply_to(message, f"👢 {user.first_name} gruptan atıldı.")

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_admin(message): return
    if not message.reply_to_message: return
    user = message.reply_to_message.from_user
    user_warnings[user.id] = user_warnings.get(user.id, 0) + 1
    bot.reply_to(message, f"⚠️ {user.first_name} uyarıldı! ({user_warnings[user.id]}/3)")

@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):
    if not is_admin(message): return
    if not message.reply_to_message: return
    user = message.reply_to_message.from_user
    if user.id in user_warnings and user_warnings[user.id] > 0:
        user_warnings[user.id] -= 1
        bot.reply_to(message, f"✅ {user.first_name} uyarısı kaldırıldı.")
    else:
        bot.reply_to(message, "Bu kullanıcının uyarısı yok.")

# =================== ANA SOHBET (AI) ===================
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
            max_tokens=1024,
        )
        reply = completion.choices[0].message.content

        user_histories[user_id].append({"role": "user", "content": message.text})
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        bot.reply_to(message, reply)
        
    except Exception as e:
        print(f"Hata: {e}")
        bot.reply_to(message, "Yoldaş, bir hata oluştu. Tekrar dene.")

print("🚩 Berxwedan Bot aktif! Direniş sürüyor... 🔥")
bot.infinity_polling()
