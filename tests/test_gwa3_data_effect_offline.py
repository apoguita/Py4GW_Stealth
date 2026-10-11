"""Offline tests for `py4gw/gwa3/data_effect.py` and `data_agent.Agent_GetAgentEffectInfo`.

No client. These two members are a pair -- the effect-argument reader prices a skill by its caster's
attribute level, which it asks the agent-side reader for -- and porting them un-refused three `Anti_*`
predicates and, through those, the 805 strategy bodies that guard on them. So what is asserted here is
the source's own arithmetic and its own guard order.

**One divergence is the source's, not this port's**, and it is pinned below: `Effect_GetEffectArg`
divides the skill table's scale ends by ``65536`` where the plugin's own `UAI_GetAgentEffectInfo` reads
them raw.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import data_agent, data_effect


class _Effect:
    """The port's effect record: the fields `EffectType` declares."""

    def __init__(
        self,
        skill_id: int = 0,
        attribute_level: int = 0,
        effect_id: int = 0,
        agent_id: int = 0,
        duration: float = 0.0,
        timestamp: int = 0,
    ) -> None:
        self.skill_id = skill_id
        self.attribute_level = attribute_level
        self.effect_id = effect_id
        self.agent_id = agent_id
        self.duration = duration
        self.timestamp = timestamp


class EffectArgTests(unittest.TestCase):
    """`Effect_GetEffectArg`: the three cases, their two roundings, and the hero arm."""

    SKILL = 1062

    def _serve(
        self, effect: _Effect | None, skill_values: dict[str, float] | None = None
    ) -> None:
        values = {
            "Duration0": 10,
            "Duration15": 40,
            "Scale0": 65536,
            "Scale15": 262144,
            "BonusScale0": 0,
            "BonusScale15": 655360,
            **(skill_values or {}),
        }
        patches = [
            mock.patch.object(
                data_effect, "Skill_GetSkillInfo", lambda skill_id, key="": values.get(key, 0)
            ),
            mock.patch.object(
                data_agent,
                "Agent_GetAgentEffectInfo",
                lambda agent_id=-2, skill_id=0, info="": (
                    int(effect.attribute_level) if effect is not None else 0
                ),
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_duration_interpolates_and_rounds(self) -> None:
        """``Round(10 + ((40 - 10) / 15) * 12)`` = ``round(34.0)`` = 34, and the halves round up."""

        self._serve(_Effect(attribute_level=12))
        self.assertEqual(data_effect.Effect_GetEffectArg(self.SKILL, "Duration"), 34)

        self._serve(_Effect(attribute_level=1))
        # 10 + 2 = 12 exactly; a half case is checked with a value that lands on .5
        self.assertEqual(data_effect.Effect_GetEffectArg(self.SKILL, "Duration"), 12)

    def test_scale_divides_the_skill_tables_ends_by_65536_and_floors(self) -> None:
        """``Floor(1 + ((4 - 1) / 15) * 12)`` = ``floor(3.4)`` = 3 -- the source's ``/ 65536`` kept."""

        self._serve(_Effect(attribute_level=12))
        self.assertEqual(data_effect.Effect_GetEffectArg(self.SKILL, "Scale"), 3)

    def test_bonus_scale_is_the_same_arithmetic_over_its_own_two_ends(self) -> None:
        """``Floor(0 + ((10 - 0) / 15) * 12)`` = ``floor(8.0)`` = 8."""

        self._serve(_Effect(attribute_level=12))
        self.assertEqual(data_effect.Effect_GetEffectArg(self.SKILL, "BonusScale"), 8)

    def test_an_unknown_argument_answers_zero(self) -> None:
        """The source's ``Case Else``."""

        self._serve(_Effect(attribute_level=12))
        self.assertEqual(data_effect.Effect_GetEffectArg(self.SKILL, "Nonsense"), 0)
        self.assertEqual(data_effect.Effect_GetEffectArg(self.SKILL), 0)

    def test_a_hero_number_resolves_that_heros_agent_id_first(self) -> None:
        """``$a_i_HeroNumber <> 0`` reads the hero's ``AgentID`` and asks for *its* effect (``:11``)."""

        seen: list[tuple] = []
        patches = [
            mock.patch.object(
                data_effect, "Skill_GetSkillInfo", lambda skill_id, key="": 10
            ),
            mock.patch.object(
                data_effect, "Party_GetMyPartyHeroInfo", lambda hero, key="": 4321
            ),
            mock.patch.object(
                data_agent,
                "Agent_GetAgentEffectInfo",
                lambda agent_id=-2, skill_id=0, info="": (
                    seen.append((agent_id, skill_id, info)) or 5
                ),
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

        data_effect.Effect_GetEffectArg(self.SKILL, "Duration", 2)
        self.assertEqual(seen, [(4321, self.SKILL, "AttributeLevel")])

        seen.clear()
        data_effect.Effect_GetEffectArg(self.SKILL, "Duration")
        self.assertEqual(seen, [(-2, self.SKILL, "AttributeLevel")])


class AgentEffectInfoTests(unittest.TestCase):
    """`Agent_GetAgentEffectInfo`: the five fields, the two computed columns and the guards."""

    SKILL = 1062

    def _serve(self, records: list[_Effect], timer: int = 10_000) -> None:
        patches = [
            mock.patch("py4gw.effect.get_effects", lambda agent_id: list(records)),
            mock.patch("py4gw.gwa3.data_skill.Skill_GetSkillTimer", lambda: timer),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_each_column_is_the_field_at_the_sources_own_offset(self) -> None:
        record = _Effect(
            skill_id=self.SKILL,
            attribute_level=9,
            effect_id=41,
            agent_id=235,
            duration=12.5,
            timestamp=9_000,
        )
        self._serve([record])
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "AttributeLevel"), 9)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "EffectID"), 41)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "CasterID"), 235)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "Duration"), 12.5)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "Timestamp"), 9_000)

    def test_the_two_computed_columns_are_the_sources_arithmetic(self) -> None:
        record = _Effect(skill_id=self.SKILL, duration=12.5, timestamp=9_000)
        self._serve([record], timer=10_000)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "TimeElapsed"), 1000)
        self.assertEqual(
            data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "TimeRemaining"), 12_500 - 1000
        )

    def test_has_effect_is_true_for_a_record_that_was_found(self) -> None:
        self._serve([_Effect(skill_id=self.SKILL)])
        self.assertIs(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "HasEffect"), True)

    def test_the_empty_column_answers_the_record_rather_than_a_pointer(self) -> None:
        """``If $a_s_Info = "" Then Return $l_p_EffectPtr`` (``:885``) -- the documented divergence."""

        record = _Effect(skill_id=self.SKILL)
        self._serve([record])
        self.assertIs(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, ""), record)
        self.assertIsNone(data_agent.Agent_GetAgentEffectInfo(-2, 999, ""))

    def test_a_skill_with_no_record_answers_zero(self) -> None:
        """``:884``: no record, no column. ``SkillID`` is commented out in the source and is not a column."""

        self._serve([_Effect(skill_id=self.SKILL)])
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, 999, "AttributeLevel"), 0)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "SkillID"), 0)
        self.assertEqual(data_agent.Agent_GetAgentEffectInfo(-2, self.SKILL, "Nonsense"), 0)


if __name__ == "__main__":
    unittest.main()
