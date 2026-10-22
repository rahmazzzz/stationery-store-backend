
from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import engine
from app.exceptions.handlers import register_exception_handlers
from app.routers.category_router import router as category_router
from app.routers.product_router import router as product_router
from app.routers.product_image_router import router as product_image_router
from app.routers.auth_router import router as auth_router


app = FastAPI(
    title="Stationery Store API",
    description="Backend API for the stationery e-commerce store.",
    version="0.1.0",
)

register_exception_handlers(app)

app.include_router(category_router)
app.include_router(product_router)
app.include_router(product_image_router)
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
def readiness_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ready",
        "database": "connected",
    }
