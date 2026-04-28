from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.agent import RCAAgent
from src.intake import DataCataloger
from src.anomalies import AnomalyCandidateBuilder
from src.evidence import EvidenceBuilder
from src.models import SourceKind
from src.profiler import DataProfiler
from src.reports import ReportWriter
from src.schema import SchemaProfiler
from src.tools import InvestigationToolFactory, ToolExecutionRequest
from src.logger import AppLogger


class PipelineTest(unittest.TestCase):
    def test_cataloger_ignores_repository_and_cache_files(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".git" / "config").write_text("ignored", encoding="utf-8")
            (tmp_path / "__pycache__").mkdir()
            (tmp_path / "__pycache__" / "module.pyc").write_bytes(b"ignored")
            (tmp_path / "application.log").write_text("service started", encoding="utf-8")

            cataloger = DataCataloger(data_root=tmp_path)
            cataloger.setup()
            catalog = cataloger.build_catalog()

            self.assertEqual(len(catalog.files), 1)
            self.assertEqual(catalog.files[0].relative_path.as_posix(), "application.log")
            self.assertEqual(catalog.files[0].source_kind, SourceKind.LOG)

    def test_cataloger_does_not_treat_logger_source_code_as_logs(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            (tmp_path / "logger.py").write_text("import logging\n", encoding="utf-8")

            cataloger = DataCataloger(data_root=tmp_path)
            cataloger.setup()
            catalog = cataloger.build_catalog()

            self.assertEqual(catalog.files[0].source_kind, SourceKind.UNKNOWN)

    def test_profiler_and_tool_factory_generate_executable_specs(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            (tmp_path / "metrics").mkdir()
            (tmp_path / "metrics" / "cpu.csv").write_text("time,cpu\n1,10\n", encoding="utf-8")

            cataloger = DataCataloger(data_root=tmp_path)
            cataloger.setup()
            catalog = cataloger.build_catalog()

            profiler = DataProfiler()
            profiler.setup()
            profile = profiler.profile(catalog)

            factory = InvestigationToolFactory()
            factory.setup()
            specs = factory.generate_specs(profile)
            validations = factory.validate_specs(specs)
            executions = [
                factory.execute_spec(
                    spec=spec,
                    catalog=catalog,
                    request=ToolExecutionRequest(tool_name=spec.name, source_kind=spec.source_kind),
                )
                for spec in specs
            ]

            self.assertTrue(all(result.is_valid for result in validations))
            self.assertTrue(all(result.is_successful for result in executions))
            self.assertTrue(any(spec.source_kind == SourceKind.METRIC for spec in specs))

    def test_schema_profiler_infers_csv_field_roles(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            (tmp_path / "events.csv").write_text(
                "timestamp,service,cpu_usage,status_code\n1,api,90,500\n",
                encoding="utf-8",
            )
            cataloger = DataCataloger(data_root=tmp_path)
            cataloger.setup()
            catalog = cataloger.build_catalog()

            schema_profiler = SchemaProfiler(max_files=10, max_lines=5)
            schema_profiler.setup()
            profiles = schema_profiler.profile_catalog(catalog)

            roles = {field.name: field.inferred_role for field in profiles[0].fields}
            self.assertEqual(roles["timestamp"], "timestamp")
            self.assertEqual(roles["service"], "entity")
            self.assertEqual(roles["cpu_usage"], "metric")
            self.assertEqual(roles["status_code"], "status")
            self.assertEqual(profiles[0].timestamp_examples, ["1"])
            self.assertTrue(any(summary.name == "cpu_usage" for summary in profiles[0].numeric_summaries))

    def test_evidence_builder_creates_schema_role_evidence(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            source_path = tmp_path / "metrics.csv"
            source_path.write_text("time,host,cpu\n1,api,42\n", encoding="utf-8")
            cataloger = DataCataloger(data_root=tmp_path)
            cataloger.setup()
            catalog = cataloger.build_catalog()
            schema_profiler = SchemaProfiler(max_files=10, max_lines=5)
            schema_profiler.setup()
            profiles = schema_profiler.profile_catalog(catalog)

            builder = EvidenceBuilder()
            builder.setup()
            evidence = builder.from_schema_profiles(profiles)
            signal_types = {item.signal_type for item in evidence}

            self.assertIn("timestamp_field_detected", signal_types)
            self.assertIn("entity_field_detected", signal_types)
            self.assertIn("metric_field_detected", signal_types)
            self.assertIn("timestamp_examples_detected", signal_types)
            self.assertIn("numeric_field_summary", signal_types)

    def test_report_writer_creates_json_and_markdown(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            json_path = tmp_path / "report.json"
            markdown_path = tmp_path / "report.md"
            writer = ReportWriter(output_path=json_path, markdown_output_path=markdown_path)
            writer.setup()

            from src.models import RCAReport

            report = RCAReport(
                executive_summary="Test summary.",
                impacted_sli="latency",
                suspected_root_cause=None,
                confidence=0.0,
            )
            writer.write_json(report)
            writer.write_markdown(report)

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("Test summary.", markdown_path.read_text(encoding="utf-8"))

    def test_anomaly_candidate_builder_ranks_numeric_spread(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            (tmp_path / "metrics.csv").write_text("time,cpu\n1,10\n2,90\n", encoding="utf-8")
            cataloger = DataCataloger(data_root=tmp_path)
            cataloger.setup()
            catalog = cataloger.build_catalog()
            schema_profiler = SchemaProfiler(max_files=10, max_lines=5)
            schema_profiler.setup()
            profiles = schema_profiler.profile_catalog(catalog)

            builder = AnomalyCandidateBuilder()
            builder.setup()
            candidates = builder.from_schema_profiles(profiles)

            self.assertTrue(candidates)
            self.assertEqual(candidates[0].signal_name, "cpu")

    def test_rca_agent_runs_full_deterministic_workflow(self) -> None:
        with TemporaryDirectory() as raw_path:
            tmp_path = Path(raw_path)
            data_root = tmp_path / "data"
            data_root.mkdir()
            (data_root / "metrics.csv").write_text(
                "timestamp,service,cpu\n1,api,10\n2,api,90\n",
                encoding="utf-8",
            )
            logger = AppLogger(level="CRITICAL")
            logger.setup()
            agent = RCAAgent(
                data_root=data_root,
                output_path=tmp_path / "report.json",
                markdown_output_path=tmp_path / "report.md",
                impacted_sli="latency",
                anomaly_start="2",
                customer_context="unit test",
                max_schema_files=10,
                max_schema_lines=5,
                llm_provider="none",
                llm_model="openai:gpt-4.1-mini",
                openai_api_key="",
                logger=logger,
            )
            agent.setup()
            report = agent.run()

            self.assertEqual(report.impacted_sli, "latency")
            self.assertTrue(report.evidence)
            self.assertTrue(report.anomaly_candidates)
            self.assertTrue((tmp_path / "report.json").exists())
            self.assertTrue((tmp_path / "report.md").exists())


if __name__ == "__main__":
    unittest.main()
