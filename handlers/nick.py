from aiogram import Router, F, types
from .profile import pending_nick
import database as db

router = Router()

@router.message(F.text)
async def universal_nick_handler(message: types.Message):
    tg_id = message.from_user.id
    if tg_id not in pending_nick:
        return
    text = message.text.strip()
    if len(text) < 5 or len(text) > 25:
        await message.answer("❌ От 5 до 25 символов!")
        return
    pending_nick.pop(tg_id)
    await db.update_player(tg_id, username=text)
    await message.answer(f"✅ Ник: <b>{text}</b>", parse_mode="HTML")
