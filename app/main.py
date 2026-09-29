from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EVE Diagnostics API")
app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}