from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_TITLE: str = "Punjab GeoGuardian 3D API"
    VERSION: str = "2.0.0"
    GCP_PROJECT_ID: str = "satelite-514107"
    AOI_NAME: str = "Lahore District"
    AOI_BBOX: list[float] = [74.10, 31.30, 74.55, 31.68]
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()