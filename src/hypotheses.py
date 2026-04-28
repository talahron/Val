from src.models import AnomalyCandidate, Evidence, EvidenceRelation, InvestigationRequest, RCAHypothesis


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
        evidence: list[Evidence],
    ) -> list[RCAHypothesis]:
        if not self._is_ready:
            raise ValueError("HypothesisBuilder.setup() must be called first.")

        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: self._candidate_rank_score(candidate, evidence),
            reverse=True,
        )
        return [
            self._candidate_to_hypothesis(request, candidate, evidence)
            for candidate in ranked_candidates[: self.max_hypotheses]
        ]

    def _candidate_to_hypothesis(
        self,
        request: InvestigationRequest,
        candidate: AnomalyCandidate,
        evidence: list[Evidence],
    ) -> RCAHypothesis:
        sli_context = request.impacted_sli or "the impacted SLI"
        supporting_evidence = self._supporting_evidence_for_candidate(request, candidate, evidence)
        confidence = self._confidence_for_candidate(candidate, supporting_evidence)
        evidence_context = self._evidence_context_summary(candidate, supporting_evidence)
        return RCAHypothesis(
            hypothesis_id=f"hypothesis:{candidate.candidate_id}",
            title=f"Investigate {candidate.signal_name} as a driver of {sli_context}",
            affected_signal=candidate.signal_name,
            supporting_candidate_ids=[candidate.candidate_id],
            supporting_evidence_ids=[item.evidence_id for item in supporting_evidence],
            confidence=confidence,
            summary=(
                f"{candidate.summary} {evidence_context} This signal should be checked against "
                f"{sli_context} and the anomaly time window."
            ),
        )

    def _candidate_rank_score(
        self,
        candidate: AnomalyCandidate,
        evidence: list[Evidence],
    ) -> float:
        return candidate.score + self._candidate_context_boost(candidate, evidence)

    def _confidence_for_candidate(
        self,
        candidate: AnomalyCandidate,
        supporting_evidence: list[Evidence],
    ) -> float:
        confidence = 0.25 + (candidate.score / 4.0)
        if candidate.time_aligned:
            confidence += 0.1
        if candidate.entity_id:
            confidence += 0.05
        confidence += min(0.15, len(supporting_evidence) * 0.03)
        return min(0.95, confidence)

    def _candidate_context_boost(
        self,
        candidate: AnomalyCandidate,
        evidence: list[Evidence],
    ) -> float:
        boost = 0.0
        if candidate.time_aligned:
            boost += 0.4
        if candidate.entity_id:
            boost += 0.2
        boost += min(0.5, len(self._supporting_evidence_for_candidate(None, candidate, evidence)) * 0.1)
        return boost

    def _supporting_evidence_for_candidate(
        self,
        request: InvestigationRequest | None,
        candidate: AnomalyCandidate,
        evidence: list[Evidence],
    ) -> list[Evidence]:
        return [
            item
            for item in evidence
            if item.relation == EvidenceRelation.SUPPORTS
            and self._evidence_matches_candidate(request, candidate, item)
        ]

    def _evidence_matches_candidate(
        self,
        request: InvestigationRequest | None,
        candidate: AnomalyCandidate,
        evidence: Evidence,
    ) -> bool:
        if evidence.source_path == candidate.source_path:
            return True
        if candidate.entity_id and evidence.entity_id == candidate.entity_id:
            return True
        if evidence.signal_type == "message_burst_summary":
            return self._burst_matches_time(request, candidate, evidence)
        return False

    def _burst_matches_time(
        self,
        request: InvestigationRequest | None,
        candidate: AnomalyCandidate,
        evidence: Evidence,
    ) -> bool:
        timestamp = candidate.timestamp or (request.anomaly_start if request else None)
        if not timestamp:
            return True
        return self._minute_prefix(timestamp) in evidence.summary

    def _minute_prefix(self, timestamp: str) -> str:
        return timestamp.strip().replace(" ", "T")[:16]

    def _evidence_context_summary(
        self,
        candidate: AnomalyCandidate,
        supporting_evidence: list[Evidence],
    ) -> str:
        details: list[str] = []
        if candidate.time_aligned:
            details.append("It is aligned with the supplied anomaly window")
        if candidate.entity_id:
            details.append(f"it is tied to entity `{candidate.entity_id}`")
        if supporting_evidence:
            details.append(f"{len(supporting_evidence)} supporting evidence records were found")
        if not details:
            return "No additional supporting context has been linked yet."
        return "; ".join(details) + "."
