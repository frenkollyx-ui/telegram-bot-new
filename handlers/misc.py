import random
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from .utils import get_or_create, fmt, now_str, parse_dt
import database as db

router = Router()

safe_sessions = {}


@router.message(F.text.lower() == "дуэль", F.reply_to_message)
async def cmd_duel(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_duel"])
    if last and datetime.now() - last < timedelta(minutes=30):
        left = timedelta(minutes=30) - (datetime.now() - last)
        await message.answer(f"⏳ КД: {int(left.seconds/60)}м")
        return
    ci = await db.get_inventory_item(p["id"], "coins", "монетки")
    if not ci or ci["quantity"] < 3:
        await message.answer("❌ Нужно 3 монетки!")
        return
    target = await get_or_create(message.reply_to_message.from_user.id)
    if target["tg_id"] == message.from_user.id:
        await message.answer("❌ Нельзя вызвать себя!")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"duel_accept_{message.from_user.id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data="duel_decline")
    ]])
    await message.answer(
        f"⚔️ <b>{p['username']}</b> вызывает <b>{target['username']}</b>! (3 монетки)",
        parse_mode="HTML", reply_markup=kb
    )


@router.callback_query(F.data.startswith("duel_accept_"))
async def duel_accept(callback: types.CallbackQuery):
    challenger_tg = int(callback.data.split("_")[-1])
    challenger = await get_or_create(challenger_tg)
    target = await get_or_create(callback.from_user.id)
    await db.remove_inventory_item(challenger["id"], "coins", "монетки", 3)
    await db.remove_inventory_item(target["id"], "coins", "монетки", 3)
    ct = random.randint(1, 100)
    tt = random.randint(1, 100)
    if ct == tt:
        await callback.message.edit_text(f"⚔️ Ничья! {ct}м vs {tt}м")
        await callback.answer()
        return
    winner = challenger if ct > tt else target
    loser = target if ct > tt else challenger
    winner_tg = challenger_tg if ct > tt else callback.from_user.id
    loser_tg = callback.from_user.id if ct > tt else challenger_tg
    prize = random.randint(1, 1000)
    await db.update_player(winner_tg, balance=winner["balance"] + prize)
    await db.update_player(loser_tg, balance=max(0, loser["balance"] - prize))
    await db.update_player(challenger_tg, last_duel=now_str())
    await db.update_player(callback.from_user.id, last_duel=now_str())
    await callback.message.edit_text(
        f"⚔️ {challenger['username']}: {ct}м | {target['username']}: {tt}м\n🏆 <b>{winner['username']}</b> +{fmt(prize)}$",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "duel_decline")
async def duel_decline(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Дуэль отклонена!")
    await callback.answer()


@router.message(F.text.lower() == "взломать сейф")
async def cmd_safe(message: types.Message):
    tg_id = message.from_user.id
    p = await get_or_create(tg_id)
    sess = safe_sessions.get(tg_id)
    if sess and sess.get("attempts", 0) >= 3:
        last = parse_dt(p["last_safe"])
        if last and datetime.now() - last < timedelta(hours=24):
            left = timedelta(hours=24) - (datetime.now() - last)
            await message.answer(f"⏳ Через {int(left.total_seconds()//3600)}ч")
            return
    code = str(random.randint(1000, 9999))
    safe_sessions[tg_id] = {"code": code, "attempts": 0, "started": datetime.now()}
    await db.update_player(tg_id, last_safe=now_str())
    await message.answer("🔐 Угадай 4-значный код! 3 попытки, 5 минут:")


@router.message(F.text)
async def universal_safe_handler(message: types.Message):
    """Handles safe code guessing."""
    tg_id = message.from_user.id
    text = message.text.strip()
    if tg_id not in safe_sessions or not text.isdigit() or len(text) != 4:
        return
    p = await get_or_create(tg_id)
    session = safe_sessions[tg_id]
    if datetime.now() - session["started"] > timedelta(minutes=5):
        safe_sessions.pop(tg_id)
        await message.answer("⏰ Время вышло!")
        return
    session["attempts"] += 1
    if text == session["code"]:
        safe_sessions.pop(tg_id)
        roll = random.random()
        if roll < 0.01:
            await db.add_inventory_item(p["id"], "case", "3", 1)
            reward = "🎁 Эпический кейс!"
        elif roll < 0.10:
            await db.add_inventory_item(p["id"], "case", "2", 1)
            reward = "🎁 Редкий кейс!"
        elif roll < 0.30:
            await db.add_inventory_item(p["id"], "case", "1", 1)
            reward = "🎁 Обычный кейс!"
        else:
            amount = random.randint(500, 10000)
            await db.update_player(tg_id, balance=p["balance"] + amount)
            reward = f"💰 {fmt(amount)}$"
        await message.answer(f"🔓 Взломан! {reward}", parse_mode="HTML")
    elif session["attempts"] >= 3:
        safe_sessions.pop(tg_id)
        await message.answer(f"❌ Попытки исчерпаны! Код: <b>{session['code']}</b>", parse_mode="HTML")
    else:
        await message.answer(f"❌ Неверно! Осталось: {3 - session['attempts']}")
