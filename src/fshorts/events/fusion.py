from __future__ import annotations

from fshorts.events.candidate import Candidate


class CandidateMerger:
    """Collapses nearby candidates from all sources and keeps the strongest ones."""

    def __init__(self, merge_seconds: float, max_candidates: int) -> None:
        self._merge_seconds = merge_seconds
        self._max_candidates = max_candidates

    def merge(self, candidates: list[Candidate]) -> list[Candidate]:
        clusters: list[list[Candidate]] = []
        for candidate in sorted(candidates, key=lambda c: c.time):
            # Measured from the cluster's first member: chaining lets one cluster drift far past the event
            if clusters and candidate.time - clusters[-1][0].time <= self._merge_seconds:
                clusters[-1].append(candidate)
            else:
                clusters.append([candidate])

        merged = [self._combine(cluster) for cluster in clusters]
        strongest = sorted(merged, key=lambda c: c.score, reverse=True)[: self._max_candidates]
        return sorted(strongest, key=lambda c: c.time)

    @staticmethod
    def _combine(cluster: list[Candidate]) -> Candidate:
        # Agreement between independent sources is the strongest evidence, so it gets a bonus
        sources = tuple(dict.fromkeys(s for c in cluster for s in c.sources))
        score = sum(c.score for c in cluster) * len(sources)
        return Candidate(
            time=min(c.time for c in cluster),
            score=round(score, 3),
            sources=sources,
            details=tuple(dict.fromkeys(d for c in cluster for d in c.details)),
        )
