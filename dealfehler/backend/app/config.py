"""Zentrale Konfiguration. Alle Geheimnisse kommen ausschließlich aus Umgebungsvariablen."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # --- Allgemein ---
    app_env: str = "development"  # development | production | test
    app_name: str = "DealFehler"
    public_base_url: str = "http://localhost:3000"  # Website (Next.js)
    api_base_url: str = "http://localhost:8000"  # Backend (für /go/-Links und Medien)
    log_level: str = "INFO"
    log_json: bool = False

    # --- Sicherheit ---
    secret_key: str = Field(default="dev-insecure-change-me-0123456789abcdef", min_length=32)
    access_token_minutes: int = 60 * 12
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    cors_origins: str = "http://localhost:3000"

    # --- Infrastruktur ---
    database_url: str = "postgresql+psycopg://dealfehler:dealfehler@localhost:5432/dealfehler"
    redis_url: str = "redis://localhost:6379/0"

    # --- Medien / Speicher ---
    storage_backend: str = "local"  # local | s3
    media_dir: str = "./media"
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None  # öffentlich erreichbar (Instagram braucht das)
    font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_path_regular: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    # --- Amazon PartnerNet ---
    amazon_partner_tag: str | None = None  # z.B. dealfehler-21
    amazon_marketplace: str = "www.amazon.de"
    # Tracking-IDs je Kanal (optional, Komma-getrennt "instagram=df-ig-21,pinterest=df-pin-21")
    amazon_channel_tracking_ids: str = ""

    # --- Datenquellen ---
    keepa_api_key: str | None = None
    keepa_domain: int = 3  # 3 = amazon.de
    awin_api_token: str | None = None
    awin_publisher_id: str | None = None

    # --- KI ---
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-5-5"
    llm_daily_budget_usd: float = 2.0
    llm_monthly_budget_usd: float = 40.0

    # --- Plattformen ---
    meta_graph_version: str = "v23.0"
    instagram_user_id: str | None = None
    instagram_access_token: str | None = None
    pinterest_access_token: str | None = None
    pinterest_api_base: str = "https://api.pinterest.com/v5"
    telegram_bot_token: str | None = None
    telegram_channel_id: str | None = None  # z.B. @dealfehler
    whatsapp_channel_invite_url: str | None = None

    # --- Alarme ---
    alert_telegram_chat_id: str | None = None  # privater Chat für Alarme
    alert_webhook_url: str | None = None  # generischer Webhook (Slack/Discord/…)

    # --- Betrieb ---
    dry_run: bool = True  # Standard: NICHTS wird extern veröffentlicht
    max_price_age_minutes: int = 60  # Preis muss vor Veröffentlichung so frisch sein
    timezone: str = "Europe/Berlin"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    def channel_tracking_ids(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for part in self.amazon_channel_tracking_ids.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
