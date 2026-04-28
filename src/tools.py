import csv
from pathlib import Path
import re

from src.models import (
    CatalogProfile,
    DataCatalog,
    DelimitedRow,
    Evidence,
    EvidenceRelation,
    InvestigationToolSpec,
    SourceKind,
    StructuredExtraction,
    ToolInputField,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolValidationResult,
)


class InvestigationToolFactory:
    def __init__(self) -> None:
        self._is_ready = False

    def setup(self) -> None:
        self._is_ready = True

    def generate_specs(self, profile: CatalogProfile) -> list[InvestigationToolSpec]:
        if not self._is_ready:
            raise ValueError("InvestigationToolFactory.setup() must be called first.")

        specs = [self._catalog_summary_spec()]
        specs.extend(self._source_kind_spec(source_kind) for source_kind in profile.source_kinds)
        return specs

    def validate_specs(self, specs: list[InvestigationToolSpec]) -> list[ToolValidationResult]:
        if not self._is_ready:
            raise ValueError("InvestigationToolFactory.setup() must be called first.")

        return [self._validate_spec(spec) for spec in specs]

    def execute_spec(
        self,
        spec: InvestigationToolSpec,
        catalog: DataCatalog,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        if not self._is_ready:
            raise ValueError("InvestigationToolFactory.setup() must be called first.")
        if spec.name != request.tool_name:
            raise ValueError("Tool execution request does not match the selected spec.")

        if spec.name == "catalog_summary":
            return self._execute_catalog_summary(spec, catalog)
        return self._execute_source_inspection(spec, catalog, request)

    def _catalog_summary_spec(self) -> InvestigationToolSpec:
        return InvestigationToolSpec(
            name="catalog_summary",
            purpose="Summarize available customer data sources by suffix, size, and detected category.",
            source_kind=SourceKind.UNKNOWN,
            input_fields=[
                ToolInputField(
                    name="catalog_root",
                    field_type="Path",
                    required=True,
                    description="Root folder that was profiled.",
                )
            ],
            output_model="CatalogProfile",
        )

    def _source_kind_spec(self, source_kind: SourceKind) -> InvestigationToolSpec:
        return InvestigationToolSpec(
            name=f"inspect_{source_kind.value}_sources",
            purpose=f"Inspect files classified as {source_kind.value} and prepare RCA evidence candidates.",
            source_kind=source_kind,
            input_fields=[
                ToolInputField(
                    name="time_window",
                    field_type="str | None",
                    required=False,
                    description="Optional anomaly time window used to focus inspection.",
                ),
                ToolInputField(
                    name="entity_id",
                    field_type="str | None",
                    required=False,
                    description="Optional entity identifier used to focus inspection.",
                ),
            ],
            output_model="list[Evidence]",
        )

    def _validate_spec(self, spec: InvestigationToolSpec) -> ToolValidationResult:
        has_name = bool(spec.name.strip())
        has_inputs = all(field.name.strip() and field.field_type.strip() for field in spec.input_fields)
        has_output = bool(spec.output_model.strip())
        is_valid = has_name and has_inputs and has_output
        summary = "Tool spec is valid." if is_valid else "Tool spec is missing required metadata."
        return ToolValidationResult(tool_name=spec.name, is_valid=is_valid, summary=summary)

    def _execute_catalog_summary(
        self,
        spec: InvestigationToolSpec,
        catalog: DataCatalog,
    ) -> ToolExecutionResult:
        evidence = [
            Evidence(
                evidence_id=f"{spec.name}:file_type:{summary.suffix}",
                source_path=catalog.root,
                signal_type="catalog_file_type_summary",
                summary=(
                    f"Detected {summary.count} files with suffix {summary.suffix} "
                    f"covering {summary.total_size_bytes} bytes."
                ),
                relation=EvidenceRelation.NEUTRAL,
                confidence=1.0,
            )
            for summary in catalog.file_type_summaries
        ]
        return ToolExecutionResult(
            tool_name=spec.name,
            is_successful=True,
            evidence=evidence,
            summary=f"Catalog summary produced {len(evidence)} evidence records.",
        )

    def _execute_source_inspection(
        self,
        spec: InvestigationToolSpec,
        catalog: DataCatalog,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        matching_files = [
            file_profile
            for file_profile in catalog.files
            if file_profile.source_kind == request.source_kind
        ]
        evidence: list[Evidence] = []
        extractions: list[StructuredExtraction] = []
        for index, file_profile in enumerate(matching_files, start=1):
            focused_evidence = self._focused_source_evidence(spec, file_profile.path, request, index)
            if focused_evidence:
                evidence.extend(focused_evidence)
                extractions.extend(
                    self._structured_extractions(file_profile.path, request)
                )
                continue
            evidence.append(
                Evidence(
                    evidence_id=f"{spec.name}:source:{index}",
                    source_path=file_profile.path,
                    entity_id=request.entity_id,
                    signal_type=f"{request.source_kind.value}_source_available",
                    summary=(
                        f"Source file {file_profile.relative_path.as_posix()} is available "
                        f"for {request.source_kind.value} inspection."
                    ),
                    relation=EvidenceRelation.NEUTRAL,
                    confidence=0.5,
                )
            )
        return ToolExecutionResult(
            tool_name=spec.name,
            is_successful=True,
            evidence=evidence,
            extractions=extractions,
            summary=f"Inspected {len(matching_files)} {request.source_kind.value} sources.",
        )

    def _focused_source_evidence(
        self,
        spec: InvestigationToolSpec,
        source_path: Path,
        request: ToolExecutionRequest,
        source_index: int,
    ) -> list[Evidence]:
        if not request.time_window and not request.entity_id:
            return []
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        matching_lines = [
            line.strip()
            for line in text.splitlines()
            if self._line_matches_request(line, request)
        ][:5]
        return [
            Evidence(
                evidence_id=f"{spec.name}:focus:{source_index}:{line_index}",
                source_path=source_path,
                entity_id=request.entity_id,
                signal_type=f"{request.source_kind.value}_focused_match",
                summary=f"Matched focused inspection line: {self._shorten(line)}",
                relation=EvidenceRelation.SUPPORTS,
                confidence=0.75,
            )
            for line_index, line in enumerate(matching_lines, start=1)
        ]

    def _structured_extractions(
        self,
        source_path: Path,
        request: ToolExecutionRequest,
    ) -> list[StructuredExtraction]:
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        delimited_extractions = self._delimited_extractions(source_path, text, request)
        if delimited_extractions:
            return delimited_extractions
        return [
            StructuredExtraction(
                extraction_id=f"{request.source_kind.value}:{self._safe_id(source_path)}:line:{line_index}",
                source_path=source_path,
                source_kind=request.source_kind,
                signal_type=self._line_signal_type(request.source_kind),
                timestamp=self._extract_timestamp(line),
                entity_id=request.entity_id or self._extract_entity(line),
                severity=self._extract_severity(line) if request.source_kind == SourceKind.LOG else None,
                status=self._extract_status(line),
                text=self._shorten(line.strip()),
            )
            for line_index, line in enumerate(text.splitlines(), start=1)
            if self._line_matches_request(line, request)
        ][:5]

    def _delimited_extractions(
        self,
        source_path: Path,
        text: str,
        request: ToolExecutionRequest,
    ) -> list[StructuredExtraction]:
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return []
        delimiter = "\t" if "\t" in lines[0] else ","
        if delimiter not in lines[0]:
            return []
        reader = csv.DictReader(lines, delimiter=delimiter)
        if not reader.fieldnames:
            return []
        extractions: list[StructuredExtraction] = []
        for row_index, row in enumerate(reader, start=1):
            delimited_row = DelimitedRow(
                fieldnames=reader.fieldnames,
                values=[str(row.get(field) or "") for field in reader.fieldnames],
            )
            row_text = delimited_row.as_text(delimiter)
            if not self._line_matches_request(row_text, request):
                continue
            extractions.extend(
                self._row_extractions(
                    source_path=source_path,
                    request=request,
                    row=delimited_row,
                    row_index=row_index,
                    row_text=row_text,
                )
            )
            if len(extractions) >= 5:
                return extractions[:5]
        return extractions[:5]

    def _row_extractions(
        self,
        source_path: Path,
        request: ToolExecutionRequest,
        row: DelimitedRow,
        row_index: int,
        row_text: str,
    ) -> list[StructuredExtraction]:
        timestamp = self._row_value_by_role(row, ("timestamp", "time", "date"))
        entity_id = request.entity_id or self._row_value_by_role(
            row,
            ("service", "host", "node", "pod", "instance", "entity"),
        )
        status = self._row_value_by_role(row, ("status", "code", "result", "state"))
        metric_extractions = [
            StructuredExtraction(
                extraction_id=(
                    f"{request.source_kind.value}:{self._safe_id(source_path)}:"
                    f"row:{row_index}:field:{self._safe_id_text(field_name)}"
                ),
                source_path=source_path,
                source_kind=request.source_kind,
                signal_type=self._row_signal_type(request.source_kind),
                signal_name=field_name,
                timestamp=timestamp,
                entity_id=entity_id,
                status=status,
                value=value,
                text=self._shorten(row_text),
            )
            for field_name in row.fieldnames
            for value in [self._float_value(row.value_for(field_name))]
            if value is not None and not self._is_context_field(field_name)
        ]
        if metric_extractions:
            return metric_extractions
        return [
            StructuredExtraction(
                extraction_id=f"{request.source_kind.value}:{self._safe_id(source_path)}:row:{row_index}",
                source_path=source_path,
                source_kind=request.source_kind,
                signal_type=self._row_signal_type(request.source_kind),
                timestamp=timestamp,
                entity_id=entity_id,
                status=status,
                text=self._shorten(row_text),
            )
        ]

    def _row_value_by_role(
        self,
        row: DelimitedRow,
        role_tokens: tuple[str, ...],
    ) -> str | None:
        for field_name in row.fieldnames:
            normalized = field_name.lower()
            if any(token in normalized for token in role_tokens):
                value = row.value_for(field_name)
                if value:
                    return value
        return None

    def _float_value(self, value: str | None) -> float | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if re.fullmatch(r"-?\d+(?:\.\d+)?", normalized):
            return float(normalized)
        return None

    def _is_context_field(self, field_name: str) -> bool:
        normalized = field_name.lower()
        return any(
            token in normalized
            for token in ("time", "date", "service", "host", "node", "pod", "instance", "entity", "status", "code")
        )

    def _row_signal_type(self, source_kind: SourceKind) -> str:
        if source_kind == SourceKind.METRIC:
            return "metric_sample"
        if source_kind == SourceKind.EVENT:
            return "event_record"
        if source_kind == SourceKind.TRACE:
            return "trace_span"
        if source_kind == SourceKind.CONFIGURATION:
            return "configuration_record"
        return f"{source_kind.value}_record"

    def _line_signal_type(self, source_kind: SourceKind) -> str:
        if source_kind == SourceKind.LOG:
            return "log_message"
        return f"{source_kind.value}_line_match"

    def _extract_timestamp(self, line: str) -> str | None:
        match = re.search(r"\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b", line)
        if not match:
            return None
        return match.group(0).replace(" ", "T")

    def _extract_severity(self, line: str) -> str | None:
        normalized = line.lower()
        if any(token in normalized for token in ("fatal", "critical", "exception", "error")):
            return "error"
        if "warn" in normalized:
            return "warning"
        if any(token in normalized for token in ("info", "debug", "notice")):
            return "info"
        return None

    def _extract_entity(self, line: str) -> str | None:
        match = re.search(r"\b(?:service|host|node|pod|instance|entity)[=:]\s*([A-Za-z0-9_.:-]+)", line)
        if match:
            return match.group(1)
        return None

    def _extract_status(self, line: str) -> str | None:
        match = re.search(r"\b(?:status|code|result|state)[=:]\s*([A-Za-z0-9_.:-]+)", line, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _line_matches_request(self, line: str, request: ToolExecutionRequest) -> bool:
        if request.time_window and self._minute_prefix(request.time_window) in line.replace(" ", "T"):
            return True
        if request.entity_id and request.entity_id in line:
            return True
        return False

    def _minute_prefix(self, timestamp: str) -> str:
        return timestamp.strip().replace(" ", "T")[:16]

    def _shorten(self, value: str) -> str:
        if len(value) <= 180:
            return value
        return value[:177] + "..."

    def _safe_id(self, path: Path) -> str:
        return self._safe_id_text(path.as_posix())

    def _safe_id_text(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_") or "unknown"
