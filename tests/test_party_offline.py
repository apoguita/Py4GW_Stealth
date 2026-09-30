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

import struct
import unittest
from typing import Any
from unittest import mock

from py4gw import party as party_module
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

#: Members Reforged refuses to run: they need code inside the client. **Only the artifact is left**
#: (round 6, 2026-09-30): every other member of the class answers, and `party_instance` cannot — it
#: returns native's in-process `PyParty` object, which an external port has no counterpart for. It is
#: the third member of that kind in this project, with `Player.player_instance` and
#: `Agent.GetProfessionsTexturePaths`.
NOT_PORTED_MEMBERS = ("party_instance",)

#: Nested members Reforged refuses to run, with a call of the right arity. **Empty as of round 6**:
#: the last four landed (`Players.GetPlayerNameByLoginNumber`, `Players.InvitePlayer`,
#: `Players.KickPlayer`, `Heroes.UseSkill`), and `DISABLED_NESTED_CALLS` stays here so the shape of the
#: check does not change when a member has to be taken out again.
DISABLED_NESTED_CALLS: tuple[tuple[str, Any], ...] = ()


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

    def test_the_return_shape_of_every_member_is_the_sources(self) -> None:
        """Does each member hand a value back? Compare the two ASTs, with five recorded exceptions.

        The surface test above checks names and nesting; this checks the other half of a call-site
        contract. A member that answers ``None`` where the source returns a bool — or a value where the
        source returns nothing — is a caller's ``if`` behaving differently, and it is exactly what
        slipped once already: `SearchPartyReply` was written without its returned bool until round 3
        checked the source's own ``return``.

        **The five differences are all accounted for**, and transcribed here so a sixth cannot appear
        unnoticed:

        * `IsPlayerLoaded` — Reforged's body is ``pass``, and the port implements the native function
          its docstring names (§ Findings of ``PARTY_PORT.md``);
        * `party_instance` — the recorded artifact: it raises rather than returning native's object;
        * `LeaveParty`, `Players.InvitePlayer`, `Players.KickPlayer` — native's own guards
          (``return false`` in ``party_methods.cpp``) are what the port carries, because it cannot call
          the binding; every path still answers ``None`` at the call site, which is what Reforged's
          ungarded bodies answer too.
        """

        import ast
        from pathlib import Path

        source_path = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Party.py")
        if not source_path.exists():
            self.skipTest("The Reforged source checkout is not present.")

        def shapes(path: Path) -> dict[str, str]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            klass = next(
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == "Party"
            )
            found: dict[str, str] = {}

            def shape(node: ast.FunctionDef) -> str:
                if any(
                    isinstance(statement, ast.Return) and statement.value is not None
                    for statement in ast.walk(node)
                ):
                    return "value"
                if any(
                    isinstance(statement, ast.Return) and statement.value is None
                    for statement in ast.walk(node)
                ):
                    return "none"
                return "falls-off"

            def walk(node: ast.ClassDef, prefix: str) -> None:
                for child in node.body:
                    if isinstance(child, ast.ClassDef):
                        walk(child, f"{prefix}{child.name}.")
                        continue
                    if isinstance(child, ast.FunctionDef) and not child.name.startswith("_"):
                        found[f"{prefix}{child.name}"] = shape(child)

            walk(klass, "")
            return found

        theirs = shapes(source_path)
        mine = shapes(Path(__file__).resolve().parent.parent / "py4gw" / "party.py")

        expected = {
            "IsPlayerLoaded": ("falls-off", "value"),
            "party_instance": ("value", "falls-off"),
            "LeaveParty": ("falls-off", "none"),
            "Players.InvitePlayer": ("falls-off", "none"),
            "Players.KickPlayer": ("falls-off", "none"),
        }
        found = {
            name: (theirs[name], mine[name])
            for name in sorted(set(theirs) & set(mine))
            if theirs[name] != mine[name]
        }
        self.assertEqual(found, expected)

    def test_the_declaration_order_is_the_sources_own(self) -> None:
        """**Same order**, not just the same set: compare this module's member sequence to the source's.

        The porting rule is names, nesting **and order**; the tests above check the first two, and
        round 17 found the third was never checked at all — the port had grouped `Party`'s members by
        subject (identity, state, actions) and `Players`, `Heroes` and `Pets` each had one member out
        of place. `tools/reorder_party.py` moved them, and this keeps them there: a member inserted in
        the wrong place, or a namespace reordered, fails here.

        Members the source does not declare — the port's own private helpers — are skipped, since the
        source has nothing to order them by; they sit first in each class.
        """

        import ast
        from pathlib import Path

        source_path = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Party.py")
        if not source_path.exists():
            self.skipTest("The Reforged source checkout is not present.")

        def order(path: Path) -> dict[str, list[str]]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            klass = next(
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == "Party"
            )
            found: dict[str, list[str]] = {
                "": [child.name for child in klass.body if isinstance(child, ast.FunctionDef)]
            }
            for child in klass.body:
                if isinstance(child, ast.ClassDef):
                    found[child.name] = [
                        grandchild.name
                        for grandchild in child.body
                        if isinstance(grandchild, ast.FunctionDef)
                    ]
            return found

        theirs = order(source_path)
        mine = order(Path(__file__).resolve().parent.parent / "py4gw" / "party.py")

        for namespace, names in theirs.items():
            with self.subTest(namespace=namespace or "Party"):
                self.assertEqual(
                    [name for name in mine.get(namespace, []) if not name.startswith("_")],
                    names,
                )

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
        """Refuse each action member without touching a client.

        The party-button family used to be in this list: ``SearchPartyCancel``,
        ``SearchPartyReply`` and ``LeaveParty`` are built now (``PartyButtonTests`` drives them
        against a stand-in client), and so is ``ReturnToOutpost`` (``ReturnToOutpostTests``), so what
        is left here is the two whose call site the port has not built yet, each naming what it still
        needs.
        """

        calls = {
            "party_instance": Party.party_instance,
        }
        for name, call in calls.items():
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(f"Party.{name}", str(caught.exception))

    def test_the_members_that_now_answer_do_not_raise(self) -> None:
        """The tick group and the two difficulty members answer; nothing here is a refusal.

        They are called **with no client attached**, which is the point: none of them reaches the
        client through a path that has to be connected for the call itself to be well-formed —
        ``SetTickasToggle`` writes a flag, ``SetTicked`` and ``RespondToPartyRequest`` do nothing at
        all (the source's own bodies), and the two difficulty members return before calling anything
        because their guards are not met.
        """

        self.assertIsNone(Party.SetTickasToggle(True))
        self.assertTrue(party_module.tick_work_as_toggle)
        self.assertIsNone(Party.SetTickasToggle(False))
        self.assertFalse(party_module.tick_work_as_toggle)

        self.assertIsNone(Party.SetTicked(True))
        self.assertIsNone(Party.RespondToPartyRequest(7, True))

        # The difficulty guards read the context, which is not there without a client... so they
        # refuse to *run*, they do not refuse to *exist*: any exception is the connection's, not a
        # ``NotImplementedError``.
        for call in (Party.SetHardMode, Party.SetNormalMode):
            with self.subTest(member=call.__name__):
                try:
                    call()
                except NotImplementedError as error:  # pragma: no cover - the assertion below
                    self.fail(f"{call.__name__} still refuses: {error}")
                except RuntimeError:
                    pass  # no client: the read refused before the guard could be satisfied

    def test_set_ticked_reaches_no_client_state_and_that_is_the_source(self) -> None:
        """*Finding*: the source's own body writes to an object it throws away.

        ``Party.SetTicked`` is ``Party.party_instance().tick.SetTicked(ticked)``, and
        ``party_instance()`` returns a **new** ``PyParty`` every call (``Party.py:13-18``) whose
        ``PartyTick`` is the object's own bool (``party_bindings.cpp:88-92``). So the member is a
        no-op in the source — this pins that the port did not "fix" it into a client call, which
        would be behaviour neither source has.
        """

        import ast
        from pathlib import Path

        source = (
            Path(__file__).resolve().parent.parent / "py4gw" / "party.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "SetTicked":
                found = node
        self.assertIsNotNone(found, "SetTicked is declared")
        body = [
            statement
            for statement in found.body  # type: ignore[union-attr]
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ]
        self.assertEqual(
            body,
            [],
            "SetTicked's body must be its docstring alone: the source's own body has no effect",
        )

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

    def test_the_raising_set_is_the_recorded_artifact_alone(self) -> None:
        """The whole surface answers except `party_instance` — derived from the module's own AST.

        The lists above are transcribed, so they can agree with a wrong port. This reads
        ``py4gw/party.py`` and collects every member whose body still raises `_unported`, then
        compares that set with the one this project has recorded: native's `PyParty` object, which
        an external port has no counterpart for. A member that starts raising again fails here, and
        so does a member that is dropped from `NOT_PORTED_MEMBERS` without being built.
        """

        import ast
        from pathlib import Path

        source = (
            Path(__file__).resolve().parent.parent / "py4gw" / "party.py"
        ).read_text(encoding="utf-8")
        party = next(
            node
            for node in ast.parse(source).body
            if isinstance(node, ast.ClassDef) and node.name == "Party"
        )

        def unported(klass: ast.ClassDef, prefix: str = "") -> set[str]:
            found: set[str] = set()
            for node in klass.body:
                if isinstance(node, ast.ClassDef):
                    found |= unported(node, f"{prefix}{node.name}.")
                    continue
                if not isinstance(node, ast.FunctionDef):
                    continue
                for statement in ast.walk(node):
                    if (
                        isinstance(statement, ast.Raise)
                        and isinstance(statement.exc, ast.Call)
                        and getattr(statement.exc.func, "id", "") == "_unported"
                    ):
                        found.add(f"{prefix}{node.name}")
            return found

        self.assertEqual(unported(party), {"party_instance"})


class PartyReadSourceCallTests(unittest.TestCase):
    """The two reads round 10 corrected: `GetPartyLeaderID` and `GetPartyTarget`.

    Both were answering the right *values* while doing the wrong *thing*, which is why they are pinned
    here by the calls they make rather than by what they return:

    * `GetPartyLeaderID` carried an `if not players: return 0` the source does not have — the source's
      line is ``players[0]``, so an empty party raises there and must raise here;
    * `GetPartyTarget` called ``Party.IsPlayerLoaded`` and ``Player.IsAgentIDValid`` where the source
      calls ``Party.IsPartyLoaded`` and ``Agent.IsValid`` — different members, nearly the same answers.
    """

    class _Member:
        def __init__(self, login_number: int, called_target_id: int = 0) -> None:
            self.login_number = login_number
            self.called_target_id = called_target_id

    def _patch(self, players: list[Any], *, party_loaded: bool = True) -> None:
        party = mock.Mock()
        party.players = players
        context = mock.Mock()
        context.player_party = party
        patches = (
            mock.patch.object(Party, "_context", staticmethod(lambda: context)),
            mock.patch.object(Party, "IsPartyLoaded", staticmethod(lambda: party_loaded)),
            mock.patch.object(
                Party.Players,
                "GetAgentIDByLoginNumber",
                staticmethod(lambda login: 1000 + int(login)),
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_leader_is_the_first_entry_and_an_empty_party_raises(self) -> None:
        """``leader = players[0]`` — the source's own line, its own assumption included."""

        self._patch([self._Member(48), self._Member(49)])
        self.assertEqual(Party.GetPartyLeaderID(), 1048)

        self._patch([])
        with self.assertRaises(IndexError):
            Party.GetPartyLeaderID()

    def test_the_party_target_reads_the_first_entries_called_target(self) -> None:
        """``target = players[0].called_target_id``, accepted only when ``Agent.IsValid`` says so."""

        from py4gw.agent import Agent

        self._patch([self._Member(48, called_target_id=777)])
        with mock.patch.object(Agent, "IsValid", staticmethod(lambda agent_id: True)):
            self.assertEqual(Party.GetPartyTarget(), 777)
        with mock.patch.object(Agent, "IsValid", staticmethod(lambda agent_id: False)):
            self.assertEqual(
                Party.GetPartyTarget(), 0, "an agent that does not resolve is the source's own 0"
            )

    def test_the_party_target_is_gated_on_the_partys_own_loaded_member(self) -> None:
        """The source's guard is `Party.IsPartyLoaded`, not `Party.IsPlayerLoaded`."""

        self._patch([self._Member(48, called_target_id=777)], party_loaded=False)

        self.assertEqual(Party.GetPartyTarget(), 0)
        self.assertEqual(
            Party.IsPartyLoaded(), False, "the fixture answers the member the source calls"
        )


class _PartyBridge:
    """The stand-in bridge: the block's data region, and what was placed in it."""

    #: Where the region's words start, so a "region offset" has an address to answer with.
    REGION_BASE = 0x71000000

    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []

    def write_data(self, offset: int, payload: bytes) -> int:
        self.writes.append((int(offset), bytes(payload)))
        return self.REGION_BASE + int(offset)

    def words_at(self, offset: int) -> list[int]:
        """Return the words written at one region offset, or an empty list."""

        for written_offset, payload in self.writes:
            if written_offset == offset:
                return [
                    struct.unpack_from("<I", payload, index * 4)[0]
                    for index in range(len(payload) // 4)
                ]
        return []


class _PartyBridgeClient:
    """The stand-in client the party-button members are driven against."""

    def __init__(self, resolvable: bool = True) -> None:
        self.bridge = _PartyBridge()
        self.resolvable = resolvable
        self.calls: list[dict[str, Any]] = []

    def resolves(self, name: str) -> bool:
        return self.resolvable

    def call_function(
        self,
        name: str,
        form: Any,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
    ) -> None:
        self.calls.append(
            {
                "name": name,
                "form": form,
                "address": int(arg1),
                "edx": int(arg2),
                "wparam_address": int(arg3),
            }
        )


class _FlagClient:
    """The stand-in client the flag members are driven against.

    These four members call one function each and hand it **words** only — the ``GamePos`` record is
    built by the payload from the command's own args — so what this fixture has to carry is the
    resolver question, the call, and the words it was given.
    """

    def __init__(self, resolvable: bool = True) -> None:
        self.resolvable = resolvable
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []

    def resolves(self, name: str) -> bool:
        return self.resolvable

    def call_function(
        self,
        name: str,
        form: Any,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
    ) -> None:
        self.calls.append((name, int(form), (arg1, arg2, arg3, arg4, arg5)))


class PartyFlagTests(unittest.TestCase):
    """The flag group: native's ``flag_hero_agent`` / ``flag_all`` and the unflag sentinel.

    ``GW::GamePos`` is ``{float x; float y; uint32_t zplane;}`` (``game_pos.h:255-267``), and both
    forms the payload emits build that record in the payload's own frame from the command's words, so
    the two coordinates travel as their **bit patterns** (``shared_block.float_bits``). The tests
    below therefore check the words, the form and the guards — the three things the source decides.
    """

    #: The agent id `flag_hero_agent`'s second guard compares against (`_controlled_character_id`).
    CONTROLLED_ID = 999

    def setUp(self) -> None:
        from py4gw.player import Player

        self.client = _FlagClient()
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The guard reads the controlled character through the ported member, so it is answered here
        # rather than through a stand-in: what is under test is the guard's **comparison**, and the
        # member that produces the id has its own tests.
        player = mock.patch.object(
            Player, "GetAgentID", staticmethod(lambda: self.CONTROLLED_ID)
        )
        player.start()
        self.addCleanup(player.stop)

    def call(self) -> tuple[str, int, tuple[int, ...]]:
        self.assertEqual(len(self.client.calls), 1, "one call per member")
        return self.client.calls[0]

    def test_flag_hero_hands_the_agent_word_and_the_two_floats(self) -> None:
        """``PyParty::FlagHero`` → ``flag_hero_agent(agent_id, GamePos(x, y))`` (``:359-361``)."""

        from py4gw.game_thread.shared_block import CallForm, float_bits

        self.assertIsNone(Party.Heroes.FlagHero(5, 1234.5, -678.25))

        name, form, args = self.call()
        self.assertEqual(name, party_module.FLAG_HERO_AGENT_FUNC)
        self.assertEqual(form, int(CallForm.U32_FLOAT_PTR))
        self.assertEqual(
            args,
            (5, float_bits(1234.5), float_bits(-678.25), float_bits(0.0), 0),
            "the word, then x, y and GamePos's own zplane",
        )

    def test_flag_hero_refuses_zero_and_the_controlled_character(self) -> None:
        """Native's two guards (``party_methods.cpp:328-329``), and neither is this port's."""

        from py4gw.player import Player

        self.assertIsNone(Party.Heroes.FlagHero(0, 1.0, 2.0))
        self.assertEqual(self.client.calls, [], "`if (agent_id == 0) return false;`")

        with mock.patch.object(Player, "GetAgentID", staticmethod(lambda: 21)):
            self.assertIsNone(Party.Heroes.FlagHero(21, 1.0, 2.0))
        self.assertEqual(
            self.client.calls, [], "`if (agent_id == agent::GetControlledCharacterId()) return false;`"
        )
    def test_flag_all_heroes_is_the_pointer_form_with_no_agent_word(self) -> None:
        """``flag_all(GamePos(x, y))``: ``FLOAT_PTR``, and native's own ternary (``:338-340``)."""

        from py4gw.game_thread.shared_block import CallForm, float_bits

        self.assertIsNone(Party.Heroes.FlagAllHeroes(10.5, 20.25))

        name, form, args = self.call()
        self.assertEqual(name, party_module.FLAG_ALL_FUNC)
        self.assertEqual(form, int(CallForm.FLOAT_PTR))
        self.assertEqual(args, (float_bits(10.5), float_bits(20.25), float_bits(0.0), 0, 0))

    def test_unflag_hero_is_the_index_form_with_the_sentinel(self) -> None:
        """``unflag_hero(index)`` = ``flag_hero(index, GamePos(HUGE_VALF, HUGE_VALF, 0))``.

        The argument reaches ``agent::GetHeroAgentID`` (``agent_methods.cpp:240-247``) — the port's
        ``GetHeroAgentIDByPartyPosition`` — before ``flag_hero_agent`` is called, which is why the
        agent word here is the one that walk answered and not the caller's index.
        """

        from py4gw.game_thread.shared_block import CallForm, float_bits

        with mock.patch.object(
            Party.Heroes, "GetHeroAgentIDByPartyPosition", staticmethod(lambda index: 20 + index)
        ):
            self.assertIsNone(Party.Heroes.UnflagHero(1))

        name, form, args = self.call()
        self.assertEqual(name, party_module.FLAG_HERO_AGENT_FUNC)
        self.assertEqual(form, int(CallForm.U32_FLOAT_PTR))
        self.assertEqual(
            args,
            (21, float_bits(party_module.HUGE_VALF), float_bits(party_module.HUGE_VALF), float_bits(0.0), 0),
            "the sentinel is both coordinates, and the agent word is the resolved one",
        )

    def test_unflag_all_heroes_is_the_sentinel_through_flag_all(self) -> None:
        """``return flag_all(GamePos(HUGE_VALF, HUGE_VALF, 0));`` (``:342-344``)."""

        from py4gw.game_thread.shared_block import CallForm, float_bits

        self.assertIsNone(Party.Heroes.UnflagAllHeroes())

        name, form, args = self.call()
        self.assertEqual(name, party_module.FLAG_ALL_FUNC)
        self.assertEqual(form, int(CallForm.FLOAT_PTR))
        self.assertEqual(
            args,
            (float_bits(party_module.HUGE_VALF), float_bits(party_module.HUGE_VALF), float_bits(0.0), 0, 0),
        )
        self.assertEqual(
            args[0], 0x7F800000, "+inf as a float's own bits, which is what HUGE_VALF is"
        )

    def test_an_unresolvable_function_is_a_refusal_not_a_call(self) -> None:
        """``if (!g_flag_hero_agent_func) return false;`` — and the same for ``flag_all``."""

        self.client.resolvable = False

        self.assertIsNone(Party.Heroes.FlagHero(5, 1.0, 2.0))
        self.assertIsNone(Party.Heroes.FlagAllHeroes(1.0, 2.0))
        self.assertIsNone(Party.Heroes.UnflagAllHeroes())

        self.assertEqual(self.client.calls, [])


class _BehaviorWorld:
    """A world context, as far as the behaviour, pet, search and name members read it.

    The arrays are the sources' own: `hero_flags` is the one `set_hero_behavior` walks (and its
    **size** is part of native's guard), `skillbars` is `Context::GetSkillbarArray`'s record (null
    unless the array is valid), `pets` is the one `set_pet_behavior` guards on, and `players` is the
    array the name and chat members index by login number.
    """

    def __init__(self, hero_flags=None, skillbars=None, pets=None, players=None) -> None:
        self.hero_flags = hero_flags
        self.skillbars = skillbars
        self.pets = pets
        self.players = players


class _BehaviorClient:
    """The stand-in client the behaviour, pet, search and name members are driven against."""

    def __init__(self, world: Any = None, resolvable: bool = True) -> None:
        self.world = world
        self.resolvable = resolvable
        self.bridge = _PartyBridge()
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []

    @property
    def writes(self) -> list[tuple[int, bytes]]:
        """Where the block's words went, as the bridge recorded them."""

        return self.bridge.writes

    def resolves(self, name: str) -> bool:
        return self.resolvable

    def read_world_context(self):
        return self.world

    def call_function(
        self,
        name: str,
        form: Any,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
    ) -> None:
        self.calls.append((name, int(form), (arg1, arg2, arg3, arg4, arg5)))


class _Skillbar:
    """One `SkillbarStruct`, as the AI member reads it: the agent and the disabled bits."""

    def __init__(self, agent_id: int, disabled: int = 0) -> None:
        self.agent_id = agent_id
        self.disabled = disabled


class _HeroFlag:
    """One `HeroFlagStruct`, as `set_hero_behavior` reads it."""

    def __init__(self, agent_id: int, hero_behavior: int) -> None:
        self.agent_id = agent_id
        self.hero_behavior = hero_behavior


class _Pet:
    """One `PetInfoStruct`, as `set_pet_behavior` reads it."""

    def __init__(
        self, agent_id: int, owner_agent_id: int, behavior: int, locked_target_id: int
    ) -> None:
        self.agent_id = agent_id
        self.owner_agent_id = owner_agent_id
        self.behavior = behavior
        self.locked_target_id = locked_target_id


class PartyBehaviorTests(unittest.TestCase):
    """`SetHeroBehavior` and `SetSkillAIEnabled`: native's guards, walk and write-if-different.

    Both members are the binding's body, and both are **conditional writers** — the client is told
    only when what it holds differs from what was asked for — which is the part a test has to check
    from both sides: the call when it should happen, and its absence when it should not.
    """

    def setUp(self) -> None:
        self.client = _BehaviorClient(_BehaviorWorld())
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self) -> tuple[str, int, tuple[int, ...]]:
        self.assertEqual(len(self.client.calls), 1, "one call per member")
        return self.client.calls[0]

    def test_set_hero_behavior_tells_the_client_only_when_the_word_differs(self) -> None:
        """``if (flag.hero_behavior != behavior) g_set_hero_behavior_func(...)`` (`:352-355`)."""

        from py4gw.game_thread.shared_block import CallForm

        self.client.world.hero_flags = [_HeroFlag(agent_id=21, hero_behavior=1)]
        Party.Heroes.SetHeroBehavior(21, 0)

        name, form, args = self.call()
        self.assertEqual(name, party_module.SET_HERO_BEHAVIOR_FUNC)
        self.assertEqual(form, int(CallForm.U32_U32))
        self.assertEqual(args, (21, 0, 0, 0, 0))

        self.client.calls.clear()
        Party.Heroes.SetHeroBehavior(21, 1)
        self.assertEqual(
            self.client.calls, [], "the record already holds this behaviour: native returns true"
        )

    def test_set_hero_behavior_answers_nothing_for_a_record_that_is_not_there(self) -> None:
        """The walk ends in ``return false`` when no flag carries the agent (`:357-358`)."""

        self.client.world.hero_flags = [_HeroFlag(agent_id=21, hero_behavior=0)]
        self.assertIsNone(Party.Heroes.SetHeroBehavior(22, 0))
        self.assertEqual(self.client.calls, [])

    def test_set_hero_behavior_refuses_without_a_world_function_or_flags(self) -> None:
        """Native's one guard: ``w && g_set_hero_behavior_func && w->hero_flags.size()` (`:347-349`)."""

        self.client.world.hero_flags = [_HeroFlag(agent_id=21, hero_behavior=0)]
        self.client.resolvable = False
        self.assertIsNone(Party.Heroes.SetHeroBehavior(21, 1))
        self.assertEqual(self.client.calls, [], "no function, no call")

        self.client.resolvable = True
        self.client.world.hero_flags = []
        self.assertIsNone(Party.Heroes.SetHeroBehavior(21, 1))
        self.assertEqual(self.client.calls, [], "an empty array is native's size() == 0")

        self.client.world = None
        self.assertIsNone(Party.Heroes.SetHeroBehavior(21, 1))
        self.assertEqual(self.client.calls, [], "no world at all")

    def test_set_skill_ai_enabled_reads_the_disabled_bit_and_sends_a_zero_based_slot(self) -> None:
        """``is_disabled == !enabled`` returns early; otherwise one call with ``skill_slot - 1``.

        The slot here is *enabled* (bit clear) and the caller asks to disable it, so the state differs
        and the client is told — with ``slot - 1``, which is what ``command_hotkey_disable_ai_func``
        takes (`party_methods.cpp:369-386`).
        """

        from py4gw.game_thread.shared_block import CallForm

        self.client.world.skillbars = [_Skillbar(agent_id=21, disabled=0)]
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 3, False), True)

        name, form, args = self.call()
        self.assertEqual(name, party_module.COMMAND_HOTKEY_DISABLE_AI_FUNC)
        self.assertEqual(form, int(CallForm.U32_U32))
        self.assertEqual(args, (21, 2, 0, 0, 0), "slot 3 is word 2 for the client")

    def test_set_skill_ai_enabled_is_idempotent_and_reports_true_either_way(self) -> None:
        """``if (is_disabled == !enabled) return true;`` — the state already matches (`:381-383`)."""

        self.client.world.skillbars = [_Skillbar(agent_id=21, disabled=0)]
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 3, True), True)
        self.assertEqual(self.client.calls, [], "the slot is already enabled")

        self.client.world.skillbars = [_Skillbar(agent_id=21, disabled=0b0000_0100)]
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 3, False), True)
        self.assertEqual(self.client.calls, [], "the slot is already disabled")

    def test_set_skill_ai_enabled_keeps_natives_four_guards(self) -> None:
        """``!func || !hero_agent_id || slot < 1 || slot > 8`` (`:362-363`), then the walks."""

        self.client.world.skillbars = [_Skillbar(agent_id=21, disabled=0)]
        self.assertIs(Party.Heroes.SetSkillAIEnabled(0, 1, True), False)
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 0, True), False)
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 9, True), False)
        self.assertIs(Party.Heroes.SetSkillAIEnabled(22, 1, True), False)
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.calls, [], "no agent, no slot range, no skillbar: nothing sent")

        self.client.world.skillbars = None
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 1, True), False, "GetSkillbarArray was null")

        self.client.resolvable = False
        self.client.world.skillbars = [_Skillbar(agent_id=21, disabled=0)]
        self.assertIs(Party.Heroes.SetSkillAIEnabled(21, 1, True), False, "the function is missing")


class PartyPetBehaviorTests(unittest.TestCase):
    """`Pets.SetPetBehavior`: the pet, the optional target, and the two conditional writes.

    Native's body is ``party_methods.cpp:391-413``. The target is resolved **only for the Fight
    behaviour**, and it must be a living **enemy**; anything else refuses before either the lock or the
    behaviour is written. The pet is the controlled character's own, so the owner walk is answered
    here (it is `Party.Pets._pet_info`'s own test elsewhere).
    """

    def setUp(self) -> None:
        from py4gw.player import Player

        self.client = _BehaviorClient(_BehaviorWorld())
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = mock.patch.object(Player, "GetAgentID", staticmethod(lambda: 99))
        self.player.start()
        self.addCleanup(self.player.stop)
        self.target = mock.patch.object(Player, "GetTargetID", staticmethod(lambda: 77))
        self.target.start()
        self.addCleanup(self.target.stop)

    def calls(self) -> list[str]:
        return [name for name, _form, _args in self.client.calls]

    def test_fight_writes_the_locked_target_then_the_behaviour(self) -> None:
        """``pet_info->locked_target_id != target_agent_id`` and ``behavior != behavior`` (`:408-411`)."""

        from py4gw.agent import Agent
        from py4gw.enums_src.game_data_enums import Allegiance
        from py4gw.enums_src.hero_enums import PetBehavior
        from py4gw.game_thread.shared_block import CallForm

        self.client.world.pets = [_Pet(agent_id=30, owner_agent_id=99, behavior=1, locked_target_id=0)]
        living = type("_Living", (), {"agent_id": 88, "allegiance": int(Allegiance.Enemy)})()
        with mock.patch.object(Agent, "GetLivingAgentByID", staticmethod(lambda agent_id: living)), \
                mock.patch.object(Agent, "IsLiving", staticmethod(lambda agent_id: True)):
            self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Fight), 0))

        self.assertEqual(
            self.client.calls,
            [
                (party_module.LOCK_PET_TARGET_FUNC, int(CallForm.U32_U32), (30, 88, 0, 0, 0)),
                (party_module.SET_HERO_BEHAVIOR_FUNC, int(CallForm.U32_U32), (30, 0, 0, 0, 0)),
            ],
            "the pet's own agent id, the target's own agent id, then the behaviour",
        )

    def test_a_non_fight_behaviour_locks_no_target(self) -> None:
        """``target_agent_id`` stays ``0`` for Guard/Avoid, and the lock is cleared if it differs."""

        from py4gw.enums_src.hero_enums import PetBehavior
        from py4gw.game_thread.shared_block import CallForm

        self.client.world.pets = [_Pet(agent_id=30, owner_agent_id=99, behavior=1, locked_target_id=88)]
        self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Guard), 0))

        self.assertEqual(
            self.client.calls,
            [(party_module.LOCK_PET_TARGET_FUNC, int(CallForm.U32_U32), (30, 0, 0, 0, 0))],
            "the behaviour already matches, so only the lock is written",
        )

    def test_fight_refuses_a_target_that_is_not_a_living_enemy(self) -> None:
        """``!(target && GetIsLivingType() && allegiance == Enemy)`` → false (`:402-405`)."""

        from py4gw.agent import Agent
        from py4gw.enums_src.game_data_enums import Allegiance
        from py4gw.enums_src.hero_enums import PetBehavior

        self.client.world.pets = [_Pet(agent_id=30, owner_agent_id=99, behavior=0, locked_target_id=0)]
        ally = type("_Living", (), {"agent_id": 88, "allegiance": int(Allegiance.Ally)})()

        with mock.patch.object(Agent, "GetLivingAgentByID", staticmethod(lambda agent_id: ally)), \
                mock.patch.object(Agent, "IsLiving", staticmethod(lambda agent_id: True)):
            self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Fight), 0))
        self.assertEqual(self.client.calls, [], "an ally is not a fight target")

        with mock.patch.object(Agent, "GetLivingAgentByID", staticmethod(lambda agent_id: None)), \
                mock.patch.object(Agent, "IsLiving", staticmethod(lambda agent_id: False)):
            self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Fight), 0))
        self.assertEqual(self.client.calls, [], "no agent, no target")

    def test_the_callers_target_id_is_used_when_none_is_passed(self) -> None:
        """``lock_target_id ? GetAgentByID(lock_target_id) : GetTarget()`` (`:401-402`)."""

        from py4gw.agent import Agent
        from py4gw.enums_src.game_data_enums import Allegiance
        from py4gw.enums_src.hero_enums import PetBehavior

        self.client.world.pets = [_Pet(agent_id=30, owner_agent_id=99, behavior=1, locked_target_id=0)]
        seen: list[int] = []
        living = type("_Living", (), {"agent_id": 88, "allegiance": int(Allegiance.Enemy)})()

        def lookup(agent_id: int):
            seen.append(int(agent_id))
            return living

        with mock.patch.object(Agent, "GetLivingAgentByID", staticmethod(lookup)), \
                mock.patch.object(Agent, "IsLiving", staticmethod(lambda agent_id: True)):
            Party.Pets.SetPetBehavior(int(PetBehavior.Fight), 0)
        self.assertEqual(seen, [77], "zero means the player's own current target")

        self.client.calls.clear()
        seen.clear()
        with mock.patch.object(Agent, "GetLivingAgentByID", staticmethod(lookup)), \
                mock.patch.object(Agent, "IsLiving", staticmethod(lambda agent_id: True)):
            Party.Pets.SetPetBehavior(int(PetBehavior.Fight), 55)
        self.assertEqual(seen, [55], "a passed id wins over the current target")

    def test_set_pet_behavior_refuses_without_a_world_resolvers_or_pets(self) -> None:
        """``w && g_set_hero_behavior_func && g_lock_pet_target_func && w->pets.size()` (`:392-394`)."""

        from py4gw.enums_src.hero_enums import PetBehavior

        self.client.world.pets = [_Pet(agent_id=30, owner_agent_id=99, behavior=0, locked_target_id=0)]
        self.client.resolvable = False
        self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Guard), 0))
        self.assertEqual(self.client.calls, [])

        self.client.resolvable = True
        self.client.world.pets = []
        self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Guard), 0))
        self.assertEqual(self.client.calls, [], "an empty pets array")

        self.client.world.pets = [_Pet(agent_id=30, owner_agent_id=98, behavior=0, locked_target_id=0)]
        self.assertIsNone(Party.Pets.SetPetBehavior(int(PetBehavior.Guard), 0))
        self.assertEqual(self.client.calls, [], "no pet for this owner: get_pet_info answered null")


class _WorldPlayer:
    """One `PlayerStruct`, as the name and chat members read it: the two name pointers."""

    def __init__(self, agent_id: int, name: str) -> None:
        self.agent_id = agent_id
        self.name_encoded_str = name


class PartySearchTests(unittest.TestCase):
    """`SearchParty`: the wide advertisement, placed and then pointed at.

    ``GW::party::search_party`` (``party_methods.cpp:467-472``) is three words — the type, the address
    of the advertisement, and native's ``0`` — so what a test has to check is the **text** it places
    and where it says the text is.
    """

    def setUp(self) -> None:
        self.client = _BehaviorClient(_BehaviorWorld())
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_it_places_the_advertisement_and_passes_its_address(self) -> None:
        from py4gw.game_thread.shared_block import CallForm

        self.assertIs(Party.SearchParty(1, "LDoA run"), True)

        self.assertEqual(
            self.client.writes,
            [
                (
                    party_module.PARTY_ADVERTISEMENT_OFFSET,
                    "LDoA run".encode("utf-16-le") + b"\x00\x00",
                )
            ],
        )
        self.assertEqual(
            self.client.calls,
            [
                (
                    party_module.PARTY_SEARCH_SEEK_FUNC,
                    int(CallForm.U32_U32_U32),
                    (
                        1,
                        _PartyBridge.REGION_BASE + party_module.PARTY_ADVERTISEMENT_OFFSET,
                        0,
                        0,
                        0,
                    ),
                )
            ],
            "the type, the advertisement's address, and native's own zero",
        )

    def test_an_empty_advertisement_is_still_an_empty_wide_string(self) -> None:
        """Native passes ``L""``, not a null pointer, once the methods layer has its wide string."""

        self.assertIs(Party.SearchParty(0, ""), True)
        self.assertEqual(self.client.writes[0][1], b"\x00\x00")

    def test_the_text_is_bounded_by_the_region_that_holds_it(self) -> None:
        """The port's own bound: the block's span, terminator included (`PARTY_ADVERTISEMENT_CODE_UNITS`)."""

        long_text = "x" * 200
        Party.SearchParty(1, long_text)

        written = self.client.writes[0][1]
        self.assertEqual(
            len(written), party_module.PARTY_ADVERTISEMENT_CODE_UNITS * 2
        )
        self.assertTrue(written.endswith(b"\x00\x00"))

    def test_an_unresolvable_function_is_a_refusal_not_a_call(self) -> None:
        """``if (!g_party_search_seek_func) return false;`` (`:468-469`)."""

        self.client.resolvable = False
        self.assertIs(Party.SearchParty(1, "run"), False)
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.writes, [], "nothing is placed when nothing will read it")


class PartyPlayersTests(unittest.TestCase):
    """The name and chat members: the player-array walk, its own name pointer, and the chat send.

    All three go through `player::GetPlayerByID` (``player_methods.cpp:105-112``), so the array and
    the record are what the fixture supplies; the chat send is `chat.SendChat` on the command channel,
    which is the client's own ``/invite`` and ``/kick`` syntax.
    """

    PLAYER_ID = 1

    def setUp(self) -> None:
        from py4gw.player import Player

        self.client = _BehaviorClient(
            _BehaviorWorld(players=[_WorldPlayer(11, "Ann"), _WorldPlayer(22, "Bo")])
        )
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.number = mock.patch.object(Player, "GetPlayerNumber", staticmethod(lambda: 1))
        self.number.start()
        self.addCleanup(self.number.stop)
        self.sent: list[tuple[Any, str]] = []
        chat = mock.patch(
            "py4gw.chat.SendChat",
            lambda channel, message: self.sent.append((channel, message)) or True,
        )
        chat.start()
        self.addCleanup(chat.stop)

    def test_the_agent_id_lookup_is_natives_player_lookup(self) -> None:
        """``player::GetPlayerByID`` — an array index, and zero means the caller's own number.

        Round 7's live read found this member answering ``0`` for login ``0``: it went through
        Reforged's ``WorldContextStruct.GetPlayerById`` (a search by ``player_number``) where the
        source indexes the array and maps a zero login to the caller's own player number. The
        stand-in is the same one `PartyPlayersTests` uses, so the two members that read a login
        number are checked against the same array.
        """

        from py4gw.player import Player

        client = _BehaviorClient(
            _BehaviorWorld(players=[_WorldPlayer(11, "Ann"), _WorldPlayer(22, "Bo")])
        )
        with mock.patch("py4gw.client._current_client", client), mock.patch.object(
            Player, "GetPlayerNumber", staticmethod(lambda: 1)
        ):
            self.assertEqual(Party.Players.GetAgentIDByLoginNumber(1), 22)
            self.assertEqual(
                Party.Players.GetAgentIDByLoginNumber(0), 22, "zero is the caller's own number"
            )
            self.assertEqual(Party.Players.GetAgentIDByLoginNumber(9), 0, "past the array")

    def test_the_name_is_the_records_own_and_the_binding_narrows_it(self) -> None:
        """``player->name``, then ``*name < 128 ? *name : '?'`` (``party_bindings.cpp:406-408``)."""

        self.assertEqual(
            Party.Players.GetPlayerNameByLoginNumber(self.PLAYER_ID), "Bo"
        )

        self.client.world.players = [_WorldPlayer(11, "Ann"), _WorldPlayer(22, "Ünïcøde")]
        self.assertEqual(
            Party.Players.GetPlayerNameByLoginNumber(self.PLAYER_ID),
            "?n?c?de",
            "the binding's own narrowing, which is what the source answers with",
        )

    def test_login_number_zero_is_the_callers_own_player_number(self) -> None:
        """``if (!player_id) player_id = GetPlayerNumber();`` (``player_methods.cpp:106-108``)."""

        self.assertEqual(Party.Players.GetPlayerNameByLoginNumber(0), "Bo")

    def test_no_player_or_no_name_answers_nothing(self) -> None:
        """``GetPlayerByID`` returning null and the binding's own ``if (!name) return {}``."""

        self.assertEqual(Party.Players.GetPlayerNameByLoginNumber(9), "", "past the array")
        self.client.world.players = None
        self.assertEqual(Party.Players.GetPlayerNameByLoginNumber(self.PLAYER_ID), "", "no array")

    def test_kick_player_sends_the_command_the_source_builds(self) -> None:
        """``swprintf(buf, 32, L"kick %s", player_name); chat::SendChat('/', buf);`` (`:292-297`)."""

        self.assertIsNone(Party.Players.KickPlayer(self.PLAYER_ID))
        self.assertEqual(self.sent, [("/", "kick Bo")])

    def test_invite_player_by_id_sends_the_same_shape_with_invite(self) -> None:
        """``invite_player(player_id)`` (`:310-315`): the record's name, ``L"invite %s"``, same send."""

        self.assertIsNone(Party.Players.InvitePlayer(self.PLAYER_ID))
        self.assertEqual(self.sent, [("/", "invite Bo")])

    def test_a_player_the_array_does_not_hold_sends_nothing(self) -> None:
        """``if (!(player && player->name)) return false;`` — both members (`:294`, `:312`)."""

        self.assertIsNone(Party.Players.KickPlayer(9))
        self.assertIsNone(Party.Players.InvitePlayer(9))
        self.assertEqual(self.sent, [])

    def test_invite_player_by_name_goes_through_the_caller(self) -> None:
        """``Player.SendChatCommand("invite " + require_real_name(name))`` (``Party.py:465-467``)."""

        from py4gw.player import Player

        commands: list[str] = []
        with mock.patch.object(
            Player, "SendChatCommand", staticmethod(lambda command: commands.append(command))
        ):
            self.assertIsNone(Party.Players.InvitePlayer("Ann"))

        self.assertEqual(commands, ["invite Ann"], "the resolver returns the name unchanged here")
        self.assertEqual(self.sent, [], "the by-name branch does not use the port's own chat send")

    def test_invite_player_refuses_anything_else_with_the_sources_own_error(self) -> None:
        """``else: raise TypeError("Invalid argument type. Must be int (ID) or str (name).")``."""

        with self.assertRaises(TypeError) as caught:
            Party.Players.InvitePlayer(None)
        self.assertIn("Must be int (ID) or str (name)", str(caught.exception))
        self.assertEqual(self.sent, [])


class PartyUseSkillTests(unittest.TestCase):
    """`Heroes.UseSkill`: the control-action switch, the target swap, and the restore.

    ``PyParty::UseHeroSkill`` (``party_bindings.cpp:424-447``) presses ``ControlAction_Hero{N}Skill1 +
    (slot - 1)`` through ``ui::Keypress``, changing the target first when the caller asked for one and
    putting the old one back afterwards. The bases are **not** evenly spaced — ``Hero3Skill1`` is
    ``0xF5`` and ``Hero4Skill1`` ``0x106`` — so the switch is what makes this testable at all.
    """

    def setUp(self) -> None:
        from py4gw.player import Player

        self.events: list[tuple] = []
        self.target = 4242
        target = mock.patch.object(
            Player, "GetTargetID", staticmethod(lambda: self.target)
        )
        target.start()
        self.addCleanup(target.stop)
        change = mock.patch.object(
            Player,
            "ChangeTarget",
            staticmethod(lambda agent_id: self.events.append(("target", agent_id))),
        )
        change.start()
        self.addCleanup(change.stop)
        press = mock.patch(
            "py4gw.ui_manager.UIManager.Keypress",
            lambda key, frame_id: self.events.append(("press", key, frame_id)),
        )
        press.start()
        self.addCleanup(press.stop)

    def test_it_changes_target_presses_the_slot_and_restores(self) -> None:
        """Native's enqueued body, in its own order (`:439-446`)."""

        self.assertIsNone(Party.Heroes.UseSkill(4, 2, 77))
        self.assertEqual(
            self.events,
            [("target", 77), ("press", int(HERO_BASE[3]) + 1, 0), ("target", 4242)],
            "hero 4 slot 2 is Hero4Skill1 + 1, and the caller's target comes back",
        )

    def test_a_target_that_is_already_current_is_not_set_twice(self) -> None:
        """``if (target_id && target_id != GetTargetId())`` — and the same test for the restore."""

        self.assertIsNone(Party.Heroes.UseSkill(1, 1, 4242))
        self.assertEqual(self.events, [("press", int(HERO_BASE[0]), 0)])

    def test_no_target_id_presses_without_touching_the_target(self) -> None:
        """``target_id == 0`` skips the first change, and the restore's own test still holds."""

        self.assertIsNone(Party.Heroes.UseSkill(1, 1, 0))
        self.assertEqual(
            self.events,
            [("press", int(HERO_BASE[0]), 0), ("target", 4242)],
            "the source restores because the target it remembered differs from the caller's zero",
        )

    def test_no_previous_target_leaves_nothing_to_restore(self) -> None:
        """``if (curr_target && ...)`` — nothing is put back when there was no target."""

        self.target = 0
        self.assertIsNone(Party.Heroes.UseSkill(1, 1, 77))
        self.assertEqual(self.events, [("target", 77), ("press", int(HERO_BASE[0]), 0)])

    def test_a_hero_number_outside_the_switch_does_nothing(self) -> None:
        """The switch's ``default: return;`` — heroes 1..7 only (`:436`)."""

        for hero_number in (0, 8, 99):
            with self.subTest(hero=hero_number):
                self.assertIsNone(Party.Heroes.UseSkill(hero_number, 1, 77))
        self.assertEqual(self.events, [])


#: The seven `ControlAction_Hero{N}Skill1` bases, read from the port's own enum table.
HERO_BASE = (
    party_module.ControlAction.ControlAction_Hero1Skill1,
    party_module.ControlAction.ControlAction_Hero2Skill1,
    party_module.ControlAction.ControlAction_Hero3Skill1,
    party_module.ControlAction.ControlAction_Hero4Skill1,
    party_module.ControlAction.ControlAction_Hero5Skill1,
    party_module.ControlAction.ControlAction_Hero6Skill1,
    party_module.ControlAction.ControlAction_Hero7Skill1,
)


class PartyButtonTests(unittest.TestCase):
    """The party-button family: the arrays they build, and the callback they call.

    Native builds ``uint32_t ctx[13]`` and ``uint32_t wparam[4]`` **on its stack**
    (``party_methods.cpp:206``, ``:216`` and the rest), fills the fields the client's button handler
    reads, and calls the callback with the two addresses. The port places the same arrays in the
    block's data region, so a stand-in bridge that records what was written is what checks the
    **values and their indices** — the part a source reading cannot: whether ``ctx[9]`` really holds
    the hero id, and whether the button word is where the client looks for it.
    """

    def setUp(self) -> None:
        self.client = _PartyBridgeClient()
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    #: The two data-region offsets the members place their arrays at, from ``py4gw.party``.
    CTX = party_module.PARTY_CTX_OFFSET
    WPARAM = party_module.PARTY_WPARAM_OFFSET

    def ctx(self) -> list[int]:
        """Return the context array the member placed, as words."""

        words = self.client.bridge.words_at(self.CTX)
        self.assertEqual(len(words), party_module.PARTY_CTX_WORDS, "the source's ctx size")
        return words

    def wparam(self) -> list[int]:
        """Return the ``wparam`` array the member placed, as words."""

        words = self.client.bridge.words_at(self.WPARAM)
        self.assertEqual(len(words), party_module.PARTY_WPARAM_WORDS, "the source's wparam size")
        return words

    def call(self) -> dict[str, Any]:
        self.assertEqual(len(self.client.calls), 1, "one callback per member")
        return self.client.calls[0]

    def test_add_hero_puts_the_id_at_ctx9_and_the_tag_at_ctx11(self) -> None:
        """``party_methods.cpp:213-227``: ``ctx[0xb] = 1; ctx[9] = heroid;`` and ``edx = 2``."""

        Party.Heroes.AddHero(7)

        call = self.call()
        self.assertEqual(call["name"], party_module.PARTY_SEARCH_BUTTON_CALLBACK)
        self.assertEqual(call["edx"], 2, "add_hero is the one that passes a second word in EDX")
        self.assertEqual(
            call["address"],
            self.client.bridge.REGION_BASE + self.CTX,
            "the callback is handed the region address, where the array now sits",
        )
        self.assertEqual(call["wparam_address"], self.client.bridge.REGION_BASE + self.WPARAM)
        ctx = self.ctx()
        self.assertEqual(ctx[0xB], 1)
        self.assertEqual(ctx[9], 7)
        wparam = self.wparam()
        self.assertEqual((wparam[1], wparam[2]), (0x1, 0x7))

    def test_kick_hero_writes_the_same_slot_the_add_does(self) -> None:
        """``ctx[ctx[0xb] + 8]`` is the **value** at ``ctx[0xb]`` plus eight — ``ctx[9]``."""

        Party.Heroes.KickHero(9)

        call = self.call()
        self.assertEqual(call["edx"], 0)
        ctx = self.ctx()
        self.assertEqual((ctx[0xB], ctx[9]), (1, 9))
        wparam = self.wparam()
        self.assertEqual((wparam[1], wparam[2]), (0x6, 0x7))

    def test_kick_all_heroes_is_kick_hero_of_thirty_eight(self) -> None:
        """``party_methods.cpp:245-247``: the whole body is ``kick_hero(0x26)``."""

        Party.Heroes.KickAllHeroes()

        self.assertEqual(self.ctx()[9], 0x26)

    def test_add_and_kick_henchman_use_ctx10_and_the_henchman_tag(self) -> None:
        """``ctx[0xb] = 2`` is what makes the client read ``ctx[10]`` rather than ``ctx[9]``."""

        Party.Henchmen.AddHenchman(11)
        added = self.ctx()
        self.assertEqual((added[0xB], added[10], added[9]), (2, 11, 0))
        self.assertEqual(self.wparam()[1], 0x2)
        self.client.calls.clear()
        self.client.bridge.writes.clear()

        Party.Henchmen.KickHenchman(12)

        kicked = self.ctx()
        self.assertEqual((kicked[0xB], kicked[10]), (2, 12))
        self.assertEqual(self.wparam()[1], 0x6)

    def test_the_name_forms_resolve_through_the_ported_hero_table(self) -> None:
        """``Party.py:611-618``: ``PyParty.Hero(name).GetID()``, then the id form."""

        Party.Heroes.AddHeroByName("Norgu")

        self.assertEqual(self.ctx()[9], int(HeroType.Norgu))

        self.client.calls.clear()
        self.client.bridge.writes.clear()

        Party.Heroes.KickHeroByName("M.O.X.")

        self.assertEqual(self.ctx()[9], int(HeroType.MOX))

    def test_search_party_cancel_and_reply_are_the_sources_words(self) -> None:
        """``party_methods.cpp:474-498``: cancel is ``wparam[2] = 0x8`` with everything else zero."""

        self.assertIsNone(Party.SearchPartyCancel())

        cancel = self.wparam()
        self.assertEqual((cancel[0], cancel[1], cancel[2]), (0, 0, 0x8))
        self.assertEqual(sum(self.ctx()), 0)
        self.client.calls.clear()
        self.client.bridge.writes.clear()

        self.assertTrue(Party.SearchPartyReply(True))

        reply = self.wparam()
        self.assertEqual((reply[1], reply[2]), (0x3, 0x6))
        ctx = self.ctx()
        self.assertEqual((ctx[0xB], ctx[8]), (0, 1), "the acceptance is ctx[8] as a word")

    def test_only_the_members_reforged_returns_a_value_answer_one(self) -> None:
        """The source's own ``return``s, member by member (``Party.py:352-396``, ``:602-763``).

        ``SearchPartyReply`` is the one member of this family whose Reforged body is
        ``return Party.party_instance().SearchPartyReply(accept)`` (``:368``); the rest call and
        discard — ``SearchPartyCancel`` ``:358``, ``LeaveParty`` ``:396``, ``AddHero`` ``:608``,
        ``KickHero`` ``:627``, ``KickAllHeroes`` ``:645``, ``AddHenchman`` ``:754``,
        ``KickHenchman`` ``:763``. Native's bodies behind them answer ``true``/``false``, so a
        port that returned the helper's bool everywhere would invent a contract for seven members
        that the source does not have.
        """

        self.assertIsNone(Party.Heroes.AddHero(1))
        self.assertIsNone(Party.Heroes.KickHero(1))
        self.assertIsNone(Party.Heroes.KickAllHeroes())
        self.assertIsNone(Party.Henchmen.AddHenchman(1))
        self.assertIsNone(Party.Henchmen.KickHenchman(1))
        self.assertIsNone(Party.SearchPartyCancel())
        self.assertIs(Party.SearchPartyReply(True), True)

        with mock.patch.object(Party, "GetPartySize", staticmethod(lambda: 2)):
            self.assertIsNone(Party.LeaveParty())

    def test_a_resolver_that_answers_nothing_is_a_refusal_not_a_call(self) -> None:
        """``if (!g_party_search_button_callback_func) return false;`` is every one of these bodies."""

        self.client.resolvable = False

        for member, argument in (
            (Party.Heroes.AddHero, 1),
            (Party.Heroes.KickHero, 1),
            (Party.Henchmen.AddHenchman, 1),
            (Party.SearchPartyCancel, None),
        ):
            with self.subTest(member=getattr(member, "__name__", member)):
                self.assertIsNone(
                    member() if argument is None else member(argument)  # type: ignore[call-arg]
                )

        # The member whose source *returns* the call's answer reports the refusal instead.
        self.assertIs(Party.SearchPartyReply(True), False)

        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.bridge.writes, [])

    def test_the_search_callback_is_the_form_that_pops_its_own_word(self) -> None:
        """The measured ABI: the search handler ends ``ret 4`` (``tests/probe_party_abi.py``)."""

        from py4gw.game_thread.shared_block import CallForm

        Party.SearchPartyReply(False)

        self.assertEqual(self.call()["form"], CallForm.FASTCALL_U32)
        self.assertEqual(self.ctx()[8], 0, "a refusal is the same call with the word cleared")

    def test_leave_party_calls_the_window_callback_which_releases_its_own_word(self) -> None:
        """``party_methods.cpp:200-211``: ``ctx[0xd] = 1`` and the **window** callback.

        The two party callbacks have different measured ABIs — the search one ends ``ret 4`` and the
        window one a bare ``ret`` — so the form is part of this member's answer, not decoration.
        """

        from py4gw.game_thread.shared_block import CallForm

        with mock.patch.object(Party, "GetPartySize", staticmethod(lambda: 2)):
            Party.LeaveParty()

        call = self.call()
        self.assertEqual(call["name"], party_module.PARTY_WINDOW_BUTTON_CALLBACK)
        self.assertEqual(call["form"], CallForm.FASTCALL_U32_CALLER_RELEASES)
        self.assertEqual(self.ctx()[0xD], 1)

    def test_leave_party_with_no_party_answers_without_calling(self) -> None:
        """The source's own first line: ``if (!get_party_size()) return true;``."""

        with mock.patch.object(Party, "GetPartySize", staticmethod(lambda: 0)):
            Party.LeaveParty()

        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.bridge.writes, [])


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

    def test_the_bound_operators_and_repr_are_the_sources_own(self) -> None:
        """``Hero`` is a bound class: `operator==`/`!=` (``:49-50``) and ``__repr__`` (``:491``).

        Reforged Native binds all three (``party_bindings.cpp:489-492``) and the port carried none of
        them until round 15 — a caller could construct a ``Hero`` and not compare or print it.
        """

        self.assertEqual(Hero(1), Hero("Norgu"))
        self.assertNotEqual(Hero(1), Hero(2))
        self.assertEqual(
            repr(Hero("Norgu")),
            "<Hero name='' id=1>",
            "the source's own format, with the name it never assigns",
        )
        self.assertNotEqual(
            Hero(1), 1, "a non-Hero is not equal: the source's operator takes a Hero"
        )
        self.assertEqual(len({Hero(1), Hero("Norgu"), Hero(2)}), 2, "usable as a key")

    def test_the_bound_hero_surface_is_natives_own(self) -> None:
        """Every ``.def`` of the bound ``Hero`` class exists here (``party_bindings.cpp:482-493``).

        The transcribed list is the binding's own: two constructors (one int, one string — the port's
        one ``__init__`` answers both), the three getters, the flag press, and the two operators plus
        ``__repr__``. Reading it off the source is what showed that the port was missing the last
        three (round 15).
        """

        bound = (
            "__init__",  # py::init<int>() and py::init<const std::string&>()
            "GetID",
            "GetName",
            "GetProfession",
            "FlagHero",
            "__eq__",
            "__ne__",
            "__repr__",
        )
        for member in bound:
            with self.subTest(member=member):
                self.assertTrue(hasattr(Hero, member), f"Hero.{member} is bound in the source")

    def test_flag_hero_presses_the_hero_command_keybind(self) -> None:
        """``Hero::FlagHero`` (``party_bindings.cpp:235-250``): a switch on ``1..7``, then Keypress."""

        pressed: list[tuple[int, int]] = []
        with mock.patch(
            "py4gw.ui_manager.UIManager.Keypress",
            lambda key, frame_id: pressed.append((key, frame_id)),
        ):
            self.assertIs(Hero(1).FlagHero(1), True)
            self.assertIs(Hero(1).FlagHero(4), True)
            self.assertIs(Hero(1).FlagHero(0), False, "the switch's default")
            self.assertIs(Hero(1).FlagHero(8), False, "the switch's default")

        self.assertEqual(
            pressed,
            [
                (int(party_module.ControlAction.ControlAction_CommandHero1), 0),
                (int(party_module.ControlAction.ControlAction_CommandHero4), 0),
            ],
            "heroes 1 and 4 are the CommandHero keybinds, pressed with no target frame",
        )


class _OutpostFrameArray:
    """`client.frame_array`, in the three shapes the return-to-outpost chain reads it.

    ``iter_frames`` is the label scan (native's ``GetFrameByLabel`` loop), ``get`` is native's
    ``GetFrameById`` — which `Frame.child_native` makes before it calls anything — and ``read_u32``
    answers the parent's state and callback-count words the click reads.
    """

    def __init__(self, records: dict[int, Any], words: dict[int, int] | None = None) -> None:
        self.records = dict(records)
        self.words = dict(words or {})

    def iter_frames(self):
        for frame_id in sorted(self.records):
            yield frame_id, self.records[frame_id]

    def get(self, frame_id: int):
        return self.records.get(int(frame_id))

    def read_u32(self, address: int) -> int:
        return int(self.words.get(int(address), 0))


class _OutpostCallRecord:
    """The two words a completed command carries: `value` is the callee's return, `result` its status."""

    def __init__(self, value: int, result: int = 0) -> None:
        self.value = int(value)
        self.result = int(result)


class _OutpostClient:
    """The client the return-to-outpost chain is driven against.

    It answers the three calls the chain makes — the label hash, the child lookup and the click's send
    — from one place, so the test can assert the whole sequence: which function was called, with which
    words, and where the two structs and the label were placed.
    """

    #: What the client's own `CreateHashFromWChar` answers for the label.
    LABEL_HASH = 0xABCD1234
    #: The frame carrying it (`GetFrameByLabel`), and the child the walk finds (`GetChildFrame`).
    LABEL_FRAME_ID = 3
    CHILD_ID = 4

    #: Where the stand-in bridge says the region's words are (`_PartyBridge.REGION_BASE`).
    REGION_BASE = _PartyBridge.REGION_BASE

    def __init__(self, *, has_label_frame: bool = True, has_child: bool = True) -> None:
        from py4gw.context.gw_array import GWArray
        from py4gw.frame_tree import frame as frame_module
        from py4gw.ui.frame import FrameStruct

        self.frame_module = frame_module
        self.bridge = _PartyBridge()
        self.calls: list[tuple[str, int, tuple]] = []
        self.parent_address = 0x00200000
        child_address = 0x00100000

        label = FrameStruct()
        label.bind_address(self.parent_address)
        setattr(label, "frame_state", 0x4)
        setattr(label, "frame_hash", self.LABEL_HASH if has_label_frame else 0x1234)

        child = FrameStruct()
        child.bind_address(child_address)
        setattr(child, "frame_state", 0x4)
        setattr(child, "child_offset_id", 0x62)
        setattr(child, "field105_0x1c4", 0x1234)
        setattr(getattr(child, "relation"), "parent", self.parent_address + FrameStruct.relation.offset)

        self.frame_array = _OutpostFrameArray(
            {self.LABEL_FRAME_ID: label, self.CHILD_ID: child},
            {
                self.parent_address + FrameStruct.frame_state.offset: 0x4,
                self.parent_address
                + FrameStruct.frame_callbacks.offset
                + GWArray.m_size.offset: 1,
            },
        )
        self.has_child = has_child

    def resolves(self, name: str) -> bool:
        return True

    def call_function(self, name: str, form: Any, *args: Any) -> Any:
        self.calls.append((name, int(form), tuple(int(a) for a in args)))
        if name == self.frame_module._CREATE_HASH_FROM_WCHAR_FUNC:
            return _OutpostCallRecord(self.LABEL_HASH)
        if name == self.frame_module._GET_CHILD_FRAME_ID_FUNC:
            return _OutpostCallRecord(self.CHILD_ID if self.has_child else 0)
        return _OutpostCallRecord(1)


class ReturnToOutpostTests(unittest.TestCase):
    """`Party.ReturnToOutpost` — native's one line, step for step.

    ``return ui::ButtonClick(ui::GetChildFrame(ui::GetFrameByLabel(L"DlgRedirect"), 0));``
    (``party_methods.cpp:119-121``). The three steps are the frame layer's members
    (``_FrameTree.by_label``, ``Frame.child_native``, ``Frame.click``), so this test asserts the
    **sequence** against a stand-in client: the label the client is handed and the hash it answers,
    the label frame the array scan finds, the child lookup's two words, and then the click's own send —
    which is where the `MouseAction` and `ButtonParam` are placed.
    """

    def setUp(self) -> None:
        self.client = _OutpostClient()
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def client_calls(self) -> list[str]:
        return [name for name, _form, _args in self.client.calls]

    def test_it_walks_the_label_to_the_child_and_clicks_it(self) -> None:
        self.assertIs(Party.ReturnToOutpost(), True)

        frame_module = self.client.frame_module
        self.assertEqual(
            self.client_calls(),
            [
                frame_module._CREATE_HASH_FROM_WCHAR_FUNC,
                frame_module._GET_CHILD_FRAME_ID_FUNC,
                frame_module._SEND_FRAME_UI_MESSAGE_FUNC,
            ],
            "native's order: hash the label, walk to the child, click it",
        )

        from py4gw.game_thread.shared_block import CallForm

        hash_call = self.client.calls[0]
        self.assertEqual(int(hash_call[1]), int(CallForm.U32_U32))
        self.assertEqual(
            self.client.bridge.writes[0],
            (
                frame_module._LABEL_OFFSET,
                "DlgRedirect".encode("utf-16-le") + b"\x00\x00",
            ),
            "the label is placed in the block and its address handed over",
        )
        self.assertEqual(hash_call[2], (self.client.REGION_BASE + frame_module._LABEL_OFFSET, frame_module._HASH_LABEL_LENGTH))

        child_call = self.client.calls[1]
        self.assertEqual(int(child_call[1]), int(CallForm.U32_U32))
        self.assertEqual(
            child_call[2],
            (self.client.LABEL_FRAME_ID, 0),
            "GetChildFrame(frame, 0): the frame the label named, and offset zero",
        )

        # The click places the two structs and sends kMouseClick2 to the **parent's** callbacks.
        from py4gw.ui.frame import FrameStruct

        self.assertEqual(
            self.client.bridge.writes[1][0:2],
            (frame_module._BUTTON_PARAM_OFFSET, struct.pack("<III", 0, 0x1234, 0)),
        )
        action = self.client.bridge.writes[2][1]
        self.assertEqual(
            struct.unpack("<IIIII", action),
            (0x62, 0x62, frame_module._MOUSE_UP, self.client.REGION_BASE + frame_module._BUTTON_PARAM_OFFSET, 0),
        )
        self.assertEqual(
            self.client.calls[2][2],
            (
                self.client.parent_address + FrameStruct.frame_callbacks.offset,
                0,
                frame_module._K_MOUSE_CLICK_2,
                self.client.REGION_BASE + frame_module._MOUSE_ACTION_OFFSET,
                0,
            ),
        )

    def test_a_label_no_frame_carries_answers_false_without_a_click(self) -> None:
        """``GetFrameByLabel`` → ``nullptr`` → ``ButtonClick(nullptr)`` → ``false`` (``:1250-1252``)."""

        self.client = _OutpostClient(has_label_frame=False)
        with mock.patch("py4gw.client._current_client", self.client):
            self.assertIs(Party.ReturnToOutpost(), False)

        self.assertEqual(self.client_calls(), [self.client.frame_module._CREATE_HASH_FROM_WCHAR_FUNC])

    def test_a_child_that_is_not_there_answers_false_without_a_click(self) -> None:
        """``GetChildFrame`` → ``GetFrameById(0)`` → ``nullptr`` → ``false``."""

        self.client = _OutpostClient(has_child=False)
        with mock.patch("py4gw.client._current_client", self.client):
            self.assertIs(Party.ReturnToOutpost(), False)

        self.assertEqual(
            self.client_calls(),
            [
                self.client.frame_module._CREATE_HASH_FROM_WCHAR_FUNC,
                self.client.frame_module._GET_CHILD_FRAME_ID_FUNC,
            ],
            "the walk ran, and the click never did",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
