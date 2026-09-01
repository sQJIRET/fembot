import asyncio
import logging
import random
import sqlite3
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

# ========== ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ ИЗ .env ==========
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

# ========== БАЗА ДАННЫХ ==========
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

# ========== НАСТОЯЩИЕ ФЕМБОИ ==========
ALL_FEMBOYS = [
    {"name": "Xingqiu", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Saika Totsuka", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Nagisa Shiota", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Chihiro Fujisaki", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Gasper Vladi", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Suzuya Juzo", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Freminet", "rarity": "Обычный", "income": 50, "price": 100},
    {"name": "Alois Trancy", "rarity": "Обычный", "income": 50, "price": 100},

    {"name": "Hideri Kanzaki", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Ruka Urushibara", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Haku", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Tetora", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Lyney", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Narancia Ghirga", "rarity": "Необычный", "income": 100, "price": 300},
    {"name": "Gowther", "rarity": "Необычный", "income": 100, "price": 300},

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

    {"name": "Line", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Hana Macchia", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Syo", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Maruruk", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Totsugeki", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Wanderer", "rarity": "Эпический", "income": 400, "price": 1000},
    {"name": "Ciel (Robin Outfit)", "rarity": "Эпический", "income": 400, "price": 1000},

    {"name": "Astolfo", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Felix Argyle", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Venti", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "F1nn5ter", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Astellas", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Babo", "rarity": "Легендарный", "income": 700, "price": 2000},
    {"name": "Mikazuki", "rarity": "Легендарный", "income": 700, "price": 2000},

    {"name": "Тофик", "rarity": "Мифический", "income": 999999, "price": 999999},
]

# ========== БОТ ==========
bot = Bot(token=TOKEN)
dp = Dispatcher()


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


# ========== КОМАНДЫ ==========

@dp.message(Command("start"))
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
        "`Фарма` — собрать монеты (1 раз в час)\n"
        "/shop — обычный магазин (3 карточки, 1 обязательно Обычный)\n"
        "/dailyshop — ежедневный магазин (1 карточка, от Эпика и выше)\n"
        "/my — посмотреть свою ферму\n"
        "/coins — баланс\n"
        "/top — топ игроков\n\n"
        "⭐ **Редкости:**\n"
        f"{get_rarity_emoji('Обычный')} Обычный — 50 монет/час (100 монет)\n"
        f"{get_rarity_emoji('Необычный')} Необычный — 100 монет/час (300 монет)\n"
        f"{get_rarity_emoji('Редкий')} Редкий — 200 монет/час (600 монет)\n"
        f"{get_rarity_emoji('Эпический')} Эпический — 400 монет/час (1000 монет)\n"
        f"{get_rarity_emoji('Легендарный')} Легендарный — 700 монет/час (2000 монет)\n"
        f"{get_rarity_emoji('Мифический')} Мифический — 999999 монет/час (❌ НЕ ПОКУПАЕТСЯ)",
        parse_mode="Markdown"
    )


@dp.message(lambda msg: msg.text and msg.text.lower() == "фарма")
async def farm_text(message: types.Message):
    user_id = message.from_user.id

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
        f"💰 Ты собрал **{total_income}** монет!\n"
        f"💳 Всего: **{balance}** монет",
        parse_mode="Markdown"
    )


@dp.message(Command("coins"))
async def coins(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (user_id,))
    result = cursor.fetchone()
    coins_count = result[0] if result else 0
    await message.answer(f"💰 **{coins_count}** монет", parse_mode="Markdown")


@dp.message(Command("my"))
async def my_farm(message: types.Message):
    user_id = message.from_user.id

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

    text += f"\n💰 Доход: **{total_income}** монет"
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("top"))
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


@dp.message(Command("shop"))
async def shop(message: types.Message):
    user_id = message.from_user.id
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

            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for femboy in shop_items:
                if not is_owned(user_id, femboy["name"]):
                    button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
                    callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text=button_text, callback_data=callback_data)
                    ])

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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for femboy in shop_items:
        if not is_owned(user_id, femboy["name"]):
            button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
            callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=callback_data)
            ])

    if not keyboard.inline_keyboard:
        text += "\n✅ **У тебя уже есть все фембои из магазина!**"

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@dp.message(Command("dailyshop"))
async def daily_shop(message: types.Message):
    user_id = message.from_user.id
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    if not is_owned(user_id, daily_item["name"]):
        if daily_item["rarity"] == "Мифический":
            text += "❌ **Эту карту нельзя купить!** Только получить от админа."
        else:
            button_text = f"{get_rarity_emoji(daily_item['rarity'])} Купить {daily_item['name']} ({daily_item['price']}💳)"
            callback_data = f"buy_{daily_item['name'].replace(' ', '_')}"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=callback_data)
            ])
    else:
        text += "\n✅ **У тебя уже есть этот фембой!**"

    if not hasattr(dp, 'daily_cache'):
        dp.daily_cache = {}
    dp.daily_cache[user_id] = [daily_item]

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@dp.callback_query(lambda call: call.data.startswith("buy_"))
async def buy_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    femboy_name = call.data.replace("buy_", "").replace("_", " ")

    target = None
    for f in ALL_FEMBOYS:
        if f["name"] == femboy_name:
            target = f
            break

    if not target:
        await call.answer("❌ Фембой не найден!", show_alert=True)
        return

    if target["rarity"] == "Мифический":
        await call.answer("❌ Эту карту нельзя купить!", show_alert=True)
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    if hasattr(dp, 'shop_cache') and user_id in dp.shop_cache:
        shop_items = dp.shop_cache[user_id]
        for femboy in shop_items:
            if not is_owned(user_id, femboy["name"]) and femboy["name"] != target["name"]:
                button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
                callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=button_text, callback_data=callback_data)
                ])

    if hasattr(dp, 'daily_cache') and user_id in dp.daily_cache:
        daily_items = dp.daily_cache[user_id]
        for femboy in daily_items:
            if not is_owned(user_id, femboy["name"]) and femboy["name"] != target["name"]:
                if femboy["rarity"] != "Мифический":
                    button_text = f"{get_rarity_emoji(femboy['rarity'])} Купить {femboy['name']} ({femboy['price']}💳)"
                    callback_data = f"buy_{femboy['name'].replace(' ', '_')}"
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text=button_text, callback_data=callback_data)
                    ])

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


# ========== АДМИНКА ==========

@dp.message(Command("addcoins"))
async def add_coins(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("❌ /addcoins @username 500")
        return

    target_username = args[1].replace("@", "")
    try:
        amount = int(args[2])
    except:
        await message.answer("❌ Сумма должна быть числом!")
        return

    try:
        target = None
        cursor.execute("SELECT tg_id FROM users")
        for (tg_id,) in cursor.fetchall():
            try:
                user = await bot.get_chat(tg_id)
                if user.username and user.username.lower() == target_username.lower():
                    target = tg_id
                    break
            except:
                continue

        if not target:
            await message.answer(f"❌ @{target_username} не найден!")
            return

        cursor.execute("UPDATE users SET coins = coins + ? WHERE tg_id = ?", (amount, target))
        conn.commit()
        await message.answer(f"✅ Начислено {amount} монет @{target_username}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("give_tofik"))
async def give_tofik(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ /give_tofik @username")
        return

    target_username = args[1].replace("@", "")

    try:
        target = None
        cursor.execute("SELECT tg_id FROM users")
        for (tg_id,) in cursor.fetchall():
            try:
                user = await bot.get_chat(tg_id)
                if user.username and user.username.lower() == target_username.lower():
                    target = tg_id
                    break
            except:
                continue

        if not target:
            await message.answer(f"❌ @{target_username} не найден!")
            return

        if is_owned(target, "Тофик"):
            await message.answer(f"❌ У @{target_username} уже есть Тофик!")
            return

        tofik = find_femboy("Тофик")
        cursor.execute("""
            INSERT INTO inventory (tg_id, femboy_name, rarity, income)
            VALUES (?, ?, ?, ?)
        """, (target, tofik["name"], tofik["rarity"], tofik["income"]))
        conn.commit()

        await message.answer(f"🌟 **Тофик** выдан пользователю @{target_username}!\n"
                             f"💰 Доход: {tofik['income']} доход")

        try:
            await bot.send_message(
                target,
                f"🌟 **Поздравляю!**\n"
                f"Тебе выдали **Тофика** — самую редкую карту!\n"
                f"💰 Доход: {tofik['income']} доход"
            )
        except:
            pass

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("giveadmin"))
async def give_admin(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT tg_id FROM admins WHERE tg_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer("⛔ Нет прав!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ /giveadmin @username")
        return

    target_username = args[1].replace("@", "")

    try:
        target = None
        cursor.execute("SELECT tg_id FROM users")
        for (tg_id,) in cursor.fetchall():
            try:
                user = await bot.get_chat(tg_id)
                if user.username and user.username.lower() == target_username.lower():
                    target = tg_id
                    break
            except:
                continue

        if not target:
            await message.answer(f"❌ @{target_username} не найден!")
            return

        cursor.execute("INSERT OR IGNORE INTO admins (tg_id) VALUES (?)", (target,))
        conn.commit()
        await message.answer(f"✅ @{target_username} теперь администратор!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# ========== WEBHOOK + FLASK (ДЛЯ RENDER) ==========

async def on_startup():
    """Выполняется при запуске бота"""
    print("🌸 Femboy Farm запущен!")


async def on_shutdown():
    """Выполняется при остановке бота"""
    print("🌸 Femboy Farm остановлен!")


async def main():
    """Главная функция"""
    logging.basicConfig(level=logging.INFO)

    # Настройка веб-сервера
    app = web.Application()

    # Обработчик вебхуков
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")

    # Установка вебхука
    port = int(os.getenv("PORT", 5000))
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL', 'localhost')}/webhook"

    # Если мы на Render, используем вебхук
    if os.getenv("RENDER"):
        await bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")

    # Запускаем сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    print(f"🚀 Бот запущен на порту {port}")

    # Если не Render, запускаем polling
    if not os.getenv("RENDER"):
        await dp.start_polling(bot)

    # Держим сервер запущенным
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())