from hera_mdt.agents import AgentContext, default_agents
from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import Axis, PatientProfile


def test_six_specialists(profile: PatientProfile, knowledge: AxisKnowledgeBase) -> None:
    opinions = tuple(agent.assess(AgentContext(profile, knowledge)) for agent in default_agents())
    assert len(opinions) == 6
    assert sum(opinion.axis == Axis.TUMOR for opinion in opinions) == 2
    assert sum(opinion.axis == Axis.HEPATIC for opinion in opinions) == 2
    assert sum(opinion.axis == Axis.BRIDGE for opinion in opinions) == 2
    assert all(0.0 <= opinion.confidence <= 1.0 for opinion in opinions)
    assert all(opinion.evidence for opinion in opinions)
