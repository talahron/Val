from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATA_ROOT: str = Field(default=".", description="Customer data root folder to inspect.")
    LOG_LEVEL: str = Field(default="INFO", description="Application log level.")
    LLM_PROVIDER: str = Field(default="none", description="LLM provider used by the RCA agent.")
    LLM_MODEL: str = Field(default="openai:gpt-4.1-mini", description="Pydantic AI model identifier.")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key loaded from .env.")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
