import sqlite3
from datetime import datetime
from config import DB_PATH
from typing import Optional, List, Dict

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица вал��нтинок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS valentines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                recipient_id INTEGER,
                recipient_username TEXT,
                text TEXT,
                image_template INTEGER,
                is_anonymous BOOLEAN DEFAULT 1,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT 0
            )
        """)

        # Таблица очереди (для невидимых пользователей)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                recipient_username TEXT,
                text TEXT,
                image_template INTEGER,
                is_anonymous BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        """Добавить пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            conn.commit()
        except Exception as e:
            print(f"Error adding user: {e}")
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получить пользователя по username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"user_id": row[0], "username": row[1], "first_name": row[2]}
        return None

    def save_valentine(self, sender_id: int, recipient_id: Optional[int], recipient_username: str,
                      text: str, image_template: int, is_anonymous: bool):
        """Сохранить валентинку"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO valentines (sender_id, recipient_id, recipient_username, text, 
                                   image_template, is_anonymous)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sender_id, recipient_id, recipient_username, text, image_template, is_anonymous))
        
        conn.commit()
        conn.close()

    def queue_valentine(self, sender_id: int, recipient_username: str, text: str,
                       image_template: int, is_anonymous: bool):
        """Добавить валентинку в очередь"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO queue (sender_id, recipient_username, text, image_template, is_anonymous)
            VALUES (?, ?, ?, ?, ?)
        """, (sender_id, recipient_username, text, image_template, is_anonymous))
        
        conn.commit()
        conn.close()

    def get_queued_valentines(self, recipient_username: str) -> List[Dict]:
        """Получить валентинки из очереди"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sender_id, text, image_template, is_anonymous FROM queue 
            WHERE recipient_username = ?
        """, (recipient_username,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{"id": row[0], "sender_id": row[1], "text": row[2], 
                "image_template": row[3], "is_anonymous": row[4]} for row in rows]

    def remove_from_queue(self, queue_id: int):
        """Удалить валентинку из очереди"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM queue WHERE id = ?", (queue_id,))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Получить статистику"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM valentines WHERE delivered = 1")
        delivered = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM queue")
        in_queue = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "delivered": delivered,
            "in_queue": in_queue
        }

    def get_all_users(self) -> List[int]:
        """Получить ID всех пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users