"""Generate the field-name accessor modules of the GwAu3-compatible layer.

Part of the GwAu3-compatible layer; see ``docs/GWA3_COMPAT_SPEC.md``.

Run from the project root:

    python tools/generate_gwa3_family.py

**What a "family" is here.** GwAu3's read surface is dominated by a handful of accessors with the same
shape: a record is resolved, then one ``Switch`` on a field-name string reads one field at one offset
with one width. ``Agent_GetAgentInfo`` is the biggest (`tools/generate_gwa3_data_agent.py`, written
before this and left alone -- it works, and a refactor of working code for tidiness is not worth the
risk). This generator covers the rest of the families from one specification each, because the only
things that differ are *which* record, *which* structure answers the offsets, and the handful of keys
whose case is not a field read.

**Why generated.** ``Skill_GetSkillInfo`` alone is 63 keys across a 0xA4-stride table; transcribing
them by hand is that many chances to mistype an offset, and a mistyped offset reads the wrong client
field silently. The offsets are parsed from GwAu3's source and resolved against **ctypes'** view of the
structure this project reads.

**Why each reader names its attribute.** The record is a ``ctypes.Structure`` and the porting rules
forbid reaching a field through a dynamic name, so the *offset* picks the attribute once at generation
time and the emitted reader names it literally. Nothing resolves a field by string at run time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
#: Hand-written source the generated families carry, read at generation time. Kept beside this
#: generator because it is generator input, the same standing as the `.au3` sources it reads.
SNIPPETS_DIR = Path(__file__).resolve().parent / "gwa3_snippets"
GWAU3_DATA_DIR = REPO_ROOT / "external" / "GwAu3" / "API" / "Modules" / "Data"

CASE_LINE = re.compile(r"^\s*Case\s+(?P<keys>.+?)\s*$")
KEY = re.compile(r'"([^"]+)"')
# The record may be held in a local (`$l_p_Ptr`) or handed in as a parameter (`$a_p_ItemPtr`), and
# GwAu3 uses both spellings depending on the function. An earlier version accepted only the local
# form, so `Item_GetItemInfoByPtr` -- whose record *is* its parameter -- parsed one case out of 39.
MEMORY_READ = re.compile(
    r"Memory_Read\(\s*\$(?P<base>\w+)(?P<expr>(?:\s*\+\s*(?:0x[0-9A-Fa-f]+|\d+))*)\s*,\s*\"(?P<type>[^\"]+)\""
)
# The offset is a **sum**, not one term: an array's count is written `$l_p_Ptr + 0x52C + 0x8`. A
# pattern that stopped at the first term reported 20 of `World_GetWorldInfo`'s keys as unrepresented --
# and an unrepresented key is answered `0` by the accessor's `Case Else`, which is a wrong count.
OFFSET_TERM = re.compile(r"\+\s*(0x[0-9A-Fa-f]+|\d+)")


def _resolve_offset(expression: str) -> int:
    """The offset a ``Memory_Read`` addresses, summing every ``+`` term it carries."""

    total = 0
    for term in OFFSET_TERM.findall(expression or ""):
        total += int(term, 16) if term.lower().startswith("0x") else int(term)
    return total

WIDTHS = {"byte": "B", "word": "H", "short": "h", "Short": "h", "long": "i", "dword": "I", "float": "f", "ptr": "I"}
ARRAY_WIDTH = re.compile(r"^(?P<type>\w+)\[(?P<count>\d+)\]$")


@dataclass(frozen=True)
class Family:
    """One GwAu3 field-name accessor, and what this project answers it from.

    ``structure`` is the module and class name of the record whose offsets are matched;
    ``record_call`` is the Python that produces one -- the emitted accessor's only project-specific
    line, and the reason this is a specification rather than a second implementation.
    """

    module: str
    """The generated module's file name, without the extension (``data_skill``)."""

    source_file: str
    """The GwAu3 file the function is declared in."""

    function: str
    """The GwAu3 function name, reproduced exactly."""

    structure: tuple[str, str]
    """``(module path under py4gw, class name)`` -- the record the offsets are matched against."""

    record_call: str
    """Python that returns one record, or ``None``, with ``{record_id}`` standing for the caller's id.

    A template rather than a literal because a family's record is keyed by the caller's argument: the
    skill table is indexed by the skill id, the party context is not keyed at all. The emitted
    accessor substitutes its own parameter name, so the generated line is always the same shape.
    """

    guard: str = ""
    """An extra guard the source makes before the switch, reproduced verbatim when it is one line."""

    unimplemented: dict[str, str] = field(default_factory=dict)
    """Keys this family refuses, with the reason -- a wrong value of the right type is undetectable."""

    boolean_keys: tuple[str, ...] = ()
    """Keys whose case answers a boolean from a masked word; the reason is emitted with them."""

    masks: dict[str, tuple[str, int]] = field(default_factory=dict)
    """``{key: (attribute, bit)}`` for a key whose case is ``BitAND(attribute, bit) <> 0``.

    Generated as a real function naming the attribute literally, so nothing reaches a field through a
    dynamic name. The bit is GwAu3's own literal from the case it belongs to.
    """

    equalities: dict[str, tuple[str, int]] = field(default_factory=dict)
    """``{key: (attribute, value)}`` for a key whose case is ``If attribute <> value Then Return False``.

    A third shape, and it needs its own table for the same reason the masks do: the offset alone says
    which field, not what the case *answers*. `Item_GetItemInfoByPtr`'s `IsMaterial` reads the type
    byte at ``+0x20`` and compares it to 11 -- so a reader that returned the byte would answer a
    number where GwAu3 answers a boolean, which is a wrong value of a plausible type.
    """

    flags: dict[str, str] = field(default_factory=dict)
    """``{key: expression}`` for a key whose case is a boolean over a bitmask word.

    A fifth shape, and it exists because GwAu3's flag tests are **not** all ``BitAND``:
    `IsOnWorldMap` is ``BitAND(flags, 0x20) = 0`` -- a *false* when the bit is set, the negation of its
    neighbours -- and `HasEnterButton` is ``BitAND(flags, 0x100) <> 0 Or BitAND(flags, 0x40000) <> 0``,
    two bits rather than one. A single ``(attribute, bit)`` pair cannot express either, so the expression
    is written out and the attribute it reads stays literal.
    """


    text_handshake: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    """``{key: (request, ready, get)}`` -- the port's own name-decode handshake, by function name.

    A decode is **not a read**. `PyItem.GetName` answers `""` until `PyItem.RequestName` has filled its
    map (`py4gw/item.py:394`, `:449`), and a caller that reads without requesting gets an empty string
    it cannot tell from a nameless item. So the generated reader runs the same three steps the port
    runs -- request, poll until ready, take the value -- against the port's own functions, which carry
    the source's own `"Timeout"` literal and its timeout bound.

    Written out per key because the three function names differ per family and per field, and because
    picking them is the decision this used to refuse over.
    """

    pointer_reads: dict[str, str] = field(default_factory=dict)
    """``{key: expression}`` for a key whose case reads *through* a pointer at its offset.

    GwAu3's `Rarity` reads a pointer at ``+0x38`` and then a `ushort` at the address it points to. An
    offset-resolved reader would answer the pointer, so these are written out instead of resolved.
    """

    false_on_missing: tuple[str, ...] = ()
    """Keys that answer `False` -- not `0` -- when no record matches, because GwAu3 does.

    `Quest_GetQuestInfo` has a guard before its walk: when no quest matched, `HasQuest` returns `False`
    and every other key returns `0` (``GwAu3_Data_Quest.au3:16-21``). The distinction matters to an
    AutoIt caller that tests `If Not $x`, which treats both the same, and to one that compares against
    `False` explicitly, which does not.
    """

    computed: dict[str, str] = field(default_factory=dict)
    """``{key: python}`` for a key whose case combines other keys, expressed over this module's own
    accessor. GwAu3's own expression, transcribed."""

    summary: str = ""
    """One line for the generated module's docstring, saying what the family covers."""

    record_arg: str = "record_id: Any"
    """The accessor's first parameter, as written.

    Families differ here and it is GwAu3's own signature that decides: every reader takes the record's
    id first, except the two whose only parameter is the field name -- `World_GetWorldInfo`, whose
    record is a singleton (`GwAu3_Data_World.au3:10` -- ``Func World_GetWorldInfo($a_s_Info = "")``),
    and `Party_GetPartyContextInfo`, declared ``Func Party_GetPartyContextInfo($a_s_Info = "")``
    (`GwAu3_Data_Party.au3:4`). Giving one an id parameter shifts the caller's argument into the wrong
    slot: the first version emitted a two-parameter `World_GetWorldInfo` and
    `World_GetWorldInfo("PlayerArray")` read the *key* as the record id, so the refusal test never
    reached the accessor's refusal branch.

    **`Party_GetPartyContextInfo` was emitted with an id parameter until the first live run
    (2026-10-09)**, on the same wrong assumption. That one is worse than it looks: a migrating script's
    own call is `Party_GetPartyContextInfo("IsHardMode")`, which under the two-parameter signature
    answers `0` -- GwAu3's own empty-key guard -- with no error, so every party flag a script reads
    would silently be zero. It is emitted without one now.
    """

    extra_imports: tuple[str, ...] = ()
    """Imports the hand-written expressions in this family need, beyond the structure and the client.

    `data_item`'s name keys go through this project's own decode route (`Item.GetName` and its
    siblings), so the module has to import it. Declared per family rather than guessed at: a generated
    module referencing an unimported name would fail at the *call* rather than at import, which is the
    harder failure to notice.
    """

    helpers: str = ""
    """Hand-written module-level helpers the generated module needs, emitted after ``_read_raw``.

    Written out in the spec rather than generated, because a helper is where judgement lives: the item
    family's record lookup is a traversal whose shape is this project's, and the source's reads it with
    a pointer walk of its own.
    """

    helper_files: tuple[str, ...] = ()
    """Hand-written source this family carries, read from ``tools/gwa3_snippets/<name>`` at run time.

    **A file rather than a literal, because the helpers have docstrings.** The item family carries five
    resolvers, and each opens with a triple-quoted docstring: embedding that inside the generator's own
    triple-quoted template is a quoting problem with no good answer, and escaping it by hand across 155
    lines is where a line gets lost. Kept beside the generator as generator *input* -- the same standing
    as the ``.au3`` sources it reads -- and emitted verbatim into the module it belongs to.
    """

    extra_exports: tuple[str, ...] = ()
    """Hand-written names this family's module exports beside the accessor, added to ``__all__``.

    A family is one source file, and a source file may declare more than one function a migrating
    script calls: `GwAu3_Data_Item.au3` declares `Item_GetItemInfoByItemID` **and** the resolvers every
    ``Item_*`` call goes through (`Item_ItemID`, `Item_GetItemPtr`, `Item_GetItemInfoByPtr`) and the bag
    readers its kit searches use (`Item_GetBagPtr`, `Item_GetBagInfo`). They live in the same generated
    module as the accessor -- one module per source file, as the spec requires -- which is why the names
    are declared here rather than in a module of their own.
    """

    source_function: str = ""
    """The function the ``Switch`` is actually in, when the public name delegates to it.

    ``Item_GetItemInfoByItemID`` resolves an item pointer and then calls ``Item_GetItemInfoByPtr``,
    which holds the ``Switch``. Both take the same arguments in the same order, so the cases are read
    from the second while the generated routine keeps the first one's name -- which is what a script
    calls. Empty means the public name holds the ``Switch`` itself.
    """

    @property
    def exported(self) -> list[str]:
        """``__all__``: the accessor first, then this family's hand-written names."""

        return [self.function, *self.extra_exports]


def _signature(family: "Family") -> str:
    """The accessor's parameter list, as GwAu3 writes it.

    Every reader takes the record's id first and the field name second -- except
    `World_GetWorldInfo`, whose only parameter is the field name because the world context is a
    singleton (``GwAu3_Data_World.au3:10``, ``Func World_GetWorldInfo($a_s_Info = "")``). Emitting a
    record-id parameter for that one shifts the caller's argument into the wrong slot: the first
    version did, and `World_GetWorldInfo("PlayerArray")` read the *key* as a record id, so its refusal
    never fired.
    """

    if family.record_arg:
        return f'{family.record_arg}, info: str = ""'
    return 'info: str = ""'


def _world_array_keys() -> dict[str, str]:
    """``{key: reason}`` for every ``World_GetWorldInfo`` key whose case returns an array address.

    Derived from GwAu3's own source and the structure's own offsets, rather than listed by hand: a
    hand-written list is a second surface to keep in step, and a key that is declared and *not* refused
    would be answered with a client address where a caller expects data.

    The test is narrow -- a ``ptr`` read at an offset **the structure does not name**. A ``ptr`` read
    GwAu3 makes at an offset the structure *does* name is a field like any other, and a plain read at
    such an offset is not an address at all.
    """

    import ctypes
    import importlib

    module = importlib.import_module("py4gw.context.world_context")
    structure = module.WorldContextStruct

    primitives = (
        ctypes.c_byte, ctypes.c_ubyte, ctypes.c_short, ctypes.c_ushort,
        ctypes.c_int, ctypes.c_uint, ctypes.c_long, ctypes.c_ulong,
        ctypes.c_longlong, ctypes.c_ulonglong, ctypes.c_float, ctypes.c_double,
    )
    # Every offset a *named* value occupies: a scalar field, or a scalar member of a nested structure --
    # but **only when the nested type is an array container or a plain struct, and never a container's
    # own `m_buffer`**.
    #
    # That exclusion is the whole point. `players_array.m_buffer` sits at the array's own offset, so a
    # descent that accepted any primitive member made `PlayerArray` -- a key whose case returns the
    # array's *address* -- resolve to the buffer pointer. It is the same false positive that once made
    # a party's `Flags` answer `henchmen_array.m_buffer`: a value of the right type naming the wrong
    # thing, which no caller can detect.
    CONTAINER_SIGNATURES = ("m_buffer", "m_size", "m_capacity")

    named: set[int] = set()
    for cls in structure.__mro__:
        for name, declared in getattr(cls, "_fields_", None) or []:
            descriptor = getattr(structure, name, None)
            offset = getattr(descriptor, "offset", None)
            if not isinstance(offset, int):
                continue
            if declared in primitives:
                named.add(offset)
                continue
            inner_names = [entry[0] for entry in getattr(declared, "_fields_", None) or []]
            is_container = all(member in inner_names for member in CONTAINER_SIGNATURES)
            if is_container:
                # The wrapper's own count member is a real answer -- `PlayerArraySize` is exactly that,
                # and GwAu3 reads it at the wrapper plus 8. Only the buffer address is not.
                inner = getattr(declared, "m_size", None)
                inner_offset = getattr(inner, "offset", None)
                if isinstance(inner_offset, int):
                    named.add(offset + inner_offset)
                continue
            for inner_name, inner_type in getattr(declared, "_fields_", None) or []:
                if inner_type not in primitives:
                    continue
                inner_offset = getattr(getattr(declared, inner_name, None), "offset", None)
                if isinstance(inner_offset, int):
                    named.add(offset + inner_offset)

    reasons: dict[str, str] = {}
    path = GWAU3_DATA_DIR / "GwAu3_Data_World.au3"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("Func World_GetWorldInfo("))
    end = next(index for index in range(start, len(lines)) if lines[index].strip() == "EndFunc")

    pending: tuple[str, ...] | None = None
    for index in range(start, end):
        line = lines[index]
        match = CASE_LINE.match(line)
        if match and not line.strip().startswith("Case Else"):
            keys = tuple(KEY.findall(match.group("keys")))
            if keys:
                pending = keys
                continue
        if pending is None:
            continue
        read = MEMORY_READ.search(line)
        if read is None:
            continue
        key = pending[0]
        offset = _resolve_offset(read.group("expr"))
        if read.group("type") == "ptr" and offset not in named:
            reasons[key] = (
                f"GwAu3_Data_World.au3:{index + 1} returns the client *address* of an array this "
                f"project's `WorldContextStruct` holds as a field "
                f"(`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a "
                f"reader bound to the address, which this layer does not do -- and answering the address "
                f"itself would be a value a caller could not tell from data. Refused."
            )
        pending = None
    return reasons


FAMILIES: tuple[Family, ...] = (
    Family(
        module="data_skill",
        source_file="GwAu3_Data_Skill.au3",
        function="Skill_GetSkillInfo",
        summary=(
            "GwAu3's skill-table reader. The record is the client's own constant skill table, one "
            "0xA4-byte entry per skill id, which this project reads as `SkillStruct`.\n\n"
            "The file's **skillbar** reader is carried as a snippet "
            "(`tools/gwa3_snippets/data_skill_skillbar.py`): `Skill_GetSkillbarInfo` -- the stride walk "
            "UtilityAI's slot loop asks what is on a skillbar -- and `Skill_GetSkillTimer`, the clock a "
            "slot's recharge timestamp is measured against. Both are over the port's own structures, "
            "whose strides are GwAu3's: `SkillbarStruct` ``0xBC`` and `SkillbarSkillStruct` ``0x14``."
        ),
        structure=("context.skill_context", "SkillStruct"),
        record_call="client.read_skill(int({record_id}))",
        extra_exports=("Skill_GetSkillTimer", "Skill_GetSkillbarInfo"),
        helper_files=("data_skill_skillbar.py",),
        extra_imports=(
            "from .data_agent import Agent_GetMyID",
            "from .data_party import Party_GetMyPartyHeroInfo",
        ),
    ),
    Family(
        module="data_item",
        source_file="GwAu3_Data_Item.au3",
        function="Item_GetItemInfoByItemID",
        source_function="Item_GetItemInfoByPtr",
        summary=(
            "GwAu3's item reader. The public name resolves an item pointer and then calls "
            "`Item_GetItemInfoByPtr`, which holds the ``Switch``; both take the same arguments in the "
            "same order, so the cases come from the second and the routine keeps the first one's name "
            "-- which is what a script calls.\n\n"
            "This project reads the same record as `ItemStruct`, and its offsets match GwAu3's exactly "
            "(item id at ``+0x0``, agent id at ``+0x4``, bag at ``+0xC``, model file id at ``+0x1C``, "
            "type at ``+0x20``, value at ``+0x24``, model id at ``+0x2C``)."
        ),
        structure=("context.item_context", "ItemStruct"),
        record_call="_find_item(client.read_item_records(), int({record_id}))",
        helpers='''

def _find_item(records: list[ItemStruct], item_id: int) -> ItemStruct | None:
    """The one item record whose id matches, from the inventory records read now.

    GwAu3 walks ``BasePointer -> 0x18 -> 0x40 -> 0xB8 -> 4 * item_id`` to reach an item pointer. This
    project reads the bags and their records (``py4gw/client.py:1621``, ``read_item_records``) and
    picks the entry with the id -- from a traversal made on **every** call, because a stored record is
    a dereferenced read and this project does not keep those.
    """

    for record in records:
        if record.item_id == item_id:
            return record
    return None
''',
        masks={
            "IsIdentified": ("interaction", 0x1),
            "IsStackable": ("interaction", 0x2),
            "IsInscribable": ("interaction", 0x80000),
            "IsCommonMaterial": ("interaction", 0x2000000),
        },
        equalities={
            "IsMaterial": ("type", 11),
        },
    # `Item_RequestName` -> `Item_IsNameReady` -> `Item_GetName` is the port's own name handshake
    # (`py4gw/item.py:773`, `:779`, `:785`), which carries the source's own `"Timeout"` literal and
    # its 1000 ms bound. `CompleteName` and `SingleItemName` take the same handshake because the port
    # offers one name route -- the encoded variants are separate keys and stay refused.
        text_handshake={
            "Name": (
                "Item.RequestName(record_id)",
                "Item.IsNameReady(record_id)",
                "Item.GetName(record_id)",
            ),
            "CompleteName": (
                "Item.RequestName(record_id)",
                "Item.IsNameReady(record_id)",
                "Item.GetName(record_id)",
            ),
            "SingleItemName": (
                "Item.RequestName(record_id)",
                "Item.IsNameReady(record_id)",
                "Item.GetName(record_id)",
            ),
        },
        # `Item_GetItemInventoryID` walks a bag record to the inventory that owns it, so the two records
        # it binds -- `BagStruct` and `InventoryStruct` -- are imported beside the item's own, and
        # `Item_GetInventoryIDByAgentID` resolves its id through this layer's own `Agent_ConvertID` and
        # `Agent_GetMyID` (`py4gw/gwa3/data_agent.py`), which is the pair GwAu3's body calls.
        extra_imports=(
            "import ctypes",
            "from ..context import BagStruct, InventoryStruct",
            "from ..item import Item",
            "from .data_agent import Agent_ConvertID, Agent_GetMyID",
        ),
        extra_exports=(
            "Item_GetBagInfo",
            "Item_GetBagItemArray",
            "Item_GetBagPtr",
            "Item_FindItemByAgentID",
            "Item_FindItemByModelID",
            "Item_GetInventoryIDByAgentID",
            "Item_GetItemInventoryID",
            "Item_GetItemContextPtr",
            "Item_GetItemIsCommonMaterial",
            "Item_GetMaxItems",
            "Item_GetModByIdentifier",
            "Item_GetInventoryInfo",
            "Item_GetInventoryArray",
            "Item_GetInventoryPtr",
            "Item_GetItemArray",
            "Item_GetItemBySlot",
            "Item_GetItemInfoByPtr",
            "Item_GetItemPtr",
            "Item_GetModStruct",
            "Item_ItemID",
        ),
        helper_files=("data_item_resolvers.py", "data_item_readers.py"),
        pointer_reads={
            "Rarity": "record.complete_name_enc",
        },
        unimplemented={
            "Dye1": (
                "GwAu3_Data_Item.au3:605 reads a byte at ``+0x21``. This project's `ItemStruct` holds "
                "a three-byte `dye` structure at exactly that offset, so the byte is inside it and "
                "there is no attribute naming it (`py4gw/context/item_context.py:282`). Reading the "
                "structure's first byte would work but would be an offset read of a field the port "
                "chose not to name, which is the kind of answer this layer refuses rather than "
                "guesses at. It needs a named accessor on the ported class."
            ),
            "Dye2": (
                "GwAu3_Data_Item.au3:607 reads a byte at ``+0x22`` -- the second byte of the `dye` "
                "structure at ``+0x21``, which this project declares as a three-byte field without "
                "naming its parts (`py4gw/context/item_context.py:282`). Refused for the same reason "
                "as `Dye1`: it needs a named accessor on the ported class."
            ),
            "Dye3": (
                "GwAu3_Data_Item.au3:609 reads a byte at ``+0x23`` -- the third byte of the `dye` "
                "structure named at `py4gw/context/item_context.py:282`. Refused for the same reason "
                "as `Dye1`: it needs a named accessor on the ported class."
            ),
            "ExtraID": (
                "GwAu3_Data_Item.au3:610 reads a byte at ``+0x22``, the same offset as `Dye2`, and its "
                "own comment records the alias. Refused for the same reason as `Dye1`: the byte is "
                "inside a structure this project does not name its parts for "
                "(`py4gw/context/item_context.py:282`)."
            ),



        },
    ),
    Family(
        module="data_map",
        source_file="GwAu3_Data_Map.au3",
        function="Map_GetAreaInfo",
        summary=(
            "GwAu3's map-area reader. GwAu3 indexes the client's own area-info table -- its "
            "``Map_GetAreaPtr`` is ``$g_p_AreaInfo + (0x7C * $aMapID)`` -- and this project reads the same "
            "table with the same stride: `MapMethods.GetMapInfo(map_id)` walks the catalog's area-info "
            "address and materializes `AreaInfoStruct`, whose size is asserted at ``0x7C`` "
            "(`py4gw/context/instance_info_context.py:239`).\n\n"
            "Every field offset lines up: ``campaign`` at ``+0x0``, ``type`` at ``+0xC``, ``flags`` at "
            "``+0x10``, ``min_party_size`` at ``+0x18``, ``file_id`` at ``+0x68``, ``description_id`` at "
            "``+0x78``.\n\n"
            "The file's **instance** reader is carried as a snippet "
            "(`tools/gwa3_snippets/data_map_instance_info.py`): `Map_GetInstanceInfo` answers what kind of "
            "place the client is in -- outpost, explorable or loading -- from `Map.GetInstanceType`, "
            "compared with the source's own three literals. `py4gw/gwa3/uai_cache.py` and `UAI_Fight` "
            "both gate on it."
        ),
        extra_exports=(
            "Map_GetCharacterInfo",
            "Map_GetClickCoords",
            "Map_GetCurrentAreaInfo",
            "Map_GetCurrentRegionType",
            "Map_GetInstanceInfo",
            "Map_GetInstanceUpTime",
            "Map_GetLastMoveCoords",
            "Map_GetMapID",
            "Map_GetRegion",
            "Map_IsMapUnlocked",
        ),
        helper_files=(
            "data_map_instance_info.py",
            "data_map_character_info.py",
            "data_map_current_area.py",
            "data_map_stragglers.py",
        ),
        structure=("context.instance_info_context", "AreaInfoStruct"),
        record_call="MapMethods.GetMapInfo(int({record_id}))",
        extra_imports=("from ..native_src.methods.map_methods import MapMethods",),
        flags={
            # `GwAu3_Data_Map.au3`'s own flag tests. The first is the negation of its neighbours, and
            # the second tests two bits -- which is why these are expressions rather than (field, bit).
            "HasEnterButton": "(record.flags & 0x100) != 0 or (record.flags & 0x40000) != 0",
            "IsOnWorldMap": "(record.flags & 0x20) == 0",
            "IsPvP": "(record.flags & 0x40001) != 0",
            "IsGuildHall": "(record.flags & 0x800000) != 0",
            "IsVanquishableArea": "(record.flags & 0x10000000) != 0",
            "IsUnlockable": "(record.flags & 0x10000) != 0",
            "HasMissionMapsTo": "(record.flags & 0x8000000) != 0",
        },
        computed={
            # `FileID1`/`FileID2` split the file id into two bytes' worth, in GwAu3's own arithmetic
            # (`:373-379`). They re-read the field rather than a second key, so they take the record.
            "FileID1": "((record.file_id - 1) % 0xFF00) + 0x100",
            "FileID2": "int((record.file_id - 1) / 0xFF00) + 0x100",
        },
    ),
    Family(
        module="data_account",
        source_file="GwAu3_Data_Account.au3",
        function="Account_GetAccountInfo",
        summary=(
            "GwAu3's account record -- wins, losses, rating, qualifier points, rank and the tournament "
            "reward points. GwAu3 reaches it through the account context its own "
            "``Account_GetAccountContextPtr`` resolves and reads fixed offsets; this project reads the "
            "same record as `AccountInfoStruct` out of the world context it already holds "
            "(`WorldContextStruct.account_info`, ``py4gw/context/world_context.py:1651``).\n\n"
            "**The name key is a pointer in GwAu3 and a string here.** Its case reads a ``ptr`` at "
            "``+0x0`` and then a ``wchar[32]``; this answers `Player.GetAccountName` "
            "(`py4gw/player.py:573`), because this layer hands out no client address. The other six keys "
            "are the record's own fields, by offset."
        ),
        structure=("context.world_context", "AccountInfoStruct"),
        record_call="_account_info(client.read_world_context())",
        record_arg="",
        extra_exports=("Account_GetAccountContextPtr", "Account_IsSkillUnlocked"),
        helper_files=("data_account_info.py",),
        pointer_reads={"AccountName": "Player.GetAccountName()"},
        extra_imports=("from ..player import Player", "from .data_game import Game_GetGameInfo"),
    ),
    Family(
        module="data_match",
        source_file="GwAu3_Data_Match.au3",
        function="Match_GetObserverMatchInfo",
        summary=(
            "GwAu3's observer-match record -- an observer's view of a PvP match's id, map, age, scores, "
            "stats and the two team names. GwAu3 indexes its own pointer table out of the character "
            "context and reads fixed offsets; this project reads the same records as `ObserverMatch` "
            "through `CharContextStruct.observer_matches` (`py4gw/context/char_context.py:263-271`), and "
            "every key offset lands on a named field of it.\n\n"
            "**The two team names are pointers in GwAu3 and strings here**, and its two `*Ptr` keys are "
            "refused by name below rather than answered with an address. GwAu3's own chain is "
            "self-contradictory there -- it indexes the table at ``+0x24C`` while the pointer it "
            "dereferences sits at ``+0x254`` (`docs/RESEARCH.md` records the same reading), and the port "
            "names the array at ``+0x258`` -- so the record is reached through the port's own member and "
            "the disagreement is written down rather than resolved by picking a word."
        ),
        structure=("context.char_context", "ObserverMatch"),
        record_call="_observer_match(client, int({record_id}))",
        record_arg="match_number",
        helper_files=("data_match_observer.py",),
        unimplemented={
            "TeamNamesPtr": (
                "GwAu3_Data_Match.au3:52-53 answers the client address at ``+0x48``. This layer hands "
                "out no address; `Team1Name` answers the same record's own name through "
                "`ObserverMatch.team_name1_str` (`py4gw/context/char_context.py:96`)."
            ),
            "TeamNames2Ptr": (
                "GwAu3_Data_Match.au3:57-58 answers the client address at ``+0x74``. Refused for the "
                "same reason as `TeamNamesPtr`; `Team2Name` answers "
                "`ObserverMatch.team_name2_str` (`py4gw/context/char_context.py:109`)."
            ),
        },
        pointer_reads={
            "Team1Name": 'record.team_name1_str or ""',
            "Team2Name": 'record.team_name2_str or ""',
        },
    ),
    Family(
        module="data_title",
        source_file="GwAu3_Data_Title.au3",
        function="Title_GetTitleInfo",
        summary=(
            "GwAu3's title record -- a character's title points, its tier, and the two description "
            "strings. GwAu3 indexes its own title array and reads fixed offsets; this project reads the "
            "same record as `TitleStruct` (`py4gw/context/world_context.py:1329-1345`) through "
            "`Player.GetTitle` (`py4gw/player.py:998-1005`), whose own ``None`` is exactly GwAu3's "
            "out-of-range guard.\n\n"
            "**Five of the middle keys are named one word apart in the two sources, and the port's names "
            "win.** GwAu3 reads ``+0x14``, ``+0x18``, ``+0x1C`` and ``+0x20`` for `NextTitleTierIndex`, "
            "`PointsNeededNextRank`, `MaxTitleRank` and `MaxTitleTierIndex`; this project's fields of "
            "those names sit one word earlier (``+0x10``..``+0x1C``), and GwAu3's own `Unknown10` "
            "(``+0x10``, commented ``; dhuum/reforged``) lands on the port's `next_title_tier_index`. So "
            "each key answers the port's field **of its own name** and `Unknown10` answers the word "
            "GwAu3's own offset names; a live read would settle which layout the client writes. The four "
            "description keys are pointers in GwAu3 and this port's own reads of the same bytes."
        ),
        structure=("context.world_context", "TitleStruct"),
        record_call="Player.GetTitle(int({record_id}))",
        record_arg="title_number",
        extra_imports=("from ..player import Player",),
        helper_files=("data_title_info.py",),
        pointer_reads={
            "Unknown10": "record.next_title_tier_index",
            "NextTitleTierIndex": "record.next_title_tier_index",
            "NextTitleTier": "record.next_title_tier_index",
            "PointsNeededNextRank": "record.points_needed_next_rank",
            "MaxTitleRank": "record.max_title_rank",
            "MaxTitleTierIndex": "record.max_title_tier_index",
            "MaxTitleTier": "record.max_title_tier_index",
            "PointsDescriptionEnc": "record.points_desc_encoded_str",
            "PointsDescription": "record.points_desc_str",
            "TitleDescriptionEnc": "record.h0028_encoded_str",
            "TitleDescription": "record.h0028_str",
        },
    ),
    Family(
        module="data_trade",
        source_file="GwAu3_Data_Trade.au3",
        function="Trade_GetTradeInfo",
        summary=(
            "GwAu3's trade window state -- the flags word, both sides' gold and item counts, and the "
            "pending operation. GwAu3 reads the record its own ``Trade_GetTradePtr`` resolves; this "
            "project reads the same record as `TradeContextStruct` through "
            "`py4gw/client.py:1593`'s `read_trade_context`, whose offsets match GwAu3's exactly.\n\n"
            "**GwAu3's four state cases compare the whole flags word and this port's properties test "
            "bits, so the whole-word comparison is what is wire here.** With ``flags = 3`` (initiated and "
            "an offer submitted) GwAu3 answers `IsTradeInitiated` **False** while "
            "`TradeContextStruct.is_trade_initiated` answers True -- different questions, and the source's "
            "is the one a migrating script asks. `IsSubmitted` and `IsConfirmed` do agree with the port's "
            "``is_trade_offered``/``is_trade_accepted`` (the same bits 2 and 4), and they are answered by "
            "mask.\n\n"
            "**Three keys refuse rather than answer an address**: both item-array pointers and the "
            "partner's name. The item readers that would use the pointers walk the port's own "
            "`TradePlayerStruct.offered_items` instead, and the partner's name has no field here to read."
        ),
        structure=("context.trade_context", "TradeContextStruct"),
        record_call="client.read_trade_context()",
        record_arg="",
        computed={
            # GwAu3's own equalities on the whole word (`:18`, `:20`, `:22`, `:24`), kept as the source
            # writes them: they are not this port's bit tests, and the two readings disagree.
            "IsTradeClosed": "int(record.flags) == 0",
            "IsTradeInitiated": "int(record.flags) == 1",
            "IsPlayerTradeOffered": "int(record.flags) == 3",
            "IsPlayerTradeAccepted": "int(record.flags) == 7",
            # The counts live two levels down (`side.items.m_size`), which the offset table cannot
            # express, so they are written out.
            "PlayerItemCount": "int(record.player.items.m_size)",
            "PartnerItemCount": "int(record.partner.items.m_size)",
            "PendingOp": "int(record.h0004[0])",
            "IsBusy": "int(record.h0004[0]) != 0",
        },
        masks={
            "IsSubmitted": ("flags", 0x2),
            "IsConfirmed": ("flags", 0x4),
        },
        unimplemented={
            "PlayerItemsPtr": (
                "GwAu3_Data_Trade.au3:29 answers the client address at ``+0x14``. This layer hands out "
                "no address; `Trade_GetPlayerTradeItemsInfo` and `Trade_GetArrayPlayerTradeItems` walk "
                "the same array through `TradePlayerStruct.offered_items` "
                "(`py4gw/context/trade_context.py:52`)."
            ),
            "PartnerItemsPtr": (
                "GwAu3_Data_Trade.au3:36 answers the client address at ``+0x28``. Refused for the same "
                "reason; the partner item readers walk `partner_offer` "
                "(`py4gw/context/trade_context.py:142`)."
            ),
            "PartnerName": (
                "GwAu3_Data_Trade.au3:51-54 reads a pointer at ``+0x38`` and then a ``wchar[32]`` at "
                "that address. This project's `TradeContextStruct` is exactly ``0x38`` bytes (asserted "
                "at `py4gw/context/trade_context.py:200`), so it names no field there and this port has "
                "no partner-name read to route to."
            ),
        },
        extra_exports=(
            "Trade_GetTradePtr",
            "Trade_GetArrayPartnerTradeItems",
            "Trade_GetArrayPlayerTradeItems",
            "Trade_GetPartnerTradeItemsInfo",
            "Trade_GetPlayerTradeItemsInfo",
        ),
        helper_files=("data_trade_info.py",),
    ),
    Family(
        module="data_guild",
        source_file="GwAu3_Data_Guild.au3",
        function="Guild_GetMyGuildInfo",
        summary=(
            "GwAu3's guild context -- the player's guild index, rank and name, the announcement and its "
            "author, the alliance and roster sizes, the town counts, and one roster member's own fields. "
            "GwAu3 reads the record its own ``Guild_GetGuildContextPtr`` resolves; this project reads the "
            "same record as `GuildContextStruct` through `client.read_guild_context` "
            "(`py4gw/client.py:1511`), and every offset it names lands on a named field of it.\n\n"
            "**Its four pointer keys answer the record lists, not addresses** -- the alliance, the "
            "roster, the guild array and the history -- because this layer hands out no client address, "
            "and an absent array answers `[]`, which is the falsy value GwAu3's own ``Return 0`` gave a "
            "caller's guard. `Guild_GetGuildPlayerInfo` reads its roster and size through those same two "
            "keys, exactly as the source's body does."
        ),
        structure=("context.guild_context", "GuildContextStruct"),
        record_call="client.read_guild_context()",
        record_arg="",
        extra_exports=("Guild_GetGuildContextPtr", "Guild_GetGuildPlayerInfo"),
        helper_files=("data_guild_info.py",),
        pointer_reads={
            # The three wide-string keys. GwAu3 reads a ``wchar[N]`` buffer at a fixed offset; this
            # project's own record names each of them as a decoded string property, which is the same
            # buffer through the port's own read. Declared here rather than left to the offset table
            # because the table has no width for a wide character array -- the generator stopped on
            # ``KeyError: 'wchar'`` until they were named, which is the failure this entry prevents.
            "PlayerName": "record.player_name_str",
            "Announcement": "record.announcement_str",
            "AnnouncementAuthor": "record.announcement_author_str",
        },
    ),
    Family(
        module="data_world",
        source_file="GwAu3_Data_World.au3",
        function="World_GetWorldInfo",
        summary=(
            "GwAu3's world-context reader. GwAu3 resolves the world context and reads fields at fixed "
            "offsets; this project reads the same record as `WorldContextStruct`, and its offsets match "
            "GwAu3's for the **record fields** -- ``experience`` at ``+0x740``, ``current_kurzick`` at "
            "``+0x748``, ``level`` at ``+0x788``, ``current_skill_points`` at ``+0x7A8``, "
            "``player_number`` at ``+0x67C``, ``active_quest_id`` at ``+0x528``.\n\n"
            "**Most of this family's keys are refused, and they are the array addresses.** GwAu3's "
            "`WorldInfo` key is either a field of the context or the *address* of one of its arrays "
            "(`PlayerArray`, `AgentEffectsArray`, `TitleArray`, ...). This layer reads records, not "
            "addresses -- a client pointer is of no use to a caller here -- so each address key refuses "
            "and names the array it would have had to walk."
        ),
        structure=("context.world_context", "WorldContextStruct"),
        record_call="client.read_world_context()",
        record_arg="",
        extra_exports=(
            "World_GetSkillDuplicateCount",
            "World_GetWorldContextPtr",
            "World_IsSkillLearnt",
        ),
        helper_files=("data_world_stragglers.py",),
        unimplemented=_world_array_keys(),
    ),
    Family(
        module="data_quest",
        source_file="GwAu3_Data_Quest.au3",
        function="Quest_GetQuestInfo",
        summary=(
            "GwAu3's quest-log reader. GwAu3 walks ``BasePointer -> 0x18 -> 0x2C -> 0x52C`` with a "
            "``0x34`` stride and matches the quest id; this project walks the same log "
            "(`py4gw/context/world_context.py:1442`, `quest_log_array` at ``+0x52C``) and reads each "
            "entry as `QuestStruct`, whose size is exactly GwAu3's ``0x34``."
        ),
        structure=("context.world_context", "QuestStruct"),
        record_call="_find_quest(_quest_log(client), int({record_id}))",
        masks={
            "HasInfo": ("log_state", 0x1),
            "IsCompleted": ("log_state", 0x2),
            "IsCurrentQuest": ("log_state", 0x10),
            "IsPrimary": ("log_state", 0x20),
            "IsAreaPrimary": ("log_state", 0x40),
        },
        false_on_missing=("HasQuest",),
        text_handshake={
            "Name": (
                "Quest.RequestQuestName(record_id)",
                "Quest.IsQuestNameReady(record_id)",
                "Quest.GetQuestName(record_id)",
            ),
            "Location": (
                "Quest.RequestQuestLocation(record_id)",
                "Quest.IsQuestLocationReady(record_id)",
                "Quest.GetQuestLocation(record_id)",
            ),
            "LocationStr": (
                "Quest.RequestQuestLocation(record_id)",
                "Quest.IsQuestLocationReady(record_id)",
                "Quest.GetQuestLocation(record_id)",
            ),
            "Description": (
                "Quest.RequestQuestDescription(record_id)",
                "Quest.IsQuestDescriptionReady(record_id)",
                "Quest.GetQuestDescription(record_id)",
            ),
        },
        extra_imports=("from ..quest import Quest",),
        helpers='''

def _quest_log(client: Any) -> list[QuestStruct]:
    """The quest log, as the client's own ``GetQuestLog`` answers it.

    ``py4gw/native_src/quest/py_quest.py:130-144`` reaches it the same way: the world context is read
    **now** -- a stored one is a dereferenced read, which this project does not keep -- and its quest
    array is taken as a list.
    """

    world = client.read_world_context()
    if world is None:
        return []
    return list(world.quests or [])


def _find_quest(records: list[QuestStruct], quest_id: int) -> QuestStruct | None:
    """The log entry whose id matches, from the log read on **every** call.

    The same walk GwAu3 makes, over the same array: its offsets are ``0x52C`` into the world context
    with a ``0x34`` stride, and this project's `quest_log_array` sits at ``+0x52C`` with
    `QuestStruct` sized ``0x34``. A stored record is a dereferenced read, which this project does not
    keep.
    """

    for record in records:
        if int(record.quest_id) == quest_id:
            return record
    return None
''',
        unimplemented={


            "NameEnc": (
                "GwAu3_Data_Quest.au3:30-32 returns the pointer at ``+0xC``. This project names that "
                "field `name_ptr` (`py4gw/context/world_context.py:1169`), and a client address is of no "
                "use to a caller here -- the answer is refused rather than returned raw, because a "
                "caller cannot tell an address from an encoded string."
            ),

            "NPCNameEnc": (
                "GwAu3_Data_Quest.au3:36-38 returns the pointer at ``+0x10``, which this project names "
                "`npc_ptr` (`py4gw/context/world_context.py:1169`). Refused rather than returned raw: a "
                "caller cannot tell a client address from an encoded string."
            ),
            "NPCName": (
                "GwAu3_Data_Quest.au3:39-41 decodes the pointer at ``+0x10`` on the game thread. This "
                "project's decode is the request/collect handshake in "
                "`py4gw/native_src/quest/py_quest.py:242` and `:278`, whose sequencing is outstanding. "
                "Refused rather than returning the pointer."
            ),
            "DescriptionEnc": (
                "GwAu3_Data_Quest.au3:63-65 returns the pointer at ``+0x2C``, which this project names "
                "`description_ptr` (`py4gw/context/world_context.py:1169`). Refused rather than returned "
                "raw: a caller cannot tell a client address from an encoded string."
            ),

            "ObjectivesEnc": (
                "GwAu3_Data_Quest.au3:69-71 returns the pointer at ``+0x30``, which this project names "
                "`objectives_ptr` (`py4gw/context/world_context.py:1169`). Refused rather than returned "
                "raw: a caller cannot tell a client address from an encoded string."
            ),
            "Objectives": (
                "GwAu3_Data_Quest.au3:72-74 decodes the pointer at ``+0x30`` on the game thread. This "
                "project's decode is the request/collect handshake in "
                "`py4gw/native_src/quest/py_quest.py:242` and `:278`; `py4gw/quest.py:158` "
                "`GetQuestObjectives` is behind the same handshake. Refused rather than returning the "
                "pointer."
            ),
        },
    ),
    Family(
        module="data_party",
        source_file="GwAu3_Data_Party.au3",
        function="Party_GetPartyContextInfo",
        summary=(
            "GwAu3's party-**context** reader -- flags, invitation counts and the pointer to the "
            "player's own party. This project reads the same record as `PartyContextStruct`.\n\n"
            "The context points at a second record (`player_party_ptr` at ``+0x54``) which holds the "
            "member counts and arrays, and GwAu3 reads through that pointer for `PlayerCount`, "
            "`HenchmenCount`, `HeroCount`, `OtherCount` and `PlayerPartyID`. **This layer follows it** "
            "(`PartyContextStruct.player_party`, `py4gw/context/party_context.py:357-367`, a bound "
            "`PartyInfoStruct`), so those five keys answer from the party record's own fields -- the "
            "array's ``m_size`` for a count, ``party_id`` for the id.\n\n"
            "The file's **member** accessors are carried as a snippet "
            "(`tools/gwa3_snippets/data_party_my_party.py`): `Party_GetMyPartyInfo`, "
            "`Party_GetMyPartyPlayerMemberInfo`, `Party_GetMyPartyHeroInfo` and "
            "`Party_GetMyPartyHenchmanInfo` over the port's `PlayerPartyMember` (``0xC``), "
            "`HeroPartyMember` (``0x18``) and `HenchmanPartyMember` (``0x34``) -- the same strides GwAu3 "
            "multiplies by -- while `Party_GetHeroFlagInfo` refuses, naming the world array whose "
            "elements it needs. The four ``Array*PartyMember`` keys still refuse: they answer a client "
            "*address*, and `MyPartyPtr` with them."
        ),
        structure=("context.party_context", "PartyContextStruct"),
        record_call="client.read_party_context()",
        record_arg="",
        masks={
            "IsHardMode": ("flag", 0x10),
            "IsDefeated": ("flag", 0x20),
            "IsPartyLeader": ("flag", 0x80),
            "IsWaitingForMission": ("flag", 0x08),
        },
        computed={
            "TotalPartySize": (
                "return (\n"
                "        Party_GetPartyContextInfo(\"PlayerCount\")\n"
                "        + Party_GetPartyContextInfo(\"HenchmenCount\")\n"
                "        + Party_GetPartyContextInfo(\"HeroCount\")\n"
                "    )"
            ),
            # The five second-level keys, read through the party pointer the context already exposes.
            # GwAu3 reads ``Memory_Read(partyPtr + offset, type)``; each of these is the same field of the
            # same record, named by the port's own structure (`py4gw/context/party_context.py:108-120`).
            # The pointer is followed by `_party` (the snippet below), and a zero pointer answers `0` --
            # GwAu3's own ``If $l_p_PartyPtr = 0 ... Then Return 0`` guard (`GwAu3_Data_Party.au3:71`).
            "PlayerCount": (
                "int(p.players_array.m_size) if (p := _party(record)) is not None else 0"
            ),
            "HenchmenCount": (
                "int(p.henchmen_array.m_size) if (p := _party(record)) is not None else 0"
            ),
            "HeroCount": "int(p.heroes_array.m_size) if (p := _party(record)) is not None else 0",
            "OtherCount": "int(p.others_array.m_size) if (p := _party(record)) is not None else 0",
            "PlayerPartyID": "int(p.party_id) if (p := _party(record)) is not None else 0",
        },
        unimplemented={
            "MyPartyPtr": (
                "GwAu3_Data_Party.au3:35-36 returns the client address held at context ``+0x54``. This "
                "project's structure names that field `player_party_ptr` "
                "(`py4gw/context/party_context.py:257`), and a client address is of no use to a caller "
                "here -- the same shape difference `Agent_GetAgentPtr` records. Its `player_party` "
                "property (`py4gw/context/party_context.py:357-367`) is what follows it, and "
                "`Party_GetMyPartyInfo` (the next accessor in this file) is what a caller wants."
            ),
        },
        extra_exports=(
            "Party_GetPartyContextPtr",
            "Party_GetHeroFlagInfo",
            "Party_GetHeroInfo",
            "Party_GetControlledMinionsInfo",
            "Party_GetMoraleInfo",
            "Party_IsPet",
            "Party_GetMyPartyHenchmanInfo",
            "Party_GetMyPartyHeroInfo",
            "Party_GetMyPartyInfo",
            "Party_GetMyPartyPlayerMemberInfo",
            "Party_GetPetInfo",
        ),
        helper_files=("data_party_my_party.py", "data_party_members.py"),
        extra_imports=("from .data_agent import Agent_GetAgentInfo",),
    ),
)


@dataclass(frozen=True)
class FieldCase:
    keys: tuple[str, ...]
    line: int
    offset: int
    type_text: str
    attribute: str
    inner: str


def _structure_fields(family: Family) -> dict[int, tuple[str, str]]:
    """``{offset: (attribute, component)}`` for the family's structure, nested members included.

    **Only a primitive field may claim an offset.** An earlier version of this accepted any field
    covering an offset, and it produced false positives of the worst kind: in the party context,
    GwAu3's ``Flags`` at ``+0x14`` resolved to ``record.henchmen_array.m_buffer`` -- because
    ``henchmen_array`` *starts* at 0x14, so its first member sits there. ``m_buffer`` is a pointer to
    the array's storage, and party flags have nothing to do with it. The value would have been a
    plausible-looking integer read from the wrong field, which no caller could detect.

    So a candidate must be a primitive: either a scalar field, or a member of a nested structure whose
    declared type at that offset is itself a scalar. A container's internal pointer is never an answer
    to a GwAu3 field read.

    The nested members go in **first**, for the reason that also held for the agent record: a nested
    structure's first member shares its struct's offset, and GwAu3 asks for the member, not the struct.
    """

    import ctypes
    import importlib

    PRIMITIVES = (
        ctypes.c_byte, ctypes.c_ubyte, ctypes.c_short, ctypes.c_ushort,
        ctypes.c_int, ctypes.c_uint, ctypes.c_long, ctypes.c_ulong,
        ctypes.c_longlong, ctypes.c_ulonglong, ctypes.c_float, ctypes.c_double,
    )

    def is_primitive(declared_type: object) -> bool:
        return declared_type in PRIMITIVES

    def sub_fields(declared_type: object) -> list[tuple[str, object]]:
        """A struct's own ``_fields_`` as ``(name, type)`` pairs, skipping anything else.

        A ctypes structure may declare a **bitfield**, whose entry is ``(name, type, width)`` rather
        than a pair. `ItemStruct` has one, and unpacking it as a pair raised -- which is how this came
        to be written down rather than assumed.
        """

        entries = getattr(declared_type, "_fields_", None) or []
        return [(entry[0], entry[1]) for entry in entries if len(entry) == 2]

    module = importlib.import_module(f"py4gw.{family.structure[0]}")
    structure = getattr(module, family.structure[1])

    mapping: dict[int, tuple[str, str]] = {}
    declared: list[tuple[str, object]] = []
    for cls in structure.__mro__:
        for name, declared_type in getattr(cls, "_fields_", None) or []:
            if isinstance(getattr(getattr(structure, name, None), "offset", None), int):
                declared.append((name, declared_type))

    # Nested primitives first: a struct's first member shares the struct's offset.
    for name, declared_type in declared:
        offset = getattr(getattr(structure, name), "offset")
        for inner_name, inner_type in sub_fields(declared_type):
            if not is_primitive(inner_type):
                continue
            inner_offset = getattr(getattr(declared_type, inner_name), "offset", None)
            if isinstance(inner_offset, int):
                mapping[offset + inner_offset] = (name, inner_name)

    # A field may *be* a wrapper whose own first member sits at its offset: the party context's
    # `requests_count` is the first member of a `GW_Array`-shaped struct that starts at 0x28, and
    # GwAu3 reads a count at exactly 0x28. Descending into the wrapper by name finds it.
    for name, declared_type in declared:
        offset = getattr(getattr(structure, name), "offset")
        for inner_name, inner_type in sub_fields(declared_type):
            if not is_primitive(inner_type):
                continue
            inner_offset = getattr(getattr(declared_type, inner_name), "offset", None)
            if isinstance(inner_offset, int):
                mapping.setdefault(offset + inner_offset, (name, inner_name))

    # Then scalars, which fill only what nothing else claimed.
    for name, declared_type in declared:
        if not is_primitive(declared_type):
            continue
        offset = getattr(getattr(structure, name), "offset")
        mapping.setdefault(offset, (name, ""))
    return mapping


def parse_cases(family: Family) -> list[FieldCase]:
    """Every ``Case`` of the family's function that reads one field, with its offset and width.

    Read from ``family.source_function`` when the public name delegates to another function, because
    that is where the ``Switch`` lives.
    """

    holder = family.source_function or family.function
    path = GWAU3_DATA_DIR / family.source_file
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"Func {holder}("))
    end = next(index for index in range(start, len(lines)) if lines[index].strip() == "EndFunc")

    offsets = _structure_fields(family)
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
        # No `+ offset` at all means the base itself is the address -- GwAu3's first key in a `Switch`
        # often reads `Memory_Read($l_p_Ptr, "long")`, which is offset 0. And when there are terms,
        # they sum: an array's count is `+ 0x52C + 0x8`.
        offset = _resolve_offset(read.group("expr"))
        attribute, inner = offsets.get(offset, ("", ""))
        cases.append(
            FieldCase(
                keys=pending[0],
                line=pending[1],
                offset=offset,
                type_text=read.group("type"),
                attribute=attribute,
                inner=inner,
            )
        )
        pending = None
    return cases


def declared_keys(family: Family) -> set[str]:
    """Every key the family's ``Switch`` accepts, read from the source independently of the parser."""

    holder = family.source_function or family.function
    path = GWAU3_DATA_DIR / family.source_file
    text = path.read_text(encoding="utf-8", errors="replace")
    body = text.split(f"Func {holder}(", 1)[1].split("\nEndFunc", 1)[0]
    keys: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("Case ") and not stripped.startswith("Case Else"):
            keys.update(KEY.findall(stripped))
    return keys


def _reader_expression(case: FieldCase, key: str, family: Family) -> str:
    """The reader a key gets, named literally so no field is reached through a dynamic name.

    A computed key is a lambda over both the record and the caller's id, because its case re-enters
    the accessor for the keys it combines -- GwAu3's own expression does the same.
    """

    if key in family.masks or key in family.unimplemented or key in family.false_on_missing:
        return f"_read_{key.lower()}"
    if key in family.flags:
        return f"_read_{key.lower()}"
    if key in family.equalities or key in family.pointer_reads:
        return f"_read_{key.lower()}"
    if key in family.text_handshake:
        # A text key is a real function, because it runs three steps rather than one expression.
        return f"_read_{key.lower()}"
    if key in family.computed:
        # A computed case re-enters the accessor, so it is a lambda over `(record, record_id)`.
        body = family.computed.get(key, "").strip()
        inner = body[len("return ") :] if body.startswith("return ") else body
        return f"lambda record, record_id: {inner.strip()}"

    array = ARRAY_WIDTH.match(case.type_text)
    if array:
        base, count = array.group("type"), int(array.group("count"))
        if case.attribute and not case.inner:
            return f"lambda record: tuple(record.{case.attribute})"
        return f'lambda record: _read_raw(record, {case.offset:#06x}, "<{count}{WIDTHS[base]}")'

    if case.attribute and case.inner:
        return f"lambda record: record.{case.attribute}.{case.inner}"
    if case.attribute:
        return f"lambda record: record.{case.attribute}"
    return f'lambda record: _read_raw(record, {case.offset:#06x}, "<{WIDTHS[case.type_text]}")'


def render(family: Family, cases: list[FieldCase]) -> str:
    by_key: dict[str, FieldCase] = {}
    for case in cases:
        for key in case.keys:
            # A key this family refuses, or computes, must not carry the offset-resolved reader the
            # parser produced for its case. The first version let it through, so `PlayerCount`
            # answered `record.player_party_ptr` -- the pointer GwAu3 reads *through*, not the count
            # -- while the refusal and the computed sum sat unreferenced beside it.
            if key in family.unimplemented or key in family.computed:
                continue
            by_key[key] = case

    # A key with no `Case` the parser sees as a field read is added here, so the table is complete:
    # the computed ones, the refusals, and the keys GwAu3's guard answers `False` for. Missing one of
    # these means a caller gets `0` from the accessor's `Case Else` path instead of the real answer.
    placeholder = FieldCase(keys=(), line=0, offset=0, type_text="", attribute="", inner="")
    for key in (*family.computed, *family.unimplemented, *family.false_on_missing):
        by_key.setdefault(key, placeholder)

    resolvable = sum(1 for case in by_key.values() if case.attribute)
    total = len(declared_keys(family))
    structure_import = family.structure[0].split(".")[0]

    # The masked-boolean keys: a real function each, naming its attribute literally.
    mask_helpers = "".join(
        f'def _read_{key.lower()}(record: Any) -> bool:\n'
        f'    """``{family.source_file}`` -- the ``{key}`` case: ``BitAND({attribute}, {bit:#x}) <> 0``."""\n\n'
        f'    return bool(record.{attribute} & {bit:#x})\n\n\n'
        for key, (attribute, bit) in sorted(family.masks.items())
    )

    # The keys whose case combines others are emitted as lambdas over `(record, record_id)`, because
    # their expression re-enters the accessor; there is no separate helper function for them.
    computed_helpers = ""

    unimplemented_helpers = "".join(
        f'def _read_{key.lower()}(record: Any) -> Any:\n'
        f'    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""\n\n'
        f'    raise NotImplementedError(_UNIMPLEMENTED["{key}"])\n\n\n'
        for key in sorted(family.unimplemented)
    )

    # A key answered `False` when no record matches: with a record it never runs (the accessor only
    # reaches here when the record is missing), and its presence in the table is what stops the
    # accessor's `Case Else` path answering `0` instead.
    false_helpers = "".join(
        f'def _read_{key.lower()}(record: Any) -> bool:\n'
        f'    """``{family.source_file}`` -- the ``{key}`` case has no record to read, so GwAu3\'s own\n'
        f'    no-match guard answers ``False`` (``{family.source_file}``, the guard before its walk)."""\n\n'
        f'    return False\n\n\n'
        for key in sorted(family.false_on_missing)
    )

    equality_helpers = "".join(
        f'def _read_{key.lower()}(record: Any) -> bool:\n'
        f'    """``{family.source_file}`` -- the ``{key}`` case: ``{attribute} = {value}``."""\n\n'
        f'    return record.{attribute} == {value}\n\n\n'
        for key, (attribute, value) in sorted(family.equalities.items())
    )

    # The flag keys: one boolean expression per key, written in Python so the field it reads is named
    # literally. Written out rather than derived because the shapes differ -- `IsOnWorldMap` tests a bit
    # for *zero* while its neighbours test one for non-zero, and `HasEnterButton` tests two bits.
    flag_helpers = "".join(
        f'def _read_{key.lower()}(record: Any) -> bool:\n'
        f'    """``{family.source_file}`` -- the ``{key}`` case."""\n\n'
        f"    return bool({expression})\n\n\n"
        for key, expression in sorted(family.flags.items())
    )

    # The text keys go through the port's own name handshake, written out as a real function per key so
    # the three steps are visible and nothing is reached by a dynamic name.
    decoded_helpers = "".join(
        f'def _read_{key.lower()}(record: Any, record_id: Any) -> Any:\n'
        f'    """``{family.source_file}`` -- the ``{key}`` case, through this project\'s name handshake.\n\n'
        f'    The three steps are the port\'s own (`{request}`, `{ready}`, `{get}`), taken in the order\n'
        f'    that makes them work: a decode is not a read, and taking the value without requesting it\n'
        f'    answers an empty string a caller cannot tell from a nameless record.\n'
        f'    """\n\n'
        f"    return _read_text({request.split('(')[0]}, {ready.split('(')[0]}, "
        f"{get.split('(')[0]}, record_id)\n\n\n"
        for key, (request, ready, get) in sorted(family.text_handshake.items())
    )

    pointer_helpers = "".join(
        f'def _read_{key.lower()}(record: Any) -> Any:\n'
        f'    """``{family.source_file}`` -- the ``{key}`` case: the pointer read *through* ``+0x38``."""\n\n'
        f"    return {expression}\n\n\n"
        for key, expression in sorted(family.pointer_reads.items())
    )

    parts: list[str] = []
    # The hand-written expressions in a family may need an import of their own (the item family's
    # name keys go through `Item`), so they are declared in the spec and emitted here. Joined with a
    # newline because an f-string's `\n` would be literal inside the template.
    #
    # A plain `import x` is a standard-library name and is emitted beside the template's own `import
    # struct`; only the `from ..` lines belong after the structure import. Keeping the two apart is
    # what stops a generated module from reading as though `ctypes` came out of this package.
    stdlib_imports = "\n".join(
        name for name in family.extra_imports if name.startswith("import ")
    )
    extra_imports = "\n".join(
        name for name in family.extra_imports if not name.startswith("import ")
    )
    # The snippet files get their own slot, **not** appended to `family.helpers`: the template already
    # emits `helpers` further up beside the other generated helpers, so appending the files to that
    # string emitted the item family's record lookup twice -- which pyright caught as "obscured by a
    # declaration of the same name" rather than as anything a caller would see.
    snippets = ""
    for name in family.helper_files:
        snippet = SNIPPETS_DIR / name
        if not snippet.is_file():
            raise SystemExit(f"{family.module}: no such helper file: {snippet}")
        snippets += snippet.read_text(encoding="utf-8")
    parts.append(
        f'''"""GwAu3's `{family.function}`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

{family.summary}

`{family.function}` is one ``Switch`` over {total} keys in GwAu3
(``{family.source_file}``). {resolvable} of the {len(by_key)} field keys resolve to a **named
attribute** of the structure this project reads, chosen by offset against ctypes' own view of the
record. The reader for each key names its attribute literally, so nothing here reaches a field through
a dynamic name.

**The return shapes are GwAu3's.** An unknown field name answers ``0`` and a record that cannot be
resolved answers ``0`` -- AutoIt has no exceptions in this role and a script branches on the return.
A key this layer cannot answer **raises**, naming what it needs, rather than answering a wrong value
of the right type, which a caller could not detect.
"""

from __future__ import annotations

import struct
{stdlib_imports}
from typing import Any

from ..client import require_client
from ..{structure_import} import {family.structure[1]}
{extra_imports}
_UNIMPLEMENTED: dict[str, str] = {dict(family.unimplemented)!r}

_COMPUTED: frozenset[str] = frozenset({sorted(set(family.computed) | set(family.text_handshake))!r})

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset({sorted(family.false_on_missing)!r})


def _read_text(request: Any, ready: Any, get: Any, record_id: Any) -> str:
    """Run this project's name-decode handshake and answer the text it produces.

    **A decode is not a read, and this is the whole of that difference.** The port's name getters
    answer `""` until a request has been made *and* the client's decoder has answered
    (`py4gw/item.py:394`, `:449`), so the three steps are run in order:

    1. **request** -- asks the client's own decoder for this id, through the game thread;
    2. **ready** -- advances the port's polling and says whether an answer has arrived;
    3. **get** -- takes the text, which carries the source's own `"Timeout"` literal if the client
       never answered within the bound the port uses.

    A caller cannot tell an unanswered decode from a nameless record, which is exactly why this layer
    refused these keys until the handshake was wired: answering `""` early is a wrong value of the
    right type. `ready` is polled once here rather than looped, because the port's own request already
    waits its bound -- looping would only make a stalled game thread block the bridge.
    """

    request(record_id)
    ready(record_id)
    return str(get(record_id))


def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own, so a field with no
    attribute name is read from those bytes at GwAu3's own offset and width. That covers the ``hXXXX``
    fields, whose names in the port are placeholders because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values


{mask_helpers}{flag_helpers}{equality_helpers}{decoded_helpers}{pointer_helpers}{computed_helpers}{unimplemented_helpers}{false_helpers}{family.helpers}
_READERS: dict[str, Any] = {{}}
_READERS.update(
    {{
'''
    )
    for key in sorted(by_key):
        parts.append(f'        "{key}": {_reader_expression(by_key[key], key, family)},\n')
    parts.append("    }\n)\n\n\n")

    # The accessor's own first parameter names the record for every family but `World_GetWorldInfo`,
    # which has no id: it passes its field name and its `_record` ignores it. It has no computed or
    # text keys either, so the two-argument dispatch below never runs for it -- but it is written
    # against the same name so the emitted module has no undefined variable in any family.
    record_argument = 'record_id' if family.record_arg else 'info'
    parts.append(
        f'''def {family.function}({_signature(family)}) -> Any:
    """One field of the record, by GwAu3's field name (``{family.source_file}``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    record the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.

    **The key is resolved before the record is.** A key this layer refuses raises without touching the
    client, which is the whole point of refusing: a caller with no connection must still be told that
    the key is unbuilt, not that it is unconnected. The first version resolved the record first, so
    asking for a refused key without a client reported a connection error instead of the gap.
    """

    if info == "":
        return 0

    # A refused key is answered before the record is resolved, deliberately: the refusal is a fact
    # about this layer, not about the client, so a caller with no connection must still be told the
    # key is unbuilt rather than told it is unconnected. The first version resolved the record first
    # and reported a connection error for a refusal that never needed one.
    if info in _UNIMPLEMENTED:
        raise NotImplementedError(_UNIMPLEMENTED[info])

    reader = _READERS.get(info)
    if reader is None:
        return 0

    record = _record({record_argument})
    if record is None:
        # GwAu3's own no-match guard answers `False` for these keys and `0` for the rest
        # (``GwAu3_Data_Quest.au3:16-21``).
        if info in _FALSE_ON_MISSING:
            return False
        return 0

    # A computed or text key re-enters this accessor, so it is handed the caller's id too. A family
    # with no id parameter -- World_GetWorldInfo -- has none of those keys, so the branch is written
    # against whatever its own first parameter is.
    if info in _COMPUTED:
        return reader(record, {record_argument})
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``{family.record_call.format(record_id="record_id")}`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return {family.record_call.format(record_id="record_id")}

{snippets}
__all__ = {family.exported!r}
'''
    )
    return "".join(parts)


def main() -> int:
    for family in FAMILIES:
        cases = parse_cases(family)
        keys = {key for case in cases for key in case.keys}
        named = sum(1 for case in cases if case.attribute)
        declared = len(declared_keys(family))

        output = REPO_ROOT / "py4gw" / "gwa3" / f"{family.module}.py"
        output.write_text(render(family, cases), encoding="utf-8")
        print(f"Wrote {output.relative_to(REPO_ROOT)}")
        print(f"  {family.function}: {len(cases)} field cases, {len(keys)} keys in the table, {declared} declared")
        print(f"  resolved to a named attribute: {named} of {len(cases)}")
        # A key is accounted for when it is in the table. The refusals are in the table as readers
        # that raise, so they count -- reporting them as missing was wrong the first time.
        # A key is accounted for when it appears in the generated table -- the refusals appear there
        # as readers that raise. This is computed from the rendered table, not from the parser, so a
        # key no `Case` expresses as a field read (`TotalPartySize`) still counts as represented.
        table_keys = set(re.findall(r'^\s+"([^"]+)":', render(family, cases), re.MULTILINE))
        missing = sorted(declared_keys(family) - table_keys)
        print(f"  keys in the generated table: {len(table_keys)}")
        if missing:
            print(f"  KEYS NOT REPRESENTED ({len(missing)}): {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
