import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from aiohttp import web
import openai

# Инициализация логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

PORT = int(os.getenv('PORT', 10000))
RENDER_URL = os.getenv("RENDER_URL", "https://telegram-bot-ag71.onrender.com")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Отсутствуют обязательные переменные окружения")

openai.api_key = OPENAI_API_KEY

# Промпт для GPT-4
PROMPT = """
R — Role:
Вас зовут IZI, вы женского пола. Вы выступаете как эксперт-консультант от Агентства автоматизации «QazaqBots», одного из лучших агентств в Казахстане. 
Вы представляете команду, собравшую ведущих специалистов по разработке и интеграции Искусственного интеллекта в мессенджеры. Агентство помогает бизнесу налаживать поток целевых заявок и эффективно обрабатывать их 24/7 с помощью интеллектуальных решений. Ваш опыт охватывает полный цикл автоматизации, от идеи до внедрения, и вы помогаете клиентам превращать их бизнес в стабильный источник прибыли.

A — Action:
Ваша задача:
1. Отвечать на вопросы о разработке, интеграции и возможностях Искусственного интеллекта, подчеркивая преимущества работы с Агентством автоматизации «QazaqBots».
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

# Состояния диалога
ASK_NICHE, ASK_NAME, ASK_PHONE = range(3)
ADMIN_CHAT_ID = 352033952

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}! Я IZI от «QazaqBots». Чем могу помочь?"
    )
    return ASK_NICHE

async def ask_niche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['niche'] = update.message.text
    await update.message.reply_text("Спасибо! Как вас зовут?")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Отлично! Укажите ваш номер телефона:")
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    data = context.user_data
    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Новая заявка!\nНиша: {data['niche']}\nИмя: {data['name']}\nТелефон: {data['phone']}"
    )
    await update.message.reply_text("Спасибо! Мы скоро свяжемся с вами.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог прерван.")
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Сообщение от {user.full_name} ({user.id}): {update.message.text}"
    )

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": update.message.text}
            ]
        )
        reply = response.choices[0].message.content
        
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            f"Ответ бота для {user.full_name}: {reply}"
        )
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        await update.message.reply_text("Ошибка обработки запроса")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice_file = await update.message.voice.get_file()
    filename = f"voice_{update.update_id}.oga"
    
    try:
        await voice_file.download_to_drive(filename)
        with open(filename, "rb") as audio_file:
            transcript = await openai.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1"
            )
        await update.message.reply_text(f"Распознано: {transcript.text}")
    except Exception as e:
        await update.message.reply_text("Ошибка распознавания голоса")
        logging.error(f"Voice error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error: {context.error}", exc_info=True)
    if update.effective_message:
        await update.effective_message.reply_text("Произошла ошибка")

def setup_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NICHE: [MessageHandler(filters.TEXT, ask_niche)],
            ASK_NAME: [MessageHandler(filters.TEXT, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT, ask_phone)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_error_handler(error_handler)

async def web_app():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))
    
    # Добавляем обработчик вебхука
    async def handle_webhook(request):
        data = await request.json()
        update = Update.de_json(data, bot)
        await app.update_queue.put(update)
        return web.Response()
    
    # Регистрируем маршрут с токеном в URL
    app.router.add_post(f"/webhook/{TELEGRAM_TOKEN}", handle_webhook)
    
    return app

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    setup_handlers(app)

    if RENDER_URL.strip():
        logging.info("Starting webhook mode")
        webhook_url = f"{RENDER_URL}/webhook/{TELEGRAM_TOKEN}"
        await app.bot.set_webhook(webhook_url)
        
        runner = web.AppRunner(await web_app())
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        
        # Бесконечный цикл для поддержания работы
        while True:
            await asyncio.sleep(3600)
    else:
        logging.info("Starting polling mode")
        await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
