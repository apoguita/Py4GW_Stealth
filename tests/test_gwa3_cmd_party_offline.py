"""Offline tests for `py4gw/gwa3/cmd_party.py`.

No client and no elevation. What is being established is the layer's *routing contract*, which is the
part that can be wrong in a way no caller can see:

* each function reaches the ported member this project's route map records for it;
* the argument GwAu3's own packet carries is the argument the ported member gets -- and the two hero
  spellings (`Party_CommandHero` takes a party position, `Heroes.FlagHero` takes an agent id) do not
  get crossed;
* the return shapes are GwAu3's, including the two that differ from the obvious reading:
  `Party_DisableHeroSkill` answers `True` unconditionally and `Party_EnableHeroSkill` answers nothing;
* every refused function refuses, naming its rule, rather than reporting an action that never
  happened.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import cmd_party


class PartyActionRouteTests(unittest.TestCase):
    """Every routed function, against a mocked ported surface."""

    def setUp(self) -> None:
        self.heroes = mock.MagicMock()
        self.henchmen = mock.MagicMock()
        self.party = mock.MagicMock()
        self.heroes.GetHeroAgentIDByPartyPosition.return_value = 4242
        patches = [
            mock.patch.object(cmd_party.Party, "Heroes", self.heroes),
            mock.patch.object(cmd_party.Party, "Henchmen", self.henchmen),
            mock.patch.object(cmd_party.Party, "SetTicked", self.party.SetTicked),
            mock.patch.object(cmd_party.Party, "LeaveParty", self.party.LeaveParty),
            mock.patch.object(
                cmd_party.Party, "RespondToPartyRequest", self.party.RespondToPartyRequest
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_hero_and_henchman_calls_keep_gwau3s_argument(self) -> None:
        self.assertTrue(cmd_party.Party_AddHero(7))
        self.heroes.AddHero.assert_called_once_with(7)

        self.assertTrue(cmd_party.Party_KickHero(9))
        self.heroes.KickHero.assert_called_once_with(9)

        self.assertTrue(cmd_party.Party_KickAllHeroes())
        self.heroes.KickAllHeroes.assert_called_once_with()

        self.assertTrue(cmd_party.Party_AddNpc(3))
        self.henchmen.AddHenchman.assert_called_once_with(3)

        self.assertTrue(cmd_party.Party_KickNpc(4))
        self.henchmen.KickHenchman.assert_called_once_with(4)

    def test_a_hero_number_resolves_to_an_agent_id(self) -> None:
        """GwAu3's packet carries the agent id, so the route must resolve the position first."""

        self.assertTrue(cmd_party.Party_CommandHero(2, 100.0, 200.0))
        self.heroes.GetHeroAgentIDByPartyPosition.assert_called_with(2)
        self.heroes.FlagHero.assert_called_once_with(4242, 100.0, 200.0)

        self.heroes.reset_mock()
        self.heroes.GetHeroAgentIDByPartyPosition.return_value = 4242
        self.assertTrue(cmd_party.Party_CancelHero(1))
        # 0x7F800000 is HUGE_VALF: GwAu3's own "no position" literal, the same as UnflagHero uses.
        self.heroes.FlagHero.assert_called_once_with(4242, float(0x7F800000), float(0x7F800000))
        # and NOT UnflagHero, whose argument is a hero id resolved through another function.
        self.heroes.UnflagHero.assert_not_called()

    def test_the_all_party_forms(self) -> None:
        self.assertTrue(cmd_party.Party_CommandAll(1.5, 2.5))
        self.heroes.FlagAllHeroes.assert_called_once_with(1.5, 2.5)

        self.assertTrue(cmd_party.Party_CancelAll())
        self.heroes.UnflagAllHeroes.assert_called_once_with()

    def test_aggression_goes_through_unchanged(self) -> None:
        self.assertTrue(cmd_party.Party_SetHeroAggression(1, 2))
        self.heroes.SetHeroBehavior.assert_called_once_with(4242, 2)

    def test_the_tick_takes_the_state_not_a_flip(self) -> None:
        self.assertTrue(cmd_party.Party_Tick(False))
        self.party.SetTicked.assert_called_once_with(False)
        self.assertFalse(hasattr(self.party, "ToggleTicked") and self.party.ToggleTicked.called)

    def test_leave_group_kicks_before_it_leaves(self) -> None:
        """The order is GwAu3's own and it decides who is still in the party when it dissolves."""

        order: list[str] = []
        self.heroes.KickAllHeroes.side_effect = lambda: order.append("kick")
        self.party.LeaveParty.side_effect = lambda: order.append("leave")

        self.assertTrue(cmd_party.Party_LeaveGroup(True))
        self.assertEqual(order, ["kick", "leave"])

        order.clear()
        self.assertTrue(cmd_party.Party_LeaveGroup(False))
        self.assertEqual(order, ["leave"])

    def test_the_skill_state_calls_take_the_state_explicitly(self) -> None:
        self.heroes.SetSkillAIEnabled.return_value = True

        # GwAu3's Party_EnableHeroSkill has no Return at all, so the layer answers nothing.
        self.assertIsNone(cmd_party.Party_EnableHeroSkill(1, 5))
        self.heroes.SetSkillAIEnabled.assert_called_once_with(4242, 5, True)

        self.heroes.reset_mock()
        self.heroes.GetHeroAgentIDByPartyPosition.return_value = 4242
        # GwAu3's Party_DisableHeroSkill returns True unconditionally -- the guard decides whether the
        # client is called, not what is answered.
        self.assertTrue(cmd_party.Party_DisableHeroSkill(1, 5))
        self.heroes.SetSkillAIEnabled.assert_called_once_with(4242, 5, False)

    def test_the_invitation_answers(self) -> None:
        cmd_party.Party_AcceptInvitation(11)
        self.party.RespondToPartyRequest.assert_called_once_with(11, True)

        self.party.RespondToPartyRequest.reset_mock()
        cmd_party.Party_RejectInvitation(12)
        self.party.RespondToPartyRequest.assert_called_once_with(12, False)


class PartyRefusalTests(unittest.TestCase):
    """Every refused function refuses, and says which rule it refuses by."""

    def test_every_refused_function_raises_with_a_reason(self) -> None:
        cases = {
            "Party_LockHeroTarget": (1, 0),
            "Party_GetIsHeroSkillDisabled": (1, 5),
            "Party_ToggleHeroSkillState": (1, 5),
            "Party_AddPlayer": (2,),
            "Party_KickPlayer": (2,),
            "Party_KickInvitedPlayer": (3,),
        }
        for name, args in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_party, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_Cmd_Party.au3", message)
                self.assertIn("py4gw/", message)

    def test_the_declared_surface_is_the_sources_own(self) -> None:
        """22 functions, which is what `GwAu3_Cmd_Party.au3` declares."""

        self.assertEqual(len(cmd_party.__all__), 22)
        for name in cmd_party.__all__:
            self.assertTrue(callable(getattr(cmd_party, name)), name)


if __name__ == "__main__":
    unittest.main()
