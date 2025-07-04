import os
import sys
import telegram  # Added for version check
from http import HTTPStatus
from contextlib import asynccontextmanager

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from gspread.exceptions import SpreadsheetNotFound, APIError

# --- Critical Version Check ---
print("Checking python-telegram-bot version...")
ptb_version = telegram.__version__
print(f"Detected version: {ptb_version}")

# Convert version string to comparable numbers
version_parts = ptb_version.split('.')
major = int(version_parts[0])
minor = int(version_parts[1]) if len(version_parts) > 1 else 0

if major < 20 or (major == 20 and minor < 8):
    print(f"❌ FATAL ERROR: Need python-telegram-bot v20.8+, found v{ptb_version}")
    print("This version causes AttributeError in Render deployments")
    sys.exit(1)  # Force quit with error code
else:
    print("✅ Version check passed - compatible with Render")

# --- Load Env Vars ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Validate environment variables
if not all([BOT_TOKEN, WEBHOOK_URL, SPREADSHEET_ID]):
    missing = [var for var in ["BOT_TOKEN", "WEBHOOK_URL", "SPREADSHEET_ID"] if not os.getenv(var)]
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

# --- Google Sheets Setup ---
try:
    print("Initializing Google Sheets connection...")
    gc = gspread.service_account(filename="credentials.json")
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    print("✅ Google Sheets connection successful")
except (SpreadsheetNotFound, APIError) as e:
    print(f"❌ Google Sheets Error: {str(e)}")
    sys.exit(1)

# --- Telegram Bot Setup ---
try:
    print("Building Telegram application...")
    application = Application.builder().token(BOT_TOKEN).build()
    print("✅ Telegram application built successfully")
except Exception as e:
    print(f"❌ Telegram setup failed: {str(e)}")
    sys.exit(1)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your bot 👋")
    auto_msg = await update.message.reply_text("This message will self-destruct in 12 hours 🔥")
    context.job_queue.run_once(lambda ctx: ctx.job.context.delete(), 43200, context=auto_msg)

async def log_to_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user.username or update.effective_user.id
        text = update.message.text
        sheet.append_row([str(user), text])
        await update.message.reply_text("✅ Logged to sheet!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to log: {str(e)}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("log", log_to_sheet))

# --- FastAPI Webhook Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print(f"Setting webhook to: {WEBHOOK_URL}")
        await application.bot.set_webhook(WEBHOOK_URL)
        print("✅ Webhook set successfully")
    except Exception as e:
        print(f"❌ Webhook setup failed: {str(e)}")
        sys.exit(1)
    
    async with application:
        await application.start()
        yield
        await application.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=HTTPStatus.OK)
    except Exception as e:
        print(f"Webhook processing error: {str(e)}")
        return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)