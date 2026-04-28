import random
from aiogram import Router, F, types

from .utils import get_or_create, fmt
from config import CASES, PETS
import database as db

router = Router()


def open_case_reward(case_num):
    if case_num == 1:
        return ("💵", random.randint(0, 1000), "деньги")
    elif case_num == 2:
        return ("💵", random.randint(100, 10000), "деньги")
    elif case_num == 3:
        if random.random() < 0.2:
            return ("🐾", random.choice([k for k, v in PETS.items() if v["rarity"] == "epic"]), "питомец")
        return ("💵", random.randint(1000, 50000), "деньги")
    elif case_num == 4:
        if random.random() < 0.2:
            return ("🐾", random.choice([k for k, v in PETS.items() if v["rarity"] == "mythic"]), "питомец")
        return ("💵", random.randint(50000, 150000), "деньги")
    else:
        if random.random() < 0.2:
            return ("🐾", random.choice([k for k, v in PETS.items() if v["rarity"] == "legendary"]), "питомец")
        return ("💵", random.randint(500000, 1000000), "деньги")


@router.message(F.text.lower() == "кейсы")
async def cmd_cases_list(message: types.Message):
    text = "🎁 <b>Кейсы</b>\n\n"
    for num, case in CASES.items():
        price_str = f"{fmt(case['price'])}$" if case["buyable"] else "Только от админа"
        text += f"Кейс {num} — {case['name']}: {price_str}\n"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.lower().startswith("купить кейс "))
async def cmd_buy_case(message: types.Message):
    p = await get_or_create(message.from_user.id)
    parts = message.text.split()
    try:
        case_num = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1
    except:
        await message.answer("❌ Купить кейс [1-4] [кол-во]")
        return
    if case_num not in CASES or not CASES[case_num]["buyable"]:
        await message.answer("❌ Этот кейс нельзя купить!")
        return
    total = CASES[case_num]["price"] * qty
    if p["balance"] < total:
        await message.answer(f"❌ Нужно {fmt(total)}$")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - total)
    await db.add_inventory_item(p["id"], "case", str(case_num), qty)
    await message.answer(f"✅ Куплено {qty}x {CASES[case_num]['name']} за {fmt(total)}$")


@router.message(F.text.lower().startswith("открыть кейс "))
async def cmd_open_case(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        case_num = int(message.text.split()[-1])
    except:
        await message.answer("❌ Открыть кейс [1-5]")
        return
    if case_num not in CASES:
        await message.answer("❌ Такого кейса нет!")
        return
    item = await db.get_inventory_item(p["id"], "case", str(case_num))
    if not item or item["quantity"] < 1:
        await message.answer(f"❌ Нет кейса {case_num}!")
        return
    await db.remove_inventory_item(p["id"], "case", str(case_num), 1)
    emoji, value, reward_type = open_case_reward(case_num)
    if reward_type == "деньги":
        await db.update_player(message.from_user.id, balance=p["balance"] + value)
        await message.answer(f"🎁 [{CASES[case_num]['name']}]\n{emoji} <b>{fmt(value)}$</b>", parse_mode="HTML")
    else:
        existing = await db.get_pet(p["id"], value)
        if existing:
            sell_price = PETS[value]["sell"]
            await db.update_player(message.from_user.id, balance=p["balance"] + sell_price)
            await message.answer(
                f"🎁 [{CASES[case_num]['name']}]\n🐾 {value} (уже есть) → автопродажа <b>{fmt(sell_price)}$</b>",
                parse_mode="HTML"
            )
        else:
            await db.add_pet(p["id"], value)
            await message.answer(f"🎁 [{CASES[case_num]['name']}]\n🐾 Питомец: <b>{value}</b>!", parse_mode="HTML")


@router.message(F.text.lower().startswith("продать пет "))
async def cmd_sell_pet(message: types.Message):
    p = await get_or_create(message.from_user.id)
    pet_name = message.text[12:].strip().lower()
    if pet_name not in PETS or not await db.get_pet(p["id"], pet_name):
        await message.answer(f"❌ Питомца «{pet_name}» нет!")
        return
    price = PETS[pet_name]["sell"]
    await db.remove_pet(p["id"], pet_name)
    await db.update_player(message.from_user.id, balance=p["balance"] + price)
    await message.answer(f"🐾 <b>{pet_name}</b> продан за <b>{fmt(price)}$</b>", parse_mode="HTML")


@router.message(F.text.lower().startswith("купить билет "))
async def cmd_buy_ticket(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        qty = int(message.text.split()[-1])
    except:
        await message.answer("❌ Купить билет [кол-во]")
        return
    cost = qty * 100
    if p["balance"] < cost:
        await message.answer(f"❌ Нужно {fmt(cost)}$")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - cost)
    await db.add_lottery_tickets(p["id"], qty)
    await message.answer(f"🎟 {qty} билетов за {fmt(cost)}$")
