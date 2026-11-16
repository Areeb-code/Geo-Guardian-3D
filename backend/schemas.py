from typing import Optional
from pydantic import BaseModel

class MetricsResponse(BaseModel):
    mode: str
    aoi: str
    center: list[float]
    bbox: list[float]
    total_area_sqkm: float
    year_a_label: str
    year_b_label: str
    veg_a_sqkm: float
    veg_b_sqkm: float
    built_a_sqkm: float
    built_b_sqkm: float
    converted_sqkm: float
    loss_pct: float
    smog_a_index: Optional[float]
    smog_b_index: Optional[float]
    smog_status: str
    smog_date_window: str

class TilesResponse(BaseModel):
    rgb_a: str
    rgb_b: str
    class_a: str
    class_b: str
    change: str
    smog_a: Optional[str]
    smog_b: Optional[str]