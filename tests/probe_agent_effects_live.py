"""Read-only live probe: the agent-name walk, the effects walk and the skill timer.

**What it proves, and what it does not.** Every one of these three read paths is new (2026-09-26) and
had only offline evidence: `Agent.GetNameByID` and its neighbours over `PyAgent.get_agent_enc_name`,
the whole `Effects` class over `WorldContext.party_effects`, and `PY4GW::MemoryManager.GetSkillTimer`,
which the effect snapshot's two computed fields and `Skillbar`'s `get_recharge` are measured against.
This probe points them at the **running client** and prints what they answer.

**It needs no elevation, and that is deliberate.** `py4gw.connect()` asserts elevation because
connecting *writes* — it installs hooks and patches. Nothing here needs that: the probe opens the
read-only `ProcessMemoryReader`, builds the same facades `ConnectedClient` builds, and registers that
stand-in as the current client so the **ported members themselves** run — unmodified — against live
data. So:

- **no elevation**, no `connect()`, no capability layer, no hook, no patch, no call into the client;
- the stand-in is a harness, not port code: it exposes exactly the reads the members make
  (`reader`, `read_world_context()`, `read_acc_agent_context()`, `read_gadget_context()`,
  `read_item_context()`, `read_skill()`, `agent_array`, `memory_manager`, `acc_agent_context`,
  `resolves()`), each delegating to the real facade over the live process;
- the two *action* members `Effects.DropBuff` and `Effects.ApplyDrunkEffect` are **not** called: both
  are calls into the client that change the game (a dropped buff, a drunk post-process). The probe
  only reports whether their resolvers are in the catalog.

**What the elevated suite adds.** `tests/test_live_agent_effects.py` runs the same members through a
real `py4gw.connect()`: that is where the connection's own wiring, the GW.dat string-table decode
(`Agent.GetNameByID` for a name that is not a player's inline form) and the capability layer are
exercised. This probe covers the reads; that suite covers the connection.

Usage: python tests/probe_agent_effects_live.py [report-path]
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Any

from py4gw.context.acc_agent_context import AccAgentContext
from py4gw.context.agent_array import AgentArray, AgentArrayStruct
from py4gw.context.game_context import GameContext
from py4gw.context.gadget_context import GadgetContext
from py4gw.context.item_context import ItemContext
from py4gw.context.text_parser_context import TextParser
from py4gw.context.world_context import WorldContext, WorldContextStruct
from py4gw.memory import MemoryManager, ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How many agents to look at by name. The walk is one remote read per step, so a sample is enough
#: to prove the mechanism while keeping the probe under a second.
NAME_SAMPLE = 6

#: The bound the ported copy uses (``py4gw/agent.py``, ``MAX_ENC_NAME_CODE_UNITS``).
MAX_ENC_NAME_CODE_UNITS = 256

_WIDE_CHAR_SIZE = 2
_DWORD_MASK = 0xFFFFFFFF


class _LiveClient:
    """A connection stand-in whose every read is the real facade over the live process.

    This is the probe's own harness. The ported members call ``require_client()`` and then use
    ``reader``, the ``read_*`` accessors, ``agent_array``, ``memory_manager`` and
    ``acc_agent_context``; offering those is the whole of it, and each one is the same object
    ``ConnectedClient`` would hand out.
    """

    def __init__(
        self,
        pid: int,
        reader: ProcessMemoryReader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        self.pid = pid
        self.reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self.memory_manager = MemoryManager(reader, scanner, patterns)
        self.memory_manager.Scan()
        self._game_context = GameContext(reader, scanner, patterns)
        self._game_context.initialize()
        self._world_context = WorldContext(reader, self._game_context)
        self.acc_agent_context = AccAgentContext(reader, self._game_context)
        self._gadget_context = GadgetContext(reader, self._game_context)
        self._item_context = ItemContext(
            reader, self._game_context, scanner, patterns
        )
        self._text_parser = TextParser(reader, self._game_context)
        self.agent_array = AgentArray(
            reader, scanner, patterns, cache_context_validator=lambda: True
        )
        self.agent_array.initialize()

    def resolves(self, name: str) -> bool:
        return self._patterns.resolve(name, self._scanner).ok

    def call_function(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "this probe installs no capability layer, so no client function can be called"
        )

    def read_world_context(self) -> WorldContextStruct | None:
        return self._world_context.read()

    def read_acc_agent_context(self) -> Any:
        return self.acc_agent_context.read()

    def read_gadget_context(self) -> Any:
        return self._gadget_context.read()

    def read_item_context(self) -> Any:
        return self._item_context.read()

    def read_skill(self, skill_id: int) -> Any:
        """``Skill.GetID``'s lookup: the record is not needed for the id, only the name table is."""

        return None

    @property
    def text_parser(self) -> Any:
        """The context the string table's own ``_get_client_language`` asks for."""

        return self._text_parser


def _read_enc_name(reader: ProcessMemoryReader, pointer: int) -> list[int]:
    """The binding's copy, as ``py4gw/agent.py`` writes it (``agent_bindings.cpp:217-223``)."""

    raw = bytearray()
    for index in range(MAX_ENC_NAME_CODE_UNITS):
        unit = reader.read(pointer + index * _WIDE_CHAR_SIZE, _WIDE_CHAR_SIZE)
        raw.extend(unit)
        if int.from_bytes(unit, "little") == 0:
            break
    return list(raw)


def _text_from_bytes(values: list[int]) -> str:
    """The port's own decode of the copied bytes (``Agent._enc_name_bytes_to_wstr``)."""

    if not values:
        return ""
    raw = bytes(values)
    text = raw[: len(raw) & ~1].decode("utf-16-le", "ignore")
    null_index = text.find("\x00")
    return text[:null_index] if null_index >= 0 else text


def _resolve_name_pointer(
    client: _LiveClient, world: WorldContextStruct | None, agent: Any
) -> tuple[str, int]:
    """Where the source's walk finds this agent's name pointer (``agent_methods.cpp:249-316``).

    Returns ``(branch, pointer)`` so the report says which of the four branches answered.
    """

    if agent is None:
        return "no record", 0

    if bool(agent.is_living_type):
        living = agent.GetAsAgentLiving()
        if living is None:
            return "living without record", 0
        login_number = int(living.login_number)
        if login_number:
            players = world.players if world is not None else None
            if not players or login_number >= len(players):
                return "player past the array", 0
            return "player array", int(players[login_number].name_enc_ptr)
        infos = world.agent_name_info if world is not None else None
        agent_id = int(agent.agent_id)
        if infos and agent_id < len(infos):
            pointer = int(infos[agent_id].name_enc_ptr)
            if pointer:
                return "world agent_infos", pointer
        npcs = world.npc_models if world is not None else None
        player_number = int(living.player_number)
        if npcs and player_number < len(npcs):
            return "npc record", int(npcs[player_number].name_enc_ptr)
        return "living, no name", 0

    if bool(agent.is_gadget_type):
        agent_id = int(agent.agent_id)
        summary = client.acc_agent_context.read()
        if summary is None:
            return "gadget, no agent context", 0
        infos = summary.agent_summary_info_list
        if not infos or agent_id >= len(infos):
            return "gadget past the summary array", 0
        sub = infos[agent_id].extra_info_sub
        if sub is None:
            return "gadget, no summary entry", 0
        if int(sub.gadget_name_enc):
            return "agent summary gadget name", int(sub.gadget_name_enc)
        gadget = client.read_gadget_context()
        gadget_id = int(sub.gadget_id)
        if gadget is None or gadget_id >= gadget.array_size:
            return "gadget past its context array", 0
        values = gadget.gadget_infos(gadget_id + 1)
        if gadget_id >= len(values):
            return "gadget, no context entry", 0
        return "gadget context", int(values[gadget_id].name_enc)

    if bool(agent.is_item_type):
        item_agent = agent.GetAsAgentItem()
        if item_agent is None:
            return "item without record", 0
        context = client.read_item_context()
        if context is None:
            return "item, no context", 0
        item = context.GetItemById(int(item_agent.item_id))
        return ("item array", int(item.name_enc)) if item is not None else ("item, no record", 0)

    return "unknown kind", 0


def _name_walk_section(client: _LiveClient, reader: ProcessMemoryReader) -> dict[str, Any]:
    """Every present agent, walked the way the binding's ``GetAgentEncName`` walks it.

    The point of the section is the *coverage of the branches*: which of native's four answer
    (``agent_methods.cpp:263-316``), how many agents carry a name at all, and — for the one form the
    port can decode without the string table — the decoded text. A player's encoded name carries the
    text inline behind the ``0xBA9`` prefix, so its decode needs neither the table nor the client;
    every other name is string-table indices and needs the table GW.dat fills.
    """

    from py4gw.agent import Agent, get_agent_enc_name
    from py4gw.internals.string_table import decode as decode_raw

    section: dict[str, Any] = {}
    world = client.read_world_context()
    view = client.agent_array.get_context()

    #: Time the ported binding's own walk, which is the thing the sources keep fast: native's
    #: ``GetAgentEncName`` reaches the record through ``GetAgentByID``'s single index into the
    #: client's agent table (``agent_methods.cpp:73-88``), not through a rebuilt cache. The other
    #: number is the *old* path — Reforged's Python ``Agent.GetAgentByID``, whose view answers from
    #: ``_build_allegiance_cache`` — timed cold, after that cache is dropped.
    timed_ids = [
        int(record.agent_id)
        for record in view.raw_agents
        if record is not None and int(record.agent_id) != 0
    ][:25]
    if timed_ids:
        started = time.perf_counter()
        get_agent_enc_name(timed_ids[0])
        section["binding_walk_ms_cold"] = round(
            (time.perf_counter() - started) * 1000.0, 3
        )
        started = time.perf_counter()
        for agent_id in timed_ids:
            get_agent_enc_name(agent_id)
        elapsed = time.perf_counter() - started
        section["binding_walk_ms_total"] = round(elapsed * 1000.0, 2)
        section["binding_walk_ms_per_agent"] = round(
            elapsed * 1000.0 / len(timed_ids), 3
        )

        from py4gw.agent import Agent

        facade = client.agent_array
        cache_cold: list[float] = []
        for agent_id in timed_ids[:3]:
            facade.reset_cache()
            started = time.perf_counter()
            Agent.GetAgentByID(agent_id)
            cache_cold.append(round((time.perf_counter() - started) * 1000.0, 3))
        section["view_cache_ms_cold"] = cache_cold
    section["binding_walk_agents"] = len(timed_ids)

    branches: dict[str, int] = {}
    with_name = 0
    player_rows: list[dict[str, Any]] = []
    sample: list[dict[str, Any]] = []
    mismatches: list[int] = []

    for record in view.raw_agents:
        if record is None:
            continue
        agent_id = int(record.agent_id)
        if agent_id == 0:
            continue
        branch, pointer = _resolve_name_pointer(client, world, record)
        branches[branch] = branches.get(branch, 0) + 1
        if not pointer:
            continue
        raw = _read_enc_name(reader, pointer)
        if not raw:
            continue
        with_name += 1

        # The ported member must answer exactly the same bytes as this independent read.
        if get_agent_enc_name(agent_id) != raw:
            mismatches.append(agent_id)

        row = {
            "agent_id": agent_id,
            "kind": "living"
            if bool(record.is_living_type)
            else ("item" if bool(record.is_item_type) else "gadget"),
            "branch": branch,
            "pointer": hex(pointer),
            "bytes": len(raw),
        }
        # 0xBA9: a player name, inline text. That decode is the port's own function and needs no
        # string table, so it is checked here.
        if raw[:2] == [0xA9, 0x0B]:
            text = decode_raw(bytes(raw))
            row["player_prefix"] = True
            row["decoded"] = text
            row["GetNameByID"] = Agent.GetNameByID(agent_id)
            row["GetEncNameStrByID"] = Agent.GetEncNameStrByID(agent_id)
            player_rows.append(row)
        elif len(sample) < 6:
            row["code_units"] = _text_from_bytes(raw)[:24]
            row["GetEncNameStrByID"] = Agent.GetEncNameStrByID(agent_id)
            sample.append(row)

    section["branches"] = branches
    section["agents_with_a_name"] = with_name
    section["port_bytes_mismatches"] = mismatches
    section["player_names"] = player_rows
    section["string_table_names_sample"] = sample
    section["table_note"] = (
        "every name that is not player-prefixed is string-table indices; decoding it needs the "
        "table GW.dat fills, which is a call into the client (py4gw/dat_reader.py), so it is the "
        "elevated suite that proves that half"
    )
    return section


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report)

    process = clients[0]
    pid = int(process["pid"])
    report["pid"] = pid
    report["path"] = process.get("path")
    report["elevated"] = win32.is_elevated()
    report["connect"] = "not used: this probe reads directly"

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(
            reader, int(module["base_address"]), int(module["size"])
        )
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        client = _LiveClient(pid, reader, scanner, patterns)
    except Exception as error:  # noqa: BLE001 - reported, not raised
        report["error"] = f"{type(error).__name__}: {error}"
        reader.close()
        return _write(report)

    # The ported members are readable now: register the stand-in where ``require_client`` looks.
    import py4gw.client as client_module
    import py4gw.agent as agent_module
    import py4gw.effect as effect_module
    from py4gw.agent import Agent
    from py4gw.effect import Effects

    client_module._current_client = client  # type: ignore[attr-defined]

    try:
        report["memory_manager"] = _memory_manager_section(client)
        report["agent_array"] = _array_section(client)
        report["effects"] = _effects_section(client)
        report["names"] = _names_section(client, reader, patterns)
        report["name_walk"] = _name_walk_section(client, reader)
        report["martial"] = _martial_section(client)
        report["resolvers"] = {
            "effects.drop_buff_func": patterns.resolve(
                "effects.drop_buff_func", scanner
            ).ok,
            "effects.post_process_effect_func": patterns.resolve(
                "effects.post_process_effect_func", scanner
            ).ok,
        }
        report["action_members"] = (
            "not called: Effects.DropBuff and Effects.ApplyDrunkEffect change the game "
            "(a dropped buff, a drunk post-process) and need the capability layer"
        )
        report["imports_used"] = (
            f"{agent_module.__name__}, {effect_module.__name__}: the ported members themselves"
        )
    finally:
        client_module._current_client = None  # type: ignore[attr-defined]
        reader.close()

    return _write(report)


def _memory_manager_section(client: _LiveClient) -> dict[str, Any]:
    """The skill timer and the window handle, straight from the ported ``MemoryManager``."""

    section: dict[str, Any] = {}
    manager = client.memory_manager
    first = manager.GetSkillTimer()
    time.sleep(0.25)
    second = manager.GetSkillTimer()
    section["GetSkillTimer_first"] = first
    section["GetSkillTimer_second"] = second
    section["advanced_ms"] = (second - first) & _DWORD_MASK
    section["GetGWWindowHandle"] = manager.GetGWWindowHandle()
    return section


def _array_section(client: _LiveClient) -> dict[str, Any]:
    """The source-shaped view: header, records, and the category lists the source fills."""

    from py4gw.agent import Agent
    from py4gw.agent_array import AgentArray as AgentArrayClass

    section: dict[str, Any] = {}
    view = client.agent_array.read_context()
    header = view.agent_array
    section["address"] = hex(client.agent_array.get_ptr())
    section["buffer"] = hex(int(header.m_buffer))
    section["size"] = int(header.m_size)
    section["capacity"] = int(header.m_capacity)
    section["struct_matches_gwarray"] = ctypes.sizeof(AgentArrayStruct) == ctypes.sizeof(
        type(header)
    )

    records = view.raw_agents
    present = [record for record in records if record is not None]
    section["raw_slots"] = len(records)
    section["non_null"] = len(present)
    section["ids_sample"] = [int(record.agent_id) for record in present[:8]]
    section["kinds"] = {
        "living": sum(1 for record in present if bool(record.is_living_type)),
        "item": sum(1 for record in present if bool(record.is_item_type)),
        "gadget": sum(1 for record in present if bool(record.is_gadget_type)),
    }

    # The category lists come through the port, not from the probe: this is the gate that needed
    # the point-of-use ``AccAgentContext`` refresh.
    agents = view.GetAgentArray()
    section["category_all"] = len(agents)
    section["category_ally"] = len(view.GetAllyArray())
    section["category_enemy"] = len(view.GetEnemyArray())
    section["category_items"] = len(view.GetItemAgentArray())
    section["category_gadgets"] = len(view.GetGadgetAgentArray())
    section["module_getter_agrees"] = AgentArrayClass.GetAgentArray() == agents
    if agents:
        first = view.GetAgentByID(int(agents[0]))
        section["view_GetAgentByID"] = None if first is None else int(first.agent_id)
        through_agent = Agent.GetAgentByID(int(agents[0]))
        section["agent_GetAgentByID"] = (
            None if through_agent is None else int(through_agent.agent_id)
        )
    return section


def _effects_section(client: _LiveClient) -> dict[str, Any]:
    """The effects walk, through the ported ``Effects`` class."""

    from py4gw.effect import Effects

    section: dict[str, Any] = {}
    world = client.read_world_context()
    section["world_context_read"] = world is not None
    if world is not None:
        header = world.party_effects_array
        section["party_effects_array"] = {
            "buffer": hex(int(header.m_buffer)),
            "size": int(header.m_size),
            "capacity": int(header.m_capacity),
        }
    blocks = world.party_effects if world is not None else None
    section["party_effect_blocks"] = 0 if not blocks else len(blocks)
    rows: list[dict[str, Any]] = []
    for block in (blocks or [])[:6]:
        agent_id = int(block.agent_id)
        effects = Effects.GetEffects(agent_id)
        buffs = Effects.GetBuffs(agent_id)
        row: dict[str, Any] = {
            "agent_id": agent_id,
            "effect_count": Effects.GetEffectCount(agent_id),
            "buff_count": Effects.GetBuffCount(agent_id),
            "effects": len(effects),
            "buffs": len(buffs),
        }
        if effects:
            first = effects[0]
            row["first_effect"] = {
                "skill_id": first.skill_id,
                "attribute_level": first.attribute_level,
                "effect_id": first.effect_id,
                "duration": first.duration,
                "timestamp": first.timestamp,
                "time_elapsed": first.time_elapsed,
                "time_remaining": first.time_remaining,
            }
            row["attribute_level_lookup"] = Effects.EffectAttributeLevel(
                agent_id, first.skill_id
            )
            row["remaining_lookup"] = Effects.GetEffectTimeRemaining(
                agent_id, first.skill_id
            )
            row["EffectExists"] = Effects.EffectExists(agent_id, first.skill_id)
            row["HasEffect"] = Effects.HasEffect(agent_id, first.skill_id)
            row["HasEffect_absent_skill"] = Effects.HasEffect(agent_id, 0xFFFF)
        if buffs:
            row["first_buff"] = {
                "skill_id": buffs[0].skill_id,
                "buff_id": buffs[0].buff_id,
                "target_agent_id": buffs[0].target_agent_id,
            }
            row["BuffExists"] = Effects.BuffExists(agent_id, buffs[0].skill_id)
            row["HasEffect_for_buff"] = Effects.HasEffect(agent_id, buffs[0].skill_id)
        instance = Effects.get_instance(agent_id)
        row["instance_is_PyEffects"] = type(instance).__name__
        rows.append(row)
    section["blocks"] = rows
    return section


def _names_section(
    client: _LiveClient, reader: ProcessMemoryReader, patterns: PatternCatalog
) -> dict[str, Any]:
    """The encoded-name walk: which branch answers, and the bytes it answers with."""

    from py4gw.agent import Agent, get_agent_enc_name

    section: dict[str, Any] = {}
    world = client.read_world_context()
    view = client.agent_array.get_context()
    candidates = [
        record for record in view.raw_agents if record is not None
    ][: NAME_SAMPLE * 3]
    rows: list[dict[str, Any]] = []
    for record in candidates:
        if len(rows) >= NAME_SAMPLE:
            break
        agent_id = int(record.agent_id)
        branch, pointer = _resolve_name_pointer(client, world, record)
        raw = _read_enc_name(reader, pointer) if pointer else []
        through_port = get_agent_enc_name(agent_id)
        row: dict[str, Any] = {
            "agent_id": agent_id,
            "kind": "living"
            if bool(record.is_living_type)
            else ("item" if bool(record.is_item_type) else "gadget"),
            "branch": branch,
            "pointer": hex(pointer),
            "bytes": len(raw),
            "code_units": _text_from_bytes(raw)[:24],
            "port_bytes": len(through_port),
            "port_matches_probe": through_port == raw,
            "GetEncNameByID_matches": Agent.GetEncNameByID(agent_id) == raw,
        }
        try:
            row["IsNameReady"] = Agent.IsNameReady(agent_id)
        except Exception as error:  # noqa: BLE001 - reported, not raised
            row["IsNameReady"] = f"{type(error).__name__}: {error}"
        try:
            row["GetNameByID"] = Agent.GetNameByID(agent_id)
        except Exception as error:  # noqa: BLE001 - reported, not raised
            row["GetNameByID"] = f"{type(error).__name__}: {error}"
        try:
            row["GetEncNameStrByID"] = Agent.GetEncNameStrByID(agent_id)[:40]
        except Exception as error:  # noqa: BLE001 - reported, not raised
            row["GetEncNameStrByID"] = f"{type(error).__name__}: {error}"
        rows.append(row)
    section["sample"] = rows
    section["walked"] = len(rows)
    if rows:
        first_name = rows[0].get("GetEncNameStrByID")
        if isinstance(first_name, str) and first_name and not first_name.startswith(
            ("RuntimeError", "AttributeError")
        ):
            found = Agent.GetAgentIDByName(first_name[:12])
            section["GetAgentIDByName_round_trip"] = found
    return section


def _martial_section(client: _LiveClient) -> dict[str, Any]:
    """``IsMartial``/``IsMelee`` against the source's own body, over every armed agent.

    The expectation is built in the source's order — the Illusionary Weaponry effect first, then the
    pet check, then the weapon name (``Agent.py:1340-1355`` and ``1381-1394``) — so a disagreement
    says which step of the body differs.
    """

    from py4gw.agent import Agent
    from py4gw.effect import Effects

    #: The source's own lists (``Agent.py:1351`` and ``1390``).
    martial_weapons = ("Bow", "Axe", "Hammer", "Daggers", "Scythe", "Spear", "Sword")
    melee_weapons = ("Axe", "Hammer", "Daggers", "Scythe", "Sword")

    view = client.agent_array.get_context()
    armed = 0
    mismatches: list[dict[str, Any]] = []
    for record in view.raw_agents:
        if record is None:
            continue
        agent_id = int(record.agent_id)
        if agent_id == 0:
            continue
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if int(weapon_type) == 0:
            continue
        armed += 1
        illusionary = Effects.HasEffect(agent_id, Agent.ILLUSIONARY_WEAPONRY_ID)
        is_pet = Agent.IsPet(agent_id)
        expected_martial = False if illusionary else (is_pet or weapon_name in martial_weapons)
        expected_melee = False if illusionary else (is_pet or weapon_name in melee_weapons)
        got_martial = Agent.IsMartial(agent_id)
        got_melee = Agent.IsMelee(agent_id)
        if got_martial != expected_martial or got_melee != expected_melee:
            mismatches.append(
                {
                    "agent_id": agent_id,
                    "kind": "living"
                    if bool(record.is_living_type)
                    else ("item" if bool(record.is_item_type) else "gadget"),
                    "weapon_type": weapon_type,
                    "weapon_name": weapon_name,
                    "is_pet": is_pet,
                    "illusionary_weaponry": illusionary,
                    "expected_martial": expected_martial,
                    "got_martial": got_martial,
                    "expected_melee": expected_melee,
                    "got_melee": got_melee,
                }
            )

    return {
        "illusionary_weaponry_id": Agent.ILLUSIONARY_WEAPONRY_ID,
        "agents_examined": len([r for r in view.raw_agents if r is not None]),
        "armed_agents": armed,
        "mismatches": mismatches[:6],
        "mismatch_count": len(mismatches),
    }


def _write(report: dict[str, Any]) -> int:
    import json

    text = json.dumps(report, indent=2, default=str)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"\nreport written to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
