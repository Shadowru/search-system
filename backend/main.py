import uvicorn
from fastapi import FastAPI
from app.routers import auth, search, systems

app = FastAPI(title="Unified Systems & Topics Service")

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(systems.router)

@app.get("/")
def read_root():
    return {"message": "Service is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)