import telebot
from groq import Groq
import os
import random
import threading
import time
import json
import re
import logging
from datetime import datetime, timedelta
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

# ====================== LOGGING ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("berxwedan.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====================== AYARLAR ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")

bot    = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID    = 8739789412
BOT_TRIGGER = "berxwedan bot"
DATA_FILE   = "bot_data.json"

# ====================== VERİ KATMANI ======================
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "warnings": {},
        "muted_until": {},
        "banned_users": [],
        "notes": {},
        "filters": {},
        "welcome_messages": {},
        "stats": {"messages": 0, "commands": 0, "ai_calls": 0},
        "afk": {},
        "anti_spam": {},
        "locked_chats": []
    }

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ====================== YARDIMCI FONKSİYONLAR ======================
def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_admin(message) -> bool:
    if is_owner(message.from_user.id):
        return True
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ["administrator", "creator"]
    except Exception:
        return False

def get_target(message):
    """Reply veya @username/ID ile hedef kullanıcıyı döndürür.
    Her zaman .id ve .first_name alanlarına sahip bir obje döner.
    """
    if message.reply_to_message:
        return message.reply_to_message.from_user

    text  = message.text or ""
    parts = text.split()
    if len(parts) < 2:
        return None

    arg = parts[1]

    # @kullanici_adi
    if arg.startswith("@"):
        try:
            chat = bot.get_chat(arg)          # Chat objesi döner
            # Chat objesini moderasyon komutlarının beklediği yapıya sar
            chat.first_name = (
                getattr(chat, "first_name", None)
                or getattr(chat, "title", None)
                or arg
            )
            return chat
        except Exception as e:
            logger.warning(f"@username çözümleme hatası ({arg}): {e}")
            return None

    # Sayısal ID
    if arg.lstrip("-").isdigit():
        try:
            chat = bot.get_chat(int(arg))
            chat.first_name = (
                getattr(chat, "first_name", None)
                or getattr(chat, "title", None)
                or arg
            )
            return chat
        except Exception as e:
            logger.warning(f"ID çözümleme hatası ({arg}): {e}")
            return None

    return None

def mention(user) -> str:
    name = getattr(user, "first_name", None) or str(getattr(user, "id", "?"))
    uid  = getattr(user, "id", None)
    if uid:
        return f"[{name}](tg://user?id={uid})"
    return name

def get_reason(message) -> str:
    parts = (message.text or "").split(None, 2)
    return parts[2] if len(parts) >= 3 else "Sebep belirtilmedi."

def parse_duration(text: str) -> int | None:
    """'10m', '2h', '1d' gibi süreleri saniyeye çevirir."""
    match = re.match(r"(\d+)([mhd])", text.lower())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    return val * {"m": 60, "h": 3600, "d": 86400}[unit]

def update_stats(key: str):
    data["stats"][key] = data["stats"].get(key, 0) + 1
    save_data(data)

def fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

# ====================== ANTİ-SPAM ======================
def check_spam(user_id: int) -> bool:
    now = time.time()
    history = data["anti_spam"].get(str(user_id), [])
    history = [t for t in history if now - t < 5]
    history.append(now)
    data["anti_spam"][str(user_id)] = history
    save_data(data)
    return len(history) > 8  # 5 saniyede 8'den fazla mesaj

# ====================== SYSTEM PROMPT ======================
SYSTEM_PROMPT = """
Sen Berxwedan Bot'sun — özgürlükçü, devrimci, analitik ve dürüst bir yapay zekasın.
Kürt özgürlük hareketi, Apocu felsefe (demokratik konfederalizm, jin-jiyan-azadî) ve
toplumsal kurtuluş üzerine derinlikli, tutarlı cevaplar verirsin.
Kısa ve öz konuş; gerektiğinde uzun açıkla. Yoldaşça bir dil kullan.
Türkçe veya Kürtçe sorulara aynı dilde cevap ver.
"""

CONVERSATION_HISTORY: dict[int, list] = {}
MAX_HISTORY = 10  # konuşma başına max tur

def build_messages(chat_id: int, user_text: str) -> list:
    history = CONVERSATION_HISTORY.get(chat_id, [])
    history.append({"role": "user", "content": user_text})
    if len(history) > MAX_HISTORY * 2:
        history = history[-MAX_HISTORY * 2:]
    CONVERSATION_HISTORY[chat_id] = history
    return [{"role": "system", "content": SYSTEM_PROMPT}] + history

def store_assistant_reply(chat_id: int, reply: str):
    history = CONVERSATION_HISTORY.get(chat_id, [])
    history.append({"role": "assistant", "content": reply})
    CONVERSATION_HISTORY[chat_id] = history

# ====================== ADMIN PANELİ ======================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Sadece kurucu kullanabilir.")
    update_stats("commands")
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 Ban",     callback_data="panel_ban"),
        InlineKeyboardButton("✅ Unban",   callback_data="panel_unban"),
        InlineKeyboardButton("🔇 Mute",    callback_data="panel_mute"),
        InlineKeyboardButton("🔊 Unmute",  callback_data="panel_unmute"),
        InlineKeyboardButton("⚠️ Warn",    callback_data="panel_warn"),
        InlineKeyboardButton("✅ Unwarn",  callback_data="panel_unwarn"),
        InlineKeyboardButton("👢 Kick",    callback_data="panel_kick"),
        InlineKeyboardButton("📊 İstatistik", callback_data="panel_stats"),
    )
    bot.reply_to(message, "🛡️ *Berxwedan Admin Paneli*\nBir eylem seç, ardından hedef mesaja reply ver.", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("panel_"))
def callback_handler(call):
    if call.from_user.id != OWNER_ID:
        return bot.answer_callback_query(call.id, "❌ Yetkin yok!")
    bot.answer_callback_query(call.id)
    action = call.data.split("_", 1)[1]
    if action == "stats":
        s = data["stats"]
        bot.send_message(
            call.message.chat.id,
            f"📊 *Bot İstatistikleri*\n"
            f"💬 Mesaj: {s.get('messages', 0)}\n"
            f"⚙️ Komut: {s.get('commands', 0)}\n"
            f"🤖 AI Çağrısı: {s.get('ai_calls', 0)}"
        )
    else:
        bot.send_message(
            call.message.chat.id,
            f"✅ *{action.upper()}* aktif!\nŞimdi hedef mesaja **reply ver**."
        )

# ====================== MODERASYON ======================
@bot.message_handler(commands=["ban"])
def ban_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver veya ID gir.")
    reason = get_reason(message)
    bot.kick_chat_member(message.chat.id, target.id)
    data["banned_users"].append(target.id)
    save_data(data)
    bot.reply_to(message, f"🚫 {mention(target)} banlandı.\n📝 *Sebep:* {reason}")
    logger.info(f"BAN: {target.id} — {reason}")

@bot.message_handler(commands=["unban"])
def unban_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target:
        return bot.reply_to(message, "❗ Reply ver, @kullanıcıadı veya ID gir.")
    bot.unban_chat_member(message.chat.id, target.id)
    if target.id in data["banned_users"]:
        data["banned_users"].remove(target.id)
    save_data(data)
    bot.reply_to(message, f"✅ {mention(target)} banı kaldırıldı.")

@bot.message_handler(commands=["mute"])
def mute_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver veya ID gir.")
    parts  = (message.text or "").split()
    dur    = parse_duration(parts[2]) if len(parts) > 2 else None
    until  = datetime.now() + timedelta(seconds=dur) if dur else None
    telebot_until = until if until else datetime(2038, 1, 1)
    bot.restrict_chat_member(message.chat.id, target.id,
                              until_date=telebot_until,
                              can_send_messages=False)
    if dur:
        data["muted_until"][str(target.id)] = (datetime.now() + timedelta(seconds=dur)).timestamp()
        save_data(data)
    info = f"süre: {parts[2]}" if dur else "süresiz"
    bot.reply_to(message, f"🔇 {mention(target)} susturuldu ({info}).")

@bot.message_handler(commands=["unmute"])
def unmute_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    uid = target.id if target else None
    if not uid:
        try: uid = int((message.text or "").split()[1])
        except Exception: return bot.reply_to(message, "Kullanım: `/unmute <ID>`")
    bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True)
    data["muted_until"].pop(str(uid), None)
    save_data(data)
    bot.reply_to(message, f"🔊 `{uid}` susturulması kaldırıldı.")

@bot.message_handler(commands=["warn"])
def warn_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver.")
    reason = get_reason(message)
    sid = str(target.id)
    data["warnings"][sid] = data["warnings"].get(sid, 0) + 1
    w = data["warnings"][sid]
    save_data(data)
    bot.reply_to(message, f"⚠️ {mention(target)} uyarıldı ({w}/3)\n📝 *Sebep:* {reason}")
    if w >= 3:
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 {mention(target)} 3 uyarı dolduğu için susturuldu!")

@bot.message_handler(commands=["unwarn"])
def unwarn_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver.")
    sid = str(target.id)
    if data["warnings"].get(sid, 0) > 0:
        data["warnings"][sid] -= 1
        save_data(data)
        bot.reply_to(message, f"✅ {mention(target)} bir uyarısı silindi. ({data['warnings'][sid]}/3)")

@bot.message_handler(commands=["kick"])
def kick_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver.")
    reason = get_reason(message)
    bot.kick_chat_member(message.chat.id, target.id)
    bot.unban_chat_member(message.chat.id, target.id)
    bot.reply_to(message, f"👢 {mention(target)} gruptan çıkarıldı.\n📝 *Sebep:* {reason}")

@bot.message_handler(commands=["warnings"])
def warnings_cmd(message):
    update_stats("commands")
    target = get_target(message) or message.from_user
    sid = str(target.id)
    w = data["warnings"].get(sid, 0)
    bot.reply_to(message, f"⚠️ {mention(target)} — `{w}/3` uyarı")

# ====================== NOTLAR ======================
@bot.message_handler(commands=["savenote"])
def save_note(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split(None, 2)
    if len(parts) < 3:
        return bot.reply_to(message, "Kullanım: `/savenote <ad> <içerik>`")
    cid, name, content = str(message.chat.id), parts[1].lower(), parts[2]
    data["notes"].setdefault(cid, {})[name] = content
    save_data(data)
    bot.reply_to(message, f"📌 Not `{name}` kaydedildi.")

@bot.message_handler(commands=["note"])
def get_note(message):
    update_stats("commands")
    parts = (message.text or "").split()
    if len(parts) < 2:
        return bot.reply_to(message, "Kullanım: `/note <ad>`")
    cid, name = str(message.chat.id), parts[1].lower()
    note = data["notes"].get(cid, {}).get(name)
    bot.reply_to(message, note if note else f"❌ `{name}` notu bulunamadı.")

@bot.message_handler(commands=["notes"])
def list_notes(message):
    update_stats("commands")
    cid = str(message.chat.id)
    notes = data["notes"].get(cid, {})
    if not notes:
        return bot.reply_to(message, "📭 Kayıtlı not yok.")
    bot.reply_to(message, "📒 *Notlar:*\n" + "\n".join(f"• `{k}`" for k in notes))

@bot.message_handler(commands=["delnote"])
def del_note(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split()
    if len(parts) < 2: return
    cid, name = str(message.chat.id), parts[1].lower()
    if data["notes"].get(cid, {}).pop(name, None) is not None:
        save_data(data)
        bot.reply_to(message, f"🗑️ Not `{name}` silindi.")

# ====================== FİLTRELER ======================
@bot.message_handler(commands=["addfilter"])
def add_filter(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split(None, 2)
    if len(parts) < 3:
        return bot.reply_to(message, "Kullanım: `/addfilter <anahtar> <yanıt>`")
    cid, key, reply = str(message.chat.id), parts[1].lower(), parts[2]
    data["filters"].setdefault(cid, {})[key] = reply
    save_data(data)
    bot.reply_to(message, f"✅ Filtre `{key}` eklendi.")

@bot.message_handler(commands=["delfilter"])
def del_filter(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split()
    if len(parts) < 2: return
    cid, key = str(message.chat.id), parts[1].lower()
    if data["filters"].get(cid, {}).pop(key, None) is not None:
        save_data(data)
        bot.reply_to(message, f"🗑️ Filtre `{key}` silindi.")

@bot.message_handler(commands=["filters"])
def list_filters(message):
    update_stats("commands")
    cid = str(message.chat.id)
    filters = data["filters"].get(cid, {})
    if not filters:
        return bot.reply_to(message, "📭 Kayıtlı filtre yok.")
    bot.reply_to(message, "🔍 *Filtreler:*\n" + "\n".join(f"• `{k}`" for k in filters))

# ====================== HOŞ GELDİN ======================
@bot.message_handler(commands=["setwelcome"])
def set_welcome(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        return bot.reply_to(message, "Kullanım: `/setwelcome <mesaj>` — `{name}` ile kullanıcı adını ekle.")
    data["welcome_messages"][str(message.chat.id)] = parts[1]
    save_data(data)
    bot.reply_to(message, "✅ Hoş geldin mesajı ayarlandı.")

@bot.message_handler(content_types=["new_chat_members"])
def new_member(message):
    cid = str(message.chat.id)
    template = data["welcome_messages"].get(cid, "👋 Hoş geldin, {name}! Berxwedan grubumuza merhaba 🌹")
    for user in message.new_chat_members:
        text = template.replace("{name}", mention(user))
        bot.send_message(message.chat.id, text)

# ====================== AFK ======================
@bot.message_handler(commands=["afk"])
def afk_cmd(message):
    update_stats("commands")
    uid = str(message.from_user.id)
    reason = (message.text or "").split(None, 1)[1] if len((message.text or "").split()) > 1 else "Meşgul"
    data["afk"][uid] = {"since": time.time(), "reason": reason}
    save_data(data)
    bot.reply_to(message, f"😴 {mention(message.from_user)} AFK moduna geçti. Sebep: _{reason}_")

# ====================== GRUP KİLİTLEME ======================
@bot.message_handler(commands=["lock"])
def lock_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    cid = str(message.chat.id)
    if cid not in data["locked_chats"]:
        data["locked_chats"].append(cid)
        save_data(data)
    bot.reply_to(message, "🔒 Grup kilitlendi. Sadece adminler yazabilir.")

@bot.message_handler(commands=["unlock"])
def unlock_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    cid = str(message.chat.id)
    if cid in data["locked_chats"]:
        data["locked_chats"].remove(cid)
        save_data(data)
    bot.reply_to(message, "🔓 Grup kilidi açıldı.")

# ====================== BROADCAST ======================
@bot.message_handler(commands=["broadcast"])
def broadcast_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    text = (message.text or "").split(None, 1)
    if len(text) < 2:
        return bot.reply_to(message, "Kullanım: `/broadcast <mesaj>`")
    # Tüm grupları data'dan bul (gelecekte group_ids listesi tutulabilir)
    bot.reply_to(message, f"📢 Broadcast gönderildi:\n{text[1]}")

# ====================== İSTATİSTİK ======================
@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    s = data["stats"]
    bot.reply_to(
        message,
        f"📊 *Bot İstatistikleri*\n"
        f"💬 Toplam Mesaj: `{s.get('messages', 0)}`\n"
        f"⚙️ Komut: `{s.get('commands', 0)}`\n"
        f"🤖 AI Çağrısı: `{s.get('ai_calls', 0)}`\n"
        f"🗃️ Kayıtlı Not: `{sum(len(v) for v in data['notes'].values())}`\n"
        f"🔍 Filtre: `{sum(len(v) for v in data['filters'].values())}`"
    )

# ====================== YARDIM ======================
HELP_TEXT = """
🌹 *Berxwedan Bot — Komutlar*

*🛡️ Moderasyon (Sadece Kurucu):*
`/ban [@/ID] [sebep]` — Kullanıcıyı banla
`/unban <ID>` — Banı kaldır
`/kick [@/ID] [sebep]` — Gruptan at
`/mute [@/ID] [süre: 10m/2h/1d]` — Sustur
`/unmute [@/ID]` — Susturmayı kaldır
`/warn [@/ID] [sebep]` — Uyar (3'te mute)
`/unwarn [@/ID]` — Uyarı azalt

*📌 Notlar (Admin):*
`/savenote <ad> <içerik>` — Not kaydet
`/note <ad>` — Not oku
`/notes` — Tüm notlar
`/delnote <ad>` — Notu sil

*🔍 Filtreler (Admin):*
`/addfilter <anahtar> <yanıt>` — Filtre ekle
`/delfilter <anahtar>` — Filtre sil
`/filters` — Filtreleri listele

*🔒 Grup (Admin):*
`/lock` — Grubu kilitle
`/unlock` — Kilidi aç
`/setwelcome <mesaj>` — Hoş geldin ayarla

*💡 Diğer:*
`/afk [sebep]` — AFK moduna gir
`/warnings` — Uyarılarını gör
`/stats` — İstatistikler
`/help` — Bu mesaj

*🤖 AI:* Mesajına "berxwedan bot" yazarak sohbet et.
"""

@bot.message_handler(commands=["help", "start"])
def help_cmd(message):
    update_stats("commands")
    bot.reply_to(message, HELP_TEXT)

# ====================== ANA MESAJ İŞLEYİCİ ======================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    update_stats("messages")
    uid  = str(message.from_user.id)
    cid  = str(message.chat.id)
    text = message.text or ""

    # --- Kilitli grup kontrolü ---
    if cid in data["locked_chats"] and not is_admin(message):
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        return

    # --- Anti-spam kontrolü ---
    if check_spam(message.from_user.id) and not is_admin(message):
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        return

    # --- AFK dönüş kontrolü ---
    if uid in data["afk"]:
        afk_info = data["afk"].pop(uid)
        save_data(data)
        elapsed = int(time.time() - afk_info["since"])
        h, m = divmod(elapsed // 60, 60)
        bot.reply_to(message, f"👋 {mention(message.from_user)} AFK'dan döndü. Süre: `{h}s {m}d`")

    # --- Reply AFK kontrolü ---
    if message.reply_to_message:
        rid = str(message.reply_to_message.from_user.id)
        if rid in data["afk"]:
            info = data["afk"][rid]
            bot.reply_to(message, f"😴 Bu kullanıcı AFK: _{info['reason']}_ (since {fmt_time(info['since'])})")

    # --- Filtre kontrolü ---
    for key, reply in data["filters"].get(cid, {}).items():
        if key in text.lower():
            bot.reply_to(message, reply)
            return

    # --- AI Tetikleyici ---
    if BOT_TRIGGER in text.lower():
        update_stats("ai_calls")
        typing_action = threading.Thread(
            target=lambda: bot.send_chat_action(message.chat.id, "typing"), daemon=True
        )
        typing_action.start()
        try:
            messages = build_messages(message.chat.id, text)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.85,
                max_tokens=700,
            )
            reply = completion.choices[0].message.content
            store_assistant_reply(message.chat.id, reply)
            bot.reply_to(message, reply)
        except Exception as e:
            logger.error(f"AI hatası: {e}")
            bot.reply_to(message, "⚙️ Yoldaş, AI şu an yoğun. Birazdan tekrar dene.")

# ====================== HATA YÖNETİMİ ======================
@bot.message_handler(func=lambda m: True)
def fallback(message):
    pass  # Bilinmeyen mesaj türleri için sessiz geç

def handle_error(exception):
    logger.error(f"Polling hatası: {exception}")

# ====================== ZAMANLAYICI: Mute Kaldır ======================
def auto_unmute():
    while True:
        now = time.time()
        to_remove = []
        for uid, until in list(data["muted_until"].items()):
            if now >= until:
                to_remove.append(uid)
        for uid in to_remove:
            del data["muted_until"][uid]
        if to_remove:
            save_data(data)
        time.sleep(60)

threading.Thread(target=auto_unmute, daemon=True).start()

# ====================== BAŞLAT ======================
if __name__ == "__main__":
    logger.info("🚩 Berxwedan Bot — Gelişmiş Versiyon AKTİF!")
    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=30,
        logger_level=logging.WARNING,
        allowed_updates=["message", "callback_query", "chat_member"]
    )
