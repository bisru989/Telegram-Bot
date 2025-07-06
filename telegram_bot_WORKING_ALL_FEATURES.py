import json
import time
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# === CONFIG (USE ENV FOR DEPLOYMENT) ===
TOKEN = os.getenv("TOKEN", "YOUR_BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "YourAdminUsername")
UPI_ID = os.getenv("UPI_ID", "yourupi@upi")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername")
DATA_FILE = "users.json"

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

def get_user(users, uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"wallet": 0, "bonus_time": 0, "ref_by": None}
    return users[uid]

# === /start COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = load_users()
    args = context.args

    if args and args[0].startswith("ref"):
        ref_by = args[0][3:]
        if ref_by != uid and not get_user(users, uid).get("ref_by"):
            get_user(users, uid)["ref_by"] = ref_by
            get_user(users, ref_by)["wallet"] += 5

    get_user(users, uid)
    save_users(users)

    keyboard = [
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet"),
         InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily")],
        [InlineKeyboardButton("✈️ Aviator", callback_data="aviator")],
        [InlineKeyboardButton("💸 Deposit", callback_data="deposit"),
         InlineKeyboardButton("🏧 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("👥 Referral", callback_data="referral")]
    ]
    await update.message.reply_text("🎮 Welcome to the Game Bot!", reply_markup=InlineKeyboardMarkup(keyboard))

# === CALLBACKS ===
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(update.effective_user.id)
    balance = get_user(users, uid)["wallet"]
    await update.callback_query.edit_message_text(f"💼 Wallet: ₹{balance}")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(update.effective_user.id)
    user = get_user(users, uid)
    now = time.time()

    if now - user["bonus_time"] >= 86400:
        bonus = random.randint(1, 5)
        user["wallet"] += bonus
        user["bonus_time"] = now
        save_users(users)
        await update.callback_query.edit_message_text(f"🎁 You received ₹{bonus} bonus!")
    else:
        remaining = int(86400 - (now - user["bonus_time"]))
        hrs = remaining // 3600
        mins = (remaining % 3600) // 60
        await update.callback_query.edit_message_text(f"⏳ Come back in {hrs}h {mins}m.")

async def aviator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(update.effective_user.id)
    user = get_user(users, uid)
    bet = 10

    if user["wallet"] < bet:
        await update.callback_query.edit_message_text("❌ Not enough balance (₹10 needed).")
        return

    user["wallet"] -= bet
    won = random.choice([True, False])
    multiplier = round(random.uniform(1.1, 3.0), 2)

    if won:
        win_amt = int(bet * multiplier)
        user["wallet"] += win_amt
        result = f"✈️ Plane flew to {multiplier}x
✅ You won ₹{win_amt}"
    else:
        result = f"💥 Plane crashed!
❌ You lost ₹{bet}"

    save_users(users)
    await update.callback_query.edit_message_text(result)

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    msg = (
        f"💸 Send ₹10+ to: `{UPI_ID}`
"
        f"After payment, send screenshot to admin.
"
        f"Your UID: `{uid}`"
    )
    await update.callback_query.edit_message_text(msg, parse_mode="Markdown")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🏧 Send withdrawal request like:

`withdraw 50 yourupi@upi`"
    await update.callback_query.edit_message_text(msg, parse_mode="Markdown")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    top = sorted(users.items(), key=lambda x: x[1]["wallet"], reverse=True)[:5]
    text = "🏆 Top 5 Users:

"
    for i, (uid, u) in enumerate(top, 1):
        text += f"{i}. UID {uid} — ₹{u['wallet']}
"
    await update.callback_query.edit_message_text(text)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref{uid}"
    await update.callback_query.edit_message_text(f"👥 Referral link:
{link}")

# === WITHDRAW HANDLER ===
async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    text = update.message.text.strip()
    if not text.startswith("withdraw"): return

    parts = text.split()
    if len(parts) != 3:
        await update.message.reply_text("❌ Format: withdraw 50 yourupi@upi")
        return

    uid = str(update.effective_user.id)
    amt, upi = int(parts[1]), parts[2]
    user = get_user(users, uid)

    if user["wallet"] < amt:
        await update.message.reply_text("❌ Not enough balance.")
    else:
        user["wallet"] -= amt
        save_users(users)
        await update.message.reply_text(f"✅ ₹{amt} withdrawal to `{upi}` requested.")

# === MAIN ===
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(wallet, pattern="wallet"))
    app.add_handler(CallbackQueryHandler(daily, pattern="daily"))
    app.add_handler(CallbackQueryHandler(aviator, pattern="aviator"))
    app.add_handler(CallbackQueryHandler(deposit, pattern="deposit"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="withdraw"))
    app.add_handler(CallbackQueryHandler(leaderboard, pattern="leaderboard"))
    app.add_handler(CallbackQueryHandler(referral, pattern="referral"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw))
    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()