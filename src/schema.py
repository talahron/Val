import csv
import json
from pathlib import Path

from src.models import (
    DataCatalog,
    FieldProfile,
    NumericFieldSummary,
    NumericObservation,
    SourceKind,
    SourceSchemaProfile,
)


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
        timestamp_examples: list[str] = []
        numeric_summaries: list[NumericFieldSummary] = []
        if lines:
            dialect = csv.Sniffer().sniff("\n".join(lines))
            reader = list(csv.reader(lines, dialect))
            header = reader[0] if reader else []
            data_rows = reader[1:]
            fields = [FieldProfile(name=name, inferred_role=self._infer_field_role(name)) for name in header]
            timestamp_examples = self._extract_timestamp_examples(fields, data_rows)
            numeric_summaries = self._summarize_numeric_fields(fields, header, data_rows)
            delimiter = dialect.delimiter
        else:
            delimiter = None
        return SourceSchemaProfile(
            source_path=path,
            suffix=".csv",
            inferred_source_kind=self._infer_source_kind(fields),
            is_text_readable=True,
            sample_line_count=len(lines),
            delimiter=delimiter,
            fields=fields,
            timestamp_examples=timestamp_examples,
            numeric_summaries=numeric_summaries,
        )

    def _profile_json(self, path: Path) -> SourceSchemaProfile:
        lines = self._read_sample_lines(path)
        fields: list[FieldProfile] = []
        timestamp_examples: list[str] = []
        numeric_summaries: list[NumericFieldSummary] = []
        if lines:
            parsed = json.loads(lines[0])
            if isinstance(parsed, dict):
                fields = [
                    FieldProfile(name=str(name), inferred_role=self._infer_field_role(str(name)))
                    for name in parsed.keys()
                ]
                timestamp_examples = [
                    str(parsed[field.name])
                    for field in fields
                    if field.inferred_role == "timestamp" and field.name in parsed
                ][:3]
                numeric_summaries = self._summarize_json_numeric_fields(fields, parsed)
        return SourceSchemaProfile(
            source_path=path,
            suffix=path.suffix.lower(),
            inferred_source_kind=self._infer_source_kind(fields),
            is_text_readable=True,
            sample_line_count=len(lines),
            fields=fields,
            timestamp_examples=timestamp_examples,
            numeric_summaries=numeric_summaries,
        )

    def _profile_text(self, path: Path) -> SourceSchemaProfile:
        lines = self._read_sample_lines(path)
        return SourceSchemaProfile(
            source_path=path,
            suffix=path.suffix.lower() or "<none>",
            inferred_source_kind=SourceKind.UNKNOWN,
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

    def _infer_source_kind(self, fields: list[FieldProfile]) -> SourceKind:
        roles = {field.inferred_role for field in fields}
        if "metric" in roles or "latency" in roles:
            return SourceKind.METRIC
        if "status" in roles and "timestamp" in roles:
            return SourceKind.EVENT
        if "timestamp" in roles and "entity" in roles:
            return SourceKind.LOG
        return SourceKind.UNKNOWN

    def _extract_timestamp_examples(
        self,
        fields: list[FieldProfile],
        data_rows: list[list[str]],
    ) -> list[str]:
        timestamp_indexes = [
            index for index, field in enumerate(fields) if field.inferred_role == "timestamp"
        ]
        examples: list[str] = []
        for row in data_rows:
            for index in timestamp_indexes:
                if index < len(row) and row[index]:
                    examples.append(row[index])
        return examples[:3]

    def _summarize_numeric_fields(
        self,
        fields: list[FieldProfile],
        header: list[str],
        data_rows: list[list[str]],
    ) -> list[NumericFieldSummary]:
        summaries: list[NumericFieldSummary] = []
        timestamp_index = self._first_role_index(fields, "timestamp")
        entity_index = self._first_role_index(fields, "entity")
        for index, field_name in enumerate(header):
            observations = [
                NumericObservation(
                    field_name=field_name,
                    value=float(row[index]),
                    timestamp=self._row_value(row, timestamp_index),
                    entity_id=self._row_value(row, entity_index),
                )
                for row in data_rows
                if index < len(row) and self._is_float(row[index])
            ]
            values = [observation.value for observation in observations]
            if not values:
                continue
            summaries.append(
                NumericFieldSummary(
                    name=field_name,
                    count=len(values),
                    minimum=min(values),
                    maximum=max(values),
                    average=sum(values) / len(values),
                    observations=observations,
                )
            )
        return summaries

    def _summarize_json_numeric_fields(
        self,
        fields: list[FieldProfile],
        parsed: dict[object, object],
    ) -> list[NumericFieldSummary]:
        summaries: list[NumericFieldSummary] = []
        timestamp_key = self._first_role_name(fields, "timestamp")
        entity_key = self._first_role_name(fields, "entity")
        for key, value in parsed.items():
            if isinstance(value, int | float):
                numeric_value = float(value)
                summaries.append(
                    NumericFieldSummary(
                        name=str(key),
                        count=1,
                        minimum=numeric_value,
                        maximum=numeric_value,
                        average=numeric_value,
                        observations=[
                            NumericObservation(
                                field_name=str(key),
                                value=numeric_value,
                                timestamp=str(parsed[timestamp_key]) if timestamp_key in parsed else None,
                                entity_id=str(parsed[entity_key]) if entity_key in parsed else None,
                            )
                        ],
                    )
                )
        return summaries

    def _is_float(self, value: str) -> bool:
        cleaned = value.strip()
        if not cleaned:
            return False
        try:
            float(cleaned)
        except ValueError:
            return False
        return True

    def _first_role_index(self, fields: list[FieldProfile], role: str) -> int | None:
        for index, field in enumerate(fields):
            if field.inferred_role == role:
                return index
        return None

    def _first_role_name(self, fields: list[FieldProfile], role: str) -> str:
        for field in fields:
            if field.inferred_role == role:
                return field.name
        return ""

    def _row_value(self, row: list[str], index: int | None) -> str | None:
        if index is None or index >= len(row):
            return None
        value = row[index].strip()
        return value or None
