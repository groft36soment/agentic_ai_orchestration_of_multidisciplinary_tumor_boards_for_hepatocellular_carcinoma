from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from hera_mdt.schema import Axis


@dataclass(frozen=True)
class GuidelineChunk:
    identifier: str
    version: str
    axis: Axis
    decision_node: str
    text: str
    source: str


@dataclass(frozen=True)
class RetrievalHit:
    chunk: GuidelineChunk
    score: float


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.lower()))


class AxisKnowledgeBase:
    def __init__(self, chunks: tuple[GuidelineChunk, ...]) -> None:
        self._chunks = chunks
        self._document_frequency = self._build_document_frequency(chunks)

    @staticmethod
    def _build_document_frequency(chunks: tuple[GuidelineChunk, ...]) -> dict[str, int]:
        frequencies: dict[str, int] = {}
        for chunk in chunks:
            for token in set(tokenize(chunk.text + " " + chunk.decision_node)):
                frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    @classmethod
    def from_directory(cls, directory: Path) -> AxisKnowledgeBase:
        chunks: list[GuidelineChunk] = []
        for path in sorted(directory.glob("*.txt")):
            parts = path.stem.split("__")
            if len(parts) != 4:
                raise ValueError(f"invalid guideline chunk name: {path.name}")
            source, version, axis_name, node = parts
            chunks.append(
                GuidelineChunk(path.stem, version, Axis(axis_name), node, path.read_text(), source)
            )
        return cls(tuple(chunks))

    def retrieve(self, query: str, axis: Axis, limit: int = 5) -> tuple[RetrievalHit, ...]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return ()
        eligible = tuple(chunk for chunk in self._chunks if chunk.axis in {axis, Axis.BRIDGE})
        scores: list[RetrievalHit] = []
        total = max(1, len(self._chunks))
        for chunk in eligible:
            document = tokenize(chunk.text + " " + chunk.decision_node)
            counts = {token: document.count(token) for token in set(document)}
            score = 0.0
            for token in query_tokens:
                frequency = self._document_frequency.get(token, 0)
                inverse = math.log((total + 1.0) / (frequency + 1.0)) + 1.0
                score += counts.get(token, 0) * inverse / max(1, len(document))
            if score > 0:
                scores.append(RetrievalHit(chunk, score))
        return tuple(sorted(scores, key=lambda hit: (-hit.score, hit.chunk.identifier))[:limit])

    @property
    def chunks(self) -> tuple[GuidelineChunk, ...]:
        return self._chunks
