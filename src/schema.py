import csv
import json
from pathlib import Path

from src.models import DataCatalog, FieldProfile, SourceSchemaProfile


class SchemaProfiler:
    def __init__(self, max_files: int, max_lines: int) -> None:
        self.max_files = max_files
        self.max_lines = max_lines
        self._is_ready = False

    def setup(self) -> None:
        if self.max_files < 1:
            raise ValueError("max_files must be at least 1.")
        if self.max_lines < 1:
            raise ValueError("max_lines must be at least 1.")
        self._is_ready = True

    def profile_catalog(self, catalog: DataCatalog) -> list[SourceSchemaProfile]:
        if not self._is_ready:
            raise ValueError("SchemaProfiler.setup() must be called before profile_catalog().")

        return [
            self._profile_file(file_profile.path)
            for file_profile in catalog.files[: self.max_files]
        ]

    def _profile_file(self, path: Path) -> SourceSchemaProfile:
        suffix = path.suffix.lower() or "<none>"
        if suffix == ".csv":
            return self._profile_csv(path)
        if suffix in {".json", ".jsonl", ".ndjson"}:
            return self._profile_json(path)
        return self._profile_text(path)

    def _profile_csv(self, path: Path) -> SourceSchemaProfile:
        lines = self._read_sample_lines(path)
        fields: list[FieldProfile] = []
        if lines:
            dialect = csv.Sniffer().sniff("\n".join(lines))
            reader = csv.reader(lines, dialect)
            header = next(reader, [])
            fields = [FieldProfile(name=name, inferred_role=self._infer_field_role(name)) for name in header]
            delimiter = dialect.delimiter
        else:
            delimiter = None
        return SourceSchemaProfile(
            source_path=path,
            suffix=".csv",
            is_text_readable=True,
            sample_line_count=len(lines),
            delimiter=delimiter,
            fields=fields,
        )

    def _profile_json(self, path: Path) -> SourceSchemaProfile:
        lines = self._read_sample_lines(path)
        fields: list[FieldProfile] = []
        if lines:
            parsed = json.loads(lines[0])
            if isinstance(parsed, dict):
                fields = [
                    FieldProfile(name=str(name), inferred_role=self._infer_field_role(str(name)))
                    for name in parsed.keys()
                ]
        return SourceSchemaProfile(
            source_path=path,
            suffix=path.suffix.lower(),
            is_text_readable=True,
            sample_line_count=len(lines),
            fields=fields,
        )

    def _profile_text(self, path: Path) -> SourceSchemaProfile:
        lines = self._read_sample_lines(path)
        return SourceSchemaProfile(
            source_path=path,
            suffix=path.suffix.lower() or "<none>",
            is_text_readable=bool(lines),
            sample_line_count=len(lines),
        )

    def _read_sample_lines(self, path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [line for line in text.splitlines()[: self.max_lines] if line.strip()]

    def _infer_field_role(self, field_name: str) -> str:
        normalized = field_name.lower()
        if any(token in normalized for token in ("time", "timestamp", "date")):
            return "timestamp"
        if any(token in normalized for token in ("host", "pod", "node", "service", "instance", "entity")):
            return "entity"
        if any(token in normalized for token in ("latency", "duration", "elapsed")):
            return "latency"
        if any(token in normalized for token in ("status", "code", "success", "error")):
            return "status"
        if any(token in normalized for token in ("cpu", "memory", "cost", "rate", "usage")):
            return "metric"
        return "unknown"
