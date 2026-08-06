from __future__ import annotations

import time

from hera_mdt.agents import AgentContext, SpecialistAgent, default_agents
from hera_mdt.arbitration import EpistemicArbitrator, combine_axis, reopen_conditions
from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import Axis, ConfidenceDecomposition, DecisionPacket, PatientProfile
from hera_mdt.staging import bclc_stage


class HeraOrchestrator:
    def __init__(
        self,
        knowledge: AxisKnowledgeBase,
        agents: tuple[SpecialistAgent, ...] | None = None,
        arbitrator: EpistemicArbitrator | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.agents = agents or default_agents()
        self.arbitrator = arbitrator or EpistemicArbitrator()

    def decide(self, profile: PatientProfile) -> DecisionPacket:
        started = time.perf_counter()
        context = AgentContext(profile, self.knowledge)
        opinions = tuple(agent.assess(context) for agent in self.agents)
        tumor = combine_axis(Axis.TUMOR, opinions)
        hepatic = combine_axis(Axis.HEPATIC, opinions)
        bridges = tuple(opinion for opinion in opinions if opinion.axis == Axis.BRIDGE)
        treatment, integrated, rounds, minority = self.arbitrator.deliberate(
            tumor, hepatic, bridges
        )
        evidence = tuple(
            sorted(
                tumor.evidence
                + hepatic.evidence
                + tuple(item for opinion in bridges for item in opinion.evidence),
                key=lambda item: item.relevance,
                reverse=True,
            )[:20]
        )
        dimensions = self._cuse_dimensions(profile, len(rounds), minority is not None)
        profile_values: dict[str, object] = {
            "child_pugh_score": profile.child_pugh_score,
            "vascular_invasion": profile.vascular_invasion,
        }
        return DecisionPacket(
            profile.patient_id,
            treatment,
            ConfidenceDecomposition(tumor.confidence, hepatic.confidence, integrated),
            bclc_stage(profile),
            dimensions,
            evidence,
            rounds,
            minority,
            reopen_conditions(treatment, profile_values),
            time.perf_counter() - started,
        )

    @staticmethod
    def _cuse_dimensions(profile: PatientProfile, rounds: int, minority: bool) -> tuple[str, ...]:
        dimensions: list[str] = []
        missing = sum(
            value is None
            for value in (
                profile.child_pugh_score,
                profile.meld_score,
                profile.vascular_invasion,
                profile.extrahepatic_spread,
            )
        )
        if rounds:
            dimensions.append("Complexity")
        if missing >= 2 or minority:
            dimensions.append("Uncertainty")
        if profile.metadata.get("patient_preference"):
            dimensions.append("Subjectivity")
        if profile.metadata.get("emotional_context"):
            dimensions.append("Emotion")
        return tuple(dimensions or ("Low complexity",))
