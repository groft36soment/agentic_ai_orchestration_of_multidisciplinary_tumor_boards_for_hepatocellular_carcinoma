from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Treatment(StrEnum):
    CURATIVE = "curative_resection_or_ablation"
    TRANSPLANT = "transplantation"
    LOCOREGIONAL = "locoregional_therapy"
    SYSTEMIC = "systemic_therapy"
    SUPPORTIVE = "best_supportive_care"


class Axis(StrEnum):
    TUMOR = "tumor_staging"
    HEPATIC = "hepatic_reserve"
    BRIDGE = "bridge"


class EpistemicAct(StrEnum):
    PROPOSE = "PROPOSE"
    CHALLENGE = "CHALLENGE"
    BRIDGE = "BRIDGE"
    SYNTHESIZE = "SYNTHESIZE"


class BCLCStage(StrEnum):
    ZERO_A = "0/A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(frozen=True)
class PatientProfile:
    patient_id: str
    age: int
    sex: str
    tumor_size_cm: float | None
    tumor_count: int | None
    vascular_invasion: str | None
    extrahepatic_spread: bool | None
    performance_status: int | None
    child_pugh_score: int | None
    meld_score: float | None
    albumin_g_dl: float | None
    bilirubin_mg_dl: float | None
    inr: float | None
    platelets_10e9_l: float | None
    ascites: str | None
    encephalopathy: str | None
    portal_hypertension: bool | None
    afp_ng_ml: float | None
    fibrosis_stage: str | None
    etiology: str | None
    first_course_treatment: Treatment | None = None
    registry: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    variable: str
    value: str
    clause: str
    relevance: float


@dataclass(frozen=True)
class AgentOpinion:
    agent: str
    axis: Axis
    treatment: Treatment
    confidence: float
    evidence: tuple[Evidence, ...]
    cross_axis_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AxisProposal:
    axis: Axis
    treatment: Treatment
    confidence: float
    opinions: tuple[AgentOpinion, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class DeliberationAct:
    act: EpistemicAct
    actor: str
    treatment: Treatment
    confidence: float
    rationale: tuple[Evidence, ...]
    addressed: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeliberationRound:
    number: int
    acts: tuple[DeliberationAct, ...]
    viable_options: tuple[Treatment, ...]
    converged: bool


@dataclass(frozen=True)
class ConfidenceDecomposition:
    tumor_axis: float
    hepatic_axis: float
    integrated: float


@dataclass(frozen=True)
class DecisionPacket:
    patient_id: str
    treatment: Treatment
    confidence: ConfidenceDecomposition
    bclc_stage: BCLCStage
    cuse_dimensions: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    rounds: tuple[DeliberationRound, ...]
    minority_report: AxisProposal | None
    reopen_conditions: tuple[str, ...]
    elapsed_seconds: float
