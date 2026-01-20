import sqlite3
import pandas as pd
from app.config import DB_PATH, logger
from app.utils.text import fix_encoding

class SystemRepository:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Создает структуру таблицы, если она не существует."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS systems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                product_code TEXT,
                status TEXT,
                owner_name TEXT,
                owner_email TEXT,
                owner_telegram TEXT,
                description TEXT,
                wiki_url TEXT,
                jira_url TEXT,
                repo_url TEXT,
                wiki_content TEXT,
                ai_keywords TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT
            )
        ''')
        self.conn.commit()
        
    def get_user(self, username):
        cursor = self.conn.cursor()
        cursor.execute("SELECT username, hashed_password FROM users WHERE username = ?", (username,))
        return cursor.fetchone()

    def get_all_systems_df(self):
        """Возвращает DataFrame для поиска"""
        return pd.read_sql("SELECT * FROM systems", self.conn)

    def update_wiki_content(self, sys_id, content):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE systems SET wiki_content = ? WHERE id = ?", (content, sys_id))
        self.conn.commit()

    def create_user(self, username, hashed_password):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

