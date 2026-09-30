import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import telebot
from google import genai
from google.genai import types

# Завантаження змінних оточення з .env файлу (якщо присутній)
load_dotenv()

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

if not TELEGRAM_TOKEN:
    raise ValueError("Помилка: змінна оточення TELEGRAM_TOKEN не встановлена! Додайте її у .env або налаштування платформи.")

if not GOOGLE_API_KEY:
    raise ValueError("Помилка: змінна оточення GOOGLE_API_KEY не встановлена! Додайте її у .env або налаштування платформи.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GOOGLE_API_KEY)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Мінімальний HTTP сервер для проходження перевірки стану (Health Check) на Render."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is healthy and running!")

    def log_message(self, format, *args):
        # Приглушуємо логування GET запитів, щоб не засмічувати консоль
        pass


def run_health_server(port: int):
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привіт! Надішли мені голосове повідомлення (voice message), і я транскрибую його у текст за допомогою Google Gemini."
    )


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        audio_part = types.Part.from_bytes(
            data=downloaded_file,
            mime_type='audio/ogg'
        )
        
        prompt = "напиши текст з цього аудіо без жодних інших слів"
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, audio_part]
        )

        bot.reply_to(message, response.text)

    except Exception as e:
        bot.reply_to(message, f"Сталася помилка: {e}")


if __name__ == '__main__':
    # Якщо задана змінна PORT (наприклад, на Render Web Service), запускаємо HTTP health check у фоновому потоці
    port_env = os.environ.get('PORT')
    if port_env:
        try:
            port = int(port_env)
            health_thread = threading.Thread(target=run_health_server, args=(port,), daemon=True)
            health_thread.start()
            print(f"Health check сервер успішно запущено на порту {port}")
        except ValueError:
            print(f"Невірне значення PORT: {port_env}")

    print(f"Бот запускається (модель: {GEMINI_MODEL})...")
    bot.infinity_polling()