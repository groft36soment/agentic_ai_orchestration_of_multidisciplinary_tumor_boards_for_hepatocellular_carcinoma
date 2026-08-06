from hera_mdt.schema import BCLCStage, PatientProfile


def child_pugh_class(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score <= 6:
        return "A"
    if score <= 9:
        return "B"
    return "C"


def albi_score(albumin_g_dl: float | None, bilirubin_mg_dl: float | None) -> float | None:
    if albumin_g_dl is None or bilirubin_mg_dl is None or bilirubin_mg_dl <= 0:
        return None
    import math

    bilirubin_umol_l = bilirubin_mg_dl * 17.1
    albumin_g_l = albumin_g_dl * 10.0
    return math.log10(bilirubin_umol_l) * 0.66 - albumin_g_l * 0.085


def albi_grade(score: float | None) -> int | None:
    if score is None:
        return None
    if score <= -2.60:
        return 1
    if score <= -1.39:
        return 2
    return 3


def within_milan(profile: PatientProfile) -> bool:
    if profile.tumor_size_cm is None or profile.tumor_count is None:
        return False
    return (
        profile.tumor_count == 1
        and profile.tumor_size_cm <= 5.0
        or profile.tumor_count <= 3
        and profile.tumor_size_cm <= 3.0
    )


def bclc_stage(profile: PatientProfile) -> BCLCStage:
    if profile.performance_status is not None and profile.performance_status >= 3:
        return BCLCStage.D
    if child_pugh_class(profile.child_pugh_score) == "C":
        return BCLCStage.D
    if profile.extrahepatic_spread or profile.vascular_invasion in {"macro", "portal", "major"}:
        return BCLCStage.C
    if profile.tumor_count is not None and profile.tumor_count > 3:
        return BCLCStage.B
    if profile.tumor_size_cm is not None and profile.tumor_size_cm > 5.0:
        return BCLCStage.B
    return BCLCStage.ZERO_A


def hepatic_reserve_index(profile: PatientProfile) -> float:
    values: list[float] = []
    if profile.child_pugh_score is not None:
        values.append(max(0.0, min(1.0, (10.0 - profile.child_pugh_score) / 5.0)))
    score = albi_score(profile.albumin_g_dl, profile.bilirubin_mg_dl)
    if score is not None:
        values.append(max(0.0, min(1.0, (-score - 1.0) / 2.5)))
    if profile.meld_score is not None:
        values.append(max(0.0, min(1.0, (30.0 - profile.meld_score) / 24.0)))
    if profile.portal_hypertension is not None:
        values.append(0.3 if profile.portal_hypertension else 0.9)
    if not values:
        age_component = max(0.1, min(0.9, (90.0 - profile.age) / 60.0))
        fibrosis_component = 0.4 if profile.fibrosis_stage else 0.65
        values.extend((age_component, fibrosis_component))
    return sum(values) / len(values)
