from fastapi import APIRouter, Depends, Query
from app.dependencies import get_current_user, get_search_service
from app.services.search import SearchService
from app.config import logger

router = APIRouter()

@router.get("/api/search")
def search_systems(
    q: str, 
    limit: int = 5, 
    current_user: tuple = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
):
    logger.info(f"User {current_user[0]} searching for: {q}")
    return search_service.fuzzy_search(q, limit=limit)