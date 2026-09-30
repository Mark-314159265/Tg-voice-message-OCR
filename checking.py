import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY не знайдено у змінних оточення!")

client = genai.Client(api_key=GOOGLE_API_KEY)

with open('models.txt', 'r', encoding='utf-8') as file:
    models = file.read().splitlines()

for model_name in models:
    clean_name = model_name.strip()
    if not clean_name:
        continue
    
    try:
        response = client.models.generate_content(
            model=clean_name,
            contents="тест"
        )
        print(f"{clean_name}: успіх")
    except Exception as e:
        print(f"{clean_name}: помилка, {e}")