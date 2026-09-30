import os
import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Усі технічні деталі та помилки виводяться в логи Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', '1111')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in environment variables")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GOOGLE_API_KEY)

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
            logger.error(f"Помилка завантаження {AUTH_FILE}: {e}")
    return set()

def save_authorized_user(user_id: int):
    with auth_lock:
        authorized_users.add(user_id)
        try:
            with open(AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(list(authorized_users), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Помилка збереження {AUTH_FILE}: {e}")

authorized_users = load_authorized_users()

# ==========================================================
# 🔄 Список моделей та автоперемикання при навантаженні
# ==========================================================
DEFAULT_MODELS = [
    'gemini-3.8-flash',
    'gemini-3.5-flash',
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-flash-latest',
    'gemini-2.5-pro'
]

env_models = os.environ.get('GEMINI_MODELS')
if env_models:
    MODELS_LIST = [m.strip() for m in env_models.split(',') if m.strip()]
else:
    MODELS_LIST = DEFAULT_MODELS

current_model_index = 0
models_lock = threading.Lock()

def is_retryable_error(e: Exception) -> bool:
    err_str = str(e).upper()
    retryable_markers = [
        '503', 'UNAVAILABLE', 'HIGH DEMAND',
        '429', 'RESOURCE_EXHAUSTED', 'QUOTA', 'RATE_LIMIT',
        '404', 'NOT_FOUND', '500', 'INTERNAL'
    ]
    return any(marker in err_str for marker in retryable_markers)

def transcribe_audio_with_fallback(audio_bytes: bytes, status_updater=None) -> str:
    global current_model_index
    total_models = len(MODELS_LIST)
    prompt = "напиши текст з цього аудіо без жодних інших слів"
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg')
    last_error = None

    for attempt in range(total_models):
        with models_lock:
            model = MODELS_LIST[current_model_index]

        try:
            logger.info(f"Спроба розпізнавання через: {model} (спроба {attempt + 1}/{total_models})")
            if status_updater and attempt > 0:
                status_updater("⏳ Запит відправлено, очікую текст...")

            response = client.models.generate_content(
                model=model,
                contents=[prompt, audio_part]
            )

            text = response.text or ""
            logger.info(f"Успішно розпізнано моделлю: {model}")
            return text.strip()

        except Exception as e:
            last_error = e
            logger.warning(f"Модель {model} повернула помилку: {e}")

            if is_retryable_error(e):
                with models_lock:
                    current_model_index = (current_model_index + 1) % total_models
                    next_model = MODELS_LIST[current_model_index]

                logger.info(f"Перемикаємось на наступну модель: {next_model}")

                if status_updater:
                    if '503' in str(e) or 'HIGH DEMAND' in str(e).upper():
                        status_updater("⏳ Високе навантаження, змінюю модель...")
                    elif '429' in str(e) or 'QUOTA' in str(e).upper():
                        status_updater("⏳ Ліміт моделі вичерпано, змінюю модель...")
                    else:
                        status_updater("⏳ Зміна моделі, зачекайте...")

                time.sleep(1)
                continue
            else:
                logger.error(f"Непоправна помилка моделі {model}: {e}", exc_info=True)
                raise e

    logger.error(f"Всі моделі вичерпано. Остання помилка: {last_error}", exc_info=True)
    raise RuntimeError(f"Всі моделі недоступні: {last_error}")

# ==========================================================
# 🌐 Health Check сервер для Render Web Service
# ==========================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================================
# 🤖 Обробка повідомлень Telegram
# ==========================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        bot.reply_to(message, "🔒 Введіть пароль для доступу:")
        return
    bot.reply_to(message, "Надішліть голосове повідомлення 🎤")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = (message.text or '').strip()

    if user_id not in authorized_users:
        if text == BOT_PASSWORD:
            save_authorized_user(user_id)
            bot.reply_to(message, "✅ Доступ надано! Надішліть голосове повідомлення 🎤")
        else:
            bot.reply_to(message, "❌ Невірний пароль. Спробуйте ще раз:")
        return

    bot.reply_to(message, "Надішліть голосове повідомлення 🎤")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        bot.reply_to(message, "🔒 Спочатку введіть пароль для доступу:")
        return

    status_msg = None
    try:
        status_msg = bot.reply_to(message, "⏳ Запит відправлено, очікую текст...")
    except Exception as e:
        logger.warning(f"Не вдалося відправити початковий статус: {e}")

    def update_status(text: str):
        if not status_msg:
            return
        try:
            bot.edit_message_text(text, chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        except Exception as edit_err:
            logger.debug(f"Не вдалося оновити статус: {edit_err}")

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        transcribed_text = transcribe_audio_with_fallback(
            downloaded_file,
            status_updater=update_status
        )

        if not transcribed_text:
            transcribed_text = "(Текст не вдалося розпізнати або аудіо порожнє)"

        if status_msg:
            try:
                bot.edit_message_text(
                    transcribed_text,
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )
            except Exception:
                bot.reply_to(message, transcribed_text)
        else:
            bot.reply_to(message, transcribed_text)

    except Exception as e:
        logger.error(f"Помилка обробки голосового повідомлення: {e}", exc_info=True)
        err_user_text = "⚠️ Не вдалося розпізнати аудіо. Спробуйте пізніше."
        if status_msg:
            try:
                bot.edit_message_text(err_user_text, chat_id=status_msg.chat.id, message_id=status_msg.message_id)
            except Exception:
                bot.reply_to(message, err_user_text)
        else:
            bot.reply_to(message, err_user_text)

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    logger.info("Бот успішно запущений...")
    bot.infinity_polling()