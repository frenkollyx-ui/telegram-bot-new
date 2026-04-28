import asyncpg
import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_conn()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE,
                username TEXT DEFAULT 'Игрок',
                balance REAL DEFAULT 10000,
                btc REAL DEFAULT 0,
                bank REAL DEFAULT 0,
                deposit REAL DEFAULT 0,
                deposit_initial REAL DEFAULT 0,
                deposit_date TEXT DEFAULT NULL,
                energy INTEGER DEFAULT 100,
                exp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                clan_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'player',
                gender TEXT DEFAULT NULL,
                spouse_id INTEGER DEFAULT NULL,
                banned_until TEXT DEFAULT NULL,
                muted_until TEXT DEFAULT NULL,
                daily_bonus_date TEXT DEFAULT NULL,
                last_casino TEXT DEFAULT NULL,
                last_roulette TEXT DEFAULT NULL,
                last_blackjack TEXT DEFAULT NULL,
                last_duel TEXT DEFAULT NULL,
                last_safe TEXT DEFAULT NULL,
                last_coins TEXT DEFAULT NULL,
                last_report TEXT DEFAULT NULL,
                last_war TEXT DEFAULT NULL,
                vip_level INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                player_id INTEGER,
                item_type TEXT,
                item_name TEXT,
                quantity INTEGER DEFAULT 0,
                UNIQUE(player_id, item_type, item_name)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                owner_id INTEGER,
                treasury REAL DEFAULT 0,
                rating INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                player_id INTEGER,
                PRIMARY KEY (clan_id, player_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS marriages (
                id SERIAL PRIMARY KEY,
                husband_id INTEGER,
                wife_id INTEGER,
                created_at TEXT,
                children INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id SERIAL PRIMARY KEY,
                marriage_id INTEGER,
                name TEXT,
                gender TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id SERIAL PRIMARY KEY,
                player_id INTEGER,
                quantity INTEGER DEFAULT 0,
                bought_at TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE,
                amount REAL,
                condition TEXT DEFAULT NULL,
                usage_limit INTEGER DEFAULT NULL,
                used_count INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promocode_usage (
                player_id INTEGER,
                code TEXT,
                PRIMARY KEY (player_id, code)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id SERIAL PRIMARY KEY,
                player_id INTEGER UNIQUE,
                level INTEGER DEFAULT 1,
                last_collect TEXT DEFAULT NULL,
                taxes REAL DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id SERIAL PRIMARY KEY,
                player_id INTEGER UNIQUE,
                level INTEGER DEFAULT 1,
                last_collect TEXT DEFAULT NULL,
                taxes REAL DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clan_wars (
                id SERIAL PRIMARY KEY,
                challenger_clan INTEGER,
                defender_clan INTEGER,
                started_at TEXT,
                winner_clan INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending',
                word TEXT DEFAULT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id SERIAL PRIMARY KEY,
                player_id INTEGER,
                pet_name TEXT,
                last_income TEXT DEFAULT NULL,
                UNIQUE(player_id, pet_name)
            )
        """)
    finally:
        await conn.close()


# ─── PLAYERS ───────────────────────────────────────────────

async def get_player(tg_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM players WHERE tg_id = $1", tg_id)
    finally:
        await conn.close()

async def get_player_by_game_id(game_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM players WHERE id = $1", game_id)
    finally:
        await conn.close()

async def create_player(tg_id: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO players (tg_id) VALUES ($1) ON CONFLICT (tg_id) DO NOTHING", tg_id
        )
    finally:
        await conn.close()
    return await get_player(tg_id)

async def update_player(tg_id: int, **kwargs):
    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    values = [tg_id] + list(kwargs.values())
    conn = await get_conn()
    try:
        await conn.execute(f"UPDATE players SET {fields} WHERE tg_id = $1", *values)
    finally:
        await conn.close()

async def get_top_players(by: str = "balance", limit: int = 10):
    col = {"balance": "balance", "btc": "btc"}.get(by, "balance")
    conn = await get_conn()
    try:
        return await conn.fetch(f"SELECT * FROM players ORDER BY {col} DESC LIMIT $1", limit)
    finally:
        await conn.close()


# ─── INVENTORY ─────────────────────────────────────────────

async def get_inventory(player_id: int):
    conn = await get_conn()
    try:
        return await conn.fetch("SELECT * FROM inventory WHERE player_id = $1", player_id)
    finally:
        await conn.close()

async def add_inventory_item(player_id: int, item_type: str, item_name: str, quantity: int = 1):
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO inventory (player_id, item_type, item_name, quantity)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (player_id, item_type, item_name)
            DO UPDATE SET quantity = inventory.quantity + $4
        """, player_id, item_type, item_name, quantity)
    finally:
        await conn.close()

async def remove_inventory_item(player_id: int, item_type: str, item_name: str, quantity: int = 1):
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT quantity FROM inventory WHERE player_id = $1 AND item_type = $2 AND item_name = $3",
            player_id, item_type, item_name
        )
        if not row or row["quantity"] < quantity:
            return False
        new_qty = row["quantity"] - quantity
        if new_qty <= 0:
            await conn.execute(
                "DELETE FROM inventory WHERE player_id = $1 AND item_type = $2 AND item_name = $3",
                player_id, item_type, item_name
            )
        else:
            await conn.execute(
                "UPDATE inventory SET quantity = $1 WHERE player_id = $2 AND item_type = $3 AND item_name = $4",
                new_qty, player_id, item_type, item_name
            )
        return True
    finally:
        await conn.close()

async def get_inventory_item(player_id: int, item_type: str, item_name: str):
    conn = await get_conn()
    try:
        return await conn.fetchrow(
            "SELECT * FROM inventory WHERE player_id = $1 AND item_type = $2 AND item_name = $3",
            player_id, item_type, item_name
        )
    finally:
        await conn.close()


# ─── CLANS ─────────────────────────────────────────────────

async def get_clan(clan_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM clans WHERE id = $1", clan_id)
    finally:
        await conn.close()

async def get_clan_by_name(name: str):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM clans WHERE name = $1", name)
    finally:
        await conn.close()

async def create_clan(name: str, owner_id: int):
    conn = await get_conn()
    try:
        await conn.execute("INSERT INTO clans (name, owner_id) VALUES ($1, $2)", name, owner_id)
    finally:
        await conn.close()
    return await get_clan_by_name(name)

async def update_clan(clan_id: int, **kwargs):
    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    values = [clan_id] + list(kwargs.values())
    conn = await get_conn()
    try:
        await conn.execute(f"UPDATE clans SET {fields} WHERE id = $1", *values)
    finally:
        await conn.close()

async def get_top_clans(limit: int = 10):
    conn = await get_conn()
    try:
        return await conn.fetch("SELECT * FROM clans ORDER BY rating DESC LIMIT $1", limit)
    finally:
        await conn.close()

async def get_clan_members(clan_id: int):
    conn = await get_conn()
    try:
        return await conn.fetch(
            "SELECT p.* FROM players p JOIN clan_members cm ON p.id = cm.player_id WHERE cm.clan_id = $1",
            clan_id
        )
    finally:
        await conn.close()

async def add_clan_member(clan_id: int, player_id: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO clan_members (clan_id, player_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            clan_id, player_id
        )
    finally:
        await conn.close()

async def remove_clan_member(clan_id: int, player_id: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "DELETE FROM clan_members WHERE clan_id = $1 AND player_id = $2", clan_id, player_id
        )
    finally:
        await conn.close()


# ─── MARRIAGES ─────────────────────────────────────────────

async def get_marriage(player_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow(
            "SELECT * FROM marriages WHERE husband_id = $1 OR wife_id = $1", player_id
        )
    finally:
        await conn.close()

async def create_marriage(husband_id: int, wife_id: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO marriages (husband_id, wife_id, created_at) VALUES ($1, $2, $3)",
            husband_id, wife_id, datetime.now().isoformat()
        )
    finally:
        await conn.close()

async def get_children(marriage_id: int):
    conn = await get_conn()
    try:
        return await conn.fetch("SELECT * FROM children WHERE marriage_id = $1", marriage_id)
    finally:
        await conn.close()

async def add_child(marriage_id: int, name: str, gender: str):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO children (marriage_id, name, gender) VALUES ($1, $2, $3)",
            marriage_id, name, gender
        )
        await conn.execute(
            "UPDATE marriages SET children = children + 1 WHERE id = $1", marriage_id
        )
    finally:
        await conn.close()

async def delete_last_child(marriage_id: int):
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT id FROM children WHERE marriage_id = $1 ORDER BY id DESC LIMIT 1", marriage_id
        )
        if row:
            await conn.execute("DELETE FROM children WHERE id = $1", row["id"])
            await conn.execute(
                "UPDATE marriages SET children = children - 1 WHERE id = $1", marriage_id
            )
    finally:
        await conn.close()


# ─── LOTTERY ───────────────────────────────────────────────

async def add_lottery_tickets(player_id: int, quantity: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO lottery_tickets (player_id, quantity, bought_at) VALUES ($1, $2, $3)",
            player_id, quantity, datetime.now().isoformat()
        )
    finally:
        await conn.close()

async def get_all_lottery_tickets():
    conn = await get_conn()
    try:
        return await conn.fetch("SELECT * FROM lottery_tickets")
    finally:
        await conn.close()

async def clear_lottery_tickets():
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM lottery_tickets")
    finally:
        await conn.close()


# ─── PROMOCODES ────────────────────────────────────────────

async def create_promocode(code: str, amount: float, condition: str = None, limit: int = None):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO promocodes (code, amount, condition, usage_limit) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
            code, amount, condition, limit
        )
    finally:
        await conn.close()

async def get_promocode(code: str):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM promocodes WHERE code = $1", code)
    finally:
        await conn.close()

async def use_promocode(player_id: int, code: str):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO promocode_usage (player_id, code) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            player_id, code
        )
        await conn.execute(
            "UPDATE promocodes SET used_count = used_count + 1 WHERE code = $1", code
        )
    finally:
        await conn.close()

async def check_promocode_used(player_id: int, code: str):
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM promocode_usage WHERE player_id = $1 AND code = $2", player_id, code
        )
        return row is not None
    finally:
        await conn.close()


# ─── BUSINESS & FARM ───────────────────────────────────────

async def get_business(player_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM businesses WHERE player_id = $1", player_id)
    finally:
        await conn.close()

async def create_business(player_id: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO businesses (player_id, last_collect) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            player_id, datetime.now().isoformat()
        )
    finally:
        await conn.close()

async def update_business(player_id: int, **kwargs):
    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    values = [player_id] + list(kwargs.values())
    conn = await get_conn()
    try:
        await conn.execute(f"UPDATE businesses SET {fields} WHERE player_id = $1", *values)
    finally:
        await conn.close()

async def get_farm(player_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow("SELECT * FROM farms WHERE player_id = $1", player_id)
    finally:
        await conn.close()

async def create_farm(player_id: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO farms (player_id, last_collect) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            player_id, datetime.now().isoformat()
        )
    finally:
        await conn.close()

async def update_farm(player_id: int, **kwargs):
    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    values = [player_id] + list(kwargs.values())
    conn = await get_conn()
    try:
        await conn.execute(f"UPDATE farms SET {fields} WHERE player_id = $1", *values)
    finally:
        await conn.close()


# ─── PETS ──────────────────────────────────────────────────

async def get_pets(player_id: int):
    conn = await get_conn()
    try:
        return await conn.fetch("SELECT * FROM pets WHERE player_id = $1", player_id)
    finally:
        await conn.close()

async def get_pet(player_id: int, pet_name: str):
    conn = await get_conn()
    try:
        return await conn.fetchrow(
            "SELECT * FROM pets WHERE player_id = $1 AND pet_name = $2", player_id, pet_name
        )
    finally:
        await conn.close()

async def add_pet(player_id: int, pet_name: str):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO pets (player_id, pet_name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            player_id, pet_name
        )
    finally:
        await conn.close()

async def remove_pet(player_id: int, pet_name: str):
    conn = await get_conn()
    try:
        await conn.execute(
            "DELETE FROM pets WHERE player_id = $1 AND pet_name = $2", player_id, pet_name
        )
    finally:
        await conn.close()

async def update_pet(player_id: int, pet_name: str, **kwargs):
    fields = ", ".join(f"{k} = ${i+3}" for i, k in enumerate(kwargs))
    values = [player_id, pet_name] + list(kwargs.values())
    conn = await get_conn()
    try:
        await conn.execute(
            f"UPDATE pets SET {fields} WHERE player_id = $1 AND pet_name = $2", *values
        )
    finally:
        await conn.close()


# ─── CLAN WARS ─────────────────────────────────────────────

async def create_clan_war(challenger: int, defender: int, word: str):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO clan_wars (challenger_clan, defender_clan, started_at, word) VALUES ($1, $2, $3, $4)",
            challenger, defender, datetime.now().isoformat(), word
        )
    finally:
        await conn.close()

async def get_active_war(clan_id: int):
    conn = await get_conn()
    try:
        return await conn.fetchrow(
            "SELECT * FROM clan_wars WHERE (challenger_clan = $1 OR defender_clan = $1) AND status = 'pending'",
            clan_id
        )
    finally:
        await conn.close()

async def finish_war(war_id: int, winner_clan: int):
    conn = await get_conn()
    try:
        await conn.execute(
            "UPDATE clan_wars SET status = 'finished', winner_clan = $1 WHERE id = $2",
            winner_clan, war_id
        )
    finally:
        await conn.close()
