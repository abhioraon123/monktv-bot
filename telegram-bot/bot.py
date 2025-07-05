import os
import json
import logging
import gspread
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

application = None  # Global application variable

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables with validation
def get_env_var(var_name: str) -> str:
    """Get environment variable with validation"""
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(f"Environment variable {var_name} is not set")
    return value

try:
    BOT_TOKEN = get_env_var("BOT_TOKEN")
    WEBHOOK_URL = get_env_var("WEBHOOK_URL")
    GOOGLE_CREDS_JSON = get_env_var("GOOGLE_CREDS_JSON")
    SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"
    logger.info("✅ Environment variables loaded successfully")
except ValueError as e:
    logger.error(f"❌ Environment variable error: {e}")
    raise

# Google Sheets setup with error handling
try:
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    gc = gspread.service_account_from_dict(creds_dict)
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    logger.info("✅ Google Sheets connected successfully")
except Exception as e:
    logger.error(f"❌ Google Sheets setup failed: {e}")
    sheet = None

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        await update.message.reply_text(
            "👋 Welcome to MonkTV Bot!\n\n"
            "🔎 Just type any movie or category name to search.\n"
            "📺 Also visit: https://monktv.glide.page"
        )
        logger.info(f"Start command handled for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for search"""
    try:
        if not sheet:
            await update.message.reply_text("🚫 Database connection error. Please try again later.")
            return

        query = update.message.text.strip().lower()
        logger.info(f"Search query: {query}")

        # Get data from Google Sheets
        data = sheet.get_all_records()
        
        # Search for matches
        results = [
            row for row in data
            if query in row.get("Name", "").lower() or query in row.get("Category", "").lower()
        ]

        if results:
            count = min(len(results), 5)  # Show max 5 results
            await update.message.reply_text(f"🎯 Found {len(results)} matches. Showing top {count}:")
            
            for row in results[:5]:
                name = row.get("Name", "No Title")
                link = row.get("Link", "No Link")
                category = row.get("Category", "Unknown")
                
                text = f"🎥 <b>{name}</b>\n📁 Category: {category}\n🔗 <a href='{link}'>Watch Now</a>"
                await update.message.reply_html(text, disable_web_page_preview=True)
        else:
            await update.message.reply_text(
                f"🚫 No matches found for '{query}'.\n"
                "Try different keywords or check spelling."
            )
            
        logger.info(f"Search completed: {len(results)} results for '{query}'")
        
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage bot lifecycle"""
    global application
    try:
        logger.info("🚀 Starting bot initialization...")
        
        # Build application
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .build()
        )
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Initialize and start
        await application.initialize()
        logger.info("✅ Application initialized")
        
        await application.start()
        logger.info("✅ Application started")
        
        # Set webhook
        webhook_url = f"{WEBHOOK_URL}/telegram/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to {webhook_url}")
        
        # Get bot info
        bot_info = await application.bot.get_me()
        logger.info(f"✅ Bot @{bot_info.username} is ready!")
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔻 Shutting down bot...")
    try:
        if application:
            await application.stop()
            await application.shutdown()
        logger.info("✅ Bot shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="MonkTV Bot",
    description="Telegram bot for movie searches",
    version="1.0.0",
    lifespan=lifespan
)

# Health check endpoint
@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "bot_ready": application is not None and application.bot is not None,
        "message": "MonkTV Bot is running"
    }

# Webhook endpoint
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    global application
    
    try:
        # Check if bot is ready
        if not application or not application.bot:
            logger.error("Bot not ready - application not initialized")
            raise HTTPException(status_code=503, detail="Bot not ready")
        
        # Get update data
        data = await request.json()
        logger.info(f"📨 Received webhook update: {data.get('update_id', 'unknown')}")
        
        # Process update
        update = Update.de_json(data, application.bot)
        if update:
            await application.process_update(update)
            logger.info("✅ Update processed successfully")
        else:
            logger.warning("⚠️ Invalid update received")
            
        return {"ok": True}
        
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in webhook request")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"❌ Unhandled exception: {exc}")
    return {"error": "Internal server error", "detail": str(exc)}

if __name__ == "__main__":
    # For local development
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)