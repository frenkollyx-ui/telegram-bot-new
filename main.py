import asyncio
import random
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, ADMIN_TG_IDS, RULES, ORES, PETS, CASES
import database as db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Pending states
pending_nick = {}
pending_marriage = {}
pending_clan_invite = {}
pending_duel = {}
pending_child_name = {}
pending_child_abort = {}
pending_keks = {}

# ─── HELPERS ───────────────────────────────────────────────

def fmt(n):
    return f"{n:,.0f}".replace(",", ".")

def now_str():
    return datetime.now().isoformat()

def parse_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s)

async def is_banned(player):
    if player["banned_until"]:
        ban_dt = parse_dt(player["banned_until"])
        if ban_dt == "forever" or ban_dt > datetime.now():
            return True
    return False

async def get_or_create(tg_id):
    p = await db.get_player(tg_id)
    if not p:
        p = await db.create_player(tg_id)
    return p

def is_admin(tg_id):
    return tg_id in ADMIN_TG_IDS

def is_mod_or_admin(player):
    return player["status"] in ("admin", "moderator") or player["tg_id"] in ADMIN_TG_IDS

def has_vip(player):
    return player["vip_level"] > 0

def casino_win_chances(player):
    pets_list = []
    base = [0, 0.5, 1, 1.5, 2]
    bonus = 0
    if player["vip_level"] == 1:
        bonus = 0.1
    elif player["vip_level"] == 2:
        bonus = 0.2
    elif player["vip_level"] == 3:
        bonus = 0.3
    return base, bonus

BUSINESS_INCOME_PER_LEVEL = 500   # $ per hour per level
FARM_INCOME_PER_LEVEL = 0.0001    # BTC per hour per level
BUSINESS_UPGRADE_COST = 25000
FARM_UPGRADE_COST = 50000

HELP_TEXT = """
📋 ВСЕ КОМАНДЫ OPG БОТА:

👤 ПРОФИЛЬ:
• Профиль — посмотреть профиль
• Б / Баланс — баланс
• Инвентарь — инвентарь
• Поменять ник — сменить ник

🏦 ФИНАНСЫ:
• Банк положить [сумма]
• Банк снять [сумма]
• Депозит положить [сумма]
• Депозит снять
• Депозит — посмотреть депозит

⛏️ РУДЫ:
• Копать [руда]
• Продать [руда] [кол-во]

🎰 ИГРЫ:
• Казино [ставка]
• Рулетка [ставка]
• Блэкджек [ставка]
• Купить билет [кол-во]

🎁 КЕЙСЫ:
• Кейсы — список кейсов
• Купить кейс [1-4] [кол-во]
• Открыть кейс [1-5]

🏰 КЛАНЫ:
• Создать клан [название]
• Казна клана [сумма]
• Клан пригласить [ID]
• Клан передать [ID]
• Клан топ

⚔️ ПРОЧЕЕ:
• Дуэль — вызов на дуэль (в ответ)
• Взломать сейф
• Найти монетки
• Ежедневный бонус
• Брак [ID]
• Мой брак
• Брак кекс

🏢 БИЗНЕС:
• Построить бизнес
• Мой бизнес
• Построить ферму
• Моя ферма

🐾 ПИТОМЦЫ:
• Продать пет [название]

📜 ПРОЧЕЕ:
• Правила
• П1-П9 — отдельное правило
• /report [причина]
• Помощь
"""

RP_ACTIONS = {
    "обнять": "обнял(а)",
    "поцеловать": "поцеловал(а)",
    "кусь": "укусил(а)",
    "бросить с обрыва": "бросил(а) с обрыва",
    "толкнуть": "толкнул(а)",
    "прижать": "прижал(а)",
    "покормить": "покормил(а)",
    "съесть": "съел(а)",
    "убить": "убил(а)",
    "зарезать": "зарезал(а)",
    "кинуть снежок": "кинул(а) снежок в",
}

# ─── /START ────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    p = await db.get_player(tg_id)
    if not p:
        await db.create_player(tg_id)
    await message.answer(
        "🎮 Добро пожаловать в <b>OPG бот</b>!\n\n"
        "Тут ты сможешь играть с людьми, создать или вступить в клан. "
        "Наполняй казну клана деньгами чтобы добраться до топ-1. "
        "Активируй промокоды которые будут выходить, открывай кейсы, вступай в брак, возьми ребёнка.\n\n"
        "Наслаждайся всеми возможностями игрового бота OPG.\n\n"
        "Если не знаешь что делать то вступай в наш официальный чат:\n"
        "https://t.me/+1YBeN8EFk9c5YjUy",
        parse_mode="HTML"
    )

# ─── ПОМОЩЬ ────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() in ("помощь", "help"))
async def cmd_help(message: types.Message):
    await message.answer(HELP_TEXT)

# ─── БАЛАНС ────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() in ("б", "баланс"))
async def cmd_balance(message: types.Message):
    p = await get_or_create(message.from_user.id)
    await message.answer(
        f"💰 <b>Баланс</b>\n\n"
        f"💵 Деньги: <b>{fmt(p['balance'])}$</b>\n"
        f"₿ BTC: <b>{p['btc']:.6f}</b>\n"
        f"🏦 Банк: <b>{fmt(p['bank'])}$</b>",
        parse_mode="HTML"
    )

# ─── ПРОФИЛЬ ───────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "профиль")
async def cmd_profile(message: types.Message):
    p = await get_or_create(message.from_user.id)
    clan_name = "—"
    if p["clan_id"]:
        clan = await db.get_clan(p["clan_id"])
        if clan:
            clan_name = clan["name"]

    marriage = await db.get_marriage(p["id"])
    marriage_info = "—"
    if marriage:
        spouse_id = marriage["wife_id"] if marriage["husband_id"] == p["id"] else marriage["husband_id"]
        spouse = await db.get_player_by_game_id(spouse_id)
        if spouse:
            marriage_info = f"{spouse['username']} (#{spouse_id})"

    inv = await db.get_inventory(p["id"])
    coins = next((i["quantity"] for i in inv if i["item_type"] == "coins"), 0)
    cases_count = sum(i["quantity"] for i in inv if i["item_type"] == "case")
    pets_list = await db.get_pets(p["id"])
    pets_str = ", ".join(pet["pet_name"] for pet in pets_list) if pets_list else "—"

    status_map = {"player": "Игрок", "moderator": "Модератор", "admin": "Администратор"}
    status_str = status_map.get(p["status"], p["status"])
    if p["vip_level"] > 0:
        status_str += f" | VIP{p['vip_level']}"

    await message.answer(
        f"👤 <b>Профиль — {p['username']}</b>\n\n"
        f"🆔 ID: <b>{p['id']}</b>\n"
        f"💵 Баланс: <b>{fmt(p['balance'])}$</b>\n"
        f"₿ BTC: <b>{p['btc']:.6f}</b>\n"
        f"🏦 Банк: <b>{fmt(p['bank'])}$</b>\n"
        f"🏰 Клан: <b>{clan_name}</b>\n"
        f"🪙 Монетки: <b>{coins}</b>\n"
        f"🎁 Кейсов: <b>{cases_count}</b>\n"
        f"🐾 Питомцы: <b>{pets_str}</b>\n"
        f"⚡ Энергия: <b>{p['energy']}/100</b>\n"
        f"⭐ Опыт: <b>{p['exp']}</b>\n"
        f"💍 Брак: <b>{marriage_info}</b>\n"
        f"🎖 Статус: <b>{status_str}</b>",
        parse_mode="HTML"
    )

# ─── НИК ───────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "поменять ник")
async def cmd_change_nick(message: types.Message):
    pending_nick[message.from_user.id] = True
    await message.answer("✏️ Введи новый ник (5–25 символов):")

@dp.message(lambda m: m.from_user.id in pending_nick)
async def cmd_set_nick(message: types.Message):
    nick = message.text.strip()
    if len(nick) < 5 or len(nick) > 25:
        await message.answer("❌ Ник должен быть от 5 до 25 символов!")
        return
    pending_nick.pop(message.from_user.id)
    await db.update_player(message.from_user.id, username=nick)
    await message.answer(f"✅ Ник изменён на: <b>{nick}</b>", parse_mode="HTML")

# ─── ИНВЕНТАРЬ ─────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "инвентарь")
async def cmd_inventory(message: types.Message):
    p = await get_or_create(message.from_user.id)
    inv = await db.get_inventory(p["id"])

    coins = next((i["quantity"] for i in inv if i["item_type"] == "coins"), 0)
    cases = {i["item_name"]: i["quantity"] for i in inv if i["item_type"] == "case"}
    ores = {i["item_name"]: i["quantity"] for i in inv if i["item_type"] == "ore"}
    pets = await db.get_pets(p["id"])

    ores_str = "\n".join(f"  • {k}: {v}" for k, v in ores.items()) if ores else "  —"
    cases_str = "\n".join(f"  • Кейс {k}: {v}" for k, v in cases.items()) if cases else "  —"
    pets_str = "\n".join(f"  • {pet['pet_name']}" for pet in pets) if pets else "  —"

    await message.answer(
        f"🎒 <b>Инвентарь — {p['username']}</b>\n\n"
        f"🪙 Монетки: <b>{coins}</b>\n\n"
        f"⛏️ Руда:\n{ores_str}\n\n"
        f"🎁 Кейсы:\n{cases_str}\n\n"
        f"🐾 Питомцы:\n{pets_str}",
        parse_mode="HTML"
    )

# ─── НАЙТИ МОНЕТКИ ─────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "найти монетки")
async def cmd_find_coins(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_coins"])
    if last and datetime.now() - last < timedelta(minutes=5):
        left = timedelta(minutes=5) - (datetime.now() - last)
        await message.answer(f"⏳ Подожди ещё {int(left.seconds/60)}м {left.seconds%60}с")
        return
    amount = random.randint(1, 5)
    await db.add_inventory_item(p["id"], "coins", "монетки", amount)
    await db.update_player(message.from_user.id, last_coins=now_str())
    await message.answer(f"🪙 Ты нашёл <b>{amount}</b> монеток!", parse_mode="HTML")

# ─── БАНК ──────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("банк положить "))
async def cmd_bank_deposit(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Укажи сумму: Банк положить [сумма]")
        return
    if amount <= 0 or p["balance"] < amount:
        await message.answer("❌ Недостаточно денег!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - amount, bank=p["bank"] + amount)
    await message.answer(f"🏦 Положено в банк: <b>{fmt(amount)}$</b>", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("банк снять "))
async def cmd_bank_withdraw(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Укажи сумму: Банк снять [сумма]")
        return
    if amount <= 0 or p["bank"] < amount:
        await message.answer("❌ Недостаточно денег в банке!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] + amount, bank=p["bank"] - amount)
    await message.answer(f"🏦 Снято из банка: <b>{fmt(amount)}$</b>", parse_mode="HTML")

# ─── ДЕПОЗИТ ───────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "депозит")
async def cmd_deposit_info(message: types.Message):
    p = await get_or_create(message.from_user.id)
    dep_date = parse_dt(p["deposit_date"])
    can_withdraw = "✅ Можно снять" if dep_date and datetime.now() - dep_date >= timedelta(days=7) else "❌ Нельзя снять (нужно 7 дней)"
    days_passed = (datetime.now() - dep_date).days if dep_date else 0
    earned = p["deposit_initial"] * 0.10 * days_passed if p["deposit_initial"] else 0
    total = p["deposit"] + earned
    await message.answer(
        f"💼 <b>Депозит</b>\n\n"
        f"💰 Внесено: <b>{fmt(p['deposit_initial'])}$</b>\n"
        f"📈 Накоплено: <b>{fmt(total)}$</b>\n"
        f"📅 Дней прошло: <b>{days_passed}</b>\n"
        f"{can_withdraw}",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().startswith("депозит положить "))
async def cmd_deposit_put(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Укажи сумму: Депозит положить [сумма]")
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
    await message.answer(
        f"💼 Внесено в депозит: <b>{fmt(net)}$</b>\n"
        f"💸 Комиссия (1.5%): <b>{fmt(commission)}$</b>",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower() == "депозит снять")
async def cmd_deposit_withdraw(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["deposit_date"]:
        await message.answer("❌ У тебя нет депозита!")
        return
    dep_date = parse_dt(p["deposit_date"])
    if datetime.now() - dep_date < timedelta(days=7):
        left = timedelta(days=7) - (datetime.now() - dep_date)
        await message.answer(f"❌ Снять можно только через 7 дней! Осталось: {left.days}д {left.seconds//3600}ч")
        return
    days_passed = (datetime.now() - dep_date).days
    earned = p["deposit_initial"] * 0.10 * days_passed
    total = p["deposit"] + earned
    commission = total * 0.02
    net = total - commission
    await db.update_player(
        message.from_user.id,
        balance=p["balance"] + net,
        deposit=0,
        deposit_initial=0,
        deposit_date=None
    )
    await message.answer(
        f"💼 Снято с депозита: <b>{fmt(net)}$</b>\n"
        f"💸 Комиссия (2%): <b>{fmt(commission)}$</b>",
        parse_mode="HTML"
    )

# ─── РУДА ──────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("копать "))
async def cmd_mine(message: types.Message):
    p = await get_or_create(message.from_user.id)
    ore_name = message.text[7:].strip().lower()
    if ore_name not in ORES:
        await message.answer("❌ Такой руды нет! Доступно: " + ", ".join(ORES.keys()))
        return
    ore = ORES[ore_name]
    if p["exp"] < ore["min_exp"]:
        await message.answer(f"❌ Нужно {ore['min_exp']} опыта! У тебя: {p['exp']}")
        return
    if p["energy"] <= 0:
        await message.answer("❌ Нет энергии! Восстанавливается 1 ед. каждые 5 минут.")
        return
    amount = random.randint(ore["min"], ore["max"])
    await db.add_inventory_item(p["id"], "ore", ore_name, amount)
    await db.update_player(message.from_user.id, energy=p["energy"] - 1, exp=p["exp"] + 10)
    await message.answer(
        f"⛏️ Ты накопал <b>{amount} {ore_name}</b>!\n"
        f"⚡ Энергия: {p['energy']-1}/100 | ⭐ Опыт: {p['exp']+10}",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().startswith("продать "))
async def cmd_sell_ore(message: types.Message):
    p = await get_or_create(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Формат: Продать [руда] [кол-во]")
        return
    ore_name = " ".join(parts[1:-1]).lower()
    try:
        qty = int(parts[-1])
    except:
        await message.answer("❌ Укажи количество числом")
        return
    if ore_name not in ORES:
        await message.answer("❌ Такой руды нет!")
        return
    item = await db.get_inventory_item(p["id"], "ore", ore_name)
    if not item or item["quantity"] < qty:
        await message.answer(f"❌ У тебя недостаточно {ore_name}!")
        return
    total = qty * ORES[ore_name]["price"]
    await db.remove_inventory_item(p["id"], "ore", ore_name, qty)
    await db.update_player(message.from_user.id, balance=p["balance"] + total)
    await message.answer(f"💰 Продано {qty} {ore_name} за <b>{fmt(total)}$</b>", parse_mode="HTML")

# ─── КЕЙСЫ ─────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "кейсы")
async def cmd_cases_list(message: types.Message):
    text = "🎁 <b>Кейсы</b>\n\n"
    for num, case in CASES.items():
        price_str = f"{fmt(case['price'])}$" if case["buyable"] else "Только от админа"
        text += f"Кейс {num} — {case['name']}: {price_str}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("купить кейс "))
async def cmd_buy_case(message: types.Message):
    p = await get_or_create(message.from_user.id)
    parts = message.text.split()
    try:
        case_num = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1
    except:
        await message.answer("❌ Формат: Купить кейс [1-4] [кол-во]")
        return
    if case_num not in CASES or not CASES[case_num]["buyable"]:
        await message.answer("❌ Этот кейс нельзя купить!")
        return
    total = CASES[case_num]["price"] * qty
    if p["balance"] < total:
        await message.answer(f"❌ Нужно {fmt(total)}$, у тебя {fmt(p['balance'])}$")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - total)
    await db.add_inventory_item(p["id"], "case", str(case_num), qty)
    await message.answer(f"✅ Куплено {qty} кейс(ов) [{CASES[case_num]['name']}] за {fmt(total)}$")

def open_case_reward(case_num):
    rewards = {
        1: lambda: ("💵", random.randint(0, 1000), "деньги"),
        2: lambda: ("💵", random.randint(100, 10000), "деньги"),
        3: lambda: open_epic_case(),
        4: lambda: open_mythic_case(),
        5: lambda: open_legendary_case(),
    }
    return rewards[case_num]()

def open_epic_case():
    if random.random() < 0.2:
        pets = [k for k, v in PETS.items() if v["rarity"] == "epic"]
        return ("🐾", random.choice(pets), "питомец")
    return ("💵", random.randint(1000, 50000), "деньги")

def open_mythic_case():
    if random.random() < 0.2:
        pets = [k for k, v in PETS.items() if v["rarity"] == "mythic"]
        return ("🐾", random.choice(pets), "питомец")
    return ("💵", random.randint(50000, 150000), "деньги")

def open_legendary_case():
    if random.random() < 0.2:
        pets = [k for k, v in PETS.items() if v["rarity"] == "legendary"]
        return ("🐾", random.choice(pets), "питомец")
    return ("💵", random.randint(500000, 1000000), "деньги")

@dp.message(lambda m: m.text and m.text.lower().startswith("открыть кейс "))
async def cmd_open_case(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        case_num = int(message.text.split()[-1])
    except:
        await message.answer("❌ Формат: Открыть кейс [1-5]")
        return
    if case_num not in CASES:
        await message.answer("❌ Такого кейса нет!")
        return
    item = await db.get_inventory_item(p["id"], "case", str(case_num))
    if not item or item["quantity"] < 1:
        await message.answer(f"❌ У тебя нет кейса {case_num}!")
        return
    await db.remove_inventory_item(p["id"], "case", str(case_num), 1)
    emoji, value, reward_type = open_case_reward(case_num)
    if reward_type == "деньги":
        await db.update_player(message.from_user.id, balance=p["balance"] + value)
        await message.answer(
            f"🎁 Открыт кейс [{CASES[case_num]['name']}]!\n\n"
            f"{emoji} Награда: <b>{fmt(value)}$</b>",
            parse_mode="HTML"
        )
    else:
        existing = await db.get_pet(p["id"], value)
        if existing:
            sell_price = PETS[value]["sell"]
            await db.update_player(message.from_user.id, balance=p["balance"] + sell_price)
            await message.answer(
                f"🎁 Открыт кейс [{CASES[case_num]['name']}]!\n\n"
                f"🐾 Выпал питомец: <b>{value}</b> (уже есть)\n"
                f"💰 Автопродажа: <b>{fmt(sell_price)}$</b>",
                parse_mode="HTML"
            )
        else:
            await db.add_pet(p["id"], value)
            await message.answer(
                f"🎁 Открыт кейс [{CASES[case_num]['name']}]!\n\n"
                f"🐾 Выпал питомец: <b>{value}</b>!",
                parse_mode="HTML"
            )

# ─── ПИТОМЦЫ ───────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("продать пет "))
async def cmd_sell_pet(message: types.Message):
    p = await get_or_create(message.from_user.id)
    pet_name = message.text[12:].strip().lower()
    pet = await db.get_pet(p["id"], pet_name)
    if not pet:
        await message.answer(f"❌ У тебя нет питомца «{pet_name}»!")
        return
    price = PETS[pet_name]["sell"]
    await db.remove_pet(p["id"], pet_name)
    await db.update_player(message.from_user.id, balance=p["balance"] + price)
    await message.answer(f"🐾 Питомец <b>{pet_name}</b> продан за <b>{fmt(price)}$</b>", parse_mode="HTML")

# ─── КАЗИНО ────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("казино "))
async def cmd_casino(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_casino"])
    if last and datetime.now() - last < timedelta(seconds=10):
        await message.answer("⏳ Подожди 10 секунд!")
        return
    try:
        bet = float(message.text.split()[1])
    except:
        await message.answer("❌ Формат: Казино [ставка]")
        return
    if bet <= 0 or p["balance"] < bet:
        await message.answer("❌ Недостаточно денег!")
        return

    # VIP bonus: weighted toward higher multipliers
    weights = [20, 25, 20, 20, 15]
    if p["vip_level"] == 1:
        weights = [15, 20, 20, 25, 20]
    elif p["vip_level"] == 2:
        weights = [10, 15, 20, 25, 30]
    elif p["vip_level"] == 3:
        weights = [5, 10, 20, 30, 35]

    # Check cat pet bonus
    cat = await db.get_pet(p["id"], "кошка")
    if cat:
        weights = [max(0, w - 2) for w in weights]
        weights[-1] += 10

    multipliers = [0, 0.5, 1, 1.5, 2]
    mult = random.choices(multipliers, weights=weights)[0]
    win = bet * mult
    diff = win - bet
    new_balance = p["balance"] + diff

    await db.update_player(message.from_user.id, balance=new_balance, last_casino=now_str())

    if mult == 0:
        result = f"😢 Множитель x0 — потерял <b>{fmt(bet)}$</b>"
    elif mult == 0.5:
        result = f"😕 Множитель x0.5 — потерял <b>{fmt(bet*0.5)}$</b>"
    elif mult == 1:
        result = f"😐 Множитель x1 — ничья"
    elif mult == 1.5:
        result = f"😊 Множитель x1.5 — выиграл <b>{fmt(bet*0.5)}$</b>"
    else:
        result = f"🎉 Множитель x2 — выиграл <b>{fmt(bet)}$</b>"

    await message.answer(
        f"🎰 <b>Казино</b>\n\nСтавка: {fmt(bet)}$\n{result}\n💰 Баланс: {fmt(new_balance)}$",
        parse_mode="HTML"
    )

# ─── РУЛЕТКА ───────────────────────────────────────────────

ROULETTE_SYMBOLS = ["🌹", "🍒", "🍑", "🍋", "🥭", "🍇", "🖕"]

@dp.message(lambda m: m.text and m.text.lower().startswith("рулетка "))
async def cmd_roulette(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_roulette"])
    if last and datetime.now() - last < timedelta(seconds=10):
        await message.answer("⏳ Подожди 10 секунд!")
        return
    try:
        bet = float(message.text.split()[1])
    except:
        await message.answer("❌ Формат: Рулетка [ставка]")
        return
    if bet <= 0 or p["balance"] < bet:
        await message.answer("❌ Недостаточно денег!")
        return

    good = ["🌹", "🍒", "🍑", "🍋", "🥭", "🍇"]
    # Dog pet bonus
    dog = await db.get_pet(p["id"], "собака")
    bad_weight = 5 if dog else 15

    slots = []
    for _ in range(3):
        if random.randint(1, 100) <= bad_weight:
            slots.append("🖕")
        else:
            slots.append(random.choice(good))

    result_str = " | ".join(slots)
    await db.update_player(message.from_user.id, last_roulette=now_str())

    if "🖕" in slots:
        await db.update_player(message.from_user.id, balance=p["balance"] - bet)
        await message.answer(
            f"🎡 <b>Рулетка</b>\n\n{result_str}\n\n😢 Проигрыш! Потерял <b>{fmt(bet)}$</b>",
            parse_mode="HTML"
        )
    else:
        win = round(bet * random.uniform(1.1, 2.0), 2)
        await db.update_player(message.from_user.id, balance=p["balance"] + (win - bet))
        await message.answer(
            f"🎡 <b>Рулетка</b>\n\n{result_str}\n\n🎉 Выигрыш: <b>{fmt(win)}$</b>",
            parse_mode="HTML"
        )

# ─── БЛЭКДЖЕК ──────────────────────────────────────────────

blackjack_games = {}

def bj_card():
    return random.randint(2, 11)

def bj_total(cards):
    return sum(cards)

@dp.message(lambda m: m.text and m.text.lower().startswith("блэкджек "))
async def cmd_blackjack(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_blackjack"])
    if last and datetime.now() - last < timedelta(seconds=10):
        await message.answer("⏳ Подожди 10 секунд!")
        return
    try:
        bet = float(message.text.split()[1])
    except:
        await message.answer("❌ Формат: Блэкджек [ставка]")
        return
    if bet <= 0 or p["balance"] < bet:
        await message.answer("❌ Недостаточно денег!")
        return

    player_cards = [bj_card(), bj_card()]
    dealer_cards = [bj_card(), bj_card()]
    blackjack_games[message.from_user.id] = {
        "bet": bet,
        "player": player_cards,
        "dealer": dealer_cards
    }
    await db.update_player(message.from_user.id, last_blackjack=now_str())

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🃏 Взять карту", callback_data="bj_hit"),
            InlineKeyboardButton(text="✋ Стоп", callback_data="bj_stand")
        ]
    ])
    await message.answer(
        f"🃏 <b>Блэкджек</b>\n\n"
        f"Твои карты: {player_cards} = <b>{bj_total(player_cards)}</b>\n"
        f"Карта дилера: [{dealer_cards[0]}, ?]\n\n"
        f"Ставка: {fmt(bet)}$",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data in ("bj_hit", "bj_stand"))
async def bj_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    p = await get_or_create(tg_id)
    game = blackjack_games.get(tg_id)
    if not game:
        await callback.answer("Игра не найдена!")
        return

    if callback.data == "bj_hit":
        game["player"].append(bj_card())
        total = bj_total(game["player"])
        if total > 21:
            blackjack_games.pop(tg_id)
            await db.update_player(tg_id, balance=p["balance"] - game["bet"])
            await callback.message.edit_text(
                f"🃏 <b>Блэкджек</b>\n\n"
                f"Твои карты: {game['player']} = <b>{total}</b>\n"
                f"💥 Перебор! Потерял <b>{fmt(game['bet'])}$</b>",
                parse_mode="HTML"
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🃏 Взять карту", callback_data="bj_hit"),
                    InlineKeyboardButton(text="✋ Стоп", callback_data="bj_stand")
                ]
            ])
            await callback.message.edit_text(
                f"🃏 <b>Блэкджек</b>\n\n"
                f"Твои карты: {game['player']} = <b>{total}</b>\n"
                f"Карта дилера: [{game['dealer'][0]}, ?]\n"
                f"Ставка: {fmt(game['bet'])}$",
                parse_mode="HTML",
                reply_markup=kb
            )
    else:
        player_total = bj_total(game["player"])
        dealer_total = bj_total(game["dealer"])
        while dealer_total < 17:
            game["dealer"].append(bj_card())
            dealer_total = bj_total(game["dealer"])

        # Bear pet bonus
        bear = await db.get_pet(p["id"], "медведь")
        if bear and dealer_total > 21:
            dealer_total = 22

        blackjack_games.pop(tg_id)
        bet = game["bet"]

        if player_total > 21:
            result = f"💥 Перебор! Потерял <b>{fmt(bet)}$</b>"
            await db.update_player(tg_id, balance=p["balance"] - bet)
        elif dealer_total > 21 or player_total > dealer_total:
            result = f"🎉 Победа! Выиграл <b>{fmt(bet)}$</b>"
            await db.update_player(tg_id, balance=p["balance"] + bet)
        elif player_total == dealer_total:
            result = "🤝 Ничья!"
        else:
            result = f"😢 Проигрыш! Потерял <b>{fmt(bet)}$</b>"
            await db.update_player(tg_id, balance=p["balance"] - bet)

        await callback.message.edit_text(
            f"🃏 <b>Блэкджек</b>\n\n"
            f"Твои карты: {game['player']} = <b>{player_total}</b>\n"
            f"Дилер: {game['dealer']} = <b>{dealer_total}</b>\n\n"
            f"{result}",
            parse_mode="HTML"
        )
    await callback.answer()

# ─── ЛОТЕРЕЯ ───────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("купить билет "))
async def cmd_buy_ticket(message: types.Message):
    p = await get_or_create(message.from_user.id)
    try:
        qty = int(message.text.split()[-1])
    except:
        await message.answer("❌ Формат: Купить билет [кол-во]")
        return
    cost = qty * 100
    if p["balance"] < cost:
        await message.answer(f"❌ Нужно {fmt(cost)}$")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - cost)
    await db.add_lottery_tickets(p["id"], qty)
    await message.answer(f"🎟 Куплено <b>{qty}</b> билетов за <b>{fmt(cost)}$</b>", parse_mode="HTML")

# ─── КЛАНЫ ─────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("создать клан "))
async def cmd_create_clan(message: types.Message):
    p = await get_or_create(message.from_user.id)
    name = message.text[13:].strip()
    if not name:
        await message.answer("❌ Укажи название!")
        return
    if p["clan_id"]:
        await message.answer("❌ Ты уже в клане!")
        return
    if p["balance"] < 50000:
        await message.answer("❌ Нужно 50.000$ для создания клана!")
        return
    existing = await db.get_clan_by_name(name)
    if existing:
        await message.answer("❌ Клан с таким названием уже существует!")
        return
    clan = await db.create_clan(name, p["id"])
    await db.update_player(message.from_user.id, balance=p["balance"] - 50000, clan_id=clan["id"])
    await db.add_clan_member(clan["id"], p["id"])
    await message.answer(f"🏰 Клан <b>{name}</b> создан!", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("казна клана "))
async def cmd_clan_treasury(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    try:
        amount = float(message.text.split()[-1])
    except:
        await message.answer("❌ Формат: Казна клана [сумма]")
        return
    if p["balance"] < amount:
        await message.answer("❌ Недостаточно денег!")
        return
    clan = await db.get_clan(p["clan_id"])
    new_treasury = clan["treasury"] + amount
    new_rating = int(new_treasury / 10000)
    await db.update_clan(p["clan_id"], treasury=new_treasury, rating=new_rating)
    await db.update_player(message.from_user.id, balance=p["balance"] - amount)
    await message.answer(
        f"🏦 Внесено в казну клана: <b>{fmt(amount)}$</b>\n"
        f"⭐ Рейтинг клана: <b>{new_rating}</b>",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().startswith("клан пригласить "))
async def cmd_clan_invite(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    clan = await db.get_clan(p["clan_id"])
    if clan["owner_id"] != p["id"]:
        await message.answer("❌ Только глава клана может приглашать!")
        return
    try:
        target_id = int(message.text.split()[-1])
    except:
        await message.answer("❌ Формат: Клан пригласить [ID]")
        return
    target = await db.get_player_by_game_id(target_id)
    if not target:
        await message.answer("❌ Игрок не найден!")
        return
    if target["clan_id"]:
        await message.answer("❌ Игрок уже в клане!")
        return
    pending_clan_invite[target["tg_id"]] = {"clan_id": p["clan_id"], "from_id": p["id"]}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"clan_accept_{p['clan_id']}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data="clan_decline")
        ]
    ])
    try:
        await bot.send_message(
            target["tg_id"],
            f"📨 Тебя приглашают в клан <b>{clan['name']}</b>!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await message.answer("✅ Приглашение отправлено!")
    except:
        await message.answer("❌ Не удалось отправить приглашение!")

@dp.callback_query(lambda c: c.data.startswith("clan_accept_") or c.data == "clan_decline")
async def clan_invite_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    p = await get_or_create(tg_id)
    if callback.data == "clan_decline":
        pending_clan_invite.pop(tg_id, None)
        await callback.message.edit_text("❌ Ты отказался от приглашения в клан.")
        return
    clan_id = int(callback.data.split("_")[-1])
    await db.update_player(tg_id, clan_id=clan_id)
    await db.add_clan_member(clan_id, p["id"])
    clan = await db.get_clan(clan_id)
    pending_clan_invite.pop(tg_id, None)
    await callback.message.edit_text(f"✅ Ты вступил в клан <b>{clan['name']}</b>!", parse_mode="HTML")
    await callback.answer()

@dp.message(lambda m: m.text and m.text.lower().startswith("клан передать "))
async def cmd_clan_transfer(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    clan = await db.get_clan(p["clan_id"])
    if clan["owner_id"] != p["id"]:
        await message.answer("❌ Только глава клана может передать клан!")
        return
    try:
        target_id = int(message.text.split()[-1])
    except:
        await message.answer("❌ Формат: Клан передать [ID]")
        return
    target = await db.get_player_by_game_id(target_id)
    if not target or target["clan_id"] != p["clan_id"]:
        await message.answer("❌ Игрок не найден или не в твоём клане!")
        return
    await db.update_clan(p["clan_id"], owner_id=target["id"])
    await message.answer(f"✅ Клан передан игроку <b>{target['username']}</b>", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower() == "клан топ")
async def cmd_clan_top(message: types.Message):
    p = await get_or_create(message.from_user.id)
    clans = await db.get_top_clans(10)
    text = "🏆 <b>Топ 10 кланов</b>\n\n"
    for i, clan in enumerate(clans, 1):
        text += f"{i}. <b>{clan['name']}</b> — ⭐{clan['rating']} | 💰{fmt(clan['treasury'])}$\n"
    if p["clan_id"]:
        clan = await db.get_clan(p["clan_id"])
        if clan:
            text += f"\n📍 Твой клан: <b>{clan['name']}</b> — ⭐{clan['rating']}"
    await message.answer(text, parse_mode="HTML")

# ─── ВОЙНЫ КЛАНОВ ──────────────────────────────────────────

clan_war_sessions = {}

@dp.message(lambda m: m.text and m.text.lower().startswith("война клан "))
async def cmd_clan_war(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["clan_id"]:
        await message.answer("❌ Ты не в клане!")
        return
    clan = await db.get_clan(p["clan_id"])
    if clan["owner_id"] != p["id"]:
        await message.answer("❌ Только глава клана может объявить войну!")
        return
    last = parse_dt(p["last_war"])
    if last and datetime.now() - last < timedelta(hours=24):
        await message.answer("❌ Войну можно объявлять раз в 24 часа!")
        return
    try:
        target_clan_id = int(message.text.split()[-1])
    except:
        await message.answer("❌ Формат: Война клан [ID клана]")
        return
    target_clan = await db.get_clan(target_clan_id)
    if not target_clan:
        await message.answer("❌ Клан не найден!")
        return

    # Generate number sequence task
    numbers = random.sample(range(1, 50), 5)
    sorted_nums = sorted(numbers)
    word = " ".join(map(str, sorted_nums))

    await db.create_clan_war(p["clan_id"], target_clan_id, word)
    await db.update_player(message.from_user.id, last_war=now_str())

    clan_war_sessions[p["clan_id"]] = {"answer": word, "defender": target_clan_id}
    clan_war_sessions[target_clan_id] = {"answer": word, "challenger": p["clan_id"]}

    members = await db.get_clan_members(target_clan_id)
    for member in members:
        try:
            await bot.send_message(
                member["tg_id"],
                f"⚔️ Клан <b>{clan['name']}</b> объявил войну вашему клану!\n\n"
                f"Напишите числа в порядке возрастания:\n<b>{' '.join(map(str, numbers))}</b>",
                parse_mode="HTML"
            )
        except:
            pass

    my_members = await db.get_clan_members(p["clan_id"])
    for member in my_members:
        try:
            await bot.send_message(
                member["tg_id"],
                f"⚔️ Война объявлена клану <b>{target_clan['name']}</b>!\n\n"
                f"Напишите числа в порядке возрастания:\n<b>{' '.join(map(str, numbers))}</b>",
                parse_mode="HTML"
            )
        except:
            pass

# ─── ДУЭЛЬ ─────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "дуэль" and m.reply_to_message)
async def cmd_duel(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_duel"])
    if last and datetime.now() - last < timedelta(minutes=30):
        left = timedelta(minutes=30) - (datetime.now() - last)
        await message.answer(f"⏳ КД дуэли: {int(left.seconds/60)}м {left.seconds%60}с")
        return
    coins_item = await db.get_inventory_item(p["id"], "coins", "монетки")
    if not coins_item or coins_item["quantity"] < 3:
        await message.answer("❌ Нужно 3 монетки для дуэли!")
        return
    target_tg_id = message.reply_to_message.from_user.id
    if target_tg_id == message.from_user.id:
        await message.answer("❌ Нельзя вызвать себя!")
        return
    target = await get_or_create(target_tg_id)
    pending_duel[target_tg_id] = {"challenger_tg": message.from_user.id, "challenger_id": p["id"]}

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"duel_accept_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data="duel_decline")
        ]
    ])
    await message.answer(
        f"⚔️ <b>{p['username']}</b> вызывает <b>{target['username']}</b> на дуэль!\n"
        f"Цена: 3 монетки",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data.startswith("duel_accept_") or c.data == "duel_decline")
async def duel_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    if callback.data == "duel_decline":
        pending_duel.pop(tg_id, None)
        await callback.message.edit_text("❌ Дуэль отклонена!")
        return

    challenger_tg = int(callback.data.split("_")[-1])
    challenger = await get_or_create(challenger_tg)
    target = await get_or_create(tg_id)

    # Remove coins
    await db.remove_inventory_item(challenger["id"], "coins", "монетки", 3)
    await db.remove_inventory_item(target["id"], "coins", "монетки", 3)

    # Duel: random throw distance
    c_throw = random.randint(1, 100)
    t_throw = random.randint(1, 100)

    if c_throw > t_throw:
        winner, loser = challenger, target
        winner_tg, loser_tg = challenger_tg, tg_id
    elif t_throw > c_throw:
        winner, loser = target, challenger
        winner_tg, loser_tg = tg_id, challenger_tg
    else:
        await callback.message.edit_text(
            f"⚔️ <b>Дуэль</b>\n\n"
            f"{challenger['username']}: {c_throw}м\n"
            f"{target['username']}: {t_throw}м\n\n"
            f"🤝 Ничья!",
            parse_mode="HTML"
        )
        await db.update_player(challenger_tg, last_duel=now_str())
        await db.update_player(tg_id, last_duel=now_str())
        await callback.answer()
        return

    prize_type = random.choice(["money", "coins"])
    if prize_type == "money":
        prize = random.randint(1, 1000)
        await db.update_player(winner_tg, balance=winner["balance"] + prize)
        await db.update_player(loser_tg, balance=loser["balance"] - min(prize, loser["balance"]))
        prize_str = f"{fmt(prize)}$"
    else:
        prize = random.randint(1, 10)
        await db.add_inventory_item(winner["id"], "coins", "монетки", prize)
        prize_str = f"{prize} монеток"

    await db.update_player(challenger_tg, last_duel=now_str())
    await db.update_player(tg_id, last_duel=now_str())
    pending_duel.pop(tg_id, None)

    await callback.message.edit_text(
        f"⚔️ <b>Дуэль</b>\n\n"
        f"{challenger['username']}: {c_throw}м 🏹\n"
        f"{target['username']}: {t_throw}м 🏹\n\n"
        f"🏆 Победитель: <b>{winner['username']}</b>\n"
        f"🎁 Приз: {prize_str}",
        parse_mode="HTML"
    )
    await callback.answer()

# ─── ЕЖЕДНЕВНЫЙ БОНУС ──────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "ежедневный бонус")
async def cmd_daily(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["daily_bonus_date"])
    if last and datetime.now() - last < timedelta(hours=24):
        left = timedelta(hours=24) - (datetime.now() - last)
        h, s = divmod(int(left.total_seconds()), 3600)
        m2, s2 = divmod(s, 60)
        await message.answer(f"⏳ Следующий бонус через {h}ч {m2}м")
        return
    await db.update_player(message.from_user.id, daily_bonus_date=now_str())
    if random.random() < 0.5:
        amount = random.randint(1000, 10000)
        await db.update_player(message.from_user.id, balance=p["balance"] + amount)
        await message.answer(f"🎁 Ежедневный бонус: <b>{fmt(amount)}$</b>!", parse_mode="HTML")
    else:
        qty = random.randint(1, 2)
        await db.add_inventory_item(p["id"], "case", "1", qty)
        await message.answer(f"🎁 Ежедневный бонус: <b>{qty} обычный кейс</b>!", parse_mode="HTML")

# ─── ВЗЛОМАТЬ СЕЙФ ─────────────────────────────────────────

safe_sessions = {}

@dp.message(lambda m: m.text and m.text.lower() == "взломать сейф")
async def cmd_safe(message: types.Message):
    p = await get_or_create(message.from_user.id)
    tg_id = message.from_user.id
    last = parse_dt(p["last_safe"])
    if last and datetime.now() - last < timedelta(hours=24):
        if tg_id in safe_sessions and safe_sessions[tg_id].get("attempts", 0) >= 3:
            left = timedelta(hours=24) - (datetime.now() - last)
            h, s = divmod(int(left.total_seconds()), 3600)
            await message.answer(f"⏳ Следующая попытка через {h}ч {s//60}м")
            return

    code = str(random.randint(1000, 9999))
    safe_sessions[tg_id] = {"code": code, "attempts": 0, "started": datetime.now()}
    await db.update_player(tg_id, last_safe=now_str())
    await message.answer(
        "🔐 <b>Взлом сейфа</b>\n\n"
        "Угадай 4-значный код!\n"
        "У тебя 3 попытки и 5 минут.\n\n"
        "Введи 4-значный код:",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.from_user.id in safe_sessions and m.text and m.text.isdigit() and len(m.text) == 4)
async def cmd_safe_guess(message: types.Message):
    tg_id = message.from_user.id
    p = await get_or_create(tg_id)
    session = safe_sessions[tg_id]

    if datetime.now() - session["started"] > timedelta(minutes=5):
        safe_sessions.pop(tg_id)
        await message.answer("⏰ Время вышло! Попробуй снова через 24 часа.")
        return

    session["attempts"] += 1
    if message.text == session["code"]:
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
        elif roll < 0.40:
            amount = random.randint(1000, 10000)
            await db.update_player(tg_id, balance=p["balance"] + amount)
            reward = f"💰 {fmt(amount)}$"
        else:
            amount = random.randint(500, 2500)
            await db.update_player(tg_id, balance=p["balance"] + amount)
            reward = f"💰 {fmt(amount)}$"
        await message.answer(f"🔓 Сейф взломан!\n\n🎁 Награда: <b>{reward}</b>", parse_mode="HTML")
    elif session["attempts"] >= 3:
        safe_sessions.pop(tg_id)
        await message.answer(f"❌ Попытки исчерпаны! Код был: <b>{session['code']}</b>\nПопробуй через 24 часа.", parse_mode="HTML")
    else:
        left = 3 - session["attempts"]
        await message.answer(f"❌ Неверно! Осталось попыток: {left}")

# ─── БИЗНЕС ────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "построить бизнес")
async def cmd_build_business(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if p["balance"] < 50000:
        await message.answer("❌ Нужно 50.000$!")
        return
    existing = await db.get_business(p["id"])
    if existing:
        await message.answer("❌ У тебя уже есть бизнес!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - 50000)
    await db.create_business(p["id"])
    await message.answer("🏢 Бизнес построен! Доход: 500$/час")

@dp.message(lambda m: m.text and m.text.lower() == "мой бизнес")
async def cmd_my_business(message: types.Message):
    p = await get_or_create(message.from_user.id)
    biz = await db.get_business(p["id"])
    if not biz:
        await message.answer("❌ У тебя нет бизнеса!")
        return
    last = parse_dt(biz["last_collect"])
    hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
    income_per_hour = BUSINESS_INCOME_PER_LEVEL * biz["level"]
    pending = income_per_hour * hours
    upgrade_cost = BUSINESS_UPGRADE_COST * biz["level"]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"💰 Забрать {fmt(pending)}$", callback_data="biz_collect"),
            InlineKeyboardButton(text=f"⬆️ Улучшить ({fmt(upgrade_cost)}$)", callback_data="biz_upgrade")
        ],
        [InlineKeyboardButton(text=f"💸 Оплатить налог ({fmt(biz['taxes'])}$)", callback_data="biz_tax")]
    ])
    await message.answer(
        f"🏢 <b>Мой бизнес</b>\n\n"
        f"📊 Уровень: {biz['level']}\n"
        f"💰 Доход: {fmt(income_per_hour)}$/час\n"
        f"⏳ Накоплено: {fmt(pending)}$\n"
        f"💸 Налоги: {fmt(biz['taxes'])}$",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data in ("biz_collect", "biz_upgrade", "biz_tax"))
async def biz_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    p = await get_or_create(tg_id)
    biz = await db.get_business(p["id"])
    if not biz:
        await callback.answer("Бизнес не найден!")
        return

    if callback.data == "biz_collect":
        last = parse_dt(biz["last_collect"])
        hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
        income = BUSINESS_INCOME_PER_LEVEL * biz["level"] * hours
        tax = income * 0.1
        new_taxes = biz["taxes"] + tax
        if new_taxes >= 10000:
            await callback.answer("❌ Налоги превысили 10.000$! Оплати налоги!")
            return
        await db.update_player(tg_id, balance=p["balance"] + income)
        await db.update_business(p["id"], last_collect=now_str(), taxes=new_taxes)
        await callback.message.edit_text(f"✅ Получено: <b>{fmt(income)}$</b>", parse_mode="HTML")

    elif callback.data == "biz_upgrade":
        upgrade_cost = BUSINESS_UPGRADE_COST * biz["level"]
        if p["balance"] < upgrade_cost:
            await callback.answer(f"❌ Нужно {fmt(upgrade_cost)}$")
            return
        await db.update_player(tg_id, balance=p["balance"] - upgrade_cost)
        await db.update_business(p["id"], level=biz["level"] + 1)
        await callback.message.edit_text(f"⬆️ Бизнес улучшен до уровня {biz['level']+1}!")

    elif callback.data == "biz_tax":
        if p["balance"] < biz["taxes"]:
            await callback.answer(f"❌ Нужно {fmt(biz['taxes'])}$")
            return
        await db.update_player(tg_id, balance=p["balance"] - biz["taxes"])
        await db.update_business(p["id"], taxes=0)
        await callback.message.edit_text("✅ Налоги оплачены!")

    await callback.answer()

# ─── ФЕРМА ─────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "построить ферму")
async def cmd_build_farm(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if p["balance"] < 100000:
        await message.answer("❌ Нужно 100.000$!")
        return
    existing = await db.get_farm(p["id"])
    if existing:
        await message.answer("❌ У тебя уже есть ферма!")
        return
    await db.update_player(message.from_user.id, balance=p["balance"] - 100000)
    await db.create_farm(p["id"])
    await message.answer("⛏️ BTC ферма построена! Доход: 0.0001 BTC/час")

@dp.message(lambda m: m.text and m.text.lower() == "моя ферма")
async def cmd_my_farm(message: types.Message):
    p = await get_or_create(message.from_user.id)
    farm = await db.get_farm(p["id"])
    if not farm:
        await message.answer("❌ У тебя нет фермы!")
        return
    last = parse_dt(farm["last_collect"])
    hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
    income_per_hour = FARM_INCOME_PER_LEVEL * farm["level"]
    pending = income_per_hour * hours
    upgrade_cost = FARM_UPGRADE_COST * farm["level"]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"₿ Забрать {pending:.6f} BTC", callback_data="farm_collect"),
            InlineKeyboardButton(text=f"⬆️ Улучшить ({fmt(upgrade_cost)}$)", callback_data="farm_upgrade")
        ],
        [InlineKeyboardButton(text=f"💸 Оплатить налог ({farm['taxes']:.6f} BTC)", callback_data="farm_tax")]
    ])
    await message.answer(
        f"⛏️ <b>Моя ферма</b>\n\n"
        f"📊 Уровень: {farm['level']}\n"
        f"₿ Доход: {income_per_hour:.6f} BTC/час\n"
        f"⏳ Накоплено: {pending:.6f} BTC\n"
        f"💸 Налоги: {farm['taxes']:.6f} BTC",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data in ("farm_collect", "farm_upgrade", "farm_tax"))
async def farm_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    p = await get_or_create(tg_id)
    farm = await db.get_farm(p["id"])
    if not farm:
        await callback.answer("Ферма не найдена!")
        return

    if callback.data == "farm_collect":
        last = parse_dt(farm["last_collect"])
        hours = (datetime.now() - last).total_seconds() / 3600 if last else 0
        income = FARM_INCOME_PER_LEVEL * farm["level"] * hours
        tax = income * 0.1
        new_taxes = farm["taxes"] + tax
        if new_taxes >= 10:
            await callback.answer("❌ Налоги превысили 10 BTC! Оплати налоги!")
            return
        await db.update_player(tg_id, btc=p["btc"] + income)
        await db.update_farm(p["id"], last_collect=now_str(), taxes=new_taxes)
        await callback.message.edit_text(f"✅ Получено: <b>{income:.6f} BTC</b>", parse_mode="HTML")

    elif callback.data == "farm_upgrade":
        upgrade_cost = FARM_UPGRADE_COST * farm["level"]
        if p["balance"] < upgrade_cost:
            await callback.answer(f"❌ Нужно {fmt(upgrade_cost)}$")
            return
        await db.update_player(tg_id, balance=p["balance"] - upgrade_cost)
        await db.update_farm(p["id"], level=farm["level"] + 1)
        await callback.message.edit_text(f"⬆️ Ферма улучшена до уровня {farm['level']+1}!")

    elif callback.data == "farm_tax":
        if p["btc"] < farm["taxes"]:
            await callback.answer(f"❌ Нужно {farm['taxes']:.6f} BTC")
            return
        await db.update_player(tg_id, btc=p["btc"] - farm["taxes"])
        await db.update_farm(p["id"], taxes=0)
        await callback.message.edit_text("✅ Налоги оплачены!")

    await callback.answer()

# ─── БРАКИ ─────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("брак ") and not m.text.lower().startswith("брак кекс"))
async def cmd_marry(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not p["gender"]:
        await message.answer("❌ Сначала укажи свой пол! Напиши «мужской» или «женский»")
        return
    existing = await db.get_marriage(p["id"])
    if existing:
        await message.answer("❌ Ты уже в браке!")
        return
    try:
        target_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Формат: Брак [ID игрока]")
        return
    target = await db.get_player_by_game_id(target_id)
    if not target:
        await message.answer("❌ Игрок не найден!")
        return
    if not target["gender"]:
        await message.answer("❌ У этого игрока не указан пол!")
        return
    if target["gender"] == p["gender"]:
        await message.answer("❌ Вступать в брак можно только с игроком противоположного пола!")
        return
    target_marriage = await db.get_marriage(target["id"])
    if target_marriage:
        await message.answer("❌ Этот игрок уже в браке!")
        return

    pending_marriage[target["tg_id"]] = {"from_id": p["id"], "from_tg": message.from_user.id}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_accept_{p['id']}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data="marry_decline")
        ]
    ])
    try:
        await bot.send_message(
            target["tg_id"],
            f"💍 <b>{p['username']}</b> предлагает тебе руку и сердце!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await message.answer("✅ Предложение отправлено!")
    except:
        await message.answer("❌ Не удалось отправить предложение!")

@dp.callback_query(lambda c: c.data.startswith("marry_accept_") or c.data == "marry_decline")
async def marry_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    target = await get_or_create(tg_id)
    if callback.data == "marry_decline":
        pending_marriage.pop(tg_id, None)
        await callback.message.edit_text("❌ Предложение отклонено.")
        return
    from_id = int(callback.data.split("_")[-1])
    proposer = await db.get_player_by_game_id(from_id)
    if not proposer:
        await callback.answer("Ошибка!")
        return
    if target["gender"] == "мужской":
        husband_id, wife_id = target["id"], from_id
    else:
        husband_id, wife_id = from_id, target["id"]
    await db.create_marriage(husband_id, wife_id)
    pending_marriage.pop(tg_id, None)
    await callback.message.edit_text(
        f"💍 Поздравляем! <b>{proposer['username']}</b> и <b>{target['username']}</b> теперь в браке!",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(lambda m: m.text and m.text.lower() == "мой брак")
async def cmd_my_marriage(message: types.Message):
    p = await get_or_create(message.from_user.id)
    marriage = await db.get_marriage(p["id"])
    if not marriage:
        await message.answer("❌ Ты не в браке!")
        return
    spouse_id = marriage["wife_id"] if marriage["husband_id"] == p["id"] else marriage["husband_id"]
    spouse = await db.get_player_by_game_id(spouse_id)
    children = await db.get_children(marriage["id"])
    created = parse_dt(marriage["created_at"])
    days = (datetime.now() - created).days if created else 0
    if days < 7:
        status = "💑 Молодожёны"
    elif days < 30:
        status = "❤️ Близкие люди"
    else:
        status = "💞 Неразлучимые"

    children_str = ", ".join(f"{c['name']} ({c['gender']})" for c in children) if children else "—"
    await message.answer(
        f"💍 <b>Мой брак</b>\n\n"
        f"👫 Супруг(а): <b>{spouse['username']}</b>\n"
        f"📅 Дней вместе: <b>{days}</b>\n"
        f"💫 Статус: <b>{status}</b>\n"
        f"👶 Дети: <b>{children_str}</b>",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower() == "брак кекс")
async def cmd_keks(message: types.Message):
    p = await get_or_create(message.from_user.id)
    marriage = await db.get_marriage(p["id"])
    if not marriage:
        await message.answer("❌ Ты не в браке!")
        return
    if marriage["children"] >= 4:
        await message.answer("❌ Максимум 4 ребёнка!")
        return
    spouse_id = marriage["wife_id"] if marriage["husband_id"] == p["id"] else marriage["husband_id"]
    spouse = await db.get_player_by_game_id(spouse_id)
    pending_keks[spouse["tg_id"]] = {"marriage_id": marriage["id"], "from_tg": message.from_user.id}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Согласиться", callback_data="keks_accept"),
            InlineKeyboardButton(text="❌ Отказать", callback_data="keks_decline")
        ]
    ])
    try:
        await bot.send_message(
            spouse["tg_id"],
            f"💕 <b>{p['username']}</b> хочет ребёнка!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await message.answer("✅ Запрос отправлен супругу(е)!")
    except:
        await message.answer("❌ Не удалось отправить запрос!")

@dp.callback_query(lambda c: c.data in ("keks_accept", "keks_decline"))
async def keks_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    if callback.data == "keks_decline":
        pending_keks.pop(tg_id, None)
        await callback.message.edit_text("❌ Отказано.")
        return
    session = pending_keks.pop(tg_id, None)
    if not session:
        await callback.answer("Ошибка!")
        return
    if random.random() < 0.5:
        gender = random.choice(["мальчик", "девочка"])
        pending_child_name[tg_id] = {"marriage_id": session["marriage_id"], "gender": gender, "from_tg": session["from_tg"]}
        pending_child_name[session["from_tg"]] = {"marriage_id": session["marriage_id"], "gender": gender, "from_tg": session["from_tg"]}

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Аборт", callback_data=f"abort_{session['marriage_id']}")]
        ])
        await callback.message.edit_text(
            f"🍼 Родился(ась) <b>{gender}</b>!\n\nВведи имя ребёнка (3–10 букв):",
            parse_mode="HTML",
            reply_markup=kb
        )
        await bot.send_message(
            session["from_tg"],
            f"🍼 Родился(ась) <b>{gender}</b>!\n\nВведи имя ребёнка (3–10 букв):",
            parse_mode="HTML"
        )
        # Give 500$ to father
        marriage = await db.get_marriage_by_id(session["marriage_id"]) if hasattr(db, "get_marriage_by_id") else None
    else:
        await callback.message.edit_text("😢 К сожалению, не получилось... Попробуйте позже!")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("abort_"))
async def abort_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    marriage_id = int(callback.data.split("_")[1])
    await db.delete_last_child(marriage_id)
    pending_child_name.pop(tg_id, None)
    await callback.message.edit_text("😢 Аборт сделан.")
    await callback.answer()

# ─── РП КОМАНДЫ ────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() in RP_ACTIONS and m.reply_to_message)
async def cmd_rp(message: types.Message):
    p = await get_or_create(message.from_user.id)
    target_name = message.reply_to_message.from_user.first_name
    action = RP_ACTIONS[message.text.lower()]
    await message.answer(f"🎭 <b>{p['username']}</b> {action} <b>{target_name}</b>!", parse_mode="HTML")

# ─── ПРАВИЛА ───────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "правила")
async def cmd_rules(message: types.Message):
    text = "📜 <b>Правила OPG</b>\n\n" + "\n".join(RULES)
    try:
        await bot.send_message(message.from_user.id, text, parse_mode="HTML")
        if message.chat.type != "private":
            await message.answer("📜 Правила отправлены в личные сообщения!")
    except:
        await message.answer(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.upper() in [f"П{i}" for i in range(1, 10)])
async def cmd_rule_single(message: types.Message):
    num = int(message.text[1:])
    if 1 <= num <= len(RULES):
        await message.answer(f"📜 {RULES[num-1]}", parse_mode="HTML")

# ─── /REPORT ───────────────────────────────────────────────

@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_report"])
    if last and datetime.now() - last < timedelta(minutes=10):
        await message.answer("⏳ Жалобу можно отправлять раз в 10 минут!")
        return
    args = message.text[7:].strip()
    if not args:
        await message.answer("❌ Укажи причину: /report [причина]")
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение нарушителя!")
        return
    violator = await get_or_create(message.reply_to_message.from_user.id)
    await db.update_player(message.from_user.id, last_report=now_str())

    report_text = (
        f"🚨 <b>Жалоба!</b>\n\n"
        f"От: {p['username']} (#{p['id']})\n"
        f"На: {violator['username']} (#{violator['id']})\n"
        f"Причина: {args}"
    )
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute("SELECT tg_id FROM players WHERE status IN ('admin', 'moderator')") as cursor:
            staff = await cursor.fetchall()
    for s in staff:
        try:
            await bot.send_message(s[0], report_text, parse_mode="HTML")
        except:
            pass
    for admin_tg in ADMIN_TG_IDS:
        try:
            await bot.send_message(admin_tg, report_text, parse_mode="HTML")
        except:
            pass
    await message.answer("✅ Жалоба отправлена администрации!")

# ─── ПУСТИТЬ ПОЛ ───────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() in ("мужской", "женский") and m.chat.type == "private")
async def cmd_set_gender(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if p["gender"]:
        await message.answer(f"❌ Пол уже указан: {p['gender']}")
        return
    await db.update_player(message.from_user.id, gender=message.text.lower())
    await message.answer(f"✅ Пол установлен: <b>{message.text.lower()}</b>", parse_mode="HTML")

# ─── ТОП ───────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "топ")
async def cmd_top(message: types.Message):
    players = await db.get_top_players("balance", 10)
    text = "🏆 <b>Топ 10 игроков по балансу</b>\n\n"
    for i, pl in enumerate(players, 1):
        text += f"{i}. <b>{pl['username']}</b> — {fmt(pl['balance'])}$\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower() == "топ btc")
async def cmd_top_btc(message: types.Message):
    players = await db.get_top_players("btc", 10)
    text = "🏆 <b>Топ 10 игроков по BTC</b>\n\n"
    for i, pl in enumerate(players, 1):
        text += f"{i}. <b>{pl['username']}</b> — {pl['btc']:.6f} BTC\n"
    await message.answer(text, parse_mode="HTML")

# ─── СМОТРЕТЬ ПРОФИЛЬ (MOD/ADMIN) ──────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "смотреть профиль" and m.reply_to_message)
async def cmd_view_profile(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not is_mod_or_admin(p):
        await message.answer("❌ Нет прав!")
        return
    target = await get_or_create(message.reply_to_message.from_user.id)
    clan_name = "—"
    if target["clan_id"]:
        clan = await db.get_clan(target["clan_id"])
        if clan:
            clan_name = clan["name"]
    await message.answer(
        f"👤 <b>Профиль игрока</b>\n\n"
        f"🆔 ID: {target['id']}\n"
        f"👤 Ник: {target['username']}\n"
        f"💵 Баланс: {fmt(target['balance'])}$\n"
        f"🏰 Клан: {clan_name}",
        parse_mode="HTML"
    )

# ─── БАН / МУТ ─────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("бан ") and m.reply_to_message)
async def cmd_ban(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not is_mod_or_admin(p):
        await message.answer("❌ Нет прав!")
        return
    target = await get_or_create(message.reply_to_message.from_user.id)
    duration = message.text.split()[1].lower()
    if duration == "навсегда":
        ban_until = "9999-12-31T00:00:00"
    else:
        try:
            days = int(duration)
            ban_until = (datetime.now() + timedelta(days=days)).isoformat()
        except:
            await message.answer("❌ Формат: Бан [дней / навсегда]")
            return
    await db.update_player(target["tg_id"], banned_until=ban_until)
    await message.answer(f"🔨 <b>{target['username']}</b> забанен на {duration}!", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("мут ") and m.reply_to_message)
async def cmd_mute(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not is_mod_or_admin(p):
        await message.answer("❌ Нет прав!")
        return
    target = await get_or_create(message.reply_to_message.from_user.id)
    try:
        parts = message.text.split()
        time_str = parts[1]
        if "ч" in time_str:
            hours = int(time_str.replace("ч", ""))
            mute_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        elif "м" in time_str:
            mins = int(time_str.replace("м", ""))
            mute_until = (datetime.now() + timedelta(minutes=mins)).isoformat()
        else:
            days = int(time_str)
            mute_until = (datetime.now() + timedelta(days=days)).isoformat()
    except:
        await message.answer("❌ Формат: Мут [время, например 1ч / 30м / 1]")
        return
    await db.update_player(target["tg_id"], muted_until=mute_until)
    await message.answer(f"🔇 <b>{target['username']}</b> замьючен!", parse_mode="HTML")

# ─── ADMIN КОМАНДЫ ─────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("выдать "))
async def cmd_give(message: types.Message):
    p = await get_or_create(message.from_user.id)
    parts = message.text.split()

    # Выдать мод / VIP
    if parts[1].lower() == "мод" and is_admin(message.from_user.id):
        try:
            target_id = int(parts[2])
        except:
            await message.answer("❌ Формат: Выдать мод [ID]")
            return
        target = await db.get_player_by_game_id(target_id)
        if not target:
            await message.answer("❌ Игрок не найден!")
            return
        await db.update_player(target["tg_id"], status="moderator")
        await message.answer(f"✅ {target['username']} теперь модератор!")
        return

    if parts[1].lower().startswith("vip") and is_admin(message.from_user.id):
        try:
            vip_level = int(parts[1][3:])
            target_id = int(parts[2])
        except:
            await message.answer("❌ Формат: Выдать VIP1/2/3 [ID]")
            return
        target = await db.get_player_by_game_id(target_id)
        if not target:
            await message.answer("❌ Игрок не найден!")
            return
        await db.update_player(target["tg_id"], vip_level=vip_level)
        await message.answer(f"✅ {target['username']} получил VIP{vip_level}!")
        return

    # Выдать кейс (admin)
    if parts[1].lower() == "кейс" and is_admin(message.from_user.id):
        try:
            target_id = int(parts[2])
        except:
            await message.answer("❌ Формат: Выдать кейс [ID]")
            return
        target = await db.get_player_by_game_id(target_id)
        if not target:
            await message.answer("❌ Игрок не найден!")
            return
        await db.add_inventory_item(target["id"], "case", "5", 1)
        await message.answer(f"✅ Легендарный кейс выдан игроку {target['username']}!")
        try:
            await bot.send_message(target["tg_id"], "🎁 Тебе выдали легендарный кейс!")
        except:
            pass
        return

    # Выдать деньги (admin или VIP)
    try:
        target_id = int(parts[1])
        amount = float(parts[2])
    except:
        await message.answer("❌ Формат: Выдать [ID] [сумма]")
        return

    vip_limits = {1: 50000, 2: 100000, 3: 250000}
    if is_admin(message.from_user.id):
        pass  # no limit
    elif p["vip_level"] > 0:
        limit = vip_limits.get(p["vip_level"], 0)
        # Check 24h cooldown (reuse daily_bonus_date as vip give — in prod use separate field)
        if amount > limit:
            await message.answer(f"❌ Лимит VIP{p['vip_level']}: {fmt(limit)}$")
            return
    else:
        await message.answer("❌ Нет прав!")
        return

    target = await db.get_player_by_game_id(target_id)
    if not target:
        await message.answer("❌ Игрок не найден!")
        return
    await db.update_player(target["tg_id"], balance=target["balance"] + amount)
    await message.answer(f"✅ Выдано <b>{fmt(amount)}$</b> игроку <b>{target['username']}</b>", parse_mode="HTML")

# ─── ПРОМОКОДЫ ─────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower().startswith("создать промокод "))
async def cmd_create_promo(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("❌ Формат: Создать промокод [код] [сумма] [условие/нет]")
        return
    code = parts[2]
    try:
        amount = float(parts[3].split()[0])
    except:
        await message.answer("❌ Неверная сумма!")
        return
    condition = " ".join(parts[3].split()[1:]) if len(parts[3].split()) > 1 else None
    await db.create_promocode(code, amount, condition)
    await message.answer(f"✅ Промокод <b>{code}</b> создан! Сумма: {fmt(amount)}$", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().startswith("промо "))
async def cmd_use_promo(message: types.Message):
    p = await get_or_create(message.from_user.id)
    code = message.text.split()[1]
    promo = await db.get_promocode(code)
    if not promo:
        await message.answer("❌ Промокод не найден!")
        return
    already_used = await db.check_promocode_used(p["id"], code)
    if already_used:
        await message.answer("❌ Ты уже использовал этот промокод!")
        return
    if promo["usage_limit"] and promo["used_count"] >= promo["usage_limit"]:
        await message.answer("❌ Промокод больше не действует!")
        return
    await db.use_promocode(p["id"], code)
    await db.update_player(message.from_user.id, balance=p["balance"] + promo["amount"])
    await message.answer(f"✅ Промокод активирован! Получено: <b>{fmt(promo['amount'])}$</b>", parse_mode="HTML")

# ─── SCHEDULER (лотерея, энергия, питомцы, брак) ───────────

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiosqlite

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", minute=0)
async def lottery_draw():
    tickets = await db.get_all_lottery_tickets()
    if not tickets:
        return
    winner = random.choice(tickets)
    prize = random.randint(10000, 1000000)
    winner_player = await db.get_player_by_game_id(winner["player_id"])
    if winner_player:
        await db.update_player(winner_player["tg_id"], balance=winner_player["balance"] + prize)
        try:
            await bot.send_message(
                winner_player["tg_id"],
                f"🎉 Ты выиграл в лотерею <b>{fmt(prize)}$</b>!",
                parse_mode="HTML"
            )
        except:
            pass
    await db.clear_lottery_tickets()

@scheduler.scheduled_job("interval", minutes=5)
async def restore_energy():
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("UPDATE players SET energy = MIN(100, energy + 1) WHERE energy < 100")
        await conn.commit()

@scheduler.scheduled_job("cron", day_of_week="mon", hour=0, minute=0)
async def pet_weekly_income():
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM pets") as cursor:
            all_pets = await cursor.fetchall()
    for pet_row in all_pets:
        pet_name = pet_row["pet_name"]
        if pet_name in PETS:
            income = PETS[pet_name]["weekly"]
            player = await db.get_player_by_game_id(pet_row["player_id"])
            if player:
                await db.update_player(player["tg_id"], balance=player["balance"] + income)
                try:
                    await bot.send_message(
                        player["tg_id"],
                        f"🐾 Твой питомец <b>{pet_name}</b> принёс <b>{fmt(income)}$</b>!",
                        parse_mode="HTML"
                    )
                except:
                    pass

@scheduler.scheduled_job("interval", hours=1)
async def check_marriage_bonuses():
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM marriages") as cursor:
            marriages = await cursor.fetchall()
    for m in marriages:
        created = parse_dt(m["created_at"])
        if not created:
            continue
        days = (datetime.now() - created).days
        # 7 days bonus
        if days == 7:
            for pid in [m["husband_id"], m["wife_id"]]:
                p = await db.get_player_by_game_id(pid)
                if p:
                    await db.update_player(p["tg_id"], balance=p["balance"] + 1000)
                    try:
                        await bot.send_message(p["tg_id"], "💑 Ваш брак достиг статуса «Близкие люди»! +1.000$", parse_mode="HTML")
                    except:
                        pass
        elif days == 30:
            for pid in [m["husband_id"], m["wife_id"]]:
                p = await db.get_player_by_game_id(pid)
                if p:
                    await db.update_player(p["tg_id"], balance=p["balance"] + 10000)
                    try:
                        await bot.send_message(p["tg_id"], "💞 Ваш брак достиг статуса «Неразлучимые»! +10.000$", parse_mode="HTML")
                    except:
                        pass

# ─── MAIN ──────────────────────────────────────────────────

async def main():
    await db.init_db()
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
