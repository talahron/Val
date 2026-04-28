from pathlib import Path

from src.models import Evidence, EvidenceRelation, FieldProfile, SourceSchemaProfile


class EvidenceBuilder:
    def __init__(self) -> None:
        self._is_ready = False

    def setup(self) -> None:
        self._is_ready = True

    def from_schema_profiles(self, schema_profiles: list[SourceSchemaProfile]) -> list[Evidence]:
        if not self._is_ready:
            raise ValueError("EvidenceBuilder.setup() must be called before from_schema_profiles().")

        evidence: list[Evidence] = []
        for profile in schema_profiles:
            evidence.extend(self._build_profile_evidence(profile))
        return evidence

    def _build_profile_evidence(self, profile: SourceSchemaProfile) -> list[Evidence]:
        role_counts = self._count_roles(profile.fields)
        evidence = [
            Evidence(
                evidence_id=f"schema:{self._safe_id(profile.source_path)}:readable",
                source_path=profile.source_path,
                signal_type="schema_profile",
                summary=(
                    f"Sampled {profile.sample_line_count} non-empty lines from "
                    f"{profile.source_path.as_posix()}."
                ),
                relation=EvidenceRelation.NEUTRAL,
                confidence=0.7 if profile.is_text_readable else 0.2,
            )
        ]
        if profile.inferred_source_kind.value != "unknown":
            evidence.append(
                Evidence(
                    evidence_id=f"schema:{self._safe_id(profile.source_path)}:source_kind",
                    source_path=profile.source_path,
                    signal_type="source_kind_inferred",
                    summary=(
                        f"Inferred {profile.inferred_source_kind.value} source kind "
                        f"from fields in {profile.source_path.as_posix()}."
                    ),
                    relation=EvidenceRelation.NEUTRAL,
                    confidence=0.7,
                )
            )

        for role, count in role_counts.items():
            evidence.append(
                Evidence(
                    evidence_id=f"schema:{self._safe_id(profile.source_path)}:{role}",
                    source_path=profile.source_path,
                    signal_type=f"{role}_field_detected",
                    summary=self._role_summary(profile, role, count),
                    relation=EvidenceRelation.NEUTRAL,
                    confidence=0.75,
                )
            )
        evidence.extend(self._build_timestamp_evidence(profile))
        evidence.extend(self._build_numeric_summary_evidence(profile))
        evidence.extend(self._build_text_summary_evidence(profile))
        return evidence

    def _count_roles(self, fields: list[FieldProfile]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for field in fields:
            if field.inferred_role == "unknown":
                continue
            counts[field.inferred_role] = counts.get(field.inferred_role, 0) + 1
        return counts

    def _role_summary(self, profile: SourceSchemaProfile, role: str, count: int) -> str:
        matching_fields = [field.name for field in profile.fields if field.inferred_role == role]
        field_list = ", ".join(matching_fields)
        return (
            f"Detected {count} {role} field(s) in {profile.source_path.as_posix()}: "
            f"{field_list}."
        )

    def _safe_id(self, path: Path) -> str:
        return path.as_posix().replace("/", "_").replace("\\", "_").replace(":", "")

    def _build_timestamp_evidence(self, profile: SourceSchemaProfile) -> list[Evidence]:
        if not profile.timestamp_examples:
            return []
        examples = ", ".join(profile.timestamp_examples)
        return [
            Evidence(
                evidence_id=f"schema:{self._safe_id(profile.source_path)}:timestamp_examples",
                source_path=profile.source_path,
                signal_type="timestamp_examples_detected",
                summary=f"Detected timestamp examples in {profile.source_path.as_posix()}: {examples}.",
                relation=EvidenceRelation.NEUTRAL,
                confidence=0.8,
            )
        ]

    def _build_numeric_summary_evidence(self, profile: SourceSchemaProfile) -> list[Evidence]:
        return [
            Evidence(
                evidence_id=f"schema:{self._safe_id(profile.source_path)}:numeric:{summary.name}",
                source_path=profile.source_path,
                signal_type="numeric_field_summary",
                summary=(
                    f"Numeric sample for {summary.name}: count={summary.count}, "
                    f"min={summary.minimum}, max={summary.maximum}, avg={summary.average:.3f}."
                ),
                relation=EvidenceRelation.NEUTRAL,
                confidence=0.75,
            )
            for summary in profile.numeric_summaries
        ]

    def _build_text_summary_evidence(self, profile: SourceSchemaProfile) -> list[Evidence]:
        if not profile.text_summary:
            return []
        summary = profile.text_summary
        if not (summary.error_count or summary.warning_count or summary.info_count):
            return []
        return [
            Evidence(
                evidence_id=f"schema:{self._safe_id(profile.source_path)}:text_summary",
                source_path=profile.source_path,
                signal_type="text_signal_summary",
                summary=(
                    f"Text sample contains errors={summary.error_count}, "
                    f"warnings={summary.warning_count}, info/debug={summary.info_count}."
                ),
                relation=EvidenceRelation.NEUTRAL,
                confidence=0.65,
            )
        ]
