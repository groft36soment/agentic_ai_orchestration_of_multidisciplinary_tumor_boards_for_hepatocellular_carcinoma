from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any

from hera_mdt.schema import PatientProfile, Treatment


class DataValidationError(ValueError):
    pass


def parse_optional_float(value: str | None) -> float | None:
    if value is None or value.strip() in {"", "NA", "N/A", "Unknown", "unknown"}:
        return None
    return float(value)


def parse_optional_int(value: str | None) -> int | None:
    number = parse_optional_float(value)
    return None if number is None else int(number)


def parse_optional_bool(value: str | None) -> bool | None:
    if value is None or value.strip().lower() in {"", "na", "n/a", "unknown"}:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "present", "positive"}:
        return True
    if normalized in {"0", "false", "no", "absent", "negative"}:
        return False
    raise DataValidationError(f"invalid boolean category: {value}")


def parse_treatment(value: str | None) -> Treatment | None:
    if value is None or not value.strip():
        return None
    aliases = {
        "resection": Treatment.CURATIVE,
        "ablation": Treatment.CURATIVE,
        "curative": Treatment.CURATIVE,
        "transplant": Treatment.TRANSPLANT,
        "transplantation": Treatment.TRANSPLANT,
        "tace": Treatment.LOCOREGIONAL,
        "tare": Treatment.LOCOREGIONAL,
        "locoregional": Treatment.LOCOREGIONAL,
        "systemic": Treatment.SYSTEMIC,
        "chemotherapy": Treatment.SYSTEMIC,
        "immunotherapy": Treatment.SYSTEMIC,
        "bsc": Treatment.SUPPORTIVE,
        "supportive": Treatment.SUPPORTIVE,
    }
    normalized = value.strip().lower()
    if normalized in aliases:
        return aliases[normalized]
    try:
        return Treatment(normalized)
    except ValueError as error:
        raise DataValidationError(f"unknown treatment: {value}") from error


def profile_from_mapping(row: Mapping[str, str]) -> PatientProfile:
    patient_id = row.get("patient_id", "").strip()
    if not patient_id:
        raise DataValidationError("patient_id is required")
    age = parse_optional_int(row.get("age"))
    if age is None or age < 0 or age > 120:
        raise DataValidationError(f"invalid age for {patient_id}")
    count = parse_optional_int(row.get("tumor_count"))
    size = parse_optional_float(row.get("tumor_size_cm"))
    if count is not None and count < 1:
        raise DataValidationError(f"invalid tumor_count for {patient_id}")
    if size is not None and size <= 0:
        raise DataValidationError(f"invalid tumor_size_cm for {patient_id}")
    known = {field.name for field in fields(PatientProfile)}
    metadata = {
        key: value for key, value in row.items() if key not in known and value not in {None, ""}
    }
    return PatientProfile(
        patient_id=patient_id,
        age=age,
        sex=row.get("sex", "unknown"),
        tumor_size_cm=size,
        tumor_count=count,
        vascular_invasion=row.get("vascular_invasion") or None,
        extrahepatic_spread=parse_optional_bool(row.get("extrahepatic_spread")),
        performance_status=parse_optional_int(row.get("performance_status")),
        child_pugh_score=parse_optional_int(row.get("child_pugh_score")),
        meld_score=parse_optional_float(row.get("meld_score")),
        albumin_g_dl=parse_optional_float(row.get("albumin_g_dl")),
        bilirubin_mg_dl=parse_optional_float(row.get("bilirubin_mg_dl")),
        inr=parse_optional_float(row.get("inr")),
        platelets_10e9_l=parse_optional_float(row.get("platelets_10e9_l")),
        ascites=row.get("ascites") or None,
        encephalopathy=row.get("encephalopathy") or None,
        portal_hypertension=parse_optional_bool(row.get("portal_hypertension")),
        afp_ng_ml=parse_optional_float(row.get("afp_ng_ml")),
        fibrosis_stage=row.get("fibrosis_stage") or None,
        etiology=row.get("etiology") or None,
        first_course_treatment=parse_treatment(row.get("first_course_treatment")),
        registry=row.get("registry") or None,
        metadata=metadata,
    )


def read_profiles(path: Path) -> Iterator[PatientProfile]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                yield profile_from_mapping(row)
        return
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if line.strip():
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise DataValidationError(f"line {line_number} is not an object")
                    yield profile_from_mapping(
                        {
                            str(key): str(value) if value is not None else ""
                            for key, value in item.items()
                        }
                    )
        return
    raise DataValidationError(f"unsupported input extension: {path.suffix}")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def manifest(path: Path, profiles: tuple[PatientProfile, ...]) -> dict[str, Any]:
    registries: dict[str, int] = {}
    for profile in profiles:
        registry = profile.registry or "unknown"
        registries[registry] = registries.get(registry, 0) + 1
    return {
        "file": path.name,
        "sha256": file_sha256(path),
        "records": len(profiles),
        "registries": registries,
    }
