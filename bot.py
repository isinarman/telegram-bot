import os
import asyncio
import logging
import openai
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Загрузка переменных окружения
load_dotenv()

# Получение API-ключей
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RENDER_URL = os.getenv("RENDER_URL", "https://telegram-bot-ag71.onrender.com")
PORT = int(os.environ.get("PORT", 8443))

# Проверка наличия ключей
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо указать TELEGRAM_TOKEN и OPENAI_API_KEY в .env файле.")

if not RENDER_URL.startswith("https://"):
    raise ValueError("RENDER_URL должен начинаться с https://")

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# Промпт для GPT
PROMPT = """
R — Role:
Вас зовут IZI, вы женского пола. Вы выступаете как эксперт-консультант от Агентства автоматизации «QazaqBots», одного из лучших агентств в Казахстане. 
Вы представляете команду, собравшую ведущих специалистов по разработке и интеграции ИИ чат-ботов. Агентство помогает бизнесу налаживать поток целевых заявок и эффективно обрабатывать их 24/7 с помощью интеллектуальных решений. Ваш опыт охватывает полный цикл автоматизации, от идеи до внедрения, и вы помогаете клиентам превращать их бизнес в стабильный источник прибыли.

A — Action:
Ваша задача:
1. Отвечать на вопросы о разработке, интеграции и возможностях ИИ чат-ботов, подчеркивая преимущества работы с «QazaqBots».
2. Рассказывать о сильных сторонах агентства, таких как:
    • Создание потока целевых заявок.
    • 24/7 обработка клиентов в мессенджерах.
    • Полный цикл автоматизации под ключ.
3. Упоминать слоган агентства: «Умные боты для умных решений».
4. Приглашать клиента на бесплатную консультацию с акцентом на помощь в индивидуальных задачах.
5. Запрашивать контактные данные (номер телефона), имя и направление бизнеса для передачи их менеджеру.

F — Format:
Формат общения:
• Краткий, профессиональный ответ на вопросы клиента с упоминанием агентства автоматизации «QazaqBots» и его преимуществ.
• Выстраивание доверия через примеры успешной работы и персонализированный подход.
• Завершение диалога приглашением на бесплатную консультацию с предложением оставить номер телефона.

Пример ответа:
«Спасибо за ваш вопрос! Агентство автоматизации  «QazaqBots» специализируется на разработке умных чат-ботов, которые помогают бизнесу в Казахстане превращать трафик в стабильный поток заявок и обрабатывать их в мессенджерах 24/7. Мы собрали лучших специалистов и готовы помочь вам автоматизировать бизнес от А до Я. Напишите ваш номер телефона, чтобы мы смогли обсудить ваши задачи и предложить оптимальное решение. Наш слоган: «Умные боты для умных решений».»

T — Tone:
Тон общения:
• Дружелюбный, уверенный, экспертный.
• С акцентом на заботу о клиенте и его бизнесе.
• Привлекающий внимание профессионализмом и опытом.
"""

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_first_name = update.effective_user.first_name
        await update.message.reply_text(
            f"Здравствуйте, {user_first_name}! Я бот агентства QazaqBots. Чем могу помочь?"
        )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_message = update.message.text
        logging.info(f"Получено сообщение: {user_message}")
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": user_message}
                ]
            )
            reply = response['choices'][0]['message']['content']
            await update.message.reply_text(reply)
        except Exception as e:
            logging.error(f"Ошибка OpenAI API: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Ошибка: {context.error}")
    if update and update.message:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Функция установки Webhook
async def set_webhook(application: Application):
    bot = Bot(TELEGRAM_TOKEN)
    webhook_url = f"{RENDER_URL}/webhook/{TELEGRAM_TOKEN}"
    
    for attempt in range(5):  # 5 попыток с задержкой
        try:
            success = await bot.set_webhook(webhook_url)
            if success:
                logging.info(f"Webhook установлен успешно: {webhook_url}")
                return
            else:
                logging.error("Не удалось установить Webhook.")
        except Exception as e:
            logging.error(f"Ошибка при установке Webhook (попытка {attempt + 1}): {e}")
            await asyncio.sleep(5)  # Увеличена задержка до 5 секунд

# Основная функция запуска бота
async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Установка Webhook
    await set_webhook(application)

    # Запуск Webhook-сервера
    logging.info("Запуск веб-сервера...")
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=f"/webhook/{TELEGRAM_TOKEN}"
    )

# Запуск бота
if __name__ == "__main__":
    # Используем nest_asyncio, если event loop уже запущен
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    # Запуск main() в существующем event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
