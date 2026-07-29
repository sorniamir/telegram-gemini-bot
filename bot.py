import os
import google.generativeai as genai

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""
تو یک دستیار هوش مصنوعی فارسی‌زبان، دقیق، محترمانه و کاربردی هستی.
جواب‌ها را ساده، واضح و مرحله‌به‌مرحله بده.
اگر سوال کاربر فارسی بود، فارسی جواب بده.
اگر سوال انگلیسی بود، انگلیسی جواب بده.
از جواب‌های خیلی طولانی بی‌دلیل پرهیز کن.
"""
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من ربات هوش مصنوعی تو هستم 🤖\nهر سوالی داری بپرس."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "کافیه پیام خودت رو بفرستی تا جواب بدم.\n"
        "مثلاً:\n"
        "طراحی لباس بهم پیشنهاد بده\n"
        "یه متن تبلیغاتی بنویس\n"
        "این جمله رو ترجمه کن"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    if not user_message:
        await update.message.reply_text("لطفاً یک پیام متنی بفرست.")
        return

    try:
        waiting_message = await update.message.reply_text("در حال فکر کردن...")

        response = model.generate_content(user_message)

        answer = response.text

        if not answer:
            answer = "متأسفم، نتونستم جواب مناسبی تولید کنم."

        await waiting_message.edit_text(answer)

    except Exception as e:
        print("Error:", e)
        await update.message.reply_text(
            "متأسفم، الان مشکلی پیش آمد. کمی بعد دوباره امتحان کن."
        )


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
