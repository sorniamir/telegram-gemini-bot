import os
import logging

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# نمایش خطاها در Railway Logs
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# دریافت اطلاعات از Environment Variables در Railway
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# می‌توانی بعداً در Railway متغیر OPENROUTER_MODEL را نیز اضافه کنی.
# اگر اضافه نشود، OpenRouter به‌صورت خودکار یک مدل رایگان انتخاب می‌کند.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")


# اتصال به OpenRouter
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com/",
        "X-Title": "Persian Telegram AI Bot",
    },
)


SYSTEM_PROMPT = """
تو یک دستیار هوش مصنوعی فارسی‌زبان، دقیق، محترمانه و کاربردی هستی.
جواب‌ها را ساده، واضح و مرحله‌به‌مرحله بده.
اگر سؤال کاربر فارسی بود، فارسی جواب بده.
اگر سؤال کاربر انگلیسی بود، انگلیسی جواب بده.
از جواب‌های خیلی طولانی و غیرضروری خودداری کن.
اگر درباره موضوعی مطمئن نیستی، صادقانه اعلام کن.
"""


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message:
        await update.message.reply_text(
            "سلام! من ربات هوش مصنوعی تو هستم 🤖\n"
            "هر سؤالی داری بپرس."
        )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message:
        await update.message.reply_text(
            "کافیه پیام خودت رو برام بفرستی تا جواب بدم.\n\n"
            "مثلاً:\n"
            "• طراحی لباس بهم پیشنهاد بده\n"
            "• یک متن تبلیغاتی بنویس\n"
            "• این جمله رو ترجمه کن"
        )


async def send_long_answer(waiting_message, answer: str):
    """
    تلگرام برای هر پیام محدودیت تعداد کاراکتر دارد.
    جواب‌های طولانی را به چند پیام تقسیم می‌کند.
    """
    max_length = 4000
    parts = [
        answer[i:i + max_length]
        for i in range(0, len(answer), max_length)
    ]

    if not parts:
        parts = ["متأسفم، پاسخ خالی دریافت شد."]

    await waiting_message.edit_text(parts[0])

    for part in parts[1:]:
        await waiting_message.reply_text(part)


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()

    if not user_message:
        await update.message.reply_text(
            "لطفاً یک پیام متنی بفرست."
        )
        return

    waiting_message = await update.message.reply_text(
        "در حال فکر کردن... 🤔"
    )

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.7,
            max_tokens=1200,
        )

        answer = response.choices[0].message.content

        if not answer:
            answer = "متأسفم، نتونستم پاسخ مناسبی تولید کنم."

        await send_long_answer(
            waiting_message,
            answer.strip(),
        )

    except Exception as error:
        logger.exception("OpenRouter error: %s", error)

        error_text = str(error).lower()

        if "401" in error_text or "unauthorized" in error_text:
            message = (
                "کلید OpenRouter معتبر نیست. "
                "لطفاً OPENROUTER_API_KEY را در Railway بررسی کن."
            )

        elif "429" in error_text or "rate limit" in error_text:
            message = (
                "سرویس فعلاً شلوغ است یا محدودیت استفاده فعال شده. "
                "کمی بعد دوباره امتحان کن."
            )

        elif "404" in error_text or "model" in error_text:
            message = (
                "مدل هوش مصنوعی فعلاً در دسترس نیست. "
                "لطفاً کمی بعد دوباره امتحان کن."
            )

        else:
            message = (
                "متأسفم، هنگام اتصال به هوش مصنوعی مشکلی پیش آمد. "
                "کمی بعد دوباره امتحان کن."
            )

        try:
            await waiting_message.edit_text(message)
        except Exception:
            await update.message.reply_text(message)


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.exception(
        "Telegram bot error:",
        exc_info=context.error,
    )


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is missing in Railway Variables"
        )

    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is missing in Railway Variables"
        )

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    app.add_error_handler(error_handler)

    logger.info(
        "Bot is running with model: %s",
        OPENROUTER_MODEL,
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
