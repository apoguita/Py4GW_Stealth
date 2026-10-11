"""Offline tests for the small action modules: quest, title, other, effect, cinematic, guild, skill.

No client and no elevation. Two things are being established, and both are the layer's own contract
rather than GwAu3's behaviour:

* the routed functions reach the ported member this project's route map records, with the argument
  GwAu3's own body produces -- including the guards that stop the call before it is made;
* every refused function refuses with a reason that cites the GwAu3 line **and** the place the work
  lives, because a refusal nobody can act on is only half a refusal.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import (
    cmd_cinematic,
    cmd_effect,
    cmd_guild,
    cmd_other,
    cmd_quest,
    cmd_skill,
    cmd_title,
)


class RefusalTests(unittest.TestCase):
    """Every refused function, in every module added this round."""

    REFUSALS = (
        (cmd_quest, "Quest_AcceptQuest", (100,)),
        (cmd_quest, "Quest_QuestReward", (100,)),
        (cmd_other, "Other_PingSleep", (0,)),
        (cmd_other, "Other_WaitPingStabilized", (2000,)),
        (cmd_cinematic, "Cinematic_SkipCinematic", ()),
        (cmd_cinematic, "Cinematic_WaitCinematic", ()),
        (cmd_effect, "Effect_DropBond", (1,)),
        (cmd_guild, "Guild_InviteGuild", ("Someone",)),
        (cmd_guild, "Guild_InviteGuest", ("Someone",)),
        (cmd_skill, "Skill_CancelHeroSkill", (1, 1)),
        (cmd_skill, "Skill_SetSkillbarSkill", (1, 1)),
        (cmd_skill, "Skill_LoadSkillBar", ()),
        (cmd_skill, "Skill_UnlockSkillBossByID", (1,)),
        (cmd_skill, "Skill_UnlockTomeSkillByID", (1, 2)),
        (cmd_skill, "Skill_SkillForQuest", (1,)),
    )

    def test_every_refusal_names_the_source_and_the_work(self) -> None:
        for module, name, args in self.REFUSALS:
            with self.subTest(module=module.__name__, function=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(module, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_", message, "the refusal must cite GwAu3's own line")
                self.assertIn("py4gw", message, "the refusal must say where the work lives")

    def test_the_declared_surfaces_are_the_sources_own(self) -> None:
        """Each module exports exactly the functions its GwAu3 file declares."""

        expected = {
            cmd_quest: 4,
            cmd_title: 1,
            cmd_other: 4,
            cmd_effect: 1,
            cmd_cinematic: 2,
            cmd_guild: 2,
            cmd_skill: 10,
        }
        for module, count in expected.items():
            with self.subTest(module=module.__name__):
                self.assertEqual(len(module.__all__), count)
                for name in module.__all__:
                    self.assertTrue(callable(getattr(module, name)), name)


class RoutedActionTests(unittest.TestCase):
    """The routed functions, against a mocked ported surface."""

    def test_the_sleeps_take_as_long_as_gwau3(self) -> None:
        """`RndSleep`/`TolSleep` are host time, and the arithmetic is GwAu3's own."""

        with mock.patch.object(cmd_other.time, "sleep") as sleep:
            cmd_other.Other_TolSleep(150, 50)
            slept = sleep.call_args.args[0]
            self.assertGreaterEqual(slept, 0.100)
            self.assertLessEqual(slept, 0.200)

        with mock.patch.object(cmd_other.time, "sleep") as sleep:
            cmd_other.Other_RndSleep(1000, 0.05)
            slept = sleep.call_args.args[0]
            # 5% of 1000 is 50, so the window is 950..1050 ms.
            self.assertGreaterEqual(slept, 0.950)
            self.assertLessEqual(slept, 1.050)

    def test_the_title_zero_hides_rather_than_displays(self) -> None:
        with mock.patch.object(cmd_title.Player, "SetActiveTitle") as set_title, mock.patch.object(
            cmd_title.Player, "RemoveActiveTitle"
        ) as remove:
            cmd_title.Title_SetDisplayedTitle(0)
            remove.assert_called_once_with()
            set_title.assert_not_called()

            cmd_title.Title_SetDisplayedTitle(7)
            set_title.assert_called_once_with(7)

    def test_quest_abandon_and_request_reach_the_ported_members(self) -> None:
        with mock.patch.object(cmd_quest.Quest, "AbandonQuest") as abandon:
            self.assertTrue(cmd_quest.Quest_AbandonQuest(42))
            abandon.assert_called_once_with(42)

        with mock.patch.object(cmd_quest.Quest, "RequestQuestInfo") as request:
            self.assertIsNone(cmd_quest.Quest_RequestInfos(42))
            request.assert_called_once_with(42, False)

    def test_use_skill_keeps_gwau3s_guards(self) -> None:
        with mock.patch.object(cmd_skill.SkillBar, "UseSkill") as use:
            # A slot outside 1..8 answers False without reaching the client.
            self.assertFalse(cmd_skill.Skill_UseSkill(0, -2))
            self.assertFalse(cmd_skill.Skill_UseSkill(9, -2))
            use.assert_not_called()

            # The -2 sentinel is GwAu3's own for the controlled character.
            with mock.patch.object(cmd_skill, "Agent_ConvertID", return_value=0):
                self.assertFalse(cmd_skill.Skill_UseSkill(1, -2))
                use.assert_not_called()

            with mock.patch.object(cmd_skill, "Agent_ConvertID", return_value=235):
                self.assertTrue(cmd_skill.Skill_UseSkill(1, -2))
                use.assert_called_once_with(1, 235)

    def test_use_hero_skill_refuses_a_hero_that_is_not_in_the_party(self) -> None:
        with mock.patch.object(
            cmd_skill.Party.Heroes, "GetHeroAgentIDByPartyPosition", return_value=0
        ), mock.patch.object(cmd_skill.Party.Heroes, "UseSkill") as use:
            self.assertFalse(cmd_skill.Skill_UseHeroSkill(1, 1, 0))
            use.assert_not_called()

        with mock.patch.object(
            cmd_skill.Party.Heroes, "GetHeroAgentIDByPartyPosition", return_value=4242
        ), mock.patch.object(cmd_skill.Party.Heroes, "UseSkill") as use, mock.patch.object(
            cmd_skill, "Agent_ConvertID", return_value=0
        ):
            # Note the difference from UseSkill: a zero target is allowed here, because GwAu3's own
            # default for this function is 0 and it makes no test on it.
            self.assertTrue(cmd_skill.Skill_UseHeroSkill(1, 5, 0))
            use.assert_called_once_with(4242, 5, 0)

    def test_the_merchant_and_priest_calls_pass_the_skill_id_through(self) -> None:
        with mock.patch.object(cmd_skill.Player, "BuySkill") as buy:
            cmd_skill.Skill_BuySkillByID(1062)
            buy.assert_called_once_with(1062)

        with mock.patch.object(cmd_skill.Player, "UnlockBalthazarSkill") as unlock:
            cmd_skill.Skill_UnlockSkillByID(1062)
            unlock.assert_called_once_with(1062)


if __name__ == "__main__":
    unittest.main()
