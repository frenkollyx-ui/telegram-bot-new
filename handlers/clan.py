from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .utils import get_or_create, fmt
import database as db

router = Router()


@router.message(F.text.lower().startswith("создать клан "))
async def cmd_create_clan(message: types.Message):
    p = await get_or_create(message.from_user.id)
    name = message.text[13:].strip()
    if not name or p["clan_id"]:
        await message.answer("❌ Ты уже в клане или не указал название!")
        return
    if p["balance"] < 50000:
        await message.answer("❌ Нужно 50.000$!")
        return
    if await db.get_clan_by_name(name):
        await message.answer("❌ Такой клан уже есть!")
        return
    clan = await db.create_clan(name, p["id"])
    await db.update_player(message.from_user.id, balance=p["balance"] - 50000, clan_id=clan["id"])
    await db.add_clan_member(clan["id"], p["id"])
    await message.answer(f"🏰 Клан <b>{name}</b> создан!", parse_mode="HTML")


@router.message(F.text.lower().startswith("казна клана "))
async def cmd_clan_treasury(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Казна клана [сумма]")
        return
    if p["balance"] < amount:
        await message.answer("❌ Недостаточно денег!")
        return
    clan = await db.get_clan(p["clan_id"])
    new_treasury = clan["treasury"] + amount
    await db.update_clan(p["clan_id"], treasury=new_treasury, rating=int(new_treasury / 10000))
    await db.update_player(message.from_user.id, balance=p["balance"] - amount)
    await message.answer(f"🏦 +{fmt(amount)}$ в казну | ⭐{int(new_treasury/10000)}")


@router.message(F.text.lower().startswith("клан пригласить "))
async def cmd_clan_invite(message: types.Message, bot=None):
    from aiogram import Bot
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    clan = await db.get_clan(p["clan_id"])
    if clan["owner_id"] != p["id"]:
        await message.answer("❌ Только глава клана!")
        return
    try:
        target = await db.get_player_by_game_id(int(message.text.split()[-1]))
    except:
        await message.answer("❌ Клан пригласить [ID]")
        return
    if not target or target["clan_id"]:
        await message.answer("❌ Игрок не найден или уже в клане!")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"clan_accept_{p['clan_id']}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data="clan_decline")
    ]])
    try:
        await message.bot.send_message(target["tg_id"], f"📨 Приглашение в клан <b>{clan['name']}</b>!", parse_mode="HTML", reply_markup=kb)
        await message.answer("✅ Приглашение отправлено!")
    except:
        await message.answer("❌ Не удалось отправить!")


@router.callback_query(F.data.startswith("clan_accept_"))
async def clan_accept(callback: types.CallbackQuery):
    p = await get_or_create(callback.from_user.id)
    clan_id = int(callback.data.split("_")[-1])
    await db.update_player(callback.from_user.id, clan_id=clan_id)
    await db.add_clan_member(clan_id, p["id"])
    clan = await db.get_clan(clan_id)
    await callback.message.edit_text(f"✅ Вступил в клан <b>{clan['name']}</b>!", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "clan_decline")
async def clan_decline(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Отказался от приглашения.")
    await callback.answer()


@router.message(F.text.lower().startswith("клан передать "))
async def cmd_clan_transfer(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    clan = await db.get_clan(p["clan_id"])
    if clan["owner_id"] != p["id"]:
        await message.answer("❌ Только глава клана!")
        return
    try:
        target = await db.get_player_by_game_id(int(message.text.split()[-1]))
    except:
        await message.answer("❌ Клан передать [ID]")
        return
    if not target or target["clan_id"] != p["clan_id"]:
        await message.answer("❌ Игрок не в твоём клане!")
        return
    await db.update_clan(p["clan_id"], owner_id=target["id"])
    await message.answer(f"✅ Клан передан <b>{target['username']}</b>", parse_mode="HTML")


@router.message(F.text.lower() == "клан топ")
async def cmd_clan_top(message: types.Message):
    p = await get_or_create(message.from_user.id)
    clans = await db.get_top_clans(10)
    text = "🏆 <b>Топ 10 кланов</b>\n\n" + "\n".join(
        f"{i}. <b>{c['name']}</b> ⭐{c['rating']} 💰{fmt(c['treasury'])}$" for i, c in enumerate(clans, 1))
    if p["clan_id"]:
        clan = await db.get_clan(p["clan_id"])
        if clan:
            text += f"\n\n📍 Твой: <b>{clan['name']}</b> ⭐{clan['rating']}"
    await message.answer(text, parse_mode="HTML")
