from pathlib import Path

import pytest

from hera_mdt.data import (
    DataValidationError,
    file_sha256,
    parse_optional_bool,
    parse_treatment,
    profile_from_mapping,
)
from hera_mdt.schema import Treatment


def test_parsers() -> None:
    assert parse_optional_bool("present") is True
    assert parse_optional_bool("no") is False
    assert parse_treatment("TACE") == Treatment.LOCOREGIONAL
    with pytest.raises(DataValidationError):
        parse_optional_bool("maybe")


def test_profile_validation() -> None:
    with pytest.raises(DataValidationError):
        profile_from_mapping({"patient_id": "", "age": "50"})


def test_digest(tmp_path: Path) -> None:
    path = tmp_path / "record"
    path.write_bytes(b"HERA")
    assert len(file_sha256(path)) == 64
