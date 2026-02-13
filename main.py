import logging
import sys
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ConversationHandler, filters
)
from config import BOT_TOKEN, ADMIN_ID
from handlers import (
    start, send_valentine_start, choose_recipient, process_recipient,
    process_text, choose_template, process_anonymous, cancel,
    get_compliment, inline_compliment, continue_sending, show_invite_link, 
    back_to_menu, copy_invite_link, share_invite,
    CHOOSE_MODE, CHOOSE_RECIPIENT, ENTER_TEXT, CHOOSE_TEMPLATE, CHOOSE_ANONYMOUS
)
from admin_panel import admin_panel, broadcast_message, process_broadcast, admin_back

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота ПочтИИИ"""
    
    # Проверяем токен
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: BOT_TOKEN не установлен!")
        print("📝 Пожалуйста, отредактируйте файл .env и добавьте ваш токен")
        print("📌 Получите токен у @BotFather в Telegram")
        return
    
    if ADMIN_ID == 0:
        print("⚠️ ВНИМАНИЕ: ADMIN_ID не установлен!")
        print("📝 Пожалуйста, отредактируйте файл .env и добавьте ваш ID")
        print("📌 Узнайте ID у @userinfobot в Telegram")
    
    print("\n" + "="*60)
    print("🤖 Инициализация ПочтИИИ")
    print("(Почта Института Искусственного Интеллекта)")
    print("="*60)
    print("✅ BOT_TOKEN загружен")
    print(f"👤 ADMIN_ID: {ADMIN_ID if ADMIN_ID != 0 else 'не установлен'}")
    
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    print("✅ Приложение создано")

    # Диалог отправки послания
    valentine_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(send_valentine_start, pattern="send_valentine")],
        states={
            CHOOSE_MODE: [
                CallbackQueryHandler(choose_recipient, pattern="valentine_text|valentine_image"),
                CallbackQueryHandler(cancel, pattern="cancel"),
            ],
            CHOOSE_RECIPIENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_recipient),
            ],
            ENTER_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_text),
            ],
            CHOOSE_TEMPLATE: [
                CallbackQueryHandler(choose_template, pattern="template_[1-3]|template_help"),
                CallbackQueryHandler(continue_sending, pattern="continue_send|change_template|switch_to_text"),
                CallbackQueryHandler(cancel, pattern="cancel"),
            ],
            CHOOSE_ANONYMOUS: [
                CallbackQueryHandler(process_anonymous, pattern="anon_yes|anon_no"),
                CallbackQueryHandler(cancel, pattern="cancel"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="cancel")],
    )

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))

    # Диалог послания
    app.add_handler(valentine_conv_handler)

    # Callback обработчики
    app.add_handler(CallbackQueryHandler(get_compliment, pattern="get_compliment"))
    app.add_handler(CallbackQueryHandler(show_invite_link, pattern="show_invite_link"))
    app.add_handler(CallbackQueryHandler(copy_invite_link, pattern="copy_invite_link"))
    app.add_handler(CallbackQueryHandler(share_invite, pattern="share_invite"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
    app.add_handler(CallbackQueryHandler(broadcast_message, pattern="admin_broadcast"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="admin_back"))

    # Inline режим
    app.add_handler(InlineQueryHandler(inline_compliment))

    # Обработчик для объявлений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        process_broadcast
    ))

    print("✅ Обработчики добавлены")
    
    # Запуск бота
    print("\n" + "="*60)
    print("🚀 ПочтИИИ ГОТОВА К РАБОТЕ!")
    print("="*60)
    print("\n📍 Откройте Telegram и найдите бота @ПочтИИИ")
    print("💬 Напишите /start для начала работы")
    print("💌 Делитесь посланиями, которые давно были на душе!")
    print("\n🤖 Спасибо, что используете Почту Института ИИ!")
    print("❤️  К 14 февраля — дню всех влюбленных!")
    print("\n⏹️  Для остановки нажмите Ctrl+C\n")
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n\n⏹️  ПочтИИИ остановлена")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return


if __name__ == '__main__':
    main()