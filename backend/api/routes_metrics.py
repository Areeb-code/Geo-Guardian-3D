from typing import Optional
from fastapi import APIRouter, Query
from backend.schemas import MetricsResponse
from backend.services.change_service import fetch_change_metrics

router = APIRouter(prefix="/api", tags=["Metrics"])

@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    location: str = Query("Lahore", description="Any city, district, or province worldwide"),
    mode: str = Query("live", pattern="^(live|compare)$"),
    year_a: int = Query(2019, ge=1984, le=2026),
    year_b: int = Query(2025, ge=1984, le=2026),
    smog_date: Optional[str] = Query(None, description="YYYY-MM-DD for specific smog date"),
    refresh: bool = Query(False)
):
    return fetch_change_metrics(location, mode, year_a, year_b, smog_date, refresh)