"""GwAu3's ``GwAu3_Data_Attribute.au3``: the attribute records, by id and by party member.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**The file is seven members and they are all here except one, which is NOT APPLICABLE.** Three of them
read the client's own **attribute-constant table** (``$g_p_AttributeInfo``, ``0x14`` per record) and
three read the **party-attribute blocks** (``$g_p_PartyAttributeArray``, ``0x43C`` per party member);
this project already reads both, through the ported structures their layouts assert:
`py4gw/context/world_context.py`'s `AttributeInfoStruct` (``profession_id``, ``attribute_id``,
``name_id``, ``desc_id``, ``is_pve`` -- the five fields ``Attribute_GetAttributeInfo`` switches over, at
the same offsets) and `PartyAttributeStruct` (an ``agent_id`` and **fifty-four** ``0x14``-byte
`AttributeStruct` records, which is ``0x43C`` exactly). So no offset in this file is a guess: each one is
the field the port already names.

**What is written by hand, and why.** This is the second ``data_*`` module with no generated table
(`data_effect.py` is the first): the family generator builds modules whose accessor is a ``Switch`` over
**one record's offsets**, and four of these members switch over *strings* with computed answers -- group
by attribute id, by party member, by hero number. The cases below are the source's own, in its own order.

**The one NOT APPLICABLE member** is `Attribute_GetLastModified`: it answers two globals
(``$g_i_LastAttributeModified``, ``$g_i_LastAttributeValue``) that GwAu3's own *setter* maintains when it
changes an attribute -- controller-side state behind a client write this layer does not perform. It says
so and answers the pair's shape rather than a stand-in number.
"""

from __future__ import annotations

import struct
from typing import Any

from ..client import require_client
from ..skillbar import get_attribute_constant_data
from .data_agent import Agent_GetMyID
from .data_party import Party_GetMyPartyHeroInfo

__all__ = [
    "Attribute_GetAttributeInfo",
    "Attribute_GetAttributeName",
    "Attribute_GetAttributePtr",
    "Attribute_GetLastModified",
    "Attribute_GetPartyAttributeInfo",
    "Attribute_GetPartyAttributePointInfo",
    "Attribute_GetProfPrimaryAttribute",
]

#: ``GwAu3_Data_Attribute.au3:116-117`` -- the block layout GwAu3 computes its point offsets from: 45
#: attribute records, then the two point words. Kept as the source writes them so the two offsets below
#: are the source's arithmetic rather than a magic number.
_ATTRIBUTE_COUNT = 45
_ATTRIBUTE_RECORD = 0x14
_BASE_ATTRIBUTE_POINT_OFFSET = _ATTRIBUTE_RECORD * _ATTRIBUTE_COUNT + 0xB0


def Attribute_GetAttributeName(a_i_AttributeID: Any) -> str:
    """An attribute id's name (``GwAu3_Data_Attribute.au3:3-8``).

    The source reads its own ``$GC_AS_ATTRIBUTE_NAMES`` array between ``0`` and ``44`` and answers
    ``"Unknown"`` outside it; this reads the table the port already carries for the same purpose
    (`py4gw/context/world_context.py`'s attribute names, which `AttributeStruct.name` answers from).
    """

    from ..context.world_context import _ATTRIBUTE_NAMES

    if 0 <= int(a_i_AttributeID) < 45:
        return str(_ATTRIBUTE_NAMES.get(int(a_i_AttributeID), "Unknown"))
    return "Unknown"


def Attribute_GetLastModified() -> Any:
    """**NOT APPLICABLE: the state behind GwAu3's own attribute setter.**

    ``:10-13`` answers ``[$g_i_LastAttributeModified, $g_i_LastAttributeValue]`` -- two globals GwAu3
    writes when *it* changes an attribute, which is a client write this layer does not perform (the
    layer's own ``cmd_attribute`` module refuses the two setters it has for the same reason: their route
    is a packet). There is no equivalent state here, and answering a pair of zeroes would look like
    "nothing has been modified" rather than "this layer cannot modify anything". The pair's **shape** is
    kept, because a caller reads it by index.
    """

    return [0, 0]


def Attribute_GetAttributePtr(a_i_AttributeID: Any) -> Any:
    """An attribute's constant-table record (``:15-18``).

    GwAu3 walks ``$g_p_AttributeInfo + 0x14 * $a_i_AttributeID`` and answers the pointer; this answers
    the **record** that address holds -- the same divergence `Item_GetItemPtr` and `Agent_GetAgentPtr`
    record, because a client address is of no use to a caller here. The table is the port's own read of
    the client's attribute-constant array (`py4gw/skillbar.py`'s ``get_attribute_constant_data``, over
    the same ``0x14`` records), and ``None`` is GwAu3's zero pointer.
    """

    return get_attribute_constant_data(int(a_i_AttributeID))


def Attribute_GetAttributeInfo(a_i_AttributeID: Any, a_s_Info: Any = "") -> Any:
    """One field of an attribute's constant-table record (``:20-38``).

    The source's guard order, kept: no record **or an empty field name** answers ``0`` (``:22``) -- note
    that this member does *not* answer the pointer for an empty name, unlike its party sibling; then the
    five cases, each a field at the offset the port's `AttributeInfoStruct` names; and ``0`` for anything
    else, which is the ``Return 0`` under the ``Switch`` (``:37``).

    **The empty name is answered before the table is read.** The source's guard reads the pointer first
    and AutoIt's failed read answers ``0``; here the key is checked first, so a caller with no connection
    is told the field name is empty rather than told it is unconnected -- the same order this layer's
    other accessors take, and it is the answer the source gives either way.
    """

    if a_s_Info == "":
        return 0

    record = Attribute_GetAttributePtr(a_i_AttributeID)
    if record is None:
        return 0

    if a_s_Info == "ProfessionID":
        return int(record.profession_id)
    if a_s_Info == "AttributeID":
        return int(record.attribute_id)
    if a_s_Info == "NameID":
        return int(record.name_id)
    if a_s_Info == "DescID":
        return int(record.desc_id)
    if a_s_Info == "IsPVE":
        return int(record.is_pve)

    return 0


def Attribute_GetPartyAttributeInfo(
    a_i_AttributeID: Any, a_i_HeroNumber: Any = 0, a_s_Info: Any = ""
) -> Any:
    """One field of a party member's attribute record (``:40-94``).

    The source's walk, kept: the party-attribute array is scanned for the block whose first dword is the
    agent id (``:47-53``) -- the agent being the controlled character when ``$a_i_HeroNumber`` is ``0``
    and that hero's agent otherwise (``:44``) -- and the block answers ``0`` when nothing matched
    (``:55``). Then ``$a_s_Info = ""`` answers the **block** (``:56``), and otherwise the record for the
    attribute id is ``block + 0x14 * id + 4``, which is the port's `PartyAttributeStruct.attribute_array`
    indexed by that id.

    **Two keys read their dword as *signed*, because the source does**: ``DecrementPoints`` and
    ``IncrementPoints`` are read with ``"long"`` and compared ``> 0`` (``:80-82``), so a stored ``-1``
    answers ``False`` -- an unsigned read of the same bytes would answer ``True``.
    """

    if a_i_HeroNumber == 0:
        agent_id = Agent_GetMyID()
    else:
        agent_id = Party_GetMyPartyHeroInfo(a_i_HeroNumber, "AgentID")

    world = require_client().read_world_context()
    if world is None:
        return 0

    block = None
    for candidate in world.party_attributes or []:
        if int(candidate.agent_id) == int(agent_id):
            block = candidate
            break

    if block is None:
        return 0
    if a_s_Info == "":
        return block

    attribute = block.attributes[int(a_i_AttributeID)]

    if a_s_Info in ("ID", "AttributeID"):
        return int(attribute.attribute_id)
    if a_s_Info in ("BaseLevel", "LevelBase"):
        return int(attribute.level_base)
    if a_s_Info in ("Level", "CurrentLevel"):
        return int(attribute.level)
    if a_s_Info == "DecrementPoints":
        return struct.unpack_from("<i", attribute, 0x0C)[0]
    if a_s_Info == "IncrementPoints":
        return struct.unpack_from("<i", attribute, 0x10)[0]
    if a_s_Info == "HasAttribute":
        return int(attribute.level) > 0
    if a_s_Info == "BonusLevel":
        return int(attribute.level) - int(attribute.level_base)
    if a_s_Info == "IsMaxed":
        return int(attribute.level_base) >= 12
    if a_s_Info == "IsDecreasable":
        return struct.unpack_from("<i", attribute, 0x0C)[0] > 0
    if a_s_Info == "IsRaisable":
        return struct.unpack_from("<i", attribute, 0x10)[0] > 0
    if a_s_Info in ("UnusedPoints", "TotalPoints"):
        return Attribute_GetPartyAttributePointInfo(a_i_HeroNumber, a_s_Info)

    return 0


def Attribute_GetPartyAttributePointInfo(a_i_HeroNumber: Any = 0, a_s_Info: Any = "") -> Any:
    """A party member's spent and unspent attribute points (``:96-134``).

    The same walk as `Attribute_GetPartyAttributeInfo`, over the same blocks, for the two words that sit
    **after the 45 attribute records**: ``0x14 * 45 + 0xB0`` for ``UnusedPoints`` and four bytes past it
    for ``TotalPoints`` (``:116-127``). The agent is resolved the same two ways (``:98-102``, the
    controlled character being ``World_GetWorldInfo("MyID")`` there and `Agent_GetMyID` here), and an
    unknown field answers ``0`` -- the source's own ``Case Else``.
    """

    if a_i_HeroNumber == 0:
        agent_id = Agent_GetMyID()
    else:
        agent_id = Party_GetMyPartyHeroInfo(a_i_HeroNumber, "AgentID")

    world = require_client().read_world_context()
    if world is None:
        return 0

    for block in world.party_attributes or []:
        if int(block.agent_id) != int(agent_id):
            continue
        if a_s_Info == "UnusedPoints":
            return struct.unpack_from("<I", block, _BASE_ATTRIBUTE_POINT_OFFSET)[0]
        if a_s_Info == "TotalPoints":
            return struct.unpack_from("<I", block, _BASE_ATTRIBUTE_POINT_OFFSET + 0x4)[0]
        return 0

    return 0


def Attribute_GetProfPrimaryAttribute(a_i_Profession: Any) -> int:
    """The attribute id a profession's primary attribute carries (``:137-160``).

    GwAu3's own ten cases and **no** ``Case Else``: a profession outside ``1..10`` falls out of the
    ``Switch`` and the ``EndFunc`` answers nothing, which is AutoIt's zero. The ten numbers are the
    source's own literals -- they are attribute *ids*, not profession ids, and the two sets have nothing
    to do with each other, which is why the switch exists rather than an arithmetic conversion.
    """

    if a_i_Profession == 1:
        return 17
    if a_i_Profession == 2:
        return 23
    if a_i_Profession == 3:
        return 16
    if a_i_Profession == 4:
        return 6
    if a_i_Profession == 5:
        return 0
    if a_i_Profession == 6:
        return 12
    if a_i_Profession == 7:
        return 35
    if a_i_Profession == 8:
        return 36
    if a_i_Profession == 9:
        return 40
    if a_i_Profession == 10:
        return 44
    return 0
