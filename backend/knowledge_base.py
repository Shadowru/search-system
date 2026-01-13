import pandas as pd
import sqlite3
import ftfy
import urllib.parse
import re
from atlassian import Confluence
from rapidfuzz import fuzz
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemKnowledgeBase:
    def __init__(self, db_path="systems_kb.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

        # --- НАСТРОЙКИ ДЛЯ УМНОГО ПОИСКА ---
        
        # 1. Стоп-слова (шум, который нужно игнорировать)
        self.stop_words = {
            'система', 'сервис', 'продукт', 'приложение', 'веб', 'для', 'на', 'в', 'и', 
            'или', 'по', 'с', 'от', 'как', 'это', 'предназначен', 'автоматизации', 
            'обеспечения', 'реализации', 'функций', 'процессов', 'аис', 'гис', 'егис'
        }

        # 2. Синонимы (что ищут -> как это может быть записано официально)
        self.synonyms = {
            "сад": "доу дошкольное",
            "сады": "доу дошкольное",
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
        self.conn.commit()

    def fix_encoding(self, text):
        if pd.isna(text):
            return ""
        return ftfy.fix_text(str(text))

    def preprocess_text(self, text):
        """Очищает текст перед поиском: удаляет мусор, раскрывает синонимы."""
        if not text: 
            return ""
        
        # 1. Нижний регистр
        text = str(text).lower()
        
        # 2. Очистка от HTML тегов (если они остались) и спецсимволов
        text = re.sub(r'<[^>]+>', ' ', text) # Удалить теги
        text = re.sub(r'[^\w\s]', ' ', text) # Удалить пунктуацию
        
        # 3. Раскрытие синонимов
        for word, replacement in self.synonyms.items():
            # Если слово есть в тексте как отдельное слово
            if re.search(r'\b' + word + r'\b', text):
                text += " " + replacement
        
        # 4. Удаление стоп-слов
        words = [w for w in text.split() if w not in self.stop_words and len(w) > 1]
        
        return " ".join(words)

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

    def fuzzy_search(self, query, limit=5):
        """
        Умный поиск с весами и предобработкой.
        """
        df = pd.read_sql("SELECT * FROM systems", self.conn)
        
        # 1. Предобработка запроса (удаление стоп-слов, синонимы)
        clean_query = self.preprocess_text(query)
        logging.info(f"Обработанный запрос: '{clean_query}'")
        
        results = []
        
        for _, row in df.iterrows():
            # 2. Предобработка полей базы
            clean_title = self.preprocess_text(row['product_name'])
            clean_desc = self.preprocess_text(row['description'])
            clean_wiki = self.preprocess_text(row['wiki_content'])
            
            # 3. Сравнение (token_set_ratio лучше находит вхождения слов)
            score_title = fuzz.token_set_ratio(clean_query, clean_title)
            score_desc = fuzz.token_set_ratio(clean_query, clean_desc)
            
            # Wiki учитываем с меньшим весом и только если там есть контент
            score_wiki = 0
            if clean_wiki:
                score_wiki = fuzz.token_set_ratio(clean_query, clean_wiki)
            
            # 4. Расчет итогового веса
            # Название: x1.5
            # Описание: x1.0
            # Wiki: x0.5
            
            # Дополнительный бонус, если все слова запроса есть в названии
            boost = 0
            query_words = clean_query.split()
            if query_words and all(w in clean_title for w in query_words):
                boost = 20

            final_score = (score_title * 1.5) + (score_desc * 1.0) + (score_wiki * 0.5) + boost
            # Нормализация (делим на сумму весов ~3)
            final_score = final_score / 3
            
            if final_score > 45: # Порог отсечения
                res = row.to_dict()
                res['search_score'] = final_score
                results.append(res)
        
        # Сортировка по убыванию релевантности
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