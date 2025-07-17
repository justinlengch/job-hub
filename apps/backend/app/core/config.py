from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", description="Supabase service role key")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase anon key")
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")


settings = Settings()
