from pathlib import Path
from typing import Any

from src.intake import DataCataloger
from src.logger import AppLogger
from src.models import AgentResponse, InvestigationRequest, RCAReport
from src.profiler import DataProfiler
from src.tools import InvestigationToolFactory


class RCAAgent:
    def __init__(
        self,
        data_root: Path,
        llm_provider: str,
        llm_model: str,
        openai_api_key: str,
        logger: AppLogger,
    ) -> None:
        self.data_root = data_root
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.openai_api_key = openai_api_key
        self.logger = logger
        self.cataloger = DataCataloger(data_root=data_root)
        self.profiler = DataProfiler()
        self.tool_factory = InvestigationToolFactory()
        self._pydantic_agent: Any | None = None

    def setup(self) -> None:
        self.cataloger.setup()
        self.profiler.setup()
        self.tool_factory.setup()
        self._setup_llm_agent()

    def run(self) -> RCAReport:
        request = InvestigationRequest(data_root=self.data_root)
        catalog = self.cataloger.build_catalog()
        profile = self.profiler.profile(catalog)
        tool_specs = self.tool_factory.generate_specs(profile)
        validation_results = self.tool_factory.validate_specs(tool_specs)
        valid_tool_count = sum(result.is_valid for result in validation_results)
        report = RCAReport(
            executive_summary=(
                "Initial RCA workspace profile completed. "
                f"Found {profile.total_files} files across "
                f"{len(profile.source_kinds)} detected source categories. "
                f"Generated {valid_tool_count}/{len(tool_specs)} valid investigation tool specs."
            ),
            impacted_sli=request.impacted_sli,
            suspected_root_cause=None,
            generated_tools=tool_specs,
            tool_validations=validation_results,
            confidence=0.0,
            data_gaps=[
                "No impacted SLI was provided.",
                "No anomaly time window was provided.",
                "No executable investigation tools have been generated yet.",
            ],
        )
        self.logger.info(report.model_dump_json(indent=2))
        return report

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
