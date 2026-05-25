import asyncio
import json
import logging
import sys
from os import getenv

from aiogram.utils.keyboard import InlineKeyboardBuilder
from groq import Groq

from aiogram import Bot, Dispatcher, html, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery

from dotenv import load_dotenv

from image_handling import get_ai_image_description
from export_utils import callbacks_router
from middleware import AlbumMiddleware

load_dotenv()
GROQ_API_KEY = getenv('GROQ_API_KEY')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = ""

text_buffer: dict[int, list] = {}
busy_tasks: dict[int, int] = {}

dp = Dispatcher()
router = Router()

groq_client = Groq(api_key=GROQ_API_KEY)

lang = {}


async def export_menu(message: Message):
    if busy_tasks.get(message.chat.id, 0) > 0:
        await message.answer(lang['busy_export_denied'])
        return

    if len(text_buffer.setdefault(message.chat.id, [])) == 0:
        await message.answer(lang['no_text_to_export'])
        return

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=lang['export_zip'], callback_data='export_as_zip'))
    builder.add(InlineKeyboardButton(text=lang['export_json'], callback_data='export_as_json'))

    await message.answer(lang['choose_export_format'], reply_markup=builder.as_markup())



@router.message(Command('export'))
async def export_cmd(message: Message):
    await export_menu(message)


@router.callback_query(F.data == 'open_export_menu')
async def callback_open_export_menu(callback: CallbackQuery):
    await export_menu(callback.message)
    await callback.answer()


def make_progress_bar(current: int, total: int) -> str:
    percent = int((current / total) * 100)
    bar_length = 10
    filled_length = int(bar_length * current // total)
    bar = '▓' * filled_length + '░' * (bar_length - filled_length)
    return f"{lang['processing']}\n\n{bar} {percent}% ({current}/{total})"


@router.message(F.photo)
async def handle_image(message: Message, bot: Bot, album: list[Message]):
    chat_id = message.chat.id

    busy_tasks[chat_id] = busy_tasks.get(chat_id, 0) + 1

    total_photos = len(album)
    current_photo = 0

    progress_message = await message.answer(make_progress_bar(current_photo, total_photos))

    for msg in album:
        await bot.send_chat_action(chat_id=chat_id, action="typing")

        largest_photo = msg.photo[-1]
        file_info = await bot.get_file(largest_photo.file_id)
        file_bytes = await bot.download_file(file_info.file_path)

        answer = get_ai_image_description(groq_client, file_bytes, SYSTEM_PROMPT)
        text_buffer.setdefault(chat_id, []).append(answer)

        current_photo += 1
        if current_photo < total_photos:
            try:
                await progress_message.edit_text(make_progress_bar(current_photo, total_photos))
            except Exception:
                pass

    busy_tasks[chat_id] = max(0, busy_tasks.get(chat_id, 0) - 1)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=lang['export'], callback_data='open_export_menu'))

    await progress_message.edit_text(
        text=lang['images_processed'].format(total_photos),
        reply_markup=builder.as_markup()
    )


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer(str(lang['greeting']).format(html.bold(message.from_user.full_name)))


async def main():
    dp.message.middleware(AlbumMiddleware())
    bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp.include_router(router)
    dp.include_router(callbacks_router)

    with open('system_prompt.txt', 'r', encoding='utf-8') as file:
        global SYSTEM_PROMPT
        SYSTEM_PROMPT = file.read()

    with open('lang.json', 'r', encoding='utf-8') as file:
        global lang
        lang = json.load(file)

    await dp.start_polling(bot, lang=lang, text_buffer=text_buffer)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
