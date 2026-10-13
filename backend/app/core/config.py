from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_VALUES = {"change-me", "changeme", "secret", "password"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "production" turns on the checks below and hides the API docs.
    environment: str = "development"

    database_url: str = "postgresql+psycopg://lgs:lgs@localhost:5432/lgs_coaching"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5173"]

    admin_email: str = "admin@example.com"
    admin_password: str | None = None

    # A login is blocked after this many wrong passwords for one email within the window.
    login_max_attempts: int = 5
    login_window_minutes: int = 15

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def refuse_weak_secrets_in_production(self) -> "Settings":
        if not self.is_production:
            return self
        if len(self.jwt_secret) < 32 or self.jwt_secret.lower() in WEAK_VALUES:
            raise ValueError("JWT_SECRET must be a random value of at least 32 characters in production")
        if self.admin_password is not None and (
            len(self.admin_password) < 8 or self.admin_password.lower() in WEAK_VALUES
        ):
            raise ValueError("ADMIN_PASSWORD must be at least 8 characters and not a placeholder in production")
        return self


settings = Settings()
