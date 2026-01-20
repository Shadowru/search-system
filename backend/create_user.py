import sys
from passlib.context import CryptContext
from knowledge_base import SystemKnowledgeBase
from app.dependencies import get_repository
from app.security import create_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



if len(sys.argv) < 3:
    print("Использование: python create_user.py <username> <password>")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

hashed_pw = pwd_context.hash(password)

if create_user(get_repository(), username, hashed_pw):
    print(f"Пользователь {username} успешно создан!")
else:
    print(f"Ошибка: Пользователь {username} уже существует.")