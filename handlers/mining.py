import random
from aiogram import Router, F, types
from datetime import datetime, timedelta

from .utils import get_or_create, fmt, now_str, parse_dt
from config import ORES
import database as db

router = Router()


@router.message(F.text.lower().startswith("копать "))
async def cmd_mine(message: types.Message):
    p = await get_or_create(message.from_user.id)
    ore_name = message.text[7:].strip().lower()
    if ore_name not in ORES:
        await message.answer("❌ Руды: " + ", ".join(ORES.keys()))
        return
    ore = ORES[ore_name]
    if p["exp"] < ore["min_exp"]:
        await message.answer(f"❌ Нужно {ore['min_exp']} опыта! У тебя: {p['exp']}")
        return
    if p["energy"] <= 0:
        await message.answer("❌ Нет энергии! +1 каждые 5 минут.")
        return
    amount = random.randint(ore["min"], ore["max"])
    await db.add_inventory_item(p["id"], "ore", ore_name, amount)
    await db.update_player(message.from_user.id, energy=p["energy"] - 1, exp=p["exp"] + 10)
    await message.answer(f"⛏️ +<b>{amount} {ore_name}</b> | ⚡{p['energy']-1}/100 | ⭐{p['exp']+10}", parse_mode="HTML")


@router.message(F.text.lower().startswith("продать "))
async def cmd_sell_ore(message: types.Message):
    p = await get_or_create(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Продать [руда] [кол-во]")
        return
    ore_name = " ".join(parts[1:-1]).lower()
    try:
        qty = int(parts[-1])
    except:
        await message.answer("❌ Укажи кол-во числом")
        return
    if ore_name not in ORES:
        await message.answer("❌ Такой руды нет!")
        return
    item = await db.get_inventory_item(p["id"], "ore", ore_name)
    if not item or item["quantity"] < qty:
        await message.answer(f"❌ Недостаточно {ore_name}!")
        return
    total = qty * ORES[ore_name]["price"]
    await db.remove_inventory_item(p["id"], "ore", ore_name, qty)
    await db.update_player(message.from_user.id, balance=p["balance"] + total)
    await message.answer(f"💰 Продано {qty} {ore_name} за <b>{fmt(total)}$</b>", parse_mode="HTML")


@router.message(F.text.lower() == "найти монетки")
async def cmd_find_coins(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_coins"])
    if last and datetime.now() - last < timedelta(minutes=5):
        left = timedelta(minutes=5) - (datetime.now() - last)
        await message.answer(f"⏳ Подожди {int(left.seconds/60)}м {left.seconds%60}с")
        return
    amount = random.randint(1, 5)
    await db.add_inventory_item(p["id"], "coins", "монетки", amount)
    await db.update_player(message.from_user.id, last_coins=now_str())
    await message.answer(f"🪙 Нашёл <b>{amount}</b> монеток!", parse_mode="HTML")


@router.message(F.text.lower() == "ежедневный бонус")
async def cmd_daily(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["daily_bonus_date"])
    if last and datetime.now() - last < timedelta(hours=24):
        left = timedelta(hours=24) - (datetime.now() - last)
        h = int(left.total_seconds() // 3600)
        m = int((left.total_seconds() % 3600) // 60)
        await message.answer(f"⏳ Через {h}ч {m}м")
        return
    await db.update_player(message.from_user.id, daily_bonus_date=now_str())
    if random.random() < 0.5:
        amount = random.randint(1000, 10000)
        await db.update_player(message.from_user.id, balance=p["balance"] + amount)
        await message.answer(f"🎁 +<b>{fmt(amount)}$</b>!", parse_mode="HTML")
    else:
        qty = random.randint(1, 2)
        await db.add_inventory_item(p["id"], "case", "1", qty)
        await message.answer(f"🎁 +<b>{qty} обычный кейс</b>!", parse_mode="HTML")
