"""GwAu3's ``Map_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**The shape GwAu3 gives these calls is kept.** Every travel action follows the same three steps:
``Map_InitMapIsLoaded()`` clears its own "loaded" flag, the travel is sent, and ``Map_WaitMapIsLoaded()``
waits for the map to arrive when the caller asked it to. That is a stateful pair inside GwAu3 --
``$g_p_MapIsLoaded`` is a slot in its injected block (``docs/_inventory_gwau3_party_map_ui_trade.md``) --
and this module keeps the ordering and the optional wait, because a caller's
``Map_TravelTo($map, ..., $a_WaitToLoad = False)`` means "send it and do not block".

**Two of these are refused, and both are refused on the caller's behalf.** ``Map_InitMapIsLoaded`` and
``Map_MapIsLoaded`` read and write a flag inside GwAu3's own injected block. This project has no such
block, and its ``Map.IsMapReady`` (``py4gw/map.py:164``) is a predicate over the client's own data
rather than a controller-side flag -- so reproducing them would mean inventing controller state the
sources do not have. The wait functions below use the client's own predicate instead, and say so.
"""

from __future__ import annotations

import random
import time
from typing import Any

from ..map import Map
from ..player import Player
from .data_agent import Agent_ConvertID  # noqa: F401  (kept for the module's own imports)

__all__ = [
    "Map_EnterChallenge",
    "Map_InitMapIsLoaded",
    "Map_LeaveGH",
    "Map_MapIsLoaded",
    "Map_Move",
    "Map_MoveLayer",
    "Map_MoveMap",
    "Map_ReturnToOutpost",
    "Map_RndTravel",
    "Map_TravelGH",
    "Map_TravelTo",
    "Map_WaitMapIsLoaded",
    "Map_WaitMapIsLoaded_Ping",
    "Map_WaitMapLoading",
]

# GwAu3's own default wait (`GwAu3_Cmd_Map.au3`, `Map_WaitMapIsLoaded($a_i_Timeout = 30000)`).
_DEFAULT_TIMEOUT_MS = 30000

# How often the wait polls. GwAu3's loop is a busy `Sleep(100)`; this is the same order of magnitude and
# is bounded by the caller's own timeout either way.
_POLL_MS = 100


def Map_Move(x: float, y: float, randomize: float = 50) -> bool:
    """Move to a point, with GwAu3's own randomisation (``GwAu3_Cmd_Map.au3:2-25``).

    **GwAu3's randomisation is part of this function and is kept.** Its own default is
    ``$a_f_Randomize = 50``, and when it is above zero it adds ``Random(-r, r)`` to each coordinate
    *before* storing them -- so the destination is never exactly the point asked for. The layer keeps
    that, because a migrating script's ``Map_Move($x, $y)`` is asking for GwAu3's wobble as much as for
    the destination. ``Player.Move`` (``py4gw/player.py:1188``) is handed the point this function
    decided on, which is the same division of labour as GwAu3's.
    """

    if randomize > 0:
        x += random.uniform(-randomize, randomize)
        y += random.uniform(-randomize, randomize)

    # `GwAu3_Cmd_Map.au3:10-12` stores the point it decided on -- after the randomisation, before the
    # move is sent -- and `Map_GetLastMoveCoords` answers that pair. It reads it from `data_map`, the
    # module of the source file that declares the reader (`GwAu3_Data_Map.au3:19-22`), so the layer's
    # transcription of `$g_f_LastMoveX/Y` lives where its reader lives. Without these two lines the
    # reader would answer the pair it was initialised with for ever.
    from . import data_map

    data_map.g_f_LastMoveX = x
    data_map.g_f_LastMoveY = y

    Player.Move(x, y, 0)
    return True


def Map_MoveLayer(x: float, y: float, layer: int = 0) -> bool:
    """Move to a point on a given layer (``GwAu3_Cmd_Map.au3:27-38``).

    No randomisation here -- GwAu3's own version has none, and its third argument is the layer, which
    is ``Player.Move``'s ``zPlane``.
    """

    Player.Move(x, y, layer)
    return True


def Map_TravelTo(
    map_id: int,
    language: int | None = None,
    region: int | None = None,
    district: int = 0,
    wait_to_load: bool = True,
) -> bool:
    """Travel to an outpost (``GwAu3_Cmd_Map.au3:86-99``).

    **GwAu3's own short-circuit is kept.** Before travelling it checks whether the character is already
    on that map, in an outpost, with the same region and language -- and answers ``True`` without
    sending anything. That is not an optimisation to drop: a script that calls ``Map_TravelTo`` in a
    loop relies on it not re-sending.

    ``language`` and ``region`` default here to ``None``, which resolves to the character's current
    values -- GwAu3's own defaults are ``Map_GetCharacterInfo("Language")`` and
    ``Map_GetCharacterInfo("Region")``, evaluated at call time. The effect is the same; the difference is
    that AutoIt evaluates the default at call time and Python cannot, so the resolution is written out.
    """

    current_map = Map.GetMapID()
    # `Map.GetRegion` and `Map.GetLanguage` answer `(id, name)`; GwAu3's `Map_GetCharacterInfo` answers
    # the number alone, so the id is what is taken. Passing the tuple through would hand the client's own
    # travel call a pair where it expects a word.
    current_region = Map.GetRegion()[0]
    current_language = Map.GetLanguage()[0]

    resolved_region = current_region if region is None else region
    resolved_language = current_language if language is None else language

    if (
        current_map == map_id
        and Map.IsOutpost()
        and resolved_language == current_language
        and resolved_region == current_region
    ):
        return True

    Map.TravelToRegion(map_id, resolved_region, district, resolved_language)
    if wait_to_load:
        return Map_WaitMapIsLoaded()
    return True


def Map_MoveMap(map_id: int, region: int, district: int, language: int) -> bool:
    """Send a travel request (``GwAu3_Cmd_Map.au3:41-44``).

    GwAu3 forges ``Core_SendPacket(0x18, $GC_I_HEADER_PARTY_TRAVEL, map, region, district, language,
    False)``. This calls ``Map.TravelToRegion`` -- the same four values, through the client's own
    ``kTravel`` message.

    **The argument order is GwAu3's, and it differs from its own ``Ui_`` twin.** ``Map_MoveMap`` takes
    ``(map, region, district, language)`` (``:41``) while ``Ui_MoveMap`` takes
    ``(map, region, language, district)`` (``GwAu3_Cmd_Ui.au3:217``) -- the same four values, two orders.
    Each keeps its own, because a script that swapped them would travel to the wrong district.
    """

    Map.TravelToRegion(map_id, region, district, language)
    return True


def Map_TravelGH(wait_to_load: bool = True) -> bool:
    """Travel to the guild hall (``GwAu3_Cmd_Map.au3:61-70``).

    GwAu3 reads the guild hall's coordinates out of its own pointer chain and forges
    ``HEADER_PARTY_ENTER_GUILD_HALL`` with them. ``Map.TravelGH`` (``py4gw/map.py:895``) sends the
    client's own ``kGuildHall`` with the address of the client's **own** ``GuildContext.player_gh_key``
    -- the same travel, with the client supplying the key instead of the caller.
    """

    Map.TravelGH()
    if wait_to_load:
        return Map_WaitMapIsLoaded()
    return True


def Map_LeaveGH(wait_to_load: bool = True) -> bool:
    """Leave the guild hall (``GwAu3_Cmd_Map.au3:73-77``)."""

    Map.LeaveGH()
    if wait_to_load:
        return Map_WaitMapIsLoaded()
    return True


def Map_EnterChallenge(wait_to_load: bool = True) -> bool:
    """Enter a challenge mission or PvP (``GwAu3_Cmd_Map.au3:54-58``)."""

    Map.EnterChallenge()
    if wait_to_load:
        return Map_WaitMapIsLoaded()
    return True


def Map_ReturnToOutpost(wait_to_load: bool = True) -> bool:
    """Return to the outpost after resigning or failing (``GwAu3_Cmd_Map.au3:47-51``).

    GwAu3 forges ``HEADER_PARTY_RETURN_TO_OUTPOST``. This calls ``Party.ReturnToOutpost``
    (``py4gw/party.py:1262``), which clicks the client's own redirect button (``DlgRedirect``) -- the
    route ``docs/GWA3_ROUTE_MAP.md`` records for this row.
    """

    from ..party import Party

    Party.ReturnToOutpost()
    if wait_to_load:
        return Map_WaitMapIsLoaded()
    return True


def Map_InitMapIsLoaded() -> bool:
    """**Refused.** GwAu3's flag lives in its own injected block, and this project has none.

    ``GwAu3_Cmd_Map.au3`` calls this before every travel to clear ``$g_p_MapIsLoaded``, a slot its
    assembler allocates (``docs/_inventory_gwau3_party_map_ui_trade.md`` records it as a slot in the
    injected code block, not a client field). This project has no injected block to hold such a flag, and
    ``Map.IsMapReady`` (``py4gw/map.py:164``) is a predicate over the **client's** own data rather than a
    controller-side latch -- so there is no state to clear. Refused rather than returning ``True`` for
    having done nothing, because a caller that believed a flag had been cleared would then wait on it.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Map.au3's Map_InitMapIsLoaded clears $g_p_MapIsLoaded, a slot inside GwAu3's own "
        "injected code block (docs/_inventory_gwau3_party_map_ui_trade.md). This project installs no such "
        "block and holds no map-loaded latch; Map.IsMapReady (py4gw/map.py:164) reads the client's own "
        "data instead. There is no state to clear, so this refuses rather than pretending to clear it."
    )


def Map_MapIsLoaded() -> bool:
    """**Refused.** GwAu3 reads its own latch; this project has a client predicate instead.

    The two are not the same question: GwAu3's flag says whether *it* has seen the map load since it
    last cleared the flag, and ``Map.IsMapReady`` says whether the client's map data is present now.
    Answering one for the other is a wrong boolean a caller could not detect, so this refuses and names
    the predicate to use instead.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Map.au3's Map_MapIsLoaded reads $g_p_MapIsLoaded, a slot inside GwAu3's own injected "
        "code block, which says whether GwAu3 has seen a load since it cleared the flag. This project "
        "holds no such latch. Its equivalent question is Map.IsMapReady (py4gw/map.py:164), which is a "
        "predicate over the client's own data -- a different question, so this refuses rather than "
        "answering one for the other."
    )


def Map_WaitMapIsLoaded(timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> bool:
    """Wait for the map to be ready (``GwAu3_Cmd_Map.au3``, ``$a_i_Timeout = 30000``).

    GwAu3 polls its own latch, which ``Map_InitMapIsLoaded`` cleared. This polls
    ``Map.IsMapReady`` -- the client's own predicate -- for the same bounded time and answers whether it
    became true. The latch itself is refused (see ``Map_MapIsLoaded``); what is kept is the wait, its
    bound, and its answer.
    """

    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        if Map.IsMapReady():
            return True
        time.sleep(_POLL_MS / 1000.0)
    return Map.IsMapReady()


def Map_RndTravel(
    map_id: int, wait_to_load: bool = True, switch_district: bool = True, mode: int = 0
) -> bool:
    """Travel to a map in a random district (``GwAu3_Cmd_Map.au3:101-129``).

    **GwAu3's two lookup tables are reproduced verbatim**, because they are the function: district index
    to region and to language, and the mode's own bounds -- ``0`` all, ``1`` EU-only (districts 0..6),
    ``2`` US-only (7..8), ``3`` Asia-only (9..11). The tables and the bounds are data about the client's
    own district numbering, so a rewritten version would be a different function.

    Three of GwAu3's own quirks are kept because a caller's behaviour depends on them:

    * the random pick is only *avoided* when the chosen district happens to match the character's current
      region **and** language -- it steps one place around the ring rather than re-rolling;
    * when the character is already on the map and the instance is not explorable, and
      ``$a_b_SwitchDistrict`` is false, it answers ``True`` **without travelling**;
    * with one valid district and ``$a_b_SwitchDistrict`` true it also answers ``True`` without
      travelling.

    ``Map_MoveMap`` is handed the tables' values, which is GwAu3's own call at ``:127``.
    """

    regions = (2, 2, 2, 2, 2, 2, 2, 0, -2, 1, 3, 4)
    languages = (0, 2, 3, 4, 5, 9, 10, 0, 0, 0, 0, 0)

    district_min, district_max = 0, 11
    if mode == 1:
        district_max = 6
    elif mode == 2:
        district_min, district_max = 7, 8
    elif mode == 3:
        district_min = 9

    valid_districts = district_max - district_min + 1

    current_map = Map.GetMapID()
    current_region = Map.GetRegion()[0]
    current_language = Map.GetLanguage()[0]

    if current_map != map_id or Map.IsExplorable():
        index = random.randint(district_min, district_max)
    elif switch_district:
        if valid_districts == 1:
            return True
        index = random.randint(district_min, district_max)
        if regions[index] == current_region and languages[index] == current_language:
            index = ((index - district_min) + 1) % valid_districts + district_min
    else:
        return True

    Map_MoveMap(map_id, regions[index], 0, languages[index])
    if wait_to_load:
        return Map_WaitMapIsLoaded()
    return True


def Map_WaitMapIsLoaded_Ping(timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> bool:
    """Wait for the map to be ready, ping included (``GwAu3_Cmd_Map.au3``).

    GwAu3's second spelling of the same wait. Its difference from ``Map_WaitMapIsLoaded`` is that it also
    requires the client's ping to be non-zero -- the condition ``Map_WaitMapLoading`` makes -- so it is
    what a caller uses when "loaded" alone is not enough. Both are provided because both are in the
    source, and the name says which one a script asked for.
    """

    return Map_WaitMapLoading(map_id=-1, instance_type=-1, timeout_ms=timeout_ms)


def Map_WaitMapLoading(
    map_id: int = -1, instance_type: int = -1, timeout_ms: int = _DEFAULT_TIMEOUT_MS
) -> bool:
    """Wait for a map to finish loading (``GwAu3_Cmd_Map.au3:131-156``).

    **GwAu3's own readiness test is reproduced term for term**, because each term is a condition that
    becomes true only once the client has finished: a controlled-character pointer, a non-zero agent
    count, a skillbar array, a party context, the instance type and map id when asked for, no cinematic
    running, and a non-zero ping. This project can answer every one of them -- the ping is the only one
    without a direct member, and it is read from the world context's own field
    (``WorldContextStruct``, ``py4gw/context/world_context.py:1442``), which is where GwAu3 reads it too.

    **The cinematic skip is not called from inside the wait.** GwAu3 calls ``Cinematic_SkipCinematic``
    when it sees a cinematic (``:137``) so a loading screen cannot stall it. That is an *action* the
    caller did not ask for, so it is not taken here; the wait simply keeps waiting, and the caller can
    skip the cinematic itself with :func:`py4gw.gwa3.cmd_cinematic.Cinematic_SkipCinematic`. Recorded
    rather than hidden, because a caller relying on the wait to skip for it would see the difference.
    """

    from .data_agent import Agent_GetAgentPtr, Agent_GetMaxAgents

    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        if (
            Agent_GetAgentPtr(-2) is not None
            and Agent_GetMaxAgents() != 0
            and _skillbar_array_present()
            and _party_context_present()
            and (instance_type == -1 or Map.GetInstanceType() == instance_type)
            and (map_id == -1 or Map.GetMapID() == map_id)
            and not Map.IsInCinematic()
            and _ping() != 0
        ):
            return True
        time.sleep(250 / 1000.0)
    return False


def _skillbar_array_present() -> bool:
    """``World_GetWorldInfo("SkillbarArray") <> 0`` -- the skillbar array is reachable."""

    from ..client import require_client

    try:
        world = require_client().read_world_context()
    except (OSError, RuntimeError):
        return False
    return bool(world is not None and world.party_skillbar_array.m_buffer)


def _party_context_present() -> bool:
    """``Party_GetPartyContextPtr() <> 0`` -- the party context resolves."""

    from ..client import require_client

    try:
        return bool(require_client().party_context.get_ptr())
    except (OSError, RuntimeError):
        return False


def _ping() -> int:
    """``Other_GetPing()`` -- the client's own ping word, out of the world context.

    GwAu3 reads it at a fixed offset in the world context (``GwAu3_Data_World.au3``); this project's
    ``WorldContextStruct`` names the same region, and where it does not name the word exactly, the read
    is refused rather than guessed at elsewhere in this layer. Here only ``<> 0`` matters, which is what
    GwAu3 tests.
    """

    from .data_world import World_GetWorldInfo

    try:
        return int(World_GetWorldInfo("Ping"))
    except (NotImplementedError, KeyError, OSError, RuntimeError):
        return 0
