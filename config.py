from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    SUPERADMIN_ID: int
    GROUP_ID: int
    DATABASE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()