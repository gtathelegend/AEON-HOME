"""
aeon/config/settings.py — Central configuration via environment / .env file.

All secrets and device-specific values are read from environment variables.
Never hard-code device IDs, tokens, or ports in source code.
"""

from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    device_id: str = Field(default="aeon-home-001", validation_alias="AEON_DEVICE_ID")
    owner_id:  str = Field(default="",              validation_alias="AEON_OWNER_ID")

    # ── API server ────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0",   validation_alias="AEON_API_HOST")
    api_port: int = Field(default=8000,        validation_alias="AEON_API_PORT")

    # ── Serial bridge ─────────────────────────────────────────────────────────
    serial_port: str = Field(default="/dev/ttyUSB0", validation_alias="AEON_SERIAL_PORT")
    serial_baud: int = Field(default=115200,          validation_alias="AEON_SERIAL_BAUD")

    # ── QNN / NPU ─────────────────────────────────────────────────────────────
    use_npu:   bool = Field(default=True,                       validation_alias="AEON_USE_NPU")
    model_dir: Path = Field(default=Path("backend/models/bin"), validation_alias="AEON_MODEL_DIR")

    # ── Persistence ───────────────────────────────────────────────────────────
    memory_db_path: Path = Field(
        default=Path("backend/data/aeon_memory.db"), validation_alias="AEON_MEMORY_DB"
    )

    # ── Auth ──────────────────────────────────────────────────────────────────
    jwt_secret:    str = Field(default="CHANGE_ME_IN_PRODUCTION", validation_alias="AEON_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256",                   validation_alias="AEON_JWT_ALG")
    jwt_expire_s:  int = Field(default=3600,                      validation_alias="AEON_JWT_EXPIRE")

    # ── Voice (Sarvam) ────────────────────────────────────────────────────────
    sarvam_api_key: str  = Field(default="", validation_alias="SARVAM_API_KEY")
    sarvam_offline: bool = Field(default=True, validation_alias="SARVAM_OFFLINE")

    # ── Cloud AI 100 (optional) ───────────────────────────────────────────────
    cloud_sync_enabled: bool = Field(default=False, validation_alias="AEON_CLOUD_SYNC")
    cloud_endpoint:     str  = Field(default="",    validation_alias="AEON_CLOUD_ENDPOINT")

    # ── Demo Mode ─────────────────────────────────────────────────────────────
    aeon_demo_mode: bool = Field(default=False, validation_alias="AEON_DEMO_MODE")
    seed_database:  bool = Field(default=False, validation_alias="AEON_SEED_DATABASE")

    # ── Metrics ───────────────────────────────────────────────────────────────
    metrics_port: int = Field(default=9090, validation_alias="AEON_METRICS_PORT")


settings = Settings()
