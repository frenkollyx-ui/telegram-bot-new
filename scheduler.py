import random
from datetime import datetime

from config import PETS
import database as db
from handlers.utils import fmt, parse_dt


def setup_scheduler(scheduler, bot):

    @scheduler.scheduled_job("cron", minute=0)
    async def lottery_draw():
        tickets = await db.get_all_lottery_tickets()
        if not tickets:
            return
        winner = random.choice(tickets)
        prize = random.randint(10000, 1000000)
        wp = await db.get_player_by_game_id(winner["player_id"])
        if wp:
            await db.update_player(wp["tg_id"], balance=wp["balance"] + prize)
            try:
                await bot.send_message(wp["tg_id"], f"🎉 Лотерея! +<b>{fmt(prize)}$</b>!", parse_mode="HTML")
            except:
                pass
        await db.clear_lottery_tickets()

    @scheduler.scheduled_job("interval", minutes=5)
    async def restore_energy():
        conn = await db.get_conn()
        try:
            await conn.execute("UPDATE players SET energy = LEAST(100, energy + 1) WHERE energy < 100")
        finally:
            await conn.close()

    @scheduler.scheduled_job("cron", day_of_week="mon", hour=0, minute=0)
    async def pet_weekly_income():
        conn = await db.get_conn()
        try:
            all_pets = await conn.fetch("SELECT * FROM pets")
        finally:
            await conn.close()
        for pet_row in all_pets:
            pn = pet_row["pet_name"]
            if pn in PETS:
                player = await db.get_player_by_game_id(pet_row["player_id"])
                if player:
                    await db.update_player(player["tg_id"], balance=player["balance"] + PETS[pn]["weekly"])
                    try:
                        await bot.send_message(player["tg_id"], f"🐾 {pn} принёс +<b>{fmt(PETS[pn]['weekly'])}$</b>!", parse_mode="HTML")
                    except:
                        pass

    @scheduler.scheduled_job("interval", hours=1)
    async def marriage_bonuses():
        conn = await db.get_conn()
        try:
            marriages = await conn.fetch("SELECT * FROM marriages")
        finally:
            await conn.close()
        for m in marriages:
            created = parse_dt(m["created_at"])
            if not created:
                continue
            days = (datetime.now() - created).days
            bonus = 1000 if days == 7 else (10000 if days == 30 else 0)
            if bonus:
                for pid in [m["husband_id"], m["wife_id"]]:
                    player = await db.get_player_by_game_id(pid)
                    if player:
                        await db.update_player(player["tg_id"], balance=player["balance"] + bonus)
                        try:
                            await bot.send_message(player["tg_id"], f"💍 Бонус брака: +{fmt(bonus)}$!")
                        except:
                            pass
