from datetime import datetime
import database as db
from config import ADMIN_TG_IDS

def fmt(n):
    return f"{n:,.0f}".replace(",", ".")

def now_str():
    return datetime.now().isoformat()

def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except:
        return None

async def get_or_create(tg_id):
    p = await db.get_player(tg_id)
    if not p:
        p = await db.create_player(tg_id)
    return p

def is_admin(tg_id):
    return tg_id in ADMIN_TG_IDS

def is_mod_or_admin(player):
    return player["status"] in ("admin", "moderator") or player["tg_id"] in ADMIN_TG_IDS
