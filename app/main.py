from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, bookings, centres, diagnostic_tests

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EVE Diagnostics API")
app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(diagnostic_tests.router)
app.include_router(bookings.router)


@app.get("/health")
def health():
    return {"status": "ok"}