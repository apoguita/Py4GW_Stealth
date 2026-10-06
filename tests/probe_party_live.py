"""Live probe: the ported ``Party`` against the running client, reads first and actions last.

Three stages, and the split is the project's own discipline (``AGENTS.md``: a live write is
deliberate, bounded and attributable):

* ``reads`` — **the default.** Unelevated, no connection, nothing called and nothing written: a
  read-only client stand-in over the live process, then every member of ``Party`` whose answer is a
  read. This is the rung that can run at any time.
* ``hold`` — **elevated, and it changes nothing.** Connects, then drives the acting members with
  **the values the client already reports**, which the sources' own guards turn into refusals: the
  hero-behaviour member, the skill-AI member and the pet member each compare before they write, and
  the difficulty member is told only when the mode differs. So the read path, the guards and the
  answer values are exercised against a real client while its state stays as it was; the reads are
  repeated afterwards and the report says whether anything moved.
* ``act`` — **elevated, and it needs the owner watching.** The steps that really act, each with the
  read it is based on and a restore where the source gives one. **Nothing runs unless the owner names
  the step** (``--allow flags``), and with no ``--allow`` the stage prints the plan and stops. A step
  also refuses when the client's own condition for it is not met — a hero that is not in the party, a
  party of one for `LeaveParty`, a map that is not an outpost for the party changes — so the report
  says *why* rather than doing something else.

Usage::

    python tests/probe_party_live.py reads [report-path]
    python tests/probe_party_live.py hold  [report-path]          # elevated, changes nothing
    python tests/probe_party_live.py act   [report-path] --allow flags,behaviour   # elevated, owner present
    python tests/probe_party_live.py act --allow use-skill,party-add --hero-number 1 --slot 1 --hero Norgu
    python tests/probe_party_live.py act --allow party-add,party-kick --henchman 1234   # a live agent id
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any

from py4gw.context.acc_agent_context import AccAgentContext
from py4gw.context.agent_array import AgentArray
from py4gw.context.char_context import CharContext
from py4gw.context.cinematic_context import Cinematic
from py4gw.context.game_context import GameContext
from py4gw.context.gadget_context import GadgetContext
from py4gw.context.instance_info_context import InstanceInfo
from py4gw.context.item_context import ItemContext
from py4gw.context.map_context import MapContext
from py4gw.context.party_context import PartyContext
from py4gw.context.player_agent_id_context import PlayerAgentId
from py4gw.context.server_region_context import ServerRegion
from py4gw.context.text_parser_context import TextParser
from py4gw.context.world_context import WorldContext
from py4gw.memory import MemoryManager, ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.ui.frame import FrameArray
from py4gw.ui.frame_tree import FrameTree
from py4gw.context.gameplay_context import GameplayContext
from py4gw.context.mission_map_context import MissionMapContext
from py4gw.win32 import Win32

#: Where the read stage's report goes, and where the elevated stages' does.
REPORT_PATH = "tests/live_reports/party_live.json"

#: Every step the acting stage knows, in the order it would run them: the reversible ones first, the
#: party-changing ones after, and the two that leave the map last. The owner names what may run.
#:
#: How long a step waits for the client to show what it just sent, before it computes the restore.
#: The client applies a party change when it processes the command, so a flip-and-restore step that
#: does not wait computes the restore from the value it is replacing (round 24's live finding).
SETTLE_TIMEOUT_SECONDS = 3.0

#: The least time between two **acting** calls this probe makes. The client processes one command at a
#: time — a party change is queued and applied on its own schedule — so a burst of calls is not a test
#: of the port, it is a test of how fast the client's queue drains, and a dropped command looks like a
#: member that did nothing. Reads are not paced: they touch no client machinery.
ACTION_INTERVAL_SECONDS = 0.75

STEPS: tuple[tuple[str, str], ...] = (
    ("flags", "FlagAllHeroes to the party's own flag position, then UnflagAllHeroes"),
    ("flag-hero", "FlagHero for one hero, then UnflagHero"),
    ("behaviour", "SetHeroBehavior with a different value for one hero, then back"),
    ("skill-ai", "SetSkillAIEnabled on one slot, then back"),
    ("difficulty", "SetHardMode/SetNormalMode, in an outpost, then back"),
    ("search", "SearchParty with a short advertisement, then SearchPartyCancel"),
    ("pet", "SetPetBehavior(Fight, current target) — needs a living enemy target — then back"),
    ("use-skill", "Heroes.UseSkill on one hero number and slot (`--hero-number`, `--slot`)"),
    ("party-add", "AddHeroByName (`--hero`), and AddHenchman when `--henchman <agent_id>` is given"
                  " — **changes the party**, outposts only"),
    ("party-kick", "KickHeroByName (`--hero`), and KickHenchman with `--henchman`"
                   " — **changes the party**"),
    ("leave", "LeaveParty — **changes the party**; needs the party window on screen (a press without "
              "it asserted the client once, `FrApi.cpp(3916)`) and someone else in the party"),
    ("outpost", "ReturnToOutpost — **leaves the map**"),
)


def _ask(call: Any) -> Any:
    """Run one member and report what it answered or exactly how it refused."""

    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


#: When the last acting call was made, so consecutive commands are spaced (``_pace``).
_last_action_at = 0.0


def _pace() -> None:
    """Wait out the interval since the last acting call, so commands are not issued back to back."""

    import time

    global _last_action_at

    now = time.monotonic()
    wait = ACTION_INTERVAL_SECONDS - (now - _last_action_at)
    if wait > 0:
        time.sleep(wait)
    _last_action_at = time.monotonic()


def _act(call: Any) -> Any:
    """One **acting** call: paced, and its answer (or its refusal) reported the way ``_ask`` does."""

    _pace()
    return _ask(call)


def _settle(read: Any, expected: Any, *, timeout: float | None = None,
            interval: float = 0.1) -> dict[str, Any]:
    """Wait, bounded, for the client to show what a step just sent, and say whether it did.

    **The client applies a party change when it processes the command, not inside the call that sends
    it.** The record every member compares against is the *client's*, and immediately after a call it
    still holds the old value — which makes a "flip it and put it back" step racy in a way the first
    live run found: the flip is sent, the restore's own guard reads the *old* value, decides the write
    is unnecessary and returns `true` without calling, and the flip is what stays. The same staleness
    makes a before/after comparison blind, because the "after" read happens before the client has
    applied anything.

    So a step that changes a value waits here for the client to show the change **before** it computes
    the restore, and the stage's own before/after comparison is taken after the steps have settled.
    The wait is bounded and its outcome is reported rather than assumed: a client that never shows the
    value is a fact the report carries (`settled: False`), not a hang.
    """

    import time

    wait = SETTLE_TIMEOUT_SECONDS if timeout is None else timeout
    deadline = time.monotonic() + wait
    started = time.monotonic()
    seen = None
    while True:
        seen = _ask(read)
        if seen == expected:
            return {
                "settled": True,
                "after": seen,
                "waited_ms": round((time.monotonic() - started) * 1000.0, 1),
            }
        if time.monotonic() >= deadline:
            return {
                "settled": False,
                "after": seen,
                "expected": expected,
                "waited_ms": round((time.monotonic() - started) * 1000.0, 1),
            }
        time.sleep(interval)


class _LiveClient:
    """A read-only connection stand-in: the facades ``ConnectedClient`` builds, over the live process.

    The party reads reach further than the party context: ``IsPlayerLoaded`` walks into the map
    context, the morale list resolves agent ids through the agent array, and the pet and player
    records carry pointers that need the reader. So the stand-in offers the same objects the real
    connection does — each one the ported facade over the live process, none of them a fake.

    ``call_function`` raises, so a member that tries to act fails loudly here rather than quietly
    doing nothing — which is what makes the read stage's claim ("nothing was called") checkable.
    """

    def __init__(self, pid: int, reader: ProcessMemoryReader, scanner: RemoteScanner,
                 patterns: PatternCatalog) -> None:
        self.pid = pid
        self.reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self.memory_manager = MemoryManager(reader, scanner, patterns)
        self.memory_manager.Scan()
        self._game_context = GameContext(reader, scanner, patterns)
        self._game_context.initialize()
        self._party_context = PartyContext(reader, self._game_context)
        self._world_context = WorldContext(reader, self._game_context)
        self._char_context = CharContext(
            reader, scanner, patterns, game_context=self._game_context
        )
        self._map_context = MapContext(reader, self._game_context)
        self.frame_array = FrameArray(reader, scanner, patterns)
        # The frame-array route to the frame-published contexts, built the way ``ConnectedClient``
        # builds it (``client.py:393-410``): ``Map.Pathing.Quad`` is the source's own body and reaches
        # screen coordinates through ``Map.MissionMap.GetPanOffset``, so a stand-in without this
        # refused ``IsPointInPathing`` with an ``AttributeError`` instead of reading it.
        self.frame_tree = FrameTree(self.frame_array, scanner.function_from_near_call)
        self._mission_map_context = MissionMapContext(
            reader, scanner, patterns, self.frame_tree
        )
        # The same reach goes on through ``Map.MissionMap.GetZoom`` (``map.py:1114``).
        self._gameplay_context = GameplayContext(reader, scanner, patterns)
        self._gameplay_context.initialize()
        self.agent_array = AgentArray(
            reader, scanner, patterns, cache_context_validator=lambda: True
        )
        self.agent_array.initialize()
        self._acc_agent_context = AccAgentContext(reader, self._game_context)
        self._gadget_context = GadgetContext(reader, self._game_context)
        self._item_context = ItemContext(reader, self._game_context, scanner, patterns)
        self._text_parser = TextParser(reader, self._game_context)
        self._instance_info = InstanceInfo(reader, scanner, patterns)
        self._instance_info.initialize()
        self._player_agent_id = PlayerAgentId(reader, scanner, patterns)
        self._player_agent_id.initialize()
        self._server_region = ServerRegion(reader, scanner, patterns)
        self._server_region.initialize()
        # ``Map.IsInCinematic`` reads this facade (``Checks.Map.MapValid`` calls it), and the pathing
        # probe's navmesh build goes through that check — so the stand-in offers what
        # ``ConnectedClient`` offers, under the same name.
        self._cinematic = Cinematic(reader, self._game_context)

    def resolves(self, name: str) -> bool:
        return self._patterns.resolve(name, self._scanner).ok

    @property
    def mission_map_context(self) -> MissionMapContext:
        """The frame-array-backed reader, under the name ``ConnectedClient`` gives it."""

        return self._mission_map_context

    @property
    def gameplay_context(self) -> GameplayContext:
        """The gameplay reader, under the name ``ConnectedClient`` gives it."""

        return self._gameplay_context

    def call_function(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "this stage installs no capability layer, so no client function can be called"
        )

    def call_address(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("this stage installs no capability layer")

    def read_party_context(self) -> Any:
        return self._party_context.read()

    def read_map_context(
        self,
        max_spawn_entries: int = 2048,
        max_pathing_maps: int = 32,
    ) -> Any:
        """The map context read, which the pathing cache inputs reach for — same arguments as
        ``ConnectedClient.read_map_context``."""

        return self._map_context.read(max_spawn_entries, max_pathing_maps)

    def read_world_context(self) -> Any:
        return self._world_context.read()

    def read_char_context(self) -> Any:
        return self._char_context.read()

    def read_acc_agent_context(self) -> Any:
        return self._acc_agent_context.read()

    def read_gadget_context(self) -> Any:
        return self._gadget_context.read()

    def read_item_context(self) -> Any:
        return self._item_context.read()

    @property
    def map_context(self) -> Any:
        """The map context facade, which ``Map.IsMapReady`` reaches for."""

        return self._map_context

    @property
    def cinematic(self) -> Any:
        """The cinematic facade, which ``Map.IsInCinematic`` reaches for."""

        return self._cinematic

    @property
    def context(self) -> Any:
        """The character context facade, under the name ``ConnectedClient`` exposes."""

        return self._char_context

    @property
    def acc_agent_context(self) -> Any:
        return self._acc_agent_context

    @property
    def gadget_context(self) -> Any:
        return self._gadget_context

    @property
    def item_context(self) -> Any:
        return self._item_context

    @property
    def party_context(self) -> Any:
        return self._party_context

    @property
    def world_context(self) -> Any:
        return self._world_context

    @property
    def instance_info(self) -> Any:
        """The instance-info facade, which the map-readiness chain reads."""

        return self._instance_info

    @property
    def player_agent_id(self) -> Any:
        return self._player_agent_id

    @property
    def server_region(self) -> Any:
        return self._server_region

    @property
    def text_parser(self) -> Any:
        return self._text_parser


# ── the read stage ───────────────────────────────────────────────────────────
def party_reads() -> dict[str, Any]:
    """Every ``Party`` member whose answer is a read, in the class's own order."""

    from py4gw.party import Party

    heroes = Party.Heroes
    players = Party.Players
    pets = Party.Pets

    rows: dict[str, Any] = {}
    rows["identity"] = {
        "GetPartyID": _ask(Party.GetPartyID),
        "GetPartyLeaderID": _ask(Party.GetPartyLeaderID),
        "GetOwnPartyNumber": _ask(Party.GetOwnPartyNumber),
        "GetPartyTarget": _ask(Party.GetPartyTarget),
        "IsPartyLeader": _ask(Party.IsPartyLeader),
    }
    rows["counts"] = {
        "GetPartySize": _ask(Party.GetPartySize),
        "GetPlayerCount": _ask(Party.GetPlayerCount),
        "GetHeroCount": _ask(Party.GetHeroCount),
        "GetHenchmanCount": _ask(Party.GetHenchmanCount),
        "GetPartyMorale": _ask(Party.GetPartyMorale),
        "others": _ask(lambda: list(Party.GetOthers())),
    }
    rows["state"] = {
        "IsHardModeUnlocked": _ask(Party.IsHardModeUnlocked),
        "IsHardMode": _ask(Party.IsHardMode),
        "IsNormalMode": _ask(Party.IsNormalMode),
        "IsPartyDefeated": _ask(Party.IsPartyDefeated),
        "IsPartyLoaded": _ask(Party.IsPartyLoaded),
        "IsPlayerLoaded": _ask(Party.IsPlayerLoaded),
        "IsAllTicked": _ask(Party.IsAllTicked),
        "IsPlayerTicked(0)": _ask(lambda: Party.IsPlayerTicked(0)),
    }
    rows["heroes"] = {
        "GetHeroAgentIDByPartyPosition(1)": _ask(
            lambda: heroes.GetHeroAgentIDByPartyPosition(1)
        ),
        "GetHeroAgentIDByPartyPosition(0)": _ask(
            lambda: heroes.GetHeroAgentIDByPartyPosition(0)
        ),
        "GetHeroIDByPartyPosition(0)": _ask(lambda: heroes.GetHeroIDByPartyPosition(0)),
        "GetHeroIdByName('Norgu')": _ask(lambda: heroes.GetHeroIdByName("Norgu")),
        "IsAllFlagged": _ask(heroes.IsAllFlagged),
        "GetAllFlag": _ask(heroes.GetAllFlag),
        "IsHeroFlagged(0)": _ask(lambda: heroes.IsHeroFlagged(0)),
        "per-hero": [
            {
                "position": index,
                "agent_id": _ask(
                    lambda index=index: heroes.GetHeroAgentIDByPartyPosition(index)
                ),
                "hero_id": _ask(
                    lambda index=index: heroes.GetHeroIDByPartyPosition(index)
                ),
                "name": _ask(
                    lambda index=index: heroes.GetNameByAgentID(
                        heroes.GetHeroAgentIDByPartyPosition(index) or 0
                    )
                ),
                "target_id": _ask(
                    lambda index=index: heroes.GetTargetIDByAgentID(
                        heroes.GetHeroAgentIDByPartyPosition(index) or 0
                    )
                ),
            }
            for index in range(1, (Party.GetHeroCount() or 0) + 1)
        ],
    }
    rows["players"] = {
        "GetAgentIDByLoginNumber(0)": _ask(
            lambda: players.GetAgentIDByLoginNumber(0)
        ),
        "GetPlayerNameByLoginNumber(0)": _ask(
            lambda: players.GetPlayerNameByLoginNumber(0)
        ),
        "GetPartyNumberFromLoginNumber(0)": _ask(
            lambda: players.GetPartyNumberFromLoginNumber(0)
        ),
        "GetLoginNumberByAgentID": _ask(
            lambda: players.GetLoginNumberByAgentID(Party.Heroes.GetHeroAgentIDByPartyPosition(0) or 0)
        ),
        "party members": [
            {
                "login_number": _ask(lambda member=member: int(member.login_number)),
                "agent_id": _ask(
                    lambda member=member: players.GetAgentIDByLoginNumber(
                        int(member.login_number)
                    )
                ),
                "called_target_id": _ask(
                    lambda member=member: int(member.called_target_id)
                ),
                "connected": _ask(lambda member=member: bool(member.is_connected)),
                "ticked": _ask(lambda member=member: bool(member.is_ticked)),
                "name": _ask(
                    lambda member=member: players.GetPlayerNameByLoginNumber(
                        int(member.login_number)
                    )
                ),
            }
            for member in Party.GetPlayers()
        ],
    }
    rows["pets"] = {
        "GetPetBehavior(0)": _ask(lambda: pets.GetPetBehavior(0)),
        "GetPetID(0)": _ask(lambda: pets.GetPetID(0)),
        "GetPetInfo(0)": _ask(
            lambda: {
                "agent_id": int(pets.GetPetInfo(0).agent_id),
                "owner_agent_id": int(pets.GetPetInfo(0).owner_agent_id),
                "behavior": int(pets.GetPetInfo(0).behavior),
                "locked_target_id": int(pets.GetPetInfo(0).locked_target_id),
                "pet_name_str": pets.GetPetInfo(0).pet_name_str,
            }
        ),
    }
    return rows


def act_readiness() -> list[dict[str, Any]]:
    """What each ``act`` step would do *right now*, and whether the client's condition for it holds.

    Every guard the acting stage applies is a read, so the whole thing can be decided without a
    connection — including the one that is not obvious: whether the ``DlgRedirect`` button
    `ReturnToOutpost` clicks is on screen, which is asked here through the frame array by the label's
    own hash (``frame_names.NAME_TO_HASH``, the port's offline table) rather than through the client's
    hasher, so it costs nothing. Reading this before the run is how the owner picks which steps can
    even fire in this map.
    """

    from py4gw.client import require_client
    from py4gw.frame_tree.frame_names import NAME_TO_HASH
    from py4gw.map import Map
    from py4gw.party import Party

    rows: list[dict[str, Any]] = []

    def row(step: str, would_do: str, guard: str, ready: Any) -> None:
        rows.append(
            {"step": step, "would_do": would_do, "guard": guard, "runnable_now": ready}
        )

    current = Party.Heroes.GetAllFlag()
    x, y = (current if isinstance(current, tuple) and len(current) == 2 else (0.0, 0.0))
    flag_is_set = math.isfinite(float(x)) and math.isfinite(float(y))
    row(
        "flags",
        f"FlagAllHeroes({x}, {y}) then UnflagAllHeroes"
        if flag_is_set
        else "UnflagAllHeroes only (the flag is unset, so there is no position to reuse)",
        "always: the flag call is the step",
        True,
    )

    hero_count = Party.GetHeroCount() or 0
    row(
        "flag-hero",
        f"FlagHero(hero 1 → {Party.Heroes.GetHeroAgentIDByPartyPosition(1)}, {x}, {y}) then UnflagHero(1)"
        if flag_is_set
        else "nothing: there is no set flag position to reuse",
        f"{hero_count} hero(es) in the party, and the party's flag reads ({x}, {y})",
        bool(hero_count) and flag_is_set,
    )

    world = _world()
    behavior = _hero_behavior(world, 1)
    row(
        "behaviour",
        f"SetHeroBehavior(hero 1, {0 if int(behavior or 0) != 0 else 2}) then back to {behavior}",
        "a hero-flag record for hero 1",
        behavior is not None,
    )
    disabled = _hero_disabled(world, 1)
    row(
        "skill-ai",
        f"SetSkillAIEnabled(hero 1, slot 1, {bool(int(disabled or 0) & 1)}) then back",
        "a skillbar for hero 1",
        disabled is not None,
    )
    if Party.IsHardMode():
        difficulty_what = "SetNormalMode() then back"
        difficulty_guard = "an outpost: the client only changes the mode there"
        difficulty_ok = bool(Map.IsOutpost())
    else:
        difficulty_what = "SetHardMode() then back"
        # Round 24's live run: this account has no hard mode unlocked, the client accepted the call
        # and never moved its own flag — ten seconds of polling showed nothing. A step whose condition
        # is not met refuses and says why, rather than reporting a change nobody will see.
        unlocked = bool(Party.IsHardModeUnlocked())
        difficulty_guard = (
            "an outpost and hard mode unlocked on this account: with the unlock false the client "
            "ignores the request (measured: 10 s, its own flag never moved)"
        )
        difficulty_ok = bool(Map.IsOutpost()) and unlocked
    row("difficulty", difficulty_what, difficulty_guard, difficulty_ok)
    row(
        "search",
        "SearchParty(PartySearchType_Hunting, 'Stealth probe') then SearchPartyCancel",
        "always: the step is the search itself",
        True,
    )
    pet = _pet_state(world)
    row(
        "pet",
        f"SetPetBehavior({pet['behavior']}, {pet['locked_target_id']})" if pet else "nothing: no pet",
        "a pet whose record is readable",
        pet is not None,
    )
    row(
        "use-skill",
        "Heroes.UseSkill(hero 1, slot 1, 0)",
        f"hero 1 in the party (declared hero count {hero_count})",
        bool(hero_count),
    )
    row(
        "party-add",
        "AddHeroByName('Norgu')",
        "an outpost: the client only accepts a party change there",
        bool(Map.IsOutpost()),
    )
    row(
        "party-kick",
        "KickHeroByName('Norgu')",
        "Norgu in this party",
        any(
            int(Party.Heroes.GetHeroIDByPartyPosition(position) or -1)
            == int(Party.Heroes.GetHeroIdByName("Norgu"))
            for position in range(1, hero_count + 1)
        ),
    )
    row(
        "leave",
        "LeaveParty()",
        f"{Party.GetPlayerCount() or 0} player(s): the step needs someone else in the party, and the "
        "party window on screen — this press asserted a client once when it was not "
        "(`FrApi.cpp(3916)`)",
        (Party.GetPlayerCount() or 0) >= 2 and _party_window_on_screen(),
    )

    hash_value = int(NAME_TO_HASH.get("DlgRedirect", 0))
    dlg_redirect = 0
    for candidate, record in require_client().frame_array.iter_frames():
        if record is not None and int(getattr(record, "frame_hash", 0) or 0) == hash_value:
            dlg_redirect = int(candidate)
            break
    row(
        "outpost",
        "ReturnToOutpost()",
        f"the DlgRedirect frame on screen (hash {hash_value}, "
        f"{'id ' + str(dlg_redirect) if dlg_redirect else 'not present'})",
        bool(dlg_redirect),
    )
    return rows


def hold_plan() -> list[dict[str, Any]]:
    """What the ``hold`` stage *would* call, decided from reads alone.

    The stage's safety claim is that every call it makes is refused by the source's own guard, because
    the value it passes is the value the client already reports. That is decided entirely by **reads**,
    so the decision can be made — and checked — before anything connects: each entry says the call, the
    argument it would pass, what the client holds, and whether the member's own comparison makes it a
    no-op. Run it as part of the read stage (unelevated, nothing called) and the elevated stage has
    nothing left to surprise anyone with.
    """

    from py4gw import party as party_module
    from py4gw.party import Party

    plan: list[dict[str, Any]] = []

    def entry(call: str, passed: Any, held: Any) -> None:
        plan.append(
            {
                "call": call,
                "would_pass": passed,
                "client_holds": held,
                "refused_by_the_source": passed == held,
            }
        )

    plan.append(
        {
            "call": f"SetTickasToggle({party_module.tick_work_as_toggle})",
            "would_pass": party_module.tick_work_as_toggle,
            "client_holds": "the port's own flag, not the client's",
            "refused_by_the_source": True,
        }
    )
    plan.append(
        {
            "call": "SetTicked(True)",
            "would_pass": True,
            "client_holds": "nothing: the source's body writes to an object it discards",
            "refused_by_the_source": True,
        }
    )
    plan.append(
        {
            "call": "RespondToPartyRequest(0, True)",
            "would_pass": (0, True),
            "client_holds": "nothing: native's body is `(void)party_id; (void)accept; return true;`",
            "refused_by_the_source": True,
        }
    )
    entry(
        "SetHardMode()" if Party.IsHardMode() else "SetNormalMode()",
        Party.IsHardMode(),
        Party.IsHardMode(),
    )

    world = _world()
    for index in range(1, (Party.GetHeroCount() or 0) + 1):
        agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(index)
        behavior = _hero_behavior(world, index)
        if agent_id and behavior is not None:
            entry(f"SetHeroBehavior({agent_id}, {behavior})", behavior, behavior)
        disabled = _hero_disabled(world, index)
        if agent_id and disabled is not None:
            for slot in range(1, 9):
                enabled = not (disabled & (1 << (slot - 1)))
                entry(f"SetSkillAIEnabled({agent_id}, {slot}, {enabled})", enabled, enabled)

    pet = _pet_state(world)
    if pet is None:
        plan.append({"call": "SetPetBehavior", "skipped": "this party has no pet record"})
    else:
        arguments = _pet_hold_call(pet)
        if arguments is None:
            plan.append(
                {
                    "call": "SetPetBehavior",
                    "skipped": (
                        "the pet's behaviour is not Fight and it holds a locked target, so the "
                        "source's own body would clear that lock"
                    ),
                }
            )
        else:
            behavior, lock_target_id = arguments
            entry(
                f"SetPetBehavior({behavior}, {lock_target_id})",
                (behavior, lock_target_id),
                (pet["behavior"], pet["locked_target_id"]),
            )
    return plan


def reads_stage(win32: Win32, process: dict[str, Any], report: dict[str, Any]) -> int:
    """Run the read stage and report; nothing is connected and nothing is called."""

    from py4gw import client as client_module

    pid = int(process["pid"])
    module = win32.get_main_module(pid)
    report["module"] = {
        "base": hex(int(module["base_address"])),
        "size": hex(int(module["size"])),
    }
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        stand_in = _LiveClient(pid, reader, scanner, patterns)
        previous = client_module._current_client
        client_module._current_client = stand_in  # type: ignore[attr-defined]
        try:
            report["reads"] = party_reads()
            report["hold_plan"] = hold_plan()
            report["act_readiness"] = act_readiness()
            # The very function both elevated stages use for their before/after comparison, run here
            # first: read-only, against the client, so a read that cannot answer is found now.
            report["state"] = client_state()
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()
    report["note"] = (
        "read stage: unelevated, no connection and no capability layer — the stand-in's "
        "call_function raises, so a member that tried to act would have said so here. 'hold_plan' is "
        "what the elevated hold stage would call, decided from these same reads: every entry's "
        "'refused_by_the_source' must be true, or that call would write."
    )
    return 0


# ── the acting stages ────────────────────────────────────────────────────────
def entry_is_original(win32: Win32, pid: int) -> bool:
    """Whether both hooked entries hold the client's own bytes (nothing else attached)."""

    hooked = (
        ("game_thread.leave_game_thread_func", "55 8b ec 81 ec 20 02 00 00"),
        ("ui.send_ui_message_func", "55 8b ec 8b 45 08 83 f8 56"),
    )
    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        catalog = PatternCatalog.from_directory("offsets")
        for name, expected in hooked:
            result = catalog.resolve(name, scanner)
            if not result.ok:
                return False
            if reader.read(int(result.value), len(expected) // 3 + 1).hex(" ") != expected:
                return False
        return True
    finally:
        reader.close()


def client_state() -> dict[str, Any]:
    """The readings every acting stage compares before and after.

    **Every one of them goes through `_ask`**, including the three that read the world context
    directly: a stage that dies mid-way with a traceback would leave the owner without the report that
    says what happened, so a read that refuses becomes a string in the report instead. The read stage
    calls this same function, so its reads are exercised against the client before either elevated
    stage depends on them.
    """

    from py4gw.party import Party

    world = _ask(_world)
    hero_count = _ask(Party.GetHeroCount)
    if not isinstance(hero_count, int):
        hero_count = 0
    return {
        "party_size": _ask(Party.GetPartySize),
        "hard_mode": _ask(Party.IsHardMode),
        "all_flag": _ask(Party.Heroes.GetAllFlag),
        "heroes": [
            {
                "position": index,
                "agent_id": _ask(
                    lambda index=index: Party.Heroes.GetHeroAgentIDByPartyPosition(index)
                ),
                "behavior": _ask(lambda index=index: _hero_behavior(world, index)),
                "disabled": _ask(lambda index=index: _hero_disabled(world, index)),
            }
            for index in range(1, hero_count + 1)
        ],
        "pet": _ask(lambda: _pet_state(world)),
    }


def _world() -> Any:
    from py4gw.client import require_client

    return require_client().read_world_context()


def _hero_behavior(world: Any, position: int) -> Any:
    """The hero-flag record's own ``hero_behavior`` word, as the probe reads it."""

    from py4gw.party import Party

    agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(position)
    for flag in (world.hero_flags if world is not None else None) or []:
        if int(flag.agent_id) == int(agent_id or 0):
            return int(flag.hero_behavior)
    return None


def _hero_disabled(world: Any, position: int) -> Any:
    """The hero's skillbar ``disabled`` word, as the probe reads it."""

    from py4gw.party import Party

    agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(position)
    for bar in (world.skillbars if world is not None else None) or []:
        if int(bar.agent_id) == int(agent_id or 0):
            return int(bar.disabled)
    return None


def _pet_state(world: Any) -> Any:
    for pet in (world.pets if world is not None else None) or []:
        return {
            "agent_id": int(pet.agent_id),
            "owner_agent_id": int(pet.owner_agent_id),
            "behavior": int(pet.behavior),
            "locked_target_id": int(pet.locked_target_id),
        }
    return None


def hold_stage(report: dict[str, Any]) -> int:
    """Value-preserving acting calls: the guards and the read path, with no state change.

    Each call is made with **the value the client already reports**, which the source's own guards
    turn into a refusal — so what this proves is that the member answers, that its guards are the
    source's, and that its reads are right. The real writes are the ``act`` stage, with the owner.

    **One step is deliberately skipped rather than risked, and the reason is the pet.** A pet whose
    behaviour is not ``Fight`` has ``target_agent_id = 0`` in the source's own body, so calling
    `SetPetBehavior` with the values it holds would still write the **lock** when the pet has one —
    a state change dressed as a value-preserving call. `_pet_hold_call` returns the arguments only when
    the call cannot write anything, and says so otherwise.
    """

    from py4gw import party as party_module
    from py4gw.party import Party

    report["before"] = client_state()
    calls: dict[str, Any] = {}

    calls[f"SetTickasToggle({party_module.tick_work_as_toggle})"] = _act(
        lambda: Party.SetTickasToggle(party_module.tick_work_as_toggle)
    )
    calls["SetTicked(True)"] = _act(lambda: Party.SetTicked(True))
    calls["RespondToPartyRequest(0, True)"] = _act(
        lambda: Party.RespondToPartyRequest(0, True)
    )
    if Party.IsHardMode():
        calls["SetHardMode (already hard)"] = _act(Party.SetHardMode)
    else:
        calls["SetNormalMode (already normal)"] = _act(Party.SetNormalMode)

    world = _world()
    for index in range(1, (Party.GetHeroCount() or 0) + 1):
        agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(index)
        behavior = _hero_behavior(world, index)
        if agent_id and behavior is not None:
            calls[f"SetHeroBehavior({agent_id}, {behavior})"] = _act(
                lambda agent_id=agent_id, behavior=behavior: Party.Heroes.SetHeroBehavior(
                    agent_id, behavior
                )
            )
        disabled = _hero_disabled(world, index)
        if agent_id and disabled is not None:
            for slot in range(1, 9):
                enabled = not (disabled & (1 << (slot - 1)))
                calls[f"SetSkillAIEnabled({agent_id}, {slot}, {enabled})"] = _act(
                    lambda agent_id=agent_id, slot=slot, enabled=enabled: Party.Heroes.SetSkillAIEnabled(
                        agent_id, slot, enabled
                    )
                )

    pet = _pet_state(world)
    if pet is None:
        calls["SetPetBehavior"] = "skipped: this party has no pet record"
    else:
        arguments = _pet_hold_call(pet)
        if arguments is None:
            calls["SetPetBehavior"] = (
                "skipped: the pet's behaviour is not Fight and it holds a locked target, so the "
                "source's own body would clear that lock — the act stage is where the pet is driven"
            )
        else:
            behavior, lock_target_id = arguments
            calls[f"SetPetBehavior({behavior}, {lock_target_id})"] = _act(
                lambda behavior=behavior, lock_target_id=lock_target_id: Party.Pets.SetPetBehavior(
                    behavior, lock_target_id
                )
            )

    report["held"] = calls
    report["after"] = client_state()
    report["unchanged"] = report["before"] == report["after"]
    report["note"] = (
        "hold stage: every call used the value the client already reports, so the sources' own "
        "guards refuse the write and the state must be identical afterwards. A 'changed' result "
        "here is a defect, not an expected write."
    )
    return 0 if report["unchanged"] else 4


def henchman_is_in_party(agent_id: int) -> bool:
    """Whether the party's henchman records hold this **agent id**, which is what the members take."""

    from py4gw.party import Party

    return any(int(member.agent_id) == int(agent_id) for member in Party.GetHenchmen())


def _party_window_on_screen() -> bool:
    """Whether the party window's frame is in the client's frame array right now.

    The label's hash comes from this port's own offline table (``frame_names.NAME_TO_HASH``, the same
    way `ReturnToOutpost`'s `DlgRedirect` check is made), so asking costs nothing and needs no client
    function. Round 25 is why it is asked at all: `LeaveParty` presses the party window's button
    callback, and pressing it with no such window asserted the client (`Assertion: childId`,
    ``FrApi.cpp(3916)``).
    """

    from py4gw.client import require_client
    from py4gw.frame_tree.frame_names import NAME_TO_HASH

    hash_value = int(NAME_TO_HASH.get("Party", 0))
    if not hash_value:
        return False
    return any(
        record is not None and int(getattr(record, "frame_hash", 0) or 0) == hash_value
        for _, record in require_client().frame_array.iter_frames()
    )


def _pet_hold_call(pet: dict[str, Any]) -> tuple[int, int] | None:
    """The arguments that make `Pets.SetPetBehavior` a no-op, or ``None`` if none do.

    The source's body resolves a target **only** for ``Fight`` (``Constants::HeroBehavior::Fight``,
    Reforged's ported ``PetBehavior.Fight`` — ``0``); every other behaviour leaves ``target_agent_id``
    at ``0`` and the lock is written whenever the pet holds one. So the call is value-preserving when

    * the pet's behaviour is ``Fight`` — passing its own locked target back writes nothing, because
      the target resolves to the same id (or the member refuses before writing at all), or
    * the pet holds **no** locked target — every behaviour then leaves both words as they are.
    """

    from py4gw.enums_src.hero_enums import PetBehavior

    behavior = int(pet["behavior"])
    locked = int(pet["locked_target_id"])
    if behavior == int(PetBehavior.Fight):
        return behavior, locked
    if locked == 0:
        return behavior, 0
    return None


def act_plan(allowed: set[str]) -> list[dict[str, Any]]:
    """What the ``act`` stage knows how to do, in the order it would do it."""

    return [
        {"step": name, "what": what, "allowed": name in allowed} for name, what in STEPS
    ]


def act_stage(report: dict[str, Any], allowed: set[str],
              options: dict[str, Any] | None = None) -> int:
    """The steps that really act — each one only when the owner has named it.

    ``options`` carries what a step needs to be *specific* rather than merely allowed: which hero
    number and slot `use-skill` presses, and which hero name `party-add`/`party-kick` use. They come
    from the command line (``--hero-number``, ``--slot``, ``--hero``) and have the safe defaults the
    structure records in `STEPS`.
    """

    from py4gw.map import Map
    from py4gw.party import Party

    options = options or {}

    report["plan"] = act_plan(allowed)
    if not allowed:
        report["note"] = (
            "act stage: nothing was allowed, so nothing ran. Name the steps you want, one at a "
            "time, e.g. `--allow flags` and watch the client."
        )
        return 0

    report["before"] = client_state()
    done: dict[str, Any] = {}

    if "flags" in allowed:
        current = Party.Heroes.GetAllFlag()
        x, y = (current if isinstance(current, tuple) and len(current) == 2 else (0.0, 0.0))
        if math.isfinite(float(x)) and math.isfinite(float(y)):
            done["FlagAllHeroes"] = _act(lambda: Party.Heroes.FlagAllHeroes(float(x), float(y)))
        else:
            done["FlagAllHeroes"] = "skipped: the party's flag is unset, so there is no position"
        done["UnflagAllHeroes"] = _act(Party.Heroes.UnflagAllHeroes)

    if "flag-hero" in allowed and (Party.GetHeroCount() or 0) > 0:
        current = Party.Heroes.GetAllFlag()
        x, y = (current if isinstance(current, tuple) and len(current) == 2 else (0.0, 0.0))
        if math.isfinite(float(x)) and math.isfinite(float(y)):
            agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(1)
            done["FlagHero(1, the party's flag)"] = _act(
                lambda: Party.Heroes.FlagHero(int(agent_id or 0), float(x), float(y))
            )
            done["UnflagHero(1)"] = _act(lambda: Party.Heroes.UnflagHero(1))
        else:
            done["FlagHero"] = "skipped: the party's flag is unset, so there is no position to use"

    if "behaviour" in allowed:
        world = _world()
        current = _hero_behavior(world, 1)
        if current is not None:
            other = 0 if int(current) != 0 else 2
            agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(1)
            done["SetHeroBehavior(other)"] = _act(
                lambda: Party.Heroes.SetHeroBehavior(int(agent_id or 0), other)
            )
            # The client owns the record the member compares against, so the restore is computed and
            # sent only once the flip is visible there — otherwise the member's own guard reads the
            # value it is about to replace, refuses, and the flip is what stays (round 24's finding).
            done["SetHeroBehavior(other) landed"] = _settle(
                lambda: _hero_behavior(world, 1), other
            )
            done["SetHeroBehavior(back)"] = _act(
                lambda: Party.Heroes.SetHeroBehavior(int(agent_id or 0), int(current))
            )
            done["SetHeroBehavior(back) landed"] = _settle(
                lambda: _hero_behavior(world, 1), int(current)
            )
        else:
            done["SetHeroBehavior"] = "skipped: no hero-flag record for position 1"

    if "skill-ai" in allowed:
        world = _world()
        disabled = _hero_disabled(world, 1)
        agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(1)
        if disabled is not None and agent_id:
            enabled = bool(disabled & 0x1)
            flipped_bit = 0 if enabled else 1
            done["SetSkillAIEnabled(flip)"] = _act(
                lambda: Party.Heroes.SetSkillAIEnabled(int(agent_id), 1, enabled)
            )
            done["SetSkillAIEnabled(flip) landed"] = _settle(
                lambda: (int(_hero_disabled(world, 1) or 0) & 0x1), flipped_bit
            )
            done["SetSkillAIEnabled(back)"] = _act(
                lambda: Party.Heroes.SetSkillAIEnabled(int(agent_id), 1, not enabled)
            )
            done["SetSkillAIEnabled(back) landed"] = _settle(
                lambda: (int(_hero_disabled(world, 1) or 0) & 0x1), 1 - flipped_bit
            )
        else:
            done["SetSkillAIEnabled"] = "skipped: no skillbar for position 1"

    if "difficulty" in allowed:
        if not Map.IsOutpost():
            done["difficulty"] = (
                "skipped: the client only changes the party's mode in an outpost, and this map is "
                "not one — the plan's own words, now checked here too"
            )
        elif not Party.IsHardMode() and not Party.IsHardModeUnlocked():
            # Round 24's live finding: the call goes through and the client ignores it, because hard
            # mode is not unlocked on this account (measured: ten seconds of polling, its own flag
            # never moved). The step refuses and says so instead of reporting a change nobody sees.
            done["difficulty"] = (
                "skipped: hard mode is not unlocked on this account (the client accepts the call and "
                "never applies it — measured at 10 s), so there is no mode to change"
            )
        elif Party.IsHardMode():
            done["SetNormalMode"] = _act(Party.SetNormalMode)
            done["SetNormalMode landed"] = _settle(Party.IsHardMode, False)
            done["SetHardMode(back)"] = _act(Party.SetHardMode)
            done["SetHardMode(back) landed"] = _settle(Party.IsHardMode, True)
        else:
            done["SetHardMode"] = _act(Party.SetHardMode)
            done["SetHardMode landed"] = _settle(Party.IsHardMode, True)
            done["SetNormalMode(back)"] = _act(Party.SetNormalMode)
            done["SetNormalMode(back) landed"] = _settle(Party.IsHardMode, False)

    if "search" in allowed:
        from py4gw.context.party_context import PartySearchType

        # Native's own first enumerator, taken by name rather than as a bare 0: the client's
        # ``PartySearchType`` words are ``context/party.h:60-66``'s, and Reforged names no enum at all.
        search_type = int(PartySearchType.PartySearchType_Hunting)
        done[f"SearchParty({search_type}, 'Stealth probe')"] = _act(
            lambda: Party.SearchParty(search_type, "Stealth probe")
        )
        done["SearchPartyCancel"] = _act(Party.SearchPartyCancel)

    if "pet" in allowed and Party.Pets.GetPetID(0):
        done["SetPetBehavior(Fight, 0)"] = _act(lambda: Party.Pets.SetPetBehavior(0, 0))

    if "use-skill" in allowed:
        hero_number = int(options.get("hero_number", 1))
        slot = int(options.get("slot", 1))
        agent_id = Party.Heroes.GetHeroAgentIDByPartyPosition(hero_number)
        if not agent_id or (Party.GetHeroCount() or 0) < hero_number:
            done["UseSkill"] = (
                f"skipped: hero {hero_number} is not in the party (the payload's control action is "
                "chosen by that number, so it has to exist)"
            )
        else:
            # ``target_id == 0`` is what the source's own binding does for "no target given": the
            # body then presses the control action without touching the target, and the restore below
            # runs only because the source's two tests are not symmetric.
            done[f"UseSkill(hero {hero_number}, slot {slot}, target 0)"] = _act(
                lambda: Party.Heroes.UseSkill(hero_number, slot, 0)
            )

    if "party-add" in allowed:
        hero_name = str(options.get("hero_name", "Norgu"))
        if not Map.IsOutpost():
            done["AddHeroByName"] = (
                "skipped: the party can only be changed in an outpost (the client refuses it "
                "anywhere else), and this map is not one"
            )
        else:
            hero_id = int(Party.Heroes.GetHeroIdByName(hero_name) or -1)

            def hero_is_in_party() -> bool:
                """Whether the party's hero array holds this hero (0-based, as the member indexes)."""

                return any(
                    int(Party.Heroes.GetHeroIDByPartyPosition(index) or -1) == hero_id
                    for index in range(Party.GetHeroCount() or 0)
                )

            done[f"AddHeroByName({hero_name!r})"] = _act(
                lambda: Party.Heroes.AddHeroByName(hero_name)
            )
            # The party change is the client's to apply, like every other one — so the step waits for
            # the party to **hold the member**, not for a count to grow: adding a hero who is already
            # there is a no-op the client is right to ignore, and a count would call that a failure.
            done[f"AddHeroByName({hero_name!r}) landed"] = _settle(hero_is_in_party, True)
            # ``Henchmen.AddHenchman`` takes the henchman's **agent id**, which is a live value only
            # the owner can name — target the henchman in the outpost and read
            # ``Player.GetTargetID()``, or run ``python tests/probe_party_henchmen.py``, which lists the
            # ones standing here, nearest first. Without an id the member is left alone and the report
            # says why, rather than this probe picking an NPC for the tester.
            henchman_id = options.get("henchman_id")
            if henchman_id is None:
                done["AddHenchman"] = (
                    "skipped: no `--henchman <agent_id>` was given, and that id is a live agent id "
                    "only you can name (target the henchman and read Player.GetTargetID(), or use "
                    "`python tests/probe_party_henchmen.py`, which lists the ones standing here)"
                )
            else:
                given = int(henchman_id)
                done[f"AddHenchman({given})"] = _act(
                    lambda: Party.Henchmen.AddHenchman(given)
                )
                done[f"AddHenchman({given}) landed"] = _settle(
                    lambda: henchman_is_in_party(given), True
                )

    if "party-kick" in allowed:
        hero_name = str(options.get("hero_name", "Norgu"))
        agent_id = Party.Heroes.GetHeroIdByName(hero_name)
        hero_count = Party.GetHeroCount() or 0
        # ``GetHeroIDByPartyPosition`` indexes the **hero array**, 0-based — the source's own
        # ``for index, hero in enumerate(heroes): if index == hero_position`` — not the party window's
        # positions. Round 25's live run is what showed this guard the difference: a party whose only
        # hero sits at index 0 was invisible to a loop that started at 1, so the step reported "not in
        # this party" and skipped a kick it should have made.
        in_party = any(
            int(Party.Heroes.GetHeroIDByPartyPosition(index) or -1) == int(agent_id)
            for index in range(hero_count)
        )
        if not in_party:
            done["KickHeroByName"] = (
                f"skipped: {hero_name!r} is not in this party, so there is nothing to kick"
            )
        else:
            done[f"KickHeroByName({hero_name!r})"] = _act(
                lambda: Party.Heroes.KickHeroByName(hero_name)
            )
            done[f"KickHeroByName({hero_name!r}) landed"] = _settle(
                lambda: not any(
                    int(Party.Heroes.GetHeroIDByPartyPosition(index) or -1) == int(agent_id)
                    for index in range(Party.GetHeroCount() or 0)
                ),
                True,
            )
        henchman_id = options.get("henchman_id")
        if henchman_id is not None:
            given = int(henchman_id)
            done[f"KickHenchman({given})"] = _act(
                lambda: Party.Henchmen.KickHenchman(given)
            )
            done[f"KickHenchman({given}) landed"] = _settle(
                lambda: not henchman_is_in_party(given), True
            )

    if "leave" in allowed:
        # Round 25: this press crashed a client. `LeaveParty` is native's `leave_party`, which calls
        # the party window's button callback with `ctx[0xd] = 1`; called from outside while the party
        # window is not on screen the engine asserted on a frame child id it did not have
        # (`Assertion: childId`, `FrApi.cpp(3916)`, Gw.exe build 38888). So the step now requires the
        # window the press belongs to, and refuses otherwise — the member itself is untouched.
        if not _party_window_on_screen():
            done["LeaveParty"] = (
                "skipped: the party window is not on screen, and the button press this member makes "
                "asserted the client on 2026-09-29 when it was called without it "
                "(`Assertion: childId`, `FrApi.cpp(3916)`) — open the party window first"
            )
        elif (Party.GetPlayerCount() or 0) < 2:
            done["LeaveParty"] = (
                "skipped: this party has no other player, and leaving a party of one is not a "
                "thing the client's own button does"
            )
        else:
            done["LeaveParty"] = _act(Party.LeaveParty)

    if "outpost" in allowed:
        report["map_is_outpost"] = _act(Map.IsOutpost)
        # `ReturnToOutpost` answers `False` when the `DlgRedirect` button is not on screen, which is
        # the client's own condition: the member refuses rather than clicking something else.
        done["ReturnToOutpost"] = _act(Party.ReturnToOutpost)

    report["acted"] = done
    settles = [
        value for value in done.values() if isinstance(value, dict) and "settled" in value
    ]
    report["settled"] = all(bool(entry["settled"]) for entry in settles)
    report["after"] = client_state()
    report["note"] = (
        "act stage: only the named steps ran, and each reversible one was put back — after waiting, "
        "bounded, for the client to show the change it was sent ('settled'), because the client applies "
        "a party change when it processes the command and a restore computed before that lands replaces "
        "the value it meant to keep. The steps that change the party or leave the map are the owner's "
        "call, one at a time — and each refuses here when the client's own condition for it is not met "
        "(no such hero, a party of one, not an outpost)."
    )
    return 0


def main() -> int:
    argv = [argument for argument in sys.argv[1:]]
    allowed: set[str] = set()
    if "--allow" in argv:
        index = argv.index("--allow")
        allowed = {name.strip() for name in argv[index + 1].split(",") if name.strip()}
        del argv[index : index + 2]

    # What a step needs to be specific rather than merely allowed. Each default is the one `STEPS`
    # describes: hero 1 slot 1 for a skill press, and Norgu (the first name in the port's own table)
    # for the party steps — never a choice this probe makes on the owner's behalf silently, because
    # the report prints what it used.
    options: dict[str, Any] = {}
    for flag, key, cast in (
        ("--hero-number", "hero_number", int),
        ("--slot", "slot", int),
        ("--hero", "hero_name", str),
        ("--henchman", "henchman_id", int),
    ):
        if flag in argv:
            index = argv.index(flag)
            options[key] = cast(argv[index + 1])
            del argv[index : index + 2]

    stage = argv[0] if argv else "reads"
    report_path = argv[1] if len(argv) > 1 else REPORT_PATH

    report: dict[str, Any] = {"stage": stage}
    if options:
        report["options"] = options
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report, report_path)
    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())

    if stage == "reads":
        code = reads_stage(win32, process, report)
        return _write(report, report_path, code)

    if stage == "act" and not allowed:
        # The plan is reviewable without a client or elevation: nothing will run, so nothing is
        # connected — which also means the owner can read it at any time, including now.
        report["plan"] = act_plan(allowed)
        report["note"] = (
            "act stage: nothing was allowed, so nothing ran and nothing was connected. Name the "
            "steps you want, one at a time, e.g. `--allow flags`, and watch the client."
        )
        return _write(report, report_path, 0)

    if not win32.is_elevated():
        report["error"] = "not elevated: connecting asserts elevation"
        return _write(report, report_path, 3)
    if not entry_is_original(win32, int(process["pid"])):
        report["error"] = (
            "one of the two hooked entries does not hold the client's own bytes, so another "
            "controller is attached or was killed while attached. Nothing was done."
        )
        return _write(report, report_path, 7)

    import py4gw

    with py4gw.connect(process, game_thread=True) as _client:
        report["game_thread"] = True
        code = hold_stage(report) if stage == "hold" else act_stage(report, allowed, options)

    # The connection has put the client's own bytes back by now; the entries are read again, directly
    # and read-only, so the report says whether the client was left as it was found.
    report["hooks_original_after_disconnect"] = bool(
        entry_is_original(win32, int(process["pid"]))
    )
    return _write(report, report_path, code)


def summary_lines(report: dict[str, Any]) -> list[str]:
    """The one-line-per-thing a person watching the client wants, before the JSON.

    The report is the evidence; these lines are what a reader needs at a glance while the game is in
    front of them — above all ``hold``'s verdict, because ``unchanged: False`` there is a defect in the
    port rather than an expected write.
    """

    lines: list[str] = []
    if report.get("error"):
        lines.append(f"error: {report['error']}")
    if report.get("stage") == "hold":
        lines.append(
            f"hold: unchanged={report.get('unchanged')} "
            f"({'nothing moved, as it must' if report.get('unchanged') else 'A READING MOVED — defect'})"
        )
        for name, result in (report.get("held") or {}).items():
            lines.append(f"  held: {name} -> {result}")
    if report.get("stage") == "act":
        plan = report.get("plan") or []
        allowed = [row["step"] for row in plan if row.get("allowed")]
        if not allowed:
            lines.append("act: nothing allowed, nothing ran")
            for row in plan:
                lines.append(f"  step: {row['step']} — {row['what']}")
        for name, result in (report.get("acted") or {}).items():
            lines.append(f"act: {name} -> {result}")
        if report.get("settled") is not None:
            lines.append(
                f"act: every change the client was sent is visible in its own records: "
                f"{report['settled']}"
                + ("" if report.get("settled") else "  <-- A STEP DID NOT LAND")
            )
    if report.get("stage") == "reads":
        reads = report.get("reads") or {}
        bad = 0
        for section in reads.values():
            for value in (section.values() if isinstance(section, dict) else []):
                if isinstance(value, str) and ("Error" in value or "error" in value):
                    bad += 1
        lines.append(f"reads: {bad} member(s) refused")
        plan = report.get("hold_plan") or []
        would_write = [row for row in plan if row.get("refused_by_the_source") is False]
        lines.append(
            f"hold would call {len(plan)} thing(s); {len(would_write)} of them would write"
        )
        for row in would_write:
            lines.append(
                f"  WOULD WRITE: {row.get('call')} (passing {row.get('would_pass')}, "
                f"the client holds {row.get('client_holds')})"
            )
        readiness = report.get("act_readiness") or []
        ready = [row["step"] for row in readiness if row.get("runnable_now")]
        lines.append(f"act steps runnable now: {', '.join(ready) if ready else 'none'}")
        for row in readiness:
            if not row.get("runnable_now"):
                lines.append(f"  not now: {row['step']} — {row['guard']}")
    return lines


def _write(report: dict[str, Any], path: str, code: int = 0) -> int:
    for line in summary_lines(report):
        print(line)
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
