"""Training-only cross-session evidence for transition-edge direction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class CrossSessionHitEvidence:
    session_hit_rates: tuple[float, ...]
    mean_hit_rate: float
    consensus: float


def leave_one_session_out_hit_evidence(
    session_means: Sequence[float],
    positive_counts: Sequence[int],
    negative_counts: Sequence[int],
    sample_counts: Sequence[int],
) -> CrossSessionHitEvidence:
    """Score each session using a direction fitted on all other sessions."""

    lengths = {len(session_means), len(positive_counts), len(negative_counts), len(sample_counts)}
    if len(lengths) != 1:
        raise ValueError("cross-session evidence inputs must have equal lengths")
    if len(session_means) < 2:
        return CrossSessionHitEvidence((), 0.0, 0.0)

    total_mean = float(sum(session_means))
    hit_rates: list[float] = []
    other_count = len(session_means) - 1
    for index, session_mean in enumerate(session_means):
        count = int(sample_counts[index])
        if count <= 0:
            raise ValueError("cross-session evidence sample counts must be positive")
        fitted_mean = (total_mean - float(session_mean)) / other_count
        if fitted_mean > 0.0:
            hits = int(positive_counts[index])
        elif fitted_mean < 0.0:
            hits = int(negative_counts[index])
        else:
            hits = 0
        hit_rates.append(hits / count)

    mean_hit_rate = float(sum(hit_rates) / len(hit_rates))
    consensus = float(sum(rate > 0.5 for rate in hit_rates) / len(hit_rates))
    return CrossSessionHitEvidence(tuple(hit_rates), mean_hit_rate, consensus)
