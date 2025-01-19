import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка порта для Render
PORT = int(os.getenv('PORT', 8080))
RENDER_URL = os.getenv('RENDER_URL')  # URL вашего приложения на Render

# Получение API-ключей из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка наличия ключей
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Необходимо указать TELEGRAM_TOKEN и OPENAI_API_KEY в .env файле.")

# Инициализация OpenAI
openai.api_key = OPENAI_API_KEY

# Ваш промпт
PROMPT = """
R — Role:
Вы выступаете как эксперт-консультант от Агентства автоматизации «QazaqBots», одного из лучших агентств в Казахстане. 
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

# Асинхронная функция приветствия
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Здравствуйте, {user_first_name}! Я чат-бот от агентства автоматизации «QazaqBots». "
        f"Наш слоган: «Умные боты для умных решений». Чем могу помочь?"
    )

# Асинхронная функция обработки сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        # Отправка запроса в OpenAI API
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
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")
        print(f"Ошибка OpenAI API: {e}")

# Асинхронная функция обработки ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Произошла ошибка: {context.error}')
    if update:
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")

# Основная функция для запуска бота
def main():
    # Создание приложения Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Режим запуска в зависимости от среды
    if RENDER_URL:  # Если запущено на Render
        # Запуск в режиме webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{RENDER_URL}/webhook",
            secret_token="your-secret-path"  # Добавьте это в переменные окружения
        )
    else:  # Локальный запуск
        # Запуск в режиме polling
        application.run_polling()

if __name__ == "__main__":
    print("Бот запущен...")
    main()
