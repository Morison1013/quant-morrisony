from fastapi import APIRouter

from app.api.stock import router as stock_router
from app.api.scanner import router as scanner_router
from app.api.dashboard import router as dashboard_router
from app.api.emotion import router as emotion_router
from app.api.rag import router as rag_router

api_router = APIRouter(prefix="/api")
api_router.include_router(stock_router)
api_router.include_router(scanner_router)
api_router.include_router(dashboard_router)
api_router.include_router(emotion_router)
api_router.include_router(rag_router)
