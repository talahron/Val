from collections import defaultdict
from pathlib import Path

from src.models import DataCatalog, FileProfile, FileTypeSummary, SourceKind


class DataCataloger:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root

    def setup(self) -> None:
        if not self.data_root.exists():
            raise ValueError(f"Data root does not exist: {self.data_root}")
        if not self.data_root.is_dir():
            raise ValueError(f"Data root must be a directory: {self.data_root}")

    def build_catalog(self) -> DataCatalog:
        files = [
            self._profile_file(path)
            for path in sorted(self.data_root.rglob("*"))
            if path.is_file() and self._is_customer_data_file(path)
        ]
        return DataCatalog(
            root=self.data_root,
            files=files,
            file_type_summaries=self._summarize_file_types(files),
        )

    def _profile_file(self, path: Path) -> FileProfile:
        suffix = path.suffix.lower() or "<none>"
        return FileProfile(
            path=path,
            relative_path=path.relative_to(self.data_root),
            suffix=suffix,
            size_bytes=path.stat().st_size,
            source_kind=self._classify_source(path),
        )

    def _summarize_file_types(self, files: list[FileProfile]) -> list[FileTypeSummary]:
        counts: defaultdict[str, int] = defaultdict(int)
        sizes: defaultdict[str, int] = defaultdict(int)
        for file_profile in files:
            counts[file_profile.suffix] += 1
            sizes[file_profile.suffix] += file_profile.size_bytes
        return [
            FileTypeSummary(suffix=suffix, count=counts[suffix], total_size_bytes=sizes[suffix])
            for suffix in sorted(counts)
        ]

    def _classify_source(self, path: Path) -> SourceKind:
        normalized = path.as_posix().lower()
        path_tokens = {part.lower() for part in path.parts}
        suffix = path.suffix.lower()

        if suffix in {".zip", ".gz", ".tar", ".tgz"}:
            return SourceKind.ARCHIVE
        if suffix in {".md", ".txt", ".pptx", ".docx", ".pdf"} and "readme" in normalized:
            return SourceKind.DOCUMENTATION
        if self._has_source_token(path_tokens, {"metric", "metrics", "performance", "statistic", "statistics"}):
            return SourceKind.METRIC
        if self._has_source_token(path_tokens, {"trace", "traces", "span", "spans"}):
            return SourceKind.TRACE
        if self._has_source_token(path_tokens, {"event", "events", "audit", "audits"}):
            return SourceKind.EVENT
        if self._has_source_token(path_tokens, {"config", "configuration", "topology", "inventory"}):
            return SourceKind.CONFIGURATION
        if self._has_source_token(path_tokens, {"log", "logs", "message", "messages", "application"}):
            return SourceKind.LOG
        if suffix in {".log", ".jtl"}:
            return SourceKind.LOG
        if suffix in {".csv", ".json", ".ndjson", ".jsonl"}:
            return SourceKind.UNKNOWN
        return SourceKind.UNKNOWN

    def _is_customer_data_file(self, path: Path) -> bool:
        ignored_parts = {
            ".git",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "reports",
            "venv",
        }
        relative_parts = path.relative_to(self.data_root).parts
        return not any(part in ignored_parts or part.startswith(".") for part in relative_parts)

    def _has_source_token(self, path_tokens: set[str], candidates: set[str]) -> bool:
        return bool(path_tokens.intersection(candidates))
