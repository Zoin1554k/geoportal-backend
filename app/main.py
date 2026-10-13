from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.redis_client import close_redis, init_redis
from app.routers import auth, features, layers, upload
from app.utils.logger import get_logger

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    log.info("Redis inicializado")
    yield
    await close_redis()
    log.info("Redis encerrado")


app = FastAPI(
    title="GeoPortal API",
    version="1.0.0",
    description="Backend geoespacial — FastAPI + PostGIS + Redis",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Erro não tratado em %s", request.url.path)
    if settings.ENV == "production":
        return JSONResponse(status_code=500, content={"error": "Erro interno"})
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(layers.router)
app.include_router(features.router)
app.include_router(upload.router)