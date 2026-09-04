import sqlite3, os, time, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
conn = sqlite3.connect("bot.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0,
    energy INTEGER DEFAULT 1000, last_daily TEXT, total_taps INTEGER DEFAULT 0
)""")
conn.commit()

def get_user(uid):
    cur = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if not row:
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (uid,))
        conn.commit()
        return get_user(uid)
    return row

def update(uid, **kw):
    sets = ", ".join(f"{k}=?" for k in kw)
    conn.execute(f"UPDATE users SET {sets} WHERE user_id=?", list(kw.values())+[uid])
    conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    user = get_user(uid)
    update(uid, username=username)
    kb = [
        [InlineKeyboardButton("🪙 تپ کن", callback_data="tap")],
        [InlineKeyboardButton("💰 موجودی", callback_data="balance"),
         InlineKeyboardButton("🎁 جایزه روزانه", callback_data="daily")],
        [InlineKeyboardButton("🏆 جدول برتر", callback_data="top")]
    ]
    await update.message.reply_text(
        f"سلام {username} 👋\nبه ربات پول‌ساز خوش اومدی!\n"
        f"با تپ کردن سکه بگیر، بعداً می‌تونی باهاش پول واقعی برداشت کنی!",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    user = get_user(uid)
    if user[3] <= 0:
        await q.edit_message_text("انرژی تموم شد! 😴 یک دقیقه صبر کن.")
        return
    earned = 1
    if random.random() < 0.1:
        earned = 2
    new_balance = user[2] + earned
    new_energy = user[3] - 1
    taps = user[5] + 1
    update(uid, balance=new_balance, energy=new_energy, total_taps=taps)
    kb = [[InlineKeyboardButton("🪙 تپ کن", callback_data="tap")],
          [InlineKeyboardButton("🔙 منو", callback_data="menu")]]
    await q.edit_message_text(
        f"✨ {earned} سکه گرفتی!\n💰 موجودی: {new_balance}\n⚡ انرژی: {new_energy}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = get_user(q.from_user.id)
    await q.edit_message_text(
        f"💰 موجودی: {user[2]} سکه\n👆 تعداد تپ‌ها: {user[5]}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منو", callback_data="menu")]])
    )

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    user = get_user(uid)
    today = time.strftime("%Y-%m-%d")
    if user[4] == today:
        await q.edit_message_text("جایزه امروز رو گرفتی! فردا بیا.")
        return
    reward = random.randint(20, 50)
    update(uid, balance=user[2]+reward, last_daily=today)
    await q.edit_message_text(
        f"🎉 جایزه روزانه: {reward} سکه!\nموجودی جدید: {user[2]+reward}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منو", callback_data="menu")]])
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cur = conn.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
    rows = cur.fetchall()
    text = "🏆 جدول برترین‌ها:\n\n"
    for i, (u, b) in enumerate(rows, 1):
        text += f"{i}. {u or 'کاربر'} — {b} سکه\n"
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منو", callback_data="menu")]]))

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("🪙 تپ کن", callback_data="tap")],
        [InlineKeyboardButton("💰 موجودی", callback_data="balance"),
         InlineKeyboardButton("🎁 جایزه روزانه", callback_data="daily")],
        [InlineKeyboardButton("🏆 جدول برتر", callback_data="top")]
    ]
    await q.edit_message_text("منوی اصلی:", reply_markup=InlineKeyboardMarkup(kb))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(tap, pattern="^tap$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(daily, pattern="^daily$"))
    app.add_handler(CallbackQueryHandler(top, pattern="^top$"))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.run_polling()

if __name__ == "__main__":
    main()
