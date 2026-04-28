from pathlib import Path

from src.models import AnomalyCandidate, NumericFieldSummary, NumericObservation, SourceSchemaProfile


class AnomalyCandidateBuilder:
    def __init__(self) -> None:
        self._is_ready = False

    def setup(self) -> None:
        self._is_ready = True

    def from_schema_profiles(
        self,
        schema_profiles: list[SourceSchemaProfile],
        anomaly_start: str | None = None,
    ) -> list[AnomalyCandidate]:
        if not self._is_ready:
            raise ValueError("AnomalyCandidateBuilder.setup() must be called first.")

        candidates: list[AnomalyCandidate] = []
        for profile in schema_profiles:
            candidates.extend(self._from_profile(profile, anomaly_start))
        return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)

    def _from_profile(
        self,
        profile: SourceSchemaProfile,
        anomaly_start: str | None,
    ) -> list[AnomalyCandidate]:
        candidates: list[AnomalyCandidate] = []
        for summary in profile.numeric_summaries:
            spread = summary.maximum - summary.minimum
            if spread <= 0:
                continue
            aligned_observation = self._find_aligned_observation(summary, anomaly_start)
            score = spread / max(abs(summary.average), 1.0)
            if aligned_observation:
                score *= 1.5
            candidates.append(
                AnomalyCandidate(
                    candidate_id=f"numeric_spread:{self._safe_id(profile.source_path)}:{summary.name}",
                    source_path=profile.source_path,
                    signal_name=summary.name,
                    score=score,
                    summary=(
                        f"Numeric signal {summary.name} has sample spread {spread:.3f} "
                        f"around average {summary.average:.3f}."
                        + self._alignment_summary(aligned_observation)
                    ),
                    time_aligned=aligned_observation is not None,
                    timestamp=aligned_observation.timestamp if aligned_observation else None,
                    entity_id=aligned_observation.entity_id if aligned_observation else None,
                )
            )
        return candidates

    def _safe_id(self, path: Path) -> str:
        return path.as_posix().replace("/", "_").replace("\\", "_").replace(":", "")

    def _find_aligned_observation(
        self,
        summary: NumericFieldSummary,
        anomaly_start: str | None,
    ) -> NumericObservation | None:
        if not anomaly_start:
            return None
        normalized_anomaly = anomaly_start.strip()
        for observation in summary.observations:
            if observation.timestamp and observation.timestamp.strip() == normalized_anomaly:
                return observation
        return None

    def _alignment_summary(self, observation: NumericObservation | None) -> str:
        if not observation:
            return ""
        entity_text = f" for entity {observation.entity_id}" if observation.entity_id else ""
        return (
            f" It has an observation at anomaly time {observation.timestamp}"
            f"{entity_text} with value {observation.value:.3f}."
        )
