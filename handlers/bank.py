from aiogram import Router, F, types
from datetime import datetime, timedelta

from .utils import get_or_create, fmt, now_str, parse_dt
import database as db

router = Router()

DEPOSIT_RATE = 0.03  # 3% в день


@router.message(F.text.lower().startswith("банк положить "))
async def cmd_bank_deposit(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Банк положить [сумма]")
        return
    if amount <= 0 or p["balance"] < amount:
        await message.answer("❌ Недостаточно денег!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - amount, bank=p["bank"] + amount)
    await message.answer(f"🏦 Положено: <b>{fmt(amount)}$</b>", parse_mode="HTML")


@router.message(F.text.lower().startswith("банк снять "))
async def cmd_bank_withdraw(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Банк снять [сумма]")
        return
    if amount <= 0 or p["bank"] < amount:
        await message.answer("❌ Недостаточно в банке!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] + amount, bank=p["bank"] - amount)
    await message.answer(f"🏦 Снято: <b>{fmt(amount)}$</b>", parse_mode="HTML")


@router.message(F.text.lower() == "депозит")
async def cmd_deposit_info(message: types.Message):
    p = await get_or_create(message.from_user.id)
    dep_date = parse_dt(p["deposit_date"])
    days_passed = (datetime.now() - dep_date).days if dep_date else 0
    earned = p["deposit_initial"] * DEPOSIT_RATE * days_passed if p["deposit_initial"] else 0
    total = p["deposit"] + earned
    can = "✅ Можно снять" if dep_date and datetime.now() - dep_date >= timedelta(days=7) else "❌ Нельзя снять (нужно 7 дней)"
    await message.answer(
        f"💼 <b>Депозит</b>\n\nВнесено: {fmt(p['deposit_initial'])}$\nНакоплено: {fmt(total)}$\n"
        f"Дней: {days_passed}\nПроцент: {int(DEPOSIT_RATE*100)}%/день\n{can}",
        parse_mode="HTML"
    )


@router.message(F.text.lower().startswith("депозит положить "))
async def cmd_deposit_put(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Депозит положить [сумма]")
        return
    if amount <= 0 or p["balance"] < amount:
        await message.answer("❌ Недостаточно денег!")
        return
    commission = amount * 0.015
    net = amount - commission
    await db.update_player(
        message.from_user.id,
        balance=p["balance"] - amount,
        deposit=p["deposit"] + net,
        deposit_initial=p["deposit_initial"] + net,
        deposit_date=now_str()
    )
    await message.answer(f"💼 Внесено: <b>{fmt(net)}$</b> (комиссия {fmt(commission)}$)", parse_mode="HTML")


@router.message(F.text.lower() == "депозит снять")
async def cmd_deposit_withdraw(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["deposit_date"]:
        await message.answer("❌ Нет депозита!")
        return
    dep_date = parse_dt(p["deposit_date"])
    if datetime.now() - dep_date < timedelta(days=7):
        left = timedelta(days=7) - (datetime.now() - dep_date)
        await message.answer(f"❌ Осталось: {left.days}д {left.seconds//3600}ч")
        return
    days_passed = (datetime.now() - dep_date).days
    total = p["deposit"] + p["deposit_initial"] * DEPOSIT_RATE * days_passed
    net = total * 0.98
    await db.update_player(
        message.from_user.id,
        balance=p["balance"] + net,
        deposit=0,
        deposit_initial=0,
        deposit_date=None
    )
    await message.answer(f"💼 Снято: <b>{fmt(net)}$</b>", parse_mode="HTML")
