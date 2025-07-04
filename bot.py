# bot.py

import os
import json
from http import HTTPStatus
from contextlib import asynccontextmanager
from gspread.exceptions import SpreadsheetNotFound

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

# --- Load environment variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not BOT_TOKEN or not WEBHOOK_URL or not SPREADSHEET_ID:
    raise ValueError("Missing BOT_TOKEN, WEBHOOK_URL, or SPREADSHEET_ID")

# --- Setup Google Sheets ---
gc = gspread.service_account(filename="credentials.json")
try:
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
except SpreadsheetNotFound:
    raise Exception("📄 Spreadsheet not found. Check SPREADSHEET_ID and permissions.")

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