from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"
    EVENT = "event"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class EvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


class FileProfile(BaseModel):
    path: Path
    relative_path: Path
    suffix: str = Field(description="Lowercase file suffix.")
    size_bytes: int
    source_kind: SourceKind


class FieldProfile(BaseModel):
    name: str
    inferred_role: str


class NumericObservation(BaseModel):
    field_name: str
    value: float
    timestamp: str | None = None
    entity_id: str | None = None


class NumericFieldSummary(BaseModel):
    name: str
    count: int
    minimum: float
    maximum: float
    average: float
    observations: list[NumericObservation] = Field(default_factory=list)


class MessageTemplateSummary(BaseModel):
    template: str
    count: int
    severity: str = "unknown"


class MessageBurstSummary(BaseModel):
    template: str
    severity: str
    window_start: str
    count: int


class TextSignalSummary(BaseModel):
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    sample_messages: list[str] = Field(default_factory=list)
    message_templates: list[MessageTemplateSummary] = Field(default_factory=list)
    message_bursts: list[MessageBurstSummary] = Field(default_factory=list)


class SourceSchemaProfile(BaseModel):
    source_path: Path
    suffix: str
    inferred_source_kind: SourceKind = SourceKind.UNKNOWN
    is_text_readable: bool
    sample_line_count: int
    delimiter: str | None = None
    fields: list[FieldProfile] = Field(default_factory=list)
    timestamp_examples: list[str] = Field(default_factory=list)
    numeric_summaries: list[NumericFieldSummary] = Field(default_factory=list)
    text_summary: TextSignalSummary | None = None


class FileTypeSummary(BaseModel):
    suffix: str
    count: int
    total_size_bytes: int


class DataCatalog(BaseModel):
    root: Path
    files: list[FileProfile]
    file_type_summaries: list[FileTypeSummary]


class Entity(BaseModel):
    entity_id: str
    entity_type: str
    display_name: str
    service_name: str | None = None
    environment: str | None = None
    parent_entity_id: str | None = None
    child_entity_ids: list[str] = Field(default_factory=list)
    observed_metric_names: list[str] = Field(default_factory=list)
    related_source_paths: list[Path] = Field(default_factory=list)


class Evidence(BaseModel):
    evidence_id: str
    source_path: Path
    entity_id: str | None = None
    signal_type: str
    summary: str
    relation: EvidenceRelation
    confidence: float = Field(ge=0.0, le=1.0)


class AnomalyCandidate(BaseModel):
    candidate_id: str
    source_path: Path
    signal_name: str
    score: float = Field(ge=0.0)
    summary: str
    time_aligned: bool = False
    timestamp: str | None = None
    entity_id: str | None = None


class RCAHypothesis(BaseModel):
    hypothesis_id: str
    title: str
    affected_signal: str
    supporting_candidate_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class InvestigationRequest(BaseModel):
    data_root: Path
    impacted_sli: str | None = None
    anomaly_start: str | None = None
    customer_context: str | None = None


class AgentResponse(BaseModel):
    """Schema for forced JSON output."""

    summary: str = Field(..., description="The AI generated summary")
    confidence: float = Field(..., description="Result confidence score", ge=0.0, le=1.0)


class ToolRunRecord(BaseModel):
    tool_name: str
    was_validated: bool
    was_executed: bool
    evidence_count: int
    extraction_count: int
    summary: str


class InvestigationCycle(BaseModel):
    cycle_id: str
    generated_tool_count: int
    valid_tool_count: int
    execution_records: list[ToolRunRecord] = Field(default_factory=list)
    evidence_count: int
    hypothesis_count: int


class RCAReport(BaseModel):
    executive_summary: str
    impacted_sli: str | None
    suspected_root_cause: str | None
    affected_entities: list[Entity] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    schema_profiles: list[SourceSchemaProfile] = Field(default_factory=list)
    anomaly_candidates: list[AnomalyCandidate] = Field(default_factory=list)
    hypotheses: list[RCAHypothesis] = Field(default_factory=list)
    generated_tools: list[InvestigationToolSpec] = Field(default_factory=list)
    tool_validations: list[ToolValidationResult] = Field(default_factory=list)
    investigation_cycles: list[InvestigationCycle] = Field(default_factory=list)
    alternative_hypotheses: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    data_gaps: list[str] = Field(default_factory=list)


class CatalogProfile(BaseModel):
    total_files: int
    total_size_bytes: int
    source_kinds: list[SourceKind]
    summaries: list[FileTypeSummary]


class ToolInputField(BaseModel):
    name: str
    field_type: str
    required: bool
    description: str


class InvestigationToolSpec(BaseModel):
    name: str
    purpose: str
    source_kind: SourceKind
    input_fields: list[ToolInputField]
    output_model: str


class ToolValidationResult(BaseModel):
    tool_name: str
    is_valid: bool
    summary: str


class ToolExecutionRequest(BaseModel):
    tool_name: str
    source_kind: SourceKind
    time_window: str | None = None
    entity_id: str | None = None


class StructuredExtraction(BaseModel):
    source_path: Path
    source_kind: SourceKind
    signal_type: str
    timestamp: str | None = None
    entity_id: str | None = None
    severity: str | None = None
    value: float | None = None
    text: str


class ToolExecutionResult(BaseModel):
    tool_name: str
    is_successful: bool
    evidence: list[Evidence] = Field(default_factory=list)
    extractions: list[StructuredExtraction] = Field(default_factory=list)
    summary: str
