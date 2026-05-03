from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
