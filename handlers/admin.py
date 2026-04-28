from aiogram import Router, F, types
from aiogram.filters import Command
from datetime import datetime, timedelta

from .utils import get_or_create, fmt, now_str, parse_dt, is_admin, is_mod_or_admin
from config import ADMIN_TG_IDS, RULES
import database as db

router = Router()


@router.message(F.text.lower() == "правила")
async def cmd_rules(message: types.Message):
    text = "📜 <b>Правила OPG</b>\n\n" + "\n".join(RULES)
    try:
        await message.bot.send_message(message.from_user.id, text, parse_mode="HTML")
        if message.chat.type != "private":
            await message.answer("📜 Правила отправлены в лс!")
    except:
        await message.answer(text, parse_mode="HTML")


@router.message(F.text.upper().in_({f"П{i}" for i in range(1, 10)}))
async def cmd_rule_single(message: types.Message):
    num = int(message.text[1:])
    if 1 <= num <= len(RULES):
        await message.answer(f"📜 {RULES[num-1]}")


@router.message(Command("report"))
async def cmd_report(message: types.Message):
    p = await get_or_create(message.from_user.id)
    last = parse_dt(p["last_report"])
    if last and datetime.now() - last < timedelta(minutes=10):
        await message.answer("⏳ Раз в 10 минут!")
        return
    args = message.text[7:].strip()
    if not args or not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение и укажи причину: /report [причина]")
        return
    violator = await get_or_create(message.reply_to_message.from_user.id)
    await db.update_player(message.from_user.id, last_report=now_str())
    text = f"🚨 Жалоба от {p['username']}(#{p['id']}) на {violator['username']}(#{violator['id']})\n{args}"
    for aid in ADMIN_TG_IDS:
        try:
            await message.bot.send_message(aid, text)
        except:
            pass
    await message.answer("✅ Жалоба отправлена!")


@router.message(F.text.lower() == "смотреть профиль", F.reply_to_message)
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
    await message.answer(f"👤 ID:{target['id']} | {target['username']}\n💵 {fmt(target['balance'])}$ | 🏰 {clan_name}")


@router.message(F.text.lower().startswith("бан "), F.reply_to_message)
async def cmd_ban(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not is_mod_or_admin(p):
        await message.answer("❌ Нет прав!")
        return
    target = await get_or_create(message.reply_to_message.from_user.id)
    dur = message.text.split()[1].lower()
    bu = "9999-12-31T00:00:00" if dur == "навсегда" else (datetime.now() + timedelta(days=int(dur))).isoformat()
    await db.update_player(target["tg_id"], banned_until=bu)
    await message.answer(f"🔨 {target['username']} забанен на {dur}!")


@router.message(F.text.lower().startswith("мут "), F.reply_to_message)
async def cmd_mute(message: types.Message):
    p = await get_or_create(message.from_user.id)
    if not is_mod_or_admin(p):
        await message.answer("❌ Нет прав!")
        return
    target = await get_or_create(message.reply_to_message.from_user.id)
    ts = message.text.split()[1]
    if "ч" in ts:
        mu = (datetime.now() + timedelta(hours=int(ts.replace("ч", "")))).isoformat()
    elif "м" in ts:
        mu = (datetime.now() + timedelta(minutes=int(ts.replace("м", "")))).isoformat()
    else:
        mu = (datetime.now() + timedelta(days=int(ts))).isoformat()
    await db.update_player(target["tg_id"], muted_until=mu)
    await message.answer(f"🔇 {target['username']} замьючен!")


@router.message(F.text.lower().startswith("выдать "))
async def cmd_give(message: types.Message):
    p = await get_or_create(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Неверный формат!")
        return
    if parts[1].lower() == "мод" and is_admin(message.from_user.id):
        target = await db.get_player_by_game_id(int(parts[2]))
        if target:
            await db.update_player(target["tg_id"], status="moderator")
            await message.answer(f"✅ {target['username']} — модератор!")
        return
    if parts[1].lower().startswith("vip") and is_admin(message.from_user.id):
        vl = int(parts[1][3:])
        target = await db.get_player_by_game_id(int(parts[2]))
        if target:
            await db.update_player(target["tg_id"], vip_level=vl)
            await message.answer(f"✅ {target['username']} VIP{vl}!")
        return
    if parts[1].lower() == "кейс" and is_admin(message.from_user.id):
        target = await db.get_player_by_game_id(int(parts[2]))
        if target:
            await db.add_inventory_item(target["id"], "case", "5", 1)
            await message.answer(f"✅ Легендарный кейс → {target['username']}")
            try:
                await message.bot.send_message(target["tg_id"], "🎁 Тебе выдали легендарный кейс!")
            except:
                pass
        return
    try:
        target_id, amount = int(parts[1]), float(parts[2])
    except:
        await message.answer("❌ Выдать [ID] [сумма]")
        return
    vip_limits = {1: 50000, 2: 100000, 3: 250000}
    if not is_admin(message.from_user.id):
        if p["vip_level"] > 0 and amount > vip_limits.get(p["vip_level"], 0):
            await message.answer(f"❌ Лимит VIP{p['vip_level']}: {fmt(vip_limits[p['vip_level']])}$")
            return
        elif p["vip_level"] == 0:
            await message.answer("❌ Нет прав!")
            return
    target = await db.get_player_by_game_id(target_id)
    if not target:
        await message.answer("❌ Игрок не найден!")
        return
    await db.update_player(target["tg_id"], balance=target["balance"] + amount)
    await message.answer(f"✅ +{fmt(amount)}$ → {target['username']}")


@router.message(F.text.lower().startswith("создать промокод "))
async def cmd_create_promo(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("❌ Создать промокод [код] [сумма] [условие]")
        return
    code = parts[2]
    try:
        amount = float(parts[3].split()[0])
    except:
        await message.answer("❌ Неверная сумма!")
        return
    await db.create_promocode(code, amount)
    await message.answer(f"✅ Промокод <b>{code}</b> создан! {fmt(amount)}$", parse_mode="HTML")


@router.message(F.text.lower().startswith("промо "))
async def cmd_use_promo(message: types.Message):
    p = await get_or_create(message.from_user.id)
    code = message.text.split()[1]
    promo = await db.get_promocode(code)
    if not promo or await db.check_promocode_used(p["id"], code):
        await message.answer("❌ Промокод недействителен или уже использован!")
        return
    await db.use_promocode(p["id"], code)
    await db.update_player(message.from_user.id, balance=p["balance"] + promo["amount"])
    await message.answer(f"✅ +<b>{fmt(promo['amount'])}$</b>!", parse_mode="HTML")
