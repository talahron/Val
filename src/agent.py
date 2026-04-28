from pathlib import Path
from typing import Any

from src.intake import DataCataloger
from src.logger import AppLogger
from src.models import AgentResponse, InvestigationRequest, RCAReport, ToolExecutionRequest
from src.profiler import DataProfiler
from src.reports import ReportWriter
from src.schema import SchemaProfiler
from src.tools import InvestigationToolFactory


class RCAAgent:
    def __init__(
        self,
        data_root: Path,
        output_path: Path,
        impacted_sli: str | None,
        anomaly_start: str | None,
        customer_context: str | None,
        max_schema_files: int,
        max_schema_lines: int,
        llm_provider: str,
        llm_model: str,
        openai_api_key: str,
        logger: AppLogger,
    ) -> None:
        self.data_root = data_root
        self.output_path = output_path
        self.impacted_sli = impacted_sli
        self.anomaly_start = anomaly_start
        self.customer_context = customer_context
        self.max_schema_files = max_schema_files
        self.max_schema_lines = max_schema_lines
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.openai_api_key = openai_api_key
        self.logger = logger
        self.cataloger = DataCataloger(data_root=data_root)
        self.profiler = DataProfiler()
        self.schema_profiler = SchemaProfiler(max_files=max_schema_files, max_lines=max_schema_lines)
        self.tool_factory = InvestigationToolFactory()
        self.report_writer = ReportWriter(output_path=output_path)
        self._pydantic_agent: Any | None = None

    def setup(self) -> None:
        self.cataloger.setup()
        self.profiler.setup()
        self.schema_profiler.setup()
        self.tool_factory.setup()
        self.report_writer.setup()
        self._setup_llm_agent()

    def run(self) -> RCAReport:
        request = InvestigationRequest(
            data_root=self.data_root,
            impacted_sli=self.impacted_sli,
            anomaly_start=self.anomaly_start,
            customer_context=self.customer_context,
        )
        catalog = self.cataloger.build_catalog()
        profile = self.profiler.profile(catalog)
        schema_profiles = self.schema_profiler.profile_catalog(catalog)
        tool_specs = self.tool_factory.generate_specs(profile)
        validation_results = self.tool_factory.validate_specs(tool_specs)
        valid_tool_count = sum(result.is_valid for result in validation_results)
        execution_results = [
            self.tool_factory.execute_spec(
                spec=spec,
                catalog=catalog,
                request=ToolExecutionRequest(tool_name=spec.name, source_kind=spec.source_kind),
            )
            for spec in tool_specs
        ]
        evidence = [
            evidence
            for execution_result in execution_results
            for evidence in execution_result.evidence
        ]
        report = RCAReport(
            executive_summary=(
                "Initial RCA workspace profile completed. "
                f"Found {profile.total_files} files across "
                f"{len(profile.source_kinds)} detected source categories. "
                f"Generated {valid_tool_count}/{len(tool_specs)} valid investigation tool specs "
                f"and collected {len(evidence)} neutral evidence records."
            ),
            impacted_sli=request.impacted_sli,
            suspected_root_cause=None,
            evidence=evidence,
            schema_profiles=schema_profiles,
            generated_tools=tool_specs,
            tool_validations=validation_results,
            confidence=0.0,
            data_gaps=self._build_data_gaps(request),
        )
        report_path = self.report_writer.write_json(report)
        self.logger.info(report.model_dump_json(indent=2))
        self.logger.info(f"RCA report written to {report_path}")
        return report

    def _build_data_gaps(self, request: InvestigationRequest) -> list[str]:
        data_gaps: list[str] = []
        if not request.impacted_sli:
            data_gaps.append("No impacted SLI was provided.")
        if not request.anomaly_start:
            data_gaps.append("No anomaly time window was provided.")
        data_gaps.append("No causal hypothesis has been evaluated yet.")
        return data_gaps

    def _setup_llm_agent(self) -> None:
        if self.llm_provider.lower() == "none":
            self.logger.info("LLM provider disabled; running deterministic RCA scaffold.")
            return

        if not self.openai_api_key and self.llm_provider.lower() == "openai":
            raise ValueError("OPENAI_API_KEY must be set when LLM_PROVIDER=openai.")

        from pydantic_ai import Agent

        self._pydantic_agent = Agent(
            self.llm_model,
            output_type=AgentResponse,
            system_prompt=(
                "You are a root cause analysis investigation agent. "
                "Only produce conclusions supported by structured evidence."
            ),
        )
