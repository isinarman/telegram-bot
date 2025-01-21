import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import openai

# Инициализация приложения
app = web.Application()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка переменных окружения
load_dotenv()

# Настройки для Render
PORT = int(os.getenv('PORT', '8080'))
RENDER_URL = "https://telegram-bot-ag71.onrender.com"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка наличия ключей
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо указать TELEGRAM_TOKEN и OPENAI_API_KEY в .env файле.")

# Инициализация OpenAI API
openai.api_key = OPENAI_API_KEY

# Промпт остается без изменений
PROMPT = """
R — Role:
Вас зовут IZI, вы женского пола. Вы выступаете как эксперт-консультант от Агентства автоматизации «QazaqBots», одного из лучших агентств в Казахстане. 
Вы представляете команду, собравшую ведущих специалистов по разработке и интеграции Искусственного интеллекта в мессенджеры. Агентство помогает бизнесу налаживать поток целевых заявок и эффективно обрабатывать их 24/7 с помощью интеллектуальных решений. Ваш опыт охватывает полный цикл автоматизации, от идеи до внедрения, и вы помогаете клиентам превращать их бизнес в стабильный источник прибыли.

A — Action:
Ваша задача:
1. Отвечать на вопросы о разработке, интеграции и возможностях Искусственного интеллекта, подчеркивая преимущества работы с «QazaqBots».
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Здравствуйте, {user_first_name}! Я IZI Искусственный интеллект от агентства автоматизации «QazaqBots». "
            f"Наш слоган: «Умные боты для умных решений». Чем могу помочь?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_message = update.message.text
    try:
        # Используем актуальный метод OpenAI API для генерации ответа
        response = openai.ChatCompletion.create(
    model="gpt-4",  # указываем модель
    messages=[  # сообщения
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": user_message}
    ]
)
        reply = response['choices'][0]['message']['content']
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка OpenAI API: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f'Произошла ошибка: {context.error}')
    if update and update.message:
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")

# Обработчик для корневого URL
async def handle_root(request):
    return web.Response(text="Telegram bot is running!")

async def setup_webhook(application: Application) -> web.Application:
    # Получаем объект web.Application из существующего приложения
    webhook_app = web.Application()
    webhook_path = f"/webhook/{TELEGRAM_TOKEN}"

    async def handle_webhook(request):
        try:
            # Получаем обновление
            update = Update.de_json(await request.json(), application.bot)
            await application.process_update(update)
            return web.Response()
        except Exception as e:
            logging.error(f"Webhook error: {e}")
            return web.Response(status=500)

    # Добавляем обработчик для вебхуков
    webhook_app.router.add_post(webhook_path, handle_webhook)
    webhook_app.router.add_get("/", handle_root)
    return webhook_app

async def main():
    # Инициализация приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    # Инициализация приложения перед запуском webhook
    await application.initialize()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Настройка webhook или polling в зависимости от среды
    if RENDER_URL:
        logging.info(f"Запуск в режиме webhook на порту {PORT}")
        webhook_app = await setup_webhook(application)
        runner = web.AppRunner(webhook_app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)

        await application.bot.set_webhook(
            url=f"{RENDER_URL}/webhook/{TELEGRAM_TOKEN}",
            allowed_updates=Update.ALL_TYPES
        )

        await site.start()

        # Держим приложение запущенным
        while True:
            await asyncio.sleep(3600)
    else:
        logging.info("Запуск в режиме polling")
        await application.initialize()
        await application.start()
        await application.run_polling()
        await application.stop()

if __name__ == "__main__":
    import asyncio

    try:
        logging.info("Бот запущен...")
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        sys.exit(1)
