from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import Axis


def test_axis_filter(knowledge: AxisKnowledgeBase) -> None:
    hits = knowledge.retrieve("portal hypertension resection", Axis.HEPATIC)
    assert hits
    assert all(hit.chunk.axis in {Axis.HEPATIC, Axis.BRIDGE} for hit in hits)


def test_empty_query(knowledge: AxisKnowledgeBase) -> None:
    assert knowledge.retrieve("", Axis.TUMOR) == ()
