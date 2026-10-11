"""Generate ``py4gw/gwa3/data_agent.py`` -- GwAu3's ``Agent_*`` reads over this project's records.

Part of the GwAu3-compatible layer; see ``docs/GWA3_COMPAT_SPEC.md``.

Run from the project root:

    python tools/generate_gwa3_data_agent.py

**Why the field table is generated.** ``Agent_GetAgentInfo`` is one ``Switch`` over 138 ``Case``
groups in GwAu3 (``GwAu3_Data_Agent.au3:82-524``), each reading one field at one offset with one
width. Transcribing 138 branches by hand is 138 chances to mistype an offset, and a mistyped offset
reads the wrong client field silently. So the cases are parsed from GwAu3's own source and each
offset is resolved against **ctypes'** view of the structure this project reads -- the authority
``docs/GWA3_AGENT_FIELD_AUDIT.md`` rests on.

**What is hand-written.** The accessors that are not a field lookup: the id sentinels, the boolean
tests, and the keys computed from more than one field. Those need judgement rather than transcription,
so they are written out in :data:`TEMPLATE_BODY` and :data:`TEMPLATE_ACCESSORS`, each citing its
GwAu3 line.

**Why each reader closes over the attribute name.** The record is a ``ctypes.Structure``, and this
project's porting rules forbid reaching a field through a dynamic name. So the *offset* decides the
attribute once, at generation time, and the emitted reader names it literally:
``lambda record: record.allegiance``. Nothing resolves a field by string at run time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GWAU3_AGENT_SOURCE = (
    REPO_ROOT / "external" / "GwAu3" / "API" / "Modules" / "Data" / "GwAu3_Data_Agent.au3"
)
OUTPUT_PATH = REPO_ROOT / "py4gw" / "gwa3" / "data_agent.py"

# Hand-written source this generated module carries, read at run time from ``tools/gwa3_snippets/``.
#
# The same mechanism the family generator uses, for the same reason: ``data_agent.py`` is rewritten
# whole on every run, so a function written straight into it would be lost the next time the generator
# runs and the module would stop matching its generator -- which a test checks, deliberately.
# ``_ApplyFilters`` is declared at ``GwAu3_Data_Agent.au3:1221``, inside this module's own GwAu3 source
# file, so this module is its home rather than a module of its own.
SNIPPETS_DIR = Path(__file__).resolve().parent / "gwa3_snippets"
HELPER_FILES: tuple[str, ...] = (
    "data_agent_apply_filters.py",
    "data_agent_effect_info.py",
    "data_agent_npc_player_info.py",
    "data_visible_effect.py",
)

CASE_LINE = re.compile(r"^\s*Case\s+(?P<keys>.+?)\s*$")
KEY = re.compile(r'"([^"]+)"')
MEMORY_READ = re.compile(
    r"Memory_Read\(\s*\$l_p_AgentPtr\s*\+\s*(?P<offset>0x[0-9A-Fa-f]+)\s*,\s*\"(?P<type>[^\"]+)\""
)

WIDTHS = {"byte": "B", "short": "h", "long": "i", "dword": "I", "float": "f", "ptr": "I"}
ARRAY_WIDTH = re.compile(r"^(?P<type>\w+)\[(?P<count>\d+)\]$")

# Keys whose behaviour is not a single-field read, and which no ``Case`` in the source expresses as
# one -- so :func:`parse_cases` does not see them. Each is implemented or refused by hand below.
#
# Measured: GwAu3's Switch declares **143** keys and the parser collects **137**; these are the six it
# cannot, because their cases return without a `Memory_Read`.
HAND_WRITTEN: tuple[str, ...] = (
    "Name", "vtable", "VisibleEffectsPtr", "VisibleEffectCount", "EffectCount", "BondCount",
    "HasVisibleEffects",
)

# Keys needing their own hand-written helper, because their case tests more than one field.
COMPUTED_KEYS: tuple[str, ...] = ("CanPickUp", "CurrentHP", "CurrentEnergy", "IsMoving", "IsCasting")

# Keys this layer **refuses** rather than answers, with the reason.
#
# All three walk a linked list that lives in the client's memory, reachable only through the
# connection. A record materialized with `from_buffer_copy` carries no target address, so the walk
# cannot be made here -- and answering `0` or `False` would be a wrong value of exactly the right
# type, which a caller cannot detect. So they refuse and name what they need.
UNIMPLEMENTED_KEYS: dict[str, str] = {
    "EffectCount": (
        "GwAu3_Data_Agent.au3:261-279 counts the agent's effects by walking the global agent-effects "
        "array through BasePointer[0x18][0x2C][0x508]. That walk needs the connection "
        "(py4gw/context); a materialized record carries no target address. Answering 0 here would be a "
        "wrong value a caller could not detect, so it refuses instead."
    ),
    "BondCount": (
        "GwAu3_Data_Agent.au3:280-299 counts the agent's bonds from the same global array "
        "(BasePointer[0x18][0x2C][0x508], bond sub-array at +0x4), and its BondArraySize is the same "
        "read pattern as `Agent_GetAgentEffectArrayInfo` (GwAu3_Data_Agent.au3:834-865). That walk "
        "needs the connection (py4gw/context) and a materialized record carries no target address. "
        "Same gap as EffectCount, same refusal."
    ),
    "HasVisibleEffects": (
        "GwAu3_Data_Agent.au3:383-384 counts the record's visible-effect linked list, which this "
        "project reads through a RemoteGWListView bound to the target address "
        "(py4gw/context/agent_array.py:935-948). A materialized record has no target address, so the "
        "walk cannot be made; this one refuses rather than answer a wrong boolean."
    ),
    "VisibleEffectCount": (
        "GwAu3_Data_Agent.au3:381-382 answers `VisibleEffect_Count`, which walks the same linked list "
        "(GwAu3_Data_Agent.au3:1143-1159). This project's `GWListStruct` "
        "(py4gw/context/gw_list.py:28-33) holds only an offset and a sentinel link -- it carries no "
        "count, so the list has to be walked through the connection "
        "(py4gw/context/agent_array.py:935-948). A materialized record has no target address, so it "
        "refuses rather than answer 0, which would be a wrong value a caller could not detect."
    ),
}

# Keys whose case tests the type word directly.
TYPE_WORD_KEYS: tuple[str, ...] = (
    "IsItemType", "IsGadgetType", "IsLivingType", "IsPlayer", "IsNPC",
    "HasVisibleEffects", "HasBond",
)

# Keys whose case compares a masked word, answered from one of the tables in TEMPLATE_BODY.
BOOLEAN_KEYS: tuple[str, ...] = (
    "IsBleeding", "IsConditioned", "IsCrippled", "IsDead", "IsDeepWounded", "IsPoisoned",
    "IsEnchanted", "IsDegenHexed", "IsHexed", "IsWeaponSpelled",
    "IsKnockedDown", "IsKnocked", "IsAttacking", "IsIdle",
    "InCombatStance", "HasQuest", "IsDeadByTypeMap", "IsFemale", "HasBossGlow", "IsHidingCap",
    "CanBeViewedInPartyWindow", "IsSpawned", "IsBeingObserved",
)

# The effect-word bits at `+0x13C` (`GwAu3_Data_Agent.au3:302-321`).
EFFECT_BITS: dict[str, int] = {
    "IsBleeding": 0x0001, "IsConditioned": 0x0002, "IsCrippled": 0x000A, "IsDead": 0x0010,
    "IsDeepWounded": 0x0020, "IsPoisoned": 0x0040, "IsEnchanted": 0x0080,
    "IsDegenHexed": 0x0400, "IsHexed": 0x0800, "IsWeaponSpelled": 0x8000,
}

# The type-map bits at `+0x15C` (`GwAu3_Data_Agent.au3:352-368`).
TYPEMAP_BITS: dict[str, int] = {
    "InCombatStance": 0x000001, "HasQuest": 0x000002, "IsDeadByTypeMap": 0x000008,
    "IsFemale": 0x000200, "HasBossGlow": 0x000400, "IsHidingCap": 0x001000,
    "CanBeViewedInPartyWindow": 0x020000, "IsSpawned": 0x040000, "IsBeingObserved": 0x400000,
}

# The model-state words at `+0x158` (`GwAu3_Data_Agent.au3:332-347`).
MODEL_STATE_SETS: dict[str, tuple[int, ...]] = {
    "IsKnockedDown": (0x450,), "IsKnocked": (0x450,), "IsMoving": (12, 76, 204),
    "IsAttacking": (0x60, 0x440, 0x460), "IsIdle": (68, 64, 100),
}


@dataclass(frozen=True)
class FieldCase:
    """One ``Case`` of GwAu3's Switch that reads a single field.

    ``declared`` is the ctypes type at the resolved offset, and it is what decides whether the named
    attribute may answer the case: a dword case whose offset this project declares as an array must be
    read from the record's bytes, not handed back as the array.

    ``derived`` marks a case whose body reads into a ``Local`` and returns something *computed* from it
    -- GwAu3's ``VisibleEffectsNextNode`` masks the pointer with ``0xFFFFFFFE``. The parser takes the
    case's first ``Memory_Read``, so such a case cannot be answered by an attribute reader at all: the
    mask would be dropped and the raw pointer answered in its place.
    """

    keys: tuple[str, ...]
    line: int
    offset: int
    type_text: str
    attribute: str
    inner: str
    declared: object = None
    derived: bool = False


# ---------------------------------------------------------------------------------------------
# The generated table's surrounding text.
# ---------------------------------------------------------------------------------------------

TEMPLATE_HEAD = '''"""GwAu3's ``Agent_*`` reads, over the records this project already reads.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_data_agent.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

``Agent_GetAgentInfo`` is one ``Switch`` over {case_count} ``Case`` groups in GwAu3
(``GwAu3_Data_Agent.au3:82-524``). {named} of the {key_count} field keys resolve to a **named
attribute** of the record this project reads, chosen by offset against ctypes' own view of the
structure -- the authority ``docs/GWA3_AGENT_FIELD_AUDIT.md`` rests on. The reader for each key names
its attribute literally, so nothing here reaches a field through a dynamic name.

**The return shapes are GwAu3's, and they are kept:**

* an unknown field name answers ``0``, and an agent that cannot be resolved answers ``0`` -- AutoIt
  has no exceptions in this role and a script branches on the return;
* ``Agent_GetAgentInfo`` with no field name answers ``0`` (GwAu3's own guard,
  ``GwAu3_Data_Agent.au3:84``);
* the two id sentinels are ``-2`` for the controlled character and ``-1`` for the current target
  (``GwAu3_Data_Agent.au3:3-16``).
"""

from __future__ import annotations

import struct
from typing import Any

from .. import effect as _effect
from ..agent import Agent
from ..agent_array import AgentArray
from ..context.agent_array import AgentItemStruct, AgentLivingStruct
from ..player import Player

# ---------------------------------------------------------------------------------------------
# The field table. One entry per key GwAu3 accepts, generated from GwAu3's own offsets and resolved
# against this project's structure at generation time.
#
# It is **built after** the helpers below, not with them, because several keys dispatch to a helper
# function and a dict literal that names one before it is defined raises at import. The first
# generated version had the table first and did not import at all.
# ---------------------------------------------------------------------------------------------

_READERS: dict[str, Any] = {{}}

# Keys that refuse rather than answer, with the reason. A wrong value of the right type is the one
# failure a caller cannot detect, so a key this layer cannot answer says so instead.
_UNIMPLEMENTED: dict[str, str] = {unimplemented}
'''

TEMPLATE_BODY_END = '''

# The table itself, now that every helper it names exists.
_READERS.update(
    {
'''

TEMPLATE_AFTER_TABLE = '''    }
)
'''

TEMPLATE_BODY = '''

def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own -- this project materializes
    a record with ``from_buffer_copy`` -- so a field with no attribute name is read from those bytes at
    GwAu3's own offset and width. That covers the ``hXXXX`` fields, whose names in the port are
    placeholders precisely because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values


def _read_field_bytes(record: Any, offset: int, fmt: str) -> Any:
    """GwAu3's own read of a field: ``Memory_Read($l_p_AgentPtr + offset, type)``.

    **Why this exists, and it is a live finding with a measurement behind it (2026-10-10).** GwAu3 reads
    the client's memory at an offset and never consults the record's *type*; this layer answers from a
    materialized record, and the record it has for a gadget is 0xE4 bytes while GwAu3's ``Allegiance``
    offset is 0x1B5 -- so a read from the record's own bytes cannot answer what GwAu3 answers, and the
    first attempt at this fix raised ``struct.error`` where the reader it replaced raised
    ``AttributeError``.

    What *can* answer it is the read GwAu3 makes: the record carries the reader and the address it was
    materialized from (``bind_reader``), so this reads ``offset`` at that address -- the same bytes in
    the same process, which is the source's own mechanism rather than an approximation of it. The
    measured values are in ``tests/live_reports/agent_view_sizes.log``: a gadget at 0x1B5 answers ``194``
    live and cannot be read from its 228-byte copy at all.

    A record with no bound reader -- a materialized one, which is what the offline tests build -- falls
    back to its own bytes at the same offset, which is the same read when the buffer covers it. A buffer
    that does not cover it raises ``struct.error``: there is nothing to answer, and a number invented
    here would be a wrong value of exactly the right type.
    """

    reader = record._remote_reader
    address = record._remote_address
    if reader is not None and address:
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, reader.read(int(address) + offset, size))[0]
    return _read_raw(record, offset, fmt)


# ---------------------------------------------------------------------------------------------
# The comparison tables, GwAu3's own literals (`GwAu3_Data_Agent.au3:302-368`).
# ---------------------------------------------------------------------------------------------

_EFFECT_BITS: dict[str, int] = {effect_bits}

_TYPEMAP_BITS: dict[str, int] = {typemap_bits}

_MODEL_STATE_SETS: dict[str, tuple[int, ...]] = {model_state_sets}

# ``{{key: (offset, struct format)}}`` for every key whose case makes one scalar ``Memory_Read`` -- the
# same read GwAu3 makes. It is what the mask-and-compare keys fall back to for a record whose view
# does not declare the field they mask (``_read_type_words``).
_RAW_READERS: dict[str, tuple[int, str]] = {raw_readers}


# ---------------------------------------------------------------------------------------------
# The keys GwAu3 computes rather than reads. Each follows its own case, and cites its GwAu3 line.
# ---------------------------------------------------------------------------------------------


def _read_canpickup(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:186-190``: an item owned by nobody or by the controlled character.

    ``owner`` is an item/living field, so a record whose view does not carry it reads GwAu3's own bytes
    at GwAu3's own offset instead (see `_read_field_bytes`); ``type`` is on every view.
    """

    if isinstance(record, AgentItemStruct) or isinstance(record, AgentLivingStruct):
        owner = record.owner
    else:
        owner = _read_field_bytes(record, *_RAW_READERS["Owner"])

    if record.type != 0x400:
        return False
    if owner == 0 or owner == Agent_GetMyID():
        return True
    return False


def _read_currenthp(record: Any) -> float:
    """``GwAu3_Data_Agent.au3:256-257``: the HP fraction times the maximum.

    The two words are the record's own fields for a living record and GwAu3's own reads otherwise --
    ``0x134`` and ``0x138`` -- which is the same pair of reads either way.
    """

    if isinstance(record, AgentLivingStruct):
        return record.hp * record.max_hp
    return _read_field_bytes(record, *_RAW_READERS["CurrentHP"]) * _read_field_bytes(
        record, *_RAW_READERS["MaxHP"]
    )


def _read_currentenergy(record: Any) -> float:
    """``GwAu3_Data_Agent.au3:244-245``: the energy fraction times the maximum."""

    if isinstance(record, AgentLivingStruct):
        return record.energy * record.max_energy
    return _read_field_bytes(record, *_RAW_READERS["CurrentEnergy"]) * _read_field_bytes(
        record, *_RAW_READERS["MaxEnergy"]
    )


def _read_ismoving(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:334-337``: a non-zero move word, or one of three model states.

    **This one raised live** (``AttributeError: 'AgentGadgetStruct' object has no attribute
    'model_state'``) until the second live pass, because it read the living fields directly instead of
    through the rule the rest of the table follows. It now reads the same two words the way GwAu3 does.
    """

    if isinstance(record, AgentLivingStruct):
        move_x = record.velocity.x
        move_y = record.velocity.y
        model_state = record.model_state
    else:
        move_x = _read_field_bytes(record, *_RAW_READERS["MoveX"])
        move_y = _read_field_bytes(record, *_RAW_READERS["MoveY"])
        model_state = _read_field_bytes(record, *_RAW_READERS["ModelState"])

    if move_x != 0 or move_y != 0:
        return True
    return model_state in _MODEL_STATE_SETS["IsMoving"]


def _read_iscasting(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:341-344``: a non-zero skill word, or one of two model states."""

    if isinstance(record, AgentLivingStruct):
        skill = record.skill
        model_state = record.model_state
    else:
        skill = _read_field_bytes(record, *_RAW_READERS["Skill"])
        model_state = _read_field_bytes(record, *_RAW_READERS["ModelState"])

    if skill != 0:
        return True
    return model_state in (0x41, 0x245)


def _read_isitemtype(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:163-164``: the type word equals ``0x400``."""

    return record.type == 0x400


def _read_isgadgettype(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:165-166``: the type word equals ``0x200``."""

    return record.type == 0x200


def _read_islivingtype(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:167-168``: the type word equals ``0xDB``."""

    return record.type == 0xDB


def _read_isplayer(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:391-392``: a non-zero login number."""

    return record.login_number != 0


def _read_isnpc(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3:393-394``: a zero login number."""

    return record.login_number == 0


def _read_hasvisibleeffects(record: Any) -> bool:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why.

    GwAu3 counts the record's visible-effect linked list (`GwAu3_Data_Agent.au3:383-384`), which lives
    in the client's memory and is reachable only through a connection. A record materialized here has
    no target address, so the count cannot be taken, and `False` would be a wrong value of the right
    type -- undetectable by a caller. It raises, naming the capability it needs.
    """

    raise NotImplementedError(_UNIMPLEMENTED["HasVisibleEffects"])


def _read_effectcount(record: Any) -> int:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["EffectCount"])


def _read_bondcount(record: Any) -> int:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["BondCount"])


def _read_vtable(record: Any) -> int:
    """``GwAu3_Data_Agent.au3:87-88``: the record's vtable pointer.

    GwAu3 reads a pointer at ``+0x0``; this project's structure names that field ``vtable_ptr``.
    """

    return int(record.vtable_ptr)


def _read_visibleeffectsptr(record: Any) -> int:
    """``GwAu3_Data_Agent.au3:374-375``: the address of the record's visible-effect list.

    GwAu3 answers ``$l_p_AgentPtr + 0x174``. This project's structure names the field at that offset
    ``visible_effects_list``, so the address is the record's own plus that field's offset -- the same
    arithmetic, expressed against the name rather than a literal.
    """

    return int(record._remote_address or 0) + AgentLivingStruct.visible_effects_list.offset


def _read_visibleeffectcount(record: Any) -> int:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["VisibleEffectCount"])


def _read_visibleeffectsnextnode(record: Any) -> int:
    """``GwAu3_Data_Agent.au3:376-378``: the next link, with its low bit masked off.

    GwAu3 reads a pointer at ``+0x178`` into a local and returns ``BitAND($l_p_Next, 0xFFFFFFFE)``.
    This is a **derived** case, not a field read: the generator marks it and a hand-written reader
    answers it, because the attribute at that offset is the list structure -- and answering the
    structure, as the generated table did before the first live run, drops the mask and returns a
    pointer GwAu3 never returns. The read and the mask are the source's own two lines.
    """

    return _read_raw(record, 0x178, "<I") & 0xFFFFFFFE


def _read_name(record: Any) -> str:
    """``GwAu3_Data_Agent.au3:423-518``: the agent's name.

    GwAu3 resolves the name itself, by type, through its own encoded-string decoder: players from the
    world's player array, NPCs from the agent-info then NPC array, gadgets from the summary info, and
    items through ``Item_GetItemInfoByItemID``. **This delegates instead**, to ``Agent.GetNameByID``
    (``py4gw/agent.py:577``), which is this project's own name path and already handles all four cases
    and the decoding. The two are not proven identical for every agent type, so a caller comparing
    names should treat this as the port's name and not GwAu3's.

    An agent whose name cannot be resolved answers ``""``, GwAu3's own fallback
    (``GwAu3_Data_Agent.au3:517``).
    """

    return str(Agent.GetNameByID(int(record.agent_id)) or "")


def _read_hasbond(record: Any) -> bool:
    """GwAu3's ``Agent_GetAgentBondInfo`` answers ``True`` for ``HasBond`` once a bond matched
    (``GwAu3_Data_Agent.au3:952-953``). Reaching that key through ``Agent_GetAgentInfo`` cannot match
    one, because this accessor takes no skill id -- so it answers ``False``, and says why.
    """

    return False


def _read_type_words(record: Any, key: str) -> bool:
    """The mask-and-compare keys in one place: the effect word, the type map, or the model state.

    Each table is GwAu3's own set of literals, and the comparison is the one its case makes --
    ``IsCrippled`` tests *both* of its bits while its neighbours test any.

    **The word is read the way GwAu3 reads it when the record's view does not declare the field.**
    ``model_state``, ``type_map`` and ``effects`` are living-record fields, and GwAu3 asks these
    questions of *every* agent in its cache -- a gadget answers the bytes at its own offset rather than
    raising. ``_RAW_READERS`` carries that offset and width per key, from the ``Memory_Read`` its own
    case makes, so the same word is masked either way. (Found by the live suite's pass over every agent
    in the array, 2026-10-10; see `Agent_GetAgentPtr` for the other half of the same finding.)
    """

    living = isinstance(record, AgentLivingStruct)

    if key in _MODEL_STATE_SETS:
        word = record.model_state if living else _read_field_bytes(record, *_RAW_READERS[key])
        return word in _MODEL_STATE_SETS[key]
    if key in _TYPEMAP_BITS:
        word = record.type_map if living else _read_field_bytes(record, *_RAW_READERS[key])
        return bool(word & _TYPEMAP_BITS[key])
    if key in _EFFECT_BITS:
        bits = _EFFECT_BITS[key]
        word = int(record.effects) if living else int(_read_field_bytes(record, *_RAW_READERS[key]))
        return (word & bits) == bits
    return False


'''

TEMPLATE_ACCESSORS = '''def Agent_ConvertID(agent_id: Any) -> int:
    """Resolve GwAu3's id forms to an agent id (``GwAu3_Data_Agent.au3:3-16``).

    GwAu3's chain, in its own order: ``-2`` is the controlled character, ``-1`` is the current
    target, a pointer is dereferenced at ``+0x2C`` (the id field), and anything else is returned as
    given. The pointer and ``DllStruct`` arms cannot arise for a caller of this module -- they are
    AutoIt's own handle types, and a Python caller passes an id -- so they are not reproduced; the two
    sentinels are, because a migrating script uses them everywhere.
    """

    if agent_id == -2:
        return Agent_GetMyID()
    if agent_id == -1:
        return Agent_GetCurrentTarget()
    return int(agent_id)


def Agent_GetMyID() -> int:
    """The controlled character's agent id (``GwAu3_Data_Agent.au3:26-28``)."""

    return int(Player.GetAgentID())


def GetMyID() -> int:
    """A second spelling of :func:`Agent_GetMyID` in GwAu3 (``GwAu3_Data_Agent.au3:30-34``).

    Its own implementation walks ``BasePointer -> 0x18 -> 0x2C -> 0x680 -> 0x14``; it is the same id
    by the same path this project's ``Player.GetAgentID`` takes.
    """

    return Agent_GetMyID()


def Agent_GetCurrentTarget() -> int:
    """The agent the client currently has targeted (``GwAu3_Data_Agent.au3:36-38``).

    Read from the target the client itself announced, which the connection captures
    (``py4gw/client.py:616-631``) -- not from a value this module keeps.
    """

    return int(Player.GetTargetID())


def Agent_GetAgentPtr(agent_id: Any = -2) -> Any:
    """The agent's record (``GwAu3_Data_Agent.au3:74-79``).

    **The shape differs and the difference is deliberate.** GwAu3 answers a raw client pointer; this
    answers the materialized record this project reads, because a client address is of no use to a
    caller here. A GwAu3 script that passes the result straight back into another ``Agent_*`` function
    is passing an id, and that keeps working -- every accessor takes the sentinel forms and resolves
    them itself.

    **The record is the agent type's own, and that was wrong until the first live run (2026-10-09).**
    GwAu3's cases read the *living* record's fields -- ``hp``, ``level``, ``type_map``, ``effects``,
    ``allegiance`` -- and this table's offsets were resolved against ``AgentLivingStruct``. The array
    hands out a bare ``AgentStruct``, which carries none of them, so every living key raised
    ``AttributeError`` against the live client while passing offline (the offline test served a
    hand-built ``AgentLivingStruct``). The record is now converted the way this project's own typed
    accessors convert it -- ``Agent.GetLivingAgentByID``, ``Agent.GetItemAgentByID`` and
    ``Agent.GetGadgetAgentByID`` all resolve the base record and then take their type's view -- in the
    order the agent cache itself uses: gadget, then item, then living.
    """

    resolved = Agent_ConvertID(agent_id)
    if resolved == 0:
        return None

    record = AgentArray.GetAgentByID(resolved)
    if record is None:
        return None
    if record.is_gadget_type:
        return record.GetAsAgentGadget()
    if record.is_item_type:
        return record.GetAsAgentItem()
    if record.is_living_type:
        return record.GetAsAgentLiving()
    return record


def Agent_GetMaxAgents() -> int:
    """**Shape differs, and this one is not settled.** GwAu3 reads the agent array's *capacity* from a
    client global (``GwAu3_Data_Agent.au3:22-24``); this project reads the ids the array holds
    (:meth:`py4gw.agent_array.AgentArray.GetAgentArray`).

    A migrating script loops ``For $i = 1 To Agent_GetMaxAgents() - 1`` to walk every agent slot, and
    GwAu3's own comment records that the bound is *exclusive* because the manager refuses an id at or
    above it (``GwAu3_Cmd_Agent.au3:41-42``). Returning the count of populated slots here changes that
    loop's bounds silently. **Until the capacity is read, this returns the number of ids the array
    holds** -- it does not pretend to be the client's capacity.
    """

    return len(AgentArray.GetAgentArray())


def Agent_GetAgentInfo(agent_id: Any = -2, info: str = "") -> Any:
    """One field of an agent, by GwAu3's field name (``GwAu3_Data_Agent.au3:82-524``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and an
    agent the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.
    """

    if info == "":
        return 0

    record = Agent_GetAgentPtr(agent_id)
    if record is None:
        return 0

    reader = _READERS.get(info)
    if reader is None:
        return 0
    return reader(record)


def Agent_GetDistanceSq(agent1_id: Any, agent2_id: Any = -2) -> float:
    """The squared distance between two agents (``GwAu3_Data_Agent.au3:821-831``).

    GwAu3's own arithmetic over ``X``/``Y``; this project has no member for it, so the sum is written
    the way the source writes it.
    """

    dx = Agent_GetAgentInfo(agent1_id, "X") - Agent_GetAgentInfo(agent2_id, "X")
    dy = Agent_GetAgentInfo(agent1_id, "Y") - Agent_GetAgentInfo(agent2_id, "Y")
    return dx * dx + dy * dy


def Agent_GetDistance(agent1_id: Any, agent2_id: Any = -2) -> float:
    """The distance between two agents (``GwAu3_Data_Agent.au3:805-815``)."""

    return Agent_GetDistanceSq(agent1_id, agent2_id) ** 0.5


def Agent_GetDistanceToXY(x: float, y: float, agent_id: Any = -2) -> float:
    """The distance from an agent to a point (``GwAu3_Data_Agent.au3:817-819``)."""

    dx = x - Agent_GetAgentInfo(agent_id, "X")
    dy = y - Agent_GetAgentInfo(agent_id, "Y")
    return (dx * dx + dy * dy) ** 0.5


__all__ = [
    "Agent_ConvertID",
    "Agent_GetAgentArray",
    "Agent_GetAgentBondInfo",
    "Agent_GetAgentEffectArrayInfo",
    "Agent_GetAgentEffectInfo",
    "Agent_GetAgentInfo",
    "Agent_GetAgentPtr",
    "Agent_GetBestTarget",
    "Agent_GetCurrentTarget",
    "Agent_GetDistance",
    "Agent_GetDistanceSq",
    "Agent_GetDistanceToXY",
    "Agent_GetMaxAgents",
    "Agent_GetMyID",
    "Agent_GetNpcInfo",
    "Agent_GetPlayerInfo",
    "GetMyID",
    "VisibleEffect_Count",
    "VisibleEffect_FindByID",
    "VisibleEffect_GetAll",
]
'''


def _load_offsets() -> dict[int, tuple[str, str, object]]:
    """``{absolute offset: (attribute, component, declared type)}`` for the record this project reads.

    **The nested members go in first, and that ordering is the whole point.** A nested structure's
    first member shares the structure's own offset -- ``pos.x`` and ``pos`` are both at 0x74, and
    ``velocity.x`` with ``velocity`` at 0xA0 -- and GwAu3 never asks for the bare structure: it asks
    for ``X`` and ``Y``, and for ``MoveX`` and ``MoveY``. Registering the structures first made ``X``
    answer a whole ``GamePos`` where GwAu3 answers a float: a wrong value of the right type, which is
    the worst kind. So a member claims the offset, and the bare structure is reachable only where none
    of its members occupies it.

    **The fields are gathered across the whole MRO.** ``AgentLivingStruct`` declares only its own from
    ``owner`` (0xC4) onwards; ``pos`` and ``terrain_normal`` are on ``AgentStruct``. The nested types
    come from ``_fields_``, because a descriptor's ``_type_`` is ``None`` on these structures.

    **The declared type comes back with the name**, because a name is not enough to answer a case: the
    first live run found ``h000C`` answering a ``c_ulong * 2`` where GwAu3 reads a dword, and
    ``VisibleEffectsPrevLink``'s offset declared as a ``GWListStruct``.
    """

    from py4gw.context import agent_array

    structure = agent_array.AgentLivingStruct
    mapping: dict[int, tuple[str, str, object]] = {}

    declared: list[tuple[str, object]] = []
    for cls in structure.__mro__:
        for name, declared_type in getattr(cls, "_fields_", None) or []:
            descriptor = getattr(structure, name, None)
            if isinstance(getattr(descriptor, "offset", None), int):
                declared.append((name, declared_type))

    for name, declared_type in declared:
        offset = getattr(getattr(structure, name), "offset")
        for inner_name, inner_type in getattr(declared_type, "_fields_", None) or []:
            inner_offset = getattr(getattr(declared_type, inner_name), "offset", None)
            if isinstance(inner_offset, int):
                mapping[offset + inner_offset] = (name, inner_name, inner_type)

    for name, declared_type in declared:
        offset = getattr(getattr(structure, name), "offset")
        mapping.setdefault(offset, (name, "", declared_type))
    return mapping


def parse_cases() -> list[FieldCase]:
    """Every ``Case`` of ``Agent_GetAgentInfo`` that reads one field, with its offset and width."""

    lines = GWAU3_AGENT_SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("Func Agent_GetAgentInfo(")
    )
    end = next(index for index in range(start, len(lines)) if lines[index].strip() == "EndFunc")

    offsets = _load_offsets()
    cases: list[FieldCase] = []
    pending: tuple[tuple[str, ...], int] | None = None

    for index in range(start, end):
        line = lines[index]
        match = CASE_LINE.match(line)
        if match and not line.strip().startswith("Case Else"):
            keys = tuple(KEY.findall(match.group("keys")))
            if keys:
                pending = (keys, index + 1)
                continue
        if pending is None:
            continue
        read = MEMORY_READ.search(line)
        if read is None:
            continue
        offset = int(read.group("offset"), 16)
        attribute, inner, declared_type = offsets.get(offset, ("", "", None))
        # The parser takes the case's first `Memory_Read`, and for a **derived** case that read is a
        # `Local ... = Memory_Read(...)` whose value is then computed into the `Return`
        # (`VisibleEffectsNextNode` masks the pointer's low bit). A case whose matched line is a `Local`
        # therefore cannot be answered by the field at its offset -- the mask would be dropped -- so it
        # is marked, and a hand-written reader must answer it.
        derived = line.strip().startswith("Local")
        cases.append(
            FieldCase(
                keys=pending[0],
                line=pending[1],
                offset=offset,
                type_text=read.group("type"),
                attribute=attribute,
                inner=inner,
                declared=declared_type,
                derived=derived,
            )
        )
        pending = None
    return cases


def _attribute_on_base_struct(attribute: str) -> bool:
    """Whether the record's **base** type declares the attribute, so every view of a record carries it."""

    from py4gw.context import agent_array

    root = attribute.split(".", 1)[0]
    return any(name == root for name, _ in agent_array.AgentStruct._fields_)


def _attribute_reader(reference: str, case: FieldCase) -> str:
    """``lambda record: record.<field>``, with GwAu3's own bytes behind it for a record that lacks it.

    **The second live finding (2026-10-10), and it is the first one's other half.** The table is a
    ``Switch`` over *living* fields resolved against ``AgentLivingStruct``, and `Agent_GetAgentPtr`
    answers each agent's own view -- an ``AgentGadgetStruct`` for a gadget, an ``AgentItemStruct`` for an
    item. ``AgentGadgetStruct`` has no ``allegiance``, so a question the source answers for *every* row
    of its cache raised instead: the live suite's first pass over every agent in the array (the UtilityAI
    targeting queries) hit ``AttributeError: 'AgentGadgetStruct' object has no attribute 'allegiance'``.

    GwAu3 reads the bytes at its own offset and never consults the record's type, so that is what the
    reader does when the view does not declare the field: the same ``Memory_Read(ptr + offset, type)``
    as ``_read_raw``, over the same record. A field the **base** ``AgentStruct`` declares needs no
    fallback -- every view inherits it -- and one it does not is a living field, which is why the test
    is against the living view by name. Nothing here reaches a field through a dynamic name: the
    attribute is spelled literally, and the type in the test is the record's own class.
    """

    if _attribute_on_base_struct(case.attribute):
        return f"lambda record: {reference}"
    return (
        f"lambda record: {reference} if isinstance(record, AgentLivingStruct) "
        f'else _read_field_bytes(record, {case.offset:#06x}, "<{WIDTHS[case.type_text]}")'
    )


def _reader_expression(case: FieldCase, key: str) -> str:
    """The reader a key gets, named literally so no field is reached through a dynamic name.

    **Three cases cannot be answered by the attribute at the offset**, and each of the three was found
    by the first live run rather than by reading:

    * the case reads several words (``byte[4]``) -- the array branch below, which answers a tuple;
    * the case reads one word and this project declares the offset as an **array or a structure**
      (``h000C`` is a ``c_ulong * 2`` where GwAu3 reads a dword), so the bytes are read at GwAu3's own
      offset and width instead of handing back the aggregate;
    * the case **derives** its answer from the read, which an attribute cannot express
      (``VisibleEffectsNextNode`` masks the pointer's low bit off), so a hand-written reader answers,
      and if none exists the key refuses rather than answers the raw pointer.
    """

    if key in HAND_WRITTEN or key in UNIMPLEMENTED_KEYS:
        return f"_read_{key.lower()}"
    if key in COMPUTED_KEYS or key in TYPE_WORD_KEYS or key in BOOLEAN_KEYS:
        return f"_read_{key.lower()}"
    if case.derived:
        return f"_read_{key.lower()}"

    array = ARRAY_WIDTH.match(case.type_text)
    if array:
        base, count = array.group("type"), int(array.group("count"))
        if case.attribute and not case.inner:
            return f"lambda record: tuple(record.{case.attribute})"
        return f'lambda record: _read_field_bytes(record, {case.offset:#06x}, "<{count}{WIDTHS[base]}")'

    if case.attribute and case.inner:
        return _attribute_reader(f"record.{case.attribute}.{case.inner}", case)
    if case.attribute and not _is_aggregate(case.declared):
        return _attribute_reader(f"record.{case.attribute}", case)
    return f'lambda record: _read_field_bytes(record, {case.offset:#06x}, "<{WIDTHS[case.type_text]}")'


def _is_aggregate(declared_type: object) -> bool:
    """Whether a declared ctypes type is a container rather than one value."""

    import ctypes

    if not isinstance(declared_type, type):
        return False
    return issubclass(declared_type, (ctypes.Array, ctypes.Structure, ctypes.Union))


def _helper_stubs(defined: set[str]) -> str:
    """A function for every ``_read_<key>`` the readers reference and the template does not define.

    Derived by diffing what the table needs against what the template defines, rather than by
    re-listing the keys. Two earlier attempts got this wrong in different ways -- lowercasing a key
    produced names that were never defined, and listing helpers from one table left keys in another
    with none -- and each time the generated module failed to import. A diff cannot drift.
    """

    needed = {f"_read_{key.lower()}": key for key in (*COMPUTED_KEYS, *TYPE_WORD_KEYS, *BOOLEAN_KEYS)}
    return "".join(
        f'def _read_{helper.removeprefix("_read_")}(record: Any) -> bool:\n'
        f'    """``GwAu3_Data_Agent.au3`` -- the ``{key}`` case."""\n\n'
        f'    return _read_type_words(record, "{key}")\n\n\n'
        for helper, key in sorted(needed.items())
        if helper not in defined
    )


def _raw_readers(by_key: dict[str, FieldCase]) -> dict[str, tuple[int, str]]:
    """``{key: (offset, struct format)}`` for every key whose case makes one scalar ``Memory_Read``.

    These are GwAu3's own offsets and widths, taken from the same parse that fills the reader table, and
    they are what a key falls back to when the record's view does not declare the field it names -- for
    an attribute reader (``_attribute_reader``) and for the mask-and-compare keys
    (``_read_type_words``) alike. A key with no single scalar read behind it (a hand-written reader, an
    array case, a case whose read the parser could not resolve) is absent, and a key that is absent
    re-raises rather than answering something invented.
    """

    readers: dict[str, tuple[int, str]] = {}
    for key, case in by_key.items():
        if not case.offset:
            continue
        if ARRAY_WIDTH.match(case.type_text):
            continue
        width = WIDTHS.get(case.type_text)
        if width is None:
            continue
        readers[key] = (case.offset, f"<{width}")
    return readers


def _snippets() -> str:
    """The hand-written source this module carries, in the order :data:`HELPER_FILES` names it."""

    parts = []
    for name in HELPER_FILES:
        text = (SNIPPETS_DIR / name).read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        parts.append(text)
    return "".join(parts)


# Where the snippet block goes: immediately before the module's own ``__all__``, which is the end of
# the generated body. The marker is the start of that block, and a template without it is a bug.
_SNIPPET_MARKER = "\n\n__all__ = [\n"


def render(cases: list[FieldCase]) -> str:
    # The table carries every key GwAu3 declares, including the hand-written ones: a key that is in
    # the source and absent from the table is a hole a caller falls into, and `_READERS` is what makes
    # the surface complete. Only the six the parser cannot see are added separately, because no `Case`
    # expresses them as a field read.
    by_key: dict[str, FieldCase] = {}
    for case in cases:
        for key in case.keys:
            by_key[key] = case
    for key in HAND_WRITTEN:
        by_key.setdefault(key, FieldCase(keys=(key,), line=0, offset=0, type_text="", attribute="", inner=""))

    defined = set(re.findall(r"^def (_read_\w+)", TEMPLATE_BODY, re.MULTILINE))
    named = sum(1 for case in by_key.values() if case.attribute)

    parts = [
        TEMPLATE_HEAD.format(
            case_count=len(cases),
            named=named,
            key_count=len(by_key),
            unimplemented=repr(UNIMPLEMENTED_KEYS),
        ),
        TEMPLATE_BODY.format(
            effect_bits=repr(EFFECT_BITS),
            typemap_bits=repr(TYPEMAP_BITS),
            model_state_sets=repr(MODEL_STATE_SETS),
            raw_readers=repr(_raw_readers(by_key)),
        ),
        _helper_stubs(defined),
        TEMPLATE_BODY_END,
    ]
    for key in sorted(by_key):
        parts.append(f'        "{key}": {_reader_expression(by_key[key], key)},\n')
    parts.append(TEMPLATE_AFTER_TABLE)
    accessors, marker, all_block = TEMPLATE_ACCESSORS.partition(_SNIPPET_MARKER)
    if not marker:
        raise AssertionError("TEMPLATE_ACCESSORS no longer contains the __all__ marker")
    parts.append(accessors)
    parts.append(_snippets())
    parts.append(marker + all_block)
    return "".join(parts)


def main() -> int:
    cases = parse_cases()
    keys = {key for case in cases for key in case.keys if key not in HAND_WRITTEN}
    named = sum(1 for case in cases if case.attribute)
    OUTPUT_PATH.write_text(render(cases), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  case groups: {len(cases)}   table keys: {len(keys)}")
    print(f"  case groups resolved to a named attribute: {named} of {len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
