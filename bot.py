# ====================== GELİŞTİRİLMİŞ DEVRİMCİ AI RESİM ======================
@bot.message_handler(commands=['airesim'])
def generate_image(message):
    user_input = " ".join(message.text.split()[1:]).strip()
    if not user_input:
        user_input = "Kürdistan dağlarında gerilla"

    bot.reply_to(message, "🖼️ Devrimci AI resim üretiliyor... (5-10 sn) 🔥")

    try:
        # Çok daha güçlü ve sansürü aşmaya yönelik prompt
        enhanced = (
            f"{user_input}, Kurdish mountains landscape, realistic Kurdish people, "
            "traditional Kurdish clothing, strong and proud expression, "
            "green hills and rocky mountains of Kurdistan, clear sky, "
            "cinematic lighting, national geographic style, highly detailed, "
            "8k, realistic photography, no violence, no terrorist, peaceful resistance atmosphere"
        )

        clean_prompt = enhanced.replace(" ", "%20").replace(",", "%2C")
        seed = random.randint(100000, 999999)

        image_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1024&seed={seed}&model=flux&safe=false&enhance=true"

        bot.send_photo(
            message.chat.id, 
            image_url,
            caption=f"🖼️ **{user_input}**\n🚩 Berxwedan!"
        )
        
    except Exception:
        bot.reply_to(message, "❌ Resim şu anda üretilemedi. Farklı bir prompt dene.")
