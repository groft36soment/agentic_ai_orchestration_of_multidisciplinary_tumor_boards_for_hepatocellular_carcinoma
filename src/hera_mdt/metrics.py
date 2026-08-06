from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score

from hera_mdt.schema import Treatment


@dataclass(frozen=True)
class ConcordanceResult:
    concordance: float
    kappa: float
    count: int
    matched: int


def treatment_concordance(
    predicted: Sequence[Treatment], observed: Sequence[Treatment]
) -> ConcordanceResult:
    if len(predicted) != len(observed):
        raise ValueError("prediction and observation lengths differ")
    if not predicted:
        raise ValueError("at least one pair is required")
    matched = sum(left == right for left, right in zip(predicted, observed, strict=True))
    kappa = float(
        cohen_kappa_score([item.value for item in observed], [item.value for item in predicted])
    )
    return ConcordanceResult(matched / len(predicted), kappa, len(predicted), matched)


def bootstrap_concordance(
    predicted: Sequence[Treatment],
    observed: Sequence[Treatment],
    iterations: int = 1000,
    seed: int = 2026,
) -> tuple[float, float]:
    if len(predicted) != len(observed) or not predicted:
        raise ValueError("paired non-empty inputs are required")
    random = np.random.default_rng(seed)
    agreements = np.asarray(
        [left == right for left, right in zip(predicted, observed, strict=True)], dtype=np.float64
    )
    estimates = np.empty(iterations, dtype=np.float64)
    for index in range(iterations):
        sample = random.integers(0, len(agreements), size=len(agreements))
        estimates[index] = float(agreements[sample].mean())
    lower, upper = np.percentile(estimates, [2.5, 97.5])
    return float(lower), float(upper)


def mcnemar_exact(reference_correct: Sequence[bool], comparator_correct: Sequence[bool]) -> float:
    if len(reference_correct) != len(comparator_correct):
        raise ValueError("paired correctness lengths differ")
    reference_only = sum(
        left and not right
        for left, right in zip(reference_correct, comparator_correct, strict=True)
    )
    comparator_only = sum(
        right and not left
        for left, right in zip(reference_correct, comparator_correct, strict=True)
    )
    discordant = reference_only + comparator_only
    if discordant == 0:
        return 1.0
    return float(
        binomtest(
            min(reference_only, comparator_only), discordant, 0.5, alternative="two-sided"
        ).pvalue
    )


def expected_calibration_error(
    confidence: Sequence[float], correct: Sequence[bool], bins: int = 5
) -> float:
    if len(confidence) != len(correct) or not confidence:
        raise ValueError("paired non-empty inputs are required")
    values = np.asarray(confidence, dtype=np.float64)
    outcomes = np.asarray(correct, dtype=np.float64)
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    error = 0.0
    for index in range(bins):
        inclusive = index == bins - 1
        mask = (values >= boundaries[index]) & (
            values <= boundaries[index + 1] if inclusive else values < boundaries[index + 1]
        )
        if mask.any():
            error += float(mask.mean()) * abs(
                float(values[mask].mean()) - float(outcomes[mask].mean())
            )
    return error


def bonferroni(p_values: Sequence[float]) -> tuple[float, ...]:
    count = len(p_values)
    return tuple(min(1.0, value * count) for value in p_values)
