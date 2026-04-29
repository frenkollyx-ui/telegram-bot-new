from aiogram import Router, F, types
from aiogram.filters import Command
from datetime import datetime

from .utils import get_or_create, fmt, now_str, parse_dt
import database as db

router = Router()

pending_nick = {}

HELP_TEXT = """📋 <b>ВСЕ КОМАНДЫ OPG БОТА:</b>

👤 Профиль | Б | Баланс | Инвентарь | Поменять ник
🏦 Банк положить/снять [сумма]
💼 Депозит | Депозит положить/снять [сумма]
⛏️ Копать [руда] | Продать [руда] [кол-во]
🎰 Казино/Рулетка/Блэкджек [ставка]
🎟 Купить билет [кол-во]
🎁 Кейсы | Купить кейс [1-4] [кол-во] | Открыть кейс [1-5]
🏰 Создать клан [название] | Казна клана [сумма]
🏰 Клан пригласить/передать [ID] | Клан топ
⚔️ Дуэль (в ответ) | Взломать сейф
🪙 Найти монетки | Ежедневный бонус
💍 Брак [ID] | Мой брак | Брак кекс
🏢 Построить бизнес/ферму | Мой бизнес | Моя ферма
🐾 Продать пет [название]
📜 Правила | П1-П9 | /report [причина]
🏆 Топ | Топ btc | Клан топ"""


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await get_or_create(message.from_user.id)
    await message.answer(
        "🎮 Добро пожаловать в <b>OPG бот</b>!\n\n"
        "Тут ты сможешь играть с людьми, создать или вступить в клан. "
        "Наполняй казну клана деньгами чтобы добраться до топ-1. "
        "Активируй промокоды, открывай кейсы, вступай в брак, возьми ребёнка.\n\n"
        "Если не знаешь что делать — вступай в наш чат:\nhttps://t.me/+1YBeN8EFk9c5YjUy",
        parse_mode="HTML"
    )


@router.message(F.text.lower().in_({"помощь", "help"}))
async def cmd_help(message: types.Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(F.text.lower().in_({"б", "баланс"}))
async def cmd_balance(message: types.Message):
    p = await get_or_create(message.from_user.id)
    await message.answer(
        f"💰 <b>Баланс</b>\n\n💵 {fmt(p['balance'])}$\n₿ {p['btc']:.6f} BTC\n🏦 Банк: {fmt(p['bank'])}$",
        parse_mode="HTML"
    )


@router.message(F.text.lower() == "профиль")
async def cmd_profile(message: types.Message):
    p = await get_or_create(message.from_user.id)
    clan_name = "—"
    if p["clan_id"]:
        clan = await db.get_clan(p["clan_id"])
        if clan:
            clan_name = clan["name"]
    marriage = await db.get_marriage(p["id"])
    spouse_str = "—"
    if marriage:
        sid = marriage["wife_id"] if marriage["husband_id"] == p["id"] else marriage["husband_id"]
        sp = await db.get_player_by_game_id(sid)
        if sp:
            spouse_str = f"{sp['username']} (#{sid})"
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
        f"👤 <b>{p['username']}</b>\n\n🆔 ID: {p['id']}\n💵 {fmt(p['balance'])}$\n₿ {p['btc']:.6f}\n"
        f"🏦 Банк: {fmt(p['bank'])}$\n🏰 Клан: {clan_name}\n🪙 Монетки: {coins}\n🎁 Кейсов: {cases_count}\n"
        f"🐾 {pets_str}\n⚡ Энергия: {p['energy']}/100\n⭐ Опыт: {p['exp']}\n💍 {spouse_str}\n🎖 {status_str}",
        parse_mode="HTML"
    )


@router.message(F.text.lower() == "поменять ник")
async def cmd_change_nick(message: types.Message):
    pending_nick[message.from_user.id] = True
    await message.answer("✏️ Введи новый ник (5–25 символов):")


@router.message(F.text.lower() == "инвентарь")
async def cmd_inventory(message: types.Message):
    p = await get_or_create(message.from_user.id)
    inv = await db.get_inventory(p["id"])
    coins = next((i["quantity"] for i in inv if i["item_type"] == "coins"), 0)
    cases = {i["item_name"]: i["quantity"] for i in inv if i["item_type"] == "case"}
    ores = {i["item_name"]: i["quantity"] for i in inv if i["item_type"] == "ore"}
    pets = await db.get_pets(p["id"])
    ores_str = "\n".join(f"  • {k}: {v}" for k, v in ores.items()) or "  —"
    cases_str = "\n".join(f"  • Кейс {k}: {v}" for k, v in cases.items()) or "  —"
    pets_str = "\n".join(f"  • {pet['pet_name']}" for pet in pets) or "  —"
    await message.answer(
        f"🎒 <b>Инвентарь</b>\n\n🪙 Монетки: {coins}\n\n⛏️ Руда:\n{ores_str}\n\n🎁 Кейсы:\n{cases_str}\n\n🐾 Питомцы:\n{pets_str}",
        parse_mode="HTML"
    )


@router.message(F.text.lower() == "топ")
async def cmd_top(message: types.Message):
    players = await db.get_top_players("balance", 10)
    text = "🏆 <b>Топ по балансу</b>\n\n" + "\n".join(
        f"{i}. <b>{p['username']}</b> — {fmt(p['balance'])}$" for i, p in enumerate(players, 1))
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.lower() == "топ btc")
async def cmd_top_btc(message: types.Message):
    players = await db.get_top_players("btc", 10)
    text = "🏆 <b>Топ по BTC</b>\n\n" + "\n".join(
        f"{i}. <b>{p['username']}</b> — {p['btc']:.6f}" for i, p in enumerate(players, 1))
    await message.answer(text, parse_mode="HTML") @router.message(F.text)
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
