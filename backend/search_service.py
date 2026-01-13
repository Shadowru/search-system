import logging
import math
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from knowledge_base import SystemKnowledgeBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SearchAPI")

app = FastAPI(
    title="Корпоративный Поиск Систем",
    description="REST API для умного поиска по базе знаний систем",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    kb = SystemKnowledgeBase()
    logger.info("База знаний успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка инициализации базы знаний: {e}")
    raise e

# --- Модели данных (Pydantic) ---
# Это нужно, чтобы API возвращал красивый JSON и валидировал типы
class SearchResultItem(BaseModel):
    id: int
    product_name: str
    status: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_telegram: Optional[str] = None
    description: Optional[str] = None
    wiki_url: Optional[str] = None
    jira_url: Optional[str] = None
    repo_url: Optional[str] = None
    search_score: float

# --- Вспомогательные функции ---
def clean_nans(data_list):
    """
    Pandas/SQLite могут возвращать NaN (Not a Number) для пустых полей.
    JSON стандарт не поддерживает NaN, поэтому заменяем их на None (null).
    """
    cleaned = []
    for item in data_list:
        new_item = {}
        for k, v in item.items():
            if isinstance(v, float) and math.isnan(v):
                new_item[k] = None
            else:
                new_item[k] = v
        cleaned.append(new_item)
    return cleaned

# --- Эндпоинты ---

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}

@app.get("/search", response_model=List[SearchResultItem])
async def search_systems(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное кол-во результатов")
):
    """
    Выполняет нечеткий поиск по системам.
    """
    if not q.strip():
        return []

    logger.info(f"API Search Query: {q}")
    
    try:
        # Вызываем твой метод поиска
        results = kb.fuzzy_search(q, limit=limit)
        
        # Очищаем от NaN перед отправкой
        clean_results = clean_nans(results)
        
        return clean_results
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера: host="0.0.0.0" делает его доступным в локальной сети
    uvicorn.run(app, host="0.0.0.0", port=8000)