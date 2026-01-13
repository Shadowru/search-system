FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и базу данных
COPY . .

# Запуск
CMD ["uvicorn", "search_service:app", "--host", "0.0.0.0", "--port", "8000"]