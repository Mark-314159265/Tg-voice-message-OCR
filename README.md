# 🎙️ Telegram Voice-to-Text Bot (Gemini AI)

Telegram-бот для автоматичної транскрибації голосових повідомлень у текст за допомогою Google Gemini API (`google-genai`).

---

## 📋 Можливості

- 🎧 Приймає голосові повідомлення (voice messages) у Telegram.
- 🔐 **Захист паролем**: при першому запуску бот вимагає пароль (за замовчуванням `1111`). Неавторизовані користувачі не мають доступу до функціоналу.
- ⚡ Використовує моделі Google Gemini (за замовчуванням `gemini-2.5-flash`) для точного розпізнавання мови.
- 🔒 Безпечне зберігання токенів та ключів через змінні оточення (`.env`).
- 🚀 Повністю готовий до безкоштовного деплою на **Render**.

---

## 🛠️ Локальне налаштування та запуск

### 1. Створення віртуального оточення
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate
```

### 2. Встановлення залежностей
```bash
pip install -r requirements.txt
```

### 3. Налаштування змінних оточення
Створіть файл `.env` на основі `.env.example`:
```bash
cp .env.example .env
```
Відкрийте файл `.env` та вкажіть свої дані:
```env
TELEGRAM_TOKEN=ваш_токен_від_BotFather
GOOGLE_API_KEY=ваш_ключ_з_Google_AI_Studio
BOT_PASSWORD=1111
GEMINI_MODEL=gemini-2.5-flash
```

> 🔑 **Де отримати ключі:**
> - `TELEGRAM_TOKEN`: створіть бота через [@BotFather](https://t.me/BotFather) у Telegram.
> - `GOOGLE_API_KEY`: згенеруйте безкоштовно у [Google AI Studio](https://aistudio.google.com/).
> - `BOT_PASSWORD`: пароль для авторизації користувачів у боті (за замовчуванням `1111`).

### 4. Запуск бота
```bash
python Main.py
```

---

## ☁️ Інструкція з деплою на Render (Безкоштовно)

Render дозволяє безкоштовно запускати веб-сервіси. Оскільки безкоштовні Background Workers на Render відсутні, бот налаштовано як **Web Service** із вбудованим легким HTTP health-check сервером.

### Крок 1. Завантаження коду на GitHub
1. Переконайтеся, що файл `.env` додано до `.gitignore` (він ніколи не повинен потрапити на GitHub!).
2. Створіть репозиторій на GitHub та запушіть код:
   ```bash
   git remote add origin https://github.com/ВАШ_КОРИСТУВАЧ/ВАШ_РЕПОЗИТОРІЙ.git
   git push -u origin main
   ```

### Крок 2. Створення сервісу на Render
1. Зареєструйтесь / увійдіть на [Render](https://render.com/).
2. Натисніть кнопку **New +** у правому верхньому кутку та виберіть **Web Service**.
3. Підключіть ваш GitHub-репозиторій.

### Крок 3. Налаштування параметрів сервісу
Заповніть форму:
- **Name**: `telegram-voice-transcriber` (або будь-яка інша назва)
- **Language**: `Python 3`
- **Region**: Франкфурт (`Frankfurt (EU Central)`) або найближчий
- **Branch**: `main`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  python Main.py
  ```
- **Instance Type**: `Free`

### Крок 4. Додавання секретних змінних (Environment Variables)
У розділі **Environment Variables** додайте:
1. **Key**: `TELEGRAM_TOKEN`  
   **Value**: ваш токен бота (наприклад, `1234567890:AAH...`)
2. **Key**: `GOOGLE_API_KEY`  
   **Value**: ваш ключ Gemini API (наприклад, `AIzaSy...`)
3. **Key**: `BOT_PASSWORD`  
   **Value**: `1111` (або будь-який інший пароль на ваш вибір)
4. *(Опціонально)* **Key**: `GEMINI_MODEL`  
   **Value**: `gemini-2.5-flash`

### Крок 5. Запуск
Натисніть **Deploy Web Service** (або **Create Web Service**).
Render автоматично встановить залежності, запустить `Main.py` і пройде перевірку працездатності (порт призначається Render автоматично).

> 💡 **Порада щодо підтримки активності (Keep-Alive):**
> Безкоштовний тариф Render переводить сервіс у "сон" після 15 хвилин без HTTP-запитів. Щоб бот працював 24/7 без зупинок:
> 1. Скопіюйте URL вашого сервісу на Render (наприклад, `https://telegram-voice-transcriber.onrender.com`).
> 2. Зареєструйтесь на безкоштовному сервісі пінгів, наприклад [UptimeRobot](https://uptimerobot.com/) або [cron-job.org](https://cron-job.org/).
> 3. Створіть монітор з інтервалом запиту кожні 10-14 хвилин типу `HTTP(s)` на вашу URL-адресу. Наш вбудований сервер відповідатиме `200 OK`, і бот не засинатиме!

---

## 🛡️ Безпека
- Ніколи не зберігайте API-ключі або токени у відкритому вигляді в коді (`Main.py`, `checking.py` тощо).
- Файли `.env` та `authorized_users.json` додано до `.gitignore`, тому ваші ключі та список користувачів залишаються виключно у вас і не потрапляють до репозиторію.
