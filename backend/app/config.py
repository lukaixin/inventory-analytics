from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", f"duckdb:///{Path(__file__).resolve().parents[2] / '.runtime' / 'inventory.duckdb'}")
APP_ENV = os.getenv("APP_ENV", "development")
IDENTITY_PROVIDER = os.getenv("IDENTITY_PROVIDER", "local")
ALLOWED_LEGACY_SCOPES = {x.strip() for x in os.getenv("ALLOWED_LEGACY_SCOPES", "").split(",") if x.strip()}
ALLOWED_PDT_SCOPES = {x.strip() for x in os.getenv("ALLOWED_PDT_SCOPES", "").split(",") if x.strip()}
ALLOWED_MANAGEMENT_BUSINESS_LINES = {x.strip() for x in os.getenv("ALLOWED_MANAGEMENT_BUSINESS_LINES", "").split(",") if x.strip()}
if APP_ENV == "production":
    raise RuntimeError("当前版本尚未实现正式身份提供方，禁止在生产环境启动")
