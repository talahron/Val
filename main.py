from pathlib import Path

from src.agent import RCAAgent
from src.logger import AppLogger
from src.settings import Settings


def main() -> None:
    config = Settings()
    logger = AppLogger(level=config.LOG_LEVEL)
    logger.setup()

    agent = RCAAgent(
        data_root=Path(config.DATA_ROOT),
        output_path=Path(config.OUTPUT_PATH),
        markdown_output_path=Path(config.MARKDOWN_OUTPUT_PATH),
        impacted_sli=config.IMPACTED_SLI or None,
        anomaly_start=config.ANOMALY_START or None,
        customer_context=config.CUSTOMER_CONTEXT or None,
        max_schema_files=config.MAX_SCHEMA_FILES,
        max_schema_lines=config.MAX_SCHEMA_LINES,
        max_hypotheses=config.MAX_HYPOTHESES,
        max_investigation_cycles=config.MAX_INVESTIGATION_CYCLES,
        llm_provider=config.LLM_PROVIDER,
        llm_model=config.LLM_MODEL,
        openai_api_key=config.OPENAI_API_KEY,
        logger=logger,
    )
    agent.setup()
    agent.run()


if __name__ == "__main__":
    main()
