from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from app.security import oauth2_scheme
from app.config import SECRET_KEY, ALGORITHM
from app.db.repository import SystemRepository
from app.services.search import SearchService

# Singleton для репозитория (чтобы не пересоздавать подключение)
_repo = SystemRepository()
_search_service = SearchService(_repo)

def get_repository():
    return _repo

def get_search_service():
    return _search_service

async def get_current_user(token: str = Depends(oauth2_scheme), repo: SystemRepository = Depends(get_repository)):
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
    
    user = repo.get_user(username)
    if user is None:
        raise credentials_exception
    return user