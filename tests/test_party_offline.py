"""Offline tests for the ported ``Party`` surface.

The first test is the important one: it asserts that every member of Reforged's
``Py4GWCoreLib/Party.py``, including its four nested namespaces, exists here with
the same spelling. It fails the moment a member is dropped, which is the whole
point of "port the class" -- nothing else in the suite would notice a missing
member.

The rest pin the members whose answer is a documented constant, so a later change
cannot quietly turn them into something else.
"""

from __future__ import annotations

import unittest

from py4gw.party import HERO_NAME_TO_ID, Hero, HeroType, Party

#: Every member of Reforged's ``Party`` class, transcribed from that file.
REFORGED_PARTY_MEMBERS = (
    "party_instance",
    "GetPartyID",
    "GetPartyLeaderID",
    "GetOwnPartyNumber",
    "GetPartyTarget",
    "GetPlayers",
    "GetHeroes",
    "GetHenchmen",
    "GetOthers",
    "IsHardModeUnlocked",
    "IsHardMode",
    "IsNormalMode",
    "GetPartySize",
    "GetPlayerCount",
    "GetHeroIndex",
    "GetHeroCount",
    "GetHenchmanCount",
    "IsPartyDefeated",
    "IsPartyLoaded",
    "GetPartyMorale",
    "IsPlayerLoaded",
    "IsPartyLeader",
    "SetTickasToggle",
    "IsAllTicked",
    "IsPlayerTicked",
    "SetTicked",
    "ToggleTicked",
    "SetHardMode",
    "SetNormalMode",
    "SearchParty",
    "SearchPartyCancel",
    "SearchPartyReply",
    "RespondToPartyRequest",
    "ReturnToOutpost",
    "LeaveParty",
)

REFORGED_PLAYERS_MEMBERS = (
    "GetAgentIDByLoginNumber",
    "GetPlayerNameByLoginNumber",
    "GetPartyNumberFromLoginNumber",
    "GetLoginNumberByAgentID",
    "InvitePlayer",
    "KickPlayer",
)

REFORGED_HEROES_MEMBERS = (
    "GetHeroAgentIDByPartyPosition",
    "GetHeroIDByAgentID",
    "GetHeroIDByPartyPosition",
    "GetHeroIdByName",
    "GetHeroNameById",
    "GetNameByAgentID",
    "GetHeroPartyPositionByAgentID",
    "GetTargetIDByAgentID",
    "AddHero",
    "AddHeroByName",
    "KickHero",
    "KickHeroByName",
    "KickAllHeroes",
    "UseSkill",
    "SetSkillAIEnabled",
    "FlagHero",
    "FlagAllHeroes",
    "UnflagHero",
    "UnflagAllHeroes",
    "IsHeroFlagged",
    "IsAllFlagged",
    "GetAllFlag",
    "SetHeroBehavior",
)

REFORGED_HENCHMEN_MEMBERS = ("AddHenchman", "KickHenchman")

REFORGED_PETS_MEMBERS = (
    "SetPetBehavior",
    "GetPetBehavior",
    "GetPetInfo",
    "GetPetID",
)

NESTED = (
    ("Players", REFORGED_PLAYERS_MEMBERS),
    ("Heroes", REFORGED_HEROES_MEMBERS),
    ("Henchmen", REFORGED_HENCHMEN_MEMBERS),
    ("Pets", REFORGED_PETS_MEMBERS),
)

#: Members Reforged refuses to run: they need code inside the client.
NOT_PORTED_MEMBERS = (
    "party_instance",
    "SetHardMode",
    "SetNormalMode",
    "SearchParty",
    "SearchPartyCancel",
    "SearchPartyReply",
    "RespondToPartyRequest",
    "ReturnToOutpost",
    "LeaveParty",
    "SetTickasToggle",
    "SetTicked",
    "ToggleTicked",
)

#: Nested members Reforged refuses to run, with a call of the right arity.
DISABLED_NESTED_CALLS = (
    ("Players.GetPlayerNameByLoginNumber", lambda: Party.Players.GetPlayerNameByLoginNumber(0)),
    ("Players.InvitePlayer", lambda: Party.Players.InvitePlayer(0)),
    ("Players.KickPlayer", lambda: Party.Players.KickPlayer(0)),
    ("Heroes.AddHero", lambda: Party.Heroes.AddHero(0)),
    ("Heroes.AddHeroByName", lambda: Party.Heroes.AddHeroByName("")),
    ("Heroes.KickHero", lambda: Party.Heroes.KickHero(0)),
    ("Heroes.KickHeroByName", lambda: Party.Heroes.KickHeroByName("")),
    ("Heroes.KickAllHeroes", Party.Heroes.KickAllHeroes),
    ("Heroes.UseSkill", lambda: Party.Heroes.UseSkill(0, 1, 0)),
    ("Heroes.SetSkillAIEnabled", lambda: Party.Heroes.SetSkillAIEnabled(0, 1, True)),
    ("Heroes.FlagHero", lambda: Party.Heroes.FlagHero(0, 0.0, 0.0)),
    ("Heroes.FlagAllHeroes", lambda: Party.Heroes.FlagAllHeroes(0.0, 0.0)),
    ("Heroes.UnflagHero", lambda: Party.Heroes.UnflagHero(0)),
    ("Heroes.UnflagAllHeroes", Party.Heroes.UnflagAllHeroes),
    ("Heroes.SetHeroBehavior", lambda: Party.Heroes.SetHeroBehavior(0, 0)),
    ("Henchmen.AddHenchman", lambda: Party.Henchmen.AddHenchman(0)),
    ("Henchmen.KickHenchman", lambda: Party.Henchmen.KickHenchman(0)),
    ("Pets.SetPetBehavior", lambda: Party.Pets.SetPetBehavior(0, 0)),
)


class SurfaceParityTests(unittest.TestCase):
    """Verify the whole Reforged Party surface is present."""

    def test_the_transcribed_surface_is_the_source_surface(self) -> None:
        """Cross-check the hand-written lists against ``Party.py`` itself.

        The lists in this module were transcribed by hand, so they could agree
        with a wrong port. This reads the source file and counts its ``def``
        lines at the two indentations that matter: four spaces for the ``Party``
        class and eight for the four nested namespaces. Three members are spelled
        with a space before the parenthesis, which is why the pattern allows it.
        """

        import re
        from pathlib import Path

        source = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Party.py")
        if not source.exists():
            self.skipTest("The Reforged source checkout is not present.")

        main: list[str] = []
        nested: dict[str, list[str]] = {}
        current: str | None = None
        for line in source.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^        def (\w+)\s*\(", line)
            if match and current:
                nested[current].append(match.group(1))
                continue
            match = re.match(r"^    def (\w+)\s*\(", line)
            if match:
                main.append(match.group(1))
                continue
            match = re.match(r"^    class (\w+):", line)
            if match:
                namespace = match.group(1)
                nested[namespace] = []
                current = namespace

        self.assertEqual(main, list(REFORGED_PARTY_MEMBERS))
        for namespace, members in NESTED:
            with self.subTest(namespace=namespace):
                self.assertEqual(nested.get(namespace), list(members))

    def test_every_reforged_party_member_exists(self) -> None:
        """Keep the port from dropping a member Reforged scripts call."""

        missing = [n for n in REFORGED_PARTY_MEMBERS if not hasattr(Party, n)]
        self.assertEqual(missing, [], f"missing Party members: {missing}")

    def test_every_nested_namespace_and_member_exists(self) -> None:
        """Keep all four nested namespaces and their members."""

        for namespace, members in NESTED:
            with self.subTest(namespace=namespace):
                nested = getattr(Party, namespace, None)
                self.assertIsNotNone(nested, f"Party.{namespace} is missing")
                assert nested is not None
                missing = [n for n in members if not hasattr(nested, n)]
                self.assertEqual(
                    missing, [], f"missing Party.{namespace} members: {missing}"
                )

    def test_members_are_staticmethods(self) -> None:
        """Match Reforged, where every namespace member is a staticmethod."""

        for name in REFORGED_PARTY_MEMBERS:
            with self.subTest(member=name):
                self.assertIsInstance(
                    vars(Party).get(name),
                    staticmethod,
                    f"Party.{name} must be a staticmethod to match Reforged",
                )

    def test_no_public_member_beyond_the_source(self) -> None:
        """Keep the public surface from growing past Reforged's."""

        declared: set[str] = set(REFORGED_PARTY_MEMBERS)
        for namespace, members in NESTED:
            declared.add(namespace)
            declared.update(members)
        actual = {n for n in vars(Party) if not n.startswith("_")}
        for namespace, _ in NESTED:
            actual |= {
                n
                for n in vars(getattr(Party, namespace))
                if not n.startswith("_")
            }
        self.assertEqual(actual - declared, set())


class DisabledMemberTests(unittest.TestCase):
    """Verify the members that cannot work externally refuse clearly."""

    def test_actions_raise_not_implemented(self) -> None:
        """Refuse each action member without touching a client."""

        calls = {
            "party_instance": Party.party_instance,
            "SetHardMode": Party.SetHardMode,
            "SetNormalMode": Party.SetNormalMode,
            "SetTickasToggle": lambda: Party.SetTickasToggle(True),
            "SetTicked": lambda: Party.SetTicked(True),
            "ToggleTicked": Party.ToggleTicked,
            "SearchParty": lambda: Party.SearchParty(0, ""),
            "SearchPartyCancel": Party.SearchPartyCancel,
            "SearchPartyReply": lambda: Party.SearchPartyReply(True),
            "RespondToPartyRequest": lambda: Party.RespondToPartyRequest(1, True),
            "ReturnToOutpost": Party.ReturnToOutpost,
            "LeaveParty": Party.LeaveParty,
        }
        for name, call in calls.items():
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(f"Party.{name}", str(caught.exception))

    def test_nested_actions_raise_not_implemented(self) -> None:
        """Refuse every nested action member too."""

        for label, call in DISABLED_NESTED_CALLS:
            with self.subTest(member=label):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(label, str(caught.exception))

    def test_not_ported_names_are_real_members(self) -> None:
        """Keep the disabled list honest: each name must exist."""

        for name in NOT_PORTED_MEMBERS:
            with self.subTest(member=name):
                self.assertTrue(hasattr(Party, name))
        for label, _ in DISABLED_NESTED_CALLS:
            with self.subTest(member=label):
                namespace, member = label.split(".")
                self.assertTrue(hasattr(getattr(Party, namespace), member))


class DocumentedConstantTests(unittest.TestCase):
    """Verify members whose source answer is a constant cannot drift.

    ``GetOthers`` is deliberately not here. The binding's own ``others`` vector
    is never populated, but the game's ``PartyInfo::others`` array is, and
    Reforged reads that one -- so ``GetOthers`` returns live data, asserted in
    ``test_party.py`` against the party context.
    """

    def test_hero_name_lookups_report_the_unset_field(self) -> None:
        """``Hero::GetName`` reads a field no constructor assigns."""

        self.assertEqual(Hero(1).GetName(), "")
        self.assertEqual(Hero("Norgu").GetName(), "")
        self.assertEqual(Hero(1).GetProfession(), 0)


class HeroTableTests(unittest.TestCase):
    """Verify the ported hero name table and id clamping."""

    def test_name_table_matches_the_native_source(self) -> None:
        """Keep the table aligned with ``kHeroNameMap``, including its gaps."""

        self.assertEqual(len(HERO_NAME_TO_ID), 38)
        self.assertIs(HERO_NAME_TO_ID[""], HeroType.None_)
        self.assertIs(HERO_NAME_TO_ID["Norgu"], HeroType.Norgu)
        self.assertIs(HERO_NAME_TO_ID["M.O.X."], HeroType.MOX)
        self.assertIs(HERO_NAME_TO_ID["Zei Ri"], HeroType.ZeiRi)
        # The source table stops at Zei Ri; these two hero ids have no name.
        self.assertNotIn("Devona", HERO_NAME_TO_ID)
        self.assertNotIn("GhostOfAlthea", HERO_NAME_TO_ID)

    def test_enum_values_match_reforged(self) -> None:
        """Keep the ids aligned with ``Hero_enums.py``."""

        self.assertEqual(int(HeroType.None_), 0)
        self.assertEqual(int(HeroType.Norgu), 1)
        self.assertEqual(int(HeroType.ZeiRi), 37)
        self.assertEqual(int(HeroType.Devona), 38)
        self.assertEqual(int(HeroType.GhostOfAlthea), 39)

    def test_hero_resolves_from_id_and_name(self) -> None:
        """Resolve both constructor forms the binding offers."""

        self.assertEqual(Hero(3).GetID(), 3)
        self.assertEqual(Hero("Tahlkora").GetID(), 3)
        self.assertEqual(Hero(HeroType.Koss).GetID(), 6)

    def test_hero_rejects_out_of_range_and_unknown(self) -> None:
        """Match the source's clamp and its unknown-name fallback."""

        self.assertEqual(Hero(999).GetID(), 0)
        self.assertEqual(Hero(-1).GetID(), 0)
        self.assertEqual(Hero("Nobody").GetID(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
