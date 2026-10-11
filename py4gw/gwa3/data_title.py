"""GwAu3's `Title_GetTitleInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's title record -- a character's title points, its tier, and the two description strings. GwAu3 indexes its own title array and reads fixed offsets; this project reads the same record as `TitleStruct` (`py4gw/context/world_context.py:1329-1345`) through `Player.GetTitle` (`py4gw/player.py:998-1005`), whose own ``None`` is exactly GwAu3's out-of-range guard.

**Five of the middle keys are named one word apart in the two sources, and the port's names win.** GwAu3 reads ``+0x14``, ``+0x18``, ``+0x1C`` and ``+0x20`` for `NextTitleTierIndex`, `PointsNeededNextRank`, `MaxTitleRank` and `MaxTitleTierIndex`; this project's fields of those names sit one word earlier (``+0x10``..``+0x1C``), and GwAu3's own `Unknown10` (``+0x10``, commented ``; dhuum/reforged``) lands on the port's `next_title_tier_index`. So each key answers the port's field **of its own name** and `Unknown10` answers the word GwAu3's own offset names; a live read would settle which layout the client writes. The four description keys are pointers in GwAu3 and this port's own reads of the same bytes.

`Title_GetTitleInfo` is one ``Switch`` over 16 keys in GwAu3
(``GwAu3_Data_Title.au3``). 16 of the 16 field keys resolve to a **named
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
from ..context import TitleStruct
from ..player import Player
_UNIMPLEMENTED: dict[str, str] = {}

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


def _read_maxtitlerank(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``MaxTitleRank`` case: the pointer read *through* ``+0x38``."""

    return record.max_title_rank


def _read_maxtitletier(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``MaxTitleTier`` case: the pointer read *through* ``+0x38``."""

    return record.max_title_tier_index


def _read_maxtitletierindex(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``MaxTitleTierIndex`` case: the pointer read *through* ``+0x38``."""

    return record.max_title_tier_index


def _read_nexttitletier(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``NextTitleTier`` case: the pointer read *through* ``+0x38``."""

    return record.next_title_tier_index


def _read_nexttitletierindex(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``NextTitleTierIndex`` case: the pointer read *through* ``+0x38``."""

    return record.next_title_tier_index


def _read_pointsdescription(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``PointsDescription`` case: the pointer read *through* ``+0x38``."""

    return record.points_desc_str


def _read_pointsdescriptionenc(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``PointsDescriptionEnc`` case: the pointer read *through* ``+0x38``."""

    return record.points_desc_encoded_str


def _read_pointsneedednextrank(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``PointsNeededNextRank`` case: the pointer read *through* ``+0x38``."""

    return record.points_needed_next_rank


def _read_titledescription(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``TitleDescription`` case: the pointer read *through* ``+0x38``."""

    return record.h0028_str


def _read_titledescriptionenc(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``TitleDescriptionEnc`` case: the pointer read *through* ``+0x38``."""

    return record.h0028_encoded_str


def _read_unknown10(record: Any) -> Any:
    """``GwAu3_Data_Title.au3`` -- the ``Unknown10`` case: the pointer read *through* ``+0x38``."""

    return record.next_title_tier_index



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "CurrentPoints": lambda record: record.current_points,
        "CurrentTitleTier": lambda record: record.current_title_tier_index,
        "CurrentTitleTierIndex": lambda record: record.current_title_tier_index,
        "MaxTitleRank": _read_maxtitlerank,
        "MaxTitleTier": _read_maxtitletier,
        "MaxTitleTierIndex": _read_maxtitletierindex,
        "NextTitleTier": _read_nexttitletier,
        "NextTitleTierIndex": _read_nexttitletierindex,
        "PointsDescription": _read_pointsdescription,
        "PointsDescriptionEnc": _read_pointsdescriptionenc,
        "PointsNeededCurrentRank": lambda record: record.points_needed_current_rank,
        "PointsNeededNextRank": _read_pointsneedednextrank,
        "Props": lambda record: record.props,
        "TitleDescription": _read_titledescription,
        "TitleDescriptionEnc": _read_titledescriptionenc,
        "Unknown10": _read_unknown10,
    }
)


def Title_GetTitleInfo(title_number, info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Title.au3``).

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

    ``Player.GetTitle(int(record_id))`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return Player.GetTitle(int(record_id))

"""``GwAu3_Data_Title.au3``'s **title-progress** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism the map and party snippets use: ``data_title.py`` is rewritten whole on every run, so a function
written straight into it would be lost the next time the generator ran.

**What it is.** ``Title_GetTitleInfo`` (``GwAu3_Data_Title.au3:6-48``) answers one field of one title's
progress record. GwAu3 takes the array's address and its size from its own world-info reader
(``World_GetWorldInfo("TitleArray")`` and ``("TitleArraySize")``, ``:7-8``), guards on both (``:9``), and
strides by ``0x2C`` (``:11``) -- the size its own comment records as having changed from ``0x28``
(``:4-5``).

**This project reads the same records with its own readers.** `Player.GetTitleArrayRaw`
(``py4gw/player.py:983-990``) reads the world context's ``titles_array``
(`py4gw/context/world_context.py:1554`) as a list of `TitleStruct` (``:1329-1345``), whose size is asserted
``0x2C`` exactly (``py4gw/context/world_context.py:2088``) -- GwAu3's own stride -- and `Player.GetTitle`
(``py4gw/player.py:998-1005``) answers one record by array index, with GwAu3's own bounds guard as its
``None``. The layer already answers ``World_GetWorldInfo("TitleArraySize")`` from that array's ``m_size``
(`py4gw/gwa3/data_world.py:330`) while its ``TitleArray`` key refuses, naming the address it would have
returned (``py4gw/gwa3/data_world.py:233-236``); this family answers the records themselves, which is the
same convention -- a caller wants the title, not the address of the array it sits in.

**The five middle keys are named one word apart by the two layouts, and this member answers the port's
names.** Both records are eleven words and ``0x2C`` end to end, and they agree about the four leading
fields and the two trailing pointers:

| GwAu3 key | GwAu3's offset | The port's field | The port's offset |
| --- | --- | --- | --- |
| ``Props`` | ``+0x0`` | ``props`` | ``+0x0`` |
| ``CurrentPoints`` | ``+0x4`` | ``current_points`` | ``+0x4`` |
| ``CurrentTitleTierIndex``/``CurrentTitleTier`` | ``+0x8`` | ``current_title_tier_index`` | ``+0x8`` |
| ``PointsNeededCurrentRank`` | ``+0xC`` | ``points_needed_current_rank`` | ``+0xC`` |
| ``Unknown10`` (its own comment: ``dhuum/reforged``) | ``+0x10`` | ``next_title_tier_index`` | ``+0x10`` |
| ``NextTitleTierIndex``/``NextTitleTier`` | ``+0x14`` | ``next_title_tier_index`` | **``+0x10``** |
| ``PointsNeededNextRank`` | ``+0x18`` | ``points_needed_next_rank`` | **``+0x14``** |
| ``MaxTitleRank`` | ``+0x1C`` | ``max_title_rank`` | **``+0x18``** |
| ``MaxTitleTierIndex``/``MaxTitleTier`` | ``+0x20`` | ``max_title_tier_index`` | **``+0x1C``** |
| ``PointsDescriptionEnc``/``PointsDescription`` | ``+0x24`` (a pointer) | ``points_desc_ptr`` | ``+0x24`` |
| ``TitleDescriptionEnc``/``TitleDescription`` | ``+0x28`` (a pointer) | ``h0028_ptr`` | ``+0x28`` |

GwAu3's middle five names are one word later than the port's, which puts its ``Unknown10`` -- the word its
own comment says came with the client update -- exactly on the port's ``next_title_tier_index``, and makes
the port's ``h0020`` (``+0x20``) a word no GwAu3 key names. A name is the fact and an offset is where the
fact stood when the source was written -- `tools/gwa3_snippets/data_map_character_info.py:20-27` records the
same reading for the character context's four middle keys -- so each key answers the port's field **of that
name**, and ``Unknown10``, which names no fact at all, answers the port's word at GwAu3's own ``+0x10``.
The disagreement is written down here and on the member: a live read is what would settle which layout the
client writes, and the port's is the one this project reproduces from its own sources.

**The four text keys decode in GwAu3 and read plainly here.** ``PointsDescriptionEnc`` and
``TitleDescriptionEnc`` hand the pointer at ``+0x24``/``+0x28`` to ``Utils_DecodeEncString``
(``GwAu3_Core_Utils.au3:440-462``), which walks the encoded array's variable-length digits and answers the
**numeric id** they carry; ``PointsDescription`` and ``TitleDescription`` hand the same pointer to
``Utils_DecodeEncStringAsync`` (``:469-498``), the client's own decoder on the game thread, and answer the
text. This project's `TitleStruct` reads those two pointers itself -- ``points_desc_encoded_str`` /
``points_desc_str`` (``py4gw/context/world_context.py:1376``, ``:1380``) and ``h0028_encoded_str`` /
``h0028_str`` (``:1384``, ``:1388``) -- so the pair is answered from the port's own reads of the same bytes,
with the plain key answering the display-safe form. The port's third name for the first pointer,
``points_description`` (``py4gw/context/world_context.py:1370``), is that same read with no formatting.
"""


def Title_GetTitleInfo(title_number: Any = 0, info: str = "") -> Any:
    """One field of one title-progress record (``GwAu3_Data_Title.au3:6-48``).

    GwAu3's guard order is kept, and it is its reader's own: the title is resolved first (`:7-11`), and a
    missing array, a negative index or an index at or past the array's size answers ``0`` (`:9`) before the
    empty key is tested (`:12`). `Player.GetTitle` (`py4gw/player.py:998-1005`) is the port's member with
    exactly that guard -- ``None`` for an index outside the array, and an empty list when the client holds
    no titles at all -- so the two tests are one here, and an empty key answers ``0`` only after the world
    context has been read. An unrecognised key answers ``0``, GwAu3's own ``Return 0`` after its ``Switch``
    (`:47`).

    The twelve scalar keys answer the record's own fields (`:16-32`). The five middle keys' offsets
    disagree with GwAu3's and each answers the port's field of its own name; ``Unknown10``, which names no
    fact, answers the port's word at GwAu3's ``+0x10``. The four text keys answer this project's own reads
    of the two pointers GwAu3 hands to its decoders, so ``PointsDescription``/``TitleDescription`` answer
    the port's display-safe text where GwAu3 answers the client's decoded text, and the ``*Enc`` pair
    answers the encoded string where GwAu3 answers the numeric id its digits carry. The full table and the
    reasons are in the module docstring.
    """

    from ..player import Player

    title = Player.GetTitle(int(title_number))
    if title is None or info == "":
        return 0

    if info == "Props":
        return int(title.props)
    if info == "CurrentPoints":
        return int(title.current_points)
    if info == "CurrentTitleTierIndex":
        return int(title.current_title_tier_index)
    if info == "CurrentTitleTier":
        return int(title.current_title_tier_index)
    if info == "PointsNeededCurrentRank":
        return int(title.points_needed_current_rank)

    # GwAu3's ``Unknown10`` is the word at ``+0x10`` it declines to name (`:23-24`); the port names that
    # same word `next_title_tier_index` (`py4gw/context/world_context.py:1338`), so GwAu3's own offset
    # picks it and the port's name answers it.
    if info == "Unknown10":
        return int(title.next_title_tier_index)

    # The four keys whose GwAu3 offsets are one word later than the port's names: each answers the port's
    # field of that name, and the disagreement is the module docstring's table.
    if info == "NextTitleTierIndex":
        return int(title.next_title_tier_index)
    if info == "NextTitleTier":
        return int(title.next_title_tier_index)
    if info == "PointsNeededNextRank":
        return int(title.points_needed_next_rank)
    if info == "MaxTitleRank":
        return int(title.max_title_rank)
    if info == "MaxTitleTierIndex":
        return int(title.max_title_tier_index)
    if info == "MaxTitleTier":
        return int(title.max_title_tier_index)

    # The two pointers GwAu3 decodes (`:33-44`), answered by the port's own reads of the same bytes. The
    # second pointer is the word the port leaves as `h0028_ptr` (`py4gw/context/world_context.py:1344`).
    if info == "PointsDescriptionEnc":
        return title.points_desc_encoded_str
    if info == "PointsDescription":
        return title.points_desc_str
    if info == "TitleDescriptionEnc":
        return title.h0028_encoded_str
    if info == "TitleDescription":
        return title.h0028_str

    # GwAu3's own `Return 0` for anything its `Switch` does not match (`:47`).
    return 0

__all__ = ['Title_GetTitleInfo']
