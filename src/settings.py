from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATA_ROOT: str = Field(default=".", description="Customer data root folder to inspect.")
    OUTPUT_PATH: str = Field(default="reports/rca_report.json", description="Path for the RCA JSON report.")
    IMPACTED_SLI: str = Field(default="", description="Optional impacted SLI or business signal.")
    ANOMALY_START: str = Field(default="", description="Optional anomaly start time or time window.")
    CUSTOMER_CONTEXT: str = Field(default="", description="Optional free-text customer environment context.")
    MAX_SCHEMA_FILES: int = Field(default=25, description="Maximum files to sample for schema profiling.")
    MAX_SCHEMA_LINES: int = Field(default=5, description="Maximum lines to sample per schema-profiled file.")
    LOG_LEVEL: str = Field(default="INFO", description="Application log level.")
    LLM_PROVIDER: str = Field(default="none", description="LLM provider used by the RCA agent.")
    LLM_MODEL: str = Field(default="openai:gpt-4.1-mini", description="Pydantic AI model identifier.")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key loaded from .env.")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
