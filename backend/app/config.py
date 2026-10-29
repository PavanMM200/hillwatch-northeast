from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import re

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str = 'sqlite:///./data/app.sqlite'
    data_dir: Path = ROOT / 'data'
    allowed_origins: str = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080'
    cookie_secure: bool = False
    google_cloud_project: str = ''
    maps_browser_key: str = ''
    maps_routes_key: str = ''
    maps_apis_enabled: bool = False
    maps_billing_confirmed: bool = False
    maps_browser_restrictions: str = ''
    maps_server_restrictions: str = ''
    ee_project: str = ''
    ee_auth_method: str = 'adc'
    google_application_credentials: str = ''
    ee_service_account: str = ''
    ee_api_enabled: bool = False
    ee_project_registered: bool = False
    matlab_method: str = 'batch'
    matlab_executable: str = ''
    matlab_version: str = ''
    matlab_engine_available: bool = False
    matlab_work_dir: Path = ROOT / 'data/matlab'
    matlab_timeout_seconds: int = 900
    scene_limit: int = 60
    min_coverage: float = .85
    stale_days: int = 14
    sar_threshold_db: float = 3
    ndvi_loss_threshold: float = .2
    min_candidate_pixels: int = 9
    min_slope_degrees: float = 10
    max_route_km: float = 400
    job_timeout_seconds: int = 7200

    @field_validator('ee_project', 'google_cloud_project')
    @classmethod
    def project_id(cls, v):
        if v and not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', v):
            raise ValueError('Cloud project ID must be 6–30 lowercase letters, digits or hyphens')
        return v

settings = Settings()
