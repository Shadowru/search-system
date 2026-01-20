import pandas as pd
import sqlite3
import ftfy
import urllib.parse
import re
from atlassian import Confluence
from rapidfuzz import fuzz
import logging
import pymorphy2

# Импорты для FastAPI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemKnowledgeBase:
    def __init__(self, db_path="systems_kb.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False) # check_same_thread=False нужен для FastAPI
        self._init_db()

        # --- НАСТРОЙКИ ДЛЯ УМНОГО ПОИСКА ---
        self.morph = pymorphy2.MorphAnalyzer()
        
        # 1. Стоп-слова
        self.stop_words = {
            'система', 'сервис', 'продукт', 'приложение', 'веб', 'для', 'на', 'в', 'и', 
            'или', 'по', 'с', 'от', 'как', 'это', 'предназначен', 'автоматизации', 
            'обеспечения', 'реализации', 'функций', 'процессов', 'аис', 'гис', 'егис'
        }

        # 2. Синонимы
        self.synonyms = {
            "сад": "доу дошкольное",
            "садик": "доу дошкольное",
            "школа": "оу сош общее образование",
            "колледж": "спо профтех",
            "вуз": "впо высшее",
            "кружок": "удо дополнительное",
            "секция": "удо дополнительное",
            "еда": "питание",
            "проход": "скуд турникет",
            "ученик": "обучающийся учащийся",
        }
        
    def _init_db(self):
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
                ai_keywords TEXT
            )
        ''')
        
        try:
            cursor.execute("ALTER TABLE systems ADD COLUMN ai_keywords TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE systems ADD COLUMN product_code TEXT")
        except sqlite3.OperationalError:
            pass

        self.conn.commit()
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

    def create_user(self, username, hashed_password):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        
    def fix_encoding(self, text):
        if pd.isna(text):
            return ""
        return ftfy.fix_text(str(text))

    def preprocess_text(self, text, expand_synonyms=True):
        if not text: return ""
        
        text = str(text).lower()
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        words = text.split()
        result_words = []
        
        for word in words:
            if word in self.stop_words or len(word) < 2: continue
            
            # Лемматизация
            parses = self.morph.parse(word)
            normal_form = parses[0].normal_form 
            normal_forms = set(p.normal_form for p in parses)
            
            # Поиск синонимов
            synonyms_found = []
            for nf in normal_forms:
                if nf in self.synonyms:
                    synonyms_found.append(self.synonyms[nf])
            
            if expand_synonyms:
                if synonyms_found:
                    result_words.extend(synonyms_found)
                else:
                    result_words.append(normal_form)
            else:
                result_words.append(normal_form)
                
        return " ".join(list(dict.fromkeys(result_words)))
    
    def load_data_from_csv(self, systems_csv_path, contacts_csv_path):
        logging.info("Загрузка данных из CSV...")
        
        df_systems = pd.read_csv(systems_csv_path)
        df_contacts = pd.read_csv(contacts_csv_path)

        df_systems.columns = [self.fix_encoding(col) for col in df_systems.columns]
        df_contacts.columns = [self.fix_encoding(col) for col in df_contacts.columns]

        for col in df_systems.columns:
            df_systems[col] = df_systems[col].apply(self.fix_encoding)
        for col in df_contacts.columns:
            df_contacts[col] = df_contacts[col].apply(self.fix_encoding)

        df_systems['Владелец'] = df_systems['Владелец'].str.strip()
        df_contacts['Name'] = df_contacts['Name'].str.strip()

        df_contacts = df_contacts.drop_duplicates(subset=['Name'], keep='first')
        df_systems = df_systems.drop_duplicates(subset=['Продукт'], keep='first')

        merged_df = pd.merge(
            df_systems, 
            df_contacts, 
            left_on='Владелец', 
            right_on='Name', 
            how='left'
        )

        cursor = self.conn.cursor()
        
        for _, row in merged_df.iterrows():
            product_name = row.get('Продукт')
            
            cursor.execute("SELECT id FROM systems WHERE product_name = ?", (product_name,))
            existing = cursor.fetchone()
            
            if existing:
                sys_id = existing[0]
                cursor.execute('''
                    UPDATE systems SET 
                        status=?, owner_name=?, owner_email=?, owner_telegram=?,
                        description=?, wiki_url=?, jira_url=?, repo_url=?
                    WHERE id=?
                ''', (
                    row.get('Статус'), row.get('Владелец'), row.get('Email'), row.get('Telegram'),
                    row.get('Назначение'), row.get('Wiki'), row.get('Jira'), row.get('Repo'), sys_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO systems (
                        product_name, status, owner_name, owner_email, owner_telegram,
                        description, wiki_url, jira_url, repo_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_name, row.get('Статус'), row.get('Владелец'), row.get('Email'), row.get('Telegram'),
                    row.get('Назначение'), row.get('Wiki'), row.get('Jira'), row.get('Repo')
                ))
        
        self.conn.commit()
        logging.info("Данные успешно обновлены в БД.")

    def get_page_content(self, confluence, url):
        decoded_url = urllib.parse.unquote(url)
    
        def get_homepage_by_space_key(key):
            try:
                space_info = confluence.get_space(key, expand='homepage')
                if space_info and 'homepage' in space_info:
                    return confluence.get_page_by_id(space_info['homepage']['id'], expand='body.storage')
            except Exception:
                pass
            return None

        match_id = re.search(r'pageId=(\d+)', url)
        if match_id:
            return confluence.get_page_by_id(match_id.group(1), expand='body.storage')

        match_display_page = re.search(r'/display/([^/]+)/([^/?#]+)', decoded_url)
        if match_display_page:
            return confluence.get_page_by_title(match_display_page.group(1), match_display_page.group(2).replace('+', ' '), expand='body.storage')

        match_overview = re.search(r'/spaces/([^/]+)/overview', decoded_url)
        if match_overview:
            return get_homepage_by_space_key(match_overview.group(1))

        match_space_home = re.search(r'/display/([^/?#]+)/?', decoded_url)
        if match_space_home:
            return get_homepage_by_space_key(match_space_home.group(1))

        return None

    def sync_confluence_content(self, confluence_url, username, api_token):
        logging.info("Начало синхронизации с Confluence...")
        try:
            confluence = Confluence(url=confluence_url, username=username, token=api_token, cloud=False)
        except Exception as e:
            logging.error(f"Ошибка подключения к Confluence: {e}")
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT id, wiki_url FROM systems WHERE wiki_url LIKE '%http%'")
        rows = cursor.fetchall()

        for sys_id, url in rows:
            try:
                page_data = self.get_page_content(confluence, url)
                if page_data and 'body' in page_data:
                    raw_html = page_data['body']['storage']['value']
                    clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    cursor.execute("UPDATE systems SET wiki_content = ? WHERE id = ?", (clean_text, sys_id))
                    logging.info(f"Обновлен контент для ID {sys_id}")
            except Exception as e:
                logging.warning(f"Не удалось скачать контент для {url}: {e}")

        self.conn.commit()
        logging.info("Синхронизация завершена.")
    
    def get_system_wiki(self, sys_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT wiki_content, product_name FROM systems WHERE id = ?", (sys_id,))
        return cursor.fetchone()

    def fuzzy_search(self, query, limit=5):
        df = pd.read_sql("SELECT * FROM systems", self.conn)
        
        query_raw = self.preprocess_text(query, expand_synonyms=False)
        query_synonyms = self.preprocess_text(query, expand_synonyms=True)
        
        logging.info(f"Raw: '{query_raw}' | Synonyms: '{query_synonyms}'")
        
        results = []
        
        for _, row in df.iterrows():
            clean_title = self.preprocess_text(row['product_name'], expand_synonyms=False)
            clean_desc = self.preprocess_text(row['description'], expand_synonyms=False)
            clean_wiki = self.preprocess_text(row['wiki_content'], expand_synonyms=False)
            
            clean_ai = ""
            if row['ai_keywords']:
                clean_ai = self.preprocess_text(row['ai_keywords'], expand_synonyms=True)

            score_raw = max(
                fuzz.token_set_ratio(query_raw, clean_title),
                fuzz.token_set_ratio(query_raw, clean_desc)
            )
            
            score_syn = 0
            if query_raw != query_synonyms:
                score_syn = max(
                    fuzz.token_set_ratio(query_synonyms, clean_title),
                    fuzz.token_set_ratio(query_synonyms, clean_desc)
                )
            
            base_score = max(score_raw, score_syn)
            
            wiki_score = 0
            if clean_wiki:
                wiki_score = fuzz.token_set_ratio(query_synonyms, clean_wiki)
            
            score_ai = 0
            if clean_ai:
                score_ai = fuzz.token_set_ratio(query_synonyms, clean_ai)
            
            final_score = (base_score * 0.5) + (score_ai * 0.3) + (wiki_score * 0.2)
            
            status = str(row['status']).lower()
            if 'эксплуатации' in status or 'prod' in status:
                final_score += 5 
            
            if final_score > 45:
                res = row.to_dict()
                res['search_score'] = final_score
                results.append(res)
        
        results.sort(key=lambda x: x['search_score'], reverse=True)
        return results[:limit]

app = FastAPI(title="Unified Systems & Topics Service")

kb = SystemKnowledgeBase()
JIRA_DB_NAME = 'jira_data.db'

class TopicInfo(BaseModel):
    topic_name: str
    role: str
    jira_key: str
    consumer_group: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Service is running. Available endpoints: /search, /systems/{code}/topics"}

@app.get("/search")
def search_systems(q: str, limit: int = 5):
    """
    Умный поиск по системам (fuzzy search).
    """
    results = kb.fuzzy_search(q, limit=limit)
    return results

@app.get("/systems/{system_code}/topics", response_model=List[TopicInfo])
def get_topics_by_system(system_code: str):
    """
    Возвращает список топиков для указанной системы из jira_data.db.
    system_code - код системы (например, SYS-001)
    """
    conn = sqlite3.connect(JIRA_DB_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            d.topic_name, 
            d.role, 
            d.jira_key,
            t.consumer_group
        FROM system_dependencies d
        LEFT JOIN topics_info t 
            ON d.topic_name = t.topic_name AND d.jira_key = t.jira_key
        WHERE d.system_code = ?
    '''
    
    try:
        cursor.execute(query, (system_code,))
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        # Обработка случая, если таблицы еще не созданы
        logging.error(f"Database error: {e}")
        conn.close()
        return []
        
    conn.close()
    
    if not rows:
        return [] 
        
    results = []
    for row in rows:
        results.append({
            "topic_name": row['topic_name'],
            "role": row['role'],
            "jira_key": row['jira_key'],
            "consumer_group": row['consumer_group']
        })
        
    return results

if __name__ == "__main__":
    import uvicorn
    # Запуск для локальной отладки
    uvicorn.run(app, host="0.0.0.0", port=8000)