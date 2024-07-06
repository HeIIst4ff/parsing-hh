import logging
import random
import psycopg2
from config import TELEGRAM_BOT_TOKEN, DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext, \
    ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def connect_db():
    return psycopg2.connect(
        host=DB_bd,
        dbname=DB_postgres,
        user=DB_postgres,
        password=DB_postgres,
        port=DB_5432
    )


CHOOSING, SEARCHING = range(2)


async def start(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Все", callback_data='all')],
        [InlineKeyboardButton("Конкретные", callback_data='search')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)
    return CHOOSING


async def button(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'all':
        await show_random_vacancies(update, context)
        return CHOOSING
    elif query.data == 'search':
        await query.message.reply_text("Введите название интересующей вакансии:")
        return SEARCHING
    elif query.data == 'more_all':
        await show_random_vacancies(update, context)
        return CHOOSING
    elif query.data.startswith('more_search'):
        keyword = context.user_data.get('keyword', '')
        await show_search_vacancies(update, context, keyword)
        return CHOOSING
    elif query.data == 'change_search':
        await query.message.reply_text("Введите новое название интересующей вакансии:")
        return SEARCHING


async def show_random_vacancies(update: Update, context: CallbackContext):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, salary, company, url FROM vacancies ORDER BY RANDOM() LIMIT 20")
    vacancies = cursor.fetchall()
    conn.close()

    if not vacancies:
        await update.callback_query.message.reply_text("Нет доступных вакансий.")
        return

    message = "\n\n".join([f"{vacancy[0]} - {vacancy[1]}, {vacancy[2]}: {vacancy[3]}" for vacancy in vacancies])
    await update.callback_query.message.reply_text(message)

    keyboard = [
        [InlineKeyboardButton("Загрузить ещё", callback_data='more_all')],
        [InlineKeyboardButton("Конкретные", callback_data='search')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("Что хотите сделать дальше?", reply_markup=reply_markup)


async def search_vacancy(update: Update, context: CallbackContext) -> int:
    keyword = update.message.text
    context.user_data['keyword'] = keyword
    await show_search_vacancies(update, context, keyword)
    return CHOOSING


async def show_search_vacancies(update: Update, context: CallbackContext, keyword: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, salary, company, url FROM vacancies WHERE title ILIKE %s ORDER BY RANDOM() LIMIT 20",
                   (f'%{keyword}%',))
    vacancies = cursor.fetchall()
    conn.close()

    if not vacancies:
        await update.callback_query.message.reply_text(f"По запросу '{keyword}' ничего не найдено.")
        return

    message = "\n\n".join([f"{vacancy[0]} - {vacancy[1]}, {vacancy[2]}: {vacancy[3]}" for vacancy in vacancies])
    await update.callback_query.message.reply_text(message)

    keyboard = [
        [InlineKeyboardButton("Загрузить ещё", callback_data='more_search')],
        [InlineKeyboardButton("Поменять название", callback_data='change_search')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("Что хотите сделать дальше?", reply_markup=reply_markup)


async def error(update: Update, context: CallbackContext):
    logger.warning(f"Update {update} caused error {context.error}")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(button)
            ],
            SEARCHING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_vacancy)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error)

    application.run_polling()


if __name__ == '__main__':
    main()
