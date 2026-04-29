import random
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from .utils import get_or_create, parse_dt
import database as db

router = Router()

pending_child_name = {}

RP_ACTIONS = {
    "обнять": "обнял(а)", "поцеловать": "поцеловал(а)", "кусь": "укусил(а)",
    "бросить с обрыва": "бросил(а) с обрыва", "толкнуть": "толкнул(а)",
    "прижать": "прижал(а)", "покормить": "покормил(а)", "съесть": "съел(а)",
    "убить": "убил(а)", "зарезать": "зарезал(а)", "кинуть снежок": "кинул(а) снежок в",
}


@router.message(F.text.lower().in_({"мужской", "женский"}))
async def cmd_set_gender(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if p["gender"]:
        await message.answer(f"❌ Пол уже указан: {p['gender']}")
        return
    await db.update_player(message.from_user.id, gender=message.text.lower())
    await message.answer(f"✅ Пол: <b>{message.text.lower()}</b>", parse_mode="HTML")


@router.message(F.text.lower().startswith("брак ") & ~F.text.lower().startswith("брак кекс"))
async def cmd_marry(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["gender"]:
        await message.answer("❌ Сначала укажи пол! (мужской / женский)")
        return
    if await db.get_marriage(p["id"]):
        await message.answer("❌ Ты уже в браке!")
        return
    try:
        target = await db.get_player_by_game_id(int(message.text.split()[1]))
    except:
        await message.answer("❌ Брак [ID]")
        return
    if not target or not target["gender"] or target["gender"] == p["gender"]:
        await message.answer("❌ Нельзя вступить в брак с этим игроком!")
        return
    if await db.get_marriage(target["id"]):
        await message.answer("❌ Этот игрок уже в браке!")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept_{p['id']}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data="marry_decline")
    ]])
    try:
        await message.bot.send_message(target["tg_id"], f"💍 <b>{p['username']}</b> предлагает брак!", parse_mode="HTML", reply_markup=kb)
        await message.answer("✅ Предложение отправлено!")
    except:
        await message.answer("❌ Не удалось отправить!")


@router.callback_query(F.data.startswith("marry_accept_"))
async def marry_accept(callback: types.CallbackQuery):
    target = await get_or_create(callback.from_user.id)
    from_id = int(callback.data.split("_")[-1])
    proposer = await db.get_player_by_game_id(from_id)
    if not proposer:
        await callback.answer("Ошибка!")
        return
    h = from_id if proposer["gender"] == "мужской" else target["id"]
    w = target["id"] if proposer["gender"] == "мужской" else from_id
    await db.create_marriage(h, w)
    await callback.message.edit_text(
        f"💍 <b>{proposer['username']}</b> и <b>{target['username']}</b> теперь в браке!", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "marry_decline")
async def marry_decline(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Предложение отклонено.")
    await callback.answer()


@router.message(F.text.lower() == "мой брак")
async def cmd_my_marriage(message: types.Message):
    p = await get_or_create(message.from_user.id)
    marriage = await db.get_marriage(p["id"])
    if not marriage:
        await message.answer("❌ Ты не в браке!")
        return
    sid = marriage["wife_id"] if marriage["husband_id"] == p["id"] else marriage["husband_id"]
    sp = await db.get_player_by_game_id(sid)
    children = await db.get_children(marriage["id"])
    days = (datetime.now() - parse_dt(marriage["created_at"])).days if marriage["created_at"] else 0
    status = "💑 Молодожёны" if days < 7 else ("❤️ Близкие люди" if days < 30 else "💞 Неразлучимые")
    kids = ", ".join(f"{c['name']} ({c['gender']})" for c in children) or "—"
    await message.answer(f"💍 Супруг(а): <b>{sp['username']}</b>\n📅 {days} дней | {status}\n👶 {kids}", parse_mode="HTML")


@router.message(F.text.lower() == "брак кекс")
async def cmd_keks(message: types.Message):
    p = await get_or_create(message.from_user.id)
    marriage = await db.get_marriage(p["id"])
    if not marriage or marriage["children"] >= 4:
        await message.answer("❌ Нет брака или достигнут лимит детей (4)!")
        return
    sid = marriage["wife_id"] if marriage["husband_id"] == p["id"] else marriage["husband_id"]
    sp = await db.get_player_by_game_id(sid)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_data=f"keks_accept_{marriage['id']}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="keks_decline")
    ]])
    try:
        await message.bot.send_message(sp["tg_id"], f"💕 <b>{p['username']}</b> хочет ребёнка!", parse_mode="HTML", reply_markup=kb)
        await message.answer("✅ Запрос отправлен!")
    except:
        await message.answer("❌ Не удалось отправить!")


@router.callback_query(F.data.startswith("keks_accept_"))
async def keks_accept(callback: types.CallbackQuery):
    marriage_id = int(callback.data.split("_")[-1])
    if random.random() < 0.5:
        gender = random.choice(["мальчик", "девочка"])
        pending_child_name[callback.from_user.id] = {"marriage_id": marriage_id, "gender": gender}
        await callback.message.edit_text(f"🍼 Родился(ась) <b>{gender}</b>!\nВведи имя (3–10 букв):", parse_mode="HTML")
    else:
        await callback.message.edit_text("😢 Не получилось...")
    await callback.answer()


@router.callback_query(F.data == "keks_decline")
async def keks_decline(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Отказано.")
    await callback.answer()


@router.message(F.text.lower().in_(set(RP_ACTIONS.keys())), F.reply_to_message)
async def cmd_rp(message: types.Message):
    p = await get_or_create(message.from_user.id)
    target_name = message.reply_to_message.from_user.first_name
    await message.answer(f"🎭 <b>{p['username']}</b> {RP_ACTIONS[message.text.lower()]} <b>{target_name}</b>!", parse_mode="HTML")
