from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.intake import DataCataloger
from src.models import SourceKind
from src.profiler import DataProfiler
from src.schema import SchemaProfiler
from src.tools import InvestigationToolFactory, ToolExecutionRequest


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


if __name__ == "__main__":
    unittest.main()
