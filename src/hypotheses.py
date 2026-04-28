from src.models import AnomalyCandidate, InvestigationRequest, RCAHypothesis


class HypothesisBuilder:
    def __init__(self, max_hypotheses: int) -> None:
        self.max_hypotheses = max_hypotheses
        self._is_ready = False

    def setup(self) -> None:
        if self.max_hypotheses < 1:
            raise ValueError("max_hypotheses must be at least 1.")
        self._is_ready = True

    def from_anomaly_candidates(
        self,
        request: InvestigationRequest,
        candidates: list[AnomalyCandidate],
    ) -> list[RCAHypothesis]:
        if not self._is_ready:
            raise ValueError("HypothesisBuilder.setup() must be called first.")

        return [
            self._candidate_to_hypothesis(request, candidate)
            for candidate in candidates[: self.max_hypotheses]
        ]

    def _candidate_to_hypothesis(
        self,
        request: InvestigationRequest,
        candidate: AnomalyCandidate,
    ) -> RCAHypothesis:
        sli_context = request.impacted_sli or "the impacted SLI"
        confidence = min(0.85, 0.25 + (candidate.score / 4.0))
        return RCAHypothesis(
            hypothesis_id=f"hypothesis:{candidate.candidate_id}",
            title=f"Investigate {candidate.signal_name} as a driver of {sli_context}",
            affected_signal=candidate.signal_name,
            supporting_candidate_ids=[candidate.candidate_id],
            confidence=confidence,
            summary=(
                f"{candidate.summary} This signal should be checked against "
                f"{sli_context} and the anomaly time window."
            ),
        )
