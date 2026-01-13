import pandas as pd
import sqlite3
import ftfy
import urllib.parse
import re
from atlassian import Confluence
from rapidfuzz import fuzz
import logging
import pymorphy2


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemKnowledgeBase:
    def __init__(self, db_path="systems_kb.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

        # --- НАСТРОЙКИ ДЛЯ УМНОГО ПОИСКА ---
        self.morph = pymorphy2.MorphAnalyzer()

        
        # 1. Стоп-слова (шум, который нужно игнорировать)
        self.stop_words = {
            'система', 'сервис', 'продукт', 'приложение', 'веб', 'для', 'на', 'в', 'и', 
            'или', 'по', 'с', 'от', 'как', 'это', 'предназначен', 'автоматизации', 
            'обеспечения', 'реализации', 'функций', 'процессов', 'аис', 'гис', 'егис'
        }

        # 2. Синонимы (что ищут -> как это может быть записано официально)
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
        """Создает структуру таблицы, если она не существует."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS systems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                status TEXT,
                owner_name TEXT,
                owner_email TEXT,
                owner_telegram TEXT,
                description TEXT,
                wiki_url TEXT,
                jira_url TEXT,
                repo_url TEXT,
                wiki_content TEXT,
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
        """
        Теперь метод умеет работать в двух режимах:
        1. expand_synonyms=True: Возвращает строку ТОЛЬКО из синонимов (если они есть).
        2. expand_synonyms=False: Возвращает просто очищенный текст (лемматизированный).
        """
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
            normal_forms = set(p.normal_form for p in parses)
            
            # Поиск синонимов
            synonyms_found = []
            for nf in normal_forms:
                if nf in self.synonyms:
                    synonyms_found.append(self.synonyms[nf])
            
            if expand_synonyms:
                # Если нужны синонимы - возвращаем ИХ
                if synonyms_found:
                    result_words.extend(synonyms_found)
                else:
                    # Если синонимов нет, оставляем исходное слово (нормализованное)
                    result_words.append(parses[0].normal_form)
            else:
                # Если синонимы НЕ нужны - возвращаем просто слово
                result_words.append(word)
                
        return " ".join(list(dict.fromkeys(result_words)))
    
    def load_data_from_csv(self, systems_csv_path, contacts_csv_path):
        """Загружает, чистит, убирает дубли и объединяет данные."""
        logging.info("Загрузка данных из CSV...")
        
        df_systems = pd.read_csv(systems_csv_path)
        df_contacts = pd.read_csv(contacts_csv_path)

        # Исправляем кодировку
        df_systems.columns = [self.fix_encoding(col) for col in df_systems.columns]
        df_contacts.columns = [self.fix_encoding(col) for col in df_contacts.columns]

        for col in df_systems.columns:
            df_systems[col] = df_systems[col].apply(self.fix_encoding)
        for col in df_contacts.columns:
            df_contacts[col] = df_contacts[col].apply(self.fix_encoding)

        # Нормализация имен
        df_systems['Владелец'] = df_systems['Владелец'].str.strip()
        df_contacts['Name'] = df_contacts['Name'].str.strip()

        # --- УДАЛЕНИЕ ДУБЛЕЙ (Ваш код) ---
        initial_contacts_count = len(df_contacts)
        df_contacts = df_contacts.drop_duplicates(subset=['Name'], keep='first')
        logging.info(f"Контакты: было {initial_contacts_count}, стало {len(df_contacts)}")

        initial_systems_count = len(df_systems)
        df_systems = df_systems.drop_duplicates(subset=['Продукт'], keep='first')
        logging.info(f"Системы: было {initial_systems_count}, стало {len(df_systems)}")

        # Объединение
        merged_df = pd.merge(
            df_systems, 
            df_contacts, 
            left_on='Владелец', 
            right_on='Name', 
            how='left'
        )

        logging.info(f"Итоговое количество записей: {len(merged_df)}")

        # Сохранение в БД с проверкой существования (чтобы не затереть wiki_content)
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
                        description=?, wiki_url=?, jira_url=?, repo_url=?, last_updated=CURRENT_TIMESTAMP
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
        """Ваш метод для получения контента по разным типам ссылок."""
        decoded_url = urllib.parse.unquote(url)
    
        def get_homepage_by_space_key(key):
            try:
                space_info = confluence.get_space(key, expand='homepage')
                if space_info and 'homepage' in space_info:
                    return confluence.get_page_by_id(space_info['homepage']['id'], expand='body.storage')
            except Exception:
                pass
            return None

        # Логика определения типа ссылки
        match_id = re.search(r'pageId=(\d+)', url)
        if match_id:
            return confluence.get_page_by_id(match_id.group(1), expand='body.storage')

        match_display_page = re.search(r'/display/([^/]+)/([^/?#]+)', decoded_url)
        if match_display_page:
            return confluence.get_page_by_title(match_display_page.group(1), match_display_page.group(2).replace('+', ' '), expand='body.storage')

        match_overview = re.search(r'/spaces/([^/]+)/overview', decoded_url)
        if match_overview:
            return get_homepage_by_space_key(match_overview.group(1))

        match_space_home = re.search(r'/display/([^/?#]+)/?$', decoded_url)
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
                    # Очищаем HTML перед сохранением, чтобы не забивать поиск тегами
                    clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    cursor.execute("UPDATE systems SET wiki_content = ? WHERE id = ?", (clean_text, sys_id))
                    logging.info(f"Обновлен контент для ID {sys_id}")
            except Exception as e:
                logging.warning(f"Не удалось скачать контент для {url}: {e}")

        self.conn.commit()
        logging.info("Синхронизация завершена.")
    
    def get_system_wiki(self, sys_id):
        """Возвращает текст Wiki для конкретной системы."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT wiki_content, product_name FROM systems WHERE id = ?", (sys_id,))
        return cursor.fetchone()

    def fuzzy_search(self, query, limit=5):
        df = pd.read_sql("SELECT * FROM systems", self.conn)
        
        # 1. Формируем ДВА варианта запроса
        # Вариант А: То, что ввел юзер (очищенное) -> "кружки"
        query_raw = self.preprocess_text(query, expand_synonyms=False)
        
        # Вариант Б: Синонимы -> "удо дополнительное"
        query_synonyms = self.preprocess_text(query, expand_synonyms=True)
        
        logging.info(f"Raw: '{query_raw}' | Synonyms: '{query_synonyms}'")
        
        results = []
        
        for _, row in df.iterrows():
            # Предобработка полей базы (без расширения синонимов, просто чистый текст)
            clean_title = self.preprocess_text(row['product_name'], expand_synonyms=False)
            clean_desc = self.preprocess_text(row['description'], expand_synonyms=False)
            clean_wiki = self.preprocess_text(row['wiki_content'], expand_synonyms=False)
            
            # Сравниваем с RAW запросом ("кружки")
            score_raw = max(
                fuzz.token_set_ratio(query_raw, clean_title),
                fuzz.token_set_ratio(query_raw, clean_desc)
            )
            
            # Сравниваем с SYNONYMS запросом ("удо")
            # Если синонимы отличаются от raw, считаем и их
            score_syn = 0
            if query_raw != query_synonyms:
                score_syn = max(
                    fuzz.token_set_ratio(query_synonyms, clean_title),
                    fuzz.token_set_ratio(query_synonyms, clean_desc)
                )
            
            # Берем МАКСИМАЛЬНЫЙ балл из двух стратегий
            # То есть: если совпало по слову "кружки" - отлично.
            # Если не совпало, но совпало по "УДО" - тоже отлично.
            base_score = max(score_raw, score_syn)
            
            # Wiki учитываем с меньшим весом
            wiki_score = 0
            if clean_wiki:
                wiki_score = fuzz.token_set_ratio(query_synonyms, clean_wiki) # Wiki лучше искать по синонимам
            
            # Итоговый балл
            final_score = (base_score * 1.5) + (wiki_score * 0.5)
            final_score = final_score / 2
            
            # Бонусы (статус и т.д.)
            status = str(row['status']).lower()
            if 'эксплуатации' in status or 'prod' in status:
                final_score += 10
            
            if final_score > 45:
                res = row.to_dict()
                res['search_score'] = final_score
                results.append(res)
        
        results.sort(key=lambda x: x['search_score'], reverse=True)
        return results[:limit]

# --- ПРИМЕР ИСПОЛЬЗОВАНИЯ ---

if __name__ == "__main__":
    kb = SystemKnowledgeBase()

    # 1. Загрузка данных
    kb.load_data_from_csv("augmented_systems.csv", "contacts.csv")
    


    # 2. Синхронизация (раскомментируйте при необходимости)
    #confluence_url = os.getenv('CONFLUENCE_URL')
    #user = os.getenv('CONFLUENCE_USER')
    #token = os.getenv('CONFLUENCE_TOKEN')
    # kb.sync_confluence_content(
    #      confluence_url=confluence_url, 
    #      username=user, 
    #      api_token=token
    # )

    # 3. Тестовый поиск
    user_query = "Система для зачисления в детские сады"
    print(f"\n--- Поиск по запросу: '{user_query}' ---\n")
    
    results = kb.fuzzy_search(user_query)
    
    for res in results:
        print(f"[{res['search_score']:.1f}] {res['product_name']}")
        print(f"    Владелец: {res['owner_name']}")
        print(f"    Описание: {str(res['description'])[:100]}...")
        print("-" * 40)