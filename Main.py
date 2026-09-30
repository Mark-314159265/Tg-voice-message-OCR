import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import telebot
from google import genai
from google.genai import types

# Завантаження змінних оточення з .env
load_dotenv()

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', '1111')

if not TELEGRAM_TOKEN:
    raise ValueError("Помилка: змінна оточення TELEGRAM_TOKEN не встановлена! Додайте її у .env або налаштування платформи.")

if not GOOGLE_API_KEY:
    raise ValueError("Помилка: змінна оточення GOOGLE_API_KEY не встановлена! Додайте її у .env або налаштування платформи.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GOOGLE_API_KEY)

# ==========================================================
# 🔄 Пул моделей для обходу денного ліміту (Quota / 429)
# Кожна модель має свій окремий денний ліміт (RPD).
# Gemini 3.1 Flash Lite має 500 RPD, Gemini 3.5 Flash Lite має 500 RPD,
# а інші моделі додають ще десятки безкоштовних запитів!
# ==========================================================
DEFAULT_MODELS = [
    'gemini-3.1-flash-lite',  # 500 запитів/день
    'gemini-3.5-flash-lite',  # 500 запитів/день
    'gemini-2.5-flash',       # 20 запитів/день
    'gemini-2.5-flash-lite',  # 20 запитів/день
    'gemini-3.6-flash',       # 20 запитів/день
    'gemini-3.7-flash',       # 20 запитів/день
    'gemini-3.5-flash',       # 20 запитів/день
    'gemini-3.8-flash',       # 20 запитів/день
]

env_models = os.environ.get('GEMINI_MODELS')
if env_models:
    MODELS_LIST = [m.strip() for m in env_models.split(',') if m.strip()]
else:
    MODELS_LIST = DEFAULT_MODELS

current_model_index = 0
models_lock = threading.Lock()


def is_quota_error(e: Exception) -> bool:
    """Перевіряє, чи помилка викликана перевищенням лімітів запитів (429 / RESOURCE_EXHAUSTED)."""
    if hasattr(e, 'code') and getattr(e, 'code') == 429:
        return True
    err_str = str(e).upper()
    return any(marker in err_str for marker in ['429', 'RESOURCE_EXHAUSTED', 'QUOTA', 'RATE_LIMIT'])


def transcribe_with_fallback(audio_data: bytes, prompt: str) -> tuple[str, str]:
    """
    Транскрибує аудіо, автоматично перемикаючись на наступну модель,
    якщо поточна досягла ліміту 429 / RESOURCE_EXHAUSTED.
    Повертає (текст, назва_успішної_моделі).
    """
    global current_model_index
    total_models = len(MODELS_LIST)
    audio_part = types.Part.from_bytes(data=audio_data, mime_type='audio/ogg')
    last_error = None

    for attempt in range(total_models):
        with models_lock:
            model = MODELS_LIST[current_model_index]

        try:
            print(f"Спроба транскрибації через модель: {model}...")
            response = client.models.generate_content(
                model=model,
                contents=[prompt, audio_part]
            )
            return response.text, model
        except Exception as e:
            last_error = e
            if is_quota_error(e):
                print(f"⚠️ Модель {model} вичерпала ліміт запитів: {e}")
                with models_lock:
                    current_model_index = (current_model_index + 1) % total_models
                    next_model = MODELS_LIST[current_model_index]
                    print(f"🔄 Автоматично перемикаємось на: {next_model} (спроба {attempt + 1}/{total_models})")
                continue
            else:
                # Інші помилки (наприклад, збій мережі або некоректні дані)
                raise e

    raise RuntimeError(f"Всі доступні моделі вичерпали денний ліміт запитів. Остання помилка: {last_error}")


# ==========================================================
# 🔐 Авторизація за паролем
# ==========================================================
AUTH_FILE = "authorized_users.json"
auth_lock = threading.Lock()


def load_authorized_users() -> set:
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data)
        except Exception as e:
            print(f"Помилка завантаження {AUTH_FILE}: {e}")
    return set()


def save_authorized_user(user_id: int):
    with auth_lock:
        authorized_users.add(user_id)
        try:
            with open(AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(list(authorized_users), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Помилка збереження {AUTH_FILE}: {e}")


authorized_users = load_authorized_users()


# ==========================================================
# 🌐 Health Check сервер для Render Web Service
# ==========================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is healthy and running!")

    def log_message(self, format, *args):
        pass


def run_health_server(port: int):
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()


# ==========================================================
# 🤖 Обробники повідомлень Telegram
# ==========================================================
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        bot.reply_to(
            message,
            "🔒 Бот захищений паролем.\nБудь ласка, введіть пароль для доступу до бота:"
        )
        return

    with models_lock:
        active_model = MODELS_LIST[current_model_index]

    bot.reply_to(
        message,
        f"👋 Привіт! Надішліть мені голосове повідомлення (voice message), і я транскрибую його у текст.\n\n"
        f"🤖 Активна модель Gemini: `{active_model}`\n"
        f"💡 Доступні команди:\n"
        f"/status — стан та список доступних моделей\n"
        f"/reset_models — скинути активну модель на початкову"
    )


@bot.message_handler(commands=['status', 'model'])
def handle_status(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        return

    with models_lock:
        active_model = MODELS_LIST[current_model_index]
        models_view = "\n".join(
            f"{'👉' if i == current_model_index else '  '} {i+1}. {m}"
            for i, m in enumerate(MODELS_LIST)
        )

    bot.reply_to(
        message,
        f"🤖 **Поточна активна модель:** `{active_model}`\n\n"
        f"📋 **Пул моделей (автоперемикання при 429):**\n{models_view}\n\n"
        f"💡 Якщо поточна модель вичерпає денний ліміт (500 запитів), бот миттєво перемкнеться на наступну."
    )


@bot.message_handler(commands=['reset_models'])
def handle_reset_models(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        return

    global current_model_index
    with models_lock:
        current_model_index = 0
        active_model = MODELS_LIST[0]

    bot.reply_to(message, f"🔄 Активну модель успішно скинуто на: `{active_model}`")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = (message.text or '').strip()

    if user_id not in authorized_users:
        if text == BOT_PASSWORD:
            save_authorized_user(user_id)
            bot.reply_to(
                message,
                "✅ Пароль правильний! Доступ надано.\n\nТепер надішліть мені голосове повідомлення для розпізнавання тексту 🎤"
            )
        else:
            bot.reply_to(
                message,
                "❌ Невірний пароль. Будь ласка, введіть правильний пароль:"
            )
        return

    bot.reply_to(
        message,
        "Надішліть мені голосове повідомлення (voice message), щоб я перетворив його на текст 🎤"
    )


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        bot.reply_to(
            message,
            "🔒 Доступ обмежено. Будь ласка, спочатку надішліть пароль текстовим повідомленням."
        )
        return

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        prompt = "напиши текст з цього аудіо без жодних інших слів"
        transcribed_text, used_model = transcribe_with_fallback(downloaded_file, prompt)

        bot.reply_to(message, transcribed_text)

    except Exception as e:
        bot.reply_to(message, f"Сталася помилка: {e}")


if __name__ == '__main__':
    port_env = os.environ.get('PORT')
    if port_env:
        try:
            port = int(port_env)
            health_thread = threading.Thread(target=run_health_server, args=(port,), daemon=True)
            health_thread.start()
            print(f"Health check сервер успішно запущено на порту {port}")
        except ValueError:
            print(f"Невірне значення PORT: {port_env}")

    with models_lock:
        init_model = MODELS_LIST[current_model_index]

    print(f"Бот запускається (початкова модель: {init_model})...")
    bot.infinity_polling()