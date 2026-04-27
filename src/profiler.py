from src.models import CatalogProfile, DataCatalog, SourceKind


class DataProfiler:
    def __init__(self) -> None:
        self._is_ready = False

    def setup(self) -> None:
        self._is_ready = True

    def profile(self, catalog: DataCatalog) -> CatalogProfile:
        if not self._is_ready:
            raise ValueError("DataProfiler.setup() must be called before profile().")

        source_kinds = sorted({file.source_kind for file in catalog.files}, key=lambda item: item.value)
        total_size = sum(file.size_bytes for file in catalog.files)
        return CatalogProfile(
            total_files=len(catalog.files),
            total_size_bytes=total_size,
            source_kinds=source_kinds or [SourceKind.UNKNOWN],
            summaries=catalog.file_type_summaries,
        )
