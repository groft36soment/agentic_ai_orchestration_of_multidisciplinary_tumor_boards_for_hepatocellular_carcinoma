import pytest

from hera_mdt.metrics import (
    bonferroni,
    bootstrap_concordance,
    expected_calibration_error,
    mcnemar_exact,
    treatment_concordance,
)
from hera_mdt.schema import Treatment


def test_concordance() -> None:
    observed = (
        Treatment.CURATIVE,
        Treatment.SYSTEMIC,
        Treatment.SUPPORTIVE,
        Treatment.LOCOREGIONAL,
    )
    predicted = (
        Treatment.CURATIVE,
        Treatment.SYSTEMIC,
        Treatment.LOCOREGIONAL,
        Treatment.LOCOREGIONAL,
    )
    result = treatment_concordance(predicted, observed)
    assert result.concordance == 0.75
    assert result.matched == 3
    lower, upper = bootstrap_concordance(predicted, observed, 100, 7)
    assert lower <= result.concordance <= upper


def test_paired_statistics() -> None:
    assert mcnemar_exact((True, True, False), (False, True, False)) == 1.0
    assert bonferroni((0.01, 0.2)) == (0.02, 0.4)
    assert expected_calibration_error((0.8, 0.2), (True, False), 2) == pytest.approx(0.2)
