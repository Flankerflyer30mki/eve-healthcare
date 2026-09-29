from fastapi import FastAPI

from app.database import Base, engine

Base.metadata.create_all(bind=engine)  # fine for this scope; Alembic is a "would improve" item

app = FastAPI(title="EVE Diagnostics API")


@app.get("/health")
def health():
    return {"status": "ok"}