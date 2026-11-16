from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api import routes_metrics, routes_tiles

app = FastAPI(title=settings.PROJECT_TITLE, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_metrics.router)
app.include_router(routes_tiles.router)

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "online", "aoi": settings.AOI_NAME}