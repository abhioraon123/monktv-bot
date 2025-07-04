import os
from http import HTTPStatus
from contextlib import asynccontextmanager

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from gspread.exceptions import SpreadsheetNotFound, APIError  # Added error handling

# --- Load Env Vars ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Validate environment variables
if not all([BOT_TOKEN, WEBHOOK_URL, SPREADSHEET_ID]):
    missing = [var for var in ["BOT_TOKEN", "WEBHOOK_URL", "SPREADSHEET_ID"] if not os.getenv(var)]
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# --- Google Sheets Setup ---
try:
    gc = gspread.service_account(filename="credentials.json")
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    print("✅ Google Sheets connection successful")
except (SpreadsheetNotFound, APIError) as e:
    print(f"❌ Google Sheets Error: {str(e)}")
    raise

# --- Telegram Bot Setup ---
application = Application.builder().token(BOT_TOKEN).build()

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
        print(f"Logging error: {str(e)}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("log", log_to_sheet))

# --- FastAPI Webhook Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await application.bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Webhook setup failed: {str(e)}")
        raise
    
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
        print(f"Webhook error: {str(e)}")
        return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)