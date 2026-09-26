from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CRISPR/Cas9 基因编辑设计与多组学决策系统"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api/v1"
    
    # 默认使用本地 SQLite 异步模式，当指定环境变量 DATABASE_URL 时切换为 PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./lifescience.db"
    
    # 允许的跨域来源
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
