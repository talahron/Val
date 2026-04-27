from src.models import (
    CatalogProfile,
    InvestigationToolSpec,
    SourceKind,
    ToolInputField,
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
