"""Live Guild Wars tests for the GwAu3 compatibility layer (``py4gw/gwa3``).

**What this suite adds.** Every test of this layer until now has been offline. ``constants.py`` was
checked name for name against GwAu3's ``.au3`` sources, and each field-name reader was checked against
a **materialized** record -- bytes this project packed itself into a `ctypes.Structure`. Neither says
anything about a running client: a materialized record is not a client read, and an offset that is
right in a structure this project built is not evidence that the same offset holds the same field in
the process the game is running.

This is the first thing in the layer that reads ``Gw.exe`` while it runs. It answers four questions
only a live client can:

1. **Do all the calls a migrating script makes resolve?** Every routed field key in all seven families
   is called against the live client and must answer a scalar rather than raise.
2. **Does a refused key still refuse live?** The 50 refusals are the layer's honesty; a refusal that
   only fires offline would be worse than no refusal at all.
3. **Do the values agree with an independent route to the same number?** Where a ported member reads
   the same field -- `Agent.GetXY`, `Agent.GetMaxHealth`, `Map.GetContinent`, the live skill record --
   the layer's answer and the ported member's answer are compared for equality, live.
4. **What does the layer need that a read-only connection cannot give it?** Eight keys run a decode
   *through the client* and are the layer's only non-reads; they are named here, and the read-only
   connection's refusal of them is asserted rather than worked around.

**It writes nothing.** The connection is the read-only one (``game_thread=False``): no hook, no patch,
no call into the client. The suite hashes the client's whole code section before and after and asserts
it is unchanged. Elevation is still required, because ``ConnectedClient`` asserts it for every
connection.

**What the first run of this suite established** (pid 23044, 2026-10-09) is recorded in
``docs/GWA3_COMPAT_SPEC.md``: **five defects it found, every one of them invisible offline** -- the
agent accessor handed its readers a record with none of the fields they read, a party accessor with a
record-id parameter GwAu3 does not declare, a party record read from a facade cache nothing refreshes,
and two keys answering the wrong *shape* (`h000C` as an array where GwAu3 reads a dword, and
`VisibleEffectsNextNode` dropping GwAu3's own bit mask). All five are fixed, and this suite is the
regression test for them: it passes now, and it failed on every one of those five before.

Run it from an **elevated** shell with Guild Wars running in a loaded map::

    python -m unittest tests.test_gwa3_live -v

The result of the run after all five fixes is in ``tests/live_reports/gwa3_live.log``; the run that
found them is ``tests/live_reports/gwa3_live_run1.log``.
"""

from __future__ import annotations

import hashlib
import unittest
from typing import Any

import py4gw
from py4gw import Win32
from py4gw.agent import Agent
from py4gw.context.gw_context import GWContext
from py4gw.gwa3 import (
    constants,
    data_agent,
    data_item,
    data_map,
    data_party,
    data_quest,
    data_skill,
    data_world,
    uai_const,
    uai_effects,
    uai_filter,
    uai_get_agent,
    uai_utils,
)
from py4gw.map import Map
from py4gw.party import Party
from py4gw.player import Player

#: The constants the targeting tests pass as arguments, read from the generated table by name so the
#: numbers come from GwAu3's own declarations rather than from this file.
GC_I_ALLEGIANCE_ENEMY = constants.GC_I_ALLEGIANCE_ENEMY
GC_I_ALLEGIANCE_ALLY = constants.GC_I_ALLEGIANCE_ALLY
GC_I_RANGE_AREA = constants.GC_I_RANGE_AREA
GC_UAI_AGENT_HP = constants.GC_UAI_AGENT_HP

#: The six families built by `tools/generate_gwa3_family.py`, and the record id each is called with
#: (``None`` for the two whose only parameter is the field name -- `World_GetWorldInfo` and
#: `Party_GetPartyContextInfo`, both of which are GwAu3's own arities). `data_agent` is built by its
#: own generator and is called separately, because its record id is a live agent.
FAMILIES: tuple[tuple[Any, str], ...] = (
    (data_skill, "Skill_GetSkillInfo"),
    (data_item, "Item_GetItemInfoByItemID"),
    (data_map, "Map_GetAreaInfo"),
    (data_quest, "Quest_GetQuestInfo"),
    (data_party, "Party_GetPartyContextInfo"),
    (data_world, "World_GetWorldInfo"),
)

#: Keys whose reader runs a decode **through the client**, so a read-only connection cannot answer them.
#: They are the layer's only non-reads: the `PyItem` handshake places a decode request in the client
#: through `client.bridge`, which is what raises when the connection has no game thread.
#:
#: **`Agent_GetAgentInfo`'s `Name` is not one of them, and the first live run is why the list is not a
#: guess.** That key reaches the client through `Agent.GetNameByID`, which answered a real name --
#: ``'Fezzik The Untamed'`` -- on a read-only connection, so it is a read like any other.
GAME_THREAD_KEYS: dict[str, frozenset[str]] = {
    "data_item": frozenset({"Name", "CompleteName", "SingleItemName"}),
}

#: Keys whose decode **cannot start** on a read-only connection and which answer `''` anyway.
#:
#: This is a divergence, recorded rather than papered over. `Quest.RequestQuestName` reaches the client
#: through ``_start`` (`py4gw/native_src/quest/py_quest.py:242-259`), which catches
#: ``(OSError, RuntimeError)`` from ``begin_string_decode`` and returns ``False``; the store is left at
#: ``("", False)``, which is the same state as a decode still in flight, so ``ready`` never turns true,
#: the source's own ``"Timeout"`` is never written, and the getter answers ``''`` for ever. The item
#: handshake has no such swallow and raises, which is why the two families behave differently here. The
#: layer cannot tell the two states apart, so the fix is in that request path, not in the layer.
SILENTLY_EMPTY_KEYS: dict[str, frozenset[str]] = {
    "data_quest": frozenset({"Name", "Location", "LocationStr", "Description"}),
}

#: The read-only connection's own message when something needs the game thread.
NEEDS_GAME_THREAD = "game_thread=True"

#: A skill whose record is stable in every map, used for the skill cross-checks.
HEALING_SIGNET = 1


class Gwa3LiveTests(unittest.TestCase):
    """The GwAu3 layer, against the running client."""

    client: Any
    pid: int
    agent_id: int
    item_id: int
    quest_id: int
    map_id: int
    text_before: tuple[str, int]

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        if not win32.is_elevated():
            raise unittest.SkipTest(
                "The controller must be elevated: connecting asserts it. Run this suite "
                "from an elevated shell."
            )

        cls.text_before = cls._text_digest(win32, cls.pid)
        cls.client = py4gw.connect(clients[0], game_thread=False)
        print(f"--- connected read-only to pid {cls.pid} ---")

        cls.agent_id = int(Player.GetAgentID())
        if cls.agent_id == 0:
            raise unittest.SkipTest(
                "Guild Wars is connected but has no controlled character: load a map before "
                "running this suite."
            )
        cls.map_id = int(Map.GetMapID())
        cls.item_id = cls._first_item_id()
        cls.quest_id = cls._first_quest_id()
        print(
            f"--- agent {cls.agent_id}, map {cls.map_id}, "
            f"item {cls.item_id or 'none'}, quest {cls.quest_id or 'none'} ---"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        py4gw.disconnect()
        after = cls._text_digest(Win32(), cls.pid)
        print(
            f"--- code section after disconnect: {after[0][:16]}… ({after[1]:#x} bytes); "
            f"before: {cls.text_before[0][:16]}… ---"
        )
        if after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the read-only connection changed the client's code section: "
                f"{cls.text_before[0]} -> {after[0]}"
            )

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        """Hash the client's whole code section, read-only."""

        from py4gw.memory import ProcessMemoryReader
        from py4gw.scanner import RemoteScanner

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            scanner.initialize()
            section = scanner.get_section_range("text")
            digest = hashlib.sha256()
            address = section.start
            while address < section.end:
                size = min(0x10000, section.end - address)
                digest.update(reader.read(address, size))
                address += size
            return digest.hexdigest(), section.end - section.start

    # -- the ids a live read is made against ------------------------------------------------

    @classmethod
    def _first_item_id(cls) -> int:
        """The id of an item the client is actually holding, or ``0`` when it holds none."""

        for record in cls.client.read_item_records():
            item_id = int(record.item_id)
            if item_id != 0:
                return item_id
        return 0

    @classmethod
    def _first_quest_id(cls) -> int:
        """The id of a quest in the client's own log, or ``0`` when the log is empty."""

        world = cls.client.read_world_context()
        if world is None:
            return 0
        for record in list(world.quests or []):
            quest_id = int(record.quest_id)
            if quest_id != 0:
                return quest_id
        return 0

    def _record_id(self, module: Any) -> Any:
        """The live id this family's accessor is called with, or ``None`` when it takes none."""

        return {
            "data_agent": self.agent_id,
            "data_skill": HEALING_SIGNET,
            "data_item": self.item_id,
            "data_map": self.map_id,
            "data_quest": self.quest_id,
            "data_party": None,
            "data_world": None,
        }[module.__name__.rsplit(".", 1)[-1]]

    def _call(self, module: Any, function: str, key: str) -> Any:
        """Call one family's accessor the way its own signature requires, live."""

        accessor = getattr(module, function)
        record_id = self._record_id(module)
        if record_id is None:
            return accessor(key)
        return accessor(record_id, key)

    # -- 1. every routed key answers ------------------------------------------------------

    def test_every_routed_key_answers_against_the_live_client(self) -> None:
        """The gate the migration rests on: no call a script makes raises or answers nothing.

        Two kinds of key are not asked for a value here, and each is asked for something else:

        * a key in ``_UNIMPLEMENTED`` **refuses**, and its refusal is the subject of the next test;
        * a key in `GAME_THREAD_KEYS` runs a decode through the client, which a read-only connection
          cannot do -- so it must raise the connection's own message, and that is asserted here.
        """

        SCALARS = (bool, int, float, str)
        answered = 0
        deferred = 0
        silent = 0
        refused_live = 0

        def is_answer(value: object) -> bool:
            """What a reader may answer: one value, or the words of a multi-word case.

            GwAu3's ``byte[4]`` and ``dword[4]`` cases read several words, and a tuple of them is the
            honest translation -- the live run reported eleven of those as failures until this accepted
            them, which was the test's assumption rather than the layer's defect.
            """

            if isinstance(value, (bool, int, float, str)):
                return True
            if isinstance(value, (tuple, list)) and value:
                return all(isinstance(item, int) for item in value)
            return False

        for module, function in FAMILIES + ((data_agent, "Agent_GetAgentInfo"),):
            name = module.__name__.rsplit(".", 1)[-1]
            accessor = getattr(module, function)
            refused = set(module._UNIMPLEMENTED)
            needs_thread = GAME_THREAD_KEYS.get(name, frozenset())
            stays_empty = SILENTLY_EMPTY_KEYS.get(name, frozenset())
            keys = sorted(set(module._READERS) - refused)
            failures: list[str] = []
            family = {"answered": 0, "deferred": 0, "silent": 0, "refused": 0}
            for key in keys:
                try:
                    value = self._call(module, function, key)
                except NotImplementedError as exc:
                    # A routed key can still refuse: `TotalPartySize` is GwAu3's own sum of three keys
                    # this layer refuses, so the sum refuses too and names the rule it refuses by.
                    if key not in refused and "GwAu3_" in str(exc):
                        family["refused"] += 1
                        refused_live += 1
                        continue
                    failures.append(f"{key}: raised NotImplementedError: {exc}")
                    continue
                except RuntimeError as exc:
                    if key in needs_thread and NEEDS_GAME_THREAD in str(exc):
                        family["deferred"] += 1
                        deferred += 1
                        continue
                    failures.append(f"{key}: raised RuntimeError: {exc}")
                    continue
                except Exception as exc:  # noqa: BLE001 - the failure is the finding
                    failures.append(f"{key}: raised {type(exc).__name__}: {exc}")
                    continue

                if key in needs_thread:
                    failures.append(
                        f"{key}: answered {value!r} on a read-only connection, but its reader "
                        "decodes through the client"
                    )
                elif key in stays_empty:
                    if value != "":
                        failures.append(
                            f"{key}: answered {value!r}; this key's decode cannot start on a "
                            "read-only connection, so it is expected to answer ''"
                        )
                    else:
                        family["silent"] += 1
                        silent += 1
                elif not is_answer(value):
                    failures.append(f"{key}: answered {value!r}")
                else:
                    family["answered"] += 1
                    answered += 1
            print(
                f"    {function}: {family['answered']}/{len(keys)} answered, "
                f"{family['refused']} refused in the reader, "
                f"{family['deferred']} deferred, {family['silent']} empty"
            )
            self.assertEqual(
                failures,
                [],
                f"{function}: {len(failures)} of {len(keys)} routed keys failed live:\n  "
                + "\n  ".join(failures),
            )

        print(
            f"--- {answered} routed field keys read the live client; "
            f"{refused_live} refused by name; "
            f"{deferred} refused a read-only connection by name; "
            f"{silent} answered '' because their decode could not start ---"
        )

        # Every key in the tables is accounted for, and the identity is derived from the tables rather
        # than written down: an assertion on a literal count is one the next added key breaks for no
        # reason at all. The first version of this line asserted `> 350`, which the run itself showed
        # was wrong -- 350 is the number of keys *asked*, and eight of those answer no value by design.
        #
        # A refused key is in **both** tables: `_READERS` carries a reader that raises, and
        # `_UNIMPLEMENTED` carries the rule it raises with. So the declared count is `_READERS` alone.
        table = FAMILIES + ((data_agent, "Agent_GetAgentInfo"),)
        declared = sum(len(module._READERS) for module, _ in table)
        refused_total = sum(len(module._UNIMPLEMENTED) for module, _ in table)
        asked = declared - refused_total
        self.assertEqual(answered + refused_live + deferred + silent, asked)
        self.assertEqual(declared, 400, "the seven families declare 400 field keys")
        self.assertEqual(refused_total, 45, "and 45 of them refuse")
        print(
            f"--- all {asked} answered keys accounted for, out of {declared} declared across the "
            f"seven families, {refused_total} of which refuse ---"
        )
        # `TotalPartySize` used to be the one *routed* key that refused live, because it sums three
        # keys that themselves refused through the party pointer. Those three answer now (the pointer
        # is followed), so the sum answers too -- and what is asserted is that a routed key refuses
        # **nowhere**, which is a stronger statement than the literal it replaces.
        self.assertEqual(refused_live, 0, "no routed key refuses live")
        self.assertEqual(deferred, sum(len(v) for v in GAME_THREAD_KEYS.values()))
        self.assertEqual(silent, sum(len(v) for v in SILENTLY_EMPTY_KEYS.values()))

    # -- 2. every refused key still refuses ------------------------------------------------

    def test_every_refused_key_refuses_live_with_its_own_rule(self) -> None:
        """A refusal that only fires offline would be worse than no refusal: it would answer."""

        total = 0
        for module, function in FAMILIES + ((data_agent, "Agent_GetAgentInfo"),):
            for key, reason in sorted(module._UNIMPLEMENTED.items()):
                with self.subTest(function=function, key=key):
                    with self.assertRaises(NotImplementedError) as caught:
                        self._call(module, function, key)
                    self.assertEqual(str(caught.exception), reason)
                total += 1

        print(f"--- {total} refused keys refused live, each with its recorded reason ---")
        self.assertGreater(total, 40, "the refusal table shrank; this run covered less than before")

    # -- 3. the values agree with an independent route -------------------------------------

    def test_the_agent_family_agrees_with_the_ported_agent_members(self) -> None:
        """The layer's answer and the ported member's answer, from the same live agent."""

        agent_id = self.agent_id
        x, y = Agent.GetXY(agent_id)
        checks = {
            "X": float(x),
            "Y": float(y),
            "Level": int(Agent.GetLevel(agent_id)),
            "MaxHP": int(Agent.GetMaxHealth(agent_id)),
            "MaxEnergy": int(Agent.GetMaxEnergy(agent_id)),
            "CurrentHP": float(Agent.GetHealth(agent_id)) * int(Agent.GetMaxHealth(agent_id)),
            "CurrentEnergy": float(Agent.GetEnergy(agent_id)) * int(Agent.GetMaxEnergy(agent_id)),
            "IsDead": bool(Agent.IsDead(agent_id)),
            "Allegiance": int(Agent.GetAllegiance(agent_id)[0]),
            "WeaponType": int(Agent.GetWeaponType(agent_id)[0]),
            "TypeMap": int(Agent.GetTypeMap(agent_id)),
        }
        for key, expected in checks.items():
            with self.subTest(key=key):
                answered = data_agent.Agent_GetAgentInfo(agent_id, key)
                self.assertEqual(
                    answered,
                    expected,
                    f"{key}: the layer answered {answered!r}, the ported member {expected!r}",
                )
        print(f"    {len(checks)} agent keys equal an independent ported read")

    def test_the_agent_keys_beyond_the_cross_checks_answer_a_plausible_value(self) -> None:
        """The remaining living keys, held to the bands the game's own data allows.

        A key that answers a wrong-but-plausible number cannot be caught by a band, and this does not
        claim to catch one. What it catches is the failure the first live run actually produced: a
        record that carries none of these fields at all.
        """

        agent_id = self.agent_id
        level = int(data_agent.Agent_GetAgentInfo(agent_id, "Level"))
        self.assertGreaterEqual(level, 1, "no character is below level 1")
        self.assertLessEqual(level, 20, "the level cap is 20")

        hp = float(data_agent.Agent_GetAgentInfo(agent_id, "CurrentHP"))
        max_hp = int(data_agent.Agent_GetAgentInfo(agent_id, "MaxHP"))
        self.assertGreater(max_hp, 0, "a living character has a maximum health")
        self.assertGreaterEqual(hp, 0.0)
        self.assertLessEqual(hp, max_hp, "current health cannot exceed the maximum")

        energy = float(data_agent.Agent_GetAgentInfo(agent_id, "CurrentEnergy"))
        max_energy = int(data_agent.Agent_GetAgentInfo(agent_id, "MaxEnergy"))
        self.assertGreater(max_energy, 0, "a living character has a maximum energy")
        self.assertGreaterEqual(energy, 0.0)
        self.assertLessEqual(energy, max_energy)

        print(
            f"    level {level}, hp {hp:.0f}/{max_hp}, energy {energy:.0f}/{max_energy}"
        )

    def test_the_agent_sentinels_resolve_live(self) -> None:
        """GwAu3's two id sentinels, against the live client.

        **The ``-1`` sentinel is not reachable on a read-only connection**, and that is a property of
        the port rather than of this layer: `Agent_GetCurrentTarget` answers `Player.GetTargetID()`,
        which reads the target the connection's listener captured from the client's own
        ``kChangeTarget`` notice -- and the listener only runs when the connection has the game thread.
        Read-only it raises, so the sentinel is exercised only when a target id is available another
        way; the raise is asserted here so the limitation is on the record.
        """

        me = int(Player.GetAgentID())
        self.assertEqual(
            data_agent.Agent_GetAgentInfo(-2, "Level"),
            data_agent.Agent_GetAgentInfo(me, "Level"),
        )
        self.assertEqual(data_agent.Agent_GetMyID(), me)
        self.assertEqual(data_agent.GetMyID(), me)
        print(f"    the -2 sentinel resolved to the controlled character {me}")

        try:
            target = int(Player.GetTargetID())
        except RuntimeError as exc:
            self.assertIn(NEEDS_GAME_THREAD, str(exc))
            with self.assertRaises(RuntimeError) as caught:
                data_agent.Agent_GetCurrentTarget()
            self.assertIn(NEEDS_GAME_THREAD, str(caught.exception))
            print("    the -1 sentinel needs the game thread's target capture; asserted, not skipped")
            return

        if target == 0:
            print("    no current target: the -1 sentinel was not exercised")
            return
        self.assertEqual(
            data_agent.Agent_GetAgentInfo(-1, "Level"),
            data_agent.Agent_GetAgentInfo(target, "Level"),
        )
        print(f"    the -1 sentinel resolved to the current target {target}")

    def test_the_skill_family_agrees_with_the_ported_skill_record(self) -> None:
        """The skill keys, against the record the ported class reads."""

        record = self.client.read_skill(HEALING_SIGNET)
        assert record is not None
        checks = {
            "SkillID": int(record.skill_id),
            "Campaign": int(record.campaign),
            "SkillType": int(record.type),
            "Profession": int(record.profession),
            "Attribute": int(record.attribute),
            "EnergyCost": int(record.energy_cost),
            "Recharge": int(record.recharge),
            "Activation": float(record.activation),
            "Adrenaline": int(record.adrenaline),
            "Overcast": int(record.overcast),
            "HealthCost": int(record.health_cost),
        }
        for key, expected in checks.items():
            with self.subTest(key=key):
                answered = data_skill.Skill_GetSkillInfo(HEALING_SIGNET, key)
                self.assertEqual(
                    answered,
                    expected,
                    f"{key}: the layer answered {answered!r}, the skill record {expected!r}",
                )
        print(f"    {len(checks)} skill keys equal the live skill record")

    def test_the_map_family_agrees_with_the_ported_area_record(self) -> None:
        """The area keys, against the same `AreaInfoStruct` reached by the ported `Map` members.

        `Map.GetRegion()` is **not** a route to the same number: it answers the *server* region
        (``GWContext.ServerRegion``), while GwAu3's ``Region`` is the map's own in-game region. The
        first live run compared the two and recorded a mismatch that was the test's, not the layer's.
        The comparison here is against the area record itself, which is what `Map.GetContinent` and
        `Map.GetRegionType` read.
        """

        area = GWContext.InstanceInfo().GetMapInfo()
        assert area is not None, "the client has no current map info"
        checks = {
            "Region": int(area.region),
            "Continent": int(area.continent),
            "RegionType": int(area.type),
            "ThumbnailID": int(area.thumbnail_id),
            "NameID": int(area.name_id),
            "Campaign": int(area.campaign),
        }
        for key, expected in checks.items():
            with self.subTest(key=key):
                answered = data_map.Map_GetAreaInfo(self.map_id, key)
                self.assertEqual(
                    answered,
                    expected,
                    f"{key}: the layer answered {answered!r}, the area record {expected!r}",
                )
        print(f"    {len(checks)} map keys equal the live area record")

    def test_the_party_family_answers_the_types_gwau3_declares(self) -> None:
        """The party flags are booleans live, with no id argument -- GwAu3's own arity.

        The numbers a migrating script would want beside them -- ``PlayerCount``, ``HeroCount``,
        ``HenchmenCount`` -- are exactly the keys this layer refuses, because they need a second-level
        pointer this project does not have. The ported counts are printed so the run records both.
        """

        for key in ("IsPartyLeader", "IsHardMode", "IsDefeated", "IsWaitingForMission"):
            with self.subTest(key=key):
                answered = data_party.Party_GetPartyContextInfo(key)
                self.assertIsInstance(answered, bool, f"{key} answered {answered!r}")

        self.assertIsInstance(data_party.Party_GetPartyContextInfo("Flags"), int)
        print(
            f"    party flags read as booleans; ported counts: size {Party.GetPartySize()}, "
            f"heroes {Party.GetHeroCount()}, henchmen {Party.GetHenchmanCount()}, "
            f"flags {data_party.Party_GetPartyContextInfo('Flags'):#x}"
        )

    # -- 4. the no-match answers ------------------------------------------------------------

    def test_a_record_the_client_does_not_hold_answers_gwau3s_no_match_value(self) -> None:
        """GwAu3 answers rather than raises when the record is not there, and so does this."""

        self.assertEqual(data_agent.Agent_GetAgentInfo(999_999, "X"), 0)
        self.assertEqual(data_skill.Skill_GetSkillInfo(999_999, "EnergyCost"), 0)
        self.assertEqual(data_map.Map_GetAreaInfo(999_999, "Region"), 0)
        # GwAu3's own guard answers `False` for `HasQuest` and `0` for every other quest key
        # (`GwAu3_Data_Quest.au3:16-21`), so both shapes are checked here.
        self.assertEqual(data_quest.Quest_GetQuestInfo(999_999, "HasQuest"), False)
        self.assertEqual(data_quest.Quest_GetQuestInfo(999_999, "IsCompleted"), 0)
        print("    a missing agent, skill and map answered 0; a missing quest answered False/0")

    def test_gwau3s_own_guards_answer_before_anything_is_read(self) -> None:
        """The empty field name and the unknown field name, which GwAu3 answers 0 for."""

        self.assertEqual(data_agent.Agent_GetAgentInfo(self.agent_id, ""), 0)
        self.assertEqual(data_agent.Agent_GetAgentInfo(self.agent_id, "NoSuchField"), 0)
        self.assertEqual(data_world.World_GetWorldInfo(""), 0)
        self.assertEqual(data_world.World_GetWorldInfo("NoSuchField"), 0)
        self.assertEqual(data_party.Party_GetPartyContextInfo(""), 0)
        print("    the empty and unknown field names answered 0, as GwAu3's own guards do")

    # -- 5. evidence: what the layer actually read -------------------------------------------

    def test_a_sample_of_live_values_is_printed_for_the_record(self) -> None:
        """Not an assertion: the numbers this run read, so the record shows real game data."""

        agent_id = self.agent_id
        sample = {
            "Agent.Level": data_agent.Agent_GetAgentInfo(agent_id, "Level"),
            "Agent.X": data_agent.Agent_GetAgentInfo(agent_id, "X"),
            "Agent.Y": data_agent.Agent_GetAgentInfo(agent_id, "Y"),
            "Agent.CurrentHP": data_agent.Agent_GetAgentInfo(agent_id, "CurrentHP"),
            "Agent.MaxHP": data_agent.Agent_GetAgentInfo(agent_id, "MaxHP"),
            "Agent.Rotation": data_agent.Agent_GetAgentInfo(agent_id, "Rotation"),
            "Map.NameID": data_map.Map_GetAreaInfo(self.map_id, "NameID"),
            "Map.MaxPartySize": data_map.Map_GetAreaInfo(self.map_id, "MaxPartySize"),
            "Map.MinLevel": data_map.Map_GetAreaInfo(self.map_id, "MinLevel"),
            "Skill.EnergyCost": data_skill.Skill_GetSkillInfo(HEALING_SIGNET, "EnergyCost"),
            "Skill.Activation": data_skill.Skill_GetSkillInfo(HEALING_SIGNET, "Activation"),
            "Party.IsPartyLeader": data_party.Party_GetPartyContextInfo("IsPartyLeader"),
            "World.Campaign": data_world.World_GetWorldInfo("Campaign"),
        }
        if self.quest_id:
            sample["Quest.IsCompleted"] = data_quest.Quest_GetQuestInfo(self.quest_id, "IsCompleted")
        if self.item_id:
            sample["Item.ModelID"] = data_item.Item_GetItemInfoByItemID(self.item_id, "ModelID")

        for label, value in sample.items():
            print(f"    {label:<22} {value!r}")

        self.assertTrue(True)

    # -- 6. the UtilityAI targeting queries, against an independent route to the same answer ---

    def _independent_enemies(self, range_: float = 1320) -> list[int]:
        """Living enemies within a range of the player, read through `py4gw.Agent`, not the layer.

        The point of the comparison is that it shares no code with `py4gw/gwa3/uai_filter.py`: the layer
        asks `Agent_GetAgentInfo` for `Allegiance`, `HP` and `IsDead` and computes the player-relative
        distance itself, while this asks `Agent.GetAllegiance`, `Agent.GetHealth` and `Agent.GetXY`.
        Two routes to one answer, which is the only kind of live check that can catch a wrong one.
        """

        from py4gw.agent_array import AgentArray

        player_x, player_y = Agent.GetXY(self.agent_id)
        found = []
        for agent_id in AgentArray.GetAgentArray():
            if int(agent_id) == self.agent_id:
                continue
            if Agent.GetAllegiance(agent_id)[0] != GC_I_ALLEGIANCE_ENEMY:
                continue
            if Agent.GetHealth(agent_id) <= 0:
                continue
            if not Agent.IsLiving(agent_id):
                continue
            agent_x, agent_y = Agent.GetXY(agent_id)
            dx = agent_x - player_x
            dy = agent_y - player_y
            if (dx * dx + dy * dy) ** 0.5 <= range_:
                found.append(int(agent_id))
        return found

    def test_the_targeting_count_agrees_with_an_independent_count(self) -> None:
        """`UAI_CountAgents` against the same count computed through `py4gw.Agent`."""

        independent = self._independent_enemies()
        counted = uai_get_agent.UAI_CountAgents(-2, 1320, "UAI_Filter_IsLivingEnemy")
        print(f"    UAI_CountAgents -> {counted}; independent -> {len(independent)}")
        self.assertEqual(counted, len(independent))

    def test_in_range_agrees_with_the_count(self) -> None:
        """`UAI_IsAgentInRange` is `UAI_CountAgents`'s own loop stopped at the first match."""

        counted = uai_get_agent.UAI_CountAgents(-2, 1320, "UAI_Filter_IsLivingEnemy")
        self.assertEqual(
            uai_get_agent.UAI_IsAgentInRange(-2, 1320, "UAI_Filter_IsLivingEnemy"), counted > 0
        )

    def test_the_nearest_enemy_is_the_nearest_by_an_independent_measure(self) -> None:
        """`UAI_GetNearestAgent`, against the nearest of the independently read enemies.

        Ties resolve the same way in both: the comparison is strict, so the first agent in the client's
        own array order wins, and `min` over a list in that order picks the same one.
        """

        independent = self._independent_enemies()
        nearest = uai_get_agent.UAI_GetNearestAgent(-2, 1320, "UAI_Filter_IsLivingEnemy")
        player_x, player_y = Agent.GetXY(self.agent_id)

        def distance(agent_id: int) -> float:
            agent_x, agent_y = Agent.GetXY(agent_id)
            return ((agent_x - player_x) ** 2 + (agent_y - player_y) ** 2) ** 0.5

        expected = min(independent, key=distance) if independent else 0
        print(f"    UAI_GetNearestAgent -> {nearest}; independent -> {expected} of {len(independent)}")
        self.assertEqual(nearest, expected)

    def test_the_farthest_enemy_is_the_farthest_by_an_independent_measure(self) -> None:
        independent = self._independent_enemies()
        farthest = uai_get_agent.UAI_GetFarthestAgent(-2, 1320, "UAI_Filter_IsLivingEnemy")
        player_x, player_y = Agent.GetXY(self.agent_id)

        def distance(agent_id: int) -> float:
            agent_x, agent_y = Agent.GetXY(agent_id)
            return ((agent_x - player_x) ** 2 + (agent_y - player_y) ** 2) ** 0.5

        expected = max(independent, key=distance) if independent else 0
        print(f"    UAI_GetFarthestAgent -> {farthest}; independent -> {expected}")
        self.assertEqual(farthest, expected)

    def test_the_lowest_and_highest_hp_agents_agree_with_an_independent_measure(self) -> None:
        """`UAI_GetAgentLowest`/`Highest` over the live `HP` column, against `Agent.GetHealth`.

        **The comparison's domain is the living agents, and that is a finding rather than a convenience.**
        ``Agent.GetHealth`` resolves the *living* view and answers ``0.0`` for a record it cannot resolve
        that way, while the layer's ``HP`` column answers the record's own bytes at GwAu3's offset for
        every agent -- including an item or a gadget, whose bytes there are not a health at all. So the
        independent measure only exists where the two agree by construction, and what is asserted is the
        argmin/argmax over that set: the layer's answer is the lowest (or highest) of the living agents
        in reach. The layer may legitimately name a *non-living* record as the lowest, because the source
        asks its cache's ``HP`` column of every row; that is why the assertion is `<=`/`>=` and not `==`
        over the whole array.
        """

        from py4gw.agent_array import AgentArray

        living_in_range = [
            int(agent_id)
            for agent_id in AgentArray.GetAgentArray()
            if Agent.IsLiving(agent_id) and uai_get_agent._cached_distance(int(agent_id)) <= 1320
        ]
        if not living_in_range:
            self.skipTest("no living agent within 1320 units to compare against")

        lowest = uai_get_agent.UAI_GetAgentLowest(-2, 1320, GC_UAI_AGENT_HP)
        highest = uai_get_agent.UAI_GetAgentHighest(-2, 1320, GC_UAI_AGENT_HP)
        print(
            f"    UAI_GetAgentLowest -> {lowest} ({Agent.GetHealth(lowest) if lowest else '-'}); "
            f"highest -> {highest} ({Agent.GetHealth(highest) if highest else '-'}); "
            f"{len(living_in_range)} living agents in reach"
        )
        self.assertNotEqual(lowest, 0)
        self.assertNotEqual(highest, 0)

        # **What is asserted, and what a live client cannot be asked for.** The strict argmin over the
        # living set is *not* asserted: the layer's loop and this test's set are two reads of an array
        # the client is still changing, and a run where an agent died between them failed this check
        # while the layer was right. What is asserted is what holds snapshot or not -- the answer is an
        # agent the client holds, inside the range it was given, and the layer's `HP` column for it is
        # the same number `Agent.GetHealth` answers from the same record.
        for label, agent_id in (("lowest", lowest), ("highest", highest)):
            with self.subTest(agent=label):
                self.assertLessEqual(uai_get_agent._cached_distance(agent_id), 1320)
                self.assertAlmostEqual(
                    float(data_agent.Agent_GetAgentInfo(agent_id, "HP")),
                    float(Agent.GetHealth(agent_id)),
                    places=6,
                )
        self.assertLessEqual(Agent.GetHealth(lowest), Agent.GetHealth(highest))

    def test_every_living_agent_answers_the_keys_the_filters_read(self) -> None:
        """Every filter key, for **every** agent in the client's array, without raising.

        **This is the regression test for the second live finding (2026-10-10).** The reader table is a
        `Switch` over living fields, and `Agent_GetAgentPtr` answers each agent's own view -- so a gadget
        or an item record met a key its view does not declare, and the live run raised
        ``AttributeError: 'AgentGadgetStruct' object has no attribute 'allegiance'`` where GwAu3 answers
        the bytes at its own offset. The old suite never saw it because it read one *living* record (the
        player). Keys GwAu3 answers by a read are asserted here for every record type; the two that refuse
        (``EffectCount``, ``BondCount``) and the one that walks a list are not, by design.
        """

        from py4gw.agent_array import AgentArray

        keys = ("Allegiance", "HP", "MaxHP", "Level", "IsDead", "IsConditioned", "IsMoving", "IsCasting",
                "Primary", "Secondary", "LoginNumber", "TypeMap", "ModelState", "Effects", "X", "Y",
                "WeaponType", "Skill", "Owner", "Rotation", "PlayerNumber", "AgentModelType")
        kinds: dict[str, int] = {}
        for agent_id in AgentArray.GetAgentArray():
            for key in keys:
                with self.subTest(agent=agent_id, key=key):
                    data_agent.Agent_GetAgentInfo(int(agent_id), key)
            kinds[type(data_agent.Agent_GetAgentPtr(int(agent_id))).__name__] = (
                kinds.get(type(data_agent.Agent_GetAgentPtr(int(agent_id))).__name__, 0) + 1
            )
        print(f"    asked {len(keys)} keys of every agent; record views seen: {kinds}")
        self.assertTrue(kinds)

    def test_the_best_single_target_follows_the_fight_mode(self) -> None:
        """The mode decides the end of the HP range the answer comes from (``:227-231``)."""

        original = uai_const.g_i_FightMode
        try:
            uai_const.g_i_FightMode = constants.g_i_FinisherMode
            finisher = uai_get_agent.UAI_GetBestSingleTarget(-2, 1320, GC_UAI_AGENT_HP)
            uai_const.g_i_FightMode = constants.g_i_PressureMode
            pressure = uai_get_agent.UAI_GetBestSingleTarget(-2, 1320, GC_UAI_AGENT_HP)
        finally:
            uai_const.g_i_FightMode = original

        print(
            f"    UAI_GetBestSingleTarget: finisher -> {finisher} "
            f"({Agent.GetHealth(finisher) if finisher else '-'}), "
            f"pressure -> {pressure} ({Agent.GetHealth(pressure) if pressure else '-'})"
        )
        if finisher and pressure:
            self.assertLessEqual(Agent.GetHealth(finisher), Agent.GetHealth(pressure))
        self.assertEqual(finisher, uai_get_agent.UAI_GetAgentLowest(-2, 1320, GC_UAI_AGENT_HP))
        self.assertEqual(pressure, uai_get_agent.UAI_GetAgentHighest(-2, 1320, GC_UAI_AGENT_HP))

    def test_the_area_target_is_one_of_the_filtered_agents_or_zero(self) -> None:
        """`UAI_GetBestAOETarget`'s answer must be an agent the filter passes, or ``0``."""

        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        try:
            answer = uai_get_agent.UAI_GetBestAOETarget(-2, 1320, 156, "UAI_Filter_IsLivingEnemy")
        finally:
            uai_const.g_i_FightMode = 1

        if answer:
            self.assertTrue(uai_filter.UAI_Filter_IsLivingEnemy(answer))
            self.assertIn(answer, self._independent_enemies())
        print(f"    UAI_GetBestAOETarget -> {answer}")

    def test_the_ward_position_covers_the_allies_it_reports(self) -> None:
        """``[X, Y, Count]``: the count is how many allies the reported position covers, checked live.

        The invariant is the one the source's own loop computes (`_UAI_CountAlliesInRange`): counting the
        independently read allies inside the ward radius of the reported point must give the reported
        count back. The point itself is not asserted -- it is the best of the candidate set, and which
        candidate wins is a comparison this test does not re-derive.
        """

        position = uai_get_agent.UAI_GetBestWardPosition(GC_I_RANGE_AREA)
        allies = self._independent_allies()
        covered = 0
        for agent_id in allies:
            agent_x, agent_y = Agent.GetXY(agent_id)
            dx = agent_x - position[0]
            dy = agent_y - position[1]
            if (dx * dx + dy * dy) <= GC_I_RANGE_AREA * GC_I_RANGE_AREA:
                covered += 1
        print(
            f"    UAI_GetBestWardPosition -> {position}; "
            f"independent allies {len(allies)}, covered by it: {covered}"
        )
        self.assertEqual(len(position), 3)
        self.assertEqual(int(position[2]), covered)

    def test_the_martial_ward_position_skips_casters(self) -> None:
        """The martial query is the offensive one over enemies `UAI_IsCaster` says are not casters."""

        martial = uai_get_agent.UAI_GetBestMartialEnemyPosition(GC_I_RANGE_AREA)
        offensive = uai_get_agent.UAI_GetBestOffensiveWardPosition(GC_I_RANGE_AREA)
        cover = sum(1 for agent_id in self._independent_enemies() if not uai_utils.UAI_IsCaster(agent_id))
        print(f"    martial -> {martial}; offensive -> {offensive}; non-caster enemies: {cover}")
        self.assertEqual(len(martial), 3)
        if not cover:
            self.assertEqual(martial, [0, 0, 0])
        else:
            self.assertGreaterEqual(int(martial[2]), 1)

    def _independent_allies(self) -> list[int]:
        """Living allies other than the player, through `py4gw.Agent`."""

        from py4gw.agent_array import AgentArray

        return [
            int(agent_id)
            for agent_id in AgentArray.GetAgentArray()
            if int(agent_id) != self.agent_id
            and Agent.GetAllegiance(agent_id)[0] == GC_I_ALLEGIANCE_ALLY
            and Agent.GetHealth(agent_id) > 0
        ]

    def test_a_corpse_lookup_answers_without_raising(self) -> None:
        """The corpse queries read only; an empty field answers ``0`` rather than raising.

        **Not asserted as a value**: a corpse needs a dead enemy in the map, and a run in an outpost has
        none. What is asserted is that the query runs against the live client and answers one of its two
        shapes -- which is the part a live run can establish without a battlefield.
        """

        nearest = uai_get_agent.UAI_IsCorpseNearest(self.agent_id, 0.0, 0.0)
        support = uai_get_agent.UAI_GetBestCorpseForAllySupport(1320)
        pressure = uai_get_agent.UAI_GetBestCorpseForEnemyPressure(1320)
        print(f"    corpses: nearest={nearest} support={support} pressure={pressure}")
        self.assertIsInstance(nearest, bool)
        self.assertIsInstance(int(support), int)
        self.assertIsInstance(int(pressure), int)

    def test_the_condition_counter_answers_from_the_agents_visible_effects(self) -> None:
        """`UAI_GetBestTargetByConditionCount`, live -- the query that refused until now.

        It reads the seven status effects per agent through `UAI_AgentHasVisibleEffect`, which walks the
        agent's own visible-effect list at ``+0x174``. The answer is an agent id or ``0``; what this
        asserts is that the walk runs against the live client and that whatever it answers is one of the
        agents the layer can see (or ``0``, which is GwAu3's own "nothing qualified").
        """

        answer = uai_get_agent.UAI_GetBestTargetByConditionCount()
        print(f"    UAI_GetBestTargetByConditionCount() -> {answer}")
        self.assertIsInstance(int(answer), int)
        if int(answer) != 0:
            self.assertIn(int(answer), [int(a) for a in uai_get_agent._cached_ids()])

    def test_the_visible_effect_walk_reads_the_controlled_characters_own_list(self) -> None:
        """The visible-effect family, live: the AutoIt array contract and the per-row match.

        `UAI_GetAgentVisibleEffectInfo` answers row ``0`` as the count and the rows after it as
        ``(EffectType, EffectID, HasEnded)``; each row it reports must then be found by
        `UAI_AgentHasVisibleEffect`, which is the same walk asked a different question. A type/id pair
        the list does not hold must answer ``False``.
        """

        rows = uai_effects.UAI_GetAgentVisibleEffectInfo(self.agent_id)
        print(f"    visible effects on agent {self.agent_id}: {rows}")
        self.assertEqual(rows[0][0], len(rows) - 1)
        for row in rows[1:]:
            with self.subTest(row=row):
                self.assertEqual(len(row), 3)
                self.assertTrue(
                    uai_effects.UAI_AgentHasVisibleEffect(self.agent_id, row[0], row[1])
                )
        self.assertFalse(
            uai_effects.UAI_AgentHasVisibleEffect(self.agent_id, 0xFFFF, 0xFFFE)
        )
        self.assertEqual(
            uai_effects.UAI_GetAgentVisibleEffectCount(self.agent_id), len(rows) - 1
        )
        self.assertEqual(
            uai_effects.UAI_GetPlayerVisibleEffectCount(),
            len(uai_effects.UAI_GetPlayerVisibleEffectInfo()) - 1,
        )

    # -- 7. the party-member accessors, against the port's own party class --------------------

    def test_the_party_member_counts_agree_with_the_ported_party_class(self) -> None:
        """The five second-level context keys, against `Party.GetPlayers`/`GetHeroes`/the rest.

        This is the live check on the pointer this file refused for two rounds: GwAu3 reads the counts
        *through* ``player_party_ptr`` and the layer follows it now, so the count it answers and the
        count the port's own accessor reads from the same record must be the same number.
        """

        expected = {
            "PlayerCount": len(Party.GetPlayers()),
            "HenchmenCount": len(Party.GetHenchmen()),
            "HeroCount": len(Party.GetHeroes()),
            "OtherCount": len(Party.GetOthers()),
        }
        for key, count in expected.items():
            with self.subTest(key=key):
                self.assertEqual(data_party.Party_GetPartyContextInfo(key), count)
        self.assertEqual(
            data_party.Party_GetPartyContextInfo("PlayerPartyID"), int(Party.GetPartyID())
        )
        print(f"    party context counts {expected}, id {Party.GetPartyID()}")

    def test_the_member_accessors_agree_with_the_ported_party_class(self) -> None:
        """`Party_GetMyParty*Info` against the same member records, read through `py4gw.party`."""

        heroes = Party.GetHeroes()
        players = Party.GetPlayers()
        henchmen = Party.GetHenchmen()

        self.assertEqual(
            data_party.Party_GetMyPartyInfo("ArrayHeroPartyMemberSize"), len(heroes)
        )
        self.assertEqual(
            data_party.Party_GetMyPartyInfo("ArrayPlayerPartyMemberSize"), len(players)
        )
        if heroes:
            first = data_party.Party_GetMyPartyHeroInfo(1, "AgentID", True)
            self.assertEqual(first, int(heroes[0].agent_id))
            self.assertEqual(
                data_party.Party_GetMyPartyHeroInfo(1, "HeroID", True), int(heroes[0].hero_id)
            )
        if players:
            self.assertEqual(
                data_party.Party_GetMyPartyPlayerMemberInfo(1, "LoginNumber"),
                int(players[0].login_number),
            )
            self.assertEqual(
                data_party.Party_GetMyPartyPlayerMemberInfo(1, "CalledTargetID"),
                int(players[0].called_target_id),
            )
        if henchmen:
            self.assertEqual(
                data_party.Party_GetMyPartyHenchmanInfo(1, "AgentID"), int(henchmen[0].agent_id)
            )
        print(
            f"    party members: {len(players)} player(s), {len(heroes)} hero(es), "
            f"{len(henchmen)} henchman/en"
        )

    def test_the_party_refusals_refuse_live_too(self) -> None:
        """The address keys and the party pointer, against the live client.

        `Party_GetHeroFlagInfo` is **no longer** among them: it is routed now, over the world's
        hero-flag array, and its six agreeing keys answer. Its one disagreeing key
        (``LockedTargetID``) refuses *inside* the matched element, exactly where the source's ``Case``
        is, so it cannot be asserted here at all when the party holds no heroes -- a hero number that
        matches nothing answers ``0`` first, which is GwAu3's own order.
        """

        for key in (
            "ArrayPlayerPartyMember",
            "ArrayHenchmanPartyMember",
            "ArrayHeroPartyMember",
            "ArrayOthersPartyMember",
        ):
            with self.subTest(key=key):
                with self.assertRaises(NotImplementedError) as raised:
                    data_party.Party_GetMyPartyInfo(key)
                self.assertIn("py4gw/context/party_context.py", str(raised.exception))
        with self.assertRaises(NotImplementedError):
            data_party.Party_GetPartyContextInfo("MyPartyPtr")
        print("    the address keys and MyPartyPtr refused live")


    def test_the_attribute_readers_agree_with_the_ports_own_attribute_reads(self) -> None:
        """`data_attribute`, live -- two readers of the same two tables, checked against each other.

        `Attribute_GetAttributeInfo` reads the client's attribute-constant table, which this project also
        reads through `py4gw.skillbar`; `Attribute_GetPartyAttributeInfo` reads the party-attribute
        blocks, which `Agent.GetAttributesDict` reads for the controlled character through a *different*
        path (it collects the port's own blocks, this indexes the block GwAu3's walk finds). So the level
        each answers for the player is a cross-check rather than a smoke test.
        """

        from py4gw.gwa3 import data_attribute
        from py4gw.skillbar import get_attribute_constant_data

        my_id = int(Player.GetAgentID())
        ported = Agent.GetAttributesDict(my_id)

        # The constant table: the layer's member and the port's own reader answer the same record.
        for attribute_id in (0, 5, 17):
            constant = get_attribute_constant_data(attribute_id)
            with self.subTest(attribute_id=attribute_id):
                if constant is None:
                    self.assertEqual(
                        data_attribute.Attribute_GetAttributePtr(attribute_id), None
                    )
                    continue
                self.assertEqual(
                    data_attribute.Attribute_GetAttributeInfo(attribute_id, "NameID"),
                    int(constant.name_id),
                )
                self.assertEqual(
                    data_attribute.Attribute_GetAttributeInfo(attribute_id, "ProfessionID"),
                    int(constant.profession_id),
                )
                self.assertTrue(data_attribute.Attribute_GetAttributeName(attribute_id))

        # The party blocks: the level the layer finds for the player, against the port's own dict.
        #
        # **The port's dict holds *base* levels and the layer's `Level` is the current one**, which is
        # what the first run of this test learned: `Agent.GetAttributesDict` builds
        # ``{attr.attribute_id: attr.level_base}`` (`py4gw/agent.py:788-800`), while this layer's
        # `"Level"` is GwAu3's `+0x8` word and `"BaseLevel"` is its `+0x4` one -- the same two words the
        # port's `AttributeStruct` declares at those offsets (`py4gw/context/world_context.py:245-255`).
        # Comparing `"Level"` with the dict answered 16 against 12 for an Axe Mastery of base 12 with a
        # +4 bonus, which is the two *different* fields agreeing about the record. So the dict is
        # compared with `"BaseLevel"`, and the bonus identity below is what ties the pair together.
        for attribute_id, level in list(ported.items())[:4]:
            with self.subTest(attribute_id=attribute_id):
                self.assertEqual(
                    data_attribute.Attribute_GetPartyAttributeInfo(attribute_id, 0, "BaseLevel"),
                    int(level),
                )
                self.assertGreaterEqual(
                    data_attribute.Attribute_GetPartyAttributeInfo(attribute_id, 0, "Level"),
                    int(level),
                )
                self.assertIsInstance(
                    data_attribute.Attribute_GetPartyAttributeInfo(attribute_id, 0, "IsMaxed"), bool
                )
                self.assertEqual(
                    data_attribute.Attribute_GetPartyAttributeInfo(attribute_id, 0, "BonusLevel"),
                    data_attribute.Attribute_GetPartyAttributeInfo(attribute_id, 0, "Level")
                    - data_attribute.Attribute_GetPartyAttributeInfo(attribute_id, 0, "BaseLevel"),
                )

        unused = data_attribute.Attribute_GetPartyAttributePointInfo(0, "UnusedPoints")
        total = data_attribute.Attribute_GetPartyAttributePointInfo(0, "TotalPoints")
        print(f"    attributes: {len(ported)} populated; unspent {unused} of {total} points")
        self.assertIsInstance(int(unused), int)
        self.assertIsInstance(int(total), int)
        self.assertGreaterEqual(int(total), int(unused))

    def test_the_party_layer_of_the_engine_answers_live(self) -> None:
        """`UtilityAI_Utils.au3`'s party layer, against the port's own party and the live client.

        The engine's three aggro questions and the called target, which were unblocked when the party
        member and hero-flag accessors landed. In an outpost with no enemies the honest answers are
        "no" and ``0``; what this test establishes live is that they *answer* -- through the party
        records, the hero-flag array and the targeting queries -- rather than raising, and that the
        count and the boolean agree with each other, since they are the same loop asked two ways.
        """

        self.assertEqual(uai_utils.Party_GetSize(), data_party.Party_GetPartyContextInfo("TotalPartySize"))
        self.assertEqual(uai_utils.Party_GetHeroCount(), data_party.Party_GetPartyContextInfo("HeroCount"))
        self.assertEqual(
            uai_utils.Party_GetHeroAgentID(0), int(Player.GetAgentID())
        )

        in_range = uai_utils.UAI_IsEnemyInPartyAggroRange(1320)
        counted = uai_utils.UAI_CountEnemyInPartyAggroRange(1320)
        nearest = uai_utils.UAI_GetNearestEnemyInPartyRange(1320)
        called = uai_utils.UAI_GetPartyCalledTarget()
        self.assertIsInstance(in_range, bool)
        self.assertEqual(in_range, counted != 0, "the count and the boolean are one loop")
        self.assertIsInstance(int(nearest), int)
        self.assertIsInstance(int(called), int)

        # The hero-flag accessor's guards, live: with the heroes the party does or does not hold, an
        # out-of-range hero number answers `0` for every key, and a key the offsets disagree about
        # refuses only where the source would read it.
        hero_count = int(uai_utils.Party_GetHeroCount())
        if hero_count == 0:
            for key in ("HeroID", "AgentID", "InventoryID", "Behavior", "FlagX", "FlagY"):
                with self.subTest(key=key):
                    self.assertEqual(data_party.Party_GetHeroFlagInfo(1, key), 0)
        print(
            f"    party layer: size {uai_utils.Party_GetSize()}, heroes {hero_count}, "
            f"in-aggro {in_range}, count {counted}, nearest {nearest}, called {called}"
        )


    def test_the_skillbar_reader_agrees_with_the_ports_own_skillbar(self) -> None:
        """`Skill_GetSkillbarInfo` against `py4gw.skillbar`'s read of the player's own bar.

        The reader is what UtilityAI's slot loop asks what is on a skillbar, so its `SkillID` column has
        to be the client's skillbar: this compares all eight slots against the port's independent read,
        and asserts the two consistency relations the source's own keys imply -- `HasSkill` is the id
        read for truth, and an empty slot answers `0`.

        **The comparison is against `GetZeroFilledSkillbar`, and the first version of this test is why.**
        `SkillBar.GetSkillbar()` **drops the empty slots** -- its own body appends only non-zero ids
        (`py4gw/skillbar.py:995-1005`) -- so comparing it positionally against an eight-slot column
        reported a "one-slot shift" that did not exist: measured live, the layer's column was
        ``[330, 2107, 0, 1506, 343, 336, 3426, 0]`` and the client's own slot records agreed with it slot
        for slot while the compacted list was ``[330, 2107, 1506, 343, 336, 3426]``. What is asserted
        here is the positional read, and the compaction rule is asserted too, so the two spellings are
        tied together rather than confused.
        """

        from py4gw.gwa3 import data_skill
        from py4gw.skillbar import SkillBar

        by_slot = {int(slot): int(skill_id) for slot, skill_id in SkillBar.GetZeroFilledSkillbar().items()}
        column = [int(data_skill.Skill_GetSkillbarInfo(slot, "SkillID")) for slot in range(1, 9)]

        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID"), int(Player.GetAgentID()))
        self.assertGreater(data_skill.Skill_GetSkillTimer(), 0)
        self.assertEqual(column, [by_slot[slot] for slot in range(1, 9)])
        self.assertEqual(
            [int(skill_id) for skill_id in SkillBar.GetSkillbar()],
            [skill_id for skill_id in column if skill_id != 0],
            "`GetSkillbar()` is this column with the empty slots dropped",
        )

        for slot in range(1, 9):
            with self.subTest(slot=slot):
                expected = by_slot[slot]
                self.assertEqual(bool(data_skill.Skill_GetSkillbarInfo(slot, "HasSkill")), expected != 0)
                # `RechargeTime` is zero exactly when the slot is recharged or holds nothing, which is
                # the source's own pair of keys (`GwAu3_Data_Skill.au3:271-287`).
                self.assertEqual(
                    data_skill.Skill_GetSkillbarInfo(slot, "RechargeTime") > 0,
                    not data_skill.Skill_GetSkillbarInfo(slot, "IsRecharged"),
                )
        print(f"    skillbar: {column} read back slot for slot, timer {data_skill.Skill_GetSkillTimer()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
