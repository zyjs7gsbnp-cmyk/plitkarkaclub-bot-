import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "plitkarka.db")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

CATEGORIES = {
    "manipulation": ("🚩 Маніпуляції та брехня",
        "Матеріали про обман, перекладання провини, тиск і повторювані маніпулятивні моделі поведінки."),
    "married": ("💍 Приховані стосунки",
        "Історії про прихований шлюб або партнерку. Публікуємо лише після модерації."),
    "ghosting": ("👻 Зникнення та повернення",
        "Історії про раптове припинення спілкування та повторні повернення."),
    "money": ("💸 Фінансові конфлікти",
        "Історії про позики, неповернуті гроші та фінансовий тиск."),
    "control": ("👑 Контроль і ревнощі",
        "Історії про контроль, порушення меж і нав'язливі ревнощі."),
    "cheating": ("💔 Невірність",
        "Історії про невірність у стосунках."),
    "emotional": ("🧊 Емоційна недоступність",
        "Історії про уникнення близькості або невизначеність у стосунках."),
    "green": ("💚 Зелені прапорці",
        "Приклади поваги, чесності, відповідальності та здорових меж."),
}

def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER,
        author_mode TEXT,
        pseudonym TEXT,
        person_name TEXT,
        instagram_url TEXT,
        category TEXT,
        story TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    return con

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Знайти людину", callback_data="search")],
        [InlineKeyboardButton("💬 Побалакати", callback_data="community")],
        [InlineKeyboardButton("🚩 Категорії", callback_data="categories")],
        [InlineKeyboardButton("🍷 Розповісти історію", callback_data="submit")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "💋 *ПЛІТКАРКА*\\n\\nЖіноча спільнота, історії та ред флеги.\\n\\n"
        "Обирай, що хочеш зробити:",
        reply_markup=main_keyboard(), parse_mode="Markdown"
    )

async def show_categories(query):
    keyboard = [[InlineKeyboardButton(label, callback_data=f"cat:{key}")]
                for key, (label, _) in CATEGORIES.items()]
    keyboard.append([InlineKeyboardButton("⬅️ Головне меню", callback_data="home")])
    await query.edit_message_text("🚩 *Категорії Пліткарки*\\nОбери категорію:",
                                  reply_markup=InlineKeyboardMarkup(keyboard),
                                  parse_mode="Markdown")

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        await query.edit_message_text("💋 *ПЛІТКАРКА*\\nОбирай розділ:",
                                      reply_markup=main_keyboard(), parse_mode="Markdown")
    elif data == "categories":
        await show_categories(query)
    elif data.startswith("cat:"):
        key = data.split(":", 1)[1]
        label, description = CATEGORIES[key]
        await query.edit_message_text(
            f"*{label}*\\n\\n{description}\\n\\n"
            "Історії в цій категорії з'являтимуться після налаштування бази та модерації.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ До категорій", callback_data="categories")],
                                               [InlineKeyboardButton("🏠 Головне меню", callback_data="home")]]),
            parse_mode="Markdown"
        )
    elif data == "search":
        context.user_data.clear()
        context.user_data["state"] = "search"
        await query.edit_message_text(
            "🔎 Надішли ім'я та прізвище або Instagram-посилання.\\n\\n"
            "Поки база наповнюється, пошук працює як демонстраційний екран. "
            "Збіг імені сам по собі не підтверджує особу чи правдивість історії.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Головне меню", callback_data="home")]])
        )
    elif data == "community":
        chat_url = os.getenv("COMMUNITY_CHAT_URL", "")
        channel_url = os.getenv("STORIES_CHANNEL_URL", "")
        rows = []
        if chat_url:
            rows.append([InlineKeyboardButton("💬 Відкрити чат", url=chat_url)])
        if channel_url:
            rows.append([InlineKeyboardButton("📚 Стрічка історій", url=channel_url)])
        rows.append([InlineKeyboardButton("⬅️ Головне меню", callback_data="home")])
        message = "💬 Розділ спільноти. Посилання на чат і канал можна додати в налаштуваннях."
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(rows))
    elif data == "submit":
        context.user_data.clear()
        context.user_data["state"] = "story_name"
        await query.edit_message_text(
            "🍷 *Розповісти історію*\\n\\n"
            "Будь ласка, не додавай адреси, телефони, місце роботи, приватні фото чи інші зайві персональні дані. "
            "Історія не буде опублікована автоматично — спершу потрібна модерація.\\n\\n"
            "1/5. Вкажи ім'я/псевдонім людини або напиши «пропустити».",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скасувати", callback_data="home")]])
        )

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if not state:
        await update.message.reply_text("Обери розділ у меню:", reply_markup=main_keyboard())
        return

    text = update.message.text.strip()
    if state == "search":
        await update.message.reply_text(
            "🔎 У першій демонстраційній версії записів для пошуку ще немає. "
            "Наступним етапом підключимо базу даних і модерацію.",
            reply_markup=main_keyboard()
        )
        context.user_data.clear()
    elif state == "story_name":
        context.user_data["person_name"] = "" if text.lower() == "пропустити" else text[:120]
        context.user_data["state"] = "story_instagram"
        await update.message.reply_text("2/5. Якщо доречно, надішли Instagram-посилання або напиши «пропустити».")
    elif state == "story_instagram":
        context.user_data["instagram_url"] = "" if text.lower() == "пропустити" else text[:300]
        context.user_data["state"] = "story_category"
        keyboard = [[InlineKeyboardButton(label, callback_data=f"submitcat:{key}")]
                    for key, (label, _) in CATEGORIES.items()]
        keyboard.append([InlineKeyboardButton("Скасувати", callback_data="home")])
        await update.message.reply_text("3/5. Обери категорію:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif state == "story_text":
        context.user_data["story"] = text[:4000]
        context.user_data["state"] = "story_author_mode"
        await update.message.reply_text(
            "5/5. Як показувати авторку?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Анонімно", callback_data="author:anonymous")],
                [InlineKeyboardButton("Під псевдонімом", callback_data="author:pseudonym")],
                [InlineKeyboardButton("Скасувати", callback_data="home")]
            ])
        )
    elif state == "story_pseudonym":
        context.user_data["pseudonym"] = text[:80]
        await save_submission(update, context, "pseudonym")

async def save_submission(update, context, mode):
    d = context.user_data
    con = db()
    cur = con.execute(
        """INSERT INTO submissions
        (telegram_user_id, author_mode, pseudonym, person_name, instagram_url, category, story, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (update.effective_user.id, mode, d.get("pseudonym", ""), d.get("person_name", ""),
         d.get("instagram_url", ""), d.get("category", ""), d.get("story", ""))
    )
    submission_id = cur.lastrowid
    con.commit()
    con.close()
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Історію отримано (№{submission_id}). Вона збережена як чернетка на модерацію й не опублікована автоматично.",
        reply_markup=main_keyboard()
    )

async def on_submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("submitcat:"):
        key = data.split(":", 1)[1]
        context.user_data["category"] = key
        context.user_data["state"] = "story_text"
        await query.edit_message_text("4/5. Опиши ситуацію фактично, без погроз, образ чи зайвих приватних даних.")
    elif data.startswith("author:"):
        mode = data.split(":", 1)[1]
        if mode == "pseudonym":
            context.user_data["state"] = "story_pseudonym"
            await query.edit_message_text("Введи псевдонім авторки:")
        else:
            await query.edit_message_text("Зберігаю історію на модерацію…")
            await save_submission_data(
                user_id=update.effective_user.id, context=context, mode=mode,
                reply_func=query.message.reply_text
            )

async def save_submission_data(user_id, context, mode, reply_func):
    d = context.user_data
    con = db()
    cur = con.execute(
        """INSERT INTO submissions
        (telegram_user_id, author_mode, pseudonym, person_name, instagram_url, category, story, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (user_id, mode, "", d.get("person_name", ""),
         d.get("instagram_url", ""), d.get("category", ""), d.get("story", ""))
    )
    sid = cur.lastrowid
    con.commit()
    con.close()
    context.user_data.clear()
    await reply_func(f"✅ Історію отримано (№{sid}). Вона чекає на модерацію й не опублікована автоматично.",
                     reply_markup=main_keyboard())

def main():
    if not TOKEN:
        raise RuntimeError("Set BOT_TOKEN as an environment variable.")
    db().close()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_submit_callback, pattern=r"^(submitcat:|author:)"))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()

if __name__ == "__main__":
    main()
