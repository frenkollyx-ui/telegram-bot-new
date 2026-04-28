import aiosqlite
import asyncio
from datetime import datetime

DB_PATH = "opg.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                item_type TEXT,
                item_name TEXT,
                quantity INTEGER DEFAULT 0,
                UNIQUE(player_id, item_type, item_name)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                treasury REAL DEFAULT 0,
                rating INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER,
                player_id INTEGER,
                PRIMARY KEY (clan_id, player_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS marriages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                husband_id INTEGER,
                wife_id INTEGER,
                created_at TEXT,
                children INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marriage_id INTEGER,
                name TEXT,
                gender TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                quantity INTEGER DEFAULT 0,
                bought_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                amount REAL,
                condition TEXT DEFAULT NULL,
                usage_limit INTEGER DEFAULT NULL,
                used_count INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocode_usage (
                player_id INTEGER,
                code TEXT,
                PRIMARY KEY (player_id, code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER UNIQUE,
                level INTEGER DEFAULT 1,
                last_collect TEXT DEFAULT NULL,
                taxes REAL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER UNIQUE,
                level INTEGER DEFAULT 1,
                last_collect TEXT DEFAULT NULL,
                taxes REAL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_clan INTEGER,
                defender_clan INTEGER,
                started_at TEXT,
                winner_clan INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending',
                word TEXT DEFAULT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                pet_name TEXT,
                last_income TEXT DEFAULT NULL,
                UNIQUE(player_id, pet_name)
            )
        """)

        await db.commit()


# ─── PLAYERS ───────────────────────────────────────────────

async def get_player(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,)) as cursor:
            return await cursor.fetchone()

async def get_player_by_game_id(game_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players WHERE id = ?", (game_id,)) as cursor:
            return await cursor.fetchone()

async def create_player(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO players (tg_id) VALUES (?)", (tg_id,)
        )
        await db.commit()
    return await get_player(tg_id)

async def update_player(tg_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [tg_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE players SET {fields} WHERE tg_id = ?", values)
        await db.commit()

async def get_top_players(by: str = "balance", limit: int = 10):
    col = {"balance": "balance", "btc": "btc"}.get(by, "balance")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"SELECT * FROM players ORDER BY {col} DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()


# ─── INVENTORY ─────────────────────────────────────────────

async def get_inventory(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM inventory WHERE player_id = ?", (player_id,)) as cursor:
            return await cursor.fetchall()

async def add_inventory_item(player_id: int, item_type: str, item_name: str, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO inventory (player_id, item_type, item_name, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id, item_type, item_name)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (player_id, item_type, item_name, quantity))
        await db.commit()

async def remove_inventory_item(player_id: int, item_type: str, item_name: str, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT quantity FROM inventory WHERE player_id = ? AND item_type = ? AND item_name = ?",
            (player_id, item_type, item_name)
        ) as cursor:
            row = await cursor.fetchone()
        if not row or row["quantity"] < quantity:
            return False
        new_qty = row["quantity"] - quantity
        if new_qty <= 0:
            await db.execute(
                "DELETE FROM inventory WHERE player_id = ? AND item_type = ? AND item_name = ?",
                (player_id, item_type, item_name)
            )
        else:
            await db.execute(
                "UPDATE inventory SET quantity = ? WHERE player_id = ? AND item_type = ? AND item_name = ?",
                (new_qty, player_id, item_type, item_name)
            )
        await db.commit()
        return True

async def get_inventory_item(player_id: int, item_type: str, item_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM inventory WHERE player_id = ? AND item_type = ? AND item_name = ?",
            (player_id, item_type, item_name)
        ) as cursor:
            return await cursor.fetchone()


# ─── CLANS ─────────────────────────────────────────────────

async def get_clan(clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)) as cursor:
            return await cursor.fetchone()

async def get_clan_by_name(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM clans WHERE name = ?", (name,)) as cursor:
            return await cursor.fetchone()

async def create_clan(name: str, owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO clans (name, owner_id) VALUES (?, ?)", (name, owner_id)
        )
        await db.commit()
    return await get_clan_by_name(name)

async def update_clan(clan_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [clan_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE clans SET {fields} WHERE id = ?", values)
        await db.commit()

async def get_top_clans(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM clans ORDER BY rating DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

async def get_clan_members(clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.* FROM players p JOIN clan_members cm ON p.id = cm.player_id WHERE cm.clan_id = ?",
            (clan_id,)
        ) as cursor:
            return await cursor.fetchall()

async def add_clan_member(clan_id: int, player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO clan_members (clan_id, player_id) VALUES (?, ?)",
            (clan_id, player_id)
        )
        await db.commit()

async def remove_clan_member(clan_id: int, player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM clan_members WHERE clan_id = ? AND player_id = ?",
            (clan_id, player_id)
        )
        await db.commit()


# ─── MARRIAGES ─────────────────────────────────────────────

async def get_marriage(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM marriages WHERE husband_id = ? OR wife_id = ?",
            (player_id, player_id)
        ) as cursor:
            return await cursor.fetchone()

async def create_marriage(husband_id: int, wife_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO marriages (husband_id, wife_id, created_at) VALUES (?, ?, ?)",
            (husband_id, wife_id, datetime.now().isoformat())
        )
        await db.commit()

async def get_children(marriage_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM children WHERE marriage_id = ?", (marriage_id,)) as cursor:
            return await cursor.fetchall()

async def add_child(marriage_id: int, name: str, gender: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO children (marriage_id, name, gender) VALUES (?, ?, ?)",
            (marriage_id, name, gender)
        )
        await db.execute(
            "UPDATE marriages SET children = children + 1 WHERE id = ?", (marriage_id,)
        )
        await db.commit()

async def delete_last_child(marriage_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM children WHERE marriage_id = ? ORDER BY id DESC LIMIT 1", (marriage_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            await db.execute("DELETE FROM children WHERE id = ?", (row[0],))
            await db.execute(
                "UPDATE marriages SET children = children - 1 WHERE id = ?", (marriage_id,)
            )
            await db.commit()


# ─── LOTTERY ───────────────────────────────────────────────

async def add_lottery_tickets(player_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO lottery_tickets (player_id, quantity, bought_at) VALUES (?, ?, ?)",
            (player_id, quantity, datetime.now().isoformat())
        )
        await db.commit()

async def get_all_lottery_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lottery_tickets") as cursor:
            return await cursor.fetchall()

async def clear_lottery_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM lottery_tickets")
        await db.commit()


# ─── PROMOCODES ────────────────────────────────────────────

async def create_promocode(code: str, amount: float, condition: str = None, limit: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO promocodes (code, amount, condition, usage_limit) VALUES (?, ?, ?, ?)",
            (code, amount, condition, limit)
        )
        await db.commit()

async def get_promocode(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promocodes WHERE code = ?", (code,)) as cursor:
            return await cursor.fetchone()

async def use_promocode(player_id: int, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO promocode_usage (player_id, code) VALUES (?, ?)",
            (player_id, code)
        )
        await db.execute(
            "UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code,)
        )
        await db.commit()

async def check_promocode_used(player_id: int, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM promocode_usage WHERE player_id = ? AND code = ?",
            (player_id, code)
        ) as cursor:
            return await cursor.fetchone() is not None


# ─── BUSINESS & FARM ───────────────────────────────────────

async def get_business(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM businesses WHERE player_id = ?", (player_id,)) as cursor:
            return await cursor.fetchone()

async def create_business(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO businesses (player_id, last_collect) VALUES (?, ?)",
            (player_id, datetime.now().isoformat())
        )
        await db.commit()

async def update_business(player_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [player_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE businesses SET {fields} WHERE player_id = ?", values)
        await db.commit()

async def get_farm(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM farms WHERE player_id = ?", (player_id,)) as cursor:
            return await cursor.fetchone()

async def create_farm(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO farms (player_id, last_collect) VALUES (?, ?)",
            (player_id, datetime.now().isoformat())
        )
        await db.commit()

async def update_farm(player_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [player_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE farms SET {fields} WHERE player_id = ?", values)
        await db.commit()


# ─── PETS ──────────────────────────────────────────────────

async def get_pets(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pets WHERE player_id = ?", (player_id,)) as cursor:
            return await cursor.fetchall()

async def get_pet(player_id: int, pet_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pets WHERE player_id = ? AND pet_name = ?", (player_id, pet_name)
        ) as cursor:
            return await cursor.fetchone()

async def add_pet(player_id: int, pet_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO pets (player_id, pet_name) VALUES (?, ?)",
            (player_id, pet_name)
        )
        await db.commit()

async def remove_pet(player_id: int, pet_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM pets WHERE player_id = ? AND pet_name = ?", (player_id, pet_name)
        )
        await db.commit()

async def update_pet(player_id: int, pet_name: str, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [player_id, pet_name]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE pets SET {fields} WHERE player_id = ? AND pet_name = ?", values
        )
        await db.commit()


# ─── CLAN WARS ─────────────────────────────────────────────

async def create_clan_war(challenger: int, defender: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO clan_wars (challenger_clan, defender_clan, started_at, word) VALUES (?, ?, ?, ?)",
            (challenger, defender, datetime.now().isoformat(), word)
        )
        await db.commit()

async def get_active_war(clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clan_wars WHERE (challenger_clan = ? OR defender_clan = ?) AND status = 'pending'",
            (clan_id, clan_id)
        ) as cursor:
            return await cursor.fetchone()

async def finish_war(war_id: int, winner_clan: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clan_wars SET status = 'finished', winner_clan = ? WHERE id = ?",
            (winner_clan, war_id)
        )
        await db.commit()
