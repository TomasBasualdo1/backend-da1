from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

    email_provider: str = "smtp"
    email_api_key: Optional[str] = None
    email_from: Optional[str] = None

    @model_validator(mode="after")
    def validate_email_config(self) -> "Settings":
        prov = self.email_provider.lower().strip()
        if prov not in ("smtp", "resend", "sendgrid"):
            import logging
            logging.warning(
                "Invalid email_provider '%s'. Falling back to 'smtp'.",
                self.email_provider
            )
            self.email_provider = "smtp"
            prov = "smtp"

        if prov == "smtp":
            if not self.smtp_user or not self.smtp_password:
                raise ValueError("smtp_user and smtp_password are required when email_provider is 'smtp'")
        elif prov in ("resend", "sendgrid"):
            if not self.email_api_key:
                raise ValueError(f"email_api_key is required when email_provider is '{prov}'")

        return self

    class Config:
        env_file = ".env"


settings = Settings()

