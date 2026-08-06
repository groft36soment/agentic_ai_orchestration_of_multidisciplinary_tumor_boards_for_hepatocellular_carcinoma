from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import AgentOpinion, Axis, Evidence, PatientProfile, Treatment
from hera_mdt.staging import bclc_stage, hepatic_reserve_index, within_milan


@dataclass(frozen=True)
class AgentContext:
    profile: PatientProfile
    knowledge: AxisKnowledgeBase


class SpecialistAgent(ABC):
    name: str
    axis: Axis

    @abstractmethod
    def assess(self, context: AgentContext) -> AgentOpinion:
        raise NotImplementedError

    def guideline_evidence(self, context: AgentContext, query: str) -> tuple[Evidence, ...]:
        return tuple(
            Evidence("guideline", hit.chunk.identifier, hit.chunk.decision_node, hit.score)
            for hit in context.knowledge.retrieve(query, self.axis, 3)
        )


class RadiologistAgent(SpecialistAgent):
    name = "radiologist"
    axis = Axis.TUMOR

    def assess(self, context: AgentContext) -> AgentOpinion:
        profile = context.profile
        stage = bclc_stage(profile)
        if stage.value == "D":
            treatment = Treatment.SUPPORTIVE
        elif stage.value == "C":
            treatment = Treatment.SYSTEMIC
        elif stage.value == "B":
            treatment = Treatment.LOCOREGIONAL
        else:
            treatment = Treatment.CURATIVE
        known = sum(
            value is not None
            for value in (
                profile.tumor_size_cm,
                profile.tumor_count,
                profile.vascular_invasion,
                profile.extrahepatic_spread,
            )
        )
        confidence = 0.48 + known * 0.11
        evidence = (
            Evidence("bclc_stage", stage.value, "tumor burden stage", 0.95),
            Evidence("tumor_size_cm", str(profile.tumor_size_cm), "radiographic burden", 0.82),
            Evidence(
                "vascular_invasion",
                str(profile.vascular_invasion),
                "advanced-stage criterion",
                0.89,
            ),
        ) + self.guideline_evidence(
            context, f"BCLC {stage.value} tumor size vascular invasion {treatment.value}"
        )
        flags = ("portal vein patency",) if profile.vascular_invasion else ()
        return AgentOpinion(self.name, self.axis, treatment, min(confidence, 0.93), evidence, flags)


class MedicalOncologistAgent(SpecialistAgent):
    name = "medical_oncologist"
    axis = Axis.TUMOR

    def assess(self, context: AgentContext) -> AgentOpinion:
        profile = context.profile
        stage = bclc_stage(profile)
        if stage.value == "C":
            treatment = Treatment.SYSTEMIC
        elif stage.value == "B":
            treatment = Treatment.LOCOREGIONAL
        elif stage.value == "D":
            treatment = Treatment.SUPPORTIVE
        else:
            treatment = Treatment.CURATIVE
        afp_signal = profile.afp_ng_ml is not None and profile.afp_ng_ml >= 400
        confidence = 0.72 + (0.08 if afp_signal else 0.0)
        evidence = (
            Evidence("bclc_stage", stage.value, "oncologic treatment node", 0.92),
            Evidence(
                "extrahepatic_spread",
                str(profile.extrahepatic_spread),
                "systemic eligibility",
                0.88,
            ),
            Evidence("afp_ng_ml", str(profile.afp_ng_ml), "tumor biology", 0.61),
        ) + self.guideline_evidence(
            context, f"oncology BCLC {stage.value} AFP spread {treatment.value}"
        )
        flags = (
            ("hepatic tolerance for systemic therapy",) if treatment == Treatment.SYSTEMIC else ()
        )
        return AgentOpinion(self.name, self.axis, treatment, min(confidence, 0.91), evidence, flags)


class HepatologistAgent(SpecialistAgent):
    name = "hepatologist"
    axis = Axis.HEPATIC

    def assess(self, context: AgentContext) -> AgentOpinion:
        profile = context.profile
        reserve = hepatic_reserve_index(profile)
        stage = bclc_stage(profile)
        if reserve < 0.25:
            treatment = Treatment.SUPPORTIVE
        elif reserve < 0.48:
            treatment = Treatment.TRANSPLANT if within_milan(profile) else Treatment.LOCOREGIONAL
        elif stage.value == "C" and not profile.extrahepatic_spread:
            treatment = Treatment.LOCOREGIONAL
        elif stage.value == "C":
            treatment = Treatment.SYSTEMIC
        elif within_milan(profile) and profile.portal_hypertension:
            treatment = Treatment.TRANSPLANT
        else:
            treatment = Treatment.CURATIVE
        direct = sum(
            value is not None
            for value in (
                profile.child_pugh_score,
                profile.meld_score,
                profile.albumin_g_dl,
                profile.bilirubin_mg_dl,
                profile.inr,
            )
        )
        confidence = 0.45 + direct * 0.075
        evidence = (
            Evidence("hepatic_reserve_index", f"{reserve:.3f}", "functional tolerance", 0.96),
            Evidence("child_pugh_score", str(profile.child_pugh_score), "liver function", 0.91),
            Evidence("meld_score", str(profile.meld_score), "short-term hepatic risk", 0.78),
            Evidence(
                "portal_hypertension", str(profile.portal_hypertension), "resection tolerance", 0.84
            ),
        ) + self.guideline_evidence(context, f"hepatic reserve child pugh MELD {treatment.value}")
        flags = (
            ("tumor technical resectability",)
            if treatment in {Treatment.CURATIVE, Treatment.TRANSPLANT}
            else ()
        )
        return AgentOpinion(self.name, self.axis, treatment, min(confidence, 0.92), evidence, flags)


class TransplantSurgeonAgent(SpecialistAgent):
    name = "transplant_surgeon"
    axis = Axis.HEPATIC

    def assess(self, context: AgentContext) -> AgentOpinion:
        profile = context.profile
        reserve = hepatic_reserve_index(profile)
        milan = within_milan(profile)
        if milan and (profile.portal_hypertension or reserve < 0.55):
            treatment = Treatment.TRANSPLANT
        elif reserve >= 0.62 and bclc_stage(profile).value == "0/A":
            treatment = Treatment.CURATIVE
        elif reserve < 0.25:
            treatment = Treatment.SUPPORTIVE
        elif bclc_stage(profile).value in {"B", "C"}:
            treatment = Treatment.LOCOREGIONAL
        else:
            treatment = Treatment.CURATIVE
        evidence = (
            Evidence("within_milan", str(milan), "transplant selection", 0.95),
            Evidence("hepatic_reserve_index", f"{reserve:.3f}", "operative tolerance", 0.89),
            Evidence(
                "portal_hypertension", str(profile.portal_hypertension), "resection risk", 0.85
            ),
        ) + self.guideline_evidence(
            context, f"transplant Milan portal hypertension {treatment.value}"
        )
        confidence = (
            0.78 if profile.tumor_count is not None and profile.tumor_size_cm is not None else 0.58
        )
        return AgentOpinion(
            self.name, self.axis, treatment, confidence, evidence, ("vascular anatomy",)
        )


class PathologistAgent(SpecialistAgent):
    name = "pathologist"
    axis = Axis.BRIDGE

    def assess(self, context: AgentContext) -> AgentOpinion:
        profile = context.profile
        reserve = hepatic_reserve_index(profile)
        stage = bclc_stage(profile)
        aggressive = profile.afp_ng_ml is not None and profile.afp_ng_ml >= 400
        if stage.value == "C" and aggressive:
            treatment = Treatment.SYSTEMIC
        elif stage.value in {"B", "C"}:
            treatment = Treatment.LOCOREGIONAL
        elif reserve < 0.3:
            treatment = Treatment.TRANSPLANT if within_milan(profile) else Treatment.SUPPORTIVE
        else:
            treatment = Treatment.CURATIVE
        evidence = (
            Evidence(
                "fibrosis_stage", str(profile.fibrosis_stage), "background liver disease", 0.72
            ),
            Evidence("afp_ng_ml", str(profile.afp_ng_ml), "tumor phenotype", 0.68),
        ) + self.guideline_evidence(context, f"fibrosis tumor grade AFP {treatment.value}")
        return AgentOpinion(self.name, self.axis, treatment, 0.64, evidence)


class InterventionalRadiologistAgent(SpecialistAgent):
    name = "interventional_radiologist"
    axis = Axis.BRIDGE

    def assess(self, context: AgentContext) -> AgentOpinion:
        profile = context.profile
        stage = bclc_stage(profile)
        reserve = hepatic_reserve_index(profile)
        patent = profile.vascular_invasion not in {"portal", "major"}
        if stage.value in {"B", "C"} and reserve >= 0.35 and patent:
            treatment = Treatment.LOCOREGIONAL
        elif stage.value == "C":
            treatment = Treatment.SYSTEMIC
        elif stage.value == "D":
            treatment = Treatment.SUPPORTIVE
        else:
            treatment = Treatment.CURATIVE
        evidence = (
            Evidence("portal_vein_patent", str(patent), "arterial therapy feasibility", 0.91),
            Evidence(
                "hepatic_reserve_index", f"{reserve:.3f}", "post-embolization tolerance", 0.86
            ),
        ) + self.guideline_evidence(context, f"TACE TARE portal patency BCLC {stage.value}")
        return AgentOpinion(self.name, self.axis, treatment, 0.75, evidence)


def default_agents() -> tuple[SpecialistAgent, ...]:
    return (
        RadiologistAgent(),
        MedicalOncologistAgent(),
        HepatologistAgent(),
        TransplantSurgeonAgent(),
        PathologistAgent(),
        InterventionalRadiologistAgent(),
    )
