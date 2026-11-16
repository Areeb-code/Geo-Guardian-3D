from typing import Optional
from fastapi import APIRouter, Query
from backend.schemas import TilesResponse
from backend.services.gee_service import get_geoguardian_payload

router = APIRouter(prefix="/api", tags=["Map Tiles"])

@router.get("/tiles", response_model=TilesResponse)
def get_tiles(
    location: str = Query("Lahore", description="Any city, district, or province worldwide"),
    mode: str = Query("live", pattern="^(live|compare)$"),
    year_a: int = Query(2019, ge=1984, le=2026),
    year_b: int = Query(2025, ge=1984, le=2026),
    smog_date: Optional[str] = Query(None, description="YYYY-MM-DD for specific smog date"),
    refresh: bool = Query(False)
):
    return get_geoguardian_payload(location, mode, year_a, year_b, smog_date, refresh)["tiles"]