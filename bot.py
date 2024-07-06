import asyncio
from aiogram import Bot, Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
import asyncpg

TOKEN = '7386217321:AAHhpIkk9WBx9IbRkkO3uokqPuFrm8aOg7M'
DATABASE_URL = 'postgresql://postgres:postgres@db:5432/postgres'

bot = Bot(token=TOKEN)
router = Router()
storage = MemoryStorage()


class JobSearch(StatesGroup):
    choosing = State()
    searching = State()
    showing_results = State()


async def get_random_jobs(conn, limit=10):
    return await conn.fetch("SELECT title, company, salary, url FROM vacancies ORDER BY RANDOM() LIMIT $1", limit)


async def search_jobs(conn, query, offset=0, limit=10):
    query = f"%{query}%"
    return await conn.fetch("SELECT title, company, salary, url FROM vacancies WHERE title ILIKE $1 LIMIT $2 OFFSET $3",
                            query, limit, offset)


@router.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Вывести 10 случайных вакансий')],
            [KeyboardButton(text='Ввести запрос для вакансий')]
        ],
        resize_keyboard=True
    )

    await message.answer("Зздравствуйте, это бот для поиска вакансий, сделайте выбор:", reply_markup=keyboard)
    await state.set_state(JobSearch.choosing)


@router.message(JobSearch.choosing)
async def choose_option(message: types.Message, state: FSMContext):
    if message.text == 'Вывести 10 случайных вакансий':
        async with asyncpg.create_pool(DATABASE_URL) as pool:
            async with pool.acquire() as conn:
                jobs = await get_random_jobs(conn)
                for job in jobs:
                    await message.answer(
                        f"{job['title']}\nКомпания: {job['company']}\nЗарплата: {job['salary']}\nСсылка: {job['url']}")

                await state.update_data(offset=10)

                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text='Вывести ещё 10 вакансий')],
                        [KeyboardButton(text='Ввести запрос для вакансий')]
                    ],
                    resize_keyboard=True
                )
                await message.answer("Сделайте выбор:", reply_markup=keyboard)
                await state.set_state(JobSearch.showing_results)

    elif message.text == 'Ввести запрос для вакансий':
        await message.answer("Введите интересующий запрос:")
        await state.update_data(offset=0)
        await state.set_state(JobSearch.searching)
    else:
        await message.answer("Сделайте один выбор.")


@router.message(JobSearch.searching)
async def search_jobs_handler(message: types.Message, state: FSMContext):
    query = message.text
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            jobs = await search_jobs(conn, query)
            if not jobs:
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text='Сменить запрос для вакансий')],
                        [KeyboardButton(text='Вернуться в начало')]
                    ],
                    resize_keyboard=True
                )
                await message.answer("Вакансии не найдены.", reply_markup=keyboard)
                await state.set_state(JobSearch.showing_results)
                return
            for job in jobs:
                await message.answer(
                    f"{job['title']}\nКомпания: {job['company']}\nЗарплата: {job['salary']}\nСсылка: {job['url']}")
            await state.update_data(query=query, offset=10)
            await show_more_options(message, state)


async def show_more_options(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Вывести ещё 10 вакансий')],
            [KeyboardButton(text='Сменить запрос для вакансий')],
            [KeyboardButton(text='Вернуться в начало')]
        ],
        resize_keyboard=True
    )
    await message.answer("Сделайте выбор:", reply_markup=keyboard)
    await state.set_state(JobSearch.showing_results)


@router.message(JobSearch.showing_results)
async def handle_more_options(message: types.Message, state: FSMContext):
    data = await state.get_data()
    query = data.get('query', None)
    offset = data.get('offset', 0)

    if message.text == 'Вывести ещё 10 вакансий':
        async with asyncpg.create_pool(DATABASE_URL) as pool:
            async with pool.acquire() as conn:
                if query:
                    jobs = await search_jobs(conn, query, offset=offset)
                else:
                    jobs = await get_random_jobs(conn, limit=10)

                if not jobs:
                    await message.answer("Больше вакансий не найдено.")
                    await state.clear()
                    await start(message, state)
                    return

                for job in jobs:
                    await message.answer(
                        f"{job['title']}\nКомпания: {job['company']}\nЗарплата: {job['salary']}\nСсылка: {job['url']}")
                await state.update_data(offset=offset + 10)
        await show_more_options(message, state)

    elif message.text == 'Сменить запрос для вакансий':
        await message.answer("Введите новый запрос:")
        await state.update_data(query=None, offset=0)
        await state.set_state(JobSearch.searching)

    elif message.text == 'Ввести запрос для вакансий':
        await message.answer("Введите запрос:")
        await state.set_state(JobSearch.searching)

    elif message.text == 'Вернуться в начало':
        await start(message, state)

    else:
        await message.answer("Сделайте один выбор.")


async def main():
    from aiogram import Dispatcher
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
