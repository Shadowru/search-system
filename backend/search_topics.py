from fastapi import FastAPI, HTTPException
import sqlite3
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Jira Topics Service")
DB_NAME = 'jira_data.db'

# Модель ответа (как будет выглядеть JSON)
class TopicInfo(BaseModel):
    topic_name: str
    role: str
    jira_key: str
    consumer_group: str | None

@app.get("/")
def read_root():
    return {"message": "Service is running. Go to /docs for Swagger UI"}

@app.get("/systems/{system_code}/topics", response_model=List[TopicInfo])
def get_topics_by_system(system_code: str):
    """
    Возвращает список топиков для указанной системы.
    system_code - код системы (например, SYS-001)
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Чтобы обращаться к полям по имени
    cursor = conn.cursor()
    
    # Запрос: ищем связи в dependencies и подтягиваем детали из topics_info
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
    
    cursor.execute(query, (system_code,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        # Можно вернуть пустой список или 404, если система вообще не найдена
        return [] 
        
    results = []
    for row in rows:
        results.append({
            "topic_name": row['topic_name'],
            "role": row['role'], # PRODUCER или CONSUMER
            "jira_key": row['jira_key'],
            "consumer_group": row['consumer_group']
        })
        
    return results

# Запуск сервера (если файл запущен напрямую)
if __name__ == "__main__":
    import uvicorn
    # Запуск на порту 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)