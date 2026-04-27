import logging


class AppLogger:
    def __init__(self, level: str) -> None:
        self.level = level
        self._logger = logging.getLogger("val-rca")

    def setup(self) -> None:
        logging.basicConfig(
            level=self.level.upper(),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)
