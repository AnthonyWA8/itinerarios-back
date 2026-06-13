from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "Wanderlust Planner API"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./wanderlust.db"

    # JWT
    JWT_SECRET: str = "change-this-secret-in-production"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días

    # LLM (Groq)
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # RAG
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # modelo local via sentence-transformers

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://control-de-itinerarios.vercel.app",
    ]


settings = Settings()
