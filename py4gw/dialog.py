"""Port of Reforged's ``Py4GWCoreLib/Dialog.py`` and of the surface it reaches.

Reforged's Python ``Dialog`` is a facade. Every value it returns comes from
``PyDialog`` — 32 static methods and six record classes, bound in
``src/GW/dialog/dialog_bindings.cpp`` and backed by ``src/GW/dialog/dialog.cpp``,
1,718 lines that keep dialog state by **listening to four of the client's own UI
messages** and decoding text asynchronously.

Both layers are ported here, and the split is the source's:

| layer | where it is in the source | where it is here |
| --- | --- | --- |
| facade | ``Dialog.py``: two getters, two record classes, the text sanitiser, the inline-choice parser | the module functions and the two data classes below |
| surface | ``PyDialog`` → ``dialog.cpp`` | :class:`Dialog` and the state it reads |

**``PyDialog`` is the sources' name for their module, not for a class here.** Reforged
imports that module (``Dialog.py:7-9``, with a ``None`` fallback) and Reforged Native
embeds it (``dialog_bindings.cpp:94``, its class backed by the empty ``PyDialogShim``
struct at ``:90``). This project has neither, so the surface lives in :class:`Dialog`,
named for its module the way ``Player``, ``Agent`` and ``Map`` are.

Three things are worth knowing before reading the member list.

**The state comes from messages, as it does there.** ``kDialogBody`` records the agent
and clears the button list; ``kDialogButton`` appends a button; a sent dialog is
remembered until the body that answers it arrives. The connection registers
:func:`_capture_message` and watches those two messages; the rest is ``dialog.cpp``'s
logic with its line numbers recorded at each step.

**A button needs no decoding.** The client's ``DialogButtonInfo`` packet is sixteen
bytes — ``{button_icon, message, dialog_id, skill_id}`` — so the whole packet fits in
the four words the observer records, and a button's dialog id is a word in the event.
That is why ``Player.SendAutomaticDialog`` works today while dialog *text* does not.

**The metadata tables are resolved where the source declares them.** Native keeps the five table
bases and the loader as constants in ``DialogMemory`` (``dialog.h:94-99``) and rebases them onto the
live module in ``dialog_patterns.cpp``; both of those files are ported here as they stand —
:data:`EVENT_HANDLER_BASE` … :data:`DIALOG_LOADER_GETTEXT` are the source's own numbers, and
:class:`DialogTables` is ``BuildStaticDialogTables``, ``ValidateDialogMetadataBases`` and the
``.rdata`` fallback scan. **Nothing about them lives in the pattern catalog**, because native's own
catalog does not carry them either: its pattern system has no module-base-relative op (its own note,
``dialog.h:80-85``), which is why the source keeps them in code. The text *decoder* is
ported too, and it is the client's own: the encoded string is handed back to `AsyncDecodeStr` and the
text returns through the callback stub (`py4gw/ui/async_decode.py`). One item is left, and it is
**deferred to a later pass by the project owner** — this build's `DialogLoader_GetText`, the client
function the source calls through to get a catalog dialog's text (`docs/DIALOG_PORT.md` records the
deferral and the two routes to identify it). Everything else in this module works.
"""

from __future__ import annotations

import re
import struct
import time
from collections.abc import Sequence
from typing import Any

from .game_thread.shared_block import CallForm, EventRecord, EventTextState
from .scanner import RemoteScanner

#: ``UIMessage::kDialogButton`` (``constants/ui.h:74``). Its packet is the client's
#: ``DialogButtonInfo`` — ``{button_icon, message, dialog_id, skill_id}``.
DIALOG_BUTTON_MESSAGE = 0x100000A3

#: ``UIMessage::kDialogBody`` (``constants/ui.h:75``). Its packet is
#: ``DialogBodyInfo`` — ``{type, agent_id, message_enc}``.
DIALOG_BODY_MESSAGE = 0x100000A6

#: ``UIMessage::kSendAgentDialog`` / ``kSendGadgetDialog`` (``constants/ui.h:194-195``). The
#: runtime's handler for the two is one body — the first case falls through into the second —
#: and this project reaches it through :func:`_note_sent_dialog` instead, so the message id it
#: records is the agent one. ``Player.SendDialog`` picks the gadget sender for a gadget; the
#: journal's row is the same row the source would write for either.
DIALOG_SEND_AGENT_MESSAGE = 0x30000014
DIALOG_SEND_GADGET_MESSAGE = 0x30000015

#: The dialog metadata tables (``dialog.h:86-100``). 57 dialogs, one 0x24-byte stride
#: for every column, and the five column bases the native code rebases onto the live
#: module. ``CONTENT_STRIDE`` and ``PROPERTY_STRIDE`` are their own constants in the
#: source even though they carry the same value as ``FLAGS_STRIDE``.
MAX_DIALOG_ID = 0x39
FLAGS_STRIDE = 0x24
CONTENT_STRIDE = 0x24
PROPERTY_STRIDE = 0x24

#: ``DialogMemory`` (``dialog.h:94-99``): five hardcoded client virtual addresses and the
#: loader, in the source's own order and spelling. They are rebased onto the live module by
#: ``ToRuntimeAddress`` (``dialog_patterns.cpp:25-31``), which is
#: :meth:`py4gw.scanner.remote.RemoteScanner.to_module_address`. Native holds them in code
#: rather than in its pattern catalog — its own note (``dialog.h:80-85``) says the pattern
#: system has no module-base-relative op to express them — so this port holds them in code too,
#: beside the resolution that uses them, which is where the source keeps them.
EVENT_HANDLER_BASE = 0x00913918
FRAME_TYPE_BASE = 0x0091391C
FLAGS_BASE = 0x00913920
CONTENT_ID_BASE = 0x00913924
PROPERTY_ID_BASE = 0x00913928

#: ``DialogMemory::DIALOG_LOADER_GETTEXT`` (``dialog.h:99``), the client function a catalog
#: dialog's text comes from. **``ResolveDialogLoaderGetText`` is unconditional in the source**
#: — it rebases the constant and caches the answer — and this port does the same. The constant
#: is native's, and this is not native's build: measured read-only, the rebased
#: ``0x0079EEF0`` lands inside another function here rather than at its entry
#: (``docs/RESEARCH.md``, 2026-09-25), so this address must not be called on build 38888.
#: Identifying *this* build's ``DialogLoader_GetText`` is the one item left in this module, and
#: the project owner has deferred it to a later pass (``docs/DIALOG_PORT.md``).
DIALOG_LOADER_GETTEXT = 0x0079EEF0

#: ``kMaxActiveDialogButtons`` (``dialog.cpp:43``). The open dialog's button list is
#: capped, and the oldest entry is dropped when it overflows (``dialog.cpp:734-739``).
MAX_ACTIVE_DIALOG_BUTTONS = 64

#: ``kMaxDecodedButtonLabelCache`` and ``kMaxDecodedButtonLabelPending`` (``dialog.cpp:44-45``).
#: The label a button's dialog id decodes to is kept, oldest out past the cap, and no more than
#: this many labels may be in flight at once — the source releases a request past that rather
#: than queueing it (``dialog.cpp:671-686``).
MAX_DECODED_BUTTON_LABEL_CACHE = 256
MAX_DECODED_BUTTON_LABEL_PENDING = 128

#: ``kMaxDialogEventLogs`` (``dialog.cpp:41``). Both journals keep at most this many
#: entries, oldest first out (``dialog.cpp:478-489``).
MAX_DIALOG_EVENT_LOGS = 512

#: ``kMaxDialogCallbackJournal`` (``dialog.cpp:42``). The callback journal's cap, and every
#: one of its three lists uses it (``dialog.cpp:529-541``).
MAX_DIALOG_CALLBACK_JOURNAL = 1000

#: The bound on one encoded dialog string read out of the client, in UTF-16 code units. The
#: source copies the string with ``DupWideStringSafe``, which walks to the terminator however
#: far it is; this port reads it one code unit at a time, so a pointer that is not a string
#: costs this many reads instead of an unbounded walk, and a string without a terminator
#: inside the bound is treated as the failed copy the source's own guard catches.
MAX_DIALOG_TEXT_CODE_UNITS = 4096

#: ``kNpcDialogHash`` (``dialog.cpp:1668``): the hash of the ``"NPC Dialog"`` root frame,
#: which is how ``is_dialog_active`` finds that frame in the client's frame array.
NPC_DIALOG_HASH = 3856160816

#: ``kDialogCallbackResumeDelay`` (``dialog.cpp:39``). Callbacks stay suspended for this long
#: after a map change, or after the map stops being ready, before the resume check may let
#: them through again.
CALLBACK_RESUME_DELAY_MS = 100

#: ``kDialogAsyncDrainTimeout`` (``dialog.cpp:38``). How long one queue's shutdown drain waits
#: for in-flight decodes before it reports.
DIALOG_ASYNC_DRAIN_TIMEOUT_MS = 500

#: ``Dialog.py:12-25``, transcribed. These clean up the client's markup before a
#: caller sees the text: colour tags, generic tags, bracket tokens, orphan line-break
#: tokens, and the spacing artefacts the encoded form leaves behind.
_COLOR_TAG_RE = re.compile(r"</?c(?:=[^>]*)?>", re.IGNORECASE)
_GENERIC_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9:_-]*(?:\s+[^>]*)?>", re.IGNORECASE)
_LBRACKET_TOKEN_RE = re.compile(r"\[lbracket\]", re.IGNORECASE)
_RBRACKET_TOKEN_RE = re.compile(r"\[rbracket\]", re.IGNORECASE)
_ORPHAN_BREAK_TOKEN_RE = re.compile(r"(?<!\w)(?:brx|br)(?!\w)", re.IGNORECASE)
_ORPHAN_PARAGRAPH_TOKEN_RE = re.compile(r"(?<!\w)p(?!\w)")
_MISSING_SPACE_AFTER_PUNCT_RE = re.compile(r"([!?:;\)\]])([A-Za-z0-9])")
_MISSING_SPACE_ALPHA_NUM_RE = re.compile(r"([A-Za-z])(\d{2,})")
_MISSING_SPACE_NUM_ALPHA_RE = re.compile(r"(\d{2,})([A-Za-z])")
_MISSING_SPACE_CAMEL_RE = re.compile(r"([a-z])([A-Z])")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_INLINE_CHOICE_RE = re.compile(r"<a\s*=\s*([^>]+)>(.*?)</a>", re.IGNORECASE | re.DOTALL)


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error a member raises while this port's work item is outstanding.

    The same shape ``Player`` and ``Map`` use: name the member, name what it needs, and state that
    the declaration is deliberate. The source's member is complete and working, so the message names
    this port's remaining work and never the source's.
    """

    return NotImplementedError(
        f"Dialog.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


# ── the facade's own helpers (``Dialog.py:28-52``) ───────────────────────────


def _safe_call(default: Any, callback: Any) -> Any:
    """``Dialog.py:28-32``: call, and return the default if it raises."""

    try:
        return callback()
    except Exception:
        return default


def _coerce_native_list(value: Any) -> list[Any]:
    """``Dialog.py:44-52``: accept whatever the surface returns as a list."""

    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return []


def _call_native_dialog_method(
    method_name: str, default: Any, *args: Any, **kwargs: Any
) -> Any:
    """Refused: this reached a binding object by name, and there is none here.

    ``Dialog.py:35-41`` looks the method up on ``PyDialog.PyDialog`` with ``getattr``
    and falls back to ``default`` when the binding is missing or the lookup fails.
    Both halves of that are unportable as written: there is no binding object outside
    the client (the same reason ``Player.player_instance`` refuses), and reaching a
    member through a dynamic name is not something this project does. The ported
    surface is :class:`Dialog` in this module, so the facade calls its methods
    directly and there is no absent case to fall back from.
    """

    raise _unported(
        "_call_native_dialog_method",
        "it resolves a member of the PyDialog binding object dynamically "
        "(Dialog.py:36-41). No binding object exists here, and this project does not "
        "reach members through dynamic names; this port's Dialog class calls the surface's "
        "directly instead",
    )


# ── the facade's pure helpers (``Dialog.py:55-149``) ─────────────────────────


def sanitize_dialog_text(value: str | None) -> str:
    """Return dialog text with the client's markup and spacing artefacts removed.

    ``Dialog.py:55-74``, transcribed line for line: the substitutions are the source's,
    in the source's order, because each one sees what the previous left behind.
    """

    if not value:
        return ""
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _LBRACKET_TOKEN_RE.sub("[", text)
    text = _RBRACKET_TOKEN_RE.sub("]", text)
    text = _COLOR_TAG_RE.sub("", text)
    text = _GENERIC_TAG_RE.sub("", text)
    text = _ORPHAN_BREAK_TOKEN_RE.sub(" ", text)
    text = _ORPHAN_PARAGRAPH_TOKEN_RE.sub(" ", text)
    text = _MISSING_SPACE_AFTER_PUNCT_RE.sub(r"\1 \2", text)
    text = _MISSING_SPACE_ALPHA_NUM_RE.sub(r"\1 \2", text)
    text = _MISSING_SPACE_NUM_ALPHA_RE.sub(r"\1 \2", text)
    text = _MISSING_SPACE_CAMEL_RE.sub(r"\1 \2", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _parse_inline_choice_dialog_id(raw_value: Any) -> int:
    """``Dialog.py:115-122``: read a dialog id out of an inline choice's attribute."""

    value = str(raw_value or "").strip()
    if not value:
        return 0
    try:
        return int(value, 0)
    except Exception:
        return 0


def extract_inline_dialog_choices_from_text(body_text: str | None) -> list[DialogButtonInfo]:
    """Return the choices a dialog body's text advertises, in order.

    ``Dialog.py:125-149``. The client writes some choices into the body text as
    ``<a=0x...>label</a>`` rather than as separate button messages, which is why the
    runtime falls back to this when it has no buttons.
    """

    text = str(body_text or "")
    if not text or "<a=" not in text.lower():
        return []

    choices: list[DialogButtonInfo] = []
    seen: set[tuple[int, str]] = set()
    for match in _INLINE_CHOICE_RE.finditer(text):
        dialog_id = _parse_inline_choice_dialog_id(match.group(1))
        if dialog_id == 0:
            continue
        label = sanitize_dialog_text(match.group(2)) or "<empty>"
        dedupe_key = (dialog_id, label)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        choices.append(
            DialogButtonInfo(
                dialog_id=dialog_id,
                message=label,
                message_decoded=label,
                message_decode_pending=False,
            )
        )
    return choices


# ── the records (``dialog.h:20-77``, and ``Dialog.py:77-112``) ───────────────


class DialogInfo:
    """One row of the client's dialog metadata table (``dialog.h:20-29``).

    Native-only: Reforged's Python never wraps it, and it is the record
    ``Dialog.get_dialog_info`` returns.
    """

    def __init__(
        self,
        *,
        dialog_id: int = 0,
        flags: int = 0,
        frame_type: int = 0,
        event_handler: int = 0,
        content_id: int = 0,
        property_id: int = 0,
        content: str = "",
        agent_id: int = 0,
    ) -> None:
        self.dialog_id = int(dialog_id)
        self.flags = int(flags)
        self.frame_type = int(frame_type)
        self.event_handler = int(event_handler)
        self.content_id = int(content_id)
        self.property_id = int(property_id)
        self.content = str(content)
        self.agent_id = int(agent_id)


class ActiveDialogInfo:
    """One snapshot of the dialog the client currently has open.

    **Adapted constructor.** ``Dialog.py:77-85`` builds this from a ``PyDialog``
    object and reaches its fields through ``getattr``, because the values arrive as
    attributes of a binding object. No such object exists here — nothing external can
    construct one, the same reason ``Player.player_instance`` refuses — so this takes
    the values instead, in the order the source reads them. ``native`` is kept and is
    always ``None``, for the same reason.
    """

    def __init__(
        self,
        dialog_id: int = 0,
        context_dialog_id: int = 0,
        agent_id: int = 0,
        dialog_id_authoritative: bool = False,
        raw_message: str = "",
    ) -> None:
        self.native = None
        self.dialog_id = int(dialog_id)
        self.context_dialog_id = int(context_dialog_id)
        self.agent_id = int(agent_id)
        self.dialog_id_authoritative = bool(dialog_id_authoritative)
        self.raw_message = str(raw_message or "")
        self.message = sanitize_dialog_text(self.raw_message)


class DialogButtonInfo:
    """One button of the open dialog (``dialog.h:39-45``, ``Dialog.py:88-112``).

    **Adapted constructor**, on the same grounds as :class:`ActiveDialogInfo`. The
    source's keyword form is what this keeps, because it is the one this port can
    build; the native-object branch needs a ``PyDialog`` button object.
    """

    def __init__(
        self,
        *,
        dialog_id: int = 0,
        button_icon: int = 0,
        message: str = "",
        message_decoded: str = "",
        message_decode_pending: bool = False,
    ) -> None:
        self.native = None
        self.dialog_id = int(dialog_id)
        self.button_icon = int(button_icon)
        self.message = sanitize_dialog_text(message)
        self.message_decoded = sanitize_dialog_text(message_decoded)
        self.message_decode_pending = bool(message_decode_pending)


class DialogTextDecodedInfo:
    """One dialog's decoded text (``dialog.h:47-51``). Native-only."""

    def __init__(
        self, *, dialog_id: int = 0, text: str = "", pending: bool = False
    ) -> None:
        self.dialog_id = int(dialog_id)
        self.text = str(text)
        self.pending = bool(pending)


class DialogEventLog:
    """One dialog message the runtime saw (``dialog.h:53-61``). Native-only.

    ``w_bytes`` and ``l_bytes`` are the message's two pointer arguments, copied.
    """

    def __init__(
        self,
        *,
        tick: int = 0,
        message_id: int = 0,
        incoming: bool = False,
        is_frame_message: bool = False,
        frame_id: int = 0,
        w_bytes: bytes = b"",
        l_bytes: bytes = b"",
    ) -> None:
        self.tick = int(tick)
        self.message_id = int(message_id)
        self.incoming = bool(incoming)
        self.is_frame_message = bool(is_frame_message)
        self.frame_id = int(frame_id)
        self.w_bytes = bytes(w_bytes)
        self.l_bytes = bytes(l_bytes)


class DialogCallbackJournalEntry:
    """One dialog callback the runtime recorded (``dialog.h:63-77``). Native-only."""

    def __init__(
        self,
        *,
        tick: int = 0,
        message_id: int = 0,
        incoming: bool = False,
        dialog_id: int = 0,
        context_dialog_id: int = 0,
        agent_id: int = 0,
        map_id: int = 0,
        model_id: int = 0,
        dialog_id_authoritative: bool = False,
        context_dialog_id_inferred: bool = False,
        npc_uid: str = "",
        event_type: str = "",
        text: str = "",
    ) -> None:
        self.tick = int(tick)
        self.message_id = int(message_id)
        self.incoming = bool(incoming)
        self.dialog_id = int(dialog_id)
        self.context_dialog_id = int(context_dialog_id)
        self.agent_id = int(agent_id)
        self.map_id = int(map_id)
        self.model_id = int(model_id)
        self.dialog_id_authoritative = bool(dialog_id_authoritative)
        self.context_dialog_id_inferred = bool(context_dialog_id_inferred)
        self.npc_uid = str(npc_uid)
        self.event_type = str(event_type)
        self.text = str(text)


# ── the metadata tables (``src/GW/dialog/dialog_patterns.cpp``) ───────────────


class DialogTableAddrs:
    """The five rebased dialog metadata bases (``dialog.h:102-109``)."""

    def __init__(self) -> None:
        self.flags_base = 0
        self.frame_type_base = 0
        self.event_handler_base = 0
        self.content_id_base = 0
        self.property_id_base = 0
        self.resolved = False


class DialogTables:
    """Resolve the dialog metadata tables, as ``dialog_patterns.cpp`` does.

    ``BuildStaticDialogTables`` (``:175-197``) rebases the five hardcoded ``DialogMemory``
    addresses (:data:`EVENT_HANDLER_BASE` … :data:`PROPERTY_ID_BASE`) onto the live module and
    validates them; when that fails, ``BuildResolvedDialogTables`` (``:199-225``) finds the flags
    column by scanning ``.rdata`` (``ResolveFlagsBase``, ``:94-133``) and derives the other four
    from it — handler ``-8``, frame type ``-4``, content id ``+4``, property id ``+8`` — and both
    stages end in ``ValidateDialogMetadataBases`` (``:135-173``). That is the whole of this class,
    and ``GetDialogTables`` (``:229-255``) is :meth:`get`: static first, fallback second, the
    answer cached either way.

    **The reader is the only difference, and it is not a choice.** Native reads its own memory,
    where a pointer read cannot fail; this port reads through ``ReadProcessMemory``, where the
    source's ``TryReadU32NoLog`` becomes :meth:`read_uint32` and an unreadable field is the
    ``false`` that ends a candidate.
    """

    def __init__(self, scanner: RemoteScanner) -> None:
        """Create the resolver over one connected client's process."""

        self._scanner = scanner
        self._tables = DialogTableAddrs()
        self._loader_address: int | None = None

    def get(self) -> DialogTableAddrs:
        """Return the tables, resolving them on first use (``GetDialogTables``)."""

        if self._tables.resolved:
            return self._tables

        self._tables.resolved = True
        static = self._build_static()
        if static.flags_base:
            self._tables = static
            self._tables.resolved = True
            return self._tables

        resolved = self._build_resolved()
        self._tables = resolved
        self._tables.resolved = True
        return self._tables

    def invalidate(self) -> None:
        """Drop the tables so the next read resolves again (``InvalidateDialogTables``)."""

        self._tables = DialogTableAddrs()

    def resolve_loader_get_text(self) -> int:
        """Return the rebased ``DialogLoader_GetText`` address.

        ``ResolveDialogLoaderGetText`` (``dialog_patterns.cpp:261-269``): rebase the constant
        and cache it in a function-static that ``InvalidateDialogTables`` leaves alone. The
        source reads nothing at the address and adds no check of its own; neither does this.

        On this build the rebased constant is **not** that function — ``0x0079EEF0`` lands inside
        another one (``docs/RESEARCH.md``, 2026-09-25) — and the address is therefore not safe to
        call. Identifying this build's loader is the module's one open item, parked by the project
        owner; see :data:`DIALOG_LOADER_GETTEXT`.
        """

        if self._loader_address is not None:
            return self._loader_address

        self._loader_address = self._scanner.to_module_address(DIALOG_LOADER_GETTEXT)
        return self._loader_address

    def read_uint32(self, address: int) -> int | None:
        """Read one word, ``None`` when it cannot be read (``TryReadU32``).

        The native helper reports its field name to the in-client log on failure; there
        is no external equivalent of that log, so the failure is the return value.
        """

        try:
            return self._scanner.read_uint32(address)
        except OSError:
            return None

    # -- the two build stages (``dialog_patterns.cpp:175-225``) -------------

    def _build_static(self) -> DialogTableAddrs:
        """Rebase the five hardcoded addresses and validate them.

        ``BuildStaticDialogTables`` (``dialog_patterns.cpp:175-197``), assignment for
        assignment: each ``DialogMemory`` constant goes through ``ToRuntimeAddress``
        (``dialog_patterns.cpp:25-31``) — the module base plus the constant minus the client's
        link-time image base (``0x00400000``) — which is
        :meth:`py4gw.scanner.remote.RemoteScanner.to_module_address`.
        """

        tables = DialogTableAddrs()

        tables.flags_base = self._scanner.to_module_address(FLAGS_BASE)
        tables.frame_type_base = self._scanner.to_module_address(FRAME_TYPE_BASE)
        tables.event_handler_base = self._scanner.to_module_address(EVENT_HANDLER_BASE)
        tables.content_id_base = self._scanner.to_module_address(CONTENT_ID_BASE)
        tables.property_id_base = self._scanner.to_module_address(PROPERTY_ID_BASE)

        if not self._validate(tables):
            return DialogTableAddrs()
        return tables

    def _build_resolved(self) -> DialogTableAddrs:
        """Find the flags column by scan, derive the rest, and validate them."""

        tables = DialogTableAddrs()
        tables.flags_base = self._resolve_flags_base()
        if tables.flags_base:
            tables.event_handler_base = tables.flags_base - 0x8
            tables.frame_type_base = tables.flags_base - 0x4
            tables.content_id_base = tables.flags_base + 0x4
            tables.property_id_base = tables.flags_base + 0x8

        if not self._validate(tables):
            return DialogTableAddrs()
        return tables

    def _text_bounds(self) -> tuple[int, int] | None:
        """Return the client's ``.text`` range, which the handler column must fall in."""

        try:
            text = self._scanner.get_section_range("text")
        except ValueError:
            return None
        return text.start, text.end

    def _validate(self, tables: DialogTableAddrs) -> bool:
        """``ValidateDialogMetadataBases`` (``dialog_patterns.cpp:135-173``)."""

        if not (
            tables.flags_base
            and tables.frame_type_base
            and tables.event_handler_base
            and tables.content_id_base
            and tables.property_id_base
        ):
            return False
        bounds = self._text_bounds()
        if bounds is None:
            return False
        text_start, text_end = bounds

        count = MAX_DIALOG_ID + 1
        enabled = 0
        for index in range(count):
            offset = index * FLAGS_STRIDE
            flags = self.read_uint32(tables.flags_base + offset)
            handler = self.read_uint32(tables.event_handler_base + offset)
            frame_type = self.read_uint32(tables.frame_type_base + offset)
            content_id = self.read_uint32(
                tables.content_id_base + index * CONTENT_STRIDE
            )
            property_id = self.read_uint32(
                tables.property_id_base + index * PROPERTY_STRIDE
            )
            if (
                flags is None
                or handler is None
                or frame_type is None
                or content_id is None
                or property_id is None
            ):
                return False
            if flags > 0xFFFF:
                return False
            if handler != 0 and not (text_start <= handler < text_end):
                return False
            if flags & 0x1:
                enabled += 1
        return enabled > 0

    def _resolve_flags_base(self) -> int:
        """``ResolveFlagsBase`` (``dialog_patterns.cpp:94-133``).

        The scan window, the four-byte step, the per-row checks and the bounds are the
        source's, field for field through :meth:`read_uint32`, which is this port's
        ``TryReadU32NoLog``: a field that cannot be read ends the candidate exactly as the
        source's ``false`` does.
        """

        bounds = self._text_bounds()
        if bounds is None:
            return 0
        text_start, text_end = bounds
        try:
            rdata = self._scanner.get_section_range("rdata")
        except ValueError:
            return 0

        count = MAX_DIALOG_ID + 1
        stride = FLAGS_STRIDE
        end = rdata.end - (count * stride)

        address = rdata.start + 8
        while address + count * stride <= end:
            ok = True
            enabled = 0
            for index in range(count):
                flags = self.read_uint32(address + index * stride)
                if flags is None:
                    ok = False
                    break
                if flags > 0xFFFF:
                    ok = False
                    break
                if flags & 0x1:
                    enabled += 1
                handler = self.read_uint32(address - 8 + index * stride)
                if handler is None:
                    ok = False
                    break
                if handler != 0 and not (text_start <= handler < text_end):
                    ok = False
                    break
            if ok and enabled > 0:
                return address
            address += 4
        return 0


def _is_dialog_map_ready() -> bool:
    """``IsDialogMapReadySafe`` (``dialog.cpp:182-191``): the gate every reader makes.

    Native asks ``GetIsMapLoaded() && !GetIsObserving() && instance != Loading``; that
    is the ported ``Map.IsMapReady()``, and the source's order puts the gate first.
    """

    from .map import Map

    return Map.IsMapReady()


def _dialog_tables() -> DialogTables:
    """Return the connected client's dialog table resolver.

    Native reaches its tables through the module's own ``GetDialogTables()``; here the
    resolver is built by the connection, because it needs that client's process.
    """

    from .client import require_client

    return require_client().dialog_tables


def _invalidate_tables() -> None:
    """Drop the tables on the connected client, as ``InvalidateDialogTables`` does.

    Native's tables are in-process and always exist, so its invalidation is
    unconditional. Here they belong to a connection: with no client there is no
    resolved table to drop, and the state being cleared is all there is.
    """

    from .client import current_client

    client = current_client()
    if client is None:
        return
    client.dialog_tables.invalidate()


# ── the catalog's decode queue (``dialog.cpp``'s DialogCatalog statics) ───────


def _resolve_dialog_loader_get_text() -> int:
    """``ResolveDialogLoaderGetText`` (``dialog_patterns.cpp:261-269``): the loader.

    Native rebases the hardcoded ``DialogMemory::DIALOG_LOADER_GETTEXT`` onto the module and
    caches it; :class:`DialogTables` does the same with the same constant. On this build the
    rebased address is not the loader (:data:`DIALOG_LOADER_GETTEXT`).
    """

    return _dialog_tables().resolve_loader_get_text()


def _read_encoded_text(address: int) -> list[int] | None:
    """Read one encoded dialog string's codepoints, or ``None``.

    The source copies the string in-process (``DupWideStringSafe``) and hands the copy to the
    client's decoder. This port reads it with the bounded reader the rest of it uses — one
    UTF-16 code unit at a time, stopping at the array's own terminator — and answers ``None``
    when the pointer cannot be read or holds no terminator within
    :data:`MAX_DIALOG_TEXT_CODE_UNITS`, which is the failed copy the source's own SEH wrapper
    turns into a null pointer.
    """

    if not address:
        return None

    read_uint32 = _dialog_tables().read_uint32
    codepoints: list[int] = []
    for index in range(MAX_DIALOG_TEXT_CODE_UNITS):
        value = read_uint32(address + index * 2)
        if value is None:
            return None
        unit = int(value) & 0xFFFF
        codepoints.append(unit)
        if unit == 0:
            return codepoints
    return None


def _copied_string(event: EventRecord) -> list[int] | None:
    """The copy the observer took of the string this message named, or ``None``.

    This is the port's ``DupWideStringSafe`` result (``dialog.cpp:237-252``): native copies the
    string inside its callback, where the client still has it, and answers null when the pointer
    is null or the read faulted.

    **Why the copy is not made here.** The pointer a dialog message carries is a buffer the
    client reuses — measured, ``docs/RESEARCH.md`` 2026-09-25 — so a read made from this side,
    however soon after the message, is a read of whatever that buffer holds by then. The
    observer is emitted code running inside the client's own call, and it copies the string
    there (:func:`py4gw.game_thread.payload.build_observer`); what arrives here is that copy.

    ``None`` covers both of the source's ways of having nothing to work with: no string at all
    (the packet's field is null, or the message declares no string field) and a copy that could
    not be made. The second is where this side has no ``__try``: the observer copies within
    :data:`py4gw.game_thread.shared_block.EVENT_TEXT_WORDS` and reports a string with no
    terminator inside that bound as unterminated, which is answered here the way native answers
    its fault.
    """

    if event.text_state != EventTextState.COPIED:
        return None
    return list(event.text)


def _encoded_text_to_text(codepoints: list[int]) -> str:
    """``WideToUtf8Safe``: a wide string as text, without its terminator.

    Used for the branch where the client's own string is **not** a valid encoded string: the
    source caches the raw string there rather than a decoded one (``dialog.cpp:1209``), and the
    conversion drops the terminator (``WideToUtf8Safe`` resizes to ``written - 1``).
    """

    text = "".join(chr(codepoint) for codepoint in codepoints)
    return text[:-1] if text.endswith("\x00") else text


def _queue_dialog_text_decode(dialog_id: int) -> None:
    """``QueueDialogTextDecode`` (``dialog.cpp:1136-1254``), up to the call this port cannot make.

    The source's first step past its guards is its loader:
    ``ResolveDialogLoaderGetText`` (``dialog_patterns.cpp:261-269``) rebases
    ``DialogMemory::DIALOG_LOADER_GETTEXT``, and ``QueueDialogTextDecode`` calls it for the
    dialog id. **That call is not ported, because this build's loader is not at that
    address** — measured read-only, the rebased ``0x0079EEF0`` lands inside another function
    and calling it faulted the client (``docs/RESEARCH.md``, 2026-09-25). Identifying this
    build's own loader is the item the project owner has deferred, so the member reports it
    here, before it flags the id pending — a refusal that left the pending flag set would
    answer "" for that id for the life of the connection.

    Everything the source does before that step is below in the source's order, and everything
    after it — the copy, ``AsyncDecodeStr``, ``OnDialogTextDecoded``, the four failure
    branches — is ported and waits on the same address.
    """

    global _catalog_pending_async_decode_count

    from .client import require_client
    from .ui.async_decode import async_decode_str, begin_string_decode
    from .ui.encoded_str import is_valid_enc_str

    if not _is_dialog_map_ready():
        return
    if dialog_id > MAX_DIALOG_ID:
        return

    if _catalog_shutdown_requested:
        return
    if dialog_id in _decoded_text_cache:
        return
    if _decoded_text_pending.get(dialog_id):
        return

    raise _unported(
        "get_dialog_text_decoded",
        "this build's DialogLoader_GetText. The source rebases "
        "DialogMemory::DIALOG_LOADER_GETTEXT (dialog.h:99, 0x0079EEF0) and calls it "
        "(dialog_patterns.cpp:261-269); identifying this build's own loader is the item "
        "the project owner has deferred",
    )

    _decoded_text_pending[dialog_id] = True
    request_epoch = _catalog_decode_epoch

    # ``dialog.cpp:1166-1216``: four failure branches, each of which caches an answer under the
    # same guard — the epoch the call captured, and no shutdown — and then clears the pending
    # flag. The two lines are written out at each site, as the source writes them; only the text
    # differs, the last site caching the **raw** string where the others cache nothing.
    address = _resolve_dialog_loader_get_text()

    pointer = int(
        require_client().call_address(address, CallForm.U32, dialog_id).value
    )
    if not pointer:
        if request_epoch == _catalog_decode_epoch and not _catalog_shutdown_requested:
            _decoded_text_cache[dialog_id] = ""
            _decoded_text_pending.pop(dialog_id, None)
        return

    codepoints = _read_encoded_text(pointer)
    if codepoints is None:
        if request_epoch == _catalog_decode_epoch and not _catalog_shutdown_requested:
            _decoded_text_cache[dialog_id] = ""
            _decoded_text_pending.pop(dialog_id, None)
        return

    if not is_valid_enc_str(codepoints):
        if request_epoch == _catalog_decode_epoch and not _catalog_shutdown_requested:
            _decoded_text_cache[dialog_id] = _encoded_text_to_text(codepoints)
            _decoded_text_pending.pop(dialog_id, None)
        return

    # The source re-checks the epoch and the shutdown flag after the string is in hand, before
    # it counts the decode as in flight (``1233-1240``); a clear in between has already taken
    # the pending flag with it.
    if _catalog_shutdown_requested or request_epoch != _catalog_decode_epoch:
        return

    # ``dialog.cpp:1239-1253``: the request is set and the decode counted as in flight **before**
    # the decoder is called, so a completion cannot arrive before its record exists. A decode
    # that could not be started releases the request, gives the count back under the source's
    # own guard, and **erases the pending flag**, under the source's two conditions — without
    # that, `decoded_text_pending` stayed true for that id for the life of the connection:
    # `get_dialog_text_decoded` answers "" for ever and never re-queues, the status list reports
    # it as in flight, and `terminate` raises on a count that can never reach zero.
    encoded = _wide_bytes(codepoints)
    try:
        slot = begin_string_decode(encoded)
    except RuntimeError:
        # ``dialog.cpp:1218-1225``: the request could not be allocated. Native's `new
        # (std::nothrow)` answers null and its branch is the **pending flag alone** — no cache
        # entry at all, so a later call queues this id again. Here the allocation that can fail
        # is the decode slot, and the same answer is given for the same reason: caching "" here
        # would turn a transient shortage into a permanent empty text.
        if request_epoch == _catalog_decode_epoch and not _catalog_shutdown_requested:
            _decoded_text_pending.pop(dialog_id, None)
        return

    _catalog_pending_async_decode_count += 1
    _catalog_decodes[slot] = (dialog_id, request_epoch)

    if not async_decode_str(encoded, slot):
        _catalog_decodes.pop(slot, None)
        if _catalog_pending_async_decode_count > 0:
            _catalog_pending_async_decode_count -= 1
        if (
            request_epoch == _catalog_decode_epoch
            and not _catalog_shutdown_requested
        ):
            _decoded_text_pending.pop(dialog_id, None)


def _on_catalog_text_decoded(
    slot: int, dialog_id: int, request_epoch: int, text: str
) -> None:
    """``OnDialogTextDecoded`` (``dialog.cpp:1120-1134``): cache what the client decoded.

    The pending count is taken back here, because this is the callback the source counts the
    decode as in flight until: ``Shutdown`` waits on that count, and it is spent by the time the
    text is in hand whichever way it arrived.
    """

    global _catalog_pending_async_decode_count

    # ``dialog.cpp:1115-1128``: the count comes back first, then the cache write under the
    # completion's own guard — no shutdown, and the epoch the request captured — with the pending
    # flag cleared either way inside it. The source's ``__try`` around the two assignments becomes
    # nothing here: assigning into a dict cannot throw.
    if _catalog_pending_async_decode_count > 0:
        _catalog_pending_async_decode_count -= 1
    if not _catalog_shutdown_requested and request_epoch == _catalog_decode_epoch:
        _decoded_text_cache[dialog_id] = text
        _decoded_text_pending.pop(dialog_id, None)


def _get_dialog_text_decoded(dialog_id: int) -> str:
    """``GetDialogTextDecoded`` (``dialog.cpp:1455-1475``): the text, or "".

    Always "" on the call that queues the decode, and the text from the cache afterwards —
    which is the source's contract with its own callers, and with the facade's.
    """

    if not _is_dialog_map_ready():
        return ""
    if dialog_id > MAX_DIALOG_ID:
        return ""

    cached = _decoded_text_cache.get(dialog_id)
    if cached is not None:
        return cached
    if _decoded_text_pending.get(dialog_id):
        return ""

    _queue_dialog_text_decode(dialog_id)
    return ""


def _is_dialog_text_decode_pending(dialog_id: int) -> bool:
    """``IsDialogTextDecodePending`` (``dialog.cpp:1477-1484``)."""

    if not _is_dialog_map_ready():
        return False
    return bool(_decoded_text_pending.get(dialog_id))


def _decoded_dialog_text_status() -> list[DialogTextDecodedInfo]:
    """``GetDecodedDialogTextStatus`` (``dialog.cpp:1486-1510``): cache first, then pending.

    A pending id that is also cached is reported once, as the cached row: the source skips it
    in the second loop for exactly that reason.
    """

    if not _is_dialog_map_ready():
        return []

    out: list[DialogTextDecodedInfo] = []
    for dialog_id in _decoded_text_cache:
        out.append(
            DialogTextDecodedInfo(
                dialog_id=dialog_id, text=_decoded_text_cache[dialog_id], pending=False
            )
        )
    for dialog_id, pending in _decoded_text_pending.items():
        if not pending or dialog_id in _decoded_text_cache:
            continue
        out.append(DialogTextDecodedInfo(dialog_id=dialog_id, pending=True))
    return out


def _try_get_cached_dialog_text_decoded(dialog_id: int) -> tuple[bool, str]:
    """``TryGetCachedDialogTextDecoded`` (``dialog.cpp:1512-1523``).

    The source's out-parameter becomes a pair: whether there was a cache entry, and what it
    held. A cached empty string is a hit, which is the distinction the pair exists for.
    """

    if not _is_dialog_map_ready():
        return False, ""
    cached = _decoded_text_cache.get(dialog_id)
    if cached is None:
        return False, ""
    return True, cached


def _clear_catalog_cache() -> None:
    """``ClearCatalogCache`` (``dialog.cpp:1256-1262``): the cache, the pending set, the epoch.

    The epoch is what makes the clear safe: a decode in flight carries the epoch it started
    with, and every site that writes the cache or a pending flag tests it first — in the queue's
    four failure branches, in its fifth, and in the completion — so a decode that began before
    the clear cannot put text back into a cache that was emptied for it. The tables are
    invalidated last, as the source does.
    """

    global _catalog_decode_epoch

    _decoded_text_cache.clear()
    _decoded_text_pending.clear()
    _catalog_decode_epoch += 1
    _invalidate_tables()


# ── the surface (``PyDialog``, ``dialog_bindings.cpp:94-138``) ───────────────


class Dialog:
    """The port of the ``PyDialog`` surface the facade reaches.

    **Why this class is called ``Dialog`` and not ``PyDialog``.** In Reforged, ``PyDialog``
    is the *injected module*: ``Dialog.py:7-9`` imports it and falls back to ``None`` when
    it is absent, and no such class exists anywhere in Reforged's Python. In Reforged
    Native it is the *embedded module*, whose Python class is backed by an empty struct —
    ``struct PyDialogShim {}`` at ``dialog_bindings.cpp:90``, bound as ``"PyDialog"`` at
    ``:101`` — with every method forwarding to a real ``GW::dialog::*`` function. This
    project has neither an injected module nor a binding, so the surface is held in the
    class its own module is named for, the way ``Player``, ``Agent`` and ``Map`` are.
    **``PyDialog`` in this tree means the sources' module and nothing else.**

    Reforged's Python finds these through ``PyDialog.PyDialog.<name>``; here they are
    static methods of this class, so the facade calls them by name. Each one is either
    implemented from the state the client's messages give us or from the metadata
    tables, or refused naming the mechanism it needs.

    **The tables are the source's own resolution.** The five bases are ``DialogMemory``'s
    constants (``dialog.h:94-99``), rebased module-relative as ``ToRuntimeAddress`` does
    (``dialog_patterns.cpp:25-31``) and validated by ``ValidateDialogMetadataBases``
    (``:135-173``), with ``ResolveFlagsBase``'s ``.rdata`` scan (``:94-133``) behind them —
    :class:`DialogTables`, entire. None of it is catalog data, because native keeps none of it
    in its catalog either.

    **The text is no longer a refusal either.** ``DialogLoader_GetText`` is called through the
    capability layer for a dialog id's encoded string, and that string is handed to the client's
    own decoder (``AsyncDecodeStr`` through :mod:`py4gw.ui.async_decode`), with the completion
    arriving as a ``STRING_DECODED`` event — the port's own queue is
    :func:`_queue_dialog_text_decode`, the port of ``QueueDialogTextDecode``.

    **Deferred to a later pass, by the project owner:** identifying this build's
    ``DialogLoader_GetText``. Every other part of this class works; what that one function leaves
    empty is a catalog dialog's ``content`` (the tables' five metadata columns answer, the open
    dialog's own body and button captions answer). The client inlines the text path into its dialog
    window, so the address the sources carry is stale here; the two routes to identify it are named
    in ``docs/RESEARCH.md`` and the search is parked, not abandoned. Until then the loader
    resolution answers the source's own "no loader" value and a catalog row's content is empty —
    the loud refusal, never a wrong string.
    """

    #: What the members that still need the client's *own* decode are waiting for. The dialog
    #: text no longer does: it is decoded by the client through the emitted stub.
    _DECODE = (
        "it needs the client to decode an encoded wide string, which the client does "
        "by calling back into a function it is given (AsyncDecodeStr, ui_methods.cpp:29-30)"
    )

    # -- lifecycle ---------------------------------------------------------

    @staticmethod
    def initialize() -> bool:
        """``dialog.cpp:1315-1331``: clear the state, then let the connection register.

        The source clears both shutdown flags, calls ``ClearCache`` — which is what sets the
        map gate from the live map, rather than leaving callbacks suspended — and then
        registers its four UI-message callbacks. The registration is the connection's here,
        and the connection calls this immediately before it registers the capture, so the
        order is the source's.

        Without this step the gate would stay suspended until something polled it, and the
        message that opens a dialog would be dropped — which is exactly what native avoids by
        taking the gate from the live map at startup.
        """

        global _shutdown_requested, _catalog_shutdown_requested

        _shutdown_requested = False
        _catalog_shutdown_requested = False
        Dialog.clear_cache()
        return True

    @staticmethod
    def terminate() -> None:
        """``Shutdown`` (``dialog.cpp:1333-1386``), step for step.

        The source sets the dialog shutdown flag and bumps the dialog epoch and body nonce,
        unregisters its four UI-message callbacks, drains the dialog-level decodes, clears the
        cache, and then does the same three things for the catalog: flag, epoch, drain, and an
        explicit clear of its cache and pending set.

        **Two of those steps belong to the connection here, and this says so rather than
        pretending otherwise.** The *unregistration* is :func:`py4gw.disconnect`, which takes
        the capture out — that is the source's ``UnregisterDialogUiHooks`` in this project's
        shape. The *drain* has nothing to wait on, because a render happens inside the call
        that asks for it; :func:`_drain_async_decodes` is written as the source writes it,
        bounded by the same timeout, so a counter that somehow stayed set is reported rather
        than waited on forever.
        """

        global _shutdown_requested, _decode_epoch, _body_decode_nonce
        global _catalog_shutdown_requested, _catalog_decode_epoch

        _shutdown_requested = True
        _decode_epoch += 1
        _body_decode_nonce += 1
        _drain_async_decodes("dialog")

        Dialog.clear_cache()

        _catalog_shutdown_requested = True
        _catalog_decode_epoch += 1
        _drain_async_decodes("catalog")
        _decoded_text_cache.clear()
        _decoded_text_pending.clear()

    @staticmethod
    def clear_cache() -> None:
        """``dialog.cpp:1819-1845``: empty the dialog state, the journals, and the catalog.

        The source clears the active cache, the buttons, the last selected id, the pending send,
        the decoded-text caches, the three journals, the table resolution, and bumps both decode
        epochs — and then re-reads the map to set the observed map and the suspension from it
        (``1839-1842``), so a cache cleared during a map load stays suspended. Every one of those
        is here now, the two button-label caches included.
        """

        global _decode_epoch, _body_decode_nonce
        global _last_observed_map_id, _last_observed_map_ready
        global _callbacks_suspended, _callbacks_resume_tick
        global _dialog_agent_id, _dialog_id, _context_dialog_id
        global _dialog_id_authoritative, _dialog_message
        global _last_selected_dialog_id, _pending_context_dialog_id
        global _pending_context_agent_id

        # ``dialog.cpp:1822-1843``: one block, written out — the state, the buttons, the last id,
        # the pending send, the two label caches, the six journal lists, both decode counters,
        # and the gate taken from the map read at the top of the function.
        map_id, map_ready = _map_state()
        now = _now_ms()
        _dialog_agent_id = 0
        _dialog_id = 0
        _context_dialog_id = 0
        _dialog_id_authoritative = False
        _dialog_message = ""
        _dialog_buttons.clear()
        _last_selected_dialog_id = 0
        _pending_context_dialog_id = 0
        _pending_context_agent_id = 0
        _decoded_button_label_cache.clear()
        _decoded_button_label_pending.clear()
        _dialog_event_logs.clear()
        _dialog_event_logs_received.clear()
        _dialog_event_logs_sent.clear()
        _dialog_callback_journal.clear()
        _dialog_callback_journal_received.clear()
        _dialog_callback_journal_sent.clear()
        _decode_epoch += 1
        _body_decode_nonce += 1
        _last_observed_map_id = map_id
        _last_observed_map_ready = map_ready
        _callbacks_suspended = not map_ready
        _callbacks_resume_tick = 0 if map_ready else now
        _clear_catalog_cache()

    # -- the open dialog, from the client's own messages --------------------

    @staticmethod
    def get_active_dialog() -> ActiveDialogInfo:
        """Return the open dialog as a record, zeros when there is none.

        ``dialog.cpp``'s ``GetActiveDialog`` builds this from ``active_dialog_cache``,
        which is what the body and button handlers keep. The facade is what decides
        that an all-zero record means *no dialog* (``Dialog.py:156-161``).

        The map check comes first, because native's update loop keeps this state fresh
        before any caller reads it and this project has no loop (see
        :func:`_poll_map_change`). The body's text is not asked for here: it arrives when the
        client's decoder has it (:func:`_on_string_decoded`), exactly as it does for native,
        whose ``active_dialog_cache.message`` is empty until its callback has run.
        """

        _poll_map_change()

        return ActiveDialogInfo(
            dialog_id=_dialog_id,
            context_dialog_id=_context_dialog_id,
            agent_id=_dialog_agent_id,
            dialog_id_authoritative=_dialog_id_authoritative,
            raw_message=_dialog_message,
        )

    @staticmethod
    def get_active_dialog_buttons() -> list[DialogButtonInfo]:
        """``GetActiveDialogButtons`` (``dialog.cpp:1632-1664``): the buttons, with labels.

        The list is a copy of what the announcements appended, and then each button's caption is
        filled in — from the label cache the button's own decode filled, or, when that has
        nothing, from the **catalog** text for the button's dialog id, which is the source's own
        fallback (``1655-1658``). A caption still being decoded is reported as pending rather
        than as empty text.
        """

        _poll_map_change()

        out = list(_dialog_buttons)
        for button in out:
            if button.dialog_id == 0:
                continue
            label = _decoded_button_label_cache.get(button.dialog_id, "")
            pending = bool(_decoded_button_label_pending.get(button.dialog_id))
            if not label:
                label = _get_dialog_text_decoded(button.dialog_id)
                pending = _is_dialog_text_decode_pending(button.dialog_id)
            button.message_decoded = label
            button.message = label
            button.message_decode_pending = pending
        return out

    @staticmethod
    def get_last_selected_dialog_id() -> int:
        """Return the last dialog this module sent, or ``0``.

        ``dialog.cpp:967`` sets it in the branch that handles a sent dialog, and
        ``ClearCache``/``Shutdown`` clear it.
        """

        _poll_map_change()

        return _last_selected_dialog_id

    @staticmethod
    def is_dialog_displayed(dialog_id: int) -> bool:
        """Return whether the open dialog is this one (``dialog.cpp:1684-1692``)."""

        _poll_map_change()

        if dialog_id == 0:
            return False
        return (
            _dialog_id == dialog_id or _context_dialog_id == dialog_id
        )

    @staticmethod
    def is_dialog_active() -> bool:
        """``dialog.cpp:1666-1682``: the client's NPC Dialog frame exists and is visible.

        Native asks the client for the frame by hash, then reads its state:

        ```cpp
        const uint32_t frame_id = GW::ui::GetFrameIDByHash(kNpcDialogHash);
        if (!frame_id) return false;
        const GW::ui::Frame* frame = GW::ui::GetFrameById(frame_id);
        if (!frame) return false;
        return frame->IsCreated() && frame->IsVisible();
        ```

        Both of those are **reads of the frame array** — ``GetFrameIDByHash`` scans it
        (``ui_methods.cpp:575-587``) and ``GetFrameById`` indexes it — so this port reads
        the same array through ``FrameArray`` and makes no call.
        """

        from .client import require_client

        frame_array = require_client().frame_array
        frame_id = frame_array.frame_id_by_hash(NPC_DIALOG_HASH)
        if not frame_id:
            return False
        frame = frame_array.get(frame_id)
        if frame is None:
            return False
        return frame.is_created and frame.is_visible

    # -- the dialog metadata tables ----------------------------------------

    @staticmethod
    def is_dialog_available(dialog_id: int) -> bool:
        """``dialog.cpp:1413-1421``: ``flags & 0x1`` for one dialog."""

        if not _is_dialog_map_ready():
            return False
        if dialog_id > MAX_DIALOG_ID:
            return False
        return (Dialog.read_dialog_flags(dialog_id) & 0x1) != 0

    @staticmethod
    def get_dialog_info(dialog_id: int) -> DialogInfo:
        """``dialog.cpp:1423-1439``: one row of the metadata table plus its text.

        The five columns are the ported readers; ``content`` is ``GetDialogTextDecoded``, which
        queues the decode the first time it is asked for a dialog and answers from the cache
        afterwards — so the record this returns has text from the *second* call on, which is
        the source's own contract with its callers.
        """

        info = DialogInfo(dialog_id=int(dialog_id))
        if not _is_dialog_map_ready():
            return info
        if dialog_id > MAX_DIALOG_ID:
            return info

        info.flags = Dialog.read_dialog_flags(dialog_id)
        info.frame_type = Dialog.read_dialog_frame_type(dialog_id)
        info.event_handler = Dialog.read_dialog_event_handler(dialog_id)
        info.content_id = Dialog.read_dialog_content_id(dialog_id)
        info.property_id = Dialog.read_dialog_property_id(dialog_id)
        info.content = _get_dialog_text_decoded(dialog_id)
        return info

    @staticmethod
    def enumerate_available_dialogs() -> list[DialogInfo]:
        """``dialog.cpp:1441-1453``: every available row of the metadata table."""

        dialogs: list[DialogInfo] = []
        if not _is_dialog_map_ready():
            return dialogs
        for dialog_id in range(MAX_DIALOG_ID + 1):
            if Dialog.is_dialog_available(dialog_id):
                dialogs.append(Dialog.get_dialog_info(dialog_id))
        return dialogs

    @staticmethod
    def read_dialog_flags(dialog_id: int) -> int:
        """``dialog.cpp:1525-1542``: the flags column of the metadata table."""

        if not _is_dialog_map_ready():
            return 0
        if dialog_id > MAX_DIALOG_ID:
            return 0
        resolver = _dialog_tables()
        tables = resolver.get()
        if not tables.flags_base:
            return 0
        flags = resolver.read_uint32(tables.flags_base + dialog_id * FLAGS_STRIDE)
        return flags or 0

    @staticmethod
    def read_dialog_frame_type(dialog_id: int) -> int:
        """``dialog.cpp:1544-1561``: the frame-type column of the metadata table."""

        if not _is_dialog_map_ready():
            return 0
        if dialog_id > MAX_DIALOG_ID:
            return 0
        resolver = _dialog_tables()
        tables = resolver.get()
        if not tables.frame_type_base:
            return 0
        frame_type = resolver.read_uint32(
            tables.frame_type_base + dialog_id * FLAGS_STRIDE
        )
        return frame_type or 0

    @staticmethod
    def read_dialog_event_handler(dialog_id: int) -> int:
        """``dialog.cpp:1563-1580``: the event-handler column of the metadata table."""

        if not _is_dialog_map_ready():
            return 0
        if dialog_id > MAX_DIALOG_ID:
            return 0
        resolver = _dialog_tables()
        tables = resolver.get()
        if not tables.event_handler_base:
            return 0
        handler = resolver.read_uint32(
            tables.event_handler_base + dialog_id * FLAGS_STRIDE
        )
        return handler or 0

    @staticmethod
    def read_dialog_content_id(dialog_id: int) -> int:
        """``dialog.cpp:1582-1599``: the content-id column of the metadata table."""

        if not _is_dialog_map_ready():
            return 0
        if dialog_id > MAX_DIALOG_ID:
            return 0
        resolver = _dialog_tables()
        tables = resolver.get()
        if not tables.content_id_base:
            return 0
        content_id = resolver.read_uint32(
            tables.content_id_base + dialog_id * CONTENT_STRIDE
        )
        return content_id or 0

    @staticmethod
    def read_dialog_property_id(dialog_id: int) -> int:
        """``dialog.cpp:1601-1618``: the property-id column of the metadata table."""

        if not _is_dialog_map_ready():
            return 0
        if dialog_id > MAX_DIALOG_ID:
            return 0
        resolver = _dialog_tables()
        tables = resolver.get()
        if not tables.property_id_base:
            return 0
        property_id = resolver.read_uint32(
            tables.property_id_base + dialog_id * PROPERTY_STRIDE
        )
        return property_id or 0

    # -- decoded text ------------------------------------------------------

    @staticmethod
    def get_dialog_text_decoded(dialog_id: int) -> str:
        """``GetDialogTextDecoded`` (``dialog.cpp:1455-1475``), bound as ``std::string``.

        The binding returns the text itself (``dialog_bindings.cpp:111``), not the status
        record that carries it: this is the member Reforged's Python reads for a dialog's
        text, and it answers "" on the call that queues the decode.
        """

        return _get_dialog_text_decoded(int(dialog_id))

    @staticmethod
    def is_dialog_text_decode_pending(dialog_id: int) -> bool:
        """``IsDialogTextDecodePending`` (``dialog.cpp:1477-1484``)."""

        return _is_dialog_text_decode_pending(int(dialog_id))

    @staticmethod
    def get_dialog_text_decode_status() -> list[DialogTextDecodedInfo]:
        """``GetDecodedDialogTextStatus`` (``dialog.cpp:1486-1510``).

        The cached rows first, each with its text, then one row per id still pending — which is
        the record ``DialogTextDecodedInfo`` exists for (``dialog.h:47-51``).
        """

        return _decoded_dialog_text_status()

    # -- the runtime's own journals ----------------------------------------

    @staticmethod
    def get_dialog_event_logs() -> list[DialogEventLog]:
        """``GetDialogEventLogs`` (``dialog.cpp:1693-1696``): every recorded message.

        The source copies the list under its lock and hands back the copy; so does this, so a
        caller cannot hold the journal itself.
        """

        return list(_dialog_event_logs)

    @staticmethod
    def get_dialog_event_logs_received() -> list[DialogEventLog]:
        """``GetDialogEventLogsReceived`` (``dialog.cpp:1698-1701``)."""

        return list(_dialog_event_logs_received)

    @staticmethod
    def get_dialog_event_logs_sent() -> list[DialogEventLog]:
        """``GetDialogEventLogsSent`` (``dialog.cpp:1703-1706``)."""

        return list(_dialog_event_logs_sent)

    @staticmethod
    def clear_dialog_event_logs() -> None:
        """``ClearDialogEventLogs`` (``dialog.cpp:1708-1713``): all three lists at once."""

        _clear_event_logs()

    @staticmethod
    def clear_dialog_event_logs_received() -> None:
        """``ClearDialogEventLogsReceived`` (``dialog.cpp:1715-1718``)."""

        _dialog_event_logs_received.clear()

    @staticmethod
    def clear_dialog_event_logs_sent() -> None:
        """``ClearDialogEventLogsSent`` (``dialog.cpp:1720-1723``)."""

        _dialog_event_logs_sent.clear()

    @staticmethod
    def get_dialog_callback_journal() -> list[DialogCallbackJournalEntry]:
        """``GetDialogCallbackJournal`` (``dialog.cpp:1725-1732``): the whole journal, sorted.

        The body's row is appended by its decode's completion, which is ``dialog.cpp:1037``'s
        own place for it: a caller that asks before the client has decoded sees what native
        sees then, which is no row yet.
        """

        return _sort_callback_journal(list(_dialog_callback_journal))

    @staticmethod
    def get_dialog_callback_journal_received() -> list[DialogCallbackJournalEntry]:
        """``GetDialogCallbackJournalReceived`` (``dialog.cpp:1734-1741``), sorted."""

        return _sort_callback_journal(list(_dialog_callback_journal_received))

    @staticmethod
    def get_dialog_callback_journal_sent() -> list[DialogCallbackJournalEntry]:
        """``GetDialogCallbackJournalSent`` (``dialog.cpp:1743-1750``), sorted."""

        return _sort_callback_journal(list(_dialog_callback_journal_sent))

    @staticmethod
    def clear_dialog_callback_journal() -> None:
        """``ClearDialogCallbackJournal`` (``dialog.cpp:1752-1757``)."""

        _clear_callback_journal()

    @staticmethod
    def clear_dialog_callback_journal_received() -> None:
        """``ClearDialogCallbackJournalReceived`` (``dialog.cpp:1759-1762``)."""

        _dialog_callback_journal_received.clear()

    @staticmethod
    def clear_dialog_callback_journal_sent() -> None:
        """``ClearDialogCallbackJournalSent`` (``dialog.cpp:1764-1767``)."""

        _dialog_callback_journal_sent.clear()

    @staticmethod
    def clear_dialog_callback_journal_filtered(
        npc_uid: str | None = None,
        incoming: bool | None = None,
        message_id: int | None = None,
        event_type: str | None = None,
    ) -> None:
        """``ClearDialogCallbackJournalFiltered`` (``dialog.cpp:1769-1817``).

        The signature is the binding's (``dialog_bindings.cpp:131-135``): every filter defaults
        to "no filter", and passing none at all clears everything — the source's own first
        branch. Otherwise the main journal is filtered first and the two direction lists are
        **rebuilt** from what is left, which is what keeps a filtered clear from leaving an
        entry in a direction list the journal no longer holds.
        """

        if npc_uid is None and incoming is None and message_id is None and event_type is None:
            _clear_callback_journal()
            return

        has_event_type = event_type is not None and str(event_type) != ""

        def matches(entry: DialogCallbackJournalEntry) -> bool:
            if npc_uid is not None and entry.npc_uid != npc_uid:
                return False
            if incoming is not None and entry.incoming != incoming:
                return False
            if message_id is not None and entry.message_id != message_id:
                return False
            if has_event_type and entry.event_type != event_type:
                return False
            return True

        _dialog_callback_journal[:] = [
            entry for entry in _dialog_callback_journal if not matches(entry)
        ]
        _dialog_callback_journal_received.clear()
        _dialog_callback_journal_sent.clear()
        for entry in _dialog_callback_journal:
            (
                _dialog_callback_journal_received
                if entry.incoming
                else _dialog_callback_journal_sent
            ).append(entry)
# ── the runtime's state (``dialog.cpp``'s file-scope variables) ───────────────

#: The open dialog: agent, dialog id, the context id it belongs to, and whether that
#: id is authoritative. ``dialog.cpp:47-49`` keeps these in ``active_dialog_cache``.
_dialog_agent_id = 0
_dialog_id = 0
_context_dialog_id = 0
_dialog_id_authoritative = False
_dialog_message = ""

#: The buttons the client has announced for the open dialog (``dialog.cpp:86``).
_dialog_buttons: list[DialogButtonInfo] = []

#: The last dialog this module sent (``dialog.cpp:94``).
_last_selected_dialog_id = 0

#: A dialog this project sent, waiting for its body (``dialog.cpp:95-96``).
_pending_context_dialog_id = 0
_pending_context_agent_id = 0

#: The map-transition gate (``dialog.cpp:106-111``). Callbacks start **suspended** — the
#: source's own initialiser — and are only released once a ready map has been observed for
#: ``CALLBACK_RESUME_DELAY_MS``.
_shutdown_requested = False
_callbacks_suspended = True
_last_observed_map_id = 0
_last_observed_map_ready = False
_callbacks_resume_tick = 0

#: The decode counters (``dialog.cpp:104-108``). The map gate bumps them here, as the source
#: does, so nothing decoded later can be read as belonging to the map that just went away.
_decode_epoch = 0
_body_decode_nonce = 0

#: How many dialog-level decodes are in flight (``dialog.cpp:104``). A body's render is one;
#: ``Shutdown`` drains this counter before it lets the state go.
_dialog_pending_async_decode_count = 0


class _BodyDecodeRequest:
    """One body's decode, in the source's own fields (``DialogBodyDecodeRequest``, ``70-80``).

    Native fills this in when the body message arrives, hands ``encoded`` — the **copy** of the
    string ``DupWideStringSafe`` made — to the client's decoder, and reads the rest back out in
    the callback: the tick, map and model the row will carry, the epoch the decode belongs to,
    and the nonce that says which body it is. The port keeps the same record for the same
    reasons, and ``slot`` is where its copy went: the decode slot of the shared block the client
    reads the string out of and writes the text back into, which is the port's ``encoded`` and
    its ``param`` at once.
    """

    def __init__(
        self,
        *,
        slot: int,
        tick: int,
        message_id: int,
        agent_id: int,
        context_dialog_id: int,
        map_id: int,
        model_id: int,
        decode_epoch: int,
        decode_nonce: int,
    ) -> None:
        self.slot = int(slot)
        self.tick = int(tick)
        self.message_id = int(message_id)
        self.agent_id = int(agent_id)
        self.context_dialog_id = int(context_dialog_id)
        self.map_id = int(map_id)
        self.model_id = int(model_id)
        self.decode_epoch = int(decode_epoch)
        self.decode_nonce = int(decode_nonce)


#: The body decodes in flight, keyed by the decode slot each one is waiting in
#: (``dialog.cpp:70-80``). Native's wait on its own heap objects and the client's callback;
#: these wait on the same callback, delivered as a ``STRING_DECODED`` event.
_body_decodes: dict[int, _BodyDecodeRequest] = {}

#: The catalog's decodes in flight, keyed the same way: the slot, and the dialog id and epoch
#: the text belongs to. Native keeps one request per dialog id; the slot is what comes back in
#: the callback, so it is what the port keys on.
_catalog_decodes: dict[int, tuple[int, int]] = {}


class _ButtonDecodeRequest:
    """One button label's decode (``DialogButtonDecodeRequest``, ``dialog.cpp:82-92``).

    Native fills this in when the button message arrives and reads it back out in
    ``OnDialogButtonDecoded``: the tick, the button's dialog id, the context it belongs to, the
    map and model the row names, and the epoch the decode belongs to. ``slot`` is where its copy
    went, as it is for the body's request.
    """

    def __init__(
        self,
        *,
        slot: int,
        tick: int,
        message_id: int,
        dialog_id: int,
        context_dialog_id: int,
        agent_id: int,
        map_id: int,
        model_id: int,
        decode_epoch: int,
    ) -> None:
        self.slot = int(slot)
        self.tick = int(tick)
        self.message_id = int(message_id)
        self.dialog_id = int(dialog_id)
        self.context_dialog_id = int(context_dialog_id)
        self.agent_id = int(agent_id)
        self.map_id = int(map_id)
        self.model_id = int(model_id)
        self.decode_epoch = int(decode_epoch)


#: The button labels in flight, keyed by the slot each is waiting in, and the two maps the
#: source keeps around them: what each dialog id's label turned out to be, and which ids are
#: still being decoded (``dialog.cpp:87-89``).
_button_decodes: dict[int, _ButtonDecodeRequest] = {}
_decoded_button_label_cache: dict[int, str] = {}
_decoded_button_label_pending: dict[int, bool] = {}

#: The catalog's decode state (``dialog.cpp:113-121``). ``_decoded_text_cache`` holds what has
#: been rendered, keyed by dialog id, and ``_decoded_text_pending`` the ids whose decode is in
#: flight. The epoch is bumped whenever the catalog cache is cleared, so a decode that started
#: before the clear cannot write into it afterwards; ``_catalog_shutdown_requested`` is the
#: source's own flag, and the pending count is what its shutdown drains.
_decoded_text_cache: dict[int, str] = {}
_decoded_text_pending: dict[int, bool] = {}
_catalog_pending_async_decode_count = 0
_catalog_decode_epoch = 0
_catalog_shutdown_requested = False

#: The journals (``dialog.cpp:97-102``). Each message appends to the whole log and to the list
#: for its direction, and both are capped at :data:`MAX_DIALOG_EVENT_LOGS` from the **front**:
#: an overflow drops the oldest entry, which is what the source's erase does. The callback
#: journal is the same idea with richer rows and its own cap.
_dialog_event_logs: list[DialogEventLog] = []
_dialog_event_logs_received: list[DialogEventLog] = []
_dialog_event_logs_sent: list[DialogEventLog] = []
_dialog_callback_journal: list[DialogCallbackJournalEntry] = []
_dialog_callback_journal_received: list[DialogCallbackJournalEntry] = []
_dialog_callback_journal_sent: list[DialogCallbackJournalEntry] = []


def _append_dialog_event_log(
    message_id: int,
    incoming: bool,
    is_frame_message: bool,
    frame_id: int,
    w_bytes: bytes = b"",
    l_bytes: bytes = b"",
) -> None:
    """``AppendDialogEventLog`` (``dialog.cpp:457-491``): one dialog message, recorded twice.

    The message's two pointer arguments are **copied** in the source (``CopyBytesSafe``), so a
    pointer the client reuses cannot rewrite history; here the caller hands over the bytes it
    read, which is the same copy one step earlier.

    Both appends carry the cap **inline**, which is how the source writes them
    (``478-482`` and ``485-488``): the same two lines twice, not a helper.
    """

    entry = DialogEventLog(
        tick=_now_ms(),
        message_id=int(message_id),
        incoming=bool(incoming),
        is_frame_message=bool(is_frame_message),
        frame_id=int(frame_id),
        w_bytes=bytes(w_bytes),
        l_bytes=bytes(l_bytes),
    )
    _dialog_event_logs.append(entry)
    if len(_dialog_event_logs) > MAX_DIALOG_EVENT_LOGS:
        del _dialog_event_logs[: len(_dialog_event_logs) - MAX_DIALOG_EVENT_LOGS]
    direction = _dialog_event_logs_received if incoming else _dialog_event_logs_sent
    direction.append(entry)
    if len(direction) > MAX_DIALOG_EVENT_LOGS:
        del direction[: len(direction) - MAX_DIALOG_EVENT_LOGS]


def _build_npc_uid(map_id: int, model_id: int, agent_id: int) -> str:
    """``BuildNpcUid`` (``dialog.cpp``): ``map:model:agent``, empty without an agent."""

    if not agent_id:
        return ""
    return f"{int(map_id)}:{int(model_id)}:{int(agent_id)}"


def _agent_model_id(agent_id: int) -> int:
    """``GetAgentModelIdSafe`` (``dialog.cpp:201-218``): the agent's model number, ``0`` if none.

    The source's three answers are all here, in its order: no agent id is ``0``; the agent is
    read and a missing one is ``0``; its **living view** is taken and a null one is ``0``
    (``GetAsAgentLiving``, ``210-214``); and the model number is that view's ``player_number``.
    The ``__try`` around it answers ``0`` for anything that fails, which here is the exception a
    read can raise.

    The field is read **by name**, as the source reads it. An earlier version reached it through
    a dynamic name with a default, which is forbidden here for the reason the rule gives: it
    hides a wrong field or a wrong record behind a silent zero.
    """

    if not agent_id:
        return 0
    try:
        from .agent import Agent

        record = Agent.GetAgentByID(int(agent_id))
    except (OSError, RuntimeError):
        return 0
    if record is None:
        return 0
    if not record.is_living_type:
        return 0
    return int(record.player_number)


def _journal_event_priority(event_type: str) -> int:
    """``DialogCallbackJournalEventPriority``: body, then choice, then sent, then the rest."""

    if event_type == "recv_body":
        return 0
    if event_type == "recv_choice":
        return 1
    if event_type == "sent_choice":
        return 2
    return 3


def _sort_callback_journal(
    entries: list[DialogCallbackJournalEntry],
) -> list[DialogCallbackJournalEntry]:
    """``SortDialogCallbackJournalEntries``: by tick, then event, then direction.

    ``std::stable_sort`` with that comparator is Python's ``sorted`` with the same key: the
    tick first, then the event's priority, then incoming before sent. The sort is stable in
    both, so entries that agree on all three keep the order they arrived in.
    """

    return sorted(
        entries,
        key=lambda entry: (
            entry.tick,
            _journal_event_priority(entry.event_type),
            not entry.incoming,
        ),
    )


def _current_map_id() -> int:
    """``GetCurrentMapIdSafe`` (``dialog.cpp:193-199``): the live map id, ``0`` if unreadable.

    The source reads ``GW::map::GetMapID()`` inside a ``__try``; here the read is the ported
    ``Map.GetMapID()`` and the failure is the exception a read can raise — the same answer, the
    same shape as :func:`_agent_model_id` above.

    **It is deliberately not the last observed id.** This is the map a journal row carries when
    its caller named none (``dialog.cpp:514``), and the source reads it at append time — so a row
    appended after a transition carries the map the client is in now, not the one the module last
    looked at.
    """

    from .map import Map

    try:
        return int(Map.GetMapID())
    except (OSError, RuntimeError):
        return 0


def _append_dialog_callback_journal_entry(
    *,
    tick: int,
    message_id: int,
    incoming: bool,
    event_type: str,
    dialog_id: int,
    context_dialog_id: int,
    agent_id: int,
    dialog_id_authoritative: bool,
    context_dialog_id_inferred: bool,
    map_id: int | None = None,
    model_id: int | None = None,
    text: str = "",
) -> None:
    """``AppendDialogCallbackJournalEntry`` (``dialog.cpp:493-544``).

    ``map_id`` and ``model_id`` are optional the way the source's are: a caller that knows them
    passes them, and one that does not gets the live map and the agent's model number.
    """

    entry_map_id = _current_map_id() if map_id is None else int(map_id)
    entry_model_id = _agent_model_id(agent_id) if model_id is None else int(model_id)
    entry = DialogCallbackJournalEntry(
        tick=int(tick) or _now_ms(),
        message_id=int(message_id),
        incoming=bool(incoming),
        dialog_id=int(dialog_id),
        context_dialog_id=int(context_dialog_id),
        agent_id=int(agent_id),
        map_id=entry_map_id,
        model_id=entry_model_id,
        dialog_id_authoritative=bool(dialog_id_authoritative),
        context_dialog_id_inferred=bool(context_dialog_id_inferred),
        npc_uid=_build_npc_uid(entry_map_id, entry_model_id, agent_id),
        event_type=str(event_type),
        text=str(text),
    )
    _dialog_callback_journal.append(entry)
    if len(_dialog_callback_journal) > MAX_DIALOG_CALLBACK_JOURNAL:
        del _dialog_callback_journal[
            : len(_dialog_callback_journal) - MAX_DIALOG_CALLBACK_JOURNAL
        ]
    direction = (
        _dialog_callback_journal_received
        if incoming
        else _dialog_callback_journal_sent
    )
    direction.append(entry)
    if len(direction) > MAX_DIALOG_CALLBACK_JOURNAL:
        del direction[: len(direction) - MAX_DIALOG_CALLBACK_JOURNAL]


def _clear_event_logs() -> None:
    """``ClearDialogEventLogs`` (``dialog.cpp:1708-1713``): all three lists at once."""

    _dialog_event_logs.clear()
    _dialog_event_logs_received.clear()
    _dialog_event_logs_sent.clear()


def _clear_callback_journal() -> None:
    """``ClearDialogCallbackJournal`` (``dialog.cpp:1752-1757``)."""

    _dialog_callback_journal.clear()
    _dialog_callback_journal_received.clear()
    _dialog_callback_journal_sent.clear()


def _pending_decodes(what: str) -> int:
    """How many decodes are in flight for one of the two queues (``dialog.cpp:104``, ``119``).

    Both counters exist here: the dialog-level one counts a body's render while it runs, and
    the catalog's a dialog name's. A render is synchronous in this port, so either is non-zero
    only from inside the call that asked for it — which is why the drain below cannot wait on
    anything a caller did not already finish.
    """

    if what == "catalog":
        return _catalog_pending_async_decode_count
    return _dialog_pending_async_decode_count


def _drain_async_decodes(what: str) -> None:
    """The bounded drain ``Shutdown`` performs on one queue (``dialog.cpp:1344-1357``).

    The source waits on a condition variable its decode callbacks notify, and keeps waiting
    fail-closed after ``kDialogAsyncDrainTimeout`` with a log line. This port has no callback to
    notify it — a render happens inside the call that asks for it — so the wait is written for
    the case the source's is written for, and a counter that somehow stayed set raises rather
    than hanging: a library with no console reports through its return values and its
    exceptions, which is what :meth:`DialogTables.read_uint32` does with the in-client log too.
    """

    deadline = time.monotonic() + DIALOG_ASYNC_DRAIN_TIMEOUT_MS / 1000.0
    while _pending_decodes(what):
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"{_pending_decodes(what)} {what} dialog decodes were still in flight "
                f"{DIALOG_ASYNC_DRAIN_TIMEOUT_MS} ms after shutdown was requested."
            )
        time.sleep(0.001)


def _now_ms() -> int:
    """The port of ``GetTickCount64()``: a monotonic millisecond clock.

    Native reads the process uptime of the client it runs inside; this project needs the
    same kind of clock and only ever compares its values with each other, so a monotonic
    millisecond count is the equivalent.
    """

    return int(time.monotonic() * 1000)


def _map_state() -> tuple[int, bool]:
    """``GetDialogMapStateSafe`` (``dialog.cpp:167-180``): the map's id and readiness.

    Native asks the client for the raw map id and for the three readiness conditions. Here
    the readiness is the ported ``Map.IsMapReady()`` — the same condition, and the same one
    the readers gate on.

    The id is read **raw**: the source calls ``GW::map::GetMapID()`` and takes the id
    the client holds, with no readiness gate (``dialog.cpp:170``), and reads the three
    readiness conditions separately. Reforged's own ``Map.GetMapID()`` wrapper answers
    ``0`` while the map is not ready, which is a different value from the source's during
    exactly the window this state machine is about — so the field is read here instead.
    """

    from .context.gw_context import GWContext
    from .map import Map

    char_context = GWContext.Char.GetContext()
    map_id = int(char_context.current_map_id) if char_context else 0
    return map_id, Map.IsMapReady()


def _observe_map_change(current_map_id: int, current_map_ready: bool) -> None:
    """``ObserveMapChange`` (``dialog.cpp:548-588``), branch for branch.

    Called at the top of every captured message and by :func:`_poll_map_change`. When the map
    changes or stops being ready it suspends callbacks for ``CALLBACK_RESUME_DELAY_MS``;
    when the state actually becomes invalid it wipes the runtime state and bumps both decode
    counters.
    """

    global _last_observed_map_id, _last_observed_map_ready
    global _callbacks_suspended, _callbacks_resume_tick
    global _decode_epoch, _body_decode_nonce
    global _dialog_agent_id, _dialog_id, _context_dialog_id
    global _dialog_id_authoritative, _dialog_message
    global _last_selected_dialog_id, _pending_context_dialog_id, _pending_context_agent_id

    # ``dialog.cpp:549``: the clock is read first, before anything is compared.
    now = _now_ms()
    previous_map_id = _last_observed_map_id
    previous_map_ready = _last_observed_map_ready
    map_id_changed = previous_map_id != current_map_id
    map_ready_changed = previous_map_ready != current_map_ready
    if not map_id_changed and not map_ready_changed:
        return

    _last_observed_map_id = current_map_id
    _last_observed_map_ready = current_map_ready
    if _shutdown_requested:
        return

    if not current_map_ready or map_id_changed:
        _callbacks_suspended = True
        _callbacks_resume_tick = now + CALLBACK_RESUME_DELAY_MS

    should_invalidate_runtime_state = (map_id_changed and previous_map_id != 0) or (
        previous_map_ready and not current_map_ready
    )
    if not should_invalidate_runtime_state:
        return

    # ``dialog.cpp:578-587``: the invalidation block, written out here as the source writes it —
    # the same clears `ClearCache` makes, minus the journals and the gate, and with the two
    # decode counters bumped by this one.
    _dialog_agent_id = 0
    _dialog_id = 0
    _context_dialog_id = 0
    _dialog_id_authoritative = False
    _dialog_message = ""
    _dialog_buttons.clear()
    _last_selected_dialog_id = 0
    _pending_context_dialog_id = 0
    _pending_context_agent_id = 0
    _decoded_button_label_cache.clear()
    _decoded_button_label_pending.clear()
    _decode_epoch += 1
    _body_decode_nonce += 1


def _poll_map_change() -> None:
    """``PollMapChange`` (``dialog.cpp:1388-1409``) over the live map.

    **The one adaptation in this module.** Native calls this from its per-frame update loop,
    and this project has no loop, so the same check runs here where the source's own rules
    put reads: at each captured message and at each member call that serves the state. The
    decisions are the source's; only *when* the resume check is evaluated differs, and it can
    only run later than native's would, never earlier.
    """

    _maybe_resume(*_map_state())


def _maybe_resume(map_id: int, map_ready: bool) -> None:
    """The body of ``PollMapChange`` over a map state given to it.

    Split from :func:`_poll_map_change` so the resume decision can be driven with explicit
    inputs — the live map is only ever one case of it, and a check that can only run inside a
    running client is a check that cannot be tested.
    """

    global _callbacks_suspended, _callbacks_resume_tick

    _observe_map_change(map_id, map_ready)

    if not map_ready or map_id == 0:
        return

    now = _now_ms()
    if _shutdown_requested or not _callbacks_suspended:
        return
    if _last_observed_map_id != map_id or not _last_observed_map_ready:
        return
    if now < _callbacks_resume_tick:
        return

    _callbacks_suspended = False
    _callbacks_resume_tick = 0


def _reset() -> None:
    """Empty the module, as a module that has just been loaded.

    The C++ statics come up in this state by themselves; a Python module does not, so this is
    the port's own way of getting back to it — the offline suite uses it between tests. **The
    connection path does not call it**: ``connect()`` calls :meth:`Dialog.initialize`, which
    is the source's ``Initialize`` → ``ClearCache``, and that already wipes every list and
    record a previous client could have left behind and takes the gate from the live map.
    """

    global _callbacks_suspended, _last_observed_map_id, _last_observed_map_ready
    global _callbacks_resume_tick, _shutdown_requested, _decode_epoch, _body_decode_nonce
    global _dialog_pending_async_decode_count
    global _dialog_agent_id, _dialog_id, _context_dialog_id
    global _dialog_id_authoritative, _dialog_message
    global _last_selected_dialog_id, _pending_context_dialog_id, _pending_context_agent_id

    # The module's as-loaded state, which the C++ statics have by themselves: every dialog
    # record, the button list, the two label caches, and both counters.
    _dialog_agent_id = 0
    _dialog_id = 0
    _context_dialog_id = 0
    _dialog_id_authoritative = False
    _dialog_message = ""
    _dialog_buttons.clear()
    _last_selected_dialog_id = 0
    _pending_context_dialog_id = 0
    _pending_context_agent_id = 0
    _decoded_button_label_cache.clear()
    _decoded_button_label_pending.clear()
    _shutdown_requested = False
    _callbacks_suspended = True
    _last_observed_map_id = 0
    _last_observed_map_ready = False
    _callbacks_resume_tick = 0
    _decode_epoch = 0
    _body_decode_nonce = 0
    _dialog_pending_async_decode_count = 0
    _body_decodes.clear()
    _button_decodes.clear()
    _catalog_decodes.clear()
    _decoded_button_label_cache.clear()
    _decoded_button_label_pending.clear()


def _capture_message(event: EventRecord) -> None:
    """Take one of the client's dialog messages, the way ``dialog.cpp`` does.

    ``OnDialogUIMessage`` (``dialog.cpp:592-605``), guard for guard:

    1. read the map snapshot and **observe** it — a transition suspends callbacks and can
       wipe the state before this message is looked at;
    2. refuse a message the observer did not hand over. The source's check is ``if (!wparam)``
       (`dialog.cpp:595-597`), on the **packet pointer**, and the observer this project places
       already makes it before it dereferences anything. There is deliberately **no** check on
       the *words* of the packet: a body whose ``message_enc`` is zero and a button whose
       ``message`` is zero are ordinary messages to the source — it updates the cache, appends
       the button with the empty label, and appends both rows (`dialog.cpp:803-818`, `724-740`,
       `902-927`, `747-772`). A guard on those words here dropped every one of those whole.
    3. refuse while the module is shut down, while callbacks are suspended, or while the map
       is not ready;
    4. only then switch on which message it is.

    **Between 1 and 3 this also runs the source's resume check**, and that is the one place the
    port's lack of a frame loop has to be made good in the capture itself. In the source
    ``PollMapChange`` runs every frame, so a gate a transition closed is reopened a frame or two
    later — long before a dialog message needs it. There are no frames here, so the message that
    needs the gate is also the call that may reopen it: the same rule the module's other readers
    follow, and the check can only ever run *later* than the source's.

    The live run of 2026-09-25 that first failed had a **different** cause, and it is worth
    keeping the two apart. The connection published itself as the current client *after* its
    startup, so ``Initialize`` read no client at all and took the gate as suspended on an
    observed map of ``0 / False``; with no frames, nothing reopened it, and the body — arriving
    0.6 ms after the observation that first saw the real map — was refused, along with both of
    its buttons. That order is fixed in ``ConnectedClient._install_game_thread``, with
    ``tests/test_client_startup_offline.py`` pinning it. What the check here covers is a
    *genuine* transition: a message that arrives more than the resume delay after the map
    settled is captured, the way a per-frame poll would have captured it.

    Registered by the connection on the UI-message kind. The packet words arrive in order in
    ``arg0``..``arg3``, which is what lets a sixteen-byte packet be read whole:
    ``DialogBodyInfo`` is ``{type, agent_id, message_enc}`` and the client's
    ``DialogButtonInfo`` is ``{button_icon, message, dialog_id, skill_id}``.
    """

    map_id, map_ready = _map_state()
    _observe_map_change(map_id, map_ready)
    _maybe_resume(map_id, map_ready)

    if event.sequence not in (DIALOG_BODY_MESSAGE, DIALOG_BUTTON_MESSAGE):
        return
    if _shutdown_requested or _callbacks_suspended or not map_ready:
        return

    _dispatch_message(event)


def _dispatch_message(event: EventRecord) -> None:
    """The switch ``OnDialogUIMessage`` runs once its guards are past (``dialog.cpp:605``).

    Split out because the guards above need a client and the state machine does not: the
    offline suite drives this directly, and the live probes cover the guarded path end to
    end — a dialog opens, and the module captures its agent and buttons.

    Each case first appends the message to the event log, with the packet's bytes, before it
    touches any state — which is the source's order (``dialog.cpp:626``, ``783``).
    """

    if event.sequence == DIALOG_BODY_MESSAGE:
        _append_dialog_event_log(
            DIALOG_BODY_MESSAGE,
            True,
            False,
            0,
            struct.pack("<3I", int(event.arg0), int(event.arg1), int(event.arg2)),
        )
        _on_body(
            agent_id=int(event.arg1),
            message_enc=int(event.arg2),
            encoded_copy=_copied_string(event),
        )
    elif event.sequence == DIALOG_BUTTON_MESSAGE:
        _append_dialog_event_log(
            DIALOG_BUTTON_MESSAGE,
            True,
            False,
            0,
            struct.pack(
                "<4I",
                int(event.arg0),
                int(event.arg1),
                int(event.arg2),
                int(event.arg3),
            ),
        )
        _on_button(
            button_icon=int(event.arg0),
            dialog_id=int(event.arg2),
            label_pointer=int(event.arg1),
            encoded_copy=_copied_string(event),
        )


def _on_body(
    agent_id: int, message_enc: int, encoded_copy: list[int] | None
) -> None:
    """``dialog.cpp:774-927``: a new body replaces the whole dialog state, text and all.

    The body is the one dialog message that carries text, and the source handles it in two
    halves: the message replaces the state and records how the text will be obtained, and the
    text arrives from the client's decoder through a callback (``OnDialogBodyDecoded``,
    ``995-1054``). Both halves are here — this function is the message's, and
    :func:`_on_body_decoded` is the callback's — and every check between them is the source's:
    the copy of the string, which of the three outcomes it is, the epoch and nonce the text will
    be checked against, and the count ``Shutdown`` drains.

    ``encoded_copy`` is that copy — taken by the observer inside the client's own call, which is
    where the source takes it too (``dialog.cpp:832``) — and ``message_enc`` is the packet field
    it was taken through, kept because the packet is what this case is about. The copy is
    ``None`` for both of the source's empty cases: a null field, and a copy that could not be
    made (:func:`_copied_string`).

    What the port supplies in place of the in-process callback is the same protocol the source
    asks the client for (``py4gw.ui.async_decode``): the copy is placed in a decode slot of the
    shared block, the client's decoder is called with the emitted stub as its callback, and the
    completion comes back as an event.
    """

    global _dialog_agent_id, _dialog_id, _context_dialog_id
    global _dialog_id_authoritative, _dialog_message
    global _pending_context_dialog_id, _pending_context_agent_id
    global _body_decode_nonce, _dialog_pending_async_decode_count

    from .ui.async_decode import async_decode_str, begin_string_decode
    from .ui.encoded_str import is_valid_enc_str

    # ``dialog.cpp:780-781``, ``829``: the message's own tick, its map, and the agent's model
    # number, which the row carries whichever half appends it.
    tick = _now_ms()
    callback_map_id = _last_observed_map_id
    callback_model_id = _agent_model_id(agent_id)

    _dialog_agent_id = agent_id

    # The body belongs to the dialog this project just sent only when the agent
    # matches — or when the send recorded no agent at all.
    context_dialog_id = 0
    if _pending_context_dialog_id:
        if _pending_context_agent_id in (0, agent_id):
            context_dialog_id = _pending_context_dialog_id
    _pending_context_dialog_id = 0
    _pending_context_agent_id = 0

    _dialog_id = 0
    _context_dialog_id = context_dialog_id
    _dialog_id_authoritative = False
    _dialog_message = ""
    _dialog_buttons.clear()

    # ``dialog.cpp:819-820``: the epoch the text will be checked against, and this body's own
    # nonce, which is what stops a decode finishing late from writing into a newer body.
    request_epoch = _decode_epoch
    decode_nonce = _body_decode_nonce + 1
    _body_decode_nonce = decode_nonce

    # ``dialog.cpp:827-928``: **one flag and one text, appended once at the end.** The branches
    # below set them and fall through; the append is made in one place, under one guard. The
    # source writes it this way and so does this: three early returns, each with its own append,
    # is the same rows by a different structure.
    append_immediate = True
    immediate_text = ""

    # ``dialog.cpp:831-833``: no string at all, or a copy the source could not make. The flag
    # and the text stay as they are, so the row is appended below with nothing in it.
    if encoded_copy is not None and not is_valid_enc_str(encoded_copy):
        # ``dialog.cpp:834-855``: not an encoded string, so it is its own text — the open dialog
        # keeps the duplicated wide string whole, terminator included, and the row carries the
        # conversion that drops it (``WideToUtf8Safe``).
        immediate_text = _encoded_text_to_text(encoded_copy)
        if (
            not _shutdown_requested
            and not _callbacks_suspended
            and request_epoch == _decode_epoch
            and _dialog_agent_id == agent_id
            and _body_decode_nonce == decode_nonce
        ):
            _dialog_message = _encoded_text_to_text(encoded_copy)
    elif encoded_copy is not None:
        # ``dialog.cpp:856-901``: the string has to be decoded, so the source records a request
        # around the copy it made and hands that copy to the client's decoder. **Prepare, then
        # call**: the request is recorded and counted as in flight before ``SafeAsyncDecodeStr``,
        # so a completion cannot arrive before the record of what it belongs to exists.
        #
        # Its three exits decide whether the row below is appended: a call that went through
        # leaves ``append_immediate`` false, because ``OnDialogBodyDecoded`` appends the row; a
        # request that could not be allocated ``break``s out of the case with **no row at all**;
        # and a call that could not be made releases the request and leaves the flag alone.
        if not (
            _shutdown_requested or _callbacks_suspended or request_epoch != _decode_epoch
        ):
            encoded = _wide_bytes(encoded_copy)
            try:
                slot = begin_string_decode(encoded)
            except RuntimeError:
                # ``dialog.cpp:857-861``: `new (std::nothrow)` answered null, and the source
                # breaks out of the case — no row, no state written by this branch at all.
                return
            _dialog_pending_async_decode_count += 1
            _body_decodes[slot] = _BodyDecodeRequest(
                slot=slot,
                tick=tick,
                message_id=DIALOG_BODY_MESSAGE,
                agent_id=agent_id,
                context_dialog_id=context_dialog_id,
                map_id=callback_map_id,
                model_id=callback_model_id,
                decode_epoch=request_epoch,
                decode_nonce=decode_nonce,
            )
            if async_decode_str(encoded, slot):
                append_immediate = False
            else:
                # ``dialog.cpp:888-898``: the call did not go through, so the request is released
                # and the flag stays as it was — the row below carries the empty text.
                _body_decodes.pop(slot, None)
                if _dialog_pending_async_decode_count > 0:
                    _dialog_pending_async_decode_count -= 1

    if append_immediate:
        # ``dialog.cpp:902-927``: the append is made while the decode is still this one — the
        # epoch is the one the message captured — and while the module is neither shutting down
        # nor suspended. The twelve arguments are written out, as the source writes them.
        if (
            request_epoch == _decode_epoch
            and not _shutdown_requested
            and not _callbacks_suspended
        ):
            _append_dialog_callback_journal_entry(
                tick=tick,
                message_id=DIALOG_BODY_MESSAGE,
                incoming=True,
                event_type="recv_body",
                dialog_id=0,
                context_dialog_id=context_dialog_id,
                agent_id=agent_id,
                dialog_id_authoritative=False,
                context_dialog_id_inferred=context_dialog_id != 0,
                map_id=callback_map_id,
                model_id=callback_model_id,
                text=immediate_text,
            )


def _wide_bytes(codepoints: Sequence[int]) -> bytes:
    """Return a codepoint array as the wide string's bytes, terminator included.

    This is the copy the source makes with ``DupWideStringSafe`` (``dialog.cpp:237-252``) and
    hands to the client's decoder; the port has to hand over the same thing, because the string
    the client reads is a ``const wchar_t*``.
    """

    return b"".join(
        int(codepoint).to_bytes(2, "little") for codepoint in codepoints
    )


def _on_string_decoded(event: EventRecord) -> None:
    """``OnDialogBodyDecoded`` (``dialog.cpp:995-1054``) and its two siblings, as one entry.

    The client's decoder calls the emitted stub, the stub fills the slot, and the completion
    arrives here as an event — which is the port of the client calling back. Native has one
    callback per queue (the body's, a button label's, a catalog text's) and names it in the
    call; here the request the slot belongs to says which one it is.

    **The checks are the source's, and they are made on the request's recorded epoch and
    nonce rather than on the state as it stands:** whether the row is appended at all, and
    whether the text is written into the open dialog.
    """

    from .ui.async_decode import decoded_text

    slot = int(event.sequence)
    body_request = _body_decodes.pop(slot, None)
    if body_request is None:
        button_request = _button_decodes.pop(slot, None)
        if button_request is None:
            catalog_request = _catalog_decodes.pop(slot, None)
            if catalog_request is None:
                # A completion this module did not ask for. **It is left alone**: a decode slot is
                # shared by every module that hands a string to the client (the chat log's lines and
                # an agent's name are the other two), and taking a slot that belongs to one of them
                # consumes its answer and hands back the empty text -- measured live, an agent name
                # reached ``DONE`` and was then read as ``FREE`` with nothing cached, which is what
                # this line did to it. The chat module's own handler already returns without taking
                # (``chat.py:447-453``); this is the same rule.
                return
            text, _ = decoded_text(slot)
            _on_catalog_text_decoded(slot, catalog_request[0], catalog_request[1], text)
            return
        text, _ = decoded_text(slot)
        _on_button_decoded(button_request, text)
        return

    text, _ = decoded_text(slot)
    _on_body_decoded(
        tick=body_request.tick,
        request_epoch=body_request.decode_epoch,
        decode_nonce=body_request.decode_nonce,
        agent_id=body_request.agent_id,
        context_dialog_id=body_request.context_dialog_id,
        map_id=body_request.map_id,
        model_id=body_request.model_id,
        text=text,
    )


def _on_body_decoded(
    *,
    tick: int,
    request_epoch: int,
    decode_nonce: int,
    agent_id: int,
    context_dialog_id: int,
    map_id: int,
    model_id: int,
    text: str,
) -> None:
    """``OnDialogBodyDecoded`` (``dialog.cpp:999-1054``): the body's text is in hand.

    Two separate things are decided here, and the source decides them on the request's recorded
    epoch and nonce rather than on the state as it stands: whether the row is appended at all
    (the decode must still be current, the module must not be shutting down or suspended, and
    the map must be ready) and whether the text is written into the open dialog (that, and the
    body must still be the one that asked for it).
    """

    global _dialog_message, _dialog_pending_async_decode_count

    # ``dialog.cpp:1017-1020``: the decode stops being in flight the moment its text is in
    # hand, whichever way it ended — this is the count ``Shutdown`` waits on.
    if _dialog_pending_async_decode_count > 0:
        _dialog_pending_async_decode_count -= 1

    current_map_id, map_ready = _map_state()
    _observe_map_change(current_map_id, map_ready)

    append_journal = False
    if (
        not _shutdown_requested
        and not _callbacks_suspended
        and map_ready
        and request_epoch == _decode_epoch
    ):
        append_journal = True
        if _dialog_agent_id == agent_id and _body_decode_nonce == decode_nonce:
            # The source assigns the duplicated wide string, terminator and all; its readers
            # drop it — ``ActiveDialogInfo.message`` sanitises it away, ``raw_message`` keeps
            # it, exactly as Reforged's does.
            _dialog_message = text

    if append_journal:
        # ``dialog.cpp:1037-1051``: the completion's own row, through the guard it has already
        # made (`append_journal` above is the source's four-part test, ready map included).
        _append_dialog_callback_journal_entry(
            tick=tick,
            message_id=DIALOG_BODY_MESSAGE,
            incoming=True,
            event_type="recv_body",
            dialog_id=0,
            context_dialog_id=context_dialog_id,
            agent_id=agent_id,
            dialog_id_authoritative=False,
            context_dialog_id_inferred=context_dialog_id != 0,
            map_id=map_id,
            model_id=model_id,
            text=text,
        )


def _on_button(
    button_icon: int,
    dialog_id: int,
    label_pointer: int,
    encoded_copy: list[int] | None,
) -> None:
    """``dialog.cpp:605-770``: one button, its label, and the row the announcement leaves.

    Native's button case is three things at once, and this is all three: the label the packet
    points at is taken as it stands when it is not an encoded string, handed to the client's
    decoder when it is, and the button is appended with whatever the label state is by then.
    A label that has to be waited for is marked pending and its row is appended by the
    completion (:func:`_on_button_decoded`, ``1056-1106``); one that did not is recorded here.

    ``encoded_copy`` is the label as the observer copied it **inside the client's own call**,
    which is where the source copies it (``DupWideStringSafe(info->message)``, ``dialog.cpp:639``)
    and ``label_pointer`` is the packet field it was copied through.
    """

    global _dialog_pending_async_decode_count

    from .ui.async_decode import async_decode_str, begin_string_decode
    from .ui.encoded_str import is_valid_enc_str

    # ``dialog.cpp:612-625``: the tick, the context the open dialog carries, the epoch this
    # announcement belongs to, and the map and model the row will name.
    tick = _now_ms()
    context_dialog_id = _context_dialog_id or _dialog_id
    context_agent_id = _dialog_agent_id
    request_epoch = _decode_epoch
    callback_map_id = _last_observed_map_id
    callback_model_id = _agent_model_id(context_agent_id)

    label_text = ""
    label_pending = False

    # ``dialog.cpp:641-644``: not an encoded string, so the label is its own text — the branch
    # the source takes for a string its check rejects, and the one this port took for every label
    # while it was reading a buffer instead of the label.
    if encoded_copy is not None and not is_valid_enc_str(encoded_copy):
        label_text = _encoded_text_to_text(encoded_copy)
    elif encoded_copy is not None:
        # ``dialog.cpp:646-708``: the label has to be decoded, so the source records a request
        # around the copy it made and hands that copy to the client's decoder. **Prepare, then
        # call**: the request, its pending flag and the count are recorded before
        # ``SafeAsyncDecodeStr``, so a completion cannot arrive before the record of what it
        # belongs to exists — which matters here, because two of the wrapper's three refusals
        # answer the callback in the same call.
        #
        # The guard is the source's (``662-687``): no shutdown, no suspension, the epoch the
        # message captured, and the pending map below its cap — a label that finds the map full
        # is not waited for, so the button is appended with what it has and its row is appended
        # here. The port makes that check before it takes a slot rather than releasing one after,
        # which is the same decision with one fewer step (``_on_body`` does the same).
        queue_async_label = (
            not _shutdown_requested
            and not _callbacks_suspended
            and request_epoch == _decode_epoch
            and not (
                dialog_id not in _decoded_button_label_pending
                and len(_decoded_button_label_pending)
                >= MAX_DECODED_BUTTON_LABEL_PENDING
            )
        )
        if queue_async_label:
            encoded = _wide_bytes(encoded_copy)
            try:
                slot = begin_string_decode(encoded)
            except RuntimeError:
                # ``dialog.cpp:646-650``: ``new (std::nothrow)`` answered null, and the source
                # **breaks out of the case** — no row, no state written by this branch at all.
                return
            _decoded_button_label_pending[dialog_id] = True
            _dialog_pending_async_decode_count += 1
            _button_decodes[slot] = _ButtonDecodeRequest(
                slot=slot,
                tick=tick,
                message_id=DIALOG_BUTTON_MESSAGE,
                dialog_id=dialog_id,
                context_dialog_id=context_dialog_id,
                agent_id=context_agent_id,
                map_id=callback_map_id,
                model_id=callback_model_id,
                decode_epoch=request_epoch,
            )
            if async_decode_str(encoded, slot):
                label_pending = True
            else:
                # ``dialog.cpp:695-705``: the call did not go through, so the request is released,
                # the count given back under the source's own guard, and the id is no longer
                # waited for — the row is appended here with the empty label.
                _button_decodes.pop(slot, None)
                if _dialog_pending_async_decode_count > 0:
                    _dialog_pending_async_decode_count -= 1
                _decoded_button_label_pending.pop(dialog_id, None)

    # ``dialog.cpp:711-746``: a label this message carried is the one the dialog has, and the
    # button is appended with it.
    if (
        label_text
        and request_epoch == _decode_epoch
        and not _shutdown_requested
        and not _callbacks_suspended
    ):
        _decoded_button_label_cache[dialog_id] = label_text
        if len(_decoded_button_label_cache) > MAX_DECODED_BUTTON_LABEL_CACHE:
            _decoded_button_label_cache.pop(next(iter(_decoded_button_label_cache)))
        _decoded_button_label_pending.pop(dialog_id, None)

    if (
        request_epoch == _decode_epoch
        and not _shutdown_requested
        and not _callbacks_suspended
    ):
        _dialog_buttons.append(
            DialogButtonInfo(
                dialog_id=dialog_id,
                button_icon=button_icon,
                message=label_text,
                message_decoded=label_text,
                message_decode_pending=label_pending,
            )
        )
        if len(_dialog_buttons) > MAX_ACTIVE_DIALOG_BUTTONS:
            del _dialog_buttons[: len(_dialog_buttons) - MAX_ACTIVE_DIALOG_BUTTONS]

    # ``dialog.cpp:747-770``: the row, when the label did not have to be waited for. The append
    # carries the source's own guard — the epoch the announcement captured, no shutdown, no
    # suspension — written out here, as the source writes it.
    if not label_pending:
        if (
            request_epoch == _decode_epoch
            and not _shutdown_requested
            and not _callbacks_suspended
        ):
            _append_dialog_callback_journal_entry(
                tick=tick,
                message_id=DIALOG_BUTTON_MESSAGE,
                incoming=True,
                event_type="recv_choice",
                dialog_id=dialog_id,
                context_dialog_id=context_dialog_id,
                agent_id=context_agent_id,
                dialog_id_authoritative=True,
                context_dialog_id_inferred=context_dialog_id != 0,
                map_id=callback_map_id,
                model_id=callback_model_id,
                text=label_text,
            )


def _on_button_decoded(request: _ButtonDecodeRequest, text: str) -> None:
    """``OnDialogButtonDecoded`` (``dialog.cpp:1056-1106``): a button's label is in hand.

    The label is cached under the button's dialog id — which is what
    :func:`get_active_dialog_buttons` reads to fill the captions — its pending flag is cleared,
    and the row is appended unless the module has stopped recording.
    """

    global _dialog_pending_async_decode_count

    if _dialog_pending_async_decode_count > 0:
        _dialog_pending_async_decode_count -= 1

    current_map_id, map_ready = _map_state()
    _observe_map_change(current_map_id, map_ready)

    append_journal = False
    if (
        not _shutdown_requested
        and not _callbacks_suspended
        and map_ready
        and request.decode_epoch == _decode_epoch
    ):
        _decoded_button_label_cache[request.dialog_id] = text
        if len(_decoded_button_label_cache) > MAX_DECODED_BUTTON_LABEL_CACHE:
            _decoded_button_label_cache.pop(next(iter(_decoded_button_label_cache)))
        _decoded_button_label_pending.pop(request.dialog_id, None)
        append_journal = True

    if append_journal:
        # ``dialog.cpp:1089-1104``: the completion's own row, through the guard it already made
        # (`append_journal` above is the source's four-part test, ready map included).
        _append_dialog_callback_journal_entry(
            tick=request.tick,
            message_id=DIALOG_BUTTON_MESSAGE,
            incoming=True,
            event_type="recv_choice",
            dialog_id=request.dialog_id,
            context_dialog_id=request.context_dialog_id,
            agent_id=request.agent_id,
            dialog_id_authoritative=True,
            context_dialog_id_inferred=request.context_dialog_id != 0,
            map_id=request.map_id,
            model_id=request.model_id,
            text=text,
        )


def _note_sent_dialog(dialog_id: int, message_id: int) -> None:
    """Record a dialog this project is about to send, and to which agent.

    ``dialog.cpp:929-991`` — the whole ``kSendAgentDialog``/``kSendGadgetDialog`` case, one
    handler body with the first case falling through into the second. The runtime reaches that
    handler by *sending the message*; this project calls the function the handler calls, so the
    message never travels and the recording happens where the send does — ``Player.SendDialog``,
    which passes the message id it is sending (``0x30000014`` for an agent, ``0x30000015`` for a
    gadget), because the source logs **the id it handled** and not a constant.

    The handler's own guards come first, in its order: the message is refused outright while the
    map is not ready (``600-603``), the **event-log row is appended before** the shutdown and
    suspension check (``933-942`` precedes ``947-951``), and only the state assignments and the
    ``sent_choice`` row are skipped when the module is shut down or suspended.

    The text is the source's too: ``decoded_button_label_cache`` for the selected id first, the
    catalog's cached text as the fallback (``956-963``).
    """

    global _last_selected_dialog_id, _pending_context_dialog_id, _pending_context_agent_id
    global _dialog_id, _context_dialog_id, _dialog_id_authoritative

    map_id, map_ready = _map_state()
    _observe_map_change(map_id, map_ready)
    if not map_ready:
        return

    # ``dialog.cpp:933-942``: the row carries the **id itself** rather than a pointer (the source
    # passes ``&selected_id``), and it is appended whether or not the module is recording state.
    _append_dialog_event_log(
        message_id,
        False,
        False,
        0,
        struct.pack("<I", int(dialog_id) & 0xFFFFFFFF),
    )

    if _shutdown_requested or _callbacks_suspended:
        return

    # ``dialog.cpp:952-954``: the context the *open* dialog belongs to, read before the
    # assignments below, so the journal records what the send was answering.
    previous_context_dialog_id = _context_dialog_id or _dialog_id
    context_agent_id = _dialog_agent_id

    # ``dialog.cpp:956-963``: the label cache first, the catalog's cached text as the fallback.
    sent_text = _decoded_button_label_cache.get(dialog_id, "")
    if not sent_text:
        _, sent_text = _try_get_cached_dialog_text_decoded(dialog_id)

    _last_selected_dialog_id = dialog_id
    _pending_context_dialog_id = dialog_id
    _pending_context_agent_id = _dialog_agent_id
    _dialog_id = 0
    _context_dialog_id = dialog_id
    _dialog_id_authoritative = False

    _append_dialog_callback_journal_entry(
        tick=_now_ms(),
        message_id=message_id,
        incoming=False,
        event_type="sent_choice",
        dialog_id=dialog_id,
        context_dialog_id=previous_context_dialog_id,
        agent_id=context_agent_id,
        dialog_id_authoritative=True,
        context_dialog_id_inferred=previous_context_dialog_id != 0,
        text=sent_text,
    )


# ── the facade's getters (``Dialog.py:152-173``) ─────────────────────────────


def get_active_dialog() -> ActiveDialogInfo | None:
    """Return the open dialog, or ``None`` when the client has none.

    ``Dialog.py:152-162``: the source reports nothing when all three ids are zero, and
    that test is kept as written — an agent with no dialog id is still a dialog,
    because the body arrives before the buttons do.
    """

    info = Dialog.get_active_dialog()
    if info.dialog_id == 0 and info.context_dialog_id == 0 and info.agent_id == 0:
        return None
    return info


def get_active_dialog_buttons() -> list[DialogButtonInfo]:
    """Return the open dialog's buttons, in the order the client announced them.

    ``Dialog.py:165-173``: the buttons from the client if there are any, otherwise the
    choices parsed out of the body text. Both caption fields are **sanitised the way the
    source's own record constructor sanitises them** (``Dialog.py:103-104``, applied at
    ``167``): the native record carries the label as the client decoded it, and what a caller
    of the facade sees is the sanitised text, not the markup and tokens the client left in it.
    """

    buttons = _coerce_native_list(Dialog.get_active_dialog_buttons())
    if buttons:
        for button in buttons:
            button.message = sanitize_dialog_text(button.message)
            button.message_decoded = sanitize_dialog_text(button.message_decoded)
        return buttons
    active = get_active_dialog()
    if active is None:
        return []
    return extract_inline_dialog_choices_from_text(active.raw_message)
