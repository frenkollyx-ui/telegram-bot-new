import os
BOT_TOKEN = "8428272271:AAFI97c1f-OhRT9Up8P_SF2iQhkz_VFwxYQ"

ADMIN_TG_IDS = [8512105562]

RULES = [
    "П1 Запрещено рекламировать без согласия с администрацией.",
    "П2 Запрещено флудить, спамить.",
    "П3 Запрещено оскорблять игроков, родителей игроков или провоцировать на конфликты.",
    "П4 Запрещено попрошайничать деньги.",
    "П5 Запрещено продавать схемы заработка и т.д.",
    "П6 Строго запрещён обман/скам.",
    "П7 Строго запрещён контент 🔞 фото/видео/стикер или другие символы.",
    "П8 Администрация и модерация могут выдать или поменять наказание на своё усмотрение.",
    "П9 Запрещено открывать кейсы в чате, открывать кейсы только в лс бота.",
]

ORES = {
    "уголь":       {"min_exp": 0,      "min": 10,  "max": 1000, "price": 6},
    "железо":      {"min_exp": 1000,   "min": 50,  "max": 100,  "price": 8},
    "медь":        {"min_exp": 5000,   "min": 100, "max": 500,  "price": 7},
    "золото":      {"min_exp": 10000,  "min": 50,  "max": 900,  "price": 10},
    "алмаз":       {"min_exp": 20000,  "min": 10,  "max": 20,   "price": 100},
    "изумруд":     {"min_exp": 25000,  "min": 1,   "max": 7,    "price": 110},
    "аметист":     {"min_exp": 30000,  "min": 1,   "max": 5,    "price": 150},
    "осколки эха": {"min_exp": 50000,  "min": 1,   "max": 3,    "price": 200},
    "сапфир":      {"min_exp": 70000,  "min": 1,   "max": 2,    "price": 300},
    "титан":       {"min_exp": 100000, "min": 1,   "max": 1,    "price": 500},
}

PETS = {
    "кошка":      {"rarity": "epic",      "weekly": 100,   "sell": 2000,  "bonus": "casino"},
    "собака":     {"rarity": "epic",      "weekly": 150,   "sell": 2000,  "bonus": "roulette"},
    "корова":     {"rarity": "epic",      "weekly": 300,   "sell": 2000,  "bonus": None},
    "коза":       {"rarity": "epic",      "weekly": 300,   "sell": 2000,  "bonus": None},
    "овца":       {"rarity": "epic",      "weekly": 300,   "sell": 2000,  "bonus": None},
    "лиса":       {"rarity": "mythic",    "weekly": 500,   "sell": 5000,  "bonus": None},
    "орёл":       {"rarity": "mythic",    "weekly": 800,   "sell": 5000,  "bonus": None},
    "белый барс": {"rarity": "legendary", "weekly": 10000, "sell": 10000, "bonus": "clan_shield"},
    "медведь":    {"rarity": "legendary", "weekly": 15000, "sell": 10000, "bonus": "blackjack"},
    "пума":       {"rarity": "legendary", "weekly": 50000, "sell": 10000, "bonus": None},
}

CASES = {
    1: {"name": "Обычный",     "price": 100,    "buyable": True},
    2: {"name": "Редкий",      "price": 1000,   "buyable": True},
    3: {"name": "Эпический",   "price": 10000,  "buyable": True},
    4: {"name": "Мифический",  "price": 100000, "buyable": True},
    5: {"name": "Легендарный", "price": 0,      "buyable": False},
}
