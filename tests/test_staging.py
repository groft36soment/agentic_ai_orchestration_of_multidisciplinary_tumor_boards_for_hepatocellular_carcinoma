from hera_mdt.schema import BCLCStage, PatientProfile
from hera_mdt.staging import (
    albi_grade,
    albi_score,
    bclc_stage,
    child_pugh_class,
    hepatic_reserve_index,
    within_milan,
)


def test_scores(profile: PatientProfile) -> None:
    assert child_pugh_class(profile.child_pugh_score) == "A"
    assert albi_grade(albi_score(profile.albumin_g_dl, profile.bilirubin_mg_dl)) == 1
    assert 0.0 <= hepatic_reserve_index(profile) <= 1.0


def test_stage(profile: PatientProfile) -> None:
    assert bclc_stage(profile) == BCLCStage.B
    assert not within_milan(profile)


def test_terminal_stage(profile: PatientProfile) -> None:
    values = dict(profile.__dict__)
    values["performance_status"] = 4
    assert bclc_stage(PatientProfile(**values)) == BCLCStage.D
