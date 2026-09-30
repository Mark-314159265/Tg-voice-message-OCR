import os
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

bot.polling(none_stop=True)
bot.polling(none_stop=True)