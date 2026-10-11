"""GwAu3's ``PreGame_*``, over the pre-game context this project already reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the family is.** ``GwAu3_Data_PreGame.au3`` is five one-line readers of the client's **pre-game
context** -- the record that exists on the character-selection screen, before a character is in the
world. GwAu3 reaches it through its own ``$g_p_PreGame`` global and then reads fixed offsets inside it.
This project reads the same record as `PreGameContextStruct`
(``py4gw/context/pre_game_context.py:104``), on demand, through `PreGameContext.read` (``:280``), which is
the port's own read -- nothing here is cached and nothing is refreshed by a loop.

**The offsets line up.** ``+0x0`` is ``frame_id``; ``+0xD8`` is ``chosen_character_index`` (``:143``);
the login-character array is the ``chars_list`` the same record resolves (``:170``), and each of its
records is `LoginCharacter`, whose ``character_name_enc`` is a ``c_uint16 * 20`` field (``:69``) -- the
same twenty wide characters GwAu3's ``WCHAR[20]`` reads at ``+0x50 + 0x78 * index`` of that array.

**Two members answer a record or a list where GwAu3 answers an address, and both say so.**
``PreGame_Ptr`` is GwAu3's context *pointer*; this answers the context itself (``None`` when the client is
not on that screen), which is what its only caller tests -- the farm script's
``If PreGame_Ptr() = 0 Then Return True`` is a truthiness test, and ``None`` answers it the same way.
``PreGame_LoginCharacterArray`` is GwAu3's array *pointer*; this answers the list of records, which is
what a caller walks. This layer hands out no client address under any name.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "PreGame_CharName",
    "PreGame_ChosenCharacter",
    "PreGame_FrameID",
    "PreGame_LoginCharacterArray",
    "PreGame_Ptr",
]


def _context() -> Any:
    """The pre-game context, read on demand, or ``None`` when the client is not on that screen."""

    from ..context.pre_game_context import PreGameContext

    return PreGameContext.read()


def PreGame_Ptr() -> Any:
    """The pre-game context (``GwAu3_Data_PreGame.au3:3-5``).

    GwAu3's whole body is one read of ``$g_p_PreGame`` and its answer is a client address. This answers
    the **record** that address holds (`PreGameContextStruct`), or ``None`` when there is none -- the
    divergence `Item_GetItemPtr` and `Agent_GetAgentPtr` already record, and the shape the source's own
    caller can use: ``If PreGame_Ptr() = 0 Then Return True`` is a truthiness test, and ``None`` answers
    it exactly as the null pointer does.
    """

    return _context()


def PreGame_FrameID() -> int:
    """The pre-game frame's id (``GwAu3_Data_PreGame.au3:7-9``).

    GwAu3 reads the dword at the context's own start; this answers `PreGameContextStruct.frame_id`
    (``py4gw/context/pre_game_context.py:108``), the same word. ``0`` when there is no context, which is
    GwAu3's answer for a null pointer too.
    """

    context = _context()
    return 0 if context is None else int(context.frame_id)


def PreGame_ChosenCharacter() -> int:
    """The index of the character the client is on (``GwAu3_Data_PreGame.au3:11-13``).

    GwAu3 reads ``+0xD8``; this answers `PreGameContextStruct.chosen_character_index`
    (``py4gw/context/pre_game_context.py:143``), the same word -- the field the farm script's
    ``PunchOut_AutoEnterSelectedCharacter`` compares a character name against.
    """

    context = _context()
    return 0 if context is None else int(context.chosen_character_index)


def PreGame_LoginCharacterArray() -> list[Any]:
    """The characters on the selection screen (``GwAu3_Data_PreGame.au3:15-17``).

    GwAu3 answers the **address** of the login-character array (``+0xE0`` of the context); this answers
    the list of `LoginCharacter` records the port reads from it
    (`PreGameContextStruct.chars_list`, ``py4gw/context/pre_game_context.py:170``). An empty list when
    there is no context, which is the null pointer's meaning for a caller that walks it.
    """

    context = _context()
    if context is None:
        return []
    return list(context.chars_list)


def PreGame_CharName(a_i_Index: Any) -> str:
    """One character's name, by its index on the screen (``GwAu3_Data_PreGame.au3:19-21``).

    GwAu3 reads ``array + 0x50 + 0x78 * index`` as ``WCHAR[20]``; this answers
    `LoginCharacter.character_name_str` (``py4gw/context/pre_game_context.py:91``) for the same index,
    which is the decoded form of the same twenty characters.

    **One guard, and it is the port's own.** GwAu3 computes an address for any index, so an index past
    the end answers whatever the client's memory happens to hold; this answers ``""`` for an index
    outside the list rather than reading another record's memory. That is the one divergence here, and it
    is recorded rather than hidden.
    """

    context = _context()
    if context is None:
        return ""

    characters = list(context.chars_list)
    index = int(a_i_Index)
    if index < 0 or index >= len(characters):
        return ""

    return str(characters[index].character_name_str)
