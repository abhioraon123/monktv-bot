# bot.py

import os
from http import HTTPStatus
from contextlib import asynccontextmanager

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

# --- Load Env Vars ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL")

# --- Google Sheets Setup ---
# The credentials.json file is in Render Secrets (not env variable)
gc = gspread.service_account(filename="credentials.json")
sheet = gc.open("YourSpreadsheetName").sheet1  # replace with your real Sheet name

# --- Telegram Bot Setup ---
application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Hello! I am your bot 👋")
    auto_msg = await update.message.reply_text("This message will self-destruct in 12 hours 🔥")
    context.job_queue.run_once(lambda ctx: ctx.job.context.delete(), 43200, context=auto_msg)

async def log_to_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.id
    text = update.message.text
    sheet.append_row([str(user), text])
    await update.message.reply_text("✅ Logged to sheet!")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("log", log_to_sheet))

# --- FastAPI Webhook Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.bot.set_webhook(WEBHOOK_URL)
    async with application:
        await application.start()
        yield
        await application.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return Response(status_code=HTTPStatus.OK)