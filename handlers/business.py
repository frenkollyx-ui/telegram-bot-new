from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .utils import get_or_create, fmt, now_str, parse_dt
import database as db

router = Router()

BUSINESS_INCOME_PER_LEVEL = 500
FARM_INCOME_PER_LEVEL = 0.0001
BUSINESS_UPGRADE_COST = 25000
FARM_UPGRADE_COST = 50000


@router.message(F.text.lower() == "построить бизнес")
async def cmd_build_business(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if p["balance"] < 50000 or await db.get_business(p["id"]):
        await message.answer("❌ Нужно 50.000$ и отсутствие бизнеса!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - 50000)
    await db.create_business(p["id"])
    await message.answer("🏢 Бизнес построен! 500$/час")


@router.message(F.text.lower() == "мой бизнес")
async def cmd_my_business(message: types.Message):
    p = await get_or_create(message.from_user.id)
    biz = await db.get_business(p["id"])
    if not biz:
        await message.answer("❌ Нет бизнеса!")
        return
    last = parse_dt(biz["last_collect"])
    hours = ((__import__('datetime').datetime.now()) - last).total_seconds() / 3600 if last else 0
    iph = BUSINESS_INCOME_PER_LEVEL * biz["level"]
    pending = iph * hours
    uc = BUSINESS_UPGRADE_COST * biz["level"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Забрать {fmt(pending)}$", callback_data="biz_collect"),
         InlineKeyboardButton(text=f"⬆️ Улучшить {fmt(uc)}$", callback_data="biz_upgrade")],
        [InlineKeyboardButton(text=f"💸 Налог {fmt(biz['taxes'])}$", callback_data="biz_tax")]
    ])
    await message.answer(
        f"🏢 Ур.{biz['level']} | {fmt(iph)}$/ч | Накоп: {fmt(pending)}$ | Налог: {fmt(biz['taxes'])}$",
        reply_markup=kb
    )


@router.callback_query(F.data.in_({"biz_collect", "biz_upgrade", "biz_tax"}))
async def biz_callback(callback: types.CallbackQuery):
    from datetime import datetime
    p = await get_or_create(callback.from_user.id)
    biz = await db.get_business(p["id"])
    if not biz:
        await callback.answer("Нет бизнеса!")
        return
    if callback.data == "biz_collect":
        last = parse_dt(biz["last_collect"])
        hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
        income = BUSINESS_INCOME_PER_LEVEL * biz["level"] * hours
        new_taxes = biz["taxes"] + income * 0.1
        if new_taxes >= 10000:
            await callback.answer("❌ Сначала оплати налоги!")
            return
        await db.update_player(callback.from_user.id, balance=p["balance"] + income)
        await db.update_business(p["id"], last_collect=now_str(), taxes=new_taxes)
        await callback.message.edit_text(f"✅ +{fmt(income)}$")
    elif callback.data == "biz_upgrade":
        cost = BUSINESS_UPGRADE_COST * biz["level"]
        if p["balance"] < cost:
            await callback.answer(f"❌ Нужно {fmt(cost)}$")
            return
        await db.update_player(callback.from_user.id, balance=p["balance"] - cost)
        await db.update_business(p["id"], level=biz["level"] + 1)
        await callback.message.edit_text(f"⬆️ Уровень {biz['level']+1}!")
    elif callback.data == "biz_tax":
        if p["balance"] < biz["taxes"]:
            await callback.answer("❌ Недостаточно денег!")
            return
        await db.update_player(callback.from_user.id, balance=p["balance"] - biz["taxes"])
        await db.update_business(p["id"], taxes=0)
        await callback.message.edit_text("✅ Налоги оплачены!")
    await callback.answer()


@router.message(F.text.lower() == "построить ферму")
async def cmd_build_farm(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if p["balance"] < 100000 or await db.get_farm(p["id"]):
        await message.answer("❌ Нужно 100.000$ и отсутствие фермы!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - 100000)
    await db.create_farm(p["id"])
    await message.answer("⛏️ BTC ферма построена! 0.0001 BTC/час")


@router.message(F.text.lower() == "моя ферма")
async def cmd_my_farm(message: types.Message):
    p = await get_or_create(message.from_user.id)
    farm = await db.get_farm(p["id"])
    if not farm:
        await message.answer("❌ Нет фермы!")
        return
    last = parse_dt(farm["last_collect"])
    from datetime import datetime
    hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
    iph = FARM_INCOME_PER_LEVEL * farm["level"]
    pending = iph * hours
    uc = FARM_UPGRADE_COST * farm["level"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"₿ Забрать {pending:.6f}", callback_data="farm_collect"),
         InlineKeyboardButton(text=f"⬆️ Улучшить {fmt(uc)}$", callback_data="farm_upgrade")],
        [InlineKeyboardButton(text=f"💸 Налог {farm['taxes']:.4f} BTC", callback_data="farm_tax")]
    ])
    await message.answer(
        f"⛏️ Ур.{farm['level']} | {iph:.6f} BTC/ч | Накоп: {pending:.6f} | Налог: {farm['taxes']:.6f}",
        reply_markup=kb
    )


@router.callback_query(F.data.in_({"farm_collect", "farm_upgrade", "farm_tax"}))
async def farm_callback(callback: types.CallbackQuery):
    from datetime import datetime
    p = await get_or_create(callback.from_user.id)
    farm = await db.get_farm(p["id"])
    if not farm:
        await callback.answer("Нет фермы!")
        return
    if callback.data == "farm_collect":
        last = parse_dt(farm["last_collect"])
        hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
        income = FARM_INCOME_PER_LEVEL * farm["level"] * hours
        new_taxes = farm["taxes"] + income * 0.1
        if new_taxes >= 10:
            await callback.answer("❌ Сначала оплати налоги!")
            return
        await db.update_player(callback.from_user.id, btc=p["btc"] + income)
        await db.update_farm(p["id"], last_collect=now_str(), taxes=new_taxes)
        await callback.message.edit_text(f"✅ +{income:.6f} BTC")
    elif callback.data == "farm_upgrade":
        cost = FARM_UPGRADE_COST * farm["level"]
        if p["balance"] < cost:
            await callback.answer(f"❌ Нужно {fmt(cost)}$")
            return
        await db.update_player(callback.from_user.id, balance=p["balance"] - cost)
        await db.update_farm(p["id"], level=farm["level"] + 1)
        await callback.message.edit_text(f"⬆️ Уровень {farm['level']+1}!")
    elif callback.data == "farm_tax":
        if p["btc"] < farm["taxes"]:
            await callback.answer("❌ Недостаточно BTC!")
            return
        await db.update_player(callback.from_user.id, btc=p["btc"] - farm["taxes"])
        await db.update_farm(p["id"], taxes=0)
        await callback.message.edit_text("✅ Налоги оплачены!")
    await callback.answer()
