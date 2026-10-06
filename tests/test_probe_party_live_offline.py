"""Offline tests for the live probe's own safety premise.

``tests/probe_party_live.py``'s middle stage claims something specific: **every call it makes with
the values the client already reports is refused by the source's own guards**, so the client's state
cannot move. That claim is load-bearing — it is what makes the stage safe to run before the owner has
decided anything — and it is exactly the kind of claim that is wrong in one member and silently
changes the game. So it is checked here, against a stand-in client, **before** the elevated run:

* the four members that cannot write (the tick toggle, the two no-ops and the difficulty member whose
  mode already matches) make **no call at all**;
* the behaviour and skill-AI members compare the same field the probe read, so they make no call;
* the pet's step is only taken when the source's body would write nothing — a pet that is not
  ``Fight`` **and** holds a locked target is skipped, because calling with the values it holds would
  clear that lock, which the source's own body does.

The probe is imported rather than copied, so a change to the stage is a change to what this checks.

**And round 22 rehearses the plan itself.** The plan is what the owner reads before deciding to run
anything, and ``hold`` is what actually runs; they are two pieces of code computing the same thing from
the same reads, which is exactly the arrangement that drifts. So the last class here replays the
**live** plan from ``tests/live_reports/party_reads_live.json``: it builds a stand-in from that report's own
state — the heroes' agent ids, behaviour words and disabled words, the mode, the pet — and asserts that
the calls ``hold_stage`` makes are the plan's calls, in the plan's order, with the state unchanged.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw.context.party_context import HeroPartyMember, PartyInfoStruct
from py4gw.party import Party

from tests import probe_party_live as probe_module
from tests.probe_party_live import _pet_hold_call, act_stage, hold_stage, party_reads


def setUpModule() -> None:
    """The probe spaces its acting calls out for the live client; these tests do not need that.

    ``ACTION_INTERVAL_SECONDS`` exists because a real client processes one command at a time, so a
    burst of calls tests its queue rather than the port. Nothing here talks to a client and the
    stand-in applies immediately, so the interval is zero for the whole module — otherwise the suite
    would spend a minute asleep.
    """

    probe_module.ACTION_INTERVAL_SECONDS = 0.0
    # The stand-ins that do not model the client never show a change, so a real 3 s wait per settle
    # would be spent asleep for no information a test can use.
    probe_module.SETTLE_TIMEOUT_SECONDS = 0.05


class _ZeroReader:
    """A reader that answers zeroes, so a record's arrays read as empty."""

    def read(self, address: int, size: int) -> bytes:
        return b"\x00" * size


class _World:
    """The world record, as the probe and the members read it."""

    def __init__(
        self,
        hero_flags=None,
        skillbars=None,
        pets=None,
        players=None,
        all_flag_array: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self.hero_flags = hero_flags
        self.skillbars = skillbars
        self.pets = pets
        self.players = players
        self.all_flag_array = all_flag_array


class _HeroFlag:
    def __init__(self, agent_id: int, hero_behavior: int) -> None:
        self.agent_id = agent_id
        self.hero_behavior = hero_behavior


class _Skillbar:
    def __init__(self, agent_id: int, disabled: int = 0) -> None:
        self.agent_id = agent_id
        self.disabled = disabled


class _Pet:
    def __init__(self, agent_id: int, owner_agent_id: int, behavior: int,
                 locked_target_id: int) -> None:
        self.agent_id = agent_id
        self.owner_agent_id = owner_agent_id
        self.behavior = behavior
        self.locked_target_id = locked_target_id


class _Client:
    """A client stand-in that records every call, so "no call" is an assertion and not a hope."""

    def __init__(self, world: _World) -> None:
        self.world = world
        self.party: Any = None
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []

    def __getattr__(self, name: str) -> Any:
        """Answer an unmodelled facade with a mock, so the stand-in's gaps are not read defects."""

        if name.startswith("_"):
            raise AttributeError(name)
        return mock.Mock()

    def resolves(self, name: str) -> bool:
        return True

    def read_world_context(self) -> Any:
        return self.world

    def read_party_context(self) -> Any:
        return self.party

    def call_function(self, name: str, form: Any, *args: int) -> Any:
        self.calls.append((name, int(form), tuple(int(a) for a in args)))
        return None


class HoldStageSafetyTests(unittest.TestCase):
    """The hold stage against a stand-in: a call that would write is a call this stage must not make."""

    HERO_AGENT = 1493
    HERO_BEHAVIOR = 1
    DISABLED = 0b0000_0100

    def _run(self, pet: _Pet | None, *, hero_count: int = 1) -> _Client:
        world = _World(
            hero_flags=[_HeroFlag(self.HERO_AGENT, self.HERO_BEHAVIOR)]
            if hero_count
            else [],
            skillbars=[_Skillbar(self.HERO_AGENT, self.DISABLED)],
            pets=[pet] if pet is not None else [],
        )
        client = _Client(world)
        context = mock.Mock()
        context.player_party = mock.Mock()
        context.in_hard_mode = False
        context.party_id = 1
        client.party = context
        patches = (
            mock.patch("py4gw.client._current_client", client),
            mock.patch.object(Party, "_world", staticmethod(lambda: world)),
            mock.patch.object(Party, "_context", staticmethod(lambda: context)),
            mock.patch.object(Party, "GetHeroCount", staticmethod(lambda: hero_count)),
            mock.patch.object(
                Party.Heroes,
                "GetHeroAgentIDByPartyPosition",
                staticmethod(lambda position: self.HERO_AGENT if position else 1189),
            ),
            mock.patch.object(
                Party, "IsHardMode", staticmethod(lambda: False)
            ),
            mock.patch.object(
                Party, "IsHardModeUnlocked", staticmethod(lambda: False)
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        # The probe spaces its acting calls out (``ACTION_INTERVAL_SECONDS``) because the client
        # processes one command at a time; a test that waited for real would take minutes.
        interval = mock.patch("tests.probe_party_live.ACTION_INTERVAL_SECONDS", 0.0)
        interval.start()
        self.addCleanup(interval.stop)
        report: dict[str, Any] = {}
        hold_stage(report)
        self.report = report
        return client

    def test_a_hero_holding_this_behaviour_and_these_bits_makes_no_call(self) -> None:
        """The behaviour and AI steps read the same fields the members compare, so nothing is sent."""

        client = self._run(pet=None)

        self.assertEqual(
            client.calls,
            [],
            "set_hero_behavior / set_hero_skill_ai_enabled compare the values they were handed",
        )
        self.assertTrue(self.report["unchanged"], "and the state is identical afterwards")
        self.assertIn(
            f"SetHeroBehavior({self.HERO_AGENT}, {self.HERO_BEHAVIOR})", self.report["held"]
        )
        for slot in range(1, 9):
            enabled = not (self.DISABLED & (1 << (slot - 1)))
            self.assertIn(
                f"SetSkillAIEnabled({self.HERO_AGENT}, {slot}, {enabled})", self.report["held"]
            )

    def test_the_four_members_that_cannot_write_report_their_answers(self) -> None:
        """The toggle, the two no-ops and the difficulty member answer; none of them calls."""

        client = self._run(pet=None)

        for key in ("SetTicked(True)", "RespondToPartyRequest(0, True)"):
            self.assertIsNone(self.report["held"][key], f"{key} answers None")
        self.assertIn("SetNormalMode (already normal)", self.report["held"])
        self.assertEqual(client.calls, [])

    def test_a_pet_that_is_not_fighting_and_holds_a_target_is_skipped(self) -> None:
        """The one step that had to be reasoned about: calling it would clear the pet's lock."""

        client = self._run(pet=_Pet(30, 1189, behavior=1, locked_target_id=88))

        self.assertIn("skipped", str(self.report["held"]["SetPetBehavior"]))
        self.assertEqual(client.calls, [], "no lock was cleared and no behaviour written")
        self.assertTrue(self.report["unchanged"])

    def test_a_fighting_pet_is_called_with_its_own_values_and_writes_nothing(self) -> None:
        """``Fight`` resolves the same target back, so the lock and the behaviour both match."""

        client = self._run(pet=_Pet(30, 1189, behavior=0, locked_target_id=0))

        self.assertIn("SetPetBehavior(0, 0)", self.report["held"])
        self.assertEqual(client.calls, [], "the member refuses a target that is not a living enemy")

    def test_a_pet_with_no_lock_is_called_for_any_behaviour(self) -> None:
        """With ``locked_target_id == 0`` the source's body leaves both words as they are."""

        self.assertEqual(_pet_hold_call({"behavior": 2, "locked_target_id": 0}), (2, 0))
        self.assertEqual(_pet_hold_call({"behavior": 0, "locked_target_id": 88}), (0, 88))
        self.assertIsNone(
            _pet_hold_call({"behavior": 1, "locked_target_id": 88}),
            "Guard with a locked target: the body would write the lock",
        )


class ActStageGuardTests(unittest.TestCase):
    """The acting stage's own guards: a step refuses when the client's condition for it is not met.

    Every step here is owner-gated (nothing runs without ``--allow``), and on top of that each one
    refuses rather than improvising: a hero number that is not in the party, a party with nobody else
    in it, a map that is not an outpost, a henchman id nobody gave. What this checks is that the
    refusal is a **report** — the member is not called — so the run cannot do something the owner did
    not ask for by accident.
    """

    def _stage(self, allowed: set[str], options: dict[str, Any] | None = None, *,
               outpost: bool = True, hero_count: int = 2, player_count: int = 1,
               hero_ids: dict[int, int] | None = None,
               party_window: bool = True) -> tuple[dict[str, Any], _Client]:
        world = _World(hero_flags=[], skillbars=[], pets=[], players=[])
        client = _Client(world)
        patches = (
            mock.patch("py4gw.client._current_client", client),
            mock.patch.object(Party, "_world", staticmethod(lambda: world)),
            mock.patch.object(Party, "GetHeroCount", staticmethod(lambda: hero_count)),
            mock.patch.object(Party, "GetPlayerCount", staticmethod(lambda: player_count)),
            mock.patch.object(
                Party.Heroes,
                "GetHeroAgentIDByPartyPosition",
                staticmethod(lambda position: 1493 if position else 1189),
            ),
            mock.patch(
                "py4gw.map.Map.IsOutpost", staticmethod(lambda: outpost)
            ),
            # The party window is a client frame and these stand-ins have none; what this class tests
            # is the step's other decisions, and the window guard has its own test below.
            mock.patch(
                "tests.probe_party_live._party_window_on_screen",
                staticmethod(lambda: party_window),
            ),
            mock.patch.object(
                Party.Heroes,
                "GetHeroIDByPartyPosition",
                staticmethod(lambda position: (hero_ids or {}).get(position, 7)),
            ),
            mock.patch.object(
                Party.Heroes, "GetHeroIdByName", staticmethod(lambda name: 1)
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        interval = mock.patch("tests.probe_party_live.ACTION_INTERVAL_SECONDS", 0.0)
        interval.start()
        self.addCleanup(interval.stop)
        report: dict[str, Any] = {}
        act_stage(report, allowed, options or {})
        return report, client

    def test_no_allow_means_the_plan_and_no_call(self) -> None:
        """``act`` with nothing named runs nothing — the stage is a menu until the owner chooses."""

        report, client = self._stage(set())

        self.assertEqual(client.calls, [])
        self.assertIn("nothing ran", report["note"])
        self.assertTrue(all(not row["allowed"] for row in report["plan"]))

    def test_use_skill_refuses_a_hero_number_that_is_not_in_the_party(self) -> None:
        """The control action is chosen by the hero's **number**, so it has to exist."""

        report, client = self._stage({"use-skill"}, {"hero_number": 4})

        self.assertIn("skipped", str(report["acted"]["UseSkill"]))
        self.assertEqual(client.calls, [])

    def test_use_skill_presses_for_a_hero_that_is_there(self) -> None:
        """Hero 1 in the party: the member is called for slot 2 with no target change."""

        report, client = self._stage({"use-skill"}, {"hero_number": 1, "slot": 2})

        self.assertTrue(
            any("UseSkill(hero 1, slot 2" in key for key in report["acted"]),
            f"the report names what it pressed: {list(report['acted'])}",
        )

    def test_the_party_steps_refuse_outside_an_outpost(self) -> None:
        """The client only accepts a party change in an outpost, so the step says so and stops."""

        report, client = self._stage({"party-add"}, outpost=False)

        self.assertIn("skipped", str(report["acted"]["AddHeroByName"]))
        self.assertEqual(client.calls, [])

    def test_add_henchman_needs_an_id_only_the_owner_can_give(self) -> None:
        """No ``--henchman``: the member is left alone and the report says how to name the id."""

        report, client = self._stage({"party-add"}, outpost=True)

        self.assertIn("--henchman", str(report["acted"]["AddHenchman"]))
        self.assertEqual(client.calls, [])

    def test_kick_hero_refuses_a_hero_that_is_not_in_the_party(self) -> None:
        """Nothing to kick: the member is not called, and the report names the hero it looked for."""

        report, client = self._stage({"party-kick"}, {"hero_name": "Norgu"}, hero_ids={1: 26})

        self.assertIn("not in this party", str(report["acted"]["KickHeroByName"]))
        self.assertEqual(client.calls, [])

    def test_leave_party_refuses_a_party_of_one(self) -> None:
        """``leave_party`` presses the client's leave button; with nobody else there that is not it."""

        report, client = self._stage({"leave"}, player_count=1)

        self.assertIn("skipped", str(report["acted"]["LeaveParty"]))
        self.assertEqual(client.calls, [])

    def test_leave_party_refuses_without_the_window_it_presses(self) -> None:
        """Round 25's crash, pinned: the press belongs to the party window, so the window must exist.

        Calling the member with no such window on screen asserted the client — ``Assertion: childId``,
        ``FrApi.cpp(3916)``, build 38888 — so the step refuses now, whatever the party looks like.
        """

        with mock.patch(
            "tests.probe_party_live._party_window_on_screen", staticmethod(lambda: False)
        ):
            report, client = self._stage({"leave"}, player_count=2, party_window=False)

        self.assertEqual(client.calls, [], "the press is not made without its window")
        self.assertIn("party window is not on screen", str(report["acted"]["LeaveParty"]))


class ReadStageAnswerTests(unittest.TestCase):
    """The read stage's own verdict, checked without a client: every read answers.

    The live summary counts the members whose answer is an error string, so a member that reaches for
    something that is not there appears as a number in front of the owner. That is exactly how round
    21's removal of ``PetInfoStruct.name`` — a port-only twin of the source's ``pet_name_str`` — was
    caught: the **live** run said ``1 member(s) refused``, while the offline suite said nothing,
    because nothing here drove ``party_reads``. This drives it against the stand-in.

    What it fails on is narrow on purpose: an ``AttributeError`` naming a **port** record (a type that
    does not start with an underscore, so the stand-in's own dummies are exempt) or a ``NameError``.
    Those are the two errors that mean a member was asked for by a name nobody declares. An error the
    stand-in itself causes — a facade it does not model, a mock where a number was expected — is not a
    finding about the port, and is reported by the live stage instead.
    """

    PROGRAMMING_ERRORS = ("AttributeError", "NameError")

    @staticmethod
    def _is_port_surface_error(value: object) -> bool:
        if not isinstance(value, str):
            return False
        if "NameError" in value:
            return True
        if "AttributeError" not in value:
            return False
        _, _, rest = value.partition("'")
        type_name, _, _ = rest.partition("'")
        return bool(type_name) and not type_name.startswith("_")

    def _reads(self) -> dict[str, Any]:
        world = _World(
            hero_flags=[_HeroFlag(1493, 1)],
            skillbars=[_Skillbar(1493)],
            pets=[],
            players=[],
        )
        client = _Client(world)
        context = mock.Mock()
        context.player_party = PartyInfoStruct().bind_reader(_ZeroReader(), 0x100000)
        context.in_hard_mode = False
        context.party_id = 1
        client.party = context
        patches = (
            mock.patch("py4gw.client._current_client", client),
            mock.patch.object(Party, "_world", staticmethod(lambda: world)),
            mock.patch.object(Party, "_context", staticmethod(lambda: context)),
            mock.patch.object(Party, "GetHeroCount", staticmethod(lambda: 1)),
            mock.patch.object(
                Party, "GetHeroes", staticmethod(lambda: [HeroPartyMember()])
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return party_reads()

    def test_no_read_asks_for_a_member_nobody_declares(self) -> None:
        """A read that names a member a port record does not have is a defect, not a client state."""

        rows = self._reads()

        bad = [
            f"{group}.{key} -> {value}"
            for group, values in rows.items()
            if isinstance(values, dict)
            for key, value in values.items()
            if self._is_port_surface_error(value)
        ]
        self.assertEqual(
            bad,
            [],
            "the read stage asked a port record for a member that does not exist — the live run "
            "reports this as 'member(s) refused'; each entry names the member and the error",
        )

    def test_the_pet_row_reads_the_sources_own_name_member(self) -> None:
        """The rows' keys are the members they read, so the pet's name has to be the source's."""

        rows = self._reads()

        self.assertIn("pet_name_str", rows["pets"]["GetPetInfo(0)"])
        self.assertNotIn(
            "name",
            rows["pets"]["GetPetInfo(0)"],
            "round 21 removed PetInfoStruct.name; the probe reads pet_name_str "
            "(WorldContext.py:510-512)",
        )


_LIVE_REPORT = (
    Path(__file__).resolve().parent.parent / "tests/live_reports" / "party_reads_live.json"
)


@unittest.skipUnless(
    _LIVE_REPORT.exists(),
    "no live read report to rehearse against — run `python tests/probe_party_live.py reads "
    "tests/live_reports/party_reads_live.json` on a running client first",
)
class LivePlanRehearsalTests(unittest.TestCase):
    """The live plan, replayed as the hold stage's calls, on the live client's own values.

    ``hold_plan`` and ``hold_stage`` are two pieces of code that walk the same members and apply the
    same guards — one to *describe* the run for the owner, one to *make* it. That is precisely the
    arrangement that drifts: a step added to the stage and not to the plan would send the owner into an
    elevated run that does something the plan never mentioned. So this takes the plan the live client
    actually produced and drives the stage against a stand-in built from that same report's state, and
    asserts the two agree — the calls, their arguments and their order — with the state unchanged and
    no client function called at all.
    """

    @staticmethod
    def _live() -> dict[str, Any]:
        return json.loads(_LIVE_REPORT.read_text(encoding="utf-8"))

    @staticmethod
    def _name(call: str) -> str:
        """A plan entry's or a report key's member name, without its parenthetical notes."""

        return call.split(" (")[0].removesuffix("()")

    @staticmethod
    def _shape(call: str) -> str:
        """A call as member-plus-arguments, with the probe's own annotations removed.

        The two halves annotate differently on purpose: the plan writes ``SetNormalMode()`` and the
        stage's report answers ``SetNormalMode (already normal)``, which is the same call — the words
        in the parentheses are the probe telling the owner *why* it was a no-op, not an argument. Every
        member that *does* take arguments spells them identically in both halves, which is what this
        comparison is for.
        """

        head, _, rest = call.partition("(")
        arguments = rest.rpartition(")")[0] if rest else ""
        if "already" in arguments:
            arguments = ""
        return f"{head.strip()}({arguments})"

    def _rehearse(self) -> tuple[dict[str, Any], _Client, list[dict[str, Any]], int]:
        live = self._live()
        state = live["state"]
        heroes = state["heroes"]
        for hero in heroes:
            for field in ("agent_id", "behavior", "disabled"):
                if not isinstance(hero.get(field), int):
                    self.skipTest(
                        f"the live report's hero {hero.get('position')} has no {field} reading "
                        f"({hero.get(field)!r}), so the plan was built with one too"
                    )
        if not isinstance(state["hard_mode"], bool):
            self.skipTest(f"the live report has no mode reading ({state['hard_mode']!r})")

        pet = state["pet"]
        world = _World(
            hero_flags=[
                _HeroFlag(int(hero["agent_id"]), int(hero["behavior"])) for hero in heroes
            ],
            skillbars=[
                _Skillbar(int(hero["agent_id"]), int(hero["disabled"])) for hero in heroes
            ],
            pets=[]
            if pet is None
            else [
                _Pet(
                    int(pet["agent_id"]),
                    int(pet["owner_agent_id"]),
                    int(pet["behavior"]),
                    int(pet["locked_target_id"]),
                )
            ],
            players=[],
            all_flag_array=tuple(state["all_flag"]),
        )

        client = _Client(world)
        context = mock.Mock()
        context.player_party = PartyInfoStruct().bind_reader(_ZeroReader(), 0x100000)
        context.in_hard_mode = bool(state["hard_mode"])
        context.party_id = 1
        client.party = context

        by_position = {
            int(hero["position"]): int(hero["agent_id"]) for hero in heroes
        }
        patches = (
            mock.patch("py4gw.client._current_client", client),
            mock.patch.object(Party, "_world", staticmethod(lambda: world)),
            mock.patch.object(Party, "_context", staticmethod(lambda: context)),
            mock.patch.object(Party, "GetHeroCount", staticmethod(lambda: len(heroes))),
            mock.patch.object(
                Party.Heroes,
                "GetHeroAgentIDByPartyPosition",
                staticmethod(lambda position: by_position.get(int(position), 1189)),
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

        report: dict[str, Any] = {}
        code = hold_stage(report)
        return report, client, live["hold_plan"], code

    def test_the_plan_names_exactly_the_calls_the_stage_makes(self) -> None:
        """Plan and stage agree on the members, the arguments and the order — on live values."""

        report, _, plan, _ = self._rehearse()

        self.assertEqual(
            [self._name(entry["call"]) for entry in plan],
            [self._name(key) for key in report["held"]],
            "the plan the owner reads and the calls the stage makes must be the same list, in the "
            "same order — a step in one half and not the other is what this catches",
        )

    def test_the_plan_is_the_calls_the_plan_says_they_are(self) -> None:
        """Each argument is checked too, not only the member names."""

        report, _, plan, _ = self._rehearse()

        held = list(report["held"])
        for index, entry in enumerate(plan):
            self.assertEqual(
                self._shape(held[index]),
                self._shape(entry["call"]),
                f"entry {index} of the plan and of the report describe different arguments",
            )

    def test_every_planned_call_is_refused_by_the_source_and_writes_nothing(self) -> None:
        """The plan's own claim — 'refused_by_the_source' — against the live values it was built on."""

        report, client, plan, code = self._rehearse()

        would_write = [
            entry
            for entry in plan
            if entry.get("refused_by_the_source") is False
        ]
        self.assertEqual(
            would_write,
            [],
            "the live plan contains a call whose value is not the one the client holds, so that "
            "call would write",
        )
        self.assertEqual(client.calls, [], "no client function was called")
        self.assertTrue(report["unchanged"], "and the state is identical afterwards")
        self.assertEqual(code, 0, "the stage reports success only when nothing moved")


class ActStepRehearsalTests(unittest.TestCase):
    """Each acting step, replayed offline: what it calls, and what it calls to get back.

    The steps that really act run only with the owner present, so what can be established beforehand is
    the **shape** of what will run: every step that changes the party calls its way back in the same
    breath, and the way back carries the value the step read — the hero's own behaviour word, the
    slot's own bit, the mode the party was already in. The members themselves are patched to a recorder
    here, because the assertion is about the arguments the *stage* chooses; whether a real client then
    accepts them is what the elevated run is for.
    """

    HERO = 1493

    def _run(
        self,
        step: str,
        calls: list[tuple[str, tuple[Any, ...]]],
        *,
        behavior: int = 1,
        disabled: int = 0,
        flag: tuple[float, float] = (float("inf"), float("inf")),
        outpost: bool = True,
        options: dict[str, Any] | None = None,
        player_count: int = 1,
        hero_in_party: bool = False,
        pet_id: int = 0,
        client_applies: bool = True,
        unlocked: bool = True,
    ) -> dict[str, Any]:
        # The probe spaces its acting calls out (``ACTION_INTERVAL_SECONDS``) because the client
        # processes one command at a time; a test that waited for real would take minutes.
        interval = mock.patch("tests.probe_party_live.ACTION_INTERVAL_SECONDS", 0.0)
        interval.start()
        self.addCleanup(interval.stop)
        world = _World(
            hero_flags=[_HeroFlag(self.HERO, behavior)],
            skillbars=[_Skillbar(self.HERO, disabled)],
            pets=[],
            players=[],
            all_flag_array=flag,
        )
        client = _Client(world)
        context = mock.Mock()
        context.player_party = PartyInfoStruct().bind_reader(_ZeroReader(), 0x100000)
        context.in_hard_mode = False
        context.party_id = 1
        client.party = context

        def recorder(name: str, apply: Any = None) -> Any:
            """Record the call, and — unless the test is modelling a client that never shows it —
            apply it to the stand-in, which is what a live client does when it processes the command.
            The steps wait for that ('settle'), so without it a stand-in would make every flip look
            like it never landed."""

            def record(*args: Any) -> None:
                calls.append((name, tuple(args)))
                if client_applies and apply is not None:
                    apply(*args)

            return record

        def apply_behavior(agent_id: Any, value: Any) -> None:
            for hero in world.hero_flags or []:
                if int(hero.agent_id) == int(agent_id):
                    hero.hero_behavior = int(value)

        def apply_skill_ai(agent_id: Any, slot: Any, enabled: Any) -> None:
            for bar in world.skillbars or []:
                if int(bar.agent_id) == int(agent_id):
                    bit = 1 << (int(slot) - 1)
                    bar.disabled = (
                        int(bar.disabled) & ~bit if enabled else int(bar.disabled) | bit
                    )

        patches = (
            mock.patch("py4gw.client._current_client", client),
            mock.patch.object(Party, "_world", staticmethod(lambda: world)),
            mock.patch.object(Party, "_context", staticmethod(lambda: context)),
            mock.patch.object(Party, "GetHeroCount", staticmethod(lambda: 1)),
            mock.patch.object(Party, "GetPlayerCount", staticmethod(lambda: player_count)),
            mock.patch.object(
                Party.Heroes,
                "GetHeroAgentIDByPartyPosition",
                staticmethod(lambda position: self.HERO if int(position) == 1 else 0),
            ),
            mock.patch.object(
                Party.Heroes,
                "GetHeroIDByPartyPosition",
                # Index 0, because that is what the member indexes: the hero **array**, 0-based.
                staticmethod(lambda index: 7 if hero_in_party and int(index) == 0 else -1),
            ),
            mock.patch.object(Party.Heroes, "GetHeroIdByName", staticmethod(lambda name: 7)),
            mock.patch.object(Party.Pets, "GetPetID", staticmethod(lambda owner: pet_id)),
            mock.patch.object(
                Party, "IsHardModeUnlocked", staticmethod(lambda: unlocked)
            ),
            mock.patch.object(Party.Heroes, "GetAllFlag", staticmethod(lambda: flag)),
            mock.patch("py4gw.map.Map.IsOutpost", staticmethod(lambda: outpost)),
            # The party window is a client frame and these stand-ins have none; what this class tests
            # is the step's other decisions, and the window guard has its own test.
            mock.patch(
                "tests.probe_party_live._party_window_on_screen", staticmethod(lambda: True)
            ),
            mock.patch.object(
                Party.Heroes, "FlagAllHeroes", staticmethod(recorder("FlagAllHeroes"))
            ),
            mock.patch.object(
                Party.Heroes, "UnflagAllHeroes", staticmethod(recorder("UnflagAllHeroes"))
            ),
            mock.patch.object(Party.Heroes, "FlagHero", staticmethod(recorder("FlagHero"))),
            mock.patch.object(Party.Heroes, "UnflagHero", staticmethod(recorder("UnflagHero"))),
            mock.patch.object(
                Party.Heroes,
                "SetHeroBehavior",
                staticmethod(recorder("SetHeroBehavior", apply_behavior)),
            ),
            mock.patch.object(
                Party.Heroes,
                "SetSkillAIEnabled",
                staticmethod(recorder("SetSkillAIEnabled", apply_skill_ai)),
            ),
            mock.patch.object(Party.Heroes, "UseSkill", staticmethod(recorder("UseSkill"))),
            mock.patch.object(
                Party.Heroes, "AddHeroByName", staticmethod(recorder("AddHeroByName"))
            ),
            mock.patch.object(
                Party.Heroes, "KickHeroByName", staticmethod(recorder("KickHeroByName"))
            ),
            mock.patch.object(
                Party.Henchmen, "AddHenchman", staticmethod(recorder("AddHenchman"))
            ),
            mock.patch.object(
                Party.Henchmen, "KickHenchman", staticmethod(recorder("KickHenchman"))
            ),
            mock.patch.object(Party, "LeaveParty", staticmethod(recorder("LeaveParty"))),
            mock.patch.object(
                Party, "ReturnToOutpost", staticmethod(recorder("ReturnToOutpost"))
            ),
            mock.patch.object(
                Party,
                "SetHardMode",
                staticmethod(
                    recorder(
                        "SetHardMode",
                        lambda: setattr(context, "in_hard_mode", True),
                    )
                ),
            ),
            mock.patch.object(
                Party,
                "SetNormalMode",
                staticmethod(
                    recorder(
                        "SetNormalMode",
                        lambda: setattr(context, "in_hard_mode", False),
                    )
                ),
            ),
            mock.patch.object(Party, "SearchParty", staticmethod(recorder("SearchParty"))),
            mock.patch.object(
                Party, "SearchPartyCancel", staticmethod(recorder("SearchPartyCancel"))
            ),
            mock.patch.object(
                Party.Pets, "SetPetBehavior", staticmethod(recorder("SetPetBehavior"))
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        report: dict[str, Any] = {}
        act_stage(report, {step}, options or {})
        return report

    def test_the_behaviour_step_flips_one_hero_and_restores_the_word_it_read(self) -> None:
        """The hero's own behaviour word, changed and put back in the same step."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        self._run("behaviour", calls, behavior=1)

        self.assertEqual(
            calls,
            [
                ("SetHeroBehavior", (self.HERO, 0)),
                ("SetHeroBehavior", (self.HERO, 1)),
            ],
            "the flip goes to another value and the restore back to the word read",
        )

    def test_the_skill_ai_step_flips_one_slot_and_restores_its_bit(self) -> None:
        """Slot 1's own ``disabled`` bit, inverted and then restored."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        self._run("skill-ai", calls, disabled=0)

        self.assertEqual(
            calls,
            [
                ("SetSkillAIEnabled", (self.HERO, 1, False)),
                ("SetSkillAIEnabled", (self.HERO, 1, True)),
            ],
        )

    def test_the_difficulty_step_leaves_the_mode_where_it_found_it(self) -> None:
        """Normal mode in, hard mode for the step, normal mode back."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        self._run("difficulty", calls, outpost=True, unlocked=True)

        self.assertEqual(calls, [("SetHardMode", ()), ("SetNormalMode", ())])

    def test_the_difficulty_step_refuses_when_the_account_has_no_hard_mode(self) -> None:
        """The live finding: the call is accepted and the client ignores it, so the step says why."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        report = self._run("difficulty", calls, outpost=True, unlocked=False)

        self.assertEqual(calls, [], "nothing is sent when the client cannot apply the mode")
        self.assertIn("not unlocked", str(report["acted"]["difficulty"]))

    def test_the_flags_step_unflags_what_it_flagged(self) -> None:
        """With a set flag the step flags it and clears it; with the live unset flag it only clears."""

        flagged: list[tuple[str, tuple[Any, ...]]] = []
        self._run("flags", flagged, flag=(123.5, -678.25))
        self.assertEqual(
            flagged,
            [
                ("FlagAllHeroes", (123.5, -678.25)),
                ("UnflagAllHeroes", ()),
            ],
            "the position it flags is the one the client reported",
        )

        unset: list[tuple[str, tuple[Any, ...]]] = []
        report = self._run("flags", unset, flag=(float("inf"), float("inf")))
        self.assertEqual(unset, [("UnflagAllHeroes", ())])
        self.assertIn("skipped", str(report["acted"]["FlagAllHeroes"]))

    def test_the_search_step_cancels_the_advertisement_it_opened(self) -> None:
        """The one step that opens a client window is closed again in the same step."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        self._run("search", calls)

        self.assertEqual([name for name, _ in calls], ["SearchParty", "SearchPartyCancel"])
        self.assertEqual(calls[0][1][1], "Stealth probe")

    def test_a_flip_and_restore_waits_for_the_client_to_show_the_flip(self) -> None:
        """The finding round 24's live run produced, pinned: the restore is computed after the flip lands.

        The client owns the record the member compares against, so a restore sent immediately reads the
        value it is replacing and its own guard refuses the write — the flip is then what stays. Here
        the stand-in applies what it is sent (a prompt client), and every step reports that it settled.
        """

        for step in ("behaviour", "skill-ai", "difficulty"):
            with self.subTest(step=step):
                calls: list[tuple[str, tuple[Any, ...]]] = []
                report = self._run(step, calls)
                self.assertTrue(
                    report["settled"],
                    f"{step}: the flip must be visible in the client's own records before the "
                    f"restore is computed — {report['acted']}",
                )
                landed = {
                    name: value
                    for name, value in report["acted"].items()
                    if isinstance(value, dict) and "settled" in value
                }
                self.assertTrue(landed, f"{step} reports what it waited for")
                for name, value in landed.items():
                    self.assertTrue(value["settled"], f"{step}: {name} -> {value}")
                # The state the step started from is the state it left, and the stand-in proves it by
                # holding the values it applied.
                self.assertEqual(report["before"], report["after"], f"{step} put the state back")

    def test_a_client_that_never_shows_the_change_is_reported_and_not_waited_on(self) -> None:
        """A client that does not apply the flip is a fact in the report, not a hang and not a lie."""

        calls: list[tuple[str, tuple[Any, ...]]] = []
        with mock.patch(
            "tests.probe_party_live.SETTLE_TIMEOUT_SECONDS", 0.05
        ):
            report = self._run("behaviour", calls, client_applies=False)

        self.assertFalse(report["settled"])
        self.assertEqual(
            calls,
            [
                ("SetHeroBehavior", (self.HERO, 0)),
                ("SetHeroBehavior", (self.HERO, 1)),
            ],
            "the restore is still sent with the value the step read, not with the flip it sent",
        )
        self.assertFalse(
            report["acted"]["SetHeroBehavior(other) landed"]["settled"],
            "the flip never appeared in the client's records, and the report says so",
        )
        self.assertFalse(
            report["acted"]["SetHeroBehavior(other) landed"].get("expected") is None,
            "a step that did not land names the value it was waiting for",
        )

    def test_the_flag_hero_step_flags_one_hero_and_unflags_it(self) -> None:
        """A set flag gives the member a position; the live unset flag means the step skips."""

        flagged: list[tuple[str, tuple[Any, ...]]] = []
        self._run("flag-hero", flagged, flag=(10.5, -4.0))
        self.assertEqual(
            flagged,
            [
                ("FlagHero", (self.HERO, 10.5, -4.0)),
                ("UnflagHero", (1,)),
            ],
            "the member takes an agent id; its counterpart takes the hero's party position",
        )

        unset: list[tuple[str, tuple[Any, ...]]] = []
        report = self._run("flag-hero", unset, flag=(float("inf"), float("inf")))
        self.assertEqual(unset, [])
        self.assertIn("skipped", str(report["acted"]["FlagHero"]))

    def test_the_use_skill_step_presses_the_named_hero_and_slot(self) -> None:
        """The step is driven by the owner's numbers, and passes native's own ``0`` for no target."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        self._run("use-skill", calls, options={"hero_number": 1, "slot": 2})

        self.assertEqual(calls, [("UseSkill", (1, 2, 0))])

    def test_the_party_add_step_adds_the_named_hero_and_only_a_named_henchman(self) -> None:
        """``AddHeroByName`` takes the name; the henchman's id is the owner's, so it is never guessed."""

        without: list[tuple[str, tuple[Any, ...]]] = []
        report = self._run("party-add", without)
        self.assertEqual(without, [("AddHeroByName", ("Norgu",))])
        self.assertIn("--henchman", str(report["acted"]["AddHenchman"]))

        with_id: list[tuple[str, tuple[Any, ...]]] = []
        self._run("party-add", with_id, options={"henchman_id": 4242})
        self.assertEqual(
            with_id, [("AddHeroByName", ("Norgu",)), ("AddHenchman", (4242,))]
        )

        outside: list[tuple[str, tuple[Any, ...]]] = []
        report = self._run("party-add", outside, outpost=False)
        self.assertEqual(outside, [], "the client only accepts a party change in an outpost")
        self.assertIn("skipped", str(report["acted"]["AddHeroByName"]))

    def test_the_party_kick_step_kicks_only_what_is_there(self) -> None:
        """Norgu is not in the live party, so the hero half refuses; the henchman half needs the id."""

        absent: list[tuple[str, tuple[Any, ...]]] = []
        report = self._run("party-kick", absent)
        self.assertEqual(absent, [])
        self.assertIn("not in this party", str(report["acted"]["KickHeroByName"]))

        present: list[tuple[str, tuple[Any, ...]]] = []
        self._run("party-kick", present, hero_in_party=True)
        self.assertEqual(present, [("KickHeroByName", ("Norgu",))])

        with_id: list[tuple[str, tuple[Any, ...]]] = []
        self._run("party-kick", with_id, hero_in_party=True, options={"henchman_id": 4242})
        self.assertEqual(
            with_id, [("KickHeroByName", ("Norgu",)), ("KickHenchman", (4242,))]
        )

    def test_a_party_of_one_hero_finds_him_at_index_zero(self) -> None:
        """Round 25's live finding: ``GetHeroIDByPartyPosition`` is 0-based, so index 0 is a member.

        The guard used to walk ``range(1, hero_count + 1)``, which for a party of exactly one hero
        looked at index 1 and found nothing — the step then reported "not in this party" and skipped a
        kick the owner had asked for. A single hero lives at index 0.
        """

        calls: list[tuple[str, tuple[Any, ...]]] = []

        report = self._run("party-kick", calls, hero_in_party=True)

        self.assertEqual(
            calls,
            [("KickHeroByName", ("Norgu",))],
            f"a hero at index 0 is in the party — {report['acted']}",
        )

    def test_the_leave_step_needs_somebody_else_in_the_party(self) -> None:
        """A party of one has nothing to leave, and the step says so instead of pressing the button."""

        alone: list[tuple[str, tuple[Any, ...]]] = []
        report = self._run("leave", alone, player_count=1)
        self.assertEqual(alone, [])
        self.assertIn("skipped", str(report["acted"]["LeaveParty"]))

        together: list[tuple[str, tuple[Any, ...]]] = []
        self._run("leave", together, player_count=2)
        self.assertEqual(together, [("LeaveParty", ())])

    def test_the_outpost_step_calls_the_member_that_checks_the_button_itself(self) -> None:
        """The member answers ``False`` when its button is not on screen — the step does not decide."""

        calls: list[tuple[str, tuple[Any, ...]]] = []

        report = self._run("outpost", calls, outpost=False)

        self.assertEqual(calls, [("ReturnToOutpost", ())])
        self.assertIs(report["map_is_outpost"], False)

    def test_the_pet_step_needs_a_pet_to_drive(self) -> None:
        """``Fight`` with no target is the call the source's own body writes nothing for."""

        without: list[tuple[str, tuple[Any, ...]]] = []
        self._run("pet", without, pet_id=0)
        self.assertEqual(without, [], "no pet in this party, so the step leaves the member alone")

        with_pet: list[tuple[str, tuple[Any, ...]]] = []
        self._run("pet", with_pet, pet_id=30)
        self.assertEqual(with_pet, [("SetPetBehavior", (0, 0))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
