import telebot
from google import genai
from google.genai import types

TELEGRAM_TOKEN = '8792665703:AAHeweldGU_Zgn6l-2ZuoCHwWjSHM8QnEu4'
GOOGLE_API_KEY = 'AIzaSyCujYiDhjBloZvLSj61_LycZoRB2KEkn3A'

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
            model='gemini-3.6-flash',
            contents=[prompt, audio_part]
        )

        bot.reply_to(message, response.text)

    except Exception as e:
        bot.reply_to(message, f"сталася помилка: {e}")

bot.polling(none_stop=True)