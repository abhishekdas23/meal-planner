from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///data/meals.db"
    secret_key: str = "change-me-in-production-use-a-random-string"
    household_pin: str = "1234"
    user_names: list[str] = ["Abhishek", "Richa"]
    algorithm: str = "HS256"
    token_expire_days: int = 90

    model_config = {"env_prefix": "MEAL_"}

    @model_validator(mode="after")
    def fix_postgres_url(self):
        # Render gives postgres:// but SQLAlchemy async needs postgresql+asyncpg://
        url = self.database_url
        if url.startswith("postgres://"):
            self.database_url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            self.database_url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


settings = Settings()
