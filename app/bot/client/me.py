import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.bot.helper.index import check_user_exists, require_user

# Import the new synchronous service function
from app.bot.services.me import get_me_sync


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("جاري جلب بينات حسابك، الرجاء الانتظار….")

    # اجلب بيانات المستخدم من الداتا بيز في Thread منفصل
    user = await check_user_exists(update, context)

    if user:
        # إعداد رسالة الترحيب
        welcome_message = (
            f"👋 مرحباً {user.display_name or user.full_name}!\n\n"
            f"📧 الإيميل: {user.email}\n"
            f"📱 رقم الهاتف: {user.phone_number}\n"
            f"👨‍👩‍👦 هاتف ولي الأمر: {user.parent_phone_number}\n"
            f"💡 الحالة: {'مفعل ✅' if user.is_active else 'غير مفعل ❌'}\n"
            f"✔️ التحقق: {'موثق ✅' if user.is_verified else 'غير موثق ❌'}\n"
            f"💬 تليجرام: @{user.telegram_username or '-'} "
            f"({user.telegram_first_name} {user.telegram_last_name})\n"
            f"📅 آخر تسجيل دخول: {user.last_login}\n"
        )

        # زر Inline لرصيد المحفظة
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"💰 الرصيد: {user.wallet_balance} ج.م",
                        callback_data="wallet_balance",
                    ),
                ],
                [
                    InlineKeyboardButton("حسابي 👤", callback_data="profile"),
                ],
                [
                    InlineKeyboardButton("كورساتي 📚", callback_data="my_courses"),
                    InlineKeyboardButton(
                        "الكورسات المقترحة 📢", callback_data="suggested_courses"
                    ),
                    InlineKeyboardButton("كل الكورسات 🧺", callback_data="all_courses"),
                ],
                [InlineKeyboardButton("المنتدي 👥", callback_data="community")],
            ]
        )

        await update.message.reply_text(welcome_message, reply_markup=keyboard)

    else:
        await update.message.reply_text(
            "حسابك غير مربوط على المنصة 🚫\n\nانشئ حسابك من خلال الرابط التالي 👇🏼",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📝 إنشاء حساب", url="http://127.0.0.1/register"
                        )
                    ]
                ]
            ),
        )


async def wallet_balance_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = await check_user_exists(update, context)

    if user:
        # إرسال الـ Balance في Popup
        await query.answer(
            f"💰 رصيدك الحالي: {user.wallet_balance} ج.م", show_alert=True
        )
    else:
        await query.answer("⚠️ لم يتم العثور على بيانات المستخدم.", show_alert=True)


async def profile(update: Update, context: CallbackContext):
    query = update.callback_query
    user = await asyncio.to_thread(get_me_sync, update.effective_user.id)

    if user:
        # إنشاء زر جديد (لو عايز تخليه يتحدث أو يفضل نفس الزر)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"💰 الرصيد: {user.wallet_balance} ج.م",
                        callback_data="wallet_balance",
                    )
                ],
                [InlineKeyboardButton("الرجوع للقائمة الرئيسية", callback_data="back")],
            ]
        )

        # تعديل الرسالة الأصلية وإظهار الرصيد
        await query.edit_message_text(
            text=f"👋 مرحباً {user.display_name or user.full_name}!\n\n"
            f"💰 رصيدك الحالي: {user.wallet_balance} ج.م",
            reply_markup=keyboard,
        )
    else:
        await query.edit_message_text("⚠️ لم يتم العثور على بيانات المستخدم.")


async def back(update: Update, context: CallbackContext):
    user = await check_user_exists(update, context)
    query = update.callback_query
    welcome_message = (
        f"👋 مرحباً {user.display_name or user.full_name}!\n\n"
        f"📧 الإيميل: {user.email}\n"
        f"📱 رقم الهاتف: {user.phone_number}\n"
        f"👨‍👩‍👦 هاتف ولي الأمر: {user.parent_phone_number}\n"
        f"💡 الحالة: {'مفعل ✅' if user.is_active else 'غير مفعل ❌'}\n"
        f"✔️ التحقق: {'موثق ✅' if user.is_verified else 'غير موثق ❌'}\n"
        f"💬 تليجرام: @{user.telegram_username or '-'} "
        f"({user.telegram_first_name} {user.telegram_last_name})\n"
        f"📅 آخر تسجيل دخول: {user.last_login}\n"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"💰 الرصيد: {user.wallet_balance} ج.م",
                    callback_data="wallet_balance",
                ),
            ],
            [
                InlineKeyboardButton("حسابي 👤", callback_data="profile"),
            ],
            [
                InlineKeyboardButton("كورساتي 📚", callback_data="my_courses"),
                InlineKeyboardButton(
                    "الكورسات المقترحة 📢", callback_data="suggested_courses"
                ),
                InlineKeyboardButton("كل الكورسات 🧺", callback_data="all_courses"),
            ],
            [InlineKeyboardButton("المنتدي 👥", callback_data="community")],
        ]
    )
    await query.edit_message_text(
        text=welcome_message,
        reply_markup=keyboard,
    )


# Register all user handlers
def register_user_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        CallbackQueryHandler(wallet_balance_callback, pattern="wallet_balance")
    )
    app.add_handler(CallbackQueryHandler(profile, pattern="profile"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
