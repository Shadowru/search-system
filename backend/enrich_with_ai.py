import sqlite3
import requests
import json
import time
import re
import os

# Настройки
DB_PATH = "./backend/systems_kb.db"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate") # Внутри Docker
# Если запускаете локально, поменяйте на http://localhost:11434/api/generate
MODEL = "gpt-oss:120b" 

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text

def get_ai_keywords(text, system_name):
    if not text: return ""
    
    prompt = f"""
    Проанализируй текст документации к системе "{system_name}".
    Твоя задача: составить список ключевых слов, синонимов и функций для поискового индекса.
    
    1. Напиши синонимы названия системы (аббревиатуры, сленг).
    2. Напиши основные функции (что система делает).
    3. Напиши, кто пользователи (учителя, родители, бухгалтеры).
    
    Ответ дай просто списком слов и фраз через запятую на русском языке. Без лишних слов.
    
    Текст:
    {text}
    """
    
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        })
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            print(f"Error Ollama: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Connection error: {e}")
        return ""

def main():
    print("🚀 Начинаем AI-обогащение базы знаний...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Берем системы, у которых есть Wiki, но нет AI-ключевиков (или обновляем все)
    cursor.execute("SELECT id, product_name, wiki_content FROM systems WHERE wiki_content IS NOT NULL AND wiki_content != ''")
    systems = cursor.fetchall()
    
    total = len(systems)
    print(f"Найдено {total} систем с документацией.")
    
    for i, (sys_id, name, content) in enumerate(systems):
        print(f"[{i+1}/{total}] Обработка: {name}...")
        
        clean_text = clean_html(content)
        keywords = get_ai_keywords(clean_text, name)
        
        if keywords:
            print(f"   ✅ Ключевые слова: {keywords[:100]}...")
            cursor.execute("UPDATE systems SET ai_keywords = ? WHERE id = ?", (keywords, sys_id))
            conn.commit()
        else:
            print("   ⚠️ Не удалось получить ответ от AI.")
            
    conn.close()
    print("🏁 Готово! База обновлена.")

if __name__ == "__main__":
    main()