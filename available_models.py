import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY не знайдено у змінних оточення!")

client = genai.Client(api_key=GOOGLE_API_KEY)

for model in client.models.list():
    print(model.name)