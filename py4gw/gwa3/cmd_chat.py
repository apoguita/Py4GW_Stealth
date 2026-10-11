"""GwAu3's ``Chat_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Why hand-written.** An action is control flow with real effects; each function here is written
against GwAu3's own body with its lines cited, which is what ``cmd_agent`` records in full.

**GwAu3 reaches chat by writing a command record into a queue**, not by calling a function:
``Chat_SendChat`` writes a ``wchar[122]`` at ``queue + 12`` and a record header, and the injected stub
does the rest (``GwAu3_Cmd_Chat.au3:52-78``). This project calls the client's own sender instead.

**The channel argument is a one-character opcode string and stays one.** GwAu3 documents the set --
``'!'`` all, ``'@'`` guild, ``'#'`` team, ``'$'`` trade, ``'%'`` alliance, ``'"'`` whisper
(``GwAu3_Cmd_Chat.au3:54-55``) -- and this project's ``chat.SendChat`` takes **exactly that opcode**
(``py4gw/native_src/chat/chat.py:105``, which resolves a one-character string as an opcode). So a
migrated script's ``Chat_SendChat("hi", "!")`` reaches the same opcode by the same spelling. A caller
must **not** pass ``ChatChannel.CHANNEL_ALL``: that is ``3``, which is not an opcode, and the port's own
guard refuses it (``chat.py:130-135``).
"""

from __future__ import annotations

from ..native_src.chat import chat

__all__ = [
    "Chat_SendChat",
    "Chat_SendWhisper",
    "Chat_WriteChat",
]

# GwAu3's own bounds (`GwAu3_Cmd_Chat.au3:70`, `:26`). Its recursion trims to these and re-sends the
# tail, so a long message becomes several lines rather than being truncated -- reproduced here.
_MESSAGE_LIMIT = 120
_LOG_MESSAGE_LIMIT = 100
_LOG_SENDER_LIMIT = 19

# The register channel, and the channel a whisper is sent through (`GwAu3_Cmd_Chat.au3:47`).
_WHISPER_CHANNEL = "/"


def Chat_SendChat(message: str, channel: str = "!") -> bool:
    """Send a message to chat (``GwAu3_Cmd_Chat.au3:56-78``).

    GwAu3 writes a command record and advances its queue counter -- **before** it checks the length,
    which is why a recursive call advances it again. This calls ``chat.SendChat(channel, message)``
    (``py4gw/native_src/chat/chat.py:105``), which drives the client's own sender on the game thread.

    **The bound is GwAu3's, and it is a recursion rather than a clamp.** GwAu3 trims the message to
    ``120`` and, when it was longer, calls itself with the remainder -- so a 250-character message
    becomes two lines, not one clamped one. The port's ``SendChat`` clamps instead
    (``chat.py:139``, the source's own clamp), which would silently drop the tail, so the recursion is
    kept here and the clamp never sees more than one line's worth.

    **The return differs.** GwAu3's ``Chat_SendChat`` has no ``Return`` at all, so it answers AutoIt's
    valueless default -- ``0`` -- on every path, and its ``Return`` in ``Chat_GoPlayer``-style callers
    is meaningless. This answers ``True`` when the line was sent and ``False`` when the client refused
    it, which is information a caller can act on.
    """

    if not message:
        return False

    head, tail = message[:_MESSAGE_LIMIT], message[_MESSAGE_LIMIT:]
    sent = chat.SendChat(channel, head)
    if tail:
        # GwAu3's recursive call, in GwAu3's position -- after the write, so the order of the two lines
        # is the order the client receives them.
        return Chat_SendChat(tail, channel) and sent
    return bool(sent)


def Chat_SendWhisper(receiver: str, message: str) -> bool:
    """Send a whisper to another player (``GwAu3_Cmd_Chat.au3:35-50``).

    GwAu3 builds ``'whisper ' & $receiver & ',' & $message``, trims it to ``120`` and sends it through
    the register channel ``'/'``, recursing with the remainder when it was longer. That is kept
    verbatim: the literal ``whisper`` prefix and the comma are the client's own whisper syntax, and
    building the string here rather than calling the port's string overload keeps GwAu3's spelling in
    one place where it can be compared with GwAu3's line.
    """

    if not receiver:
        return False
    return Chat_SendChat(f"whisper {receiver},{message}", _WHISPER_CHANNEL)


def Chat_WriteChat(message: str, sender: str = "GwAu3") -> bool:
    """Write a line into the client's own chat log, visible only to this controller
    (``GwAu3_Cmd_Chat.au3:2-32``).

    GwAu3 writes the sender into a ``wchar[20]`` and the message into a ``wchar[101]`` in its queue and
    enqueues ``$g_p_WriteChatPtr`` -- a slot its own library never assigns, which is recorded in
    ``docs/RESEARCH.md:4377-4380`` and means GwAu3's own version may write nothing at all. This calls
    ``chat.WriteChat`` (``py4gw/native_src/chat/chat.py:245``), which formats the same encoded log line
    the client's own ``WriteChat`` sends.

    **This is not a chat message and no one else sees it.** ``SendFakeChat`` is the method that puts a
    line in the log the way GwAu3 means; ``WriteChat`` is the client's own log writer and takes a
    channel, so it is given the register channel, matching GwAu3's default ``sender`` of ``'GwAu3'``.

    The bounds are GwAu3's: sender ``19``, message ``100``, and the recursion over the remainder.
    """

    if not message:
        return False

    head, tail = message[:_LOG_MESSAGE_LIMIT], message[_LOG_MESSAGE_LIMIT:]
    # **`'!'` and not `ord('!')`.** GwAu3's channel argument is the *opcode character*, and the opcode
    # for the register channel is `33`; `ChatChannel` numbers are a different scale entirely
    # (`CHANNEL_ALL` is `3`, which `GetChannel` answers as `CHANNEL_UNKNOWN`). Passing the character is
    # what reaches channel `3`'s opcode; passing its ordinal would reach a channel that does not exist.
    chat.WriteChat(chat.GetChannel("!"), head, sender[:_LOG_SENDER_LIMIT])
    if tail:
        return Chat_WriteChat(tail, sender)
    return True
