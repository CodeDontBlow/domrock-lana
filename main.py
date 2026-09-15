from fastapi import FastAPI, Depends
from app.core.config import Settings, get_settings

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "FastAPI is running on Ubuntu"}

app = FastAPI()

@app.get("/info")
def get_app_info(settings: Settings = Depends(get_settings)):
    return {
        "database_url": settings.DATABASE_URL,
        "port": settings.PORT
    }
