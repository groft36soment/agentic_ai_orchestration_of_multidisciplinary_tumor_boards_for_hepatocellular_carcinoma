from hera_mdt.agents import AgentContext, default_agents
from hera_mdt.arbitration import EpistemicArbitrator, combine_axis
from hera_mdt.retrieval import AxisKnowledgeBase
from hera_mdt.schema import Axis, EpistemicAct, PatientProfile


def test_monotonic_deliberation(profile: PatientProfile, knowledge: AxisKnowledgeBase) -> None:
    opinions = tuple(agent.assess(AgentContext(profile, knowledge)) for agent in default_agents())
    tumor = combine_axis(Axis.TUMOR, opinions)
    hepatic = combine_axis(Axis.HEPATIC, opinions)
    bridges = tuple(opinion for opinion in opinions if opinion.axis == Axis.BRIDGE)
    _, confidence, rounds, _ = EpistemicArbitrator().deliberate(tumor, hepatic, bridges)
    assert 0.0 <= confidence <= 1.0
    assert len(rounds) <= 3
    for left, right in zip(rounds, rounds[1:], strict=False):
        assert set(right.viable_options).issubset(left.viable_options)
    if rounds:
        assert {act.act for act in rounds[0].acts} == {
            EpistemicAct.PROPOSE,
            EpistemicAct.CHALLENGE,
            EpistemicAct.BRIDGE,
            EpistemicAct.SYNTHESIZE,
        }
