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
PORT = int(os.getenv("PORT", 8443))

# Проверка наличия ключей
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо указать TELEGRAM_TOKEN и OPENAI_API_KEY в .env файле.")

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# Промпт для GPT
PROMPT = """
R — Role:
Вас зовут IZI, вы женского пола. Вы выступаете как эксперт-консультант от Агентства автоматизации «QazaqBots». 
Агентство помогает бизнесу налаживать поток целевых заявок и обрабатывать их 24/7. Ваш опыт охватывает полный цикл автоматизации.

A — Action:
Ваша задача:
1. Отвечать на вопросы о разработке и интеграции чат-ботов.
2. Подчеркивать преимущества работы с «QazaqBots».
3. Приглашать клиента на бесплатную консультацию.

F — Format:
• Краткий, профессиональный ответ.
• Завершение диалога приглашением на бесплатную консультацию.

T — Tone:
• Дружелюбный, уверенный, экспертный.
"""

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Здравствуйте, {user_first_name}! Я бот агентства QazaqBots. Чем могу помочь?"
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
async def set_webhook():
    bot = Bot(TELEGRAM_TOKEN)
    webhook_url = f"{RENDER_URL}/webhook/{TELEGRAM_TOKEN}"
    try:
        success = await bot.set_webhook(webhook_url)
        if success:
            logging.info("Webhook установлен успешно!")
        else:
            logging.error("Не удалось установить Webhook.")
    except Exception as e:
        logging.error(f"Ошибка при установке Webhook: {e}")
        if "retry after" in str(e):
            retry_time = int(str(e).split("retry after ")[1].split("'")[0])
            logging.info(f"Повторная попытка через {retry_time} секунд...")
            await asyncio.sleep(retry_time)
            await set_webhook()

# Основная функция запуска бота
async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Установка Webhook
    await set_webhook()

    # Запуск Webhook-сервера
    logging.info("Запуск веб-сервера...")
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=f"/webhook/{TELEGRAM_TOKEN}"
    )

# Запуск бота
if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(main())
