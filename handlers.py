from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from config import COMPLIMENTS, MAX_TEXT_LENGTH
from database import Database
from utils2 import ImageProcessor, format_sender_info, truncate_text
from uuid import uuid4
import random
import os

db = Database()

# Состояния диалога
CHOOSE_MODE, ENTER_TEXT, CHOOSE_TEMPLATE, CHOOSE_RECIPIENT, CHOOSE_ANONYMOUS, CONFIRM = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда"""
    user = update.effective_user
    db.add_user(user.id, user.username or f"user_{user.id}", user.first_name, user.last_name or "")
    
    # Проверяем очередь
    queued = db.get_queued_valentines(user.username or f"user_{user.id}")
    if queued:
        await send_queued_valentines(update, context, queued, user)
    
    keyboard = [
        [InlineKeyboardButton("💌 Отправить послание", callback_data="send_valentine")],
        [InlineKeyboardButton("✨ Вдохновение дня", callback_data="get_compliment")],
        [InlineKeyboardButton("🤖 Панель Комитета", callback_data="admin_panel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        f"🤖 Добро пожаловать в ПочтИИИ — сервис Института искусственного интеллекта! 💝\n\n"
        f"Здесь ты можешь отправить послание, которое давно было на душе.\n\n"
        f"Скажи то, что хотел, но боялся произнести вслух.\n",
        reply_markup=reply_markup
    )


async def send_valentine_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса отправки послания"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 Текстовое послание", callback_data="valentine_text")],
        [InlineKeyboardButton("🎨 С красивой визуализацией", callback_data="valentine_image")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🌟 Как ты хочешь выразить свои чувства?\n\n"
             "Выбери формат послания:",
        reply_markup=reply_markup
    )
    
    return CHOOSE_MODE


async def choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор адресата"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "valentine_text":
        context.user_data['valentine_type'] = 'text'
    else:
        context.user_data['valentine_type'] = 'image'
    
    await query.edit_message_text(
        text="👤 Кому адресовано это послание?\n\n"
             "Напиши @username адресата (например: @ivan_vasya)"
    )
    
    return CHOOSE_RECIPIENT


async def process_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбранного адресата"""
    text = update.message.text
    
    # Парсим username
    if text.startswith('@'):
        username = text[1:]
    else:
        username = text
    
    if len(username) > 32 or len(username) < 3:
        await update.message.reply_text("❌ Неверное имя пользователя (от 3 до 32 символов)")
        return CHOOSE_RECIPIENT
    
    context.user_data['recipient_username'] = username
    
    await update.message.reply_text(
        "✍️ Теперь напиши то, что давно было на душе.\n\n"
        "Максимум 250 символов — делись своей историей:"
    )
    
    return ENTER_TEXT


async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста послания"""
    text = update.message.text
    
    if len(text) > MAX_TEXT_LENGTH:
        await update.message.reply_text(
            f"⚠️ Послание слишком длинное! Максимум {MAX_TEXT_LENGTH} символов.\n"
            f"Твой текст: {len(text)} символов\n\n"
            f"Пожалуйста, сократи текст или оставь самое важное."
        )
        return ENTER_TEXT
    
    if len(text) < 3:
        await update.message.reply_text("⚠️ Послание слишком короткое! Минимум 3 символа.")
        return ENTER_TEXT
    
    context.user_data['valentine_text'] = text
    
    if context.user_data['valentine_type'] == 'image':
        keyboard = [
            [InlineKeyboardButton("🌹 Стиль Шаблон 1", callback_data="template_1")],
            [InlineKeyboardButton("💎 Шаблон 2", callback_data="template_2")],
            [InlineKeyboardButton("🔥 Шаблон 3", callback_data="template_3")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎨 Выбери стиль визуализации послания:\n\n"
            "Каждый стиль создаст уникальный дизайн для твоего послания",
            reply_markup=reply_markup
        )
        
        return CHOOSE_TEMPLATE
    else:
        return await choose_anonymous(update, context)


async def template_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по стилям"""
    query = update.callback_query
    await query.answer(
        "Выбери понравившийся стиль оформления. "
        "Твой текст будет красиво размещен на фоне в выбранном стиле.",
        show_alert=True
    )


async def choose_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор стиля"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "template_help":
        await template_help(update, context)
        return CHOOSE_TEMPLATE
    
    template_id = int(data.split('_')[1])
    context.user_data['template_id'] = template_id
    
    # Сразу пытаемся создать послание для проверки
    valentine_text = context.user_data['valentine_text']
    sender = query.from_user
    
    await query.edit_message_text(
        text="✨ Создаю твое послание...\n\n⏳ Пожалуйста, подожди немного..."
    )
    
    # Создаем послание
    result = ImageProcessor.create_valentine(template_id, valentine_text, sender.first_name)
    
    if result["success"]:
        context.user_data['image_path'] = result["path"]
        context.user_data['template_id'] = template_id
        
        # Показываем превью
        try:
            with open(result["path"], 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=query.from_user.id,
                    photo=photo,
                    caption="🌟 Вот как выглядит твое послание!\n\n"
                )
        except Exception as e:
            print(f"Ошибка отправки превью: {e}")
            await query.edit_message_text(
                text="⚠️ Не удалось показать превью, но послание создано и готово к отправке!\n\n"
                     "Продолжим?"
            )
            return await choose_anonymous(update, context)
    else:
        # Показываем ошибку и предлагаем текстовое послание
        error_message = (
            f"{result['message']}\n\n"
            f"🔧 Техническая информация:\n"
            f"`{result['error']}`\n\n"
            f"💡 Рекомендация: Используй текстовое послание без оформления"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Отправить текстом", callback_data="switch_to_text")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=error_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['has_error'] = True
        return CHOOSE_TEMPLATE


async def continue_sending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Продолжить отправку после превью"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "continue_send":
        return await choose_anonymous(update, context)
    elif query.data == "change_template":
        keyboard = [
            [InlineKeyboardButton("🌹 Шаблон 1", callback_data="template_1")],
            [InlineKeyboardButton("💎 Шаблон 2", callback_data="template_2")],
            [InlineKeyboardButton("🔥 Шаблон 3", callback_data="template_3")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="🎨 Выбери другой стиль оформления:",
            reply_markup=reply_markup
        )
        return CHOOSE_TEMPLATE
    elif query.data == "switch_to_text":
        context.user_data['valentine_type'] = 'text'
        return await choose_anonymous(update, context)
    
    return CHOOSE_TEMPLATE


async def choose_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор анонимности"""
    keyboard = [
        [InlineKeyboardButton("🔐 Анонимно", callback_data="anon_yes")],
        [InlineKeyboardButton("✍️ От себя", callback_data="anon_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        try:
            await query.edit_message_text(
                text="🤫 Отправить анонимно или подписать своим именем?\n\n"
                     "Выбери, как ты хочешь выразить свои чувства:",
                reply_markup=reply_markup
            )
        except:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="🤫 Отправить анонимно или подписать своим именем?\n\n"
                     "Выбери, как ты хочешь выразить свои чувства:",
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            text="🤫 Отправить анонимно или подписать своим именем?\n\n"
                 "Выбери, как ты хочешь выразить свои чувства:",
            reply_markup=reply_markup
        )
    
    return CHOOSE_ANONYMOUS


async def process_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора анонимности"""
    query = update.callback_query
    await query.answer()
    
    is_anonymous = query.data == "anon_yes"
    context.user_data['is_anonymous'] = is_anonymous
    
    # Подтверждение и отправка
    return await confirm_and_send(update, context)


async def confirm_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и отправка послания"""
    query = update.callback_query
    user = query.from_user
    
    recipient_username = context.user_data['recipient_username']
    valentine_text = context.user_data['valentine_text']
    is_anonymous = context.user_data['is_anonymous']
    valentine_type = context.user_data['valentine_type']
    
    # Проверяем существование адресата
    recipient = db.get_user_by_username(recipient_username)
    
    image_path = None
    template_id = None
    
    if valentine_type == 'image':
        # Если мы уже создавали послание, используем сохраненный путь
        if 'image_path' in context.user_data:
            image_path = context.user_data['image_path']
            template_id = context.user_data.get('template_id', 1)
        else:
            template_id = context.user_data.get('template_id', 1)
            result = ImageProcessor.create_valentine(template_id, valentine_text, user.first_name)
            
            if result["success"]:
                image_path = result["path"]
            else:
                await query.edit_message_text(
                    text=f"❌ Ошибка создания послания:\n\n{result['message']}"
                )
                return ConversationHandler.END
    
    if recipient:
        # Отправляем напрямую
        recipient_id = recipient['user_id']
        db.save_valentine(user.id, recipient_id, recipient_username, 
                         valentine_text, template_id, is_anonymous)
        
        await send_valentine_to_user(
            context, recipient_id, user, valentine_text, 
            image_path, is_anonymous, valentine_type
        )
        
        await query.edit_message_text(
            text=f"✨ Твое послание в пути! 💌\n\n"
                 f"Оно отправлено @{recipient_username}\n"
                 f"Спасибо, что поделился своими чувствами! 💝"
        )
    else:
        # Добавляем в очередь
        db.queue_valentine(user.id, recipient_username, valentine_text, 
                          template_id, is_anonymous)
        
        await query.edit_message_text(
            text=f"📬 Твое послание добавлено в очередь!\n\n"
                 f"Как только @{recipient_username} откроет ПочтИИИ, он получит твое послание.\n\n"
        )
    
    # Удаляем временный файл (если он был)
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception as e:
            print(f"⚠️ Не удалось удалить временный файл: {e}")
    
    # Очищаем данные
    context.user_data.clear()
    
    return ConversationHandler.END


async def send_valentine_to_user(context, user_id, sender, text, image_path, 
                                 is_anonymous, valentine_type):
    """Отправить послание пользователю"""
    sender_info = format_sender_info(sender.id, sender.first_name, is_anonymous)
    
    message_text = f"💌 Тебе пришло послание из ПочтИИИ! 🤖\n\n{text}\n\n{sender_info}"
    
    try:
        if valentine_type == 'image' and image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=message_text,
                    parse_mode=ParseMode.HTML
                )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"❌ Ошибка отправки послания: {e}")


async def send_queued_valentines(update, context, queued, user):
    """Отправить послания из очереди"""
    
    for valentine in queued:
        sender_id = valentine['sender_id']
        try:
            sender = await context.bot.get_chat(sender_id)
            sender_name = sender.first_name
        except:
            sender_name = "Неизвестный"
        
        sender_info = format_sender_info(sender_id, sender_name, valentine['is_anonymous'])
        message_text = f"💌 Тебе пришло послание из ПочтИИИ! 🤖\n\n{valentine['text']}\n\n{sender_info}"
        
        if valentine['image_template']:
            result = ImageProcessor.create_valentine(
                valentine['image_template'], 
                valentine['text'],
                sender_name
            )
            if result["success"]:
                image_path = result["path"]
                try:
                    with open(image_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=user.id,
                            photo=photo,
                            caption=message_text
                        )
                    db.remove_from_queue(valentine['id'])
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    continue
                except Exception as e:
                    print(f"⚠️ Ошибка отправки послания из очереди: {e}")
        
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=message_text
            )
            db.remove_from_queue(valentine['id'])
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")


async def get_compliment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить вдохновение дня"""
    query = update.callback_query
    await query.answer()
    
    compliment = random.choice(COMPLIMENTS)
    await query.edit_message_text(text=f"🌟 {compliment}")


async def show_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать пригласительную ссылку для всех пользователей"""
    query = update.callback_query
    await query.answer()
    
    # Получаем информацию о боте
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "ПочтИИИ"
    
    # Создаем ссылку для приглашения
    invite_url = f"https://t.me/{bot_username}"
    
    # Создаем пригласительное сообщение
    invite_message = (
        f"✨ Приглашение в ПочтИИИ ✨\n\n"
        f"🤖 Добро пожаловать в Почту Института Искусственного Интеллекта!\n\n"
        f"💝 Здесь ты можешь отправить послание, которое давно было на душе.\n"
        f"Скажи то, что хотел, но боялся произнести вслух.\n\n"
        f"📬 К 14 февраля — дню всех влюбленных — делись своими чувствами!\n\n"
        f"👇 Нажми кнопку ниже и откройте сердце:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💌 Открыть ПочтИИИ", url=invite_url)],
        [InlineKeyboardButton("📋 Скопировать ссылку", callback_data="copy_invite_link")],
        [InlineKeyboardButton("📤 Поделиться в чате", callback_data="share_invite")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Ссылка на картинку для демонстрации
    image_url = "https://images.unsplash.com/photo-1518895949257-7621c3c786d7?w=500&h=500&fit=crop"
    
    try:
        # Отправляем сообщение с картинкой
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=image_url,
            caption=invite_message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # Удаляем старое сообщение
        await query.delete_message()
    except Exception as e:
        print(f"Ошибка отправки картинки: {e}")
        
        # Если картинка не загружается, отправляем текст
        await query.edit_message_text(
            text=invite_message,
            reply_markup=reply_markup
        )


async def copy_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скопировать пригласительную ссылку"""
    query = update.callback_query
    await query.answer()
    
    # Получаем информацию о боте
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "ПочтИИИ"
    
    # Создаем ссылку для приглашения
    invite_url = f"https://t.me/{bot_username}"
    
    # Создаем сообщение для копирования
    copy_message = (
        f"🔗 Пригласительная ссылка ПочтИИИ:\n\n"
        f"`{invite_url}`\n\n"
        f"Подели��ь этой ссылкой со своими друзьями и однокурсниками!\n\n"
        f"(Нажми на ссылку выше, чтобы скопировать)"
    )
    
    keyboard = [
        [InlineKeyboardButton("💌 Открыть ПочтИИИ", url=invite_url)],
        [InlineKeyboardButton("🔙 Назад", callback_data="show_invite_link")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=copy_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def share_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поделиться приглашением в чате"""
    query = update.callback_query
    await query.answer()
    
    # Получаем информацию о боте
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "ПочтИИИ"
    
    # Создаем ссылку для приглашения
    invite_url = f"https://t.me/{bot_username}"
    
    # Создаем сообщение для отправки в чаты
    share_message = (
        f"✨ Приглашаю вас в ПочтИИИ! ✨\n\n"
        f"🤖 Почта Института Искусственного Интеллекта\n\n"
        f"💝 Здесь ты можешь отправить послание, которое давно было на душе.\n\n"
        f"👇 Присоединяйся:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💌 Открыть ПочтИИИ", url=invite_url)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение в текущий чат (либо используем Web App API)
    await query.edit_message_text(
        text=share_message,
        reply_markup=reply_markup
    )
    
    # Показываем уведомление
    await query.answer(
        "Готово! Используй эту ссылку, чтобы пригласить друзей в ПочтИИИ",
        show_alert=False
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💌 Отправить послание", callback_data="send_valentine")],
        [InlineKeyboardButton("✨ Вдохновение ��ня", callback_data="get_compliment")],
        [InlineKeyboardButton("🔗 Пригласить друзей", callback_data="show_invite_link")],
        [InlineKeyboardButton("🤖 Панель ИИ", callback_data="admin_panel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🏠 Главное меню ПочтИИИ",
        reply_markup=reply_markup
    )


async def inline_compliment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline режим для вдохновения"""
    query = update.inline_query
    
    if query.query.lower() in ["вдохновение", "inspiration", ""]:
        compliment = random.choice(COMPLIMENTS)
        
        result = InlineQueryResultArticle(
            id=str(uuid4()),
            title="✨ Вдохновение дня",
            description=compliment,
            input_message_content=InputTextMessageContent(
                message_text=f"🌟 {compliment}"
            )
        )
        
        await context.bot.answer_inline_query(query.id, [result])


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    query = update.callback_query
    await query.answer()
    
    # Удаляем временные файлы
    if 'image_path' in context.user_data and os.path.exists(context.user_data['image_path']):
        try:
            os.remove(context.user_data['image_path'])
        except:
            pass
    
    context.user_data.clear()
    
    await query.edit_message_text(
        text="❌ Отменено. Введите /start, чтобы начать заново"
    )
    return ConversationHandler.END