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
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

bot    = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID  = 8739789412
DATA_FILE = "bot_data.json"

# AI tetikleyici: "bot" kelimesi tek başına geçerse tetikle
# Örnek: "bot ne düşünüyorsun?" veya "bot merhaba"
AI_TRIGGER_PATTERN = re.compile(r"\bbot\b", re.IGNORECASE)

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
        "goodbye_messages": {},
        "stats": {"messages": 0, "commands": 0, "ai_calls": 0},
        "afk": {},
        "anti_spam": {},
        "locked_chats": [],
        "reminders": [],
        "user_message_counts": {},
        "night_mode": {},          # {chat_id: {"enabled": bool, "start": "23:00", "end": "07:00"}}
        "pinned_notes": {},        # {chat_id: note_name}
        "rules": {},               # {chat_id: rules_text}
        "word_stats": {},          # {chat_id: {word: count}}
        "group_ids": [],           # broadcast için grup listesi
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

def resolve_user(message):
    """
    Hedef kullanıcıyı şu sırayla çözer:
    1. Reply to message
    2. @username (bot'un gördüğü mesajlardan önbelleklenir)
    3. Sayısal ID
    Her zaman .id ve .first_name olan bir obje döner ya da None.
    """
    # 1. Reply
    if message.reply_to_message:
        return message.reply_to_message.from_user

    text  = message.text or ""
    parts = text.split()
    if len(parts) < 2:
        return None

    arg = parts[1]

    # 2. @username
    if arg.startswith("@"):
        # Telegram Bot API, @username ile doğrudan get_chat çağrısına izin verir
        # ancak bu çoğu zaman çalışır; çalışmazsa kullanıcının mesaj atması gerekir.
        try:
            chat = bot.get_chat(arg)
            # Chat objesine first_name ekle (yoksa title veya username kullan)
            if not getattr(chat, "first_name", None):
                chat.first_name = (
                    getattr(chat, "title", None)
                    or getattr(chat, "username", None)
                    or arg
                )
            return chat
        except Exception as e:
            logger.warning(f"@username çözümleme hatası ({arg}): {e}")
            # Hata durumunda kullanıcıya anlamlı mesaj vermek için sentinel döndür
            return None

    # 3. Sayısal ID
    if arg.lstrip("-").isdigit():
        try:
            chat = bot.get_chat(int(arg))
            if not getattr(chat, "first_name", None):
                chat.first_name = (
                    getattr(chat, "title", None)
                    or getattr(chat, "username", None)
                    or arg
                )
            return chat
        except Exception as e:
            logger.warning(f"ID çözümleme hatası ({arg}): {e}")
            return None

    return None

# Kısa ad alias
get_target = resolve_user

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

def is_night_mode_active(chat_id: str) -> bool:
    """Gece modunun şu an aktif olup olmadığını kontrol eder."""
    nm = data.get("night_mode", {}).get(chat_id)
    if not nm or not nm.get("enabled"):
        return False
    now   = datetime.now().time()
    start = datetime.strptime(nm.get("start", "23:00"), "%H:%M").time()
    end   = datetime.strptime(nm.get("end",   "07:00"), "%H:%M").time()
    # Gece yarısını aşan aralıklar (ör. 23:00 - 07:00)
    if start > end:
        return now >= start or now < end
    return start <= now < end

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
MAX_HISTORY = 10

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

def call_ai(chat_id: int, text: str, message):
    """AI çağrısını ayrı thread'de yapar, typing action gönderir."""
    update_stats("ai_calls")
    bot.send_chat_action(message.chat.id, "typing")
    try:
        messages = build_messages(chat_id, text)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.85,
            max_tokens=700,
        )
        reply = completion.choices[0].message.content
        store_assistant_reply(chat_id, reply)
        bot.reply_to(message, reply)
    except Exception as e:
        logger.error(f"AI hatası: {e}")
        bot.reply_to(message, "⚙️ Yoldaş, AI şu an yoğun. Birazdan tekrar dene.")

# ====================== ADMIN PANELİ ======================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Sadece kurucu kullanabilir.")
    update_stats("commands")
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 Ban",        callback_data="panel_ban"),
        InlineKeyboardButton("✅ Unban",      callback_data="panel_unban"),
        InlineKeyboardButton("🔇 Mute",       callback_data="panel_mute"),
        InlineKeyboardButton("🔊 Unmute",     callback_data="panel_unmute"),
        InlineKeyboardButton("⚠️ Warn",       callback_data="panel_warn"),
        InlineKeyboardButton("✅ Unwarn",     callback_data="panel_unwarn"),
        InlineKeyboardButton("👢 Kick",       callback_data="panel_kick"),
        InlineKeyboardButton("📌 Pin",        callback_data="panel_pin"),
        InlineKeyboardButton("🌙 Gece Modu",  callback_data="panel_nightmode"),
        InlineKeyboardButton("📊 İstatistik", callback_data="panel_stats"),
    )
    bot.reply_to(message, "🛡️ *Berxwedan Admin Paneli*\nBir eylem seç:", reply_markup=markup)

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
    elif action == "nightmode":
        cid = str(call.message.chat.id)
        nm  = data.setdefault("night_mode", {}).get(cid, {})
        enabled = not nm.get("enabled", False)
        data["night_mode"][cid] = {"enabled": enabled, "start": "23:00", "end": "07:00"}
        save_data(data)
        status = "🌙 Gece modu *açıldı* (23:00–07:00)" if enabled else "☀️ Gece modu *kapatıldı*"
        bot.send_message(call.message.chat.id, status)
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
    if not target: return bot.reply_to(message, "❗ Reply ver veya @kullanıcıadı / ID gir.")
    reason = get_reason(message)
    try:
        bot.kick_chat_member(message.chat.id, target.id)
        data["banned_users"].append(target.id)
        save_data(data)
        bot.reply_to(message, f"🚫 {mention(target)} banlandı.\n📝 *Sebep:* {reason}")
        logger.info(f"BAN: {target.id} — {reason}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ban başarısız: `{e}`")

@bot.message_handler(commands=["unban"])
def unban_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver, @kullanıcıadı veya ID gir.")
    try:
        bot.unban_chat_member(message.chat.id, target.id)
        if target.id in data["banned_users"]:
            data["banned_users"].remove(target.id)
        save_data(data)
        bot.reply_to(message, f"✅ {mention(target)} banı kaldırıldı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Unban başarısız: `{e}`")

@bot.message_handler(commands=["mute"])
def mute_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver veya @kullanıcıadı / ID gir.")
    parts  = (message.text or "").split()
    dur    = parse_duration(parts[2]) if len(parts) > 2 else None
    until  = datetime.now() + timedelta(seconds=dur) if dur else None
    telebot_until = until if until else datetime(2038, 1, 1)
    try:
        bot.restrict_chat_member(message.chat.id, target.id,
                                  until_date=telebot_until,
                                  can_send_messages=False)
        if dur:
            data["muted_until"][str(target.id)] = (datetime.now() + timedelta(seconds=dur)).timestamp()
            save_data(data)
        info = f"süre: {parts[2]}" if dur else "süresiz"
        bot.reply_to(message, f"🔇 {mention(target)} susturuldu ({info}).")
    except Exception as e:
        bot.reply_to(message, f"❌ Mute başarısız: `{e}`")

@bot.message_handler(commands=["unmute"])
def unmute_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    uid = target.id if target else None
    if not uid:
        try: uid = int((message.text or "").split()[1])
        except Exception: return bot.reply_to(message, "Kullanım: `/unmute <ID>`")
    try:
        bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True)
        data["muted_until"].pop(str(uid), None)
        save_data(data)
        bot.reply_to(message, f"🔊 `{uid}` susturulması kaldırıldı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Unmute başarısız: `{e}`")

@bot.message_handler(commands=["warn"])
def warn_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver veya @kullanıcıadı / ID gir.")
    reason = get_reason(message)
    sid = str(target.id)
    data["warnings"][sid] = data["warnings"].get(sid, 0) + 1
    w = data["warnings"][sid]
    save_data(data)
    bot.reply_to(message, f"⚠️ {mention(target)} uyarıldı ({w}/3)\n📝 *Sebep:* {reason}")
    if w >= 3:
        try:
            bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
            bot.reply_to(message, f"🔇 {mention(target)} 3 uyarı dolduğu için susturuldu!")
        except Exception as e:
            bot.reply_to(message, f"❌ Otomatik mute başarısız: `{e}`")

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
    else:
        bot.reply_to(message, f"ℹ️ {mention(target)} için kayıtlı uyarı yok.")

@bot.message_handler(commands=["kick"])
def kick_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    target = get_target(message)
    if not target: return bot.reply_to(message, "❗ Reply ver veya @kullanıcıadı / ID gir.")
    reason = get_reason(message)
    try:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"👢 {mention(target)} gruptan çıkarıldı.\n📝 *Sebep:* {reason}")
    except Exception as e:
        bot.reply_to(message, f"❌ Kick başarısız: `{e}`")

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

# ====================== HOŞ GELDİN / GÜLE GÜLe ======================
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

@bot.message_handler(commands=["setgoodbye"])
def set_goodbye(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        return bot.reply_to(message, "Kullanım: `/setgoodbye <mesaj>` — `{name}` değişkeni desteklenir.")
    data["goodbye_messages"][str(message.chat.id)] = parts[1]
    save_data(data)
    bot.reply_to(message, "✅ Güle güle mesajı ayarlandı.")

@bot.message_handler(content_types=["new_chat_members"])
def new_member(message):
    cid = str(message.chat.id)
    # Grubu takip et (broadcast için)
    if cid not in data.get("group_ids", []):
        data.setdefault("group_ids", []).append(cid)
        save_data(data)
    template = data["welcome_messages"].get(
        cid, "👋 Hoş geldin, {name}! Berxwedan grubumuza merhaba 🌹\n`/help` ile komutları görebilirsin."
    )
    for user in message.new_chat_members:
        text = template.replace("{name}", mention(user))
        bot.send_message(message.chat.id, text)

@bot.message_handler(content_types=["left_chat_member"])
def left_member(message):
    cid = str(message.chat.id)
    template = data.get("goodbye_messages", {}).get(cid)
    if template:
        user = message.left_chat_member
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

# ====================== GECE MODU ======================
@bot.message_handler(commands=["nightmode"])
def night_mode_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split()
    cid   = str(message.chat.id)
    nm    = data.setdefault("night_mode", {}).setdefault(cid, {"enabled": False, "start": "23:00", "end": "07:00"})

    if len(parts) >= 2 and parts[1].lower() == "off":
        nm["enabled"] = False
        save_data(data)
        return bot.reply_to(message, "☀️ Gece modu kapatıldı.")

    # /nightmode 23:00 07:00   veya sadece /nightmode (toggle)
    if len(parts) == 3:
        try:
            datetime.strptime(parts[1], "%H:%M")
            datetime.strptime(parts[2], "%H:%M")
            nm["start"] = parts[1]
            nm["end"]   = parts[2]
        except ValueError:
            return bot.reply_to(message, "❗ Saat formatı: `HH:MM` — ör. `/nightmode 22:00 08:00`")

    nm["enabled"] = True
    save_data(data)
    bot.reply_to(message, f"🌙 Gece modu açıldı: `{nm['start']}` — `{nm['end']}`\n"
                           "Bu saatler arasında adminler dışında kimse yazamaz.")

# ====================== ANKET (POLL) ======================
@bot.message_handler(commands=["poll"])
def poll_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    # Kullanım: /poll Soru? | Seçenek1 | Seçenek2 | Seçenek3
    text  = (message.text or "").split(None, 1)
    if len(text) < 2:
        return bot.reply_to(message, "Kullanım: `/poll Soru? | Seçenek1 | Seçenek2`")
    parts = [p.strip() for p in text[1].split("|")]
    if len(parts) < 3:
        return bot.reply_to(message, "❗ En az 1 soru ve 2 seçenek gir. Ayırıcı: `|`")
    question, options = parts[0], parts[1:]
    try:
        bot.send_poll(
            message.chat.id,
            question=question,
            options=options,
            is_anonymous=False,
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Anket oluşturulamadı: `{e}`")

# ====================== MESAJ SABİTLE ======================
@bot.message_handler(commands=["pin"])
def pin_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    if not message.reply_to_message:
        return bot.reply_to(message, "❗ Sabitlemek istediğin mesaja reply ver.")
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id, disable_notification=False)
        bot.reply_to(message, "📌 Mesaj sabitlendi.")
    except Exception as e:
        bot.reply_to(message, f"❌ Pin başarısız: `{e}`")

@bot.message_handler(commands=["unpin"])
def unpin_cmd(message):
    if not is_admin(message): return
    update_stats("commands")
    try:
        bot.unpin_all_chat_messages(message.chat.id)
        bot.reply_to(message, "📌 Tüm sabitlemeler kaldırıldı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Unpin başarısız: `{e}`")

# ====================== KURAL ======================
@bot.message_handler(commands=["setrules"])
def set_rules(message):
    if not is_admin(message): return
    update_stats("commands")
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        return bot.reply_to(message, "Kullanım: `/setrules <kurallar>`")
    data.setdefault("rules", {})[str(message.chat.id)] = parts[1]
    save_data(data)
    bot.reply_to(message, "📜 Grup kuralları ayarlandı.")

@bot.message_handler(commands=["rules"])
def rules_cmd(message):
    update_stats("commands")
    rules = data.get("rules", {}).get(str(message.chat.id))
    if rules:
        bot.reply_to(message, f"📜 *Grup Kuralları:*\n\n{rules}")
    else:
        bot.reply_to(message, "ℹ️ Henüz kural belirlenmemiş.")

# ====================== HATIRLATICI ======================
@bot.message_handler(commands=["remind"])
def remind_cmd(message):
    update_stats("commands")
    # Kullanım: /remind 10m Mesaj
    parts = (message.text or "").split(None, 2)
    if len(parts) < 3:
        return bot.reply_to(message, "Kullanım: `/remind <süre> <mesaj>` — ör. `/remind 10m Toplantı var!`")
    dur = parse_duration(parts[1])
    if not dur:
        return bot.reply_to(message, "❗ Geçersiz süre. Ör: `10m`, `2h`, `1d`")
    remind_text = parts[2]
    fire_at     = time.time() + dur
    data.setdefault("reminders", []).append({
        "chat_id":    message.chat.id,
        "message_id": message.message_id,
        "user_id":    message.from_user.id,
        "text":       remind_text,
        "fire_at":    fire_at,
    })
    save_data(data)
    bot.reply_to(message, f"⏰ Hatırlatıcı ayarlandı: `{parts[1]}` sonra hatırlatacağım.")

# ====================== KELİME İSTATİSTİKLERİ ======================
@bot.message_handler(commands=["topwords"])
def top_words_cmd(message):
    update_stats("commands")
    cid   = str(message.chat.id)
    words = data.get("word_stats", {}).get(cid, {})
    if not words:
        return bot.reply_to(message, "📊 Henüz kelime verisi yok.")
    top = sorted(words.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = "\n".join(f"`{i+1}.` {w} — *{c}* kez" for i, (w, c) in enumerate(top))
    bot.reply_to(message, f"📊 *En Çok Kullanılan Kelimeler:*\n\n{lines}")

# ====================== KULLANICI PROFİLİ ======================
@bot.message_handler(commands=["profile", "info"])
def profile_cmd(message):
    update_stats("commands")
    target = get_target(message) or message.from_user
    sid    = str(target.id)
    warns  = data["warnings"].get(sid, 0)
    muted  = sid in data["muted_until"] and time.time() < data["muted_until"].get(sid, 0)
    banned = target.id in data["banned_users"]
    msgs   = data.get("user_message_counts", {}).get(sid, 0)
    afk    = "Evet" if sid in data["afk"] else "Hayır"

    status_icons = []
    if banned: status_icons.append("🚫 Banlı")
    if muted:  status_icons.append("🔇 Susturulmuş")
    if not status_icons: status_icons.append("✅ Aktif")

    lines = [
        f"👤 *Kullanıcı Profili*",
        f"🆔 ID: `{target.id}`",
        f"📛 Ad: {mention(target)}",
        f"⚠️ Uyarı: `{warns}/3`",
        f"💬 Mesaj: `{msgs}`",
        f"😴 AFK: {afk}",
        f"📌 Durum: {', '.join(status_icons)}",
    ]
    bot.reply_to(message, "\n".join(lines))

# ====================== BROADCAST ======================
@bot.message_handler(commands=["broadcast"])
def broadcast_cmd(message):
    if not is_owner(message.from_user.id): return
    update_stats("commands")
    text = (message.text or "").split(None, 1)
    if len(text) < 2:
        return bot.reply_to(message, "Kullanım: `/broadcast <mesaj>`")
    msg     = text[1]
    sent    = 0
    failed  = 0
    for gid in data.get("group_ids", []):
        try:
            bot.send_message(int(gid), f"📢 *Duyuru:*\n\n{msg}")
            sent += 1
        except Exception:
            failed += 1
    bot.reply_to(message, f"📢 Broadcast tamamlandı: ✅ {sent} grup | ❌ {failed} başarısız")

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
        f"🔍 Filtre: `{sum(len(v) for v in data['filters'].values())}`\n"
        f"👥 Grup: `{len(data.get('group_ids', []))}`"
    )

# ====================== YARDIM ======================
HELP_TEXT = """
🌹 *Berxwedan Bot — Komutlar*

*🛡️ Moderasyon (Kurucu):*
`/ban [@/ID] [sebep]` — Kullanıcıyı banla
`/unban <@/ID>` — Banı kaldır
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
`/lock` / `/unlock` — Grubu kilitle/aç
`/setwelcome <mesaj>` — Hoş geldin mesajı
`/setgoodbye <mesaj>` — Güle güle mesajı
`/setrules <kurallar>` — Kuralları ayarla
`/rules` — Kuralları göster
`/pin` — Mesajı sabitle (reply ver)
`/unpin` — Tüm sabitlemeleri kaldır
`/poll Soru? | A | B | C` — Anket oluştur
`/nightmode HH:MM HH:MM` — Gece modu
`/nightmode off` — Gece modunu kapat

*💡 Herkes:*
`/afk [sebep]` — AFK moduna gir
`/warnings [@/ID]` — Uyarıları gör
`/profile [@/ID]` — Kullanıcı profili
`/topwords` — En çok kullanılan kelimeler
`/remind <süre> <mesaj>` — Hatırlatıcı kur
`/stats` — Bot istatistikleri
`/help` — Bu mesaj

*🤖 AI:* Mesajında *bot* kelimesi geçerse otomatik cevap verir.
Örnek: _"bot bu konu hakkında ne düşünüyorsun?"_
"""

@bot.message_handler(commands=["help", "start"])
def help_cmd(message):
    update_stats("commands")
    # Grubu kaydet
    cid = str(message.chat.id)
    if cid not in data.get("group_ids", []) and message.chat.type != "private":
        data.setdefault("group_ids", []).append(cid)
        save_data(data)
    bot.reply_to(message, HELP_TEXT)

# ====================== ANA MESAJ İŞLEYİCİ ======================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    update_stats("messages")
    uid  = str(message.from_user.id)
    cid  = str(message.chat.id)
    text = message.text or ""

    # Grubu takip et
    if cid not in data.get("group_ids", []) and message.chat.type != "private":
        data.setdefault("group_ids", []).append(cid)
        save_data(data)

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

    # --- Gece modu kontrolü ---
    if is_night_mode_active(cid) and not is_admin(message):
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        return

    # --- Kelime istatistikleri ---
    words = re.findall(r"\b\w{3,}\b", text.lower())
    ws = data.setdefault("word_stats", {}).setdefault(cid, {})
    for w in words:
        ws[w] = ws.get(w, 0) + 1
    # Kullanıcı mesaj sayacı
    data.setdefault("user_message_counts", {})[uid] = \
        data["user_message_counts"].get(uid, 0) + 1
    save_data(data)

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

    # --- AI Tetikleyici: "bot" kelimesi geçiyorsa ---
    if AI_TRIGGER_PATTERN.search(text):
        threading.Thread(
            target=call_ai,
            args=(message.chat.id, text, message),
            daemon=True
        ).start()

# ====================== HATA YÖNETİMİ ======================
@bot.message_handler(func=lambda m: True)
def fallback(message):
    pass

def handle_error(exception):
    logger.error(f"Polling hatası: {exception}")

# ====================== ZAMANLAYICILAR ======================
def auto_unmute():
    """Süresi dolan mute'ları otomatik kaldırır."""
    while True:
        now = time.time()
        to_remove = [uid for uid, until in list(data["muted_until"].items()) if now >= until]
        for uid in to_remove:
            del data["muted_until"][uid]
        if to_remove:
            save_data(data)
        time.sleep(60)

def auto_remind():
    """Hatırlatıcıları kontrol eder ve zamanı gelen bildirimleri gönderir."""
    while True:
        now = time.time()
        pending   = data.get("reminders", [])
        remaining = []
        for r in pending:
            if now >= r["fire_at"]:
                try:
                    bot.send_message(
                        r["chat_id"],
                        f"⏰ *Hatırlatıcı* — [yoldaş](tg://user?id={r['user_id']})\n\n{r['text']}",
                        reply_to_message_id=r.get("message_id"),
                    )
                except Exception as e:
                    logger.warning(f"Hatırlatıcı gönderilemedi: {e}")
            else:
                remaining.append(r)
        if len(remaining) != len(pending):
            data["reminders"] = remaining
            save_data(data)
        time.sleep(15)

def auto_night_mode_notify():
    """Gece modu başlayınca gruba bildirim gönderir (günde 1 kez)."""
    notified: dict[str, str] = {}  # {chat_id: "YYYY-MM-DD"}
    while True:
        today = datetime.now().strftime("%Y-%m-%d")
        for cid, nm in list(data.get("night_mode", {}).items()):
            if not nm.get("enabled"):
                continue
            if notified.get(cid) == today:
                continue
            if is_night_mode_active(cid):
                try:
                    bot.send_message(
                        int(cid),
                        f"🌙 *Gece modu başladı.*\n"
                        f"Saat `{nm['end']}`'e kadar sadece adminler yazabilir."
                    )
                    notified[cid] = today
                except Exception:
                    pass
        time.sleep(60)

threading.Thread(target=auto_unmute,          daemon=True).start()
threading.Thread(target=auto_remind,           daemon=True).start()
threading.Thread(target=auto_night_mode_notify, daemon=True).start()

# ====================== BAŞLAT ======================
if __name__ == "__main__":
    logger.info("🚩 Berxwedan Bot — Gelişmiş Versiyon AKTİF!")
    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=30,
        logger_level=logging.WARNING,
        allowed_updates=["message", "callback_query", "chat_member"]
    )
