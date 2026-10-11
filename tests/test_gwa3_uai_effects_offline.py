"""Offline tests for `py4gw/gwa3/uai_effects.py`.

No client and no elevation. This module used to be the layer's clearest case of a split a caller feels:
**presence routed, timing refused**. That split is gone, and the reason is a correction this file records:
the timing columns rest on ``$GC_UAI_EFFECT_Timestamp``, which this layer had called a field "GwAu3 writes
when it fills its cache" -- and the cache is filled from the **client's own effect record**
(``Memory_ReadArrayStruct($l_p_EffectArray, ...)``, ``UtilityAI_EffectsCache.au3:181``). So all ten
columns are routed over the port's `EffectType`, four of them computed with the source's own arithmetic,
and the tests pin that instead.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from py4gw.gwa3 import constants, uai_effects


class _Effect:
    """A stand-in for the port's effect record: the fields `EffectType` declares, and no others."""

    def __init__(
        self,
        skill_id: int = 0,
        duration: float = 0.0,
        attribute_level: int = 0,
        effect_id: int = 0,
        agent_id: int = 0,
        timestamp: int = 0,
    ) -> None:
        self.skill_id = skill_id
        self.duration = duration
        self.attribute_level = attribute_level
        self.effect_id = effect_id
        self.agent_id = agent_id
        self.timestamp = timestamp


class PresenceTests(unittest.TestCase):
    """The routed questions: does it exist, how many, is it upkept."""

    def test_an_effect_question_goes_to_the_client(self) -> None:
        with mock.patch.object(uai_effects._effect, "effect_exists", return_value=True) as exists:
            self.assertIs(uai_effects.UAI_AgentHasEffect(235, 1062), True)
            exists.assert_called_once_with(235, 1062)

        with mock.patch.object(uai_effects._effect, "effect_exists", return_value=False):
            self.assertIs(uai_effects.UAI_AgentHasEffect(235, 1062), False)

    def test_the_player_form_uses_the_controlled_character(self) -> None:
        with mock.patch.object(
            uai_effects.Player, "GetAgentID", return_value=235
        ), mock.patch.object(
            uai_effects._effect, "effect_exists", return_value=True
        ) as exists:
            self.assertIs(uai_effects.UAI_PlayerHasEffect(1062), True)
            exists.assert_called_once_with(235, 1062)

    def test_a_bond_question_goes_to_the_client_buff_list(self) -> None:
        """An upkeep is a maintained enchantment, which is the client's own buff list."""

        with mock.patch.object(uai_effects._effect, "buff_exists", return_value=True) as exists:
            self.assertIs(uai_effects.UAI_AgentUpkeepsBond(235, 1062), True)
            exists.assert_called_once_with(235, 1062)

        with mock.patch.object(
            uai_effects.Player, "GetAgentID", return_value=235
        ), mock.patch.object(
            uai_effects._effect, "buff_exists", return_value=False
        ) as exists:
            self.assertIs(uai_effects.UAI_PlayerUpkeepsBond(1062), False)
            exists.assert_called_once_with(235, 1062)

    def test_the_counts_come_from_the_client(self) -> None:
        with mock.patch.object(uai_effects._effect, "effect_count", return_value=3) as count:
            self.assertEqual(uai_effects.UAI_GetAgentEffectCount(235), 3)
            count.assert_called_once_with(235)

        with mock.patch.object(
            uai_effects.Player, "GetAgentID", return_value=7
        ), mock.patch.object(uai_effects._effect, "effect_count", return_value=1) as count:
            self.assertEqual(uai_effects.UAI_GetPlayerEffectCount(), 1)
            count.assert_called_once_with(7)


class TimingPropertyTests(unittest.TestCase):
    """The four computed properties, over the client's own effect record.

    **These used to be asserted as refusals, and that assertion was wrong** -- it rested on the claim that
    ``$GC_UAI_EFFECT_Timestamp`` is a field GwAu3 writes when it fills its cache. The cache is filled from
    a client read (`Memory_ReadArrayStruct($l_p_EffectArray, ...)` at ``UtilityAI_EffectsCache.au3:181``)
    with the timestamp at ``+0x14`` and the duration at ``+0x10`` of the client's own record, so the
    source's formulas are formulas over client fields -- which is what these tests now check, in the
    source's own arithmetic.
    """

    TIMING = ("TimeElapsed", "TimeRemaining", "Scale", "BonusScale")

    def _serve(self, record: Any, timer: int = 10_000, scales: dict[str, int] | None = None) -> None:
        values = {"Scale0": 10, "Scale15": 40, "BonusScale0": 2, "BonusScale15": 32, **(scales or {})}
        patches = [
            mock.patch.object(uai_effects._effect, "effect_exists", return_value=True),
            mock.patch.object(uai_effects._effect, "get_effects", return_value=[record]),
            mock.patch("py4gw.gwa3.data_skill.Skill_GetSkillTimer", lambda: timer),
            mock.patch(
                "py4gw.gwa3.data_skill.Skill_GetSkillInfo",
                lambda skill_id, key="": values.get(key, 0),
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_every_column_of_the_enum_has_a_reader(self) -> None:
        """The corrected claim, stated as a test: nothing in the enum is left unread."""

        names = {
            name[len("GC_UAI_EFFECT_") :]
            for name in constants.__all__
            if name.startswith("GC_UAI_EFFECT_") and name != "GC_UAI_EFFECT_COUNT"
        }
        self.assertEqual(names, set(uai_effects._EFFECT_PROPERTY_READERS))

    def test_time_elapsed_is_the_source_masked_subtraction(self) -> None:
        record = _Effect(skill_id=1062, timestamp=9_000)
        self._serve(record, timer=10_000)
        with mock.patch.object(uai_effects, "_find_effect", return_value=record):
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_TimeElapsed),
                1000,
            )

    def test_time_remaining_is_the_duration_in_milliseconds_minus_the_elapsed(self) -> None:
        record = _Effect(skill_id=1062, duration=12.5, timestamp=9_000)
        self._serve(record, timer=10_000)
        with mock.patch.object(uai_effects, "_find_effect", return_value=record):
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_TimeRemaining),
                12_500 - 1000,
            )

    def test_scale_interpolates_the_skills_own_two_ends_and_floors(self) -> None:
        record = _Effect(skill_id=1062, attribute_level=12)
        self._serve(record, scales={"Scale0": 10, "Scale15": 40})
        with mock.patch.object(uai_effects, "_find_effect", return_value=record):
            # floor(10 + ((40 - 10) / 15) * 12) = floor(34.0) = 34
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_Scale), 34
            )

    def test_bonus_scale_uses_the_bonus_pair(self) -> None:
        record = _Effect(skill_id=1062, attribute_level=5)
        self._serve(record, scales={"BonusScale0": 2, "BonusScale15": 32})
        with mock.patch.object(uai_effects, "_find_effect", return_value=record):
            # floor(2 + ((32 - 2) / 15) * 5) = floor(12.0) = 12
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_BonusScale), 12
            )

    def test_the_player_form_answers_the_same_way(self) -> None:
        record = _Effect(skill_id=1062, timestamp=9_000)
        self._serve(record, timer=10_000)
        with mock.patch.object(uai_effects.Player, "GetAgentID", return_value=235), mock.patch.object(
            uai_effects, "_find_effect", return_value=record
        ):
            self.assertEqual(
                uai_effects.UAI_GetPlayerEffectInfo(1062, constants.GC_UAI_EFFECT_TimeElapsed), 1000
            )

    def test_the_property_enum_is_read_from_gwaus_own(self) -> None:
        """The numbers come from the generated constants, not a transcription of the enum."""

        self.assertEqual(uai_effects._EFFECT_PROPERTIES[constants.GC_UAI_EFFECT_SkillID], "SkillID")
        self.assertEqual(
            uai_effects._EFFECT_PROPERTIES[constants.GC_UAI_EFFECT_TimeElapsed], "TimeElapsed"
        )
        self.assertNotIn(constants.GC_UAI_EFFECT_COUNT, uai_effects._EFFECT_PROPERTIES)


class EffectPropertyTests(unittest.TestCase):
    """The non-timing properties, and GwAu3's own guards."""

    def test_a_property_outside_the_enum_answers_zero_first(self) -> None:
        with mock.patch.object(uai_effects._effect, "effect_exists") as exists:
            self.assertEqual(uai_effects.UAI_GetAgentEffectInfo(235, 1062, -1), 0)
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_COUNT), 0
            )
            exists.assert_not_called()

    def test_an_effect_the_agent_does_not_have_answers_zero(self) -> None:
        """GwAu3's loop simply never matches and its trailing `Return 0` does the same."""

        with mock.patch.object(uai_effects._effect, "effect_exists", return_value=False):
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(
                    235, 1062, constants.GC_UAI_EFFECT_Duration
                ),
                0,
            )

    def test_a_routed_property_reads_the_port_record(self) -> None:
        record = _Effect(skill_id=1062, duration=12.5)
        with mock.patch.object(
            uai_effects._effect, "effect_exists", return_value=True
        ), mock.patch.object(uai_effects._effect, "get_effects", return_value=[record]):
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_SkillID), 1062
            )
            self.assertEqual(
                uai_effects.UAI_GetAgentEffectInfo(235, 1062, constants.GC_UAI_EFFECT_Duration),
                12.5,
            )

    def test_every_other_column_reads_the_port_record(self) -> None:
        """`AttributeLevel`, `EffectID`, `CasterID` and `Timestamp` are the record's own fields.

        They used to refuse here -- the claim was that GwAu3 answers them from its cache -- and the cache
        is filled from the client's record, so they are the same fields. The reader table names each one
        literally, which this checks by reading the record's own values back.
        """

        record = _Effect(skill_id=1062, duration=12.5, attribute_level=7, effect_id=3, agent_id=235, timestamp=9_000)
        with mock.patch.object(
            uai_effects._effect, "effect_exists", return_value=True
        ), mock.patch.object(uai_effects._effect, "get_effects", return_value=[record]):
            for name, expected in (
                ("AttributeLevel", 7),
                ("EffectID", 3),
                ("CasterID", 235),
                ("Timestamp", 9_000),
            ):
                with self.subTest(property=name):
                    self.assertEqual(
                        uai_effects.UAI_GetAgentEffectInfo(
                            235, 1062, getattr(constants, f"GC_UAI_EFFECT_{name}")
                        ),
                        expected,
                    )
    def test_the_bond_info_refuses(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            uai_effects.UAI_GetAgentBondInfo(235, 1062, 0)
        message = str(raised.exception)
        self.assertIn("$g_amx3_BondsCache", message)
        self.assertIn("UAI_AgentUpkeepsBond", message)

    def test_the_declared_surface(self) -> None:
        """The seventeen questions this module answers, by GwAu3's own names.

        The source file declares **31** functions: these seventeen are the question set -- presence,
        counts, the ten property columns, the three effect-type names, the feeder-enchantment test and
        the six visible-effect members -- and the other fourteen are the cache's own fill machinery
        (`UAI_CacheAgentInfo`, `UAI_DecodeAgentInto`, `UAI_FillEffectRows`, the four struct getters and
        their neighbours), which write rows this layer does not keep. The route map tiers each of them;
        the layer answers their *contents* live instead.
        """

        self.assertEqual(
            sorted(uai_effects.__all__),
            [
                "UAI_AgentHasEffect",
                "UAI_AgentHasVisibleEffect",
                "UAI_AgentUpkeepsBond",
                "UAI_GetAgentBondInfo",
                "UAI_GetAgentEffectCount",
                "UAI_GetAgentEffectInfo",
                "UAI_GetAgentVisibleEffectCount",
                "UAI_GetAgentVisibleEffectInfo",
                "UAI_GetFeederEnchOnTop",
                "UAI_GetPlayerEffectCount",
                "UAI_GetPlayerEffectInfo",
                "UAI_GetPlayerVisibleEffectCount",
                "UAI_GetPlayerVisibleEffectInfo",
                "UAI_PlayerHasEffect",
                "UAI_PlayerHasEffectType",
                "UAI_PlayerHasVisibleEffect",
                "UAI_PlayerUpkeepsBond",
            ],
        )


class PlayerHasEffectTypeTests(unittest.TestCase):
    """`UAI_PlayerHasEffectType` and the `_player_effect_of_type` twin that carries its ``@extended``.

    This member was ported late and its absence was the reason `UAI_IsCastSensible` carried an inline
    scan instead: GwAu3's own name is the one a migrating script calls, and the source declares it in
    *this* file (``UtilityAI_EffectsCache.au3:587-610``), beside the questions above.
    """

    #: ``(the effect type name, the skill type constant the source's Switch maps it to)``.
    NAMES = (
        ("HasStance", constants.GC_I_SKILL_TYPE_STANCE),
        ("HasGlyph", constants.GC_I_SKILL_TYPE_GLYPH),
        ("HasPreparation", constants.GC_I_SKILL_TYPE_PREPARATION),
    )

    def _served(self, answer: int = 0) -> mock.MagicMock:
        """The twin, answering one skill id, so the constant it was asked for is observable."""

        patcher = mock.patch.object(uai_effects, "_player_effect_of_type", return_value=answer)
        twin = patcher.start()
        self.addCleanup(patcher.stop)
        return twin

    def test_each_name_is_mapped_to_the_skill_type_the_source_maps_it_to(self) -> None:
        for name, skill_type in self.NAMES:
            with self.subTest(name=name):
                twin = self._served()
                self.assertIs(uai_effects.UAI_PlayerHasEffectType(name), False)
                twin.assert_called_once_with(skill_type)

    def test_a_hit_answers_true(self) -> None:
        twin = self._served(answer=1062)
        self.assertIs(uai_effects.UAI_PlayerHasEffectType("HasStance"), True)
        twin.assert_called_once_with(constants.GC_I_SKILL_TYPE_STANCE)

    def test_an_unknown_name_answers_false_without_scanning(self) -> None:
        """``Case Else: Return SetError(1, 0, False)`` -- the ``@error`` has no twin, the ``False`` does."""

        twin = self._served()
        self.assertIs(uai_effects.UAI_PlayerHasEffectType("HasBond"), False)
        self.assertIs(uai_effects.UAI_PlayerHasEffectType(), False)
        twin.assert_not_called()

    def test_the_name_comparison_is_case_insensitive(self) -> None:
        """AutoIt's string ``Switch`` is, unless ``Opt("StringCaseSense", 1)`` is set -- it never is."""

        for spelling in ("hasstance", "HASSTANCE", "HasStance"):
            with self.subTest(spelling=spelling):
                twin = self._served()
                uai_effects.UAI_PlayerHasEffectType(spelling)
                twin.assert_called_once_with(constants.GC_I_SKILL_TYPE_STANCE)

    def test_the_scan_runs_backwards_over_the_effect_list(self) -> None:
        """``For $i = ($l_i_EffectCount - 1) To 0 Step -1``: the **last** match is the id answered.

        Two stances are up; the second one in the client's array is the answer the source hands back
        through ``@extended``, and `UAI_IsCastSensible` compares *that* with the slot's skill.
        """

        records = [
            _Effect(skill_id=1000),
            _Effect(skill_id=2000),
        ]
        types = {1000: constants.GC_I_SKILL_TYPE_STANCE, 2000: constants.GC_I_SKILL_TYPE_STANCE}
        with mock.patch.object(
            uai_effects.Player, "GetAgentID", return_value=7
        ), mock.patch.object(
            uai_effects._effect, "get_effects", return_value=records
        ), mock.patch(
            "py4gw.gwa3.data_skill.Skill_GetSkillInfo",
            lambda skill_id, key="": types.get(int(skill_id), 0),
        ):
            self.assertEqual(
                uai_effects._player_effect_of_type(constants.GC_I_SKILL_TYPE_STANCE), 2000
            )

    def test_an_effect_from_a_different_type_is_not_matched(self) -> None:
        records = [_Effect(skill_id=1000)]
        with mock.patch.object(
            uai_effects.Player, "GetAgentID", return_value=7
        ), mock.patch.object(
            uai_effects._effect, "get_effects", return_value=records
        ), mock.patch(
            "py4gw.gwa3.data_skill.Skill_GetSkillInfo",
            lambda skill_id, key="": constants.GC_I_SKILL_TYPE_GLYPH,
        ):
            self.assertEqual(
                uai_effects._player_effect_of_type(constants.GC_I_SKILL_TYPE_STANCE), 0
            )

    def test_a_zero_skill_id_row_is_skipped(self) -> None:
        """The source's loop reads every row's skill id; an empty row cannot match a type."""

        records = [_Effect(skill_id=0), _Effect(skill_id=3000)]
        with mock.patch.object(
            uai_effects.Player, "GetAgentID", return_value=7
        ), mock.patch.object(
            uai_effects._effect, "get_effects", return_value=records
        ), mock.patch(
            "py4gw.gwa3.data_skill.Skill_GetSkillInfo",
            lambda skill_id, key="": constants.GC_I_SKILL_TYPE_STANCE,
        ):
            self.assertEqual(
                uai_effects._player_effect_of_type(constants.GC_I_SKILL_TYPE_STANCE), 3000
            )


class FeederEnchantmentTests(unittest.TestCase):
    """`UAI_GetFeederEnchOnTop`: the newest Dervish enchantment, and whether it is a *new* one.

    The member is what seven generated strategy bodies call (``UtilityAI_Attack.au3`` ×6 and
    ``UtilityAI_Stance.au3`` ×1), so the tests pin its four answers: nothing up, a non-feeder on top, a
    feeder reported for the first time, and the same feeder again.
    """

    def setUp(self) -> None:
        original = uai_effects.g_i_LastFeederEnchTimestamp
        self.addCleanup(setattr, uai_effects, "g_i_LastFeederEnchTimestamp", original)
        uai_effects.g_i_LastFeederEnchTimestamp = 0

    _FEEDER = constants.GC_I_SKILL_ID_GRENTHS_FINGERS
    _OTHER = constants.GC_I_SKILL_ID_DUST_CLOAK

    def _serve(self, records: list, professions: dict[int, int] | None = None) -> None:
        """The client's effect list and the skill table's two columns."""

        profession = professions or {}
        types = {int(record.skill_id): constants.GC_I_SKILL_TYPE_ENCHANTMENT for record in records}
        patches = [
            mock.patch.object(uai_effects.Player, "GetAgentID", return_value=7),
            mock.patch.object(uai_effects._effect, "get_effects", return_value=records),
            mock.patch(
                "py4gw.gwa3.data_skill.Skill_GetSkillInfo",
                lambda skill_id, key="": (
                    profession.get(int(skill_id), constants.GC_I_PROFESSION_DERVISH)
                    if key == "Profession"
                    else types.get(int(skill_id), 0)
                ),
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_no_effects_answers_false(self) -> None:
        self._serve([])
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), False)

    def test_a_non_dervish_effect_is_not_a_feeder(self) -> None:
        record = _Effect(skill_id=self._FEEDER, timestamp=500)
        self._serve([record], professions={self._FEEDER: constants.GC_I_PROFESSION_WARRIOR})
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), False)

    def test_a_dervish_effect_that_is_not_an_enchantment_is_not_a_feeder(self) -> None:
        record = _Effect(skill_id=self._FEEDER, timestamp=500)
        self._serve([record])
        with mock.patch(
            "py4gw.gwa3.data_skill.Skill_GetSkillInfo",
            lambda skill_id, key="": constants.GC_I_PROFESSION_DERVISH
            if key == "Profession"
            else constants.GC_I_SKILL_TYPE_STANCE,
        ):
            self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), False)

    def test_a_dervish_enchantment_outside_the_sources_list_is_not_a_feeder(self) -> None:
        record = _Effect(skill_id=1494, timestamp=500)
        self._serve([record])
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), False)

    def test_a_new_feeder_answers_true_and_is_remembered(self) -> None:
        record = _Effect(skill_id=self._OTHER, timestamp=500)
        self._serve([record])
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), True)
        self.assertEqual(uai_effects.g_i_LastFeederEnchTimestamp, 500)

        # The same enchantment, still on top: the source compares the timestamp it remembered.
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), False)

    def test_the_newest_of_two_feeders_is_the_one_reported(self) -> None:
        records = [
            _Effect(skill_id=self._FEEDER, timestamp=100),
            _Effect(skill_id=self._OTHER, timestamp=900),
        ]
        self._serve(records)
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), True)
        self.assertEqual(uai_effects.g_i_LastFeederEnchTimestamp, 900)

    def test_a_reset_makes_the_same_enchantment_report_again(self) -> None:
        """``UAI_ResetRuntime`` zeroes the timestamp (``UtilityAI_Cache.au3:72``)."""

        record = _Effect(skill_id=self._FEEDER, timestamp=700)
        self._serve([record])
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), True)
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), False)

        uai_effects.g_i_LastFeederEnchTimestamp = 0
        self.assertIs(uai_effects.UAI_GetFeederEnchOnTop(), True)


class VisibleEffectTests(unittest.TestCase):
    """The visible-effect family: the agent's own list, walked from its record.

    GwAu3 fills a fourth cache from the TList at ``agent pointer + 0x174`` and answers these six
    members from it (``UtilityAI_EffectsCache.au3:116-137``, ``:480-547``). This layer walks the same
    list through the ported agent context, so what these tests pin is the **mapping**: the port's
    `VisibleEffectStruct` fields against the source's ``EffectType``/``EffectID``/``HasEnded``, the
    type-then-id order of the comparison, and the two shapes the info members answer.
    """

    class _Effect:
        """The port's visible-effect record: ``unk``, ``id`` and ``has_ended``."""

        def __init__(self, effect_type: int = 0, effect_id: int = 0, has_ended: int = 0) -> None:
            self.unk = effect_type
            self.id = effect_id
            self.has_ended = has_ended

    def _serve(self, effects: list, living: bool = True) -> None:
        record = mock.Mock()
        record.is_living_type = living
        record.visible_effects = effects
        patch = mock.patch.object(
            uai_effects, "_visible_effects", lambda agent_id: list(record.visible_effects)
            if record.is_living_type
            else []
        )
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_visible_effect_is_matched_on_its_type_and_then_its_id(self) -> None:
        """The source's order: a row is skipped when its *type* differs, then its id is compared.

        Both rows carry id 97 and differ only in type, so a port that compared ids alone would answer
        the first of these four calls ``True`` -- and it must not.
        """

        self._serve(
            [
                self._Effect(effect_type=2, effect_id=97),
                self._Effect(effect_type=1, effect_id=97),
            ]
        )
        status = constants.GC_I_EFFECT_TYPE_STATUS
        self.assertTrue(uai_effects.UAI_AgentHasVisibleEffect(11, status, 97))
        self.assertFalse(uai_effects.UAI_AgentHasVisibleEffect(11, status, 98))
        self.assertTrue(uai_effects.UAI_AgentHasVisibleEffect(11, 2, 97))
        self.assertFalse(uai_effects.UAI_AgentHasVisibleEffect(11, 2, 98))
        self.assertFalse(uai_effects.UAI_AgentHasVisibleEffect(11, 3, 97))

    def test_an_agent_with_no_list_answers_false(self) -> None:
        self._serve([])
        self.assertFalse(
            uai_effects.UAI_AgentHasVisibleEffect(
                11, constants.GC_I_EFFECT_TYPE_STATUS, constants.GC_I_EFFECT_ID_DAZED
            )
        )

    def test_the_player_form_asks_for_the_controlled_character(self) -> None:
        self._serve([self._Effect(effect_type=1, effect_id=28)])
        with mock.patch.object(uai_effects.Player, "GetAgentID", return_value=235):
            self.assertTrue(uai_effects.UAI_PlayerHasVisibleEffect(1, 28))

    def test_the_count_is_the_length_of_the_list(self) -> None:
        self._serve([self._Effect(effect_id=1), self._Effect(effect_id=2)])
        self.assertEqual(uai_effects.UAI_GetAgentVisibleEffectCount(11), 2)

    def test_the_info_rows_carry_the_count_first(self) -> None:
        """``[0][0]`` is the count and the rows are ``(EffectType, EffectID, HasEnded)`` (``:509-516``)."""

        self._serve([self._Effect(effect_type=1, effect_id=23, has_ended=0)])
        self.assertEqual(
            uai_effects.UAI_GetAgentVisibleEffectInfo(11),
            [[1, 0, 0], [1, 23, 0]],
        )

    def test_an_agent_with_no_rows_answers_the_sources_own_one_by_one(self) -> None:
        """``Local $l_ai2_VisEffects[1][1] = [[0]]`` returned unchanged (``:504-506``)."""

        self._serve([])
        self.assertEqual(uai_effects.UAI_GetAgentVisibleEffectInfo(11), [[0]])

    def test_the_player_info_and_count_read_the_players_own_record(self) -> None:
        self._serve([self._Effect(effect_type=1, effect_id=26)])
        with mock.patch.object(uai_effects.Player, "GetAgentID", return_value=235):
            self.assertEqual(uai_effects.UAI_GetPlayerVisibleEffectInfo(), [[1, 0, 0], [1, 26, 0]])
            self.assertEqual(uai_effects.UAI_GetPlayerVisibleEffectCount(), 1)

    def test_a_non_living_record_has_no_visible_effects(self) -> None:
        """GwAu3's fill passes over every non-living agent (``:229``), so its row count is zero."""

        record = mock.Mock()
        record.is_living_type = False
        with mock.patch(
            "py4gw.gwa3.data_agent.Agent_GetAgentPtr", lambda agent_id: record
        ):
            self.assertEqual(uai_effects._visible_effects(11), [])

    def test_a_record_the_client_does_not_hold_has_none_either(self) -> None:
        with mock.patch("py4gw.gwa3.data_agent.Agent_GetAgentPtr", lambda agent_id: None):
            self.assertEqual(uai_effects._visible_effects(11), [])


if __name__ == "__main__":
    unittest.main()
