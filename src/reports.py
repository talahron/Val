from pathlib import Path

from src.models import RCAReport


class ReportWriter:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def setup(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write_json(self, report: RCAReport) -> Path:
        self.output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return self.output_path
