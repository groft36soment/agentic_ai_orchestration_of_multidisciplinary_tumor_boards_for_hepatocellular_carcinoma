import json
from pathlib import Path

from hera_mdt.orchestrator import HeraOrchestrator
from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import PatientProfile
from hera_mdt.serialization import write_json


def test_decision_packet(profile: PatientProfile, knowledge: AxisKnowledgeBase) -> None:
    packet = HeraOrchestrator(knowledge).decide(profile)
    assert packet.patient_id == profile.patient_id
    assert packet.evidence
    assert packet.reopen_conditions
    assert 0.0 <= packet.confidence.integrated <= 1.0


def test_nested_packet_serialization(
    profile: PatientProfile, knowledge: AxisKnowledgeBase, tmp_path: Path
) -> None:
    packet = HeraOrchestrator(knowledge).decide(profile)
    path = tmp_path / "packet.json"
    write_json(path, {"packets": (packet,)})
    payload = json.loads(path.read_text())
    assert payload["packets"][0]["patient_id"] == profile.patient_id
