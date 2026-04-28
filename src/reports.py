from pathlib import Path

from src.models import RCAReport


class ReportWriter:
    def __init__(self, output_path: Path, markdown_output_path: Path) -> None:
        self.output_path = output_path
        self.markdown_output_path = markdown_output_path

    def setup(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_output_path.parent.mkdir(parents=True, exist_ok=True)

    def write_json(self, report: RCAReport) -> Path:
        self.output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return self.output_path

    def write_markdown(self, report: RCAReport) -> Path:
        sections = [
            "# RCA Report",
            "",
            "## Executive Summary",
            report.executive_summary,
            "",
            "## Root Cause",
            f"- Impacted SLI: {report.impacted_sli or 'not provided'}",
            f"- Suspected root cause: {report.suspected_root_cause or 'not determined'}",
            f"- Confidence: {report.confidence:.2f}",
            "",
            "## Data Gaps",
            *self._bullet_list(report.data_gaps),
            "",
            "## Affected Entities",
            *self._entity_lines(report),
            "",
            "## Evidence",
            *self._evidence_lines(report),
            "",
            "## Anomaly Candidates",
            *self._anomaly_lines(report),
            "",
            "## Initial Hypotheses",
            *self._hypothesis_lines(report),
            "",
            "## Generated Tools",
            *self._tool_lines(report),
            "",
            "## Investigation Cycles",
            *self._cycle_lines(report),
            "",
        ]
        self.markdown_output_path.write_text("\n".join(sections), encoding="utf-8")
        return self.markdown_output_path

    def _bullet_list(self, items: list[str]) -> list[str]:
        return [f"- {item}" for item in items] if items else ["- None"]

    def _evidence_lines(self, report: RCAReport) -> list[str]:
        if not report.evidence:
            return ["- No evidence collected."]
        return [
            f"- `{item.signal_type}` from `{item.source_path}`: {item.summary}"
            for item in report.evidence[:50]
        ]

    def _entity_lines(self, report: RCAReport) -> list[str]:
        if not report.affected_entities:
            return ["- No entities identified yet."]
        return [
            (
                f"- `{entity.entity_id}` metrics={', '.join(entity.observed_metric_names) or 'none'} "
                f"sources={len(entity.related_source_paths)}"
            )
            for entity in report.affected_entities
        ]

    def _tool_lines(self, report: RCAReport) -> list[str]:
        if not report.generated_tools:
            return ["- No tools generated."]
        return [
            f"- `{tool.name}` ({tool.source_kind.value}): {tool.purpose}"
            for tool in report.generated_tools
        ]

    def _anomaly_lines(self, report: RCAReport) -> list[str]:
        if not report.anomaly_candidates:
            return ["- No anomaly candidates identified."]
        return [
            (
                f"- `{candidate.signal_name}` score={candidate.score:.3f}"
                f"{' time-aligned' if candidate.time_aligned else ''}: {candidate.summary}"
            )
            for candidate in report.anomaly_candidates[:20]
        ]

    def _hypothesis_lines(self, report: RCAReport) -> list[str]:
        if not report.hypotheses:
            return ["- No hypotheses generated."]
        return [
            f"- `{hypothesis.title}` confidence={hypothesis.confidence:.2f}: {hypothesis.summary}"
            for hypothesis in report.hypotheses
        ]

    def _cycle_lines(self, report: RCAReport) -> list[str]:
        if not report.investigation_cycles:
            return ["- No investigation cycles recorded."]
        return [
            (
                f"- `{cycle.cycle_id}` tools={cycle.generated_tool_count}, "
                f"valid={cycle.valid_tool_count}, evidence={cycle.evidence_count}, "
                f"hypotheses={cycle.hypothesis_count}"
            )
            for cycle in report.investigation_cycles
        ]
