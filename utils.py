from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from config import TEMPLATES_PATH, FONTS_PATH, MAX_TEXT_LENGTH
import os
from datetime import datetime

class ImageProcessor:
    """Обработка изображений валентинок"""
    
    TEMPLATES = {
        1: {"path": f"{TEMPLATES_PATH}/template1.png", "text_pos": (50, 300), "width": 700},
        2: {"path": f"{TEMPLATES_PATH}/template2.png", "text_pos": (100, 250), "width": 600},
        3: {"path": f"{TEMPLATES_PATH}/template3.png", "text_pos": (80, 350), "width": 650},
    }
    
    @staticmethod
    def create_valentine(template_id: int, text: str, sender_name: str = "Unknown") -> dict:
        """
        Создать валентинку с текстом на шаблоне
        
        Returns:
            {
                "success": bool,
                "path": str (путь к файлу),
                "error": str (описание ошибки, если есть),
                "message": str (сообщение для пользователя)
            }
        """
        if template_id not in ImageProcessor.TEMPLATES:
            return {
                "success": False,
                "path": None,
                "error": f"Шаблон #{template_id} не найден",
                "message": f"❌ Ошибка: Шаблон #{template_id} не существует. Доступны шаблоны: 1, 2, 3"
            }
        
        template_info = ImageProcessor.TEMPLATES[template_id]
        template_path = template_info["path"]
        
        # Проверяем существование шаблона
        if not os.path.exists(template_path):
            return {
                "success": False,
                "path": None,
                "error": f"Файл шаблона не найден: {template_path}",
                "message": f"❌ Ошибка: Файл шаблона не найден!\n\n"
                           f"📁 Ожидаемый путь: `{template_path}`\n\n"
                           f"Пожалуйста, проверьте, что папка `templates` содержит файл `template{template_id}.png`"
            }
        
        # Проверяем шрифт
        if not os.path.exists(FONTS_PATH):
            return {
                "success": False,
                "path": None,
                "error": f"Шрифт не найден: {FONTS_PATH}",
                "message": f"❌ Ошибка: Шрифт не найден!\n\n"
                           f"📁 Ожидаемый путь: `{FONTS_PATH}`\n\n"
                           f"Пожалуйста, добавьте файл `Involve.ttf` в папку `fonts`"
            }
        
        try:
            # Открываем шаблон
            img = Image.open(template_path)
            draw = ImageDraw.Draw(img)
            
            # Загружаем шрифт
            try:
                font = ImageFont.truetype(FONTS_PATH, size=36)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки шрифта: {e}")
                # Используем шрифт по умолчанию
                font = ImageFont.load_default()
            
            # Форматируем текст
            wrapped_text = ImageProcessor.wrap_text(text, template_info["width"])
            
            # Рисуем текст
            y_position = template_info["text_pos"][1]
            text_color = (255, 105, 180)  # Hot pink
            
            for line in wrapped_text:
                try:
                    draw.text(
                        (template_info["text_pos"][0], y_position),
                        line,
                        fill=text_color,
                        font=font,
                        anchor="lm"
                    )
                except Exception as e:
                    print(f"⚠️ Ошибка рисования текста: {e}")
                    # Пытаемся рисовать с другими параметрами
                    draw.text(
                        (template_info["text_pos"][0], y_position),
                        line,
                        fill=text_color
                    )
                
                y_position += 50
            
            # Создаем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in sender_name)[:20]
            output_path = f"temp_valentine_{template_id}_{safe_name}_{timestamp}.png"
            
            # Сохраняем
            img.save(output_path, "PNG")
            
            # Проверяем, что файл создан
            if not os.path.exists(output_path):
                raise Exception("Файл не был сохранен на диск")
            
            return {
                "success": True,
                "path": output_path,
                "error": None,
                "message": "✅ Валентинка создана успешно!"
            }
        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Ошибка создания валентинки: {error_msg}")
            
            return {
                "success": False,
                "path": None,
                "error": error_msg,
                "message": f"⚠️ Ошибка при создании валентинки:\n\n"
                           f"`{error_msg}`\n\n"
                           f"Попробуйте отправить текстовую валентинку или свяжитесь с администратором."
            }
    
    @staticmethod
    def wrap_text(text: str, width: int = 700, font_size: int = 36) -> list:
        """Переносить текст по строкам"""
        # Примерное количество символов в строке
        chars_per_line = max(5, width // (font_size // 2))
        wrapped = wrap(text, width=chars_per_line)
        return wrapped[:3]  # Максимум 3 строки


def format_sender_info(sender_id: int, sender_name: str, is_anonymous: bool) -> str:
    """Форматировать информацию об отправителе"""
    if is_anonymous:
        return "Отправитель: Анонимный ❤️"
    return f"От: {sender_name}"


def truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Обрезать текст по максимальной длине"""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text