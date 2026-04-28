from pathlib import Path

from src.models import Entity, SourceSchemaProfile


class EntityExtractor:
    def __init__(self) -> None:
        self._is_ready = False

    def setup(self) -> None:
        self._is_ready = True

    def from_schema_profiles(self, schema_profiles: list[SourceSchemaProfile]) -> list[Entity]:
        if not self._is_ready:
            raise ValueError("EntityExtractor.setup() must be called before from_schema_profiles().")

        entities: list[Entity] = []
        for profile in schema_profiles:
            for entity_id in self._entity_ids_from_profile(profile):
                entities = self._upsert_entity(entities, entity_id, profile)
        return sorted(entities, key=lambda entity: entity.entity_id)

    def _entity_ids_from_profile(self, profile: SourceSchemaProfile) -> list[str]:
        seen: set[str] = set()
        entity_ids: list[str] = []
        for summary in profile.numeric_summaries:
            for observation in summary.observations:
                if not observation.entity_id or observation.entity_id in seen:
                    continue
                seen.add(observation.entity_id)
                entity_ids.append(observation.entity_id)
        return entity_ids

    def _upsert_entity(
        self,
        entities: list[Entity],
        entity_id: str,
        profile: SourceSchemaProfile,
    ) -> list[Entity]:
        existing = next((entity for entity in entities if entity.entity_id == entity_id), None)
        metric_names = self._metric_names(profile)
        if existing:
            for metric_name in metric_names:
                if metric_name not in existing.observed_metric_names:
                    existing.observed_metric_names.append(metric_name)
            if profile.source_path not in existing.related_source_paths:
                existing.related_source_paths.append(profile.source_path)
            return entities

        entities.append(
            Entity(
                entity_id=entity_id,
                entity_type="unknown",
                display_name=entity_id,
                observed_metric_names=metric_names,
                related_source_paths=[profile.source_path],
            )
        )
        return entities

    def _metric_names(self, profile: SourceSchemaProfile) -> list[str]:
        metric_names: list[str] = []
        for summary in profile.numeric_summaries:
            if summary.name not in metric_names:
                metric_names.append(summary.name)
        return metric_names
