import base64
import requests
import urllib3
import warnings
import telebot

# ================== API KEYS ==================
TELEGRAM_BOT_TOKEN = "8036655262:AAEvzlyEKgcvHMh2aUhbrdMx9Iijmle-jCw"
PLANT_ID_API_KEY = "75tVmrqyQrjSDk4z0qz0WnlC7Z1jgDCj6xPMrYYcxnC5oqqJ79"

OPENROUTER_API_KEY = "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"
# ==============================================

warnings.filterwarnings("ignore", message="Unverified HTTPS request")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================== PLANT.ID ==================
def identify_plant(image_bytes):
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")

    r = requests.post(
        "https://api.plant.id/v2/identify",
        headers={
            "Content-Type": "application/json",
            "Api-Key": PLANT_ID_API_KEY
        },
        json={
            "images": [img_base64],
            "modifiers": ["crops_fast"],
            "language": "ru"
        },
        timeout=30,
        verify=False
    )
    return r.json() if r.status_code == 200 else None


def analyze_plant_health(image_bytes):
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")

    r = requests.post(
        "https://api.plant.id/v2/health_assessment",
        headers={
            "Content-Type": "application/json",
            "Api-Key": PLANT_ID_API_KEY
        },
        json={
            "images": [img_base64],
            "language": "ru"
        },
        timeout=30,
        verify=False
    )
    return r.json() if r.status_code == 200 else None


# ================== OPENROUTER ==================
def openrouter_request(prompt, max_tokens=120):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Plant Doctor Bot"
        },
        json={
            "model": "mistralai/mistral-7b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        },
        timeout=30
    )
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def get_ai_treatment_advice(plant_name, disease_name):
    prompt = (
        f"Растение: {plant_name}. "
        f"Проблема: {disease_name}. "
        f"Дай короткий практичный совет по лечению (1–2 предложения, без воды)."
    )
    return openrouter_request(prompt)


# ================== FORMAT RESPONSE ==================
def format_response(plant_data, health_data):
    lines = []

    plant_name = "Неизвестно"
    if plant_data and plant_data.get("suggestions"):
        s = plant_data["suggestions"][0]
        plant_name = s.get("plant_name", "Неизвестно")
        prob = s.get("probability", 0) * 100
        lines.append(f"🌿 *Растение:* {plant_name}")
        lines.append(f"🎯 *Уверенность:* {prob:.1f}%\n")

    diseases = health_data.get("health_assessment", {}).get("diseases", [])

    if not diseases:
        lines.append("✅ *Заболеваний не обнаружено.*")
        return "\n".join(lines)

    lines.append("⚠️ *ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:*\n")

    for i, d in enumerate(diseases, 1):
        name = d.get("name", "Неизвестно")
        prob = d.get("probability", 0) * 100
        lines.append(f"{i}. 🦠 *{name}* — {prob:.1f}%")

    main_disease = diseases[0].get("name", "Unknown")

    lines.append("\n💊 *РЕКОМЕНДАЦИЯ ИИ ПО ЛЕЧЕНИЮ:*")
    lines.append(get_ai_treatment_advice(plant_name, main_disease))

    return "\n".join(lines)


# ================== TELEGRAM ==================
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "🌿 *Plant Doctor Bot*\n\n"
        "📸 Диагностика — Plant.ID\n"
        "🤖 Совет по лечению — ИИ (OpenRouter)\n\n"
        "Отправь фото растения.",
        parse_mode="Markdown"
    )


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    msg = bot.reply_to(message, "🔄 Анализирую фото...", parse_mode="Markdown")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        image = bot.download_file(file_info.file_path)

        plant_data = identify_plant(image)
        health_data = analyze_plant_health(image)

        if not health_data:
            bot.edit_message_text(
                "❌ Не удалось получить данные о здоровье растения.",
                chat_id=message.chat.id,
                message_id=msg.message_id
            )
            return

        text = format_response(plant_data, health_data)

        bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка: {str(e)[:120]}",
            chat_id=message.chat.id,
            message_id=msg.message_id
        )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "📸 Отправь фото растения.")


if __name__ == "__main__":
    print("🌿 Plant Doctor Bot запущен (Plant.ID + OpenRouter)")
    bot.polling(none_stop=True)
