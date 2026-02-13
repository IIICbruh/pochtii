from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import Database

db = Database()

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть панель администратора ИИ"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверка доступа
    if user_id != ADMIN_ID:
        await query.edit_message_text(
            "❌ У вас нет доступа к панели ИИ. "
            "Это может сделать только администратор Института."
        )
        return
    
    stats = db.get_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика ПочтИИИ", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Отправить объявление", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Вернуться", callback_data="admin_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"🤖 Панель управления ПочтИИИ\n"
        f"(Система Почты Института Искусственного Интеллекта)\n\n"
        f"📊 Статистика:\n"
        f"👥 Студентов в системе: {stats['total_users']}\n"
        f"💌 Посланий доставлено: {stats['delivered']}\n"
        f"📬 Ждет доставки: {stats['in_queue']}\n"
    )
    
    await query.edit_message_text(text=text, reply_markup=reply_markup)


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить объявление всем"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        text="📝 Напиши объявление для всех студентов ПочтИИИ:\n\n"
             "(Введи 'отмена' для выхода)"
    )
    
    context.user_data['waiting_broadcast'] = True


async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать объявление"""
    if not context.user_data.get('waiting_broadcast'):
        return
    
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text.lower() == 'отмена':
        await update.message.reply_text("❌ Объявление отменено")
        context.user_data['waiting_broadcast'] = False
        return
    
    # Получаем всех пользователей
    users = db.get_all_users()
    
    success = 0
    failed = 0
    
    broadcast_text = (
        f"📢 Объявление от ПочтИИИ (Почта Института Искусственного Интеллекта):\n\n"
        f"{text}\n\n"
        f"🤖 Спасибо за использование нашего сервиса!"
    )
    
    for user_id_to_send in users:
        try:
            await context.bot.send_message(chat_id=user_id_to_send, text=broadcast_text)
            success += 1
        except Exception as e:
            print(f"Не удалось отправить пользователю {user_id_to_send}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ Объявление распространено!\n\n"
        f"📬 Доставлено студентам: {success}\n"
        f"⚠️ Ошибок: {failed}\n\n"
        f"Спасибо за работу в системе ПочтИИИ!"
    )
    
    context.user_data['waiting_broadcast'] = False


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💌 Отправить послание", callback_data="send_valentine")],
        [InlineKeyboardButton("✨ Вдохновение дня", callback_data="get_compliment")],
        [InlineKeyboardButton("🤖 Панель Комитета", callback_data="admin_panel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🏠 Главное меню ПочтИИИ",
        reply_markup=reply_markup
    )