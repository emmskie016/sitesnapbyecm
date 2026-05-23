from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    unsplash_access_key: str
    supabase_db_url: str

    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    r2_public_base: str

    resend_api_key: str
    resend_from_email: str
    resend_operator_email: str

    admin_bearer_token: str

    sentry_dsn: str = ""
    log_level: str = "INFO"
    env: str = Field(default="local")


settings = Settings()
