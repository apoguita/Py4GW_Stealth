"""External port of Reforged's ``Py4GWCoreLib/Agent.py``.

Every member of the Reforged ``Agent`` class is present here with the same name, the same
signature and the same return values, so a script that reads ``Agent.GetLevel(agent_id)`` keeps
working after switching libraries. What differs is *which* members can produce a value.

The Reforged class is a namespace of **148** ``@staticmethod``s over an agent record — the source's
own count, which an earlier pass measured as 147 because ``GetAnimationCode`` is declared
``def GetAnimationCode (agent_id : int)`` (``Agent.py:567-568``), with a space before its
parenthesis. This port keeps that shape and reaches the record through the ported contexts —
``py4gw/context/agent_array.py`` for the agents, ``py4gw/context/world_context.py`` for attributes
and NPC models — resolved the same way every other accessor class resolves the selected client,
through :func:`py4gw.client.require_client`.

Three groups exist, and each member says which one it is in its docstring:

``implemented``
    The value comes from an agent record this project can read. These members return exactly
    what Reforged returns, including its defaults when the record is missing. A member whose body
    calls another member of this class that raises is in this group too: the raise comes from the
    member that owns the missing piece, which is the source's own call graph.

``blocked``
    The member's own body needs something this port does not have: a companion class (``Effect``),
    a native console (``PySystem.Console``) or the frame loop Reforged's per-frame caches belong
    to. These raise ``NotImplementedError`` through :func:`_unported`, naming the file and the
    lines of what is missing, so the call site fails loudly instead of receiving a plausible wrong
    value. Two groups have left this one: the game-data enums (``enums_src/GameData_enums.py`` is
    ported at ``py4gw/enums_src/game_data_enums.py``, and the eight members that waited on it take
    their professions, allegiances and weapon types from it), and **the agent-name binding**
    (``PyAgent.get_agent_enc_name``, ``agent_bindings.cpp:216-224``) — which is ported at the top
    of this file as :func:`get_agent_enc_name`, over native's own ``GW::agent::GetAgentEncName``
    walk (``agent_methods.cpp:249-316``). It was never target-side work: that walk is Py4GW's C++
    over client state this port reads, so the three name readers and the four members that called
    them answer now.

**The one adaptation that changes behaviour, and it is the source's own cache.** ``Agent.py:40-50``
declares four per-frame caches of agent records (``_agent_cache``, ``_living_cache``,
``_item_cache``, ``_gadget_cache``) and ``enable()`` registers the callback that clears them once
per frame (``Agent.py:52-60``). This port has no frame loop, so there is no frame boundary to key
those caches to and no tick to invalidate them; a verbatim copy would pin a map-scoped
dereferenced record for the life of the process, which is the stale data the port's rules forbid
(``AGENTS.md``, ``PORTING_RULES.md``). So ``GetLivingAgentByID``, ``GetItemAgentByID`` and
``GetGadgetAgentByID`` keep the source's calls, order, short-circuits and returns **without** the
cache lookup and store: the members read when they are called.

Two consequences are visible on the surface, and both are reported rather than papered over:
``_invalidate_property_cache`` and ``enable`` raise, because clearing and registering are exactly
the two halves of the mechanism this port does not have; and the source's module-level
``Agent.enable()`` (``Agent.py:1649``) is not called at import.
"""

from __future__ import annotations

import ctypes
from typing import Any

from .client import ConnectedClient, require_client
from .context.acc_agent_context import (
    AccAgentContextStruct,
    AgentMovementStruct,
    AgentSummaryInfoStruct,
)
from .context.agent_array import (
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    AgentStruct,
)
from .context.gadget_context import GadgetContextStruct, GadgetInfoStruct
from .context.gw_array import GWArray, GWArrayValueView, GWArrayView
from .context.item_context import ItemContextStruct
from .context.world_context import (
    AgentNameInfoStruct,
    AttributeStruct,
    NPC_ModelStruct,
    PlayerStruct,
    WorldContextStruct,
)
from .internals.helpers import encoded_wstr_to_str


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise
    is what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"Agent.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


#: ``wchar_t`` on the x86 client: a UTF-16 code unit.
_WIDE_CHAR_SIZE = 2

#: The player-prefixed encoded form (``string_table._PLAYER_PREFIX``): a name the bytes themselves
#: carry, which is the one branch that needs no decoder at all.
_PLAYER_PREFIX = b"\xa9\x0b"

#: Names the client's decoder has answered, keyed by the encoded bytes -- the source's own cache shape
#: (``string_table._decode_cache`` is the same dict for the table route), which is what keeps a repeat
#: lookup free instead of another round trip.
_name_cache: dict[bytes, str] = {}

#: Decodes in flight: the encoded bytes to the slot holding them. A name whose bytes are in here has
#: been asked for and not answered yet, and the source's answer for that is ``""``.
_name_requests: dict[bytes, int] = {}

#: How many name decodes one caller may keep in flight. **The client answers a few at a time, not
#: many**: measured live, a single decode answers every time (~140 ms), while a sweep that placed 32 at
#: once (every slot the block has, ``DECODE_DEPTH``) answered **none** -- the requests went out and the
#: client never called back for them. Eight is the cap that keeps answers coming while still letting a
#: caller ask for a whole map in one pass: the rest answer ``""`` and are asked again on the next pass,
#: which is the source's own two-call contract.
MAX_NAME_DECODES_IN_FLIGHT = 8


#: Why the last ``GetNameByID`` answered what it answered. Diagnostics for the live probes, which read
#: it after a call: the branch a name takes is the whole difference between a queue and an answer.
_name_debug: list[str] = []


def _reset_name_state() -> None:
    """Drop the name cache and any in-flight decode, which belong to one connection.

    A decode slot is an offset into a block that belongs to a *connection*: after a reconnect, slot
    ``3`` is a different place. **Every slot still in flight is given back**, because the bridge refuses
    to free a block while a decode is outstanding (``Bridge.remove``) -- and a connection that cannot
    be removed is a client left patched, which is the failure this project has already paid for twice.
    A name that was asked for and never taken is exactly that case: the caller stopped calling, and the
    slot would hold the block open for good.
    """

    if _name_requests:
        try:
            from .client import current_client

            client = current_client()
            bridge = client.bridge if client is not None else None
        except (RuntimeError, AttributeError):
            bridge = None
        if bridge is not None:
            for slot in list(_name_requests.values()):
                try:
                    bridge.release_decode(slot)
                except (OSError, RuntimeError):
                    # The slot is not this module's to release any more; the bridge's own removal
                    # reports what is still outstanding.
                    pass

    _name_cache.clear()
    _name_requests.clear()
    _name_debug.clear()

#: The bound on one encoded agent name. The binding walks the client's own pointer to its
#: terminator and needs no bound, because that pointer is an address in its own process
#: (``agent_bindings.cpp:217-223``); this port reads the same string through a bounded
#: ``ReadProcessMemory``, where running off the end would read whatever follows the name.
#: 256 code units is longer than any encoded agent name the client carries.
MAX_ENC_NAME_CODE_UNITS = 256


def get_agent_enc_name(agent_id: int) -> list[int]:
    """``PyAgent.get_agent_enc_name`` (``agent_bindings.cpp:216-224``).

    The binding is one call and one copy: it asks its own ``GW::agent::GetAgentEncName(id)`` for
    the client's encoded name, walks that ``wchar_t*`` to its terminator, and copies
    ``(n + 1) * sizeof(wchar_t)`` bytes out — **the name and its terminator**, or an empty vector
    for a null pointer:

    ```cpp
    const wchar_t* enc = GW::agent::GetAgentEncName(id);
    if (!enc) return {};
    size_t n = 0; while (enc[n] != 0) ++n;
    const size_t bc = (n + 1) * sizeof(wchar_t);
    std::vector<uint8_t> out(bc);
    std::memcpy(out.data(), enc, bc);
    ```

    The stub states the same answer — *"Raw encoded name as UTF-16LE bytes (list[int]), including
    the terminator. Empty list when the agent has no encoded name"* (``stubs/PyAgent.pyi:98-101``)
    — and this returns exactly that, byte for byte, from the pointer the walk answers with.

    **The work is not the copy, it is the walk, and it is not target-side.** ``GetAgentEncName``
    is Py4GW's own C++ (``agent_methods.cpp:249-316``), not a client function: it reads the agent
    record, the world's agent-name array, the player array, an NPC record, the agent-summary
    gadget entry and the item array — all of which this port reads. The two functions below are
    that walk, member for member and short-circuit for short-circuit.
    """

    pointer = _get_agent_enc_name_by_id(agent_id)
    if not pointer:
        return []
    return _read_enc_name_bytes(pointer)


def _read_enc_name_bytes(pointer: int) -> list[int]:
    """Copy the client's encoded name at ``pointer`` (``agent_bindings.cpp:217-223``).

    One code unit at a time, because the terminator is the only length the source has and a
    chunked read would speculate past it; the copy stops at the terminator or at
    :data:`MAX_ENC_NAME_CODE_UNITS`, whichever comes first, and the bytes it read are the answer.
    """

    client = require_client()
    reader = client.reader

    raw = bytearray()
    for index in range(MAX_ENC_NAME_CODE_UNITS):
        unit = reader.read(pointer + index * _WIDE_CHAR_SIZE, _WIDE_CHAR_SIZE)
        raw.extend(unit)
        if int.from_bytes(unit, "little") == 0:
            break
    return list(raw)


def _world_context(client: ConnectedClient) -> WorldContextStruct | None:
    """Return the world context, or ``None`` while it is unavailable."""

    try:
        return client.read_world_context()
    except (OSError, RuntimeError):
        return None


def _get_agent_by_id(client: ConnectedClient, agent_id: int) -> AgentStruct | None:
    """``GW::agent::GetAgentByID`` (``agent_methods.cpp:73-88``).

    ```cpp
    Agent* GetAgentByID(uint32_t agent_id) {
        auto* agents = agent_id ? GetAgentArray() : nullptr;              // g_agent_array_addr + valid()
        Agent* agent = agents && agent_id < agents->size() ? agents->at(agent_id) : nullptr;
        if (!agent) return nullptr;
        const auto* agent_context = Context::GetAgentContext();
        if (!(agent_context && agent_context->agent_movement.size() > agent->agent_id &&
              agent_context->agent_movement[agent->agent_id])) return nullptr;
        return agent;
    }
    ```

    The client's agent array is **a table indexed by agent id**, and native reads it as one: the
    index, then the movement-record check that makes a stale slot null. This is the lookup
    ``GetAgentEncName`` uses, so it is the one the name members use here.

    Reforged's *Python* ``Agent.GetAgentByID`` is a different member with a different cost: it asks
    the array view, whose answer comes from the per-id cache ``_build_allegiance_cache`` fills — a
    traversal of every slot (and, since the point-of-use refresh, a context read) before it can
    answer one id. Native's binding does not go through it, and neither does this.
    """

    if not agent_id:
        return None

    facade = client.agent_array
    address = facade.get_ptr() or facade.initialize()
    if not address:
        return None

    raw_array = client.reader.read(address, ctypes.sizeof(GWArray))
    instance = GWArray.from_buffer_copy(raw_array)
    view = GWArrayView(client.reader, instance, AgentStruct)
    if not view.valid() or agent_id >= view.size():
        return None

    agent = view.get(agent_id)
    if not isinstance(agent, AgentStruct):
        return None

    # ``agent_context->agent_movement.size() > id && agent_context->agent_movement[id]``: the
    # movement array is indexed, not walked. Reading every entry to answer one id would cost a read
    # per slot (975 in the district this was measured in) where native's check costs one.
    agent_context = client.read_acc_agent_context()
    if agent_context is None:
        return None
    agent_id_from_record = int(agent.agent_id)
    movement_view = GWArrayView(
        client.reader, agent_context.agent_movement_array, AgentMovementStruct
    )
    if not movement_view.valid() or agent_id_from_record >= movement_view.size():
        return None
    if movement_view.get(agent_id_from_record) is None:
        return None
    return agent


def _get_agent_enc_name_by_id(agent_id: int) -> int:
    """``GW::agent::GetAgentEncName(uint32_t)`` (``agent_methods.cpp:249-261``).

    The agent record first — through :meth:`Agent.GetAgentByID`, the ported
    ``GW::agent::GetAgentByID`` (``agent_methods.cpp:73-88``) — the indexed table read ported below —
    and then the world's agent-name array, which is where the client keeps the name of an id whose
    live record is gone:

    ```cpp
    const auto* agent = GetAgentByID(agent_id);
    if (agent) return GetAgentEncName(agent);
    auto* world = Context::GetWorldContext();
    auto* agent_infos = world && world->agent_infos.valid() ? &world->agent_infos : nullptr;
    if (!(agent_infos && agent_id < agent_infos->size())) return nullptr;
    return agent_infos->at(agent_id).name_enc;
    ```
    """

    client = require_client()
    agent = _get_agent_by_id(client, agent_id)
    if agent is not None:
        return _get_agent_enc_name_by_agent(agent)

    world = _world_context(client)
    if world is None:
        return 0
    view = GWArrayValueView(
        client.reader, world.agent_name_info_array, AgentNameInfoStruct
    )
    if not view.valid() or agent_id < 0 or agent_id >= view.size():
        return 0
    record = view.get(agent_id)
    if not isinstance(record, AgentNameInfoStruct):
        return 0
    return int(record.name_enc_ptr)


def _get_agent_enc_name_by_agent(agent: AgentStruct) -> int:
    """``GW::agent::GetAgentEncName(const Agent*)`` (``agent_methods.cpp:263-316``).

    Four branches in the source's own order — a living agent (a player by login number, then the
    world's agent-name array, then the NPC record its ``player_number`` names), a gadget (the
    agent-summary entry's own name, then the gadget context's ``gadget_info``), and an item — and
    a null answer for anything else. Every array index is the source's: ``at(agent_id)``,
    ``at(login_number)``, ``gadget_info[gadget_id]``, ``GetItemById(item_id)``, each behind the
    same ``< size()`` bound the source uses.
    """

    client = require_client()

    if agent.is_living_type:
        living = agent.GetAsAgentLiving()
        if living is None:
            return 0

        login_number = int(living.login_number)
        if login_number:
            world = _world_context(client)
            if world is None:
                return 0
            players = GWArrayValueView(
                client.reader, world.players_array, PlayerStruct
            )
            if not players.valid() or login_number >= players.size():
                return 0
            player = players.get(login_number)
            if not isinstance(player, PlayerStruct):
                return 0
            return int(player.name_enc_ptr)

        world = _world_context(client)
        if world is None:
            return 0
        agent_id = int(agent.agent_id)
        agent_infos = GWArrayValueView(
            client.reader, world.agent_name_info_array, AgentNameInfoStruct
        )
        if not agent_infos.valid() or agent_id >= agent_infos.size():
            return 0
        record = agent_infos.get(agent_id)
        if not isinstance(record, AgentNameInfoStruct):
            return 0
        if int(record.name_enc_ptr):
            return int(record.name_enc_ptr)

        npc = _get_npc_by_id(client, int(living.player_number))
        return int(npc.name_enc_ptr) if npc is not None else 0

    if agent.is_gadget_type:
        agent_context = client.read_acc_agent_context()
        gadget_context = client.read_gadget_context()
        if agent_context is None or gadget_context is None:
            return 0

        agent_id = int(agent.agent_id)
        summary = GWArrayValueView(
            client.reader, agent_context.agent_summary_info, AgentSummaryInfoStruct
        )
        if not summary.valid() or agent_id >= summary.size():
            return 0
        record = summary.get(agent_id)
        if not isinstance(record, AgentSummaryInfoStruct):
            return 0
        gadget_ids = record.extra_info_sub
        if gadget_ids is None:
            return 0
        if int(gadget_ids.gadget_name_enc):
            return int(gadget_ids.gadget_name_enc)

        gadget_id = int(gadget_ids.gadget_id)
        infos = GWArrayValueView(
            client.reader, gadget_context.gadget_info, GadgetInfoStruct
        )
        if gadget_id >= infos.size():
            return 0
        info = infos.get(gadget_id)
        return int(info.name_enc) if isinstance(info, GadgetInfoStruct) else 0

    if agent.is_item_type:
        item_agent = agent.GetAsAgentItem()
        if item_agent is None:
            return 0
        item_context = client.read_item_context()
        if item_context is None:
            return 0
        item = item_context.GetItemById(int(item_agent.item_id))
        return int(item.name_enc) if item is not None else 0

    return 0


def _get_npc_by_id(client: ConnectedClient, npc_id: int) -> NPC_ModelStruct | None:
    """``GW::agent::GetNPCByID`` (``agent_methods.cpp:126-129``).

    ``Context::GetNPCArray()`` is ``world->npcs`` when its header is valid, and ``at(npc_id)``
    is the indexed read behind the same ``npc_id < size()`` bound.
    """

    world = _world_context(client)
    if world is None:
        return None
    view = GWArrayValueView(client.reader, world.npc_models_array, NPC_ModelStruct)
    if not view.valid() or npc_id < 0 or npc_id >= view.size():
        return None
    record = view.get(npc_id)
    return record if isinstance(record, NPC_ModelStruct) else None


class Agent:
    """The Reforged ``Agent`` namespace class (``Agent.py:13-1646``): 148 static members.

    Every member takes an ``agent_id`` and reads. The class holds the two constants the source
    declares (``Agent.py:14-18``) and nothing else: the four per-frame caches the source declares
    at ``Agent.py:40-43`` are not kept here, for the reason the module docstring gives.
    """

    #: ``Agent.py:14``. Filled in by ``IsMartial``/``IsMelee`` on first use in the source; both
    #: members are blocked here (they need ``Skill.GetID``), so the constant stays at its
    #: declared value.
    ILLUSIONARY_WEAPONRY_ID = 0

    #: ``Agent.py:18``. Agent HP is normalized 0.0-1.0 for most non-party entities; the smallest
    #: expected enemy health pool is used so ~1 HP residual noise still counts as dead across the
    #: common 400-1000 HP range.
    DEAD_HEALTH_EPSILON = 1.0 / 400.0

    @staticmethod
    def _enc_name_bytes_to_wstr(enc_bytes: list[int]) -> str:
        """Convert raw ``GetAgentEncName()`` byte values into a UTF-16LE string (``Agent.py:20-29``).

        Pure arithmetic over the bytes it is handed, so it needs nothing the port does not have.
        """

        if not enc_bytes:
            return ""

        raw = bytes(enc_bytes)
        text = raw[: len(raw) & ~1].decode("utf-16-le", "ignore")
        null_index = text.find("\x00")
        return text[:null_index] if null_index >= 0 else text

    @staticmethod
    def IsValid(agent_id: int) -> bool:
        """Check if the agent is valid (``Agent.py:31-38``)."""

        return Agent.GetAgentByID(agent_id) is not None

    @staticmethod
    def _invalidate_property_cache() -> None:
        """Clear the four per-frame agent caches (``Agent.py:45-50``).

        Blocked: it clears ``_agent_cache``/``_living_cache``/``_item_cache``/``_gadget_cache``,
        which this port does not keep, and the only thing that ever called it is the frame tick
        ``enable()`` registers.
        """

        raise _unported(
            "_invalidate_property_cache",
            "the four per-frame agent caches it clears (Agent.py:40-50), which this port does not "
            "keep: their only invalidation is the once-per-frame callback enable() registers, and "
            "there is no frame loop here (AGENTS.md, PORTING_RULES.md)",
        )

    @staticmethod
    def enable() -> None:
        """Register the per-frame cache invalidation (``Agent.py:52-60``).

        Blocked: it calls ``PyCallback.PyCallback.Register("Agent.InvalidatePropertyCache",
        Phase.PreUpdate, ...)``, a per-frame callback registration, and this project has no frame
        loop to drive it. The source also calls this at module level (``Agent.py:1649``), which
        this port does not reproduce.
        """

        raise _unported(
            "enable",
            "the per-frame callback registration PyCallback.PyCallback.Register(..., "
            "Phase.PreUpdate, ...) (Agent.py:52-60; stubs/PyCallback.pyi:40), which this project "
            "has no frame loop for",
        )

    @staticmethod
    def GetAgentByID(agent_id: int) -> AgentStruct | None:
        """Retrieve an agent by its ID, or ``None`` (``Agent.py:62-81``).

        The source's own chain, as written: ``from .AgentArray import AgentArray`` then
        ``return AgentArray.GetAgentByID(agent_id)``. That member reaches the agent-array *context*
        (``AgentContext.py:1477-1497``) and answers ``None`` for any id the context does not hold —
        including ``0``.

        The four lines the source leaves *after* its own ``return`` (``Agent.py:74-81``) are
        unreachable there and are not reproduced; the cache they maintain is the adaptation the
        module docstring describes.
        """

        from .agent_array import AgentArray

        return AgentArray.GetAgentByID(int(agent_id))

    @staticmethod
    def GetLivingAgentByID(agent_id: int) -> AgentLivingStruct | None:
        """Retrieve a living agent by its ID, or ``None`` (``Agent.py:84-101``).

        The source's calls, order, short-circuits and returns, without the per-frame cache lookup
        and store (``Agent.py:92-93``, ``99-100``) — see the module docstring.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return None
        return agent.GetAsAgentLiving()

    @staticmethod
    def GetItemAgentByID(agent_id: int) -> AgentItemStruct | None:
        """Retrieve an item agent by its ID, or ``None`` (``Agent.py:103-120``).

        Without the per-frame cache (``Agent.py:111-112``, ``118-119``), as above.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return None
        return agent.GetAsAgentItem()

    @staticmethod
    def GetGadgetAgentByID(agent_id: int) -> AgentGadgetStruct | None:
        """Retrieve a gadget agent by its ID, or ``None`` (``Agent.py:122-139``).

        Without the per-frame cache (``Agent.py:130-131``, ``137-138``), as above.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return None
        return agent.GetAsAgentGadget()

    @staticmethod
    def GetNameByID(agent_id: int) -> str:
        """Get the decoded display name of an agent by its ID (``Agent.py:141-147``).

        The source's two steps over the binding: ``PyAgent.get_agent_enc_name`` (ported above as
        :func:`get_agent_enc_name`) and a decode.

        **The decode is Native's, not Reforged's Python one, and the reason is measured.** Reforged
        hands the bytes to ``string_table.decode`` -- a table it keeps in its own process, read out of
        GW.dat, which costs nothing when the reader is *inside* the client. This controller is outside
        it, where that table is a dat record per file: live, **one string file costs ~2.1 s** inside the
        client (open the record ~1.1 s, read and decompress 91 KB ~0.9 s), so the first name in a slot
        paid seconds, and a map-wide name search paid ~8 s. Native never pays it, because
        ``AsyncGetAgentName`` (``agent_methods.cpp:318-325``) hands the encoded string to the
        **client's own decoder** and takes the text from its callback -- and that route is live here at
        **~140 ms per name with no dat read at all**. Measured side by side on the same client
        (``live_reports/name_scheme8.txt``): ``Random Arenas``, ``Great Temple of Balthazar``,
        ``Vekk``, ``Dunkoro``, ``Zaishen Chest`` and the player's own name all agree with the table
        decode, and the client additionally resolves ``Pet - My Pet`` where the table decode stops at
        ``Pet - %str1%``.

        **The source's two-call shape is kept.** The client answers asynchronously, so the call that
        starts a decode answers ``""`` and the text arrives on a later call -- which is exactly what
        Reforged's ``decode`` does while its worker runs, and what Native's own callers get, because
        ``AsyncGetAgentName`` fills its ``std::wstring&`` from the callback. The completion is taken by
        :func:`_on_string_decoded`, registered by the connection like the dialog's and the chat's.

        A player-prefixed name is the one branch that never reaches the client: ``string_table.decode``
        renders that inline form from the bytes themselves, and this port keeps that shortcut.
        """

        enc_bytes = get_agent_enc_name(agent_id)
        if not enc_bytes:
            _name_debug.append(f"{agent_id}: no encoded name")
            return ""
        raw = bytes(enc_bytes)

        if raw[0:2] == _PLAYER_PREFIX:
            from .internals.string_table import decode as decode_raw

            _name_debug.append(f"{agent_id}: player form, decoded from the bytes")
            return decode_raw(raw)

        cached = _name_cache.get(raw)
        if cached is not None:
            _name_debug.append(f"{agent_id}: cache hit")
            return cached

        pending_slot = _name_requests.get(raw)
        if pending_slot is not None:
            # The decode this name asked for is in flight, or has just finished. **The slot's own state
            # is what says so**, not the ``STRING_DECODED`` event: measured live, a decode taken on that
            # event reads empty while the same slot read by its state answers the text -- and the
            # dialog's strings take that event, so a name must not compete with them for it. This is the
            # source's two-call shape: the call that asks answers ``""``, the next one answers the text.
            from .game_thread.shared_block import DecodeState
            from .ui.async_decode import decode_state, decoded_text

            state = decode_state(pending_slot)
            _name_debug.append(f"{agent_id}: slot {pending_slot} is {state.name}")
            if state not in (DecodeState.DONE, DecodeState.FAILED):
                return ""
            del _name_requests[raw]
            if state is DecodeState.DONE:
                text, truncated = decoded_text(pending_slot)
                _name_debug.append(f"{agent_id}: took {text!r} (truncated={truncated})")
                if text:
                    _name_cache[raw] = text
                    return text
            return ""

        if len(_name_requests) >= MAX_NAME_DECODES_IN_FLIGHT:
            _name_debug.append(f"{agent_id}: {len(_name_requests)} already in flight")
            return ""

        from .ui.async_decode import async_decode_str, begin_string_decode

        try:
            slot = begin_string_decode(raw)
        except RuntimeError as error:
            # Every decode slot is in flight (``bridge.begin_decode``'s cap, the port's own equivalent
            # of the source's pending-label limit). Asking for a name that cannot be queued answers the
            # way the source answers an unfinished decode, so a caller that sweeps a whole map keeps
            # polling instead of failing: the slots free up as the client answers the ones in flight.
            _name_debug.append(f"{agent_id}: no slot ({error})")
            return ""
        if not async_decode_str(raw, slot):
            # ``SafeAsyncDecodeStr`` answered false: nothing was queued, and the slot is back.
            _name_debug.append(f"{agent_id}: the call did not start")
            return ""
        _name_requests[raw] = slot
        _name_debug.append(f"{agent_id}: asked in slot {slot}")
        return ""

    #: ``Agent.py:149``: the source's alias for :meth:`GetNameByID`, declared in the class body
    #: right after it, so both names are the same ``staticmethod``.
    RequestName = GetNameByID

    @staticmethod
    def IsNameReady(agent_id: int) -> bool:
        """Whether the agent's name has decoded yet (``Agent.py:151-153``)."""

        return Agent.GetNameByID(agent_id) != ""

    @staticmethod
    def GetEncNameByID(agent_id: int) -> list[int]:
        """Get the encoded name of an agent by its ID (``Agent.py:155-159``)."""

        enc_bytes = get_agent_enc_name(agent_id)
        return enc_bytes

    @staticmethod
    def GetEncNameStrByID(agent_id: int, literal: bool = False) -> str:
        """Get an agent's encoded name as a readable debug string (``Agent.py:161-179``)."""

        enc_bytes = get_agent_enc_name(agent_id)
        if not enc_bytes:
            return ""
        enc_wstr = Agent._enc_name_bytes_to_wstr(enc_bytes)
        encoded = encoded_wstr_to_str(enc_wstr) or ""
        if literal:
            return encoded
        return encoded.replace("\\", "\\\\")

    @staticmethod
    def GetAgentIDByName(name: str) -> int:
        """Retrieve the first agent whose name matches, or ``0`` (``Agent.py:181-198``).

        Blocked once, and not adapted any more: the walk is ``AgentArray.GetAgentArray()``
        (``AgentArray.py:15-29``), which this port now has, and the comparison is
        ``Agent.GetNameByID``'s — whose binding call is the member that refuses.
        """

        from .agent_array import AgentArray

        try:
            agent_ids = AgentArray.GetAgentArray()
        except (OSError, RuntimeError, ValueError):
            return 0

        for agent_id in agent_ids:
            agent_name = Agent.GetNameByID(agent_id)
            if name.lower() in agent_name.lower():
                if Agent.IsValid(agent_id):
                    return agent_id
        return 0

    @staticmethod
    def GetAgentIDByEncString(enc_string: str) -> int:
        """Retrieve the first agent whose encoded name matches, or ``0`` (``Agent.py:200-220``).

        The same walk as :meth:`GetAgentIDByName`; the raise comes from
        ``Agent.GetEncNameStrByID``.
        """

        if not enc_string:
            return 0

        from .agent_array import AgentArray

        try:
            agent_ids = AgentArray.GetAgentArray()
        except (OSError, RuntimeError, ValueError):
            return 0

        for agent_id in agent_ids:
            if not Agent.IsValid(agent_id):
                continue
            if Agent.GetEncNameStrByID(agent_id, literal=True) == enc_string:
                return agent_id
        return 0

    @staticmethod
    def GetModelIDByEncString(enc_string: str, log: bool = False) -> int:
        """Retrieve a model id by encoded name, or ``0`` (``Agent.py:222-240``).

        The body is the source's, ``log`` prints included; the raise comes from
        ``Agent.GetAgentIDByEncString``.
        """

        agent_id = Agent.GetAgentIDByEncString(enc_string)
        if log:
            print(f"Debug: GetModelIDByEncString('{enc_string}') found agent_id={agent_id}")
        if agent_id == 0:
            return 0
        model_id = Agent.GetModelID(agent_id)
        if log:
            print(f"Debug: GetModelIDByEncString('{enc_string}') found model_id={model_id}")
        return model_id

    @staticmethod
    def GetAttributes(agent_id: int) -> list[AttributeStruct]:
        """Retrieve an agent's attributes, or ``[]`` (``Agent.py:242-250``).

        Adapted at the context: the source asks ``GWContext.World.GetContext()`` (``Context.py``);
        this port reads the same world context through ``ConnectedClient.read_world_context``,
        whose ``get_attributes_by_agent_id`` is the identical read over the ported
        ``attributes`` array.
        """

        client = require_client()
        try:
            world_ctx: WorldContextStruct | None = client.read_world_context()
        except (OSError, RuntimeError):
            return []
        if world_ctx is None:
            return []

        attributes = world_ctx.get_attributes_by_agent_id(agent_id)
        return attributes

    @staticmethod
    def GetAttributesDict(agent_id: int) -> dict[int, int]:
        """Retrieve an agent's attributes as ``{attribute_id: level}`` (``Agent.py:252-265``)."""

        attributes_raw: list[AttributeStruct] = Agent.GetAttributes(agent_id)
        attributes = {}

        for attr in attributes_raw:
            attr_id = int(attr.attribute_id)
            attr_level = attr.level_base
            if attr_level > 0:
                attributes[attr_id] = attr_level

        return attributes

    @staticmethod
    def GetInstanceFrames(agent_id: int) -> int:
        """Retrieve the instance timer of an agent in frames (``Agent.py:267-278``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0
        return agent.timer

    @staticmethod
    def GetInstanceUptime(agent_id: int) -> int:
        """Retrieve the instance timer of an agent in milliseconds (``Agent.py:280-294``).

        The source's body is four lines — the record, ``UIManager.GetFPSLimit()``, the ``max``
        against 30 that keeps the division safe, and the millisecond conversion. **It calls
        ``UIManager.GetFPSLimit`` here, which is the source's own route**: that member landed with
        the class on 2026-09-27 (``py4gw/ui_manager.py``) and returns what
        ``PyUIManager.UIManager.get_frame_limit()`` returns, i.e. native's ``GW::ui::GetFrameLimit``
        (``ui_methods.cpp:1833-1858``). Before the class had a home this member reached that function
        one layer lower (``py4gw.ui.preferences.get_frame_limit``); the value is the same one the
        source divides by, and the route is now the source's.
        """

        from .ui_manager import UIManager

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0
        fps_limit = UIManager.GetFPSLimit()
        fps_limit = max(fps_limit, 30)  # Prevent division by zero
        return int(agent.timer / fps_limit * 1000)

    @staticmethod
    def GetAgentEffects(agent_id: int) -> int:
        """Retrieve the effects of an agent (``Agent.py:296-308``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0

        return living.effects

    @staticmethod
    def GetTypeMap(agent_id: int) -> int:
        """Retrieve the type map of an agent (``Agent.py:310-321``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.type_map

    @staticmethod
    def GetModelState(agent_id: int) -> int:
        """Retrieve the model state of an agent (``Agent.py:323-334``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.model_state

    @staticmethod
    def GetModelID(agent_id: int) -> int:
        """Retrieve the model of an agent (``Agent.py:336-343``).

        The source also carries ``@frame_cache(category="Agent", source_lib="GetModelID")``
        (``Agent.py:337``); the decorator is dropped, because its only invalidation is Reforged's
        per-frame tick and this port has no frame loop (``PORTING_RULES.md``). The member reads
        when it is called.
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.player_number

    @staticmethod
    def IsLiving(agent_id: int) -> bool:
        """Check if the agent is living (``Agent.py:345-351``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return False
        return agent.is_living_type

    @staticmethod
    def IsItem(agent_id: int) -> bool:
        """Check if the agent is an item (``Agent.py:353-359``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return False
        return agent.is_item_type

    @staticmethod
    def IsGadget(agent_id: int) -> bool:
        """Check if the agent is a gadget (``Agent.py:361-367``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return False
        return agent.is_gadget_type

    @staticmethod
    def GetPlayerNumber(agent_id: int) -> int:
        """Retrieve the player number of an agent (``Agent.py:369-375``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.player_number

    @staticmethod
    def GetLoginNumber(agent_id: int) -> int:
        """Retrieve the login number of an agent (``Agent.py:377-383``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.login_number

    @staticmethod
    def IsSpirit(agent_id: int) -> bool:
        """Check if the agent is a spirit (``Agent.py:385-393``)."""

        from .enums_src.game_data_enums import Allegiance

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        allegiance = Allegiance(living.allegiance)
        return allegiance == Allegiance.SpiritPet and Agent.IsSpawned(agent_id)

    @staticmethod
    def IsPet(agent_id: int) -> bool:
        """Check if the agent is a pet (``Agent.py:395-403``)."""

        from .enums_src.game_data_enums import Allegiance

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        allegiance = Allegiance(living.allegiance)
        return allegiance == Allegiance.SpiritPet and not Agent.IsSpawned(agent_id)

    @staticmethod
    def IsMinion(agent_id: int) -> bool:
        """Check if the agent is a minion (``Agent.py:405-413``)."""

        from .enums_src.game_data_enums import Allegiance

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        allegiance = Allegiance(living.allegiance)
        return allegiance == Allegiance.Minion

    @staticmethod
    def GetOwnerID(agent_id: int) -> int:
        """Retrieve the owner ID of an agent (``Agent.py:415-421``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.owner

    @staticmethod
    def GetXY(agent_id: int) -> tuple[float, float]:
        """Retrieve the X and Y coordinates of an agent (``Agent.py:423-435``).

        The source also carries ``@frame_cache(category="Agent", source_lib="GetXY")``
        (``Agent.py:424``); the decorator is dropped (no frame loop here), so the member reads
        when it is called.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0
        pos = agent.pos
        return pos.x, pos.y

    @staticmethod
    def GetXYZ(agent_id: int) -> tuple[float, float, float]:
        """Retrieve the X, Y and Z coordinates of an agent (``Agent.py:437-449``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0, 0.0
        pos = agent.pos
        z = agent.z
        return pos.x, pos.y, z

    @staticmethod
    def GetZPlane(agent_id: int) -> int:
        """Retrieve the Z plane of an agent (``Agent.py:451-462``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0
        pos = agent.pos
        return pos.zplane

    @staticmethod
    def GetNameTagXYZ(agent_id: int) -> tuple[float, float, float]:
        """Retrieve the name tag X, Y and Z of an agent (``Agent.py:464-474``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0, 0.0
        return agent.name_tag_x, agent.name_tag_y, agent.name_tag_z

    @staticmethod
    def GetModelScale1(agent_id: int) -> tuple[float, float]:
        """Retrieve the model scale of an agent (``Agent.py:476-487``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0

        return agent.width1, agent.height1

    @staticmethod
    def GetModelScale2(agent_id: int) -> tuple[float, float]:
        """Retrieve the model scale of an agent (``Agent.py:489-500``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0

        return agent.width2, agent.height2

    @staticmethod
    def GetModelScale3(agent_id: int) -> tuple[float, float]:
        """Retrieve the model scale of an agent (``Agent.py:502-513``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0

        return agent.width3, agent.height3

    @staticmethod
    def GetNameProperties(agent_id: int) -> int:
        """Retrieve the name properties of an agent (``Agent.py:515-526``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0

        return agent.name_properties

    @staticmethod
    def GetVisualEffects(agent_id: int) -> int:
        """Retrieve the visual effects of an agent (``Agent.py:528-539``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0

        return agent.visual_effects

    @staticmethod
    def GetTerrainNormalXYZ(agent_id: int) -> tuple[float, float, float]:
        """Retrieve the terrain normal X, Y and Z of an agent (``Agent.py:541-552``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0, 0.0

        return agent.terrain_normal.x, agent.terrain_normal.y, agent.terrain_normal.z

    @staticmethod
    def GetGround(agent_id: int) -> float:
        """Retrieve the ground of an agent (``Agent.py:554-565``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0

        return agent.ground

    @staticmethod
    def GetAnimationCode(agent_id: int) -> int:
        """Retrieve the animation code of an agent (``Agent.py:567-578``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.animation_code

    @staticmethod
    def GetWeaponItemType(agent_id: int) -> int:
        """Retrieve the weapon item type of an agent (``Agent.py:580-591``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.weapon_item_type

    @staticmethod
    def GetOffhandItemType(agent_id: int) -> int:
        """Retrieve the offhand item type of an agent (``Agent.py:593-604``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.offhand_item_type

    @staticmethod
    def GetAnimationType(agent_id: int) -> float:
        """Retrieve the animation type of an agent (``Agent.py:606-617``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.animation_type

    @staticmethod
    def GetWeaponAttackSpeed(agent_id: int) -> float:
        """Retrieve the weapon attack speed of an agent (``Agent.py:619-630``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0.0

        return living_agent.weapon_attack_speed

    @staticmethod
    def GetAttackSpeedModifier(agent_id: int) -> float:
        """Retrieve the attack speed modifier of an agent (``Agent.py:632-643``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0.0

        return living_agent.attack_speed_modifier

    @staticmethod
    def GetAgentModelType(agent_id: int) -> int:
        """Retrieve the agent model type of an agent (``Agent.py:645-656``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.agent_model_type

    @staticmethod
    def GetTransmogNPCID(agent_id: int) -> int:
        """Retrieve the transmog NPC ID of an agent (``Agent.py:658-669``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.transmog_npc_id

    @staticmethod
    def GetGuildID(agent_id: int) -> int:
        """Retrieve the guild ID of an agent (``Agent.py:671-685``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        tags = living_agent.tags
        if tags is None:
            return 0
        return tags.guild_id

    @staticmethod
    def GetTeamID(agent_id: int) -> int:
        """Retrieve the team ID of an agent (``Agent.py:687-698``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.team_id

    @staticmethod
    def GetAnimationSpeed(agent_id: int) -> float:
        """Retrieve the animation speed of an agent (``Agent.py:700-711``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0.0

        return living_agent.animation_speed

    @staticmethod
    def GetAnimationID(agent_id: int) -> int:
        """Retrieve the animation ID of an agent (``Agent.py:713-724``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.animation_id

    @staticmethod
    def GetRotationAngle(agent_id: int) -> float:
        """Retrieve the rotation angle of an agent (``Agent.py:726-736``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0
        return agent.rotation_angle

    @staticmethod
    def GetRotationCos(agent_id: int) -> float:
        """Retrieve the cosine of the rotation angle of an agent (``Agent.py:738-748``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0
        return agent.rotation_cos

    @staticmethod
    def GetRotationSin(agent_id: int) -> float:
        """Retrieve the sine of the rotation angle of an agent (``Agent.py:751-761``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0
        return agent.rotation_sin

    @staticmethod
    def GetVelocityXY(agent_id: int) -> tuple[float, float]:
        """Retrieve the X and Y velocity of an agent (``Agent.py:763-775``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0
        velocity = agent.velocity

        return velocity.x, velocity.y

    @staticmethod
    def GetProfessions(agent_id: int) -> tuple[int, int]:
        """Retrieve the primary and secondary professions (``Agent.py:777-788``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, 0

        return living.primary, living.secondary

    @staticmethod
    def GetProfessionNames(agent_id: int) -> tuple[str, str]:
        """Retrieve the names of the primary and secondary professions (``Agent.py:790-807``)."""

        from .enums_src.game_data_enums import Profession, Profession_Names

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return "", ""

        profession = Profession(living.primary)
        prof_name = Profession_Names[profession]
        secondary_profession = Profession(living.secondary)
        secondary_prof_name = Profession_Names[secondary_profession]

        return prof_name if prof_name is not None else "", secondary_prof_name if secondary_prof_name is not None else ""

    @staticmethod
    def GetProfessionShortNames(agent_id: int) -> tuple[str, str]:
        """Retrieve the short names of the primary and secondary professions (``Agent.py:809-826``)."""

        from .enums_src.game_data_enums import ProfessionShort, ProfessionShort_Names

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return "", ""

        profession = ProfessionShort(living.primary)
        prof_name = ProfessionShort_Names[profession]
        secondary_profession = ProfessionShort(living.secondary)
        secondary_prof_name = ProfessionShort_Names[secondary_profession]

        return prof_name, secondary_prof_name

    @staticmethod
    def GetProfessionIDs(agent_id: int) -> tuple[int, int]:
        """Retrieve the ids of the primary and secondary professions (``Agent.py:828-838``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, 0
        return living.primary, living.secondary

    @staticmethod
    def GetLevel(agent_id: int) -> int:
        """Retrieve the level of an agent (``Agent.py:840-850``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.level

    @staticmethod
    def GetEnergy(agent_id: int) -> float:
        """Retrieve the energy of the agent (``Agent.py:852-862``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.energy

    @staticmethod
    def GetMaxEnergy(agent_id: int) -> int:
        """Retrieve the maximum energy of the agent (``Agent.py:864-874``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.max_energy

    @staticmethod
    def GetEnergyRegen(agent_id: int) -> float:
        """Retrieve the energy regeneration of the agent (``Agent.py:876-886``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.energy_regen

    @staticmethod
    def GetEnergyPips(agent_id: int) -> int:
        """Retrieve the energy pips of the agent (``Agent.py:888-899``).

        The conversion is ``Utils.calculate_energy_pips``
        (``py4gwcorelib_src/Utils.py:749-753``), ported as ``Utils``'s own arithmetic
        (``py4gw/py4gwcorelib_src/utils.py``).
        """

        from .py4gwcorelib_src.utils import Utils

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return Utils.calculate_energy_pips(living.max_energy, living.energy_regen)

    @staticmethod
    def GetHealth(agent_id: int) -> float:
        """Retrieve the health of the agent (``Agent.py:901-911``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.hp

    @staticmethod
    def GetMaxHealth(agent_id: int) -> int:
        """Retrieve the maximum health of the agent (``Agent.py:913-923``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.max_hp

    @staticmethod
    def GetHealthRegen(agent_id: int) -> float:
        """Retrieve the health regeneration of the agent (``Agent.py:925-935``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.hp_pips

    @staticmethod
    def GetHealthPips(agent_id: int) -> int:
        """Retrieve the health pips of the agent (``Agent.py:937-950``).

        The conversion is ``Utils.calculate_health_pips``
        (``py4gwcorelib_src/Utils.py:755-759``), ported as ``Utils``'s own arithmetic
        (``py4gw/py4gwcorelib_src/utils.py``).
        """

        from .py4gwcorelib_src.utils import Utils

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0

        return Utils.calculate_health_pips(living.max_hp, living.hp_pips)

    @staticmethod
    def CanAct(agent_id: int) -> bool:
        """Always ``True`` (``Agent.py:952-955``).

        The source returns the literal: the combat-event queue behind it is commented out
        (``Agent.py:955``), so there is nothing to port but the constant.
        """

        return True

    @staticmethod
    def IsMoving(agent_id: int) -> bool:
        """Check if the agent is moving (``Agent.py:957-962``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_moving

    @staticmethod
    def IsKnockedDown(agent_id: int) -> bool:
        """Check if the agent is knocked down (``Agent.py:964-970``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_knocked_down

    @staticmethod
    def GetKnockDownTimeRemaining(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:972-975``).

        The source returns the literal; the combat-event helper behind it is commented out.
        """

        return 0

    @staticmethod
    def IsBleeding(agent_id: int) -> bool:
        """Check if the agent is bleeding (``Agent.py:978-983``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_bleeding

    @staticmethod
    def IsCrippled(agent_id: int) -> bool:
        """Check if the agent is crippled (``Agent.py:985-990``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_crippled

    @staticmethod
    def IsDeepWounded(agent_id: int) -> bool:
        """Check if the agent is deep-wounded (``Agent.py:992-997``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_deep_wounded

    @staticmethod
    def IsPoisoned(agent_id: int) -> bool:
        """Check if the agent is poisoned (``Agent.py:999-1004``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_poisoned

    @staticmethod
    def IsConditioned(agent_id: int) -> bool:
        """Check if the agent is conditioned (``Agent.py:1006-1011``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_conditioned

    @staticmethod
    def IsEnchanted(agent_id: int) -> bool:
        """Check if the agent is enchanted (``Agent.py:1013-1018``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_enchanted

    @staticmethod
    def IsHexed(agent_id: int) -> bool:
        """Check if the agent is hexed (``Agent.py:1020-1025``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_hexed

    @staticmethod
    def IsDegenHexed(agent_id: int) -> bool:
        """Check if the agent is degeneration-hexed (``Agent.py:1027-1032``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_degen_hexed

    @staticmethod
    def IsDead(agent_id: int) -> bool:
        """Check if the agent is dead (``Agent.py:1034-1051``).

        The five terms are the source's, in its order, including the residual-health epsilon
        (``Agent.DEAD_HEALTH_EPSILON``).
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        health = float(living.hp)
        is_dead = bool(living.is_dead)
        dead_by_type_map = bool(living.is_dead_by_type_map)
        is_exploitable_corpse = bool(living.is_exploitable)
        is_used_corpse = bool(living.is_used_corpse)
        return (
            is_dead
            or dead_by_type_map
            or is_exploitable_corpse
            or is_used_corpse
            or health <= Agent.DEAD_HEALTH_EPSILON
        )

    @staticmethod
    def IsExploitable(agent_id: int) -> bool:
        """Check if the agent is exploitable (``Agent.py:1053-1058``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_exploitable

    @staticmethod
    def IsExploitableCorpse(agent_id: int) -> bool:
        """Whether the agent is a dead, unexploited, fleshy corpse (``Agent.py:1060-1063``)."""

        return Agent.IsExploitable(agent_id) and Agent.IsFleshy(agent_id)

    @staticmethod
    def IsUsedCorpse(agent_id: int) -> bool:
        """Check if the agent's corpse has been used (``Agent.py:1065-1070``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_used_corpse

    @staticmethod
    def IsExploitedCorpse(agent_id: int) -> bool:
        """Whether the agent's corpse has already been exploited (``Agent.py:1072-1075``)."""

        return Agent.IsUsedCorpse(agent_id)

    @staticmethod
    def IsAlive(agent_id: int) -> bool:
        """Check if the agent is alive (``Agent.py:1077-1093``).

        The source's negation of :meth:`IsDead`'s terms, including the epsilon.
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        health = float(living.hp)
        is_dead = bool(living.is_dead)
        dead_by_type_map = bool(living.is_dead_by_type_map)
        is_exploitable_corpse = bool(living.is_exploitable)
        is_used_corpse = bool(living.is_used_corpse)
        return (
            health > Agent.DEAD_HEALTH_EPSILON
            and not is_dead
            and not dead_by_type_map
            and not is_exploitable_corpse
            and not is_used_corpse
        )

    @staticmethod
    def IsWeaponSpelled(agent_id: int) -> bool:
        """Check if the agent's weapon is spelled (``Agent.py:1095-1100``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_weapon_spelled

    @staticmethod
    def IsInCombatStance(agent_id: int) -> bool:
        """Check if the agent is in a combat stance (``Agent.py:1102-1107``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_in_combat_stance

    @staticmethod
    def HasStance(agent_id: int) -> bool:
        """Always ``False`` (``Agent.py:1109-1112``).

        The source returns the literal; the combat-event helper behind it is commented out.
        """

        return False

    @staticmethod
    def GetStanceID(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1114-1117``)."""

        return 0

    @staticmethod
    def GetStanceCooldown(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1119-1122``)."""

        return 0

    @staticmethod
    def IsAggressive(agent_id: int) -> bool:
        """Check if the agent is attacking or casting (``Agent.py:1124-1132``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        is_attacking = living.is_attacking
        is_casting = living.is_casting
        return is_attacking or is_casting

    @staticmethod
    def IsAttacking(agent_id: int) -> bool:
        """Check if the agent is attacking (``Agent.py:1134-1140``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_attacking

    @staticmethod
    def IsCasting(agent_id: int) -> bool:
        """Check if the agent is casting (``Agent.py:1142-1148``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_casting

    @staticmethod
    def GetCastingSkillID(agent_id: int) -> int:
        """Retrieve the skill the agent is casting (``Agent.py:1150-1161``)."""

        if not Agent.IsCasting(agent_id):
            return 0

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0

        return living.skill

    @staticmethod
    def GetTarget(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1163-1203``).

        The source returns the literal: its real body — player, hero, pet and combat-event lookups
        — is one long comment (``Agent.py:1167-1203``), so there is nothing to port but the
        constant.
        """

        return 0

    @staticmethod
    def GetCastingTarget(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1205-1208``)."""

        return 0

    @staticmethod
    def GetRemainingCastTime(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1210-1213``)."""

        return 0

    @staticmethod
    def GetRemainingRechargeTime(agent_id: int, skill_id: int) -> int:
        """Always ``0`` (``Agent.py:1215-1218``)."""

        return 0

    @staticmethod
    def IsTargeted(agent_id: int) -> bool:
        """Always ``False`` (``Agent.py:1220-1223``)."""

        return False

    @staticmethod
    def GetAgetsTargeting(agent_id: int) -> list[int]:
        """Always ``[]`` (``Agent.py:1225-1228``)."""

        return []

    @staticmethod
    def IsSkillOnCooldown(agent_id: int, skill_id: int) -> bool:
        """Always ``False`` (``Agent.py:1230-1233``)."""

        return False

    @staticmethod
    def IsCooldownEstimated(agent_id: int, skill_id: int) -> bool:
        """Always ``False`` (``Agent.py:1235-1238``)."""

        return False

    @staticmethod
    def GetSkillsOnCooldown(agent_id: int) -> list[tuple[int, int, bool]]:
        """Always ``[]`` (``Agent.py:1240-1246``)."""

        return []

    @staticmethod
    def GetRecentHealingReceived(agent_id: int, count: int = 20) -> list[tuple[int, int, float, int]]:
        """Always ``[]`` (``Agent.py:1248-1252``)."""

        return []

    @staticmethod
    def GetRecentHealingDealt(agent_id: int, count: int = 20) -> list[tuple[int, int, float, int]]:
        """Always ``[]`` (``Agent.py:1254-1258``)."""

        return []

    @staticmethod
    def HasEffectRenewed(agent_id: int, effect_id: int, window_ms: int = 10000) -> bool:
        """Always ``False`` (``Agent.py:1260-1263``)."""

        return False

    @staticmethod
    def GetObservedSkillbar(agent_id: int) -> list[int]:
        """Always ``[]`` (``Agent.py:1265-1269``)."""

        return []

    @staticmethod
    def GetAttackTarget(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1271-1274``)."""

        return 0

    @staticmethod
    def IsIdle(agent_id: int) -> bool:
        """Check if the agent is idle (``Agent.py:1276-1281``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_idle

    @staticmethod
    def HasBossGlow(agent_id: int) -> bool:
        """Check if the agent has a boss glow (``Agent.py:1283-1288``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.has_boss_glow

    @staticmethod
    def GetWeaponType(agent_id: int) -> tuple[int, str]:
        """Retrieve the weapon type of the agent (``Agent.py:1290-1305``)."""

        from .enums_src.game_data_enums import Weapon, Weapon_Names

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, "Unknown"

        try:
            weapon_type_enum = Weapon(living.weapon_type)
        except ValueError:
            return living.weapon_type, "Unknown"

        name = Weapon_Names.get(weapon_type_enum, "Unknown")
        return living.weapon_type, name

    @staticmethod
    def IsHoldingItem(agent_id: int) -> bool:
        """Check if the agent is carrying a bundle (``Agent.py:1307-1318``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False

        return living.weapon_type == 0

    @staticmethod
    def GetWeaponExtraData(agent_id: int) -> tuple[int, int, int, int]:
        """Retrieve the weapon extra data of the agent (``Agent.py:1320-1331``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, 0, 0, 0

        return (
            living.weapon_item_id,
            living.weapon_item_type,
            living.offhand_item_id,
            living.offhand_item_type,
        )

    @staticmethod
    def IsMartial(agent_id: int) -> bool:
        """Check if the agent is martial (``Agent.py:1333-1355``).

        The source's body, unblocked on 2026-09-26: ``Skill.GetID("Illusionary_Weaponry")`` was
        already ported (``py4gw/skill.py`` over native's own name table), and ``Effects.HasEffect``
        (``Effect.py:101-103``) landed with ``py4gw/effect.py``. The member still writes
        ``Agent.ILLUSIONARY_WEAPONRY_ID`` on first use, which is the source's own memo.
        """

        if Agent.ILLUSIONARY_WEAPONRY_ID == 0:
            from .skill import Skill

            Agent.ILLUSIONARY_WEAPONRY_ID = Skill.GetID("Illusionary_Weaponry")

        if Agent.ILLUSIONARY_WEAPONRY_ID:
            from .effect import Effects

            if Effects.HasEffect(agent_id, Agent.ILLUSIONARY_WEAPONRY_ID):
                return False

        if Agent.IsPet(agent_id):
            return True
        martial_weapon_types = ["Bow", "Axe", "Hammer", "Daggers", "Scythe", "Spear", "Sword"]
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if weapon_type == 0:
            return False
        return weapon_name in martial_weapon_types

    @staticmethod
    def IsCaster(agent_id: int) -> bool:
        """Check if the agent is a caster (``Agent.py:1357-1372``).

        The body is the source's; the raise comes from ``Agent.IsPet`` (allegiance enum) and
        ``Agent.GetWeaponType`` (weapon enum), which own the missing pieces.
        """

        if Agent.IsPet(agent_id):
            return False

        caster_weapon_types = {"Wand", "Staff", "Staff1", "Staff2", "Staff3", "Scepter", "Scepter2"}
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if weapon_type == 0 or weapon_name == "Unknown":
            return False

        return weapon_name in caster_weapon_types

    @staticmethod
    def IsMelee(agent_id: int) -> bool:
        """Check if the agent is melee (``Agent.py:1374-1394``).

        The source's body, unblocked the same way as :meth:`IsMartial`.
        """

        if Agent.ILLUSIONARY_WEAPONRY_ID == 0:
            from .skill import Skill

            Agent.ILLUSIONARY_WEAPONRY_ID = Skill.GetID("Illusionary_Weaponry")
        if Agent.ILLUSIONARY_WEAPONRY_ID:
            from .effect import Effects

            if Effects.HasEffect(agent_id, Agent.ILLUSIONARY_WEAPONRY_ID):
                return False
        if Agent.IsPet(agent_id):
            return True
        melee_weapon_types = ["Axe", "Hammer", "Daggers", "Scythe", "Sword"]
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if weapon_type == 0:
            return False
        return weapon_name in melee_weapon_types

    @staticmethod
    def IsRanged(agent_id: int) -> bool:
        """Check if the agent is ranged (``Agent.py:1396-1409``).

        The body is the source's; the raise comes from ``Agent.IsPet`` and ``Agent.GetWeaponType``.
        """

        if Agent.IsPet(agent_id):
            return False
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if weapon_type == 0:
            return False
        ranged_weapon_types = ["Bow", "Spear"]
        return weapon_name in ranged_weapon_types

    @staticmethod
    def GetDaggerStatus(agent_id: int) -> int:
        """Retrieve the dagger status of the agent (``Agent.py:1411-1417``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.dagger_status

    @staticmethod
    def GetAllegiance(agent_id: int) -> tuple[int, str]:
        """Retrieve the allegiance of the agent (``Agent.py:1419-1433``)."""

        from .enums_src.game_data_enums import Allegiance, AllegianceNames

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, "Unknown"

        try:
            allegiance_enum = Allegiance(living.allegiance)
        except ValueError:
            return living.allegiance, "Unknown"

        name = AllegianceNames.get(allegiance_enum, "Unknown")
        return living.allegiance, name

    @staticmethod
    def IsPlayer(agent_id: int) -> bool:
        """Check if the agent is a player (``Agent.py:1435-1438``)."""

        login_number = Agent.GetLoginNumber(agent_id)
        return login_number != 0

    @staticmethod
    def IsNPC(agent_id: int) -> bool:
        """Check if the agent is an NPC (``Agent.py:1440-1443``)."""

        login_number = Agent.GetLoginNumber(agent_id)
        return login_number == 0

    @staticmethod
    def GetNPCModelByID(model_id: int) -> NPC_ModelStruct | None:
        """Retrieve an NPC model record by its id, or ``None`` (``Agent.py:1445-1463``).

        Adapted at the context, like :meth:`GetAttributes`: the source asks
        ``GWContext.World.GetContext()``; this port reads the same world context through
        ``ConnectedClient.read_world_context``, whose ``npc_models`` is the ported
        ``npc_models_array``. The member's own order is kept — the indexed record first, then the
        scan by ``model_file_id``.
        """

        if model_id <= 0:
            return None
        client = require_client()
        try:
            world_ctx: WorldContextStruct | None = client.read_world_context()
        except (OSError, RuntimeError):
            return None
        if world_ctx is None:
            return None
        npc_models = world_ctx.npc_models
        if not npc_models:
            return None
        if model_id < len(npc_models):
            npc = npc_models[model_id]
            if npc and npc.is_valid:
                return npc
        for npc in npc_models:
            if int(npc.model_file_id) == int(model_id):
                return npc
        return None

    @staticmethod
    def GetNPCFlags(agent_id: int) -> int:
        """Retrieve the NPC flags of the agent (``Agent.py:1465-1471``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None or living.is_player:
            return 0
        npc = Agent.GetNPCModelByID(int(living.player_number))
        return int(npc.npc_flags) if npc else 0

    @staticmethod
    def IsFleshy(agent_id: int) -> bool:
        """Check if the agent's model is fleshy (``Agent.py:1473-1481``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        if living.is_player:
            return True
        npc = Agent.GetNPCModelByID(int(living.player_number))
        return bool(npc and npc.is_fleshy)

    @staticmethod
    def HasQuest(agent_id: int) -> bool:
        """Check if the agent has a quest (``Agent.py:1483-1488``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.has_quest

    @staticmethod
    def IsDeadByTypeMap(agent_id: int) -> bool:
        """Check if the type map marks the agent dead (``Agent.py:1490-1495``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_dead_by_type_map

    @staticmethod
    def IsFemale(agent_id: int) -> bool:
        """Check if the agent is female (``Agent.py:1497-1502``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_female

    @staticmethod
    def IsHidingCape(agent_id: int) -> bool:
        """Check if the agent is hiding its cape (``Agent.py:1504-1509``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_hiding_cape

    @staticmethod
    def CanBeViewedInPartyWindow(agent_id: int) -> bool:
        """Check if the agent can be viewed in the party window (``Agent.py:1511-1516``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.can_be_viewed_in_party_window

    @staticmethod
    def IsSpawned(agent_id: int) -> bool:
        """Check if the agent is spawned (``Agent.py:1518-1523``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_spawned

    @staticmethod
    def IsBeingObserved(agent_id: int) -> bool:
        """Check if the agent is being observed (``Agent.py:1525-1530``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_being_observed

    @staticmethod
    def GetOvercast(agent_id: int) -> float:
        """Retrieve the overcast of the agent (``Agent.py:1532-1538``).

        The field is the source's ``h0128`` — an unnamed word of the living record that this port's
        context carries under the same name (``agent_array.py:287``).
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.h0128

    @staticmethod
    def GetProfessionsTexturePaths(agent_id: int) -> tuple[str, str]:
        """Retrieve the profession icon texture paths (``Agent.py:1540-1561``).

        **Not portable, and not a missing piece of work.** Both halves of the body that read the
        client are ported — ``GetProfessions`` reads the record and ``GetProfessionNames`` maps it
        through ``enums_src.GameData_enums.Profession`` — but the string the source prefixes both
        paths with is ``PySystem.Console.get_projects_path()``, which native defines as
        ``PY4GW::process_manager::GetModuleDirectory()`` (``system_bindings.cpp:72-74``): **the
        directory of the injected runtime's own module**, where its ``Assets/Textures/Profession_Icons``
        live (``process_manager.cpp:38-40``; the same root its ``json``, ``settings`` and ``offsets``
        folders hang from). That installation is the injected runtime's own; this project is a
        controller package with no such module and ships no such assets.

        So this is the **third member of the artifact kind** — with ``Player.player_instance`` and
        ``Dialog._call_native_dialog_method`` — and it reports that plainly rather than returning a
        path built from this project's own directory, which would be a string the source never
        produces. Per ``PORTING_RULES.md`` that divergence is a finding, and it is recorded in
        [`docs/AGENT_PORT.md`](../../docs/AGENT_PORT.md) and
        [`docs/CLASS_PORT_MAP.md`](../../docs/CLASS_PORT_MAP.md) §1.
        """

        raise _unported(
            "GetProfessionsTexturePaths",
            "the injected runtime's own module directory, which PySystem.Console."
            "get_projects_path() returns (system_bindings.cpp:72-74 → "
            "process_manager::GetModuleDirectory, process_manager.cpp:38-40) and where its "
            "Assets/Textures/Profession_Icons live. This project is a controller package with no "
            "such module and ships no such assets, so there is no path to build",
        )

    # ── item agents (Agent.py:1563-1597) ──────────────────────────────────

    @staticmethod
    def GetItemAgentOwnerID(agent_id: int) -> int:
        """Retrieve the owner ID of the item agent, or ``999`` (``Agent.py:1564-1573``)."""

        item = Agent.GetItemAgentByID(agent_id)
        if item is None:
            return 999
        current_owner_id = item.owner

        return current_owner_id

    @staticmethod
    def GetItemAgentItemID(agent_id: int) -> int:
        """Retrieve the item ID of the item agent (``Agent.py:1575-1581``)."""

        item_data = Agent.GetItemAgentByID(agent_id)
        if item_data is None:
            return 0
        return item_data.item_id

    @staticmethod
    def GetItemAgentExtraType(agent_id: int) -> int:
        """Retrieve the extra type of the item agent (``Agent.py:1583-1589``)."""

        item_data = Agent.GetItemAgentByID(agent_id)
        if item_data is None:
            return 0
        return item_data.extra_type

    @staticmethod
    def GetItemAgenth00CC(agent_id: int) -> int:
        """Retrieve the ``h00CC`` of the item agent (``Agent.py:1591-1597``)."""

        item_data = Agent.GetItemAgentByID(agent_id)
        if item_data is None:
            return 0
        return item_data.h00CC

    # ── gadget agents (Agent.py:1599-1646) ────────────────────────────────

    @staticmethod
    def GetGadgetID(agent_id: int) -> int:
        """Retrieve the gadget ID of the agent (``Agent.py:1600-1606``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.gadget_id

    @staticmethod
    def GetGadgetAgentID(agent_id: int) -> int:
        """Retrieve the agent ID of the gadget agent (``Agent.py:1608-1614``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.agent_id

    @staticmethod
    def GetGadgetAgentExtraType(agent_id: int) -> int:
        """Retrieve the extra type of the gadget agent (``Agent.py:1616-1622``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.extra_type

    @staticmethod
    def GetGadgetAgenth00C4(agent_id: int) -> int:
        """Retrieve the ``h00C4`` of the gadget agent (``Agent.py:1624-1630``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.h00C4

    @staticmethod
    def GetGadgetAgenth00C8(agent_id: int) -> int:
        """Retrieve the ``h00C8`` of the gadget agent (``Agent.py:1632-1638``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.h00C8

    @staticmethod
    def GetGadgetAgenth00D4(agent_id: int) -> list:
        """Retrieve the ``h00D4`` of the gadget agent (``Agent.py:1640-1646``).

        One detail of the value: the source returns the record's fixed-size array object as it
        stands, and this port answers with the dict-free ``list`` of its four words — the type the
        member's own ``-> list`` annotation declares, and the one a caller can iterate the same way.
        """

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return []
        return list(gadget.h00D4)
