import asyncio
import functools

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

# Import the new synchronous service function
from app.bot.services.me import get_me_sync


async def check_user_exists(update: Update, context: CallbackContext):
    """يتحقق هل المستخدم موجود في قاعدة البيانات أم لا"""
    tg_user = update.effective_user

    user = await asyncio.to_thread(get_me_sync, tg_user.id)

    if not user:
        # لو المستخدم غير موجود، ابعت له رسالة مباشرة
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            text="⚠️ حسابك غير مربوط على المنصة، من فضلك أنشئ حسابك من خلال الرابط التالي 👇🏼\n"
            "http://127.0.0.1/register",
        )
        return None

    return user


def require_user(func):
    """ديكوريتر يتحقق من المستخدم قبل تنفيذ أي handler"""

    @functools.wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        tg_user = update.effective_user
        user = await asyncio.to_thread(get_me_sync, tg_user.id)

        if not user:
            await update.effective_message.reply_text(
                "⚠️ حسابك غير مربوط على المنصة.\n"
                "📝 أنشئ حسابك من هنا: http://127.0.0.1/register"
            )
            return None  # يوقف التنفيذ

        # لو المستخدم موجود، كمل الكود وأرسله للدالة الأصلية
        return await func(update, context, user=user, *args, **kwargs)

    return wrapper
