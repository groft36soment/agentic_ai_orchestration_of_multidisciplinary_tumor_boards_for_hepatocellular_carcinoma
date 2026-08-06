from pathlib import Path

import pytest

from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import PatientProfile, Treatment


@pytest.fixture
def profile() -> PatientProfile:
    return PatientProfile(
        "case-1",
        61,
        "male",
        6.2,
        4,
        "none",
        False,
        1,
        5,
        9.0,
        4.0,
        0.8,
        1.0,
        170.0,
        "none",
        "none",
        False,
        90.0,
        "F3",
        "HCV",
        Treatment.LOCOREGIONAL,
        "TCGA-LIHC",
    )


@pytest.fixture
def knowledge() -> AxisKnowledgeBase:
    root = Path(__file__).parents[1] / "knowledge"
    return AxisKnowledgeBase.from_directory(root)
