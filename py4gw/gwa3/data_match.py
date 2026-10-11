"""GwAu3's `Match_GetObserverMatchInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's observer-match record -- an observer's view of a PvP match's id, map, age, scores, stats and the two team names. GwAu3 indexes its own pointer table out of the character context and reads fixed offsets; this project reads the same records as `ObserverMatch` through `CharContextStruct.observer_matches` (`py4gw/context/char_context.py:263-271`), and every key offset lands on a named field of it.

**The two team names are pointers in GwAu3 and strings here**, and its two `*Ptr` keys are refused by name below rather than answered with an address. GwAu3's own chain is self-contradictory there -- it indexes the table at ``+0x24C`` while the pointer it dereferences sits at ``+0x254`` (`docs/RESEARCH.md` records the same reading), and the port names the array at ``+0x258`` -- so the record is reached through the port's own member and the disagreement is written down rather than resolved by picking a word.

`Match_GetObserverMatchInfo` is one ``Switch`` over 22 keys in GwAu3
(``GwAu3_Data_Match.au3``). 20 of the 22 field keys resolve to a **named
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

from typing import Any

from ..client import require_client
from ..context import ObserverMatch

_UNIMPLEMENTED: dict[str, str] = {'TeamNamesPtr': "GwAu3_Data_Match.au3:52-53 answers the client address at ``+0x48``. This layer hands out no address; `Team1Name` answers the same record's own name through `ObserverMatch.team_name1_str` (`py4gw/context/char_context.py:96`).", 'TeamNames2Ptr': 'GwAu3_Data_Match.au3:57-58 answers the client address at ``+0x74``. Refused for the same reason as `TeamNamesPtr`; `Team2Name` answers `ObserverMatch.team_name2_str` (`py4gw/context/char_context.py:109`).'}

_COMPUTED: frozenset[str] = frozenset([])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset([])


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


def _read_team1name(record: Any) -> Any:
    """``GwAu3_Data_Match.au3`` -- the ``Team1Name`` case: the pointer read *through* ``+0x38``."""

    return record.team_name1_str or ""


def _read_team2name(record: Any) -> Any:
    """``GwAu3_Data_Match.au3`` -- the ``Team2Name`` case: the pointer read *through* ``+0x38``."""

    return record.team_name2_str or ""


def _read_teamnames2ptr(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["TeamNames2Ptr"])


def _read_teamnamesptr(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["TeamNamesPtr"])



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Age": lambda record: record.age,
        "Config1": lambda record: record.flags.config1,
        "Config2": lambda record: record.flags.config2,
        "Data1": lambda record: record.flags.data1,
        "Data2": lambda record: record.flags.data2,
        "Level": lambda record: record.flags.level,
        "MapID": lambda record: record.map_id,
        "MatchID": lambda record: record.match_id,
        "MatchIDDup": lambda record: record.match_id_dup,
        "Reserved": lambda record: record.flags.reserved,
        "Score1": lambda record: record.flags.score1,
        "Score2": lambda record: record.flags.score2,
        "Score3": lambda record: record.flags.score3,
        "Stat1": lambda record: record.flags.stat1,
        "Stat2": lambda record: record.flags.stat2,
        "State": lambda record: record.flags.state,
        "Team1Name": _read_team1name,
        "Team2Name": _read_team2name,
        "TeamNames2Ptr": _read_teamnames2ptr,
        "TeamNamesPtr": _read_teamnamesptr,
        "Type": lambda record: record.flags.type,
        "Version": lambda record: record.flags.version,
    }
)


def Match_GetObserverMatchInfo(match_number, info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Match.au3``).

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

    record = _record(record_id)
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
        return reader(record, record_id)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``_observer_match(client, int(record_id))`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return _observer_match(client, int(record_id))

"""``GwAu3_Data_Match.au3``'s **observer-match** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism the map and party snippets use: ``data_match.py`` is rewritten whole on every run, so a function
written straight into it would be lost the next time the generator ran.

**What it is.** ``Match_GetObserverMatchInfo`` (``GwAu3_Data_Match.au3:11-66``) answers one field of one
observer-match record -- the record the client holds while a match is being observed. GwAu3 resolves the
record first: ``Match_GetObserverMatchPtr`` (``:4-9``) walks ``$g_p_BasePointer`` by ``[0, 0x18, 0x44,
0x24C]`` and reads the pointer at ``+ ($a_i_MatchNumber * 4)`` of the table it lands on. This project reads
the **same records** through its own reader: `CharContextStruct.observer_matches`
(``py4gw/context/char_context.py:263-271``) walks the character context's ``observer_matches_array``
(``+0x258``, `py4gw/context/char_context.py:190`) and materializes each entry as `ObserverMatch`
(``:50-63``), bound to the reader so the two team-name pointers can be followed.

**The pairing convention, which is what ``Map_GetCharacterInfo("ObserverMatch")`` means.** GwAu3 hands back
the *pointer* to a match record there; this layer hands out no address, so that key answers ``0`` and names
its work (``tools/gwa3_snippets/data_map_character_info.py:71-75``, `py4gw/gwa3/data_map.py:356-358`). The
pairing is **the list of match records, indexed**: this family's first argument is the index into
`CharContextStruct.observer_matches` -- the array GwAu3's pointer table indexes -- and the record itself is
the answer, never an address.

**The record's own offsets line up key for key.** ``match_id`` ``+0x0``, ``match_id_dup`` ``+0x4``,
``map_id`` ``+0x8``, ``age`` ``+0xC``, then the fourteen words of `ObserverMatchFlags`
(``py4gw/context/char_context.py:33-46``) -- ``type`` ``+0x10`` through ``data2`` ``+0x44`` -- which is
every ``long`` GwAu3 reads at ``:16-51``. The port's ``team_name1_ptr`` is ``+0x48`` (GwAu3's
``TeamNamesPtr``), its ``team_name2_ptr`` is ``+0x74`` (its ``TeamNames2Ptr``), and its ``unknown1``
(``+0x4C``, ten words) is the gap GwAu3 never reads between them.

**One of GwAu3's own constants for this family disagrees with another, and the port's is the later one.**
Its chain ends at ``0x24C`` (``:5``) while the same project's research record already has the field as
``read at +0x254, dereferenced at +0x24C``, marked *self-contradictory* (``docs/RESEARCH.md:4365``). This
port's ``observer_matches_array`` sits at ``+0x258``, the offset the client update moved it to
(``docs/HANDOVER_GW_2026-09-30_UPDATE.md:216``), and the records are answered from there. The number is a
finding for the owner, not something reconciled by arithmetic here.

**Two keys refuse, and they are the two pointer keys.** ``TeamNamesPtr`` (``:52-53``) and
``TeamNames2Ptr`` (``:57-58``) answer a client *address*; this layer hands out none, and the two strings a
caller wants from them are answered by ``Team1Name``/``Team2Name``. ``Match_CleanTeamName`` (``:68-73``) is
declared in the same file and no script calls it -- its effect lives inside the port's two name reads -- so
it is not a member here.
"""


def _observer_match(client: Any, match_number: Any) -> Any:
    """The observer-match record at one index, from the character context read **now**.

    ``Match_GetObserverMatchPtr`` (``GwAu3_Data_Match.au3:4-9``) resolves the record from a pointer table
    indexed by ``$a_i_MatchNumber * 4`` (`:8`). This project's reader answers the same records as a list
    (`CharContextStruct.observer_matches`), so the index is the same index and a record the list does not
    hold is GwAu3's own "the pointer read answered zero" case -- ``None`` here, which its one guard answers
    ``0`` for (`:13`). Nothing is cached: a stored record is a dereferenced read, and this project keeps
    none.
    """

    matches = client.read_char_context().observer_matches
    if matches is None:
        return None
    index = int(match_number)
    if index < 0 or index >= len(matches):
        return None
    return matches[index]


def Match_GetObserverMatchInfo(match_number: Any = 0, info: str = "") -> Any:
    """One field of one observer-match record (``GwAu3_Data_Match.au3:11-66``).

    GwAu3's guard order is kept: the record is resolved first (`:12`) and its absence and an empty key are
    one guard (`:13`) -- so an empty key answers ``0`` only after the character context has been read, and a
    caller with no connection is refused by this project's own `require_client` before either test. An
    unrecognised key answers ``0``, which is GwAu3's own ``Return 0`` after its ``Switch`` (`:65`).

    The eighteen ``long`` keys are the record's own fields, offset for offset (`:16-51`), fourteen of them
    through the port's `ObserverMatchFlags`. The two team-name keys answer the port's own reads of the same
    two buffers: GwAu3 reads ``wchar[256]`` at the pointer and runs ``Match_CleanTeamName`` over it
    (`:54-56`, `:59-61`), and this answers `team_name1_str`/`team_name2_str`
    (`py4gw/context/char_context.py:96`, `:109`), which is that buffer with the encoded values kept visible
    as escapes rather than stripped of them, and ``""`` where a pointer the client does not hold gives
    GwAu3 its empty wide read.

    ``TeamNamesPtr`` and ``TeamNames2Ptr`` refuse, each naming the read that answers what a caller wants
    from the address.
    """

    match = _observer_match(require_client(), match_number)
    if match is None or info == "":
        return 0

    if info == "MatchID":
        return int(match.match_id)
    if info == "MatchIDDup":
        return int(match.match_id_dup)
    if info == "MapID":
        return int(match.map_id)
    if info == "Age":
        return int(match.age)

    # GwAu3's ``+0x10``..``+0x44`` are the fourteen words of the port's `ObserverMatchFlags`, in its own
    # order (`py4gw/context/char_context.py:33-46`).
    if info == "Type":
        return int(match.flags.type)
    if info == "Reserved":
        return int(match.flags.reserved)
    if info == "Version":
        return int(match.flags.version)
    if info == "State":
        return int(match.flags.state)
    if info == "Level":
        return int(match.flags.level)
    if info == "Config1":
        return int(match.flags.config1)
    if info == "Config2":
        return int(match.flags.config2)
    if info == "Score1":
        return int(match.flags.score1)
    if info == "Score2":
        return int(match.flags.score2)
    if info == "Score3":
        return int(match.flags.score3)
    if info == "Stat1":
        return int(match.flags.stat1)
    if info == "Stat2":
        return int(match.flags.stat2)
    if info == "Data1":
        return int(match.flags.data1)
    if info == "Data2":
        return int(match.flags.data2)

    if info == "TeamNamesPtr":
        # GwAu3 reads the pointer at ``+0x48`` and hands it back (`:52-53`). This layer answers no client
        # address, and the field is one the port already names -- so it refuses, citing both.
        raise NotImplementedError(
            "GwAu3_Data_Match.au3:52-53 answers the client **address** held at record ``+0x48``. This "
            "project names that field `team_name1_ptr` (`py4gw/context/char_context.py:60`) and this layer "
            "hands out no address: the string a caller wants from it is `Team1Name`, which reads through "
            "the same pointer as `team_name1_str` (`py4gw/context/char_context.py:96`)."
        )

    if info == "Team1Name":
        return match.team_name1_str or ""

    if info == "TeamNames2Ptr":
        # The same shape at ``+0x74`` (`:57-58`).
        raise NotImplementedError(
            "GwAu3_Data_Match.au3:57-58 answers the client **address** held at record ``+0x74``. This "
            "project names that field `team_name2_ptr` (`py4gw/context/char_context.py:62`) and this layer "
            "hands out no address: the string a caller wants from it is `Team2Name`, which reads through "
            "the same pointer as `team_name2_str` (`py4gw/context/char_context.py:109`)."
        )

    if info == "Team2Name":
        return match.team_name2_str or ""

    # GwAu3's own `Return 0` for anything its `Switch` does not match (`:65`).
    return 0

__all__ = ['Match_GetObserverMatchInfo']
