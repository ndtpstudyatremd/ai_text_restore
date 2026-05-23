import os
import json
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

callbacks_router = Router()


@callbacks_router.callback_query(F.data == 'export_as_json')
async def callback_export_as_json(callback: CallbackQuery, text_buffer: dict, lang: dict):
    if len(text_buffer) == 0:
        await callback.message.answer(lang['no_text_to_export'])
        await callback.answer()
        return

    file_name = f'texts_{callback.message.chat.id}.json'

    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(text_buffer.setdefault(callback.message.chat.id, []), file, ensure_ascii=False, indent=4)

    document = FSInputFile(file_name)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=lang['unpack_json'],
        callback_data='unpack_json_file'
    ))

    await callback.message.answer_document(
        document,
        caption=lang['exported_json'],
        reply_markup=builder.as_markup()
    )

    text_buffer.clear()

    if os.path.exists(file_name):
        os.remove(file_name)
    await callback.answer()


@callbacks_router.callback_query(F.data == 'export_as_zip')
async def callback_export_as_zip(callback: CallbackQuery, text_buffer: dict, lang: dict):
    if len(text_buffer) == 0:
        await callback.message.answer(lang['no_text_to_export'])
        await callback.answer()
        return

    with tempfile.TemporaryDirectory() as tempdir:
        export_as_zip(text_buffer[callback.message.chat.id], tempdir)

        text_buffer[callback.message.chat.id].clear()

        document = FSInputFile(os.path.join(tempdir, 'result.zip'))

        await callback.message.answer_document(
            document,
            caption=lang['exported_zip']
        )

        await callback.answer()


@callbacks_router.callback_query(F.data == 'unpack_json_file')
async def callback_unpack_json(callback: CallbackQuery, bot: Bot, lang: dict):
    document = callback.message.document
    if not document:
        await callback.answer(lang['error_file_not_found'], show_alert=True)
        return

    file_info = await bot.get_file(document.file_id)
    file_bytes = await bot.download_file(file_info.file_path)

    try:
        json_data = file_bytes.read().decode('utf-8')
        texts_list = json.loads(json_data)

        if not isinstance(texts_list, list) or len(texts_list) == 0:
            await callback.answer(lang['error_bad_file'], show_alert=True)
            return

        flat_text = "\n\n".join(texts_list)
        if len(flat_text) > 4000:
            flat_text = flat_text[:4000] + lang['text_is_too_long_suffix']

        caption_text = lang['json_unpacked'].format(flat_text)
        await callback.message.answer(text=caption_text)
        await callback.answer()
    except Exception:
        await callback.answer(lang['error_parsing_file'], show_alert=True)


def export_as_zip(texts: list[str], work_dir: str):
    file_paths = []
    file_id = 1

    for text in texts:
        path = os.path.join(work_dir, f'text{file_id}.txt')

        with open(path, 'w', encoding='utf-8') as file:
            file.write(text)

        file_paths.append(path)
        file_id += 1

    zip_path = os.path.join(work_dir, 'result.zip')

    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:

        for path in file_paths:
            zipf.write(path, arcname=os.path.basename(path))
