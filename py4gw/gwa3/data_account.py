"""GwAu3's `Account_GetAccountInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's account record -- wins, losses, rating, qualifier points, rank and the tournament reward points. GwAu3 reaches it through the account context its own ``Account_GetAccountContextPtr`` resolves and reads fixed offsets; this project reads the same record as `AccountInfoStruct` out of the world context it already holds (`WorldContextStruct.account_info`, ``py4gw/context/world_context.py:1651``).

**The name key is a pointer in GwAu3 and a string here.** Its case reads a ``ptr`` at ``+0x0`` and then a ``wchar[32]``; this answers `Player.GetAccountName` (`py4gw/player.py:573`), because this layer hands out no client address. The other six keys are the record's own fields, by offset.

`Account_GetAccountInfo` is one ``Switch`` over 7 keys in GwAu3
(``GwAu3_Data_Account.au3``). 7 of the 7 field keys resolve to a **named
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
from ..context import AccountInfoStruct
from ..player import Player
from .data_game import Game_GetGameInfo
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


def _read_accountname(record: Any) -> Any:
    """``GwAu3_Data_Account.au3`` -- the ``AccountName`` case: the pointer read *through* ``+0x38``."""

    return Player.GetAccountName()



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "AccountName": _read_accountname,
        "Losses": lambda record: record.losses,
        "QualifierPoints": lambda record: record.qualifier_points,
        "Rank": lambda record: record.rank,
        "Rating": lambda record: record.rating,
        "TournamentRewardPoints": lambda record: record.tournament_reward_points,
        "Wins": lambda record: record.wins,
    }
)


def Account_GetAccountInfo(info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Account.au3``).

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

    record = _record(info)
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
        return reader(record, info)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``_account_info(client.read_world_context())`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return _account_info(client.read_world_context())

"""``GwAu3_Data_Account.au3``'s readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map`'s instance and
character-info readers use: ``data_account.py`` is rewritten whole on every run, and this file is
emitted verbatim into it.

**What the file carries.** The account family is two readers a script calls and one that is plumbing:

* ``Account_GetAccountInfo`` (``GwAu3_Data_Account.au3:8-31``) is the **generated accessor's**, because
  every one of its cases is a field read at a fixed offset. GwAu3 resolves the record with
  ``World_GetWorldInfo("AccountInfo")`` (``:9``), guards ``If $l_p_Ptr = 0 Or $a_s_Info = "" Then
  Return 0`` (``:10``), and reads ``wchar[32]`` through the name pointer at ``+0x0`` (``:13-15``) or a
  dword at ``+0x4``/``+0x8``/``+0xC``/``+0x10``/``+0x14``/``+0x18`` (``:16-27``), falling through to
  ``Return 0`` (``:30``).

  This project reads the **same record** as `AccountInfoStruct`
  (`py4gw/context/world_context.py:140`, its size asserted at ``0x1C``, `:2062`) through the same world
  context field -- `WorldContextStruct.account_info` (``:1651``), which follows ``account_info_ptr``
  (``:1452``) -- and the port's seven fields are GwAu3's own seven in GwAu3's own order:
  ``account_name_ptr`` at ``+0x0``, ``wins`` at ``+0x4``, ``losses`` at ``+0x8``, ``rating`` at
  ``+0xC``, ``qualifier_points`` at ``+0x10``, ``rank`` at ``+0x14``, ``tournament_reward_points`` at
  ``+0x18`` (`:145-151`). The offset table therefore resolves all seven keys, and six of them are the
  port's own named attribute.

* ``Account_IsSkillUnlocked`` (``:33-52``) is this file's own function, below.

* ``Account_GetAccountContextPtr`` (``:4-6``) is carried below, and its body is GwAu3's own:
  ``Return Game_GetGameInfo("AccountContext")`` (``:5``). GwAu3's answer is the account context's
  *client address*; this layer hands out no address, and `Game_GetGameInfo`'s ``AccountContext`` key
  already answers **the record** that address holds, so the member answers the record -- or ``0``,
  which is GwAu3's own answer for the null context pointer.

**The one key whose answer is written out rather than offset-resolved is ``AccountName``.** GwAu3
reads a *pointer* at ``+0x0`` and then the wide string at the address it points at (``:14-15``), so an
offset-resolved reader would hand a caller the client address itself -- which this layer never
returns. The family spec declares the key in ``pointer_reads`` as `Player.GetAccountName`
(`py4gw/player.py:573`), the port's own read of that same field and the form a caller can use; GwAu3
returns the raw thirty-two-wide-character buffer where this returns the name as a string (``""``
where GwAu3's buffer would be empty).

**The family spec that carries this file**, recorded here because this file is what the generated
module's hand-written half is:

* ``module="data_account"``, ``structure=("context.world_context", "AccountInfoStruct")``,
  ``record_call="_account_info(client.read_world_context())"`` and ``record_arg=""`` -- GwAu3's own
  signature is ``Func Account_GetAccountInfo($a_s_Info = "")`` (``:8``), the field name and nothing
  else, exactly like ``World_GetWorldInfo``;
* ``extra_exports=("Account_GetAccountContextPtr", "Account_IsSkillUnlocked")`` and
  ``helper_files=("data_account_info.py",)``;
* ``pointer_reads={"AccountName": "Player.GetAccountName()"}`` with
  ``extra_imports=("from ..player import Player", "from .data_game import Game_GetGameInfo")``.
"""


def Account_GetAccountContextPtr() -> Any:
    """The account context record (``GwAu3_Data_Account.au3:4-6``).

    GwAu3's whole body is ``Return Game_GetGameInfo("AccountContext")`` (`:5`), and that is this
    member's body as well -- which is what makes it a one-line divergence rather than a new route:
    `Game_GetGameInfo` answers **the record** its ``AccountContext`` key names
    (`py4gw/gwa3/data_game.py:185`, read through `client.read_account_context`, ``py4gw/client.py:1671``)
    rather than the client address it resolves from, so this answers `AccountContextStruct`
    (`py4gw/context/account_context.py:61`, read on demand by `AccountContext.read`, `:227`) -- the
    record `Account_IsSkillUnlocked` reads its unlocked-skill words from (`:185`). ``0`` when the slot
    holds no pointer, which is GwAu3's own answer for a null context pointer.

    **The divergence, in one sentence:** GwAu3 hands the caller a client address and this hands back the
    record that address holds, the same substitution `World_GetWorldContextPtr`
    (`py4gw/gwa3/data_world.py:429`) and `Agent_GetAgentPtr` record.
    """

    return Game_GetGameInfo("AccountContext")


def _account_info(world: Any) -> Any:
    """The account-summary record GwAu3 resolves before its ``Switch``, or ``None``.

    GwAu3's first line is ``Local $l_p_Ptr = World_GetWorldInfo("AccountInfo")``
    (``GwAu3_Data_Account.au3:9``), and its second answers ``0`` when that pointer is ``0`` (``:10``).
    This is that pair over the port's own reader: `WorldContextStruct.account_info`
    (`py4gw/context/world_context.py:1651`) answers `AccountInfoStruct`, or ``None`` when the client
    holds no world context or no plausible pointer -- and ``None`` is what the generated accessor's own
    missing-record guard turns into GwAu3's ``0``.
    """

    if world is None:
        return None
    return world.account_info


def Account_IsSkillUnlocked(skill_id: Any) -> bool:
    """Whether the account has a skill unlocked (``GwAu3_Data_Account.au3:33-52``).

    GwAu3's own sequence, in GwAu3's own order, over this project's readers: it resolves the account
    context (``:34``) and answers ``False`` when there is none (``:35``); then it takes the
    unlocked-skills array at ``+0x124`` (``:37``), answers ``False`` for a zero array pointer (``:38``),
    forms ``Floor($a_i_SkillID / 32)`` as the word index (``:42``) and answers ``False`` when that index
    is past the array's advertised size (``:44``), and finally tests
    ``BitAND($word, 1 << Mod($a_i_SkillID, 32)) <> 0`` (``:46-51``).

    That whole walk is this port's own member: `AccountContextStruct.is_account_skill_unlocked`
    (`py4gw/context/account_context.py:185`) forms the same ``// 32`` index against
    ``unlocked_account_skill_words`` (``:160``) -- the same array, whose ``0x124`` offset is asserted at
    ``:204`` -- and makes the same single-bit test, answering ``False`` for an array it cannot read,
    which is GwAu3's ``$l_p_UnlockedSkillsArray = 0`` guard (``:38``). The context itself comes from
    the port's reader, `RemoteClient.read_account_context` (`py4gw/client.py:1671`), and its ``None``
    is GwAu3's zero context (``:35``).

    **One divergence, in the guard rather than the answer**: a negative skill id is answered ``False``
    here before anything is read, where GwAu3's arithmetic forms a negative index and reads the word
    before the array -- its flag is zero there, so both answer ``False``, but only one reads.
    """

    account_context = require_client().read_account_context()
    if account_context is None:
        return False
    return bool(account_context.is_account_skill_unlocked(int(skill_id)))

__all__ = ['Account_GetAccountInfo', 'Account_GetAccountContextPtr', 'Account_IsSkillUnlocked']
