from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from hera_mdt.metrics import (
    ConcordanceResult,
    bootstrap_concordance,
    expected_calibration_error,
    treatment_concordance,
)
from hera_mdt.schema import BCLCStage, DecisionPacket, PatientProfile, Treatment


@dataclass(frozen=True)
class EvaluationRow:
    patient_id: str
    registry: str
    stage: BCLCStage
    predicted: Treatment
    observed: Treatment
    confidence: float
    elapsed_seconds: float
    eap_rounds: int


@dataclass(frozen=True)
class EvaluationSummary:
    overall: ConcordanceResult
    confidence_interval: tuple[float, float]
    calibration_error: float
    by_stage: dict[BCLCStage, ConcordanceResult]
    by_registry: dict[str, ConcordanceResult]
    median_seconds: float
    eap_activation: float


def evaluate_profiles(
    profiles: Sequence[PatientProfile], decide: Callable[[PatientProfile], DecisionPacket]
) -> tuple[tuple[EvaluationRow, ...], EvaluationSummary]:
    rows: list[EvaluationRow] = []
    for profile in profiles:
        if profile.first_course_treatment is None:
            continue
        packet = decide(profile)
        rows.append(
            EvaluationRow(
                profile.patient_id,
                profile.registry or "unknown",
                packet.bclc_stage,
                packet.treatment,
                profile.first_course_treatment,
                packet.confidence.integrated,
                packet.elapsed_seconds,
                len(packet.rounds),
            )
        )
    if not rows:
        raise ValueError("no profiles have observed treatment")
    predicted = tuple(row.predicted for row in rows)
    observed = tuple(row.observed for row in rows)
    overall = treatment_concordance(predicted, observed)
    confidence_interval = bootstrap_concordance(predicted, observed)
    calibration = expected_calibration_error(
        tuple(row.confidence for row in rows), tuple(row.predicted == row.observed for row in rows)
    )
    by_stage = {
        stage: treatment_concordance(
            tuple(row.predicted for row in rows if row.stage == stage),
            tuple(row.observed for row in rows if row.stage == stage),
        )
        for stage in {row.stage for row in rows}
    }
    by_registry = {
        registry: treatment_concordance(
            tuple(row.predicted for row in rows if row.registry == registry),
            tuple(row.observed for row in rows if row.registry == registry),
        )
        for registry in {row.registry for row in rows}
    }
    elapsed = sorted(row.elapsed_seconds for row in rows)
    middle = len(elapsed) // 2
    median = elapsed[middle] if len(elapsed) % 2 else (elapsed[middle - 1] + elapsed[middle]) / 2.0
    activation = sum(row.eap_rounds > 0 for row in rows) / len(rows)
    return tuple(rows), EvaluationSummary(
        overall, confidence_interval, calibration, by_stage, by_registry, median, activation
    )


def _group_metric(
    rows: Sequence[EvaluationRow], key: Callable[[EvaluationRow], object]
) -> dict[object, ConcordanceResult]:
    grouped: dict[object, list[EvaluationRow]] = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    return {
        group: treatment_concordance(
            tuple(row.predicted for row in members), tuple(row.observed for row in members)
        )
        for group, members in grouped.items()
    }


def treatment_distribution(treatments: Sequence[Treatment]) -> dict[Treatment, float]:
    if not treatments:
        raise ValueError("at least one treatment is required")
    return {treatment: treatments.count(treatment) / len(treatments) for treatment in Treatment}


def disagreement_matrix(
    packets: Sequence[DecisionPacket], agent_names: Sequence[str]
) -> dict[tuple[str, str], float]:
    pairs = {
        (left, right): 0
        for index, left in enumerate(agent_names)
        for right in agent_names[index + 1 :]
    }
    totals = {(left, right): 0 for left, right in pairs}
    for packet in packets:
        if not packet.rounds:
            continue
        proposals = {
            act.actor: act.treatment
            for act in packet.rounds[0].acts
            if act.act.value == "PROPOSE" or act.act.value == "BRIDGE"
        }
        for pair in pairs:
            if pair[0] in proposals and pair[1] in proposals:
                totals[pair] += 1
                pairs[pair] += int(proposals[pair[0]] != proposals[pair[1]])
    return {pair: pairs[pair] / totals[pair] if totals[pair] else 0.0 for pair in pairs}
