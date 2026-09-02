import asyncio
import logging
import random
import sqlite3
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

conn = sqlite3.connect("femboy_farm.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    coins INTEGER DEFAULT 100,
    last_farm TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    tg_id INTEGER,
    femboy_name TEXT,
    rarity TEXT,
    income INTEGER,
    PRIMARY KEY (tg_id, femboy_name)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    tg_id INTEGER PRIMARY KEY
)
""")

for admin_id in ADMIN_IDS:
    cursor.execute("INSERT OR IGNORE INTO admins (tg_id) VALUES (?)", (admin_id,))

cursor.execute("UPDATE users SET coins = 100 WHERE coins = 0")
conn.commit()

ALL_FEMBOYS = [
    # ===== ОБЫЧНЫЕ (50 доход, цена 100) =====
    {"name": "Xingqiu", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Saika Totsuka", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Nagisa Shiota", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Chihiro Fujisaki", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Gasper Vladi", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Suzuya Juzo", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Freminet", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Alois Trancy", "rarity": "Обычный", "income": 50, "price": 100},

    # ===== НЕОБЫЧНЫЕ (100 доход, цена 300) =====
    {"name": "Hideri Kanzaki", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Ruka Urushibara", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Haku", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Tetora", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Lyney", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Narancia Ghirga", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Gowther", "rarity": "Необычный", "income": 100, "price": 300},

    # ===== РЕДКИЕ (200 доход, цена 600) =====
    {"name": "Sneaky", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "BoxBox", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "YOHIO", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Bridget", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Mizuki Akiyama", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Chevalier d'Eon", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Lanling Wang", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Rimuru Tempest", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Kurama", "rarity": "Редкий", "income": 200, "price": 600},
    {"name": "Asuka Kudou", "rarity": "Редкий", "income": 200, "price": 600},

    # ===== ЭПИЧЕСКИЕ (400 доход, цена 1000) =====
    {"name": "Line", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Hana Macchia", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Syo", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Maruruk", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Totsugeki", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Wanderer", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Ciel (Robin Outfit)", "rarity": "Эпический", "income": 400, "price": 1000},

    # ===== ЛЕГЕНДАРНЫЕ (700 доход, цена 2000) =====
    {"name": "Astolfo", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Felix Argyle", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Venti", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "F1nn5ter", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Astellas", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Babo", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Mikazuki", "rarity": "Легендарный", "income": 700, "price": 2000},

    # ===== МИФИЧЕСКАЯ (МОЖНО КУПИТЬ, 10,000 монет) =====
    {"name": "Тофик", "rarity": "Мифический", "income": 5000, "price": 10000},
]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


def get_rarity_emoji(rarity):
    emojis = {
        "Обычный": "⬜",
        "Необычный": "🟦",
        "Редкий": "🟪",
        "Эпический": "✨",
        "Легендарный": "👑",
        "Мифический": "🌟"
    }
    return emojis.get(rarity, "⬜")


def is_owned(user_id, femboy_name):
    cursor.execute("SELECT 1 FROM inventory WHERE tg_id = ? AND femboy_name = ?", (user_id, femboy_name))
    return cursor.fetchone() is not None


def find_femboy(name):
    for f in ALL_FEMBOYS:
        if f["name"] == name:
            return f
    return None


def user_exists(user_id):
    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (user_id,))
    return cursor.fetchone() is not None


def ensure_user_registered(user_id):
    """Проверяет, зарегистрирован ли пользователь. Если нет — добавляет."""
    if not user_exists(user_id):
        cursor.execute("INSERT INTO users (tg_id, coins) VALUES (?, 100)", (user_id,))
        conn.commit()
        return False  # Только что зарегистрирован
    return True  # Уже был


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO users (tg_id, coins) VALUES (?, 100)", (user_id,))
        conn.commit()
        coins = 100
    else:
        if result[0] == 0:
            cursor.execute("UPDATE users SET coins = 100 WHERE tg_id = ?", (user_id,))
            conn.commit()
            coins = 100
        else:
            coins = result[0]
    await message.answer(
        f"🌸 **Добро пожаловать в Femboy Farm!**\n\n"
        f"💰 Твой баланс: **{coins}** монет\n\n"
        "📋 **Команды:**\n"
        "`Фарма` — собрать доход (1 раз в час)\n"
        "/shop — обычный магазин\n"
        "/dailyshop — ежедневный магазин\n"
        "/my — посмотреть свою ферму\n"
        "/coins — баланс\n"
        "/top — топ игроков\n\n"
        "⭐ **Редкости:**\n"
        f"{get_rarity_emoji('Обычный')} Обычный — 50 доход (100 монет)\n"
        f"{get_rarity_emoji('Необычный')} Необычный — 100 доход (300 монет)\n"
        f"{get_rarity_emoji('Редкий')} Редкий — 200 доход (600 монет)\n"
        f"{get_rarity_emoji('Эпический')} Эпический — 400 доход (1000 монет)\n"
        f"{get_rarity_emoji('Легендарный')} Легендарный — 700 доход (2000 монет)\n"
        f"{get_rarity_emoji('Мифический')} Мифический — 5000 доход (10000 монет)\n\n"
        "👑 **Админ-команды:**\n"
        "/help_admin — список админ-команд",
        parse_mode="Markdown"
    )


@dp.message_handler(commands=["help_admin"])
async def help_admin(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ У тебя нет прав администратора!")
        return
    
    text = "👑 **Админ-команды:**\n\n"
    text += "💰 **Монеты:**\n"
    text += "/addcoins_id `123456789 500` — начислить по ID\n"
    text += "/removecoins_id `123456789 200` — снять по ID\n"
    text += "/reset_coins_id `123456789` — сбросить баланс до 100\n\n"
    text += "🌟 **Карты:**\n"
    text += "/give_tofik_id `123456789` — выдать Тофика по ID\n\n"
    text += "👑 **Админы:**\n"
    text += "/giveadmin_id `123456789` — выдать админку по ID\n"
    text += "/removeadmin_id `123456789` — забрать админку по ID\n\n"
    text += "🗑️ **Сброс:**\n"
    text += "/reset_inventory_id `123456789` — очистить инвентарь\n\n"
    text += "📊 **Инфо:**\n"
    text += "/user_info_id `123456789` — инфо о пользователе\n"
    text += "/all_users — список всех пользователей\n\n"
    text += "❓ Чтобы узнать свой ID — напиши @userinfobot"
    
    await message.answer(text, parse_mode="Markdown")


@dp.message_handler(lambda msg: msg.text and msg.text.lower() == "фарма")
async def farm_text(message: types.Message):
    user_id = message.from_user.id
    
    # Проверка: зарегистрирован ли пользователь
    if not user_exists(user_id):
        await message.answer("🌸 **Сначала запусти бота!**\nНапиши `/start` в личку бота, чтобы зарегистрироваться.")
        return
    
    cursor.execute("SELECT last_farm FROM users WHERE tg_id = ?", (user_id,))
    result = cursor.fetchone()
    last_farm = result[0] if result else None
    if last_farm:
        last_time = datetime.strptime(last_farm, "%Y-%m-%d %H:%M:%S")
        if datetime.now() - last_time < timedelta(hours=1):
            remaining = timedelta(hours=1) - (datetime.now() - last_time)
            minutes = int(remaining.total_seconds() // 60)
            await message.answer(f"⏳ Подожди **{minutes}** минут!")
            return
    cursor.execute("SELECT SUM(income) FROM inventory WHERE tg_id = ?", (user_id,))
    total_income = cursor.fetchone()[0] or 0
    if total_income == 0:
        await message.answer("😢 У тебя нет фембоев! Купи в /shop или /dailyshop")
        return
    cursor.execute("UPDATE users SET coins = coins + ?, last_farm = ? WHERE tg_id = ?",
                   (total_income, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    await message.answer(
        f"💰 Ты собрал **{total_income}** дохода!\n"
        f"💳 Всего: **{balance}** монет",
        parse_mode="Markdown"
    )


@dp.message_handler(commands=["coins"])
async def coins(message: types.Message):
    user_id = message.from_user.id
    
    if not user_exists(user_id):
        await message.answer("🌸 **Сначала запусти бота!**\nНапиши `/start` в личку бота, чтобы зарегистрироваться.")
        return
    
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (user_id,))
    result = cursor.fetchone()
    coins_count = result[0] if result else 0
    await message.answer(f"💰 **{coins_count}** монет", parse_mode="Markdown")


@dp.message_handler(commands=["my"])
async def my_farm(message: types.Message):
    user_id = message.from_user.id
    
    if not user_exists(user_id):
        await message.answer("🌸 **Сначала запусти бота!**\nНапиши `/start` в личку бота, чтобы зарегистрироваться.")
        return
    
    cursor.execute("""
        SELECT femboy_name, rarity, income 
        FROM inventory 
        WHERE tg_id = ? 
        ORDER BY 
            CASE rarity
                WHEN 'Мифический' THEN 1
                WHEN 'Легендарный' THEN 2
                WHEN 'Эпический' THEN 3
                WHEN 'Редкий' THEN 4
                WHEN 'Необычный' THEN 5
                WHEN 'Обычный' THEN 6
            END
    """, (user_id,))
    inventory = cursor.fetchall()
    if not inventory:
        await message.answer("😢 Нет фембоев!")
        return
    text = "📋 **Твоя ферма:**\n\n"
    total_income = 0
    for name, rarity, income in inventory:
        text += f"{get_rarity_emoji(rarity)} {name} ({rarity}) → {income} доход\n"
        total_income += income
    text += f"\n💰 Доход: **{total_income}**"
    await message.answer(text, parse_mode="Markdown")


@dp.message_handler(commands=["top"])
async def top(message: types.Message):
    cursor.execute("SELECT tg_id, coins FROM users ORDER BY coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    if not top_users:
        await message.answer("😢 Нет игроков!")
        return
    text = "🏆 **Топ игроков:**\n\n"
    for i, (tg_id, coins) in enumerate(top_users, 1):
        try:
            user = await bot.get_chat(tg_id)
            username = user.username or user.first_name
        except:
            username = f"ID {tg_id}"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        text += f"{medal} @{username} — {coins} монет\n"
    await message.answer(text, parse_mode="Markdown")


@dp.message_handler(commands=["shop"])
async def shop(message: types.Message):
    user_id = message.from_user.id
    
    # Проверка: зарегистрирован ли пользователь
    if not user_exists(user_id):
        await message.answer("🌸 **Сначала запусти бота!**\nНапиши `/start` в личку бота, чтобы зарегистрироваться.")
        return
    
    current_time = datetime.now()
    if not hasattr(dp, 'shop_cache'):
        dp.shop_cache = {}
        dp.shop_timers = {}
    if user_id in dp.shop_cache and user_id in dp.shop_timers:
        time_passed = current_time - dp.shop_timers[user_id]
        if time_passed < timedelta(hours=1):
            shop_items = dp.shop_cache[user_id]
            text = "🏪 **Обычный магазин** (обновляется каждый час)\n"
            text += "🎲 3 карточки (обязательно 1 Обычный)\n"
            remaining = timedelta(hours=1) - time_passed
            minutes = int(remaining.total_seconds() // 60)
            text += f"⏳ До обновления: **{minutes}** минут\n\n"
            for femboy in shop_items:
                owned = " ✅ (уже есть)" if is_owned(user_id, femboy["name"]) else ""
                text += f"{get_rarity_emoji(femboy['rarity'])} **{femboy['name']}** ({femboy['rarity']}){owned}\n"
                text += f"   💰 Доход: {femboy['income']} | Цена: {femboy['price']} монет\n\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            for femboy in shop_items:
                if not is_owned(user_id, femboy["name"]):
                    button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
                    callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
                    keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
            if not keyboard.inline_keyboard:
                text += "\n✅ **У тебя уже есть все фембои из магазина!**"
            await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
            return
    common_femboys = [f for f in ALL_FEMBOYS if f["rarity"] == "Обычный"]
    other_pool = [f for f in ALL_FEMBOYS if f["rarity"] in ["Необычный", "Редкий", "Эпический"]]
    random.shuffle(other_pool)
    other_items = other_pool[:2]
    common_item = random.choice(common_femboys)
    shop_items = [common_item] + other_items
    random.shuffle(shop_items)
    dp.shop_cache[user_id] = shop_items
    dp.shop_timers[user_id] = current_time
    text = "🏪 **Обычный магазин** (обновляется каждый час)\n"
    text += "🎲 3 карточки (обязательно 1 Обычный)\n"
    text += "⏳ До обновления: **60** минут\n\n"
    for femboy in shop_items:
        owned = " ✅ (уже есть)" if is_owned(user_id, femboy["name"]) else ""
        text += f"{get_rarity_emoji(femboy['rarity'])} **{femboy['name']}** ({femboy['rarity']}){owned}\n"
        text += f"   💰 Доход: {femboy['income']} | Цена: {femboy['price']} монет\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)
    for femboy in shop_items:
        if not is_owned(user_id, femboy["name"]):
            button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
            callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
            keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    if not keyboard.inline_keyboard:
        text += "\n✅ **У тебя уже есть все фембои из магазина!**"
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@dp.message_handler(commands=["dailyshop"])
async def daily_shop(message: types.Message):
    user_id = message.from_user.id
    
    # Проверка: зарегистрирован ли пользователь
    if not user_exists(user_id):
        await message.answer("🌸 **Сначала запусти бота!**\nНапиши `/start` в личку бота, чтобы зарегистрироваться.")
        return
    
    daily_pool = [f for f in ALL_FEMBOYS if f["rarity"] in ["Эпический", "Легендарный", "Мифический"]]
    today = datetime.now().strftime("%Y%m%d")
    random.seed(today)
    daily_item = random.choice(daily_pool)
    random.seed()
    text = "🌟 **Ежедневный магазин** (обновляется в 00:00)\n"
    text += "🎯 1 карточка (от Эпика и выше)\n\n"
    owned = " ✅ (уже есть)" if is_owned(user_id, daily_item["name"]) else ""
    text += f"{get_rarity_emoji(daily_item['rarity'])} **{daily_item['name']}** ({daily_item['rarity']}){owned}\n"
    text += f"   💰 Доход: {daily_item['income']} | Цена: {daily_item['price']} монет\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)
    if not is_owned(user_id, daily_item["name"]):
        button_text = f"{get_rarity_emoji(daily_item['rarity'])} Купить {daily_item['name']} ({daily_item['price']}💳)"
        callback_data = f"buy_{daily_item['name'].replace(' ', '_')}"
        keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    else:
        text += "\n✅ **У тебя уже есть этот фембой!**"
    if not hasattr(dp, 'daily_cache'):
        dp.daily_cache = {}
    dp.daily_cache[user_id] = [daily_item]
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith("buy_"))
async def buy_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    # Проверка: зарегистрирован ли пользователь
    if not user_exists(user_id):
        await call.answer("❌ Сначала запусти бота!", show_alert=True)
        await call.message.edit_text(
            call.message.text + "\n\n🌸 **Сначала запусти бота!**\nНапиши `/start` в личку бота, чтобы зарегистрироваться.",
            parse_mode="Markdown",
            reply_markup=None
        )
        return
    
    femboy_name = call.data.replace("buy_", "").replace("_", " ")
    target = None
    for f in ALL_FEMBOYS:
        if f["name"] == femboy_name:
            target = f
            break
    if not target:
        await call.answer("❌ Фембой не найден!", show_alert=True)
        return
    if is_owned(user_id, target["name"]):
        await call.answer("❌ У тебя уже есть этот фембой!", show_alert=True)
        return
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (user_id,))
    result = cursor.fetchone()
    balance = result[0] if result else 0
    if balance < target["price"]:
        await call.answer(f"❌ Нужно: {target['price']}, у тебя: {balance}", show_alert=True)
        return
    cursor.execute("UPDATE users SET coins = coins - ? WHERE tg_id = ?", (target["price"], user_id))
    cursor.execute("""
        INSERT INTO inventory (tg_id, femboy_name, rarity, income)
        VALUES (?, ?, ?, ?)
    """, (user_id, target["name"], target["rarity"], target["income"]))
    conn.commit()
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (user_id,))
    new_balance = cursor.fetchone()[0]
    await call.answer(f"✅ Куплен {target['name']}!", show_alert=False)
    current_text = call.message.text
    new_text = current_text + f"\n\n✅ **Ты купил {target['name']}** ({target['rarity']})!\n💰 Остаток: {new_balance} монет"
    keyboard = InlineKeyboardMarkup(row_width=1)
    if hasattr(dp, 'shop_cache') and user_id in dp.shop_cache:
        shop_items = dp.shop_cache[user_id]
        for femboy in shop_items:
            if not is_owned(user_id, femboy["name"]) and femboy["name"] != target["name"]:
                button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
                callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
                keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    if hasattr(dp, 'daily_cache') and user_id in dp.daily_cache:
        daily_items = dp.daily_cache[user_id]
        for femboy in daily_items:
            if not is_owned(user_id, femboy["name"]) and femboy["name"] != target["name"]:
                button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
                callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
                keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    if not keyboard.inline_keyboard:
        new_text += "\n\n✅ **Все доступные фембои куплены!**"
    try:
        await call.message.edit_text(
            new_text,
            parse_mode="Markdown",
            reply_markup=keyboard if keyboard.inline_keyboard else None
        )
    except Exception as e:
        print(f"Ошибка обновления: {e}")


# ====================================================================
# ====================== АДМИН-КОМАНДЫ (ПО ID) ======================
# ====================================================================

@dp.message_handler(commands=["addcoins_id"])
async def add_coins_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("❌ Использование: /addcoins_id 123456789 500")
        return

    try:
        target_id = int(args[1])
        amount = int(args[2])
    except:
        await message.answer("❌ ID и сумма должны быть числами!")
        return

    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (target_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    cursor.execute("UPDATE users SET coins = coins + ? WHERE tg_id = ?", (amount, target_id))
    conn.commit()
    await message.answer(f"✅ Начислено **{amount}** монет пользователю ID: `{target_id}`", parse_mode="Markdown")


@dp.message_handler(commands=["removecoins_id"])
async def remove_coins_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("❌ Использование: /removecoins_id 123456789 200")
        return

    try:
        target_id = int(args[1])
        amount = int(args[2])
    except:
        await message.answer("❌ ID и сумма должны быть числами!")
        return

    cursor.execute("SELECT tg_id, coins FROM users WHERE tg_id = ?", (target_id,))
    result = cursor.fetchone()
    if not result:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    new_balance = max(0, result[1] - amount)
    cursor.execute("UPDATE users SET coins = ? WHERE tg_id = ?", (new_balance, target_id))
    conn.commit()
    await message.answer(f"✅ Снято **{amount}** монет у пользователя ID: `{target_id}`\n💰 Новый баланс: **{new_balance}**", parse_mode="Markdown")


@dp.message_handler(commands=["reset_coins_id"])
async def reset_coins_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /reset_coins_id 123456789")
        return

    try:
        target_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом!")
        return

    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (target_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    cursor.execute("UPDATE users SET coins = 100 WHERE tg_id = ?", (target_id,))
    conn.commit()
    await message.answer(f"✅ Баланс пользователя ID: `{target_id}` сброшен до **100** монет", parse_mode="Markdown")


@dp.message_handler(commands=["give_tofik_id"])
async def give_tofik_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /give_tofik_id 123456789")
        return

    try:
        target_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом!")
        return

    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (target_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    if is_owned(target_id, "Тофик"):
        await message.answer(f"❌ У пользователя ID: `{target_id}` уже есть Тофик!", parse_mode="Markdown")
        return

    tofik = find_femboy("Тофик")
    cursor.execute("""
        INSERT INTO inventory (tg_id, femboy_name, rarity, income)
        VALUES (?, ?, ?, ?)
    """, (target_id, tofik["name"], tofik["rarity"], tofik["income"]))
    conn.commit()

    await message.answer(f"🌟 **Тофик** выдан пользователю ID: `{target_id}`!\n💰 Доход: {tofik['income']} доход", parse_mode="Markdown")

    try:
        await bot.send_message(
            target_id,
            f"🌟 **Поздравляю!**\nТебе выдали **Тофика** — самую редкую карту!\n💰 Доход: {tofik['income']} доход"
        )
    except:
        pass


@dp.message_handler(commands=["giveadmin_id"])
async def give_admin_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /giveadmin_id 123456789")
        return

    try:
        target_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом!")
        return

    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (target_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    cursor.execute("INSERT OR IGNORE INTO admins (tg_id) VALUES (?)", (target_id,))
    conn.commit()
    await message.answer(f"✅ Пользователь ID: `{target_id}` теперь администратор!", parse_mode="Markdown")


@dp.message_handler(commands=["removeadmin_id"])
async def remove_admin_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /removeadmin_id 123456789")
        return

    try:
        target_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом!")
        return

    if target_id in ADMIN_IDS:
        await message.answer("❌ Нельзя забрать права у главного админа!")
        return

    cursor.execute("DELETE FROM admins WHERE tg_id = ?", (target_id,))
    conn.commit()
    await message.answer(f"✅ У пользователя ID: `{target_id}` забраны права администратора!", parse_mode="Markdown")


@dp.message_handler(commands=["reset_inventory_id"])
async def reset_inventory_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /reset_inventory_id 123456789")
        return

    try:
        target_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом!")
        return

    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (target_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    cursor.execute("DELETE FROM inventory WHERE tg_id = ?", (target_id,))
    conn.commit()
    await message.answer(f"✅ Инвентарь пользователя ID: `{target_id}` очищен!", parse_mode="Markdown")


@dp.message_handler(commands=["user_info_id"])
async def user_info_id(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /user_info_id 123456789")
        return

    try:
        target_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом!")
        return

    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (target_id,))
    user_data = cursor.fetchone()
    if not user_data:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден!")
        return

    cursor.execute("SELECT COUNT(*) FROM inventory WHERE tg_id = ?", (target_id,))
    cards_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(income) FROM inventory WHERE tg_id = ?", (target_id,))
    total_income = cursor.fetchone()[0] or 0

    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (target_id,))
    is_admin = cursor.fetchone() is not None

    text = f"📊 **Информация о пользователе:**\n\n"
    text += f"🆔 ID: `{target_id}`\n"
    text += f"💰 Баланс: **{user_data[0]}** монет\n"
    text += f"📋 Всего карт: **{cards_count}**\n"
    text += f"📈 Доход: **{total_income}**\n"
    text += f"👑 Админ: {'✅' if is_admin else '❌'}"

    await message.answer(text, parse_mode="Markdown")


@dp.message_handler(commands=["all_users"])
async def all_users(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    cursor.execute("SELECT tg_id, coins FROM users ORDER BY coins DESC")
    users = cursor.fetchall()

    if not users:
        await message.answer("😢 Нет пользователей!")
        return

    text = "📊 **Все пользователи:**\n\n"
    for i, (tg_id, coins) in enumerate(users, 1):
        try:
            user = await bot.get_chat(tg_id)
            username = user.username or user.first_name
        except:
            username = f"ID {tg_id}"
        text += f"{i}. @{username} — {coins} монет (ID: `{tg_id}`)\n"

        if len(text) > 3500:
            await message.answer(text, parse_mode="Markdown")
            text = ""

    if text:
        await message.answer(text, parse_mode="Markdown")


# ====================================================================
# ====================== ВЕБ-СЕРВЕР ДЛЯ HEALTH CHECK ======================
# ====================================================================

async def health_check(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    print(f"🌐 Health check server started on port {port}")


async def main():
    logging.basicConfig(level=logging.INFO)
    print("🌸 Femboy Farm запущен!")
    print(f"👑 Админы: {ADMIN_IDS}")
    print("🌟 Тофик можно купить за 10,000 монет (доход 5,000)")
    print("📋 Все команды в /help_admin")

    await start_web_server()
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
