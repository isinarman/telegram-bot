import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, ContextTypes, ConversationHandler, ApplicationBuilder
from aiohttp import web
import openai
import telegram

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
# Состояния для ConversationHandler
ASK_NICHE, ASK_NAME, ASK_PHONE = range(3)

# Ваш ID для отправки собранных данных
ADMIN_CHAT_ID = 352033952
ADMIN_ID = 352033952  # Ваш Telegram ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Здравствуйте, {user_first_name}! Я IZI Искусственный интеллект от агентства автоматизации «QazaqBots». "
            f"Наш слоган: «Умные боты для умных решений». Чем могу помочь?"
    )
    update.message.reply_text(
        "Привет, {user_first_name}! В какой нише вы работаете?"
    )
    return ASK_NICHE

# Получение ниши
def ask_niche(update, context):
    context.user_data['niche'] = update.message.text  # Сохраняем нишу
    update.message.reply_text("Спасибо! Как вас зовут?")
    return ASK_NAME

# Получение имени
def ask_name(update, context):
    context.user_data['name'] = update.message.text  # Сохраняем имя
    update.message.reply_text("Отлично! Теперь укажите ваш номер телефона.")
    return ASK_PHONE

# Получение телефона и отправка данных
def ask_phone(update, context):
    context.user_data['phone'] = update.message.text  # Сохраняем телефон
    
    # Отправка собранных данных админу
    niche = context.user_data['niche']
    name = context.user_data['name']
    phone = context.user_data['phone']
    message = f"Новая заявка!\n\nНиша: {niche}\nИмя: {name}\nТелефон: {phone}"
    
    # Отправляем сообщение админу
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
    
    update.message.reply_text("Спасибо! Мы скоро с вами свяжемся.")
    return ConversationHandler.END

# Обработка отмены
def cancel(update, context):
    update.message.reply_text("Вы отменили заполнение данных.")
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_message = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    
    # Пересылка сообщения администратору
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Сообщение от {user_name} ({user_id}): {user_message}"
    )
    try:
        # Используем актуальный метод OpenAI API для генерации ответа
        response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": user_message}
    ]
)
        reply = response['choices'][0]['message']['content']
        
        # Логирование ответа бота
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Ответ бота пользователю {user_name} ({user_id}): {reply}"
        )
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
    
    # Функция для обработки webhook
async def webhook_handler(request):
    data = await request.json()
    # Передать данные в бота
    await application.update_queue.put(data)
    return web.Response()

async def main():
    # Инициализация приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    # Инициализация приложения перед запуском webhook
    await application.initialize()
    app = web.Application()
    app.router.add_post(f"/webhook/{TELEGRAM_TOKEN}", webhook_handler)
    web.run_app(app, port=PORT)
    
    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NICHE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_niche)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Добавляем обработчик
    application.add_handler(conv_handler)

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Функция для обработки голосовых сообщений
async def handle_voice(update: Update, context: CallbackContext):
    voice = update.message.voice.get_file()
    file_path = voice.download("voice_message.ogg")  # Сохранение голосового сообщения
    try:
        # Используем OpenAI для распознавания речи (или другую библиотеку)
        with open(file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)  # Замените "whisper-1" на используемую модель
        update.message.reply_text(f"Вы сказали: {transcript['text']}")
    except Exception as e:
        update.message.reply_text("Не удалось распознать голос. Попробуйте еще раз.")
        print(f"Ошибка: {e}")

    # Добавляем обработчик голосовых сообщений
    dispatcher.add_handler(MessageHandler(Filters.voice, handle_voice))

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
    TOKEN = "TELEGRAM_TOKEN"
    PORT = 8080  # Укажите порт, на котором будет работать бот
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.bot.set_webhook(url=f"https://telegram-bot-ag71.onrender.com/webhook/{TELEGRAM_TOKEN}")

    try:
        logging.info("Бот запущен...")
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        sys.exit(1)
