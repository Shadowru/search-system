from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.models import Token
from app.security import verify_password, create_access_token
from app.dependencies import get_repository
from app.db.repository import SystemRepository

router = APIRouter(tags=["Authentication"])

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    repo: SystemRepository = Depends(get_repository)
):

    # Получаем пользователя из БД через репозиторий
    user = repo.get_user(form_data.username)
    
    print('Username : ' + form_data.username)
    print('user : ')
    print(user)
    
    # user[0] - username, user[1] - hashed_password
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаем JWT токен
    access_token = create_access_token(data={"sub": user[0]})
    return {"access_token": access_token, "token_type": "bearer"}