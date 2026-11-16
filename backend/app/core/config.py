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
    # Groq retiró Llama de su capa gratuita: el modelo vigente es gpt-oss.
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # MCP de mapas (verificación de lugares reales)
    #   auto   -> usa el MCP oficial de Google si hay GOOGLE_MAPS_API_KEY; si no, el servidor propio
    #   google -> solo el MCP oficial de Google Maps (Grounding Lite)
    #   local  -> solo el servidor MCP propio (OpenStreetMap, sin API key)
    #   off    -> desactiva la verificación de lugares
    MAPS_MCP_MODE: str = "auto"
    GOOGLE_MAPS_API_KEY: str = ""
    GOOGLE_MAPS_MCP_URL: str = "https://mapstools.googleapis.com/mcp"
    MAPS_MCP_TIMEOUT_SECONDS: float = 25.0  # tiempo máximo dedicado a verificar un itinerario
    MAPS_MAX_LOOKUPS: int = 10  # máximo de lugares a verificar por itinerario
    MAPS_MAX_DISTANCE_KM: float = 80.0  # descarta coincidencias lejos del destino

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
