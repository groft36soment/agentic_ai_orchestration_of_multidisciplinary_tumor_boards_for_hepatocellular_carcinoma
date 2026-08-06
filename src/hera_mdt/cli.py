from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from hera_mdt.data import manifest, read_profiles
from hera_mdt.evaluation import evaluate_profiles
from hera_mdt.orchestrator import HeraOrchestrator
from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.serialization import json_value, write_json


def parser(command: str) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog=command)
    result.add_argument("input", type=Path)
    result.add_argument("--knowledge", type=Path, default=Path("knowledge"))
    result.add_argument("--output", type=Path, required=True)
    result.add_argument(
        "--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR")
    )
    return result


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level), format="%(asctime)s %(levelname)s %(message)s"
    )


def run_main() -> None:
    arguments = parser("hera-run").parse_args()
    configure_logging(arguments.log_level)
    profiles = tuple(read_profiles(arguments.input))
    knowledge = AxisKnowledgeBase.from_directory(arguments.knowledge)
    orchestrator = HeraOrchestrator(knowledge)
    packets = tuple(orchestrator.decide(profile) for profile in profiles)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="utf-8") as stream:
        for packet in packets:
            stream.write(json.dumps(json_value(asdict(packet)), sort_keys=True) + "\n")
    logging.info("processed %d patient profiles", len(packets))


def evaluate_main() -> None:
    arguments = parser("hera-evaluate").parse_args()
    configure_logging(arguments.log_level)
    profiles = tuple(read_profiles(arguments.input))
    knowledge = AxisKnowledgeBase.from_directory(arguments.knowledge)
    rows, summary = evaluate_profiles(profiles, HeraOrchestrator(knowledge).decide)
    write_json(arguments.output, {"rows": rows, "summary": summary})
    logging.info("evaluated %d patient profiles", len(rows))


def prepare_main() -> None:
    arguments = parser("hera-prepare").parse_args()
    configure_logging(arguments.log_level)
    profiles = tuple(read_profiles(arguments.input))
    write_json(arguments.output, manifest(arguments.input, profiles))
    logging.info("validated %d patient profiles", len(profiles))
