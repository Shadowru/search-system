import logging
import os
import math
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Query, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware


from knowledge_base import SystemKnowledgeBase

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 дней

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Модели данных (Pydantic) ---
# Это нужно, чтобы API возвращал красивый JSON и валидировал типы
class Token(BaseModel):
    access_token: str
    token_type: str
    
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
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = kb.get_user(username)
    if user is None:
        raise credentials_exception
    return user

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

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = kb.get_user(form_data.username)
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user[0]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/search", response_model=List[SearchResultItem])
async def search_systems(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное кол-во результатов"),
    current_user: tuple = Depends(get_current_user)
):
    """
    Выполняет нечеткий поиск по системам.
    """
    if not q.strip():
        return []

    logger.info(f"User {current_user[0]} searching for: {q}")
    
    try:
        results = kb.fuzzy_search(q, limit=limit)
        clean_results = clean_nans(results)
        
        return clean_results
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера: host="0.0.0.0" делает его доступным в локальной сети
    uvicorn.run(app, host="0.0.0.0", port=8000)