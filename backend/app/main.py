from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database.session import Base, engine
# Importar modelos para que se registren en Base.metadata
from app.infrastructure.database.models import user_model, itinerary_model, feedback_model  # noqa: F401
from app.infrastructure.rag import document_chunk_model  # noqa: F401
from app.presentation.api.v1 import auth_router, itinerary_router, feedback_router, finetuned_router
from app.presentation.middlewares.error_handler import unhandled_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas si no existen (suficiente para desarrollo con SQLite).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth_router.router)
app.include_router(itinerary_router.router)
app.include_router(feedback_router.router)
app.include_router(finetuned_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
