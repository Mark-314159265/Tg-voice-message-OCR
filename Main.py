import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in environment variables")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GOOGLE_API_KEY)

# Simple HTTP health check server for Render Web Service & UptimeRobot
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        pass  # Suppress HTTP access logging

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

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
        bot.reply_to(message, f"сталася помилка: {e}")

if __name__ == '__main__':
    # Start the HTTP server in a background thread so Render detects an open port
    threading.Thread(target=run_health_server, daemon=True).start()
    bot.polling(none_stop=True)