from __future__ import annotations

from collections import defaultdict

from hera_mdt.schema import (
    AgentOpinion,
    Axis,
    AxisProposal,
    DeliberationAct,
    DeliberationRound,
    EpistemicAct,
    Treatment,
)


def combine_axis(axis: Axis, opinions: tuple[AgentOpinion, ...]) -> AxisProposal:
    selected = tuple(opinion for opinion in opinions if opinion.axis == axis)
    if not selected:
        raise ValueError(f"no opinions for axis {axis}")
    weights: dict[Treatment, float] = defaultdict(float)
    for opinion in selected:
        weights[opinion.treatment] += opinion.confidence
    treatment = max(weights, key=lambda item: (weights[item], item.value))
    supporting = tuple(opinion for opinion in selected if opinion.treatment == treatment)
    confidence = sum(opinion.confidence for opinion in supporting) / len(supporting)
    evidence = tuple(item for opinion in supporting for item in opinion.evidence)
    return AxisProposal(axis, treatment, confidence, selected, evidence)


def challenge(source: AxisProposal, target: AxisProposal) -> DeliberationAct:
    evidence = tuple(sorted(source.evidence, key=lambda item: item.relevance, reverse=True)[:4])
    return DeliberationAct(
        EpistemicAct.CHALLENGE,
        source.axis.value,
        source.treatment,
        source.confidence,
        evidence,
        (target.axis.value,),
    )


def bridge_score(opinion: AgentOpinion, tumor: AxisProposal, hepatic: AxisProposal) -> float:
    agreement = 0.0
    if opinion.treatment == tumor.treatment:
        agreement += tumor.confidence
    if opinion.treatment == hepatic.treatment:
        agreement += hepatic.confidence
    compromise_bonus = (
        0.25 if opinion.treatment not in {tumor.treatment, hepatic.treatment} else 0.0
    )
    return opinion.confidence + agreement * 0.35 + compromise_bonus


class EpistemicArbitrator:
    def __init__(self, maximum_rounds: int = 3) -> None:
        if maximum_rounds != 3:
            raise ValueError("the protocol requires three maximum rounds")
        self.maximum_rounds = maximum_rounds

    def deliberate(
        self, tumor: AxisProposal, hepatic: AxisProposal, bridges: tuple[AgentOpinion, ...]
    ) -> tuple[Treatment, float, tuple[DeliberationRound, ...], AxisProposal | None]:
        if tumor.treatment == hepatic.treatment:
            confidence = (tumor.confidence + hepatic.confidence) / 2.0
            return tumor.treatment, confidence, (), None
        viable: set[Treatment] = {tumor.treatment, hepatic.treatment}
        viable.update(opinion.treatment for opinion in bridges)
        rounds: list[DeliberationRound] = []
        chosen = tumor.treatment if tumor.confidence >= hepatic.confidence else hepatic.treatment
        chosen_confidence = max(tumor.confidence, hepatic.confidence)
        converged = False
        for number in range(1, self.maximum_rounds + 1):
            previous = set(viable)
            acts: list[DeliberationAct] = [
                DeliberationAct(
                    EpistemicAct.PROPOSE,
                    tumor.axis.value,
                    tumor.treatment,
                    tumor.confidence,
                    tumor.evidence,
                ),
                DeliberationAct(
                    EpistemicAct.PROPOSE,
                    hepatic.axis.value,
                    hepatic.treatment,
                    hepatic.confidence,
                    hepatic.evidence,
                ),
                challenge(tumor, hepatic),
                challenge(hepatic, tumor),
            ]
            ranked = sorted(
                bridges, key=lambda opinion: bridge_score(opinion, tumor, hepatic), reverse=True
            )
            for opinion in ranked:
                acts.append(
                    DeliberationAct(
                        EpistemicAct.BRIDGE,
                        opinion.agent,
                        opinion.treatment,
                        opinion.confidence,
                        opinion.evidence,
                        (tumor.axis.value, hepatic.axis.value),
                    )
                )
            totals: dict[Treatment, float] = defaultdict(float)
            totals[tumor.treatment] += tumor.confidence
            totals[hepatic.treatment] += hepatic.confidence
            for opinion in bridges:
                totals[opinion.treatment] += opinion.confidence * 0.85
            threshold = max(totals.values()) * (0.55 + number * 0.08)
            viable = {option for option in viable if totals.get(option, 0.0) >= threshold}
            if not viable:
                viable = {max(totals, key=lambda option: totals[option])}
            if not viable.issubset(previous):
                raise RuntimeError("viable treatment set expanded")
            chosen = max(viable, key=lambda option: (totals[option], option.value))
            denominator = sum(totals.values())
            chosen_confidence = totals[chosen] / denominator if denominator else 0.0
            acts.append(
                DeliberationAct(
                    EpistemicAct.SYNTHESIZE,
                    "coordinator",
                    chosen,
                    chosen_confidence,
                    tuple(item for act in acts for item in act.rationale)[:12],
                )
            )
            converged = len(viable) == 1
            rounds.append(
                DeliberationRound(
                    number,
                    tuple(acts),
                    tuple(sorted(viable, key=lambda item: item.value)),
                    converged,
                )
            )
            if converged:
                break
        minority = None
        if not converged:
            minority = hepatic if chosen == tumor.treatment else tumor
        return chosen, chosen_confidence, tuple(rounds), minority


def reopen_conditions(treatment: Treatment, profile_values: dict[str, object]) -> tuple[str, ...]:
    conditions: list[str] = []
    if profile_values.get("child_pugh_score") is None:
        conditions.append("reopen when direct Child-Pugh assessment becomes available")
    if profile_values.get("vascular_invasion") is None:
        conditions.append("reopen after portal venous phase imaging review")
    if treatment == Treatment.TRANSPLANT:
        conditions.append("reopen if transplant eligibility or donor access changes")
    if treatment == Treatment.SYSTEMIC:
        conditions.append("reopen after hepatic reserve or performance status changes")
    if treatment == Treatment.LOCOREGIONAL:
        conditions.append("reopen if arterial anatomy or portal vein patency changes")
    if not conditions:
        conditions.append("reopen at interval restaging or clinically material change")
    return tuple(conditions)
