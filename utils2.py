from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from config import TEMPLATES_PATH, FONTS_PATH, MAX_TEXT_LENGTH
import os
from datetime import datetime

class ImageProcessor:
    """Обработка изображений валентинок"""
    
    TEMPLATES = {
        1: {"path": f"{TEMPLATES_PATH}/template1.png"},
        2: {"path": f"{TEMPLATES_PATH}/template2.png"},
        3: {"path": f"{TEMPLATES_PATH}/template3.png"},
    }
    
    @staticmethod
    def darken_image(img, darkness_level=0.3):
        """
        Затемнить изображение
        
        Args:
            img: PIL Image объект
            darkness_level: уровень затемнения (0-1), где 0 = оригинал, 1 = полностью черное
        """
        # Создаем черный слой
        dark_layer = Image.new('RGBA', img.size, (0, 0, 0, int(255 * darkness_level)))
        
        # Конвертируем исходное изображение в RGBA если нужно
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Накладываем черный слой
        result = Image.alpha_composite(img, dark_layer)
        return result.convert('RGB')
    
    @staticmethod
    def blur_ellipse(draw, bbox, color, alpha=120, blur_radius=25):
        """
        Рисует размытый эллипс
        
        Args:
            draw: ImageDraw объект
            bbox: координаты границ эллипса [x1, y1, x2, y2]
            color: цвет RGB
            alpha: прозрачность (0-255)
            blur_radius: радиус размытия в пикселях
        """
        x1, y1, x2, y2 = bbox
        
        # Рисуем несколько концентрических эллипсов с уменьшающейся прозрачностью
        # для эффекта размытия
        steps = blur_radius
        
        for step in range(steps, 0, -1):
            # Уменьшаем ��бласть для каждого слоя
            factor = step / steps
            
            # Вычисляем новые координаты с уменьшением от центра
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = (x2 - x1) / 2
            height = (y2 - y1) / 2
            
            # Новые координаты с уменьшением
            new_x1 = center_x - width * factor
            new_y1 = center_y - height * factor
            new_x2 = center_x + width * factor
            new_y2 = center_y + height * factor
            
            # Прозрачность уменьшается для эффекта размытия
            current_alpha = int(alpha * (1 - factor))
            
            # Рисуем эллипс с нужной прозрачностью
            draw.ellipse(
                [new_x1, new_y1, new_x2, new_y2],
                fill=(*color, current_alpha)
            )
    
    @staticmethod
    def smart_wrap_text(text, font, max_width, max_lines=4):
        """
        Умный перенос текста с учетом ширины шрифта
        
        Args:
            text: исходный текст
            font: объект шрифта PIL
            max_width: максимальная ширина строки в пикселях
            max_lines: максимальное количество строк
        
        Returns:
            список строк текста
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Пробуем добавить слово к текущей строке
            test_line = ' '.join(current_line + [word])
            
            # Измеряем ширину тестовой строки
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]
            
            # Если строка слишком длинная
            if line_width > max_width:
                # Если текущая строка не пуста, добавляем её
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Если слово само по себе слишком длинное, добавляем его отдельно
                    lines.append(word)
                    current_line = []
            else:
                # Добавляем слово к строке
                current_line.append(word)
        
        # Добавляем последнюю строку
        if current_line:
            lines.append(' '.join(current_line))
        
        # Ограничиваем максимум строк
        if len(lines) > max_lines:
            # Объединяем лишние строки с многоточием
            lines = lines[:max_lines]
            lines[-1] = lines[-1][:len(lines[-1]) - 3] + '...' if len(lines[-1]) > 3 else lines[-1]
        
        return lines
    
    @staticmethod
    def calculate_optimal_font_size(text, font_path, max_width, max_height, initial_size=60):
        """
        Вычислить оптимальный размер шрифта
        
        Args:
            text: текст для измерения
            font_path: путь к файлу шрифта
            max_width: максимальная ширина
            max_height: максимальная высота
            initial_size: начальный размер
        
        Returns:
            оптимальный размер шрифта
        """
        font_size = initial_size
        
        while font_size > 20:
            try:
                font = ImageFont.truetype(font_path, size=font_size)
            except:
                font = ImageFont.load_default()
            
            # Умно переносим текст с учетом размера шрифта
            wrapped = ImageProcessor.smart_wrap_text(text, font, max_width - 40, max_lines=4)
            
            # Вычисляем общую высоту текста
            total_height = 0
            max_line_width = 0
            
            for line in wrapped:
                try:
                    bbox = font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                    
                    max_line_width = max(max_line_width, line_width)
                    total_height += line_height + 10  # 10px промежуток между строками
                except:
                    pass
            
            # Проверяем, подходит ли размер
            if max_line_width <= max_width - 40 and total_height <= max_height - 40:
                return font_size
            
            font_size -= 2
        
        return max(20, font_size)
    
    @staticmethod
    def create_valentine(template_id: int, text: str, sender_name: str = "Unknown") -> dict:
        """
        Создать послание с текстом на шаблоне
        
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
        
        # Проверяем ��рифт
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
            
            # Затемняем изображение
            img = ImageProcessor.darken_image(img, darkness_level=0.3)
            
            # Получаем размеры изображения
            img_width, img_height = img.size
            
            # Загружаем шрифт
            try:
                # Вычисляем оптимальный размер шрифта
                font_size = ImageProcessor.calculate_optimal_font_size(
                    text, 
                    FONTS_PATH, 
                    img_width - 100, 
                    img_height // 2,
                    initial_size=60
                )
                font = ImageFont.truetype(FONTS_PATH, size=font_size)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки ш��ифта: {e}")
                font = ImageFont.load_default()
                font_size = 30
            
            # Умный перенос текста с учетом реальной ширины
            wrapped_text = ImageProcessor.smart_wrap_text(text, font, img_width - 100, max_lines=4)
            
            # Временный draw для измерения текста
            temp_img = Image.new('RGB', (img_width, img_height), (0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # Вычисляем размеры каждой строки для точного выравнивания
            line_heights = []
            line_widths = []
            max_line_width = 0
            
            for line in wrapped_text:
                try:
                    bbox = temp_draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                    
                    line_widths.append(line_width)
                    line_heights.append(line_height)
                    max_line_width = max(max_line_width, line_width)
                except:
                    line_widths.append(img_width - 100)
                    line_heights.append(font_size)
            
            # Вычисляем общую высоту текстового блока
            line_spacing = 15  # Промежуток между строками
            total_text_height = sum(line_heights) + (len(wrapped_text) - 1) * line_spacing
            
            # Параметры эллипса подложки
            padding_horizontal = 50
            padding_vertical = 40
            
            # Размеры области под текст
            text_width = max_line_width + padding_horizontal * 2
            text_height = total_text_height + padding_vertical * 2
            
            # Центрируем эллипс по центру изображения
            center_x = img_width // 2
            center_y = img_height // 2
            
            # Координаты эллипса
            ellipse_x1 = center_x - text_width // 2
            ellipse_y1 = center_y - text_height // 2
            ellipse_x2 = center_x + text_width // 2
            ellipse_y2 = center_y + text_height // 2
            
            # Создаем слой для подложки
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Рисуем размытый черный эллипс
            ImageProcessor.blur_ellipse(
                overlay_draw,
                [ellipse_x1, ellipse_y1, ellipse_x2, ellipse_y2],
                color=(0, 0, 0),  # Черный цвет
                alpha=180,  # Прозрачность (чем выше, тем непрозрачнее)
                blur_radius=35  # Радиус размытия
            )
            
            # Накладываем overlay на основное изображение
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Рисуем текст
            text_color = (255, 255, 255)  # Белый цвет
            
            # Вычисляем начальную Y позицию для центрирования текста по вертикали
            text_y_start = center_y - total_text_height // 2
            
            for idx, line in enumerate(wrapped_text):
                # Центрируем каждую строку по горизонтали
                line_width = line_widths[idx]
                x_position = center_x - line_width // 2
                
                # Позиция по вертикали
                y_position = text_y_start + sum(line_heights[:idx]) + idx * line_spacing
                
                # Рисуем текст без обводки
                try:
                    draw.text(
                        (x_position, y_position),
                        line,
                        fill=text_color,
                        font=font,
                        anchor="lt"
                    )
                except Exception as e:
                    print(f"⚠️ Ошибка рисования текста: {e}")
            
            # Создаем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in sender_name)[:20]
            output_path = f"temp_valentine_{template_id}_{safe_name}_{timestamp}.png"
            
            # Сохраняем
            img.save(output_path, "PNG", quality=95)
            
            # Проверяем, что файл создан
            if not os.path.exists(output_path):
                raise Exception("Файл не был сохранен на диск")
            
            return {
                "success": True,
                "path": output_path,
                "error": None,
                "message": "✅ Послание создано успешно!"
            }
        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Ошибка создания послания: {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "path": None,
                "error": error_msg,
                "message": f"⚠️ Ошибка при создании послания:\n\n"
                           f"`{error_msg}`\n\n"
                           f"Попробуйте отправить текстовое послание или свяжитесь с администратором."
            }


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