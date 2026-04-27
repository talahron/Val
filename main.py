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
        impacted_sli=config.IMPACTED_SLI or None,
        anomaly_start=config.ANOMALY_START or None,
        customer_context=config.CUSTOMER_CONTEXT or None,
        llm_provider=config.LLM_PROVIDER,
        llm_model=config.LLM_MODEL,
        openai_api_key=config.OPENAI_API_KEY,
        logger=logger,
    )
    agent.setup()
    agent.run()


if __name__ == "__main__":
    main()
