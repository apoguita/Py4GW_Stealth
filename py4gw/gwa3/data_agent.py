"""GwAu3's ``Agent_*`` reads, over the records this project already reads.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_data_agent.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

``Agent_GetAgentInfo`` is one ``Switch`` over 132 ``Case`` groups in GwAu3
(``GwAu3_Data_Agent.au3:82-524``). 136 of the 143 field keys resolve to a **named
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

_READERS: dict[str, Any] = {}

# Keys that refuse rather than answer, with the reason. A wrong value of the right type is the one
# failure a caller cannot detect, so a key this layer cannot answer says so instead.
_UNIMPLEMENTED: dict[str, str] = {'EffectCount': "GwAu3_Data_Agent.au3:261-279 counts the agent's effects by walking the global agent-effects array through BasePointer[0x18][0x2C][0x508]. That walk needs the connection (py4gw/context); a materialized record carries no target address. Answering 0 here would be a wrong value a caller could not detect, so it refuses instead.", 'BondCount': "GwAu3_Data_Agent.au3:280-299 counts the agent's bonds from the same global array (BasePointer[0x18][0x2C][0x508], bond sub-array at +0x4), and its BondArraySize is the same read pattern as `Agent_GetAgentEffectArrayInfo` (GwAu3_Data_Agent.au3:834-865). That walk needs the connection (py4gw/context) and a materialized record carries no target address. Same gap as EffectCount, same refusal.", 'HasVisibleEffects': "GwAu3_Data_Agent.au3:383-384 counts the record's visible-effect linked list, which this project reads through a RemoteGWListView bound to the target address (py4gw/context/agent_array.py:935-948). A materialized record has no target address, so the walk cannot be made; this one refuses rather than answer a wrong boolean.", 'VisibleEffectCount': "GwAu3_Data_Agent.au3:381-382 answers `VisibleEffect_Count`, which walks the same linked list (GwAu3_Data_Agent.au3:1143-1159). This project's `GWListStruct` (py4gw/context/gw_list.py:28-33) holds only an offset and a sentinel link -- it carries no count, so the list has to be walked through the connection (py4gw/context/agent_array.py:935-948). A materialized record has no target address, so it refuses rather than answer 0, which would be a wrong value a caller could not detect."}


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

_EFFECT_BITS: dict[str, int] = {'IsBleeding': 1, 'IsConditioned': 2, 'IsCrippled': 10, 'IsDead': 16, 'IsDeepWounded': 32, 'IsPoisoned': 64, 'IsEnchanted': 128, 'IsDegenHexed': 1024, 'IsHexed': 2048, 'IsWeaponSpelled': 32768}

_TYPEMAP_BITS: dict[str, int] = {'InCombatStance': 1, 'HasQuest': 2, 'IsDeadByTypeMap': 8, 'IsFemale': 512, 'HasBossGlow': 1024, 'IsHidingCap': 4096, 'CanBeViewedInPartyWindow': 131072, 'IsSpawned': 262144, 'IsBeingObserved': 4194304}

_MODEL_STATE_SETS: dict[str, tuple[int, ...]] = {'IsKnockedDown': (1104,), 'IsKnocked': (1104,), 'IsMoving': (12, 76, 204), 'IsAttacking': (96, 1088, 1120), 'IsIdle': (68, 64, 100)}

# ``{key: (offset, struct format)}`` for every key whose case makes one scalar ``Memory_Read`` -- the
# same read GwAu3 makes. It is what the mask-and-compare keys fall back to for a record whose view
# does not declare the field they mask (``_read_type_words``).
_RAW_READERS: dict[str, tuple[int, str]] = {'h0004': (4, '<I'), 'h0008': (8, '<I'), 'h000C': (12, '<I'), 'h0010': (16, '<I'), 'Timer': (20, '<I'), 'Timer2': (24, '<I'), 'ID': (44, '<i'), 'Z': (48, '<f'), 'Width1': (52, '<f'), 'Height1': (56, '<f'), 'Width2': (60, '<f'), 'Height2': (64, '<f'), 'Width3': (68, '<f'), 'Height3': (72, '<f'), 'Rotation': (76, '<f'), 'RotationCos': (80, '<f'), 'RotationSin': (84, '<f'), 'NameProperties': (88, '<I'), 'Ground': (92, '<I'), 'h0060': (96, '<I'), 'TerrainNormalX': (100, '<f'), 'TerrainNormalY': (104, '<f'), 'TerrainNormalZ': (108, '<I'), 'X': (116, '<f'), 'Y': (120, '<f'), 'Plane': (124, '<I'), 'NameTagX': (132, '<f'), 'NameTagY': (136, '<f'), 'NameTagZ': (140, '<f'), 'VisualEffects': (144, '<h'), 'h0092': (146, '<h'), 'Type': (156, '<i'), 'IsItemType': (156, '<i'), 'IsGadgetType': (156, '<i'), 'IsLivingType': (156, '<i'), 'MoveX': (160, '<f'), 'MoveY': (164, '<f'), 'h00A8': (168, '<I'), 'RotationCos2': (172, '<f'), 'RotationSin2': (176, '<f'), 'Owner': (196, '<i'), 'CanPickUp': (156, '<i'), 'ItemID': (200, '<I'), 'ExtraType': (204, '<I'), 'GadgetID': (208, '<I'), 'AnimationType': (224, '<f'), 'AttackSpeed': (236, '<f'), 'AttackSpeedModifier': (240, '<f'), 'PlayerNumber': (244, '<h'), 'ModelID': (244, '<h'), 'AgentModelType': (246, '<h'), 'TransmogNpcId': (248, '<I'), 'Equipment': (252, '<I'), 'h0100': (256, '<I'), 'h0104_new': (260, '<I'), 'Tags': (264, '<I'), 'h010C': (268, '<h'), 'Primary': (270, '<B'), 'Secondary': (271, '<B'), 'Level': (272, '<B'), 'Team': (273, '<B'), 'h0114': (276, '<I'), 'EnergyPips': (280, '<f'), 'EnergyRegen': (280, '<f'), 'Overcast': (284, '<f'), 'EnergyPercent': (288, '<f'), 'MaxEnergy': (292, '<I'), 'CurrentEnergy': (288, '<f'), 'h0128': (296, '<I'), 'HPPips': (300, '<f'), 'HPRegen': (300, '<f'), 'h0130': (304, '<I'), 'HP': (308, '<f'), 'HPPercent': (308, '<f'), 'MaxHP': (312, '<I'), 'CurrentHP': (308, '<f'), 'Effects': (316, '<I'), 'IsBleeding': (316, '<I'), 'IsConditioned': (316, '<I'), 'IsCrippled': (316, '<I'), 'IsDead': (316, '<I'), 'IsDeepWounded': (316, '<I'), 'IsPoisoned': (316, '<I'), 'IsEnchanted': (316, '<I'), 'IsDegenHexed': (316, '<I'), 'IsHexed': (316, '<I'), 'IsWeaponSpelled': (316, '<I'), 'h0140': (320, '<I'), 'Hex': (324, '<B'), 'ModelState': (344, '<I'), 'IsKnockedDown': (344, '<I'), 'IsKnocked': (344, '<I'), 'IsMoving': (160, '<f'), 'IsAttacking': (344, '<I'), 'IsCasting': (440, '<h'), 'IsIdle': (344, '<I'), 'TypeMap': (348, '<I'), 'InCombatStance': (348, '<I'), 'HasQuest': (348, '<I'), 'IsDeadByTypeMap': (348, '<I'), 'IsFemale': (348, '<I'), 'HasBossGlow': (348, '<I'), 'IsHidingCap': (348, '<I'), 'CanBeViewedInPartyWindow': (348, '<I'), 'IsSpawned': (348, '<I'), 'IsBeingObserved': (348, '<I'), 'InSpiritRange': (368, '<I'), 'VisibleEffectsPrevLink': (372, '<I'), 'VisibleEffectsNextNode': (376, '<I'), 'h0180': (384, '<I'), 'LoginNumber': (388, '<I'), 'IsPlayer': (388, '<I'), 'IsNPC': (388, '<I'), 'AnimationSpeed': (392, '<f'), 'AnimationCode': (396, '<I'), 'AnimationId': (400, '<I'), 'LastStrike': (436, '<B'), 'Allegiance': (437, '<B'), 'WeaponType': (438, '<h'), 'Skill': (440, '<h'), 'h01BA': (442, '<h'), 'WeaponItemType': (444, '<B'), 'OffhandItemType': (445, '<B'), 'WeaponItemId': (446, '<h'), 'OffhandItemId': (448, '<h'), 'Name': (156, '<i')}


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


def _read_canbeviewedinpartywindow(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``CanBeViewedInPartyWindow`` case."""

    return _read_type_words(record, "CanBeViewedInPartyWindow")


def _read_hasbossglow(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``HasBossGlow`` case."""

    return _read_type_words(record, "HasBossGlow")


def _read_hasquest(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``HasQuest`` case."""

    return _read_type_words(record, "HasQuest")


def _read_incombatstance(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``InCombatStance`` case."""

    return _read_type_words(record, "InCombatStance")


def _read_isattacking(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsAttacking`` case."""

    return _read_type_words(record, "IsAttacking")


def _read_isbeingobserved(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsBeingObserved`` case."""

    return _read_type_words(record, "IsBeingObserved")


def _read_isbleeding(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsBleeding`` case."""

    return _read_type_words(record, "IsBleeding")


def _read_isconditioned(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsConditioned`` case."""

    return _read_type_words(record, "IsConditioned")


def _read_iscrippled(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsCrippled`` case."""

    return _read_type_words(record, "IsCrippled")


def _read_isdead(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsDead`` case."""

    return _read_type_words(record, "IsDead")


def _read_isdeadbytypemap(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsDeadByTypeMap`` case."""

    return _read_type_words(record, "IsDeadByTypeMap")


def _read_isdeepwounded(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsDeepWounded`` case."""

    return _read_type_words(record, "IsDeepWounded")


def _read_isdegenhexed(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsDegenHexed`` case."""

    return _read_type_words(record, "IsDegenHexed")


def _read_isenchanted(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsEnchanted`` case."""

    return _read_type_words(record, "IsEnchanted")


def _read_isfemale(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsFemale`` case."""

    return _read_type_words(record, "IsFemale")


def _read_ishexed(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsHexed`` case."""

    return _read_type_words(record, "IsHexed")


def _read_ishidingcap(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsHidingCap`` case."""

    return _read_type_words(record, "IsHidingCap")


def _read_isidle(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsIdle`` case."""

    return _read_type_words(record, "IsIdle")


def _read_isknocked(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsKnocked`` case."""

    return _read_type_words(record, "IsKnocked")


def _read_isknockeddown(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsKnockedDown`` case."""

    return _read_type_words(record, "IsKnockedDown")


def _read_ispoisoned(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsPoisoned`` case."""

    return _read_type_words(record, "IsPoisoned")


def _read_isspawned(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsSpawned`` case."""

    return _read_type_words(record, "IsSpawned")


def _read_isweaponspelled(record: Any) -> bool:
    """``GwAu3_Data_Agent.au3`` -- the ``IsWeaponSpelled`` case."""

    return _read_type_words(record, "IsWeaponSpelled")




# The table itself, now that every helper it names exists.
_READERS.update(
    {
        "AgentModelType": lambda record: record.agent_model_type if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00f6, "<h"),
        "Allegiance": lambda record: record.allegiance if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01b5, "<B"),
        "AnimationCode": lambda record: record.animation_code if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x018c, "<I"),
        "AnimationId": lambda record: record.animation_id if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0190, "<I"),
        "AnimationSpeed": lambda record: record.animation_speed if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0188, "<f"),
        "AnimationType": lambda record: record.animation_type if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00e0, "<f"),
        "AttackSpeed": lambda record: record.weapon_attack_speed if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00ec, "<f"),
        "AttackSpeedModifier": lambda record: record.attack_speed_modifier if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00f0, "<f"),
        "BondCount": _read_bondcount,
        "CanBeViewedInPartyWindow": _read_canbeviewedinpartywindow,
        "CanPickUp": _read_canpickup,
        "CurrentEnergy": _read_currentenergy,
        "CurrentHP": _read_currenthp,
        "EffectCount": _read_effectcount,
        "Effects": lambda record: record.effects if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x013c, "<I"),
        "EnergyPercent": lambda record: record.energy if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0120, "<f"),
        "EnergyPips": lambda record: record.energy_regen if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0118, "<f"),
        "EnergyRegen": lambda record: record.energy_regen if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0118, "<f"),
        "Equipment": lambda record: record.equipment_ptr_ptr if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00fc, "<I"),
        "ExtraType": lambda record: record.h00CC if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00cc, "<I"),
        "GadgetID": lambda record: record.h00D0 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00d0, "<I"),
        "Ground": lambda record: record.ground,
        "HP": lambda record: record.hp if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0134, "<f"),
        "HPPercent": lambda record: record.hp if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0134, "<f"),
        "HPPips": lambda record: record.hp_pips if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x012c, "<f"),
        "HPRegen": lambda record: record.hp_pips if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x012c, "<f"),
        "HasBossGlow": _read_hasbossglow,
        "HasQuest": _read_hasquest,
        "HasVisibleEffects": _read_hasvisibleeffects,
        "Height1": lambda record: record.height1,
        "Height2": lambda record: record.height2,
        "Height3": lambda record: record.height3,
        "Hex": lambda record: record.hex if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0144, "<B"),
        "ID": lambda record: record.agent_id,
        "InCombatStance": _read_incombatstance,
        "InSpiritRange": lambda record: record.in_spirit_range if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0170, "<I"),
        "IsAttacking": _read_isattacking,
        "IsBeingObserved": _read_isbeingobserved,
        "IsBleeding": _read_isbleeding,
        "IsCasting": _read_iscasting,
        "IsConditioned": _read_isconditioned,
        "IsCrippled": _read_iscrippled,
        "IsDead": _read_isdead,
        "IsDeadByTypeMap": _read_isdeadbytypemap,
        "IsDeepWounded": _read_isdeepwounded,
        "IsDegenHexed": _read_isdegenhexed,
        "IsEnchanted": _read_isenchanted,
        "IsFemale": _read_isfemale,
        "IsGadgetType": _read_isgadgettype,
        "IsHexed": _read_ishexed,
        "IsHidingCap": _read_ishidingcap,
        "IsIdle": _read_isidle,
        "IsItemType": _read_isitemtype,
        "IsKnocked": _read_isknocked,
        "IsKnockedDown": _read_isknockeddown,
        "IsLivingType": _read_islivingtype,
        "IsMoving": _read_ismoving,
        "IsNPC": _read_isnpc,
        "IsPlayer": _read_isplayer,
        "IsPoisoned": _read_ispoisoned,
        "IsSpawned": _read_isspawned,
        "IsWeaponSpelled": _read_isweaponspelled,
        "ItemID": lambda record: record.h00C8 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00c8, "<I"),
        "LastStrike": lambda record: record.dagger_status if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01b4, "<B"),
        "Level": lambda record: record.level if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0110, "<B"),
        "LoginNumber": lambda record: record.login_number if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0184, "<I"),
        "MaxEnergy": lambda record: record.max_energy if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0124, "<I"),
        "MaxHP": lambda record: record.max_hp if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0138, "<I"),
        "ModelID": lambda record: record.player_number if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00f4, "<h"),
        "ModelState": lambda record: record.model_state if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0158, "<I"),
        "MoveX": lambda record: record.velocity.x,
        "MoveY": lambda record: record.velocity.y,
        "Name": _read_name,
        "NameProperties": lambda record: record.name_properties,
        "NameTagX": lambda record: record.name_tag_x,
        "NameTagY": lambda record: record.name_tag_y,
        "NameTagZ": lambda record: record.name_tag_z,
        "OffhandItemId": lambda record: record.offhand_item_id if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01c0, "<h"),
        "OffhandItemType": lambda record: record.offhand_item_type if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01bd, "<B"),
        "Overcast": lambda record: record.h011C if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x011c, "<f"),
        "Owner": lambda record: record.owner if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00c4, "<i"),
        "Plane": lambda record: record.pos.zplane,
        "PlayerNumber": lambda record: record.player_number if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00f4, "<h"),
        "Primary": lambda record: record.primary if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x010e, "<B"),
        "Rotation": lambda record: record.rotation_angle,
        "RotationCos": lambda record: record.rotation_cos,
        "RotationCos2": lambda record: record.rotation_cos2,
        "RotationSin": lambda record: record.rotation_sin,
        "RotationSin2": lambda record: record.rotation_sin2,
        "Secondary": lambda record: record.secondary if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x010f, "<B"),
        "Skill": lambda record: record.skill if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01b8, "<h"),
        "Tags": lambda record: record.tags_ptr if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0108, "<I"),
        "Team": lambda record: record.team_id if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0111, "<B"),
        "TerrainNormalX": lambda record: record.terrain_normal.x,
        "TerrainNormalY": lambda record: record.terrain_normal.y,
        "TerrainNormalZ": lambda record: record.terrain_normal.z,
        "Timer": lambda record: record.timer,
        "Timer2": lambda record: record.timer2,
        "TransmogNpcId": lambda record: record.transmog_npc_id if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x00f8, "<I"),
        "Type": lambda record: record.type,
        "TypeMap": lambda record: record.type_map if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x015c, "<I"),
        "VisibleEffectCount": _read_visibleeffectcount,
        "VisibleEffectsNextNode": _read_visibleeffectsnextnode,
        "VisibleEffectsPrevLink": lambda record: record.visible_effects_list.offset if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0174, "<I"),
        "VisibleEffectsPtr": _read_visibleeffectsptr,
        "VisualEffects": lambda record: record.visual_effects,
        "WeaponItemId": lambda record: record.weapon_item_id if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01be, "<h"),
        "WeaponItemType": lambda record: record.weapon_item_type if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01bc, "<B"),
        "WeaponType": lambda record: record.weapon_type if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01b6, "<h"),
        "Width1": lambda record: record.width1,
        "Width2": lambda record: record.width2,
        "Width3": lambda record: record.width3,
        "X": lambda record: record.pos.x,
        "Y": lambda record: record.pos.y,
        "Z": lambda record: record.z,
        "h0004": lambda record: record.h0004,
        "h0008": lambda record: record.h0008,
        "h000C": lambda record: _read_field_bytes(record, 0x000c, "<I"),
        "h0010": lambda record: _read_field_bytes(record, 0x0010, "<I"),
        "h001C": lambda record: _read_field_bytes(record, 0x001c, "<4I"),
        "h0060": lambda record: record.h0060,
        "h0070": lambda record: tuple(record.h0070),
        "h0080": lambda record: tuple(record.h0080),
        "h0092": lambda record: record.h0092,
        "h0094": lambda record: tuple(record.h0094),
        "h00A8": lambda record: record.h00A8,
        "h00B4": lambda record: tuple(record.h00B4),
        "h00D4": lambda record: tuple(record.h00D4),
        "h00E4": lambda record: tuple(record.h00E4),
        "h0100": lambda record: record.h0100 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0100, "<I"),
        "h0104_new": lambda record: record.h0104 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0104, "<I"),
        "h010C": lambda record: record.h010C if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x010c, "<h"),
        "h0112": lambda record: tuple(record.h0112),
        "h0114": lambda record: record.h0114 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0114, "<I"),
        "h0128": lambda record: record.h0128 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0128, "<I"),
        "h0130": lambda record: record.h0130 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0130, "<I"),
        "h0140": lambda record: record.h0140 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0140, "<I"),
        "h0145": lambda record: tuple(record.h0145),
        "h0160": lambda record: tuple(record.h0160),
        "h0180": lambda record: record.h0180 if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x0180, "<I"),
        "h0194": lambda record: tuple(record.h0194),
        "h01BA": lambda record: record.h01BA if isinstance(record, AgentLivingStruct) else _read_field_bytes(record, 0x01ba, "<h"),
        "vtable": _read_vtable,
    }
)
def Agent_ConvertID(agent_id: Any) -> int:
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
def _ApplyFilters(agent: Any, filters: str) -> bool:
    """GwAu3's filter *string* resolved to a yes/no about one agent (``GwAu3_Data_Agent.au3:1221-1243``).

    GwAu3's scripts hand this helper a pipe-separated list of filter names -- ``"UAI_Filter_IsLivingEnemy"``,
    ``"UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe"``, and a leading ``-`` inverts one -- and it answers
    whether the agent passes all of them. It lives in ``GwAu3_Data_Agent.au3``, is used by the ``GetAgents``
    family in the same file and by every targeting function in ``UtilityAI_GetAgent.au3``, so it belongs to
    this module and is reachable from `py4gw/gwa3/uai_get_agent.py` the same way.

    **The one thing a port has to be careful about is the call itself.** GwAu3 resolves each name with
    AutoIt's ``Call($l_s_FilterName, $a_p_Agent)`` -- a lookup in the script's global function namespace --
    and Python has no such namespace to hand. What it has is this layer's own surface, which is exactly
    "every routine this port implements, by its GwAu3 name" (`py4gw/gwa3/bridge.py`'s ``layer_surface``),
    and that is what is looked the name up in. So the string a caller writes is the same string, the
    function it reaches is the same function, and the two answers that matter are the source's own:

    * a name that resolves to nothing answers ``False``, which is what ``Call`` answers for an unknown
      function -- ``0`` -- inverted by the same ``If Not $l_b_Result Then Return False`` (``:1235-1238``).
      It does not raise: an unrecognised name is the source's "no match", not this port's error;
    * an empty filter, or a filter of only blanks, answers ``True`` (``:1222`` and the ``:1228`` skip).

    The whitespace rule is ``StringStripWS($name, 3)`` (strip both ends) and the inversion test is
    ``StringLeft($name, 1) == "-"`` followed by ``StringTrimLeft($name, 1)``.
    """

    if filters == "":
        return True

    from .bridge import layer_surface

    surface = layer_surface()

    for raw in filters.split("|"):
        filter_name = raw.strip()
        if filter_name == "":
            continue

        invert = False
        if filter_name.startswith("-"):
            invert = True
            filter_name = filter_name[1:]

        routine = surface.get(filter_name)
        result = bool(routine(agent)) if routine is not None else False

        if invert:
            result = not result
        if not result:
            return False

    return True
def Agent_GetAgentEffectInfo(a_i_AgentID: Any = -2, a_i_SkillID: Any = 0, a_s_Info: Any = "") -> Any:
    """One column of an agent's effect from a skill (``GwAu3_Data_Agent.au3:867-911``).

    The source's shape, kept: it walks the agent's own effect array in ``0x18`` strides looking for the
    record whose first dword is the skill id (``:874-882``), answers ``0`` when there is no such record
    (``:884``), answers the **pointer** when no column is asked for (``:885``), and otherwise switches on
    the column name (``:887-910``).

    **This project already reads that array** (`py4gw.effect.get_effects`, the ported ``PyEffects``
    binding over the same records), so the walk is the port's own and each column is the field at the
    source's own offset: ``AttributeLevel`` at ``+0x4``, ``EffectID`` at ``+0x8``, ``CasterID`` at
    ``+0xC``, ``Duration`` at ``+0x10``, ``Timestamp`` at ``+0x14`` -- the same five fields
    `py4gw/gwa3/uai_effects.py` reads for the plugin's own effect columns, from the same record. The two
    computed columns are the source's arithmetic: ``TimeElapsed`` is ``BitAND(Skill_GetSkillTimer() -
    Timestamp, 0xFFFFFFFF)`` and ``TimeRemaining`` is ``Duration * 1000`` minus that; ``HasEffect``
    answers ``True`` for any record that was found, because that is what "found it" means (``:907-908``).
    ``SkillID`` is **commented out in the source** -- "serves no actual purpose as SkillID is a required
    arg" (``:888-889``) -- so it is not a column here either, and an unknown name answers ``0``, which is
    the source's ``Case Else``.

    **The empty-column answer is a record, not a pointer.** ``:885`` answers ``$l_p_EffectPtr``, a client
    address; this answers the **materialized record** the same divergence `Item_GetItemPtr` and
    `Agent_GetAgentPtr` record, and ``None`` where the source answers a zero pointer.
    """

    from .data_skill import Skill_GetSkillTimer

    if a_s_Info == "":
        for record in _effect.get_effects(int(a_i_AgentID)):
            if int(record.skill_id) == int(a_i_SkillID):
                return record
        return None

    for record in _effect.get_effects(int(a_i_AgentID)):
        if int(record.skill_id) != int(a_i_SkillID):
            continue
        if a_s_Info == "AttributeLevel":
            return int(record.attribute_level)
        if a_s_Info == "EffectID":
            return int(record.effect_id)
        if a_s_Info == "CasterID":
            return int(record.agent_id)
        if a_s_Info == "Duration":
            return float(record.duration)
        if a_s_Info == "Timestamp":
            return int(record.timestamp)
        if a_s_Info == "TimeElapsed":
            return (int(Skill_GetSkillTimer()) - int(record.timestamp)) & 0xFFFFFFFF
        if a_s_Info == "TimeRemaining":
            return float(record.duration) * 1000 - (
                (int(Skill_GetSkillTimer()) - int(record.timestamp)) & 0xFFFFFFFF
            )
        if a_s_Info == "HasEffect":
            return True
        return 0

    return 0
"""``GwAu3_Data_Agent.au3``'s **array, effects-block, bond, NPC and player** readers, hand-written
into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_agent_effect_info.py`
uses: ``data_agent.py`` is rewritten whole on every run, and this file is emitted verbatim into it
immediately before its ``__all__``.

**What the file carries, in the source's own order** (``GwAu3_Data_Agent.au3``):

* ``Agent_GetAgentArray`` (``:707-735``) -- the agent array GwAu3 fills from the client's pointer
  buffer, read here from this project's own agent array as **ids**, in GwAu3's own count-prefixed
  shape;
* ``Agent_GetAgentEffectArrayInfo`` (``:834-865``) -- one column of an agent's effects block in the
  world's agent-effects array, read here from the same array through this project's own records;
* ``Agent_GetAgentBondInfo`` (``:914-957``) -- one column of a bond in that block's bond sub-array;
* ``Agent_GetNpcInfo`` (``:963-1007``) -- one field of an NPC table entry, by index;
* ``Agent_GetPlayerInfo`` (``:1019-1069``) -- one field of a player array entry, by agent id;
* ``Agent_GetBestTarget`` (``:1096-1119``) -- GwAu3's own scoring loop over the living-agent array.

**Every record is this project's own and every offset lines up**, which is why this file is a read of
the same client data rather than a re-invention of it:

* the **agent-effects array** GwAu3 reaches at ``BasePointer[0x18][0x2C][0x508]`` is
  `WorldContextStruct.party_effects` (``py4gw/context/world_context.py:1801``) over
  ``party_effects_array``, and each block is `AgentEffectsStruct`
  (``py4gw/context/world_context.py:356``) -- ``0x24`` bytes, ``agent_id`` at ``+0x0``, the bond
  sub-array header at ``+0x4`` and the effect sub-array header at ``+0x14``, which are the four
  offsets GwAu3 reads at ``:852-861``;
* its bond records are `BuffStruct` (``py4gw/context/world_context.py:344``, ``0x10`` bytes) and its
  effect records `EffectStruct` (``:324``, ``0x18``) -- GwAu3's own two strides (``:927``, ``:875``);
* the **NPC array** at ``+0x7FC`` is `WorldContextStruct.npc_models` (``:1813``) over `NPCStruct`
  (``:494``, ``0x30`` bytes, the source's own stride at ``:969``): ``model_file_id`` at ``+0x0``,
  ``scale`` ``+0x8``, ``sex`` ``+0xC``, ``npc_flags`` ``+0x10``, ``primary`` ``+0x14``,
  ``default_level`` ``+0x1C``, ``name_enc_ptr`` ``+0x20``;
* the **player array** at ``+0x80C`` is `WorldContextStruct.players` (``:1819``) over `PlayerStruct`
  (``:616``, ``0x50`` bytes, the source's own stride at ``:1025``) -- every field GwAu3 reads at
  ``:1036-1065`` is a named field of it.

**No client address is ever an answer.** Four of GwAu3's cases return one -- the agent array's slots,
``BondArray`` and ``EffectArray``, and `Agent_GetAgentBondInfo`'s empty-column answer -- and each of
them answers the id, the record, or the list of records instead, with the divergence written on the
member that makes it.

**The family spec that carries this file**, recorded here because this file is what the generated
module's hand-written half is: ``extra_exports`` gains the six names below and ``helper_files`` gains
``("data_agent_npc_player_info.py",)``. No ``extra_imports`` are needed: every import this file makes
is local to the function that needs it (`from ..client import require_client`,
`from ..ui_manager import UIManager`), because the generated module's head imports neither and this
file is emitted verbatim.
"""


def Agent_GetAgentArray(a_i_Type: Any = 0) -> list[int]:
    """The client's agent array, optionally filtered by agent type (``GwAu3_Data_Agent.au3:707-735``).

    GwAu3's steps, kept: it takes the array's capacity (``:708``); answers a one-element array holding
    the count ``0`` when there is nothing to walk (``:709-710``); reads the client's pointer buffer and
    **skips every null slot** (``:714-721``); skips a slot whose ``Type`` is not the one asked for when
    a type was asked for (``:723-725``); and answers an array whose element ``0`` is the count and whose
    elements ``1..count`` are the agents (``:727-734``).

    **The slots hold ids, not addresses.** GwAu3 stores the pointer it read for each slot; this answers
    the agent **id**, because a client address is of no use to a caller here -- the same substitution
    `Agent_GetAgentPtr` records, and a migrating script passes the result straight back into another
    ``Agent_*`` function, which resolves it either way. The **shape is kept**: element ``0`` is the
    count and ``[0]`` alone is the empty answer, which is what `Party_GetMembersArray` keeps for its own
    AutoIt array (``py4gw/gwa3/uai_utils.py:408``) and what a caller like `Agent_GetBestTarget` indexes.

    The array itself is this project's own read: `AgentArray.GetAgentArray` (``py4gw/agent_array.py:43``),
    which traverses the client's array on demand and holds the ids of the populated slots -- so GwAu3's
    capacity read and its null-slot skip are already the array this member is handed.
    """

    agent_ids = AgentArray.GetAgentArray()
    if not agent_ids:
        return [0]

    agent_array: list[int] = [0]
    count = 0

    for agent_id in agent_ids:
        if a_i_Type != 0:
            if Agent_GetAgentInfo(agent_id, "Type") != a_i_Type:
                continue

        count += 1
        agent_array.append(int(agent_id))

    agent_array[0] = count
    return agent_array


def Agent_GetAgentEffectArrayInfo(a_i_AgentID: Any = -2, a_s_Info: Any = "") -> Any:
    """One column of an agent's effects block (``GwAu3_Data_Agent.au3:834-865``).

    GwAu3's steps, kept: it walks the world's agent-effects array in ``0x24`` strides and stops at the
    block whose first dword is ``Agent_ConvertID($a_i_AgentID)`` (``:839-847``); answers ``0`` when no
    block matched or no column was asked for (``:849``); and otherwise switches on the column name
    (``:851-864``), answering ``0`` for anything else (``:862-863``).

    The block is `AgentEffectsStruct` (``py4gw/context/world_context.py:356``), so each column is the
    same field GwAu3 reads: ``AgentID`` is ``agent_id`` at ``+0x0`` (``:852-853``), ``BondArraySize``
    is the bond sub-array header's own ``m_size`` at ``+0xC`` and ``EffectArraySize`` the effect
    header's at ``+0x1C`` (``:856-857``, ``:860-861``).

    **The two pointer columns answer the records the sub-array holds.** GwAu3 answers
    ``BondArray``/``EffectArray`` as a client address (``:854-855``, ``:858-859``); this answers the
    sub-array's records -- `BuffStruct` list and `EffectStruct` list, read through the block's own
    `buffs`/`effects` (``py4gw/context/world_context.py:393``, ``:403``), which are the same two record
    sets `py4gw.effect.get_effects`/`get_buffs` read (``py4gw/effect.py:100-137``) and the ones
    `Agent_GetAgentBondInfo` walks.
    """

    from ..client import require_client

    world = require_client().read_world_context()
    blocks = [] if world is None else list(world.party_effects or [])

    agent_id = Agent_ConvertID(a_i_AgentID)

    record = None
    for block in blocks:
        if int(block.agent_id) == agent_id:
            record = block
            break

    if record is None or a_s_Info == "":
        return 0

    if a_s_Info == "AgentID":
        return int(record.agent_id)
    if a_s_Info == "BondArray":
        return list(record.buffs)
    if a_s_Info == "BondArraySize":
        return int(record.buff_array.m_size)
    if a_s_Info == "EffectArray":
        return list(record.effects)
    if a_s_Info == "EffectArraySize":
        return int(record.effect_array.m_size)

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetAgentBondInfo(
    a_i_AgentID: Any = -2, a_i_SkillID: Any = 0, a_i_TargetID: Any = 0, a_s_Info: Any = ""
) -> Any:
    """One column of a bond on an agent (``GwAu3_Data_Agent.au3:914-957``).

    GwAu3's steps, kept in its own order: it takes the agent's bond array and its size
    (``:915-916``); answers ``0`` for a zero array or an empty one (``:918``); resolves the target id
    through ``Agent_ConvertID`` **only when a target was given** (``:921-924``); walks the array in
    ``0x10`` strides, skipping a record whose skill differs and -- when a target was given -- one whose
    ``+0xC`` differs from it, and stops at the first match (``:926-938``); answers ``0`` when nothing
    matched (``:940``); answers the record when no column was asked for (``:941``); and otherwise
    switches on the column name (``:943-956``), answering ``0`` for anything else (``:954-955``).

    Every column is the port's own field of the same record -- `BuffStruct`
    (``py4gw/context/world_context.py:344``), whose four dwords are the source's four offsets:
    ``h0004`` at ``+0x4`` (``:946-947``), ``BondID`` at ``+0x8`` (``:948-949``) and ``TargetAgentID``
    at ``+0xC`` (``:950-951``), which is also the word the target was compared against.
    ``HasBond`` answers ``True`` once a record matched (``:952-953``), because that is what having
    found one means.

    **The empty-column answer is a record, not a pointer**: ``:941`` answers ``$l_p_BondPtr``, a client
    address, and this answers the `BuffStruct` the walk stopped at -- the same divergence
    `Agent_GetAgentEffectInfo` records for its own empty column.
    """

    bond_array = Agent_GetAgentEffectArrayInfo(a_i_AgentID, "BondArray")
    bond_count = Agent_GetAgentEffectArrayInfo(a_i_AgentID, "BondArraySize")

    if not bond_array or not bond_count:
        return 0

    bond_record = None
    check_target = a_i_TargetID != 0
    target_id = 0

    if check_target:
        target_id = Agent_ConvertID(a_i_TargetID)

    for record in bond_array:
        if int(record.skill_id) != int(a_i_SkillID):
            continue

        if check_target:
            if int(record.target_agent_id) != target_id:
                continue

        bond_record = record
        break

    if bond_record is None:
        return 0
    if a_s_Info == "":
        return bond_record

    if a_s_Info == "h0004":
        return int(bond_record.h0004)
    if a_s_Info == "BondID":
        return int(bond_record.buff_id)
    if a_s_Info == "TargetAgentID":
        return int(bond_record.target_agent_id)
    if a_s_Info == "HasBond":
        return True

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetNpcInfo(a_i_NpcIndex: Any = 0, a_s_Info: Any = "") -> Any:
    """One field of an NPC table entry, by index (``GwAu3_Data_Agent.au3:963-1007``).

    GwAu3's steps, kept: it takes the NPC array and its size (``:964-965``) and answers ``0`` for a
    zero pointer, an empty array or an empty field name (``:966``); answers ``0`` for an index at or
    below ``0``, or at or past the array's size (``:967``); and then switches on the field name over the
    entry at ``index * 0x30`` (``:969-1006``), answering ``0`` for anything else (``:1004-1005``). Its
    own comment names the index: *"Player number of an npc"* (``:961``), which is the index this
    project's `Agent.GetNPCFlags` passes to its NPC-model reader too (``py4gw/agent.py:1975``).

    The entry is `NPCStruct` (``py4gw/context/world_context.py:494``), so each field is the port's own
    name at the source's own offset: ``ModelFileID`` ``+0x0`` (``:972-973``), ``Scale`` ``+0x8``
    (``:974-975``), ``Sex`` ``+0xC`` (``:976-977``), ``NpcFlags`` ``+0x10`` (``:978-979``),
    ``Primary`` ``+0x14`` (``:980-981``) and ``DefaultLevel``/``Level`` the byte at ``+0x1C``
    (``:982-983``). The four flag questions are the record's own members, each the same mask GwAu3
    applies: `is_henchman` ``0x10`` (``:984-986``), `is_hero` ``0x20`` (``:987-989``), `is_spirit`
    ``0x4000`` (``:990-992``) and `is_minion` ``0x100`` (``:993-995``).

    ``Level`` is answered from the byte too, because **AutoIt's ``Switch`` runs the first matching
    ``Case``** and ``:982`` matches ``"Level"`` before the dword case at ``:996-997`` does; that second
    case is unreachable in GwAu3 and stays unreachable here.

    The two name fields are the port's own members for the same two GwAu3 utils, over the same pointer
    at ``+0x20`` (`NPC_ModelStruct.name_encoded_str`, ``py4gw/context/world_context.py:568``):
    ``NameEnc`` is ``Utils_DecodeEncString`` (``GwAu3_Core_Utils.au3:440-462``), which decodes the
    encoded name to its **string id** -- answered here by `UIManager.EncStrToUInt32`
    (``py4gw/ui_manager.py:760``), the ported ``GW::ui::EncStrToUInt32`` -- with that util's own
    zero-pointer answer ``0`` (``:441``); and ``Name`` is ``Utils_DecodeEncStringAsync``
    (``:469-498``), which hands the encoded name to the client's decoder and answers the text, kept here
    by `UIManager.AsyncDecodeStr` (``py4gw/ui_manager.py:672``), the ported ``GW::ui::AsyncDecodeStr``,
    with that util's own zero-pointer answer ``""`` (``:470``).
    """

    from ..client import require_client
    from ..ui_manager import UIManager

    world = require_client().read_world_context()
    models = [] if world is None else list(world.npc_models or [])

    if not models or a_s_Info == "":
        return 0

    npc_index = int(a_i_NpcIndex)
    if npc_index <= 0 or npc_index >= len(models):
        return 0

    record = models[npc_index]

    if a_s_Info == "ModelFileID":
        return int(record.model_file_id)
    if a_s_Info == "Scale":
        return int(record.scale)
    if a_s_Info == "Sex":
        return int(record.sex)
    if a_s_Info == "NpcFlags":
        return int(record.npc_flags)
    if a_s_Info == "Primary":
        return int(record.primary)
    if a_s_Info == "DefaultLevel" or a_s_Info == "Level":
        return int(record.default_level)
    if a_s_Info == "IsHenchman":
        return bool(record.is_henchman)
    if a_s_Info == "IsHero":
        return bool(record.is_hero)
    if a_s_Info == "IsSpirit":
        return bool(record.is_spirit)
    if a_s_Info == "IsMinion":
        return bool(record.is_minion)
    if a_s_Info == "NameEnc":
        encoded = record.name_encoded_str
        if encoded is None:
            return 0
        return int(UIManager.EncStrToUInt32(encoded))
    if a_s_Info == "Name":
        encoded = record.name_encoded_str
        if encoded is None:
            return ""
        return str(UIManager.AsyncDecodeStr(encoded))

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetPlayerInfo(a_i_AgentID: Any = 0, a_s_Info: Any = "") -> Any:
    """One field of a player array entry, by agent id (``GwAu3_Data_Agent.au3:1019-1069``).

    GwAu3's steps, kept: it walks the player array from index ``1`` to its size (``:1024-1030``) --
    ``:1024`` starts past the array's own first slot -- comparing each entry's first dword with
    ``Agent_ConvertID($a_i_AgentID)``; answers ``0`` when no entry matched (``:1032``); and then switches
    on the field name (``:1034-1068``), answering ``0`` for anything else (``:1066-1067``).

    **There is no empty-field guard in this function**, unlike its neighbours, and none is added: an
    empty field name falls through GwAu3's own ``Case Else`` to ``0``.

    The entry is `PlayerStruct` (``py4gw/context/world_context.py:616``, ``0x50`` bytes), so each field
    is the port's own name at the source's own offset: ``AgentID`` ``+0x0`` (``:1035-1036``),
    ``AppearanceBitmap`` ``+0x10`` (``:1037-1038``), ``Flags`` ``+0x14`` (``:1039-1040``), ``Primary``
    ``+0x18`` (``:1041-1042``), ``Secondary`` ``+0x1C`` (``:1043-1044``),
    ``PartyLeaderPlayerNumber`` ``+0x2C`` (``:1048-1049``), ``ActiveTitle`` ``+0x30`` (``:1050-1051``),
    ``ActiveChallenge`` ``+0x34`` (``:1053-1054``), ``PlayerNumber`` ``+0x38`` (``:1062-1063``) and
    ``PartySize`` ``+0x3C`` (``:1064-1065``). The three flag questions are the record's own members over
    the same word: `is_melandrus_accord` (``:1055-1056``), `is_dhuums_covenant` (``:1057-1058``) and
    `is_reforged` (``:1059-1060``).

    **One disagreement between those three bits is recorded rather than smoothed over.** GwAu3 masks
    ``0x1`` for Melandru's Accord and ``0x2`` for Dhuum's Covenant; this project's two members of those
    names mask ``0x2`` and ``0x1`` respectively (``py4gw/context/world_context.py:655-664``), so each
    key answers the port's own member of its name and the bit disagreement is a finding a live read
    would settle. ``ActiveChallenge``'s word is the port's `reforged_or_dhuums_flags` under a different
    name, the same offset ``+0x34``.

    ``Name`` is a string either way: GwAu3 reads a fixed ``wchar[20]`` at the pointer in ``+0x28``
    (``:1045-1047``) and this answers the port's own bounded read of that same pointer,
    `PlayerStruct.name_encoded_str` (``py4gw/context/world_context.py:685``) -- the display name, read
    to its terminator instead of to twenty wide characters.
    """

    from ..client import require_client

    world = require_client().read_world_context()
    players = [] if world is None else list(world.players or [])

    agent_id = Agent_ConvertID(a_i_AgentID)

    record = None
    for index in range(1, len(players)):
        if int(players[index].agent_id) == agent_id:
            record = players[index]
            break

    if record is None:
        return 0

    if a_s_Info == "AgentID":
        return int(record.agent_id)
    if a_s_Info == "AppearanceBitmap":
        return int(record.appearance_bitmap)
    if a_s_Info == "Flags":
        return int(record.flags)
    if a_s_Info == "Primary":
        return int(record.primary)
    if a_s_Info == "Secondary":
        return int(record.secondary)
    if a_s_Info == "Name":
        return str(record.name_encoded_str or "")
    if a_s_Info == "PartyLeaderPlayerNumber":
        return int(record.party_leader_player_number)
    if a_s_Info == "ActiveTitle":
        return int(record.active_title_tier)
    if a_s_Info == "ActiveChallenge":
        return int(record.reforged_or_dhuums_flags)
    if a_s_Info == "ActiveMelandrusAccord":
        return bool(record.is_melandrus_accord)
    if a_s_Info == "ActiveDhuumsCovenant":
        return bool(record.is_dhuums_covenant)
    if a_s_Info == "ActiveReforgedMode":
        return bool(record.is_reforged)
    if a_s_Info == "PlayerNumber":
        return int(record.player_number)
    if a_s_Info == "PartySize":
        return int(record.party_size)

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetBestTarget(a_i_Range: Any = 1320) -> int:
    """The enemy worth attacking most, by GwAu3's own score (``GwAu3_Data_Agent.au3:1096-1119``).

    GwAu3's steps, kept: it takes the living-agent array (``:1098``, ``0xDB`` being the living type, as
    its own comment at ``:753`` records) and, for each agent, skips one whose ``Allegiance`` is not
    ``3`` (enemy), whose ``HP`` is not above ``0``, that is the controlled character, or that is further
    than ``$a_i_Range`` from the player (``:1101-1104``); then sums that agent's distance to **every**
    agent passing the same four tests, itself included (``:1105-1112``); and keeps the agent with the
    lowest sum, ties going to the first one reached (``:1113-1116``).

    The four guard pairs and the two loops are the source's, in the source's order, over this project's
    own reads: `Agent_GetAgentArray` for the array (ids where GwAu3 holds pointers), `Agent_GetAgentInfo`
    for the four columns, `Agent_GetMyID` for the controlled character and `Agent_GetDistance` for both
    the range test (the player, its own default) and the pairwise sum.

    **The no-match answer is ``0``, and GwAu3's is not.** ``:1097`` declares ``$l_i_BestTarget`` with no
    value, so a client with nothing matching answers AutoIt's uninitialised ``""``; this answers ``0``,
    the id no agent has, which is how every other member of this layer tells "nothing found".
    """

    best_target = 0
    lowest_sum = 100000000

    agent_array = Agent_GetAgentArray(0xDB)

    for index in range(1, agent_array[0] + 1):
        this_id = agent_array[index]
        sum_distances = 0

        if Agent_GetAgentInfo(this_id, "Allegiance") != 3:
            continue
        if Agent_GetAgentInfo(this_id, "HP") <= 0:
            continue
        if Agent_GetAgentInfo(this_id, "ID") == Agent_GetMyID():
            continue
        if Agent_GetDistance(this_id) > a_i_Range:
            continue

        for sub_index in range(1, agent_array[0] + 1):
            other_id = agent_array[sub_index]

            if Agent_GetAgentInfo(other_id, "Allegiance") != 3:
                continue
            if Agent_GetAgentInfo(other_id, "HP") <= 0:
                continue
            if Agent_GetAgentInfo(other_id, "ID") == Agent_GetMyID():
                continue
            if Agent_GetDistance(other_id) > a_i_Range:
                continue

            sum_distances += Agent_GetDistance(this_id, other_id)

        if sum_distances < lowest_sum:
            lowest_sum = sum_distances
            best_target = this_id

    return best_target
"""``GwAu3_Data_Agent.au3``'s **visible-effect** readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_data_agent.py``, the same
mechanism `data_agent`'s effect-column reader and `_ApplyFilters` use: ``data_agent.py`` is rewritten
whole on every run, so a function written straight into it would be lost the next time the generator ran.

**The source file, because the task that asked for this named one that does not exist.** There is no
``GwAu3_Data_VisibleEffect.au3`` anywhere under ``external/GwAu3``: the three readers are declared in
``GwAu3_Data_Agent.au3`` -- ``VisibleEffect_Count`` at ``:1143-1159``, ``VisibleEffect_GetAll`` at
``:1161-1189`` and ``VisibleEffect_FindByID`` at ``:1191-1217`` -- between the ``#Region Visible Effect``
marker (``:1121``) and its end, which is also where the three ``Agent_*`` wrappers that call them live
(``Agent_CountVisibleEffects`` ``:1122-1124``, ``Agent_GetAllVisibleEffects`` ``:1126-1136``,
``Agent_HasVisibleEffect`` ``:1138-1141``). ``docs/GWA3_ROUTE_MAP.md:264``, ``:1008`` and ``:1009`` cite
the same file and the same lines. Their home module is therefore this one, the source file's own module.

**The walk is not written here, because this project already has it.** All three readers answer from the
same ported walk: `py4gw/gwa3/uai_effects.py:363` ``_visible_effects(agent_id)``, which reads the agent's
record through `Agent_GetAgentPtr` (this module, ``:674``) and walks the list at
``AgentLivingStruct.visible_effects_list`` -- ``+0x174``, the very offset GwAu3's own
``Agent_GetAgentInfo(..., "VisibleEffectsPtr")`` answers (``py4gw/context/agent_array.py:885``) --
through `RemoteGWListView` into `VisibleEffectStruct` records (``py4gw/context/agent_array.py:808-835``).
Those three dwords land exactly where GwAu3's ``UAI_GetVisibleEffectStruct`` puts them
(``UtilityAI_EffectsCache.au3:76-82``): the port calls the first ``unk`` where the source calls it
``EffectType``, and that is the only field-name difference.

**The record column is answered as the record.** GwAu3 puts the node's own **address** in
``VisibleEffect_GetAll``'s first column (``:1176``) and in ``VisibleEffect_FindByID``'s second cell
(``:1206``); this layer hands out no client address, so both answer the materialized
`VisibleEffectStruct` the row's other cells are read from -- the same substitution `Item_GetItemPtr` and
`Agent_GetAgentPtr` record. The column **order** is GwAu3's and is kept, because a caller indexes it:
``Agent_GetAllVisibleEffects`` reads ``[2]`` for the effect id (``:1132``) and ``Agent_HasVisibleEffect``
reads ``[0]`` of the ``FindByID`` result (``:1140``).

**One bound differs, and the difference is the walk's.** GwAu3's ``GetAll`` stops after **100** nodes
because its row array is ``[101][4]`` (``:1173``); the port's walk is bounded by its own reader at
``_MAX_VISIBLE_EFFECTS`` -- 128 (``py4gw/context/agent_array.py:841``) -- so the source's 100-row cap is
applied here, on top of the walk, and an agent carrying more than 100 visible effects is answered from
its first 100, exactly as the source answers it.

**``Utils_TList_CreateIterator``, ``Utils_TList_Iterator_Current``, ``Utils_TList_Iterator_Next`` and
``Utils_TLink_IsLinked`` are carried, in `py4gw/gwa3/core_utils.py`.**
``GwAu3_Core_Utils.au3:88-141`` builds an AutoIt array of **client addresses** (the sentinel is
``$a_p_TListPtr + 0x4``), steps it through the XOR-linked list and answers the next node's address
(``Utils_TList_Iterator_Current`` returns the dword at ``+0x4``), and ``Utils_TLink_IsLinked`` answers
whether an address's prev-link differs from the address itself. This module is the reason they could be
answered at all: the walk they need is the port's
(`py4gw/gwa3/uai_effects.py:363`, over `py4gw/context/agent_array.py:935`), and what they iterate in
`core_utils.py` is **the list that walk answers** -- the port's records -- rather than node addresses this
layer does not hand out. Their only callers in GwAu3 are the plugin's effect cache
(``UtilityAI_EffectsCache.au3:119-134``) and the two ``Tools_VisibleEffect`` scripts, both walking the
visible-effect list the three readers below read.
"""


def VisibleEffect_Count(a_i_AgentID: Any = -2) -> int:
    """How many visible effects an agent carries (``GwAu3_Data_Agent.au3:1143-1159``).

    GwAu3's guard is its own line, kept verbatim: ``If Agent_GetAgentInfo($a_i_AgentID, "Type") <> 0xDB
    Then Return 0`` (``:1144``) -- a living agent, by the type word this port also reads as ``0xDB``
    (`Agent_GetAgentInfo`, this module, ``py4gw/gwa3/data_agent.py:725``; the type test itself at
    ``:207-210``) -- and an agent the client does not hold answers ``0`` from the same call.

    The count is the walk's own length: GwAu3 counts the nodes of the TList at ``VisibleEffectsPtr``
    (``:1146-1156``); `_visible_effects` (`py4gw/gwa3/uai_effects.py:363`) walks that same list from the
    agent's record, so its length is the same number. **This is the member `VisibleEffectCount` and
    `HasVisibleEffects` were waiting on** -- both of those keys of `Agent_GetAgentInfo` still refuse
    (`py4gw/gwa3/data_agent.py:48`) and can now be routed onto this one.
    """

    from .uai_effects import _visible_effects

    if int(Agent_GetAgentInfo(a_i_AgentID, "Type")) != 0xDB:
        return 0

    return len(_visible_effects(a_i_AgentID))


def VisibleEffect_GetAll(a_i_AgentID: Any = -2) -> Any:
    """Every visible effect of an agent, as rows behind a row carrying the count
    (``GwAu3_Data_Agent.au3:1161-1189``).

    **Both of GwAu3's answers are kept, and they are not the same type.** An agent whose type word is
    not ``0xDB`` answers the scalar ``0`` (``:1165``); a living agent answers an AutoIt 2-D array
    ``[1 + count][4]`` whose row ``0`` is ``(count, 0, 0, 0)`` and whose remaining rows are
    ``(node, unk, id, has_ended)`` (``:1176-1186``), a living agent with no nodes answering the
    1-row array ``(0, 0, 0, 0)`` -- which is why the guard cannot be dropped in favour of the walk's
    empty list, the walk's answer being an array where the source's is a number. The rows are answered
    as a list of rows, the same substitution `UAI_GetAgentVisibleEffectInfo` makes.

    The three dwords are the ported record's own fields -- ``unk`` at ``+0x0``, ``id`` at ``+0x4``,
    ``has_ended`` at ``+0x8`` (``py4gw/context/agent_array.py:808-816``) -- and the first cell of each
    row is the **record itself** where GwAu3 puts the node's address (``:1176``): this layer answers no
    address, and the record is what the row's other three cells were read from. The source's 100-node
    cap is applied (``:1173``).
    """

    from .uai_effects import _visible_effects

    if int(Agent_GetAgentInfo(a_i_AgentID, "Type")) != 0xDB:
        return 0

    effects = _visible_effects(a_i_AgentID)[:100]

    rows: list[Any] = [[0, 0, 0, 0]]
    for record in effects:
        rows.append([record, int(record.unk), int(record.id), int(record.has_ended)])

    rows[0][0] = len(effects)
    return rows


def VisibleEffect_FindByID(a_i_AgentID: Any = -2, a_i_EffectID: Any = 0) -> Any:
    """The visible effect of an agent whose effect id matches (``GwAu3_Data_Agent.au3:1191-1217``).

    The source's three answers, in its order and its shapes: an agent whose type word is not ``0xDB``
    answers the scalar ``0`` (``:1194``); a match answers ``(True, node, unk, has_ended)`` at the first
    node whose ``+0x4`` equals the id (``:1202-1209``); and no match answers ``(False, 0, 0, 0)``, the
    array the function starts with (``:1192``, ``:1216``). The comparison is the **id** at ``+0x4``
    only, which is why a match does not need the type word GwAu3's other readers test.

    The second cell is this project's `VisibleEffectStruct` where GwAu3's is the node's address
    (``:1206``) -- the divergence this module's header records for the other two readers -- and the id
    and ``has_ended`` cells are the record's own ``id`` and ``has_ended`` fields at ``+0x4`` and
    ``+0x8``. ``Agent_HasVisibleEffect`` (``:1138-1141``) reads cell ``0``, so the boolean stays first.
    """

    from .uai_effects import _visible_effects

    if int(Agent_GetAgentInfo(a_i_AgentID, "Type")) != 0xDB:
        return 0

    for record in _visible_effects(a_i_AgentID):
        if int(record.id) == int(a_i_EffectID):
            return [True, record, int(record.unk), int(record.has_ended)]

    return [False, 0, 0, 0]


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
