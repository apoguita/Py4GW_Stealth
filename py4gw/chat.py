"""External port of Reforged Native's ``GW::chat``: what it sends, and what it logs.

**Source:** ``src/GW/chat/chat_methods.cpp`` and ``include/GW/chat/chat.h``, with the channel
constants from ``include/GW/common/constants/chat.h``. This file ports the half of that module
the ported ``Player`` members reach — ``GetChannel`` and the four ``SendChat`` overloads — and
leaves the rest named in ``docs/CHAT_PORT.md``: the chat history (``GetChatLog`` and the
``ChatBuffer`` it walks), the channel colours, the timestamps, the whisper receive path and the
command registry.

**What the client is handed, and how.** Every one of the source's senders builds a
``wchar_t buffer[140]`` **on its own stack** and passes its address to
``g_send_chat_func`` (``void __cdecl(wchar_t* message, uint32_t agent_id)``,
``chat_methods.cpp:88-142``; the hook and the function pointer are ``chat.cpp:26``,
``169-176`` and ``ResolveSendChatFunction``, ``chat.cpp:350-365``). Nothing of this project's
runs in the client, so the buffer is built where the source builds it *content-wise* — the same
prefix, the same clamp, the same terminator — and placed in the block's **data region**, whose
whole purpose is to be the memory inside the client a call is handed a pointer to
(``shared_block.DATA_REGION_OFFSET``). The call itself is two words, so no call form had to be
added: ``agent_id`` is the ``0`` the source passes.

That placement is not new machinery either: ``py4gw/dat_reader.py`` already hands the client a
UTF-16 string this way for the GW.dat chain, which is live-verified.

**A refusal is the source's.** ``SendChat`` answers ``false`` and sends nothing when the resolver
did not resolve, when the message is empty, or when the channel byte is not one of the seven
``GetChannel`` knows — ``GetChannel(channel) != CHANNEL_UNKNOWN`` is the source's own guard
(``chat_methods.cpp:89``), and it is made here against the same function.
"""

from __future__ import annotations

import struct
from enum import IntEnum
from typing import TYPE_CHECKING

from .game_thread.shared_block import CallForm

if TYPE_CHECKING:
    from .client import ConnectedClient

#: ``GW::chat::SendChatFn`` (``chat_methods.cpp:19``): the client's own sender. Its first
#: argument is the wide chat buffer and its second the agent id the source always passes as
#: ``0``, which is the two-word form.
SEND_CHAT_FUNC = "chat.send_chat_func"

#: ``wchar_t buffer[140]`` (``chat_methods.cpp:93``, ``116``): what the source builds on its
#: stack. The buffer is the channel byte, then the text, then a terminator, so the text can be
#: at most this many code units less the two the source keeps for those.
BUFFER_CODE_UNITS = 140

#: ``GW::Context::CHAT_LOG_LENGTH`` (``include/GW/context/chat.h``): the ring holds this many
#: messages, which is the count ``PyPlayer::RequestChatHistory`` walks
#: (``player_bindings.cpp:285``). The ported context declares the same constant.
CHAT_LOG_LENGTH = 0x200

#: ``len = len > 120 ? 120 : len`` (``chat_methods.cpp:95-96``): the source's own clamp on a
#: channel message. A longer one is **cut to 120**, not refused — the clamp is the port.
MAX_MESSAGE_CODE_UNITS = 120

#: Where the buffer goes in the block's data region. The region is shared with the other
#: callers that need a pointer in the client — the GW.dat chain keeps its hash and size words
#: at offset 0 through 12 — so this one starts past them and claims its own span.
BUFFER_OFFSET = 16


class ChatChannel(IntEnum):
    """``GW::chat::Channel`` (``common/constants/chat.h:17-35``).

    Two spellings exist in the sources and this is the Reforged Python one
    (``Py4GWCoreLib/enums_src/UI_enums.py:35-55``), which is what a ported script imports; Native
    calls the same enum ``Channel`` and spells its last member ``CHANNEL_UNKNOW`` — a typo this
    port does not carry, because Reforged's own ``CHANNEL_UNKNOWN`` names the same value.
    ``py4gw/player.py`` re-exports this class, so ``Player.ChatChannel`` is the same object and
    the two names cannot drift apart.
    """

    CHANNEL_ALLIANCE = 0
    CHANNEL_ALLIES = 1
    CHANNEL_GWCA1 = 2
    CHANNEL_ALL = 3
    CHANNEL_GWCA2 = 4
    CHANNEL_MODERATOR = 5
    CHANNEL_EMOTE = 6
    CHANNEL_WARNING = 7
    CHANNEL_GWCA3 = 8
    CHANNEL_GUILD = 9
    CHANNEL_GLOBAL = 10
    CHANNEL_GROUP = 11
    CHANNEL_TRADE = 12
    CHANNEL_ADVISORY = 13
    CHANNEL_WHISPER = 14
    CHANNEL_COUNT = 15
    CHANNEL_COMMAND = 16
    CHANNEL_UNKNOWN = -1


def GetChannel(opcode: str | int) -> ChatChannel:
    """``Channel GetChannel(char opcode)`` and its ``wchar_t`` sibling (``chat_methods.cpp:53-68``).

    The two overloads are one function in the client — the wide one casts to ``char`` and calls
    the narrow one — so they are one function here, taking the one code unit either way.
    """

    if isinstance(opcode, str):
        if len(opcode) != 1:
            raise ValueError("a channel opcode is one character.")
        code = ord(opcode)
    else:
        code = int(opcode)

    if code == ord("!"):
        return ChatChannel.CHANNEL_ALL
    if code == ord("@"):
        return ChatChannel.CHANNEL_GUILD
    if code == ord("#"):
        return ChatChannel.CHANNEL_GROUP
    if code == ord("$"):
        return ChatChannel.CHANNEL_TRADE
    if code == ord("%"):
        return ChatChannel.CHANNEL_ALLIANCE
    if code == ord('"'):
        return ChatChannel.CHANNEL_WHISPER
    if code == ord("/"):
        return ChatChannel.CHANNEL_COMMAND
    return ChatChannel.CHANNEL_UNKNOWN


def SendChat(channel: ChatChannel | int | str, message: str) -> bool:
    """``bool SendChat`` — all four overloads (``chat_methods.cpp:88-142``), as C++ resolves them.

    The overloads differ in the *type* of their first argument: a ``char`` is a channel
    **opcode**, a string is the name a whisper goes to. That is the dispatch kept here — an
    ``int`` or a :class:`ChatChannel` is one opcode byte, a one-character string is an opcode,
    and a longer string is a whisper name — with one consequence worth stating: the source's C++
    resolves ``SendChat("A", "hi")`` to the *whisper* overload, because a string literal is a
    pointer, and this port reads a one-character string as an opcode instead. Character names in
    this game are at least three characters, so nothing reachable is lost, and the divergence is
    recorded in ``docs/CHAT_PORT.md``.

    **The channel form** (``88-113``): the guard first — the sender resolved, a non-empty
    message, and an opcode ``GetChannel`` knows — then the buffer, then the call. The text is
    clamped to :data:`MAX_MESSAGE_CODE_UNITS` code units, which is the source's own clamp rather
    than a refusal. Note what the channel argument is *not*: a ``ChatChannel`` value is not an
    opcode, so ``SendChat(ChatChannel.CHANNEL_ALL, ...)`` is refused here exactly as the source's
    own guard refuses it — ``CHANNEL_ALL`` is ``3``, and ``GetChannel(3)`` is ``CHANNEL_UNKNOWN``.
    The opcodes are ``!``, ``@``, ``#``, ``$``, ``%``, ``"`` and ``/``.

    **The whisper form** (``115-142``): ``swprintf(buffer, 140, L"\\"%s,%s", from, msg)`` — the
    leading quote and the comma are the client's own whisper syntax, and the whole formatted
    buffer is what is bounded, because that is the buffer ``swprintf`` writes.
    """

    from .client import require_client

    client = require_client()
    if not message:
        return False
    if not client.resolves(SEND_CHAT_FUNC):
        return False

    if isinstance(channel, str) and len(channel) != 1:
        # ``SendChat(const wchar_t* from, const wchar_t* msg)``: the whisper form.
        if not channel:
            return False
        text = f'"{channel},{message}'
        if len(text) >= BUFFER_CODE_UNITS:
            return False
    else:
        opcode = ord(channel) if isinstance(channel, str) else int(channel) & 0xFF
        if GetChannel(opcode) is ChatChannel.CHANNEL_UNKNOWN:
            return False
        text = chr(opcode) + message[:MAX_MESSAGE_CODE_UNITS]

    address = _place(client, text)
    client.call_function(SEND_CHAT_FUNC, CallForm.U32_U32, address, 0)
    return True


def _place(client: ConnectedClient, text: str) -> int:
    """Write the chat buffer into the client, and answer its address.

    The source's buffer is 140 code units and its callers fill it with a terminator, so a buffer
    that would not fit is refused rather than truncated: half a chat line is a different message.
    """

    if len(text) + 1 > BUFFER_CODE_UNITS:
        raise ValueError(
            f"a chat buffer holds {BUFFER_CODE_UNITS} code units including its terminator; "
            f"{len(text) + 1} were needed."
        )
    return client.bridge.write_data(
        BUFFER_OFFSET, text.encode("utf-16-le") + b"\x00\x00"
    )


# ── writing a line into the client's own chat log ────────────────────────────
#
# The other direction of this module: ``GW::chat::WriteChat`` / ``WriteChatEnc``
# (``chat_methods.cpp:156-202``) put a line the *runtime* produced into the client's chat log,
# which is what ``Player.SendFakeChat`` and ``Player.SendFakeChatColored`` are. Nothing is sent
# anywhere — the line exists only in this client's log.

#: ``ui::UIMessage::kWriteToChatLog`` (``constants/ui.h:62``). ``kWriteToChatLogWithSender``
#: (``0x10000080``) exists too and the source does not use it.
WRITE_TO_CHAT_LOG = 0x1000007F

#: The three pieces a log write needs, in the block's data region: the encoded line, the sender
#: form, and the 12-byte ``UIChatMessage`` the client is handed. Clear of the GW.dat chain
#: (offsets 0..12) and of the send buffer at :data:`BUFFER_OFFSET` (16, 140 code units), and inside
#: ``shared_block.DATA_SIZE``.
LOG_MESSAGE_OFFSET = 0x200
LOG_SENDER_OFFSET = 0x600
LOG_PARAM_OFFSET = 0xA00
LOG_CODE_UNITS = (LOG_SENDER_OFFSET - LOG_MESSAGE_OFFSET) // 2
LOG_PARAM_SIZE = 12

#: ``chat_methods.cpp:159,164``: ``swprintf(buffer, len, L"\x108\x107%s\x1", text)``. The two
#: leading codepoints are the encoded form's own markers and ``0x0001`` ends the literal run
#: (``ui_methods.cpp:152-159``, ``TERM_INTERMEDIATE``).
_CHAT_WRAP_HEAD = (0x0108, 0x0107)
_CHAT_SEGMENT_END = 0x0001

#: ``GW::chat::g_transient_chat_message`` (``chat.cpp:93``). It is **Native's own** state, set
#: around the send and read by Native's own ``OnUICallback_ChatLogLine`` hook (``chat.cpp:284``) so
#: that hook recognises a line the runtime wrote itself. It is module state here for the same
#: reason and set the same way; nothing reads it yet, because that hook is a member this port has
#: not reached — the marker and its reader arrive together, and no stand-in reads it meanwhile.
_transient_chat_message = 0


def _contains(encoded: list[int], needle: str) -> bool:
    """``wcsstr(encoded, needle)`` over a code-unit array (``chat_methods.cpp:181-182``)."""

    wanted = [ord(character) for character in needle]
    limit = len(encoded) - len(wanted)
    for start in range(0, limit + 1):
        if encoded[start : start + len(wanted)] == wanted:
            return True
    return False


def _sender_form(anchor: str, sender: list[int], message: list[int]) -> list[int]:
    """The markup form (``chat_methods.cpp:185-189``), codepoint for codepoint.

    ``swprintf(param.message, len, format, sender_encoded, message_encoded)`` with one of the two
    ``format`` string literals: the anchor, then the sender, then the closing tag and the message.
    """

    return [
        *_CHAT_WRAP_HEAD,
        *(ord(character) for character in anchor),
        _CHAT_SEGMENT_END,
        0x0002,
        *sender,
        0x0002,
        *_CHAT_WRAP_HEAD,
        *(ord(character) for character in "</a>"),
        _CHAT_SEGMENT_END,
        0x0002,
        *_CHAT_WRAP_HEAD,
        *(ord(character) for character in ": "),
        _CHAT_SEGMENT_END,
        0x0002,
        *message,
    ]


def WriteChat(
    channel: ChatChannel | int,
    message: str,
    sender: str | None = None,
    transient: bool = False,
) -> None:
    """``void GW::chat::WriteChat(Channel, const wchar_t*, const wchar_t*, bool)`` (``156-171``).

    The source wraps both strings before writing them — ``L"\\x108\\x107%s\\x1"`` — so the client
    receives an *encoded* line rather than the literal one, and hands both to
    :func:`WriteChatEnc`. The two allocations the source makes for those buffers have no counterpart
    here: the port builds the arrays and places them in the block, which is the same thing the
    source's ``new wchar_t[len]`` was for.
    """

    WriteChatEnc(
        channel,
        _wrap_for_log(message),
        _wrap_for_log(sender) if sender is not None else None,
        transient,
    )


def _wrap_for_log(text: str) -> list[int]:
    """``swprintf(buffer, len, L"\\x108\\x107%s\\x1", text)`` (``chat_methods.cpp:159,164``)."""

    return [*_CHAT_WRAP_HEAD, *(ord(character) for character in text), _CHAT_SEGMENT_END]


def WriteChatEnc(
    channel: ChatChannel | int,
    message_encoded: list[int],
    sender_encoded: list[int] | None = None,
    transient: bool = False,
) -> None:
    """``void GW::chat::WriteChatEnc(Channel, const wchar_t*, const wchar_t*, bool)`` (``173-202``).

    It fills a ``ui::UIChatMessage`` — ``{channel, message, channel2}``, twelve bytes
    (``context/ui.h:325-329``) — sets the transient marker, sends
    ``ui::UIMessage::kWriteToChatLog`` with a pointer to that struct and clears the marker. The line
    itself lives in the block's data region, because the client has to be able to read it.

    **The struct's first two fields are passed as the message's own payload words, not as a pointer
    to a struct.** Native can hand ``&param`` over because it calls ``SendUIMessage`` itself; this
    port's UI-message form gives the client a pointer to a payload built from the command's words
    (``payload.py:645-669``: ``SendUIMessage(arg1, &payload, 0)`` with ``payload[0] = arg2`` and
    ``payload[1] = arg3``), so ``channel`` and ``message`` are what a caller supplies. Reading the
    form the other way is what crashed the client on 2026-09-26: a pointer went in as ``arg2``, the
    client read it as ``channel`` and read ``0`` as ``message``, and its own ``message == 0`` check
    (``CtChatLog.cpp:765``, in ``AddToChatLog`` — the function the catalog resolves as
    ``chat.add_to_chat_log_func``) asserted.

    One field therefore cannot be set the way the source sets it: ``param.channel2 = param.channel``
    (``:175``) has no word of its own in a two-word payload, so it arrives zero. That is a
    divergence of the call form, recorded here and in ``docs/CHAT_PORT.md``, and whether the client
    reads it at all is what the next live check settles.

    The source's ``len`` arithmetic and its ``swprintf`` assert are the C way of making room; here
    the array is built exactly and the placement refuses a line that does not fit, which is the
    same guarantee reached by the container instead of by a return code.
    """

    from .client import require_client

    client = require_client()
    line = (
        _log_line(message_encoded, sender_encoded)
        if sender_encoded
        else list(message_encoded)
    )
    message_address = _place_code_units(
        client, LOG_MESSAGE_OFFSET, line, LOG_CODE_UNITS
    )

    global _transient_chat_message
    _transient_chat_message = message_address if transient else 0
    client.send_ui_message(WRITE_TO_CHAT_LOG, int(channel), message_address)
    _transient_chat_message = 0


def _log_line(message_encoded: list[int], sender_encoded: list[int]) -> list[int]:
    """The sender form (``chat_methods.cpp:179-194``), branch for branch."""

    if _contains(message_encoded, "<a=1>"):
        return _sender_form("<a=2>", sender_encoded, message_encoded)
    if _contains(message_encoded, "<c="):
        return _sender_form("<a=1>", sender_encoded, message_encoded)
    return [
        0x076B,
        0x010A,
        *sender_encoded,
        _CHAT_SEGMENT_END,
        0x010B,
        *message_encoded,
        _CHAT_SEGMENT_END,
    ]


def _place_code_units(
    client: ConnectedClient, offset: int, units: list[int], limit: int
) -> int:
    """Write one code-unit array into the block's data region and answer its address."""

    if len(units) + 1 > limit:
        raise ValueError(
            f"a chat log buffer at {offset:#x} holds {limit} code units including its "
            f"terminator; {len(units) + 1} were needed."
        )
    return client.bridge.write_data(
        offset,
        struct.pack(f"<{len(units)}H", *units) + b"\x00\x00",
    )


def GetChatLog():
    """``Context::ChatBuffer* GW::chat::GetChatLog()`` (``chat_methods.cpp:70-73``).

    The source's whole body is two lines — ``auto* chat_buffer_addr =
    Context::GetChatBufferAddress(); return chat_buffer_addr ? *chat_buffer_addr : nullptr;`` — so
    this is the ported ``ChatBuffer`` context, which resolves the same global
    (``chat.chat_buffer_addr``) and walks the same ring: ``messages`` is the slot table of
    :data:`CHAT_LOG_LENGTH` pointers, and each non-null slot's record carries the encoded line
    inline past its header (``py4gw/context/chat_buffer_context.py``).

    ``None`` is the source's null, which ``Player.RequestChatHistory`` handles as its own empty
    answer.
    """

    from .client import require_client

    return require_client().read_chat_buffer()


#: ``ui::UIChatMessage``'s ``message`` word (``context/ui.h:325-329``): where the string sits in the
#: packet ``kWriteToChatLog`` carries, which is the offset the observer copies from.
CHAT_LOG_LINE_FIELD_OFFSET = 4

#: The lines this connection has watched arrive, oldest first, capped at the client's own ring size.
#: Native keeps no such thing: its chat module's callback for this message
#: (``OnUICallback_ChatLogLine``, ``chat.cpp:205-230``) sets the transient marker and notifies its
#: subscribers, and the decoded history is filled only when a request is made
#: (``player_bindings.cpp:276-325``). This port keeps the lines, at the user's direction: a chat
#: history is read after the fact, so it is maintained as the client announces lines rather than
#: only when asked for.
_live_history: list[str] = []

#: The decode slots whose lines have not come back yet, in arrival order.
_live_pending: list[int] = []


def watch_entries() -> tuple[tuple[int, int], ...]:
    """The chat-log message the connection watches, and the string field it copies.

    ``kWriteToChatLog`` (``constants/ui.h:62``) is the message the client sends when a line is added
    to its own log — including the lines this port writes with :func:`SendFakeChat`, which is why
    the observer sees them too. The copy is taken inside the client's own call, the only moment the
    string is the client's (``docs/RESEARCH.md``).
    """

    return ((WRITE_TO_CHAT_LOG, CHAT_LOG_LINE_FIELD_OFFSET),)


def live_history() -> list[str]:
    """The lines watched since this connection opened, oldest first."""

    return list(_live_history)


def reset_live_history() -> None:
    """Forget the watched lines, which a fresh connection does before it starts listening."""

    _live_history.clear()
    _live_pending.clear()


def _on_chat_log_line(event: object) -> None:
    """A line the client added to its own log: hand it to the client's decoder.

    The decode is *started* here and never waited on: the client's answer arrives as a
    ``STRING_DECODED`` event, which is the port of the callback native hands ``AsyncDecodeStr``.
    Nothing blocks the listener thread, which is what lets this run on it.
    """

    if int(getattr(event, "sequence")) != WRITE_TO_CHAT_LOG:
        return
    text = getattr(event, "text")
    if not text:
        return

    from .ui.async_decode import async_decode_str, begin_string_decode

    encoded = b"".join(int(unit).to_bytes(2, "little") for unit in text)
    if not encoded.endswith(b"\x00\x00"):
        encoded += b"\x00\x00"
    slot = begin_string_decode(encoded)
    if not async_decode_str(encoded, slot):
        # Not started: the wrapper's own refusal answered the callback, which completed the slot.
        # Whether that answer counts as a line is decided where it is read, not here.
        return
    _live_pending.append(slot)


def _on_string_decoded(event: object) -> None:
    """The client's decoder answered a watched line: keep the text."""

    slot = int(getattr(event, "sequence"))
    if slot not in _live_pending:
        return
    _live_pending.remove(slot)

    from .ui.async_decode import decoded_text

    text, _ = decoded_text(slot)
    _append_live_line(text)


def _append_live_line(text: str) -> None:
    """Append one decoded line to the watched history, capped the way the client's ring is."""

    if not text:
        return
    _live_history.append(text)
    if len(_live_history) > CHAT_LOG_LENGTH:
        del _live_history[: len(_live_history) - CHAT_LOG_LENGTH]

    # The buffer the ported ``Player`` members answer from is native's own
    # (``player_bindings.cpp:273``), so a watched line goes into it — which is the one divergence
    # of that trio and is recorded on ``Player.GetChatHistory``.
    from . import player

    player._chat_history.append(text)
    if len(player._chat_history) > CHAT_LOG_LENGTH:
        del player._chat_history[: len(player._chat_history) - CHAT_LOG_LENGTH]
    player._chat_ready = True


def SendFakeChat(channel: ChatChannel | int, message: str) -> None:
    """``void GW::chat::SendFakeChat(int channel, std::string message)`` (``262-267``).

    The source converts the narrow string to wide and enqueues the write on the game thread; here
    the call already runs on the client's own thread, which is what that ``Enqueue`` was for.
    """

    WriteChat(ChatChannel(int(channel)), message, None, True)


def SendFakeChatColored(
    channel: ChatChannel | int, message: str, r: int, g: int, b: int
) -> None:
    """``void GW::chat::SendFakeChatColored(int, std::string, int, int, int)`` (``269-275``).

    ``FormatChatMessage`` runs first, exactly as the source does, and the formatted line is written
    as a transient one.
    """

    from .player import Player

    WriteChat(ChatChannel(int(channel)), Player.FormatChatMessage(message, r, g, b), None, True)
