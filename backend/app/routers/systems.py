import sqlite3
import logging
from typing import List
from fastapi import APIRouter, HTTPException
from app.models import TopicInfo
from app.config import JIRA_DB_NAME

router = APIRouter(tags=["Systems & Topics"])

@router.get("/api/systems/{system_code}/topics", response_model=List[TopicInfo])
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
        logging.error(f"Database error (Jira DB): {e}")
        conn.close()
        # Возвращаем пустой список или ошибку 500, в зависимости от требований
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