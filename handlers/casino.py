import random
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from .utils import get_or_create, fmt, now_str, parse_dt
import database as db

router = Router()

blackjack_games = {}


@router.message(F.text.lower().startswith("казино "))
async def cmd_casino(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_casino"])
    if last and datetime.now() - last < timedelta(seconds=10):
        await message.answer("⏳ Подожди 10 секунд!")
        return
    try:
        bet = float(message.text.split()[1])
    except:
        await message.answer("❌ Казино [ставка]")
        return
    if bet <= 0 or p["balance"] < bet:
        await message.answer("❌ Недостаточно денег!")
        return
    weights = [20, 25, 20, 20, 15]
    if p["vip_level"] == 1: weights = [15, 20, 20, 25, 20]
    elif p["vip_level"] == 2: weights = [10, 15, 20, 25, 30]
    elif p["vip_level"] == 3: weights = [5, 10, 20, 30, 35]
    if await db.get_pet(p["id"], "кошка"):
        weights[-1] += 10
    mult = random.choices([0, 0.5, 1, 1.5, 2], weights=weights)[0]
    diff = bet * mult - bet
    await db.update_player(message.from_user.id, balance=p["balance"] + diff, last_casino=now_str())
    labels = {0: f"😢 x0 −{fmt(bet)}$", 0.5: f"😕 x0.5 −{fmt(bet*0.5)}$", 1: "😐 x1 ничья",
              1.5: f"😊 x1.5 +{fmt(bet*0.5)}$", 2: f"🎉 x2 +{fmt(bet)}$"}
    await message.answer(f"🎰 Ставка: {fmt(bet)}$\n{labels[mult]}", parse_mode="HTML")


@router.message(F.text.lower().startswith("рулетка "))
async def cmd_roulette(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_roulette"])
    if last and datetime.now() - last < timedelta(seconds=10):
        await message.answer("⏳ Подожди 10 секунд!")
        return
    try:
        bet = float(message.text.split()[1])
    except:
        await message.answer("❌ Рулетка [ставка]")
        return
    if bet <= 0 or p["balance"] < bet:
        await message.answer("❌ Недостаточно денег!")
        return
    good = ["🌹", "🍒", "🍑", "🍋", "🥭", "🍇"]
    bad_w = 5 if await db.get_pet(p["id"], "собака") else 15
    slots = ["🖕" if random.randint(1, 100) <= bad_w else random.choice(good) for _ in range(3)]
    await db.update_player(message.from_user.id, last_roulette=now_str())
    result_str = " | ".join(slots)
    if "🖕" in slots:
        await db.update_player(message.from_user.id, balance=p["balance"] - bet)
        await message.answer(f"🎡 {result_str}\n😢 −{fmt(bet)}$")
    else:
        win = round(bet * random.uniform(1.1, 2.0), 2)
        await db.update_player(message.from_user.id, balance=p["balance"] + win - bet)
        await message.answer(f"🎡 {result_str}\n🎉 +{fmt(win)}$")


@router.message(F.text.lower().startswith("блэкджек "))
async def cmd_blackjack(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_blackjack"])
    if last and datetime.now() - last < timedelta(seconds=10):
        await message.answer("⏳ Подожди 10 секунд!")
        return
    try:
        bet = float(message.text.split()[1])
    except:
        await message.answer("❌ Блэкджек [ставка]")
        return
    if bet <= 0 or p["balance"] < bet:
        await message.answer("❌ Недостаточно денег!")
        return
    pc = [random.randint(2, 11), random.randint(2, 11)]
    dc = [random.randint(2, 11), random.randint(2, 11)]
    blackjack_games[message.from_user.id] = {"bet": bet, "player": pc, "dealer": dc}
    await db.update_player(message.from_user.id, last_blackjack=now_str())
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🃏 Взять", callback_data="bj_hit"),
        InlineKeyboardButton(text="✋ Стоп", callback_data="bj_stand")
    ]])
    await message.answer(
        f"🃏 <b>Блэкджек</b>\nТы: {pc} = {sum(pc)}\nДилер: [{dc[0]}, ?]\nСтавка: {fmt(bet)}$",
        parse_mode="HTML", reply_markup=kb
    )


@router.callback_query(F.data.in_({"bj_hit", "bj_stand"}))
async def bj_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    p = await get_or_create(tg_id)
    game = blackjack_games.get(tg_id)
    if not game:
        await callback.answer("Игра не найдена!")
        return
    if callback.data == "bj_hit":
        game["player"].append(random.randint(2, 11))
        total = sum(game["player"])
        if total > 21:
            blackjack_games.pop(tg_id)
            await db.update_player(tg_id, balance=p["balance"] - game["bet"])
            await callback.message.edit_text(f"🃏 {game['player']} = {total}\n💥 Перебор! −{fmt(game['bet'])}$")
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🃏 Взять", callback_data="bj_hit"),
                InlineKeyboardButton(text="✋ Стоп", callback_data="bj_stand")
            ]])
            await callback.message.edit_text(
                f"🃏 Ты: {game['player']} = {total}\nДилер: [{game['dealer'][0]}, ?]\nСтавка: {fmt(game['bet'])}$",
                reply_markup=kb
            )
    else:
        pt = sum(game["player"])
        dt = sum(game["dealer"])
        while dt < 17:
            game["dealer"].append(random.randint(2, 11))
            dt = sum(game["dealer"])
        blackjack_games.pop(tg_id)
        bet = game["bet"]
        if dt > 21 or pt > dt:
            result = f"🎉 Победа! +{fmt(bet)}$"
            await db.update_player(tg_id, balance=p["balance"] + bet)
        elif pt == dt:
            result = "🤝 Ничья!"
        else:
            result = f"😢 Проигрыш! −{fmt(bet)}$"
            await db.update_player(tg_id, balance=p["balance"] - bet)
        await callback.message.edit_text(
            f"🃏 Ты: {game['player']} = {pt}\nДилер: {game['dealer']} = {dt}\n{result}"
        )
    await callback.answer()
