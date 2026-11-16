from typing import Optional
from backend.services.gee_service import get_geoguardian_payload

def fetch_change_metrics(
    location: str = "Lahore",
    mode: str = "live",
    year_a: int = 2019,
    year_b: int = 2025,
    smog_date: Optional[str] = None,
    force_refresh: bool = False
) -> dict:
    return get_geoguardian_payload(location, mode, year_a, year_b, smog_date, force_refresh)["metrics"]