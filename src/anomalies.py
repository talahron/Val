from pathlib import Path

from src.models import AnomalyCandidate, SourceSchemaProfile


class AnomalyCandidateBuilder:
    def __init__(self) -> None:
        self._is_ready = False

    def setup(self) -> None:
        self._is_ready = True

    def from_schema_profiles(self, schema_profiles: list[SourceSchemaProfile]) -> list[AnomalyCandidate]:
        if not self._is_ready:
            raise ValueError("AnomalyCandidateBuilder.setup() must be called first.")

        candidates: list[AnomalyCandidate] = []
        for profile in schema_profiles:
            candidates.extend(self._from_profile(profile))
        return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)

    def _from_profile(self, profile: SourceSchemaProfile) -> list[AnomalyCandidate]:
        candidates: list[AnomalyCandidate] = []
        for summary in profile.numeric_summaries:
            spread = summary.maximum - summary.minimum
            if spread <= 0:
                continue
            score = spread / max(abs(summary.average), 1.0)
            candidates.append(
                AnomalyCandidate(
                    candidate_id=f"numeric_spread:{self._safe_id(profile.source_path)}:{summary.name}",
                    source_path=profile.source_path,
                    signal_name=summary.name,
                    score=score,
                    summary=(
                        f"Numeric signal {summary.name} has sample spread {spread:.3f} "
                        f"around average {summary.average:.3f}."
                    ),
                )
            )
        return candidates

    def _safe_id(self, path: Path) -> str:
        return path.as_posix().replace("/", "_").replace("\\", "_").replace(":", "")
