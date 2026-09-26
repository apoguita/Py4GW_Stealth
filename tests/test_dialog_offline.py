"""Offline tests for the ported ``Dialog`` module, the surface behind it, and the state.

Three layers, tested together because they are one subsystem in the source:

- the **facade** Reforged's ``Py4GWCoreLib/Dialog.py`` defines — two getters, two data
  classes, the text sanitiser, the inline-choice parser, and three helpers;
- the **surface** ``PyDialog`` binds — 32 static methods and six record classes — of
  which eleven are served (five from the state below, six from the metadata tables) and
  the rest refuse with a named mechanism;
- the **state** ``src/GW/dialog/dialog.cpp`` keeps, fed by the client's own
  ``kDialogBody`` and ``kDialogButton`` messages. The connection registers the capture;
  these tests drive it directly, because a client cannot be asked to open a dialog on
  demand.

What this does not prove: that the client sends those messages in that shape. That is
live work, and ``tests/test_live_player.py`` reports what arrives when an interaction
opens a dialog. What it does prove is everything downstream of the message: which word
becomes which field, that a body resets the buttons, that a sent dialog is tied to the
body that answers it, that every member of the source surface exists, and that the ones
that cannot work say which mechanism they are waiting for.
"""

from __future__ import annotations

import inspect
import struct
import unittest
from collections.abc import Sequence
from typing import Any, cast
from unittest import mock

from py4gw import dialog
from py4gw.game_thread.shared_block import CallForm as CallFormat
from py4gw.game_thread.shared_block import EventKind, EventRecord, EventTextState
from py4gw.internals import string_table
from py4gw.ui.encoded_str import uint32_to_enc_str

DIALOG_BODY = dialog.DIALOG_BODY_MESSAGE
DIALOG_BUTTON = dialog.DIALOG_BUTTON_MESSAGE
DIALOG_SEND = dialog.DIALOG_SEND_AGENT_MESSAGE

#: The synthetic client the table resolver reads: an ``.rdata`` window it can read a
#: word from or buffer whole, and the two section ranges the source's rules compare
#: against. It stands in for ``RemoteScanner`` plus ``ProcessMemoryReader``, and it
#: serves the resolver's two read paths from the same bytes so a test can place a table
#: in one place and see both stages agree about it.
RDATA_START = 0x1000
RDATA_END = 0x11000
TEXT_START = 0x20000
TEXT_END = 0x30000

#: Where a valid flags column is placed in the synthetic ``.rdata``.
FLAGS_AT = 0x2000


class _Memory:
    """A flat byte image with the two reads the resolver makes.

    It covers ``.rdata`` and ``.text`` — not just the data section — because the loader check
    reads the candidate's entry bytes, and a client whose code section cannot be read is a
    client whose loader cannot be confirmed.
    """

    def __init__(self, start: int, size: int) -> None:
        self.start = start
        self.data = bytearray(size)

    def write_u32(self, address: int, value: int) -> None:
        offset = address - self.start
        self.data[offset : offset + 4] = int(value).to_bytes(4, "little")

    def read(self, address: int, size: int) -> bytes:
        offset = address - self.start
        if offset < 0 or offset + size > len(self.data):
            raise OSError(f"unreadable at 0x{address:X}")
        return bytes(self.data[offset : offset + size])

    def read_u32(self, address: int) -> int:
        return int.from_bytes(self.read(address, 4), "little")


class _Range:
    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end


class _FakeScanner:
    """``RemoteScanner``'s two operations, over one :class:`_Memory`."""

    def __init__(self, memory: _Memory, sections: dict[str, _Range]) -> None:
        self._memory = memory
        self._sections = sections

    def read_uint32(self, address: int) -> int:
        return self._memory.read_u32(address)

    def get_section_range(self, name: str) -> _Range:
        if name not in self._sections:
            raise ValueError(f"Unknown module section: {name}")
        return self._sections[name]


class _Resolution:
    def __init__(self, value: int) -> None:
        self.ok = value != 0
        self.value = value


class _FakePatterns:
    """``PatternCatalog.resolve`` for the six dialog resolvers."""

    def __init__(self, bases: dict[str, int], loader: int = 0) -> None:
        self.bases = dict(bases)
        self.loader = loader

    def resolve(self, name: str, scanner: object) -> _Resolution:
        if name == dialog.DialogTables._LOADER_RESOLVER:
            return _Resolution(self.loader)
        return _Resolution(self.bases.get(name, 0))


def _client_memory(
    bases: dict[str, int] | None = None,
    *,
    mode: str = "empty",
) -> tuple[_Memory, _FakeScanner, _FakePatterns]:
    """Build one synthetic client for the resolver.

    The window starts filled with ``0xFFFFFFFF``, which is what makes the source's two
    rules mean something: a word above ``0xFFFF`` fails the flags rule, and a word that
    is neither zero nor inside ``.text`` fails the handler rule. Real ``.rdata`` is
    dense with both, which is why a window that merely *overlaps* a table does not
    survive — a sparse image would let a shifted window pass, and that is the source's
    algorithm behaving as written rather than a property worth testing for.

    ``mode`` then chooses what is written over the filler:

    - ``empty`` — nothing, so no window passes and no base resolves;
    - ``valid`` — the five columns of a table at :data:`FLAGS_AT`, every row readable,
      flags never above ``0xFFFF``, one row enabled, its handler inside ``.text``.
    """

    memory = _Memory(RDATA_START, TEXT_END - RDATA_START)
    for offset in range(0, RDATA_END - RDATA_START, 4):
        memory.write_u32(RDATA_START + offset, 0xFFFFFFFF)

    if mode == "valid":
        for index in range(dialog.MAX_DIALOG_ID + 1):
            offset = index * dialog.FLAGS_STRIDE
            memory.write_u32(FLAGS_AT + offset, 0x1 if index in (0, 5) else 0x0)
            memory.write_u32(FLAGS_AT - 0x8 + offset, 0)
            memory.write_u32(FLAGS_AT - 0x4 + offset, 0)
            memory.write_u32(FLAGS_AT + 0x4 + offset, 0)
            memory.write_u32(FLAGS_AT + 0x8 + offset, 0)
        memory.write_u32(FLAGS_AT - 0x8 + 5 * dialog.FLAGS_STRIDE, TEXT_START)

    sections = {
        "rdata": _Range(RDATA_START, RDATA_END),
        "text": _Range(TEXT_START, TEXT_END),
    }
    names = (
        "flags_base",
        "frame_type_base",
        "event_handler_base",
        "content_id_base",
        "property_id_base",
    )
    resolved = {f"dialog.{name}": (bases or {}).get(name, 0) for name in names}
    return memory, _FakeScanner(memory, sections), _FakePatterns(resolved)


#: The five bases as the source lays them out: the event handler eight bytes below the
#: flags column, the frame type four below it, the two id columns four and eight above.
#: ``DialogMemory`` (``dialog.h:94-99``) is exactly this shape, and so is the derivation
#: ``BuildResolvedDialogTables`` makes from a scanned flags base.
STATIC_BASES = {
    "flags_base": FLAGS_AT,
    "frame_type_base": FLAGS_AT - 0x4,
    "event_handler_base": FLAGS_AT - 0x8,
    "content_id_base": FLAGS_AT + 0x4,
    "property_id_base": FLAGS_AT + 0x8,
}

#: Every module member of Reforged's ``Py4GWCoreLib/Dialog.py``, transcribed from that
#: file. The port must expose all of them.
REFORGED_DIALOG_MEMBERS = (
    "_safe_call",
    "_call_native_dialog_method",
    "_coerce_native_list",
    "sanitize_dialog_text",
    "ActiveDialogInfo",
    "DialogButtonInfo",
    "_parse_inline_choice_dialog_id",
    "extract_inline_dialog_choices_from_text",
    "get_active_dialog",
    "get_active_dialog_buttons",
)

#: Every static method ``PyDialog`` binds (``dialog_bindings.cpp:103-138``), transcribed
#: from that file. Native surface Reforged's Python never wraps, and it is still
#: declared here: the port takes the whole surface, working or refused.
PYDIALOG_MEMBERS = (
    "is_dialog_available",
    "get_dialog_info",
    "get_last_selected_dialog_id",
    "get_active_dialog",
    "get_active_dialog_buttons",
    "is_dialog_active",
    "is_dialog_displayed",
    "enumerate_available_dialogs",
    "get_dialog_text_decoded",
    "is_dialog_text_decode_pending",
    "get_dialog_text_decode_status",
    "read_dialog_flags",
    "read_dialog_frame_type",
    "read_dialog_event_handler",
    "read_dialog_content_id",
    "read_dialog_property_id",
    "get_dialog_event_logs",
    "get_dialog_event_logs_received",
    "get_dialog_event_logs_sent",
    "clear_dialog_event_logs",
    "clear_dialog_event_logs_received",
    "clear_dialog_event_logs_sent",
    "get_dialog_callback_journal",
    "get_dialog_callback_journal_received",
    "get_dialog_callback_journal_sent",
    "clear_dialog_callback_journal",
    "clear_dialog_callback_journal_received",
    "clear_dialog_callback_journal_sent",
    "clear_dialog_callback_journal_filtered",
    "clear_cache",
    "initialize",
    "terminate",
)

#: The record classes the binding declares (``dialog_bindings.cpp:94-100``).
PYDIALOG_RECORDS = (
    "DialogInfo",
    "ActiveDialogInfo",
    "DialogButtonInfo",
    "DialogTextDecodedInfo",
    "DialogEventLog",
    "DialogCallbackJournalEntry",
)

#: The five whose data this port already has, and what each returns with no dialog.
SERVED_BY_STATE = (
    ("get_active_dialog", lambda: dialog.PyDialog.get_active_dialog()),
    ("get_active_dialog_buttons", lambda: dialog.PyDialog.get_active_dialog_buttons()),
    ("get_last_selected_dialog_id", lambda: dialog.PyDialog.get_last_selected_dialog_id()),
    ("is_dialog_displayed", lambda: dialog.PyDialog.is_dialog_displayed(7)),
    ("clear_cache", lambda: dialog.PyDialog.clear_cache()),
)

#: The six the metadata tables answer. They read the connected client, so a test needs
#: a client with a scanner; what is pinned here is that they are *served* — the read
#: path itself is exercised against the live client.
SERVED_BY_TABLES = (
    ("is_dialog_available", lambda: dialog.PyDialog.is_dialog_available(1)),
    ("read_dialog_flags", lambda: dialog.PyDialog.read_dialog_flags(1)),
    ("read_dialog_frame_type", lambda: dialog.PyDialog.read_dialog_frame_type(1)),
    ("read_dialog_event_handler", lambda: dialog.PyDialog.read_dialog_event_handler(1)),
    ("read_dialog_content_id", lambda: dialog.PyDialog.read_dialog_content_id(1)),
    ("read_dialog_property_id", lambda: dialog.PyDialog.read_dialog_property_id(1)),
)

#: The member the frame array answers (``dialog.cpp:1666-1682``). Like the table readers it
#: needs a connected client; what is pinned here is that it is *served*, and the lookup and
#: state bits themselves are pinned in ``test_ui_frame_offline.py``.
SERVED_BY_FRAMES = (
    ("is_dialog_active", lambda: dialog.PyDialog.is_dialog_active()),
)

#: The lifecycle member the connection now calls at install (``dialog.cpp:1315-1331``).
SERVED_BY_LIFECYCLE = (
    ("initialize", lambda: dialog.PyDialog.initialize()),
)

#: The five the catalog's decode queue answers (``dialog.cpp:1136-1254`` and the members
#: around it). They read the client and, on the first call for a dialog, queue its decode;
#: with no connected client the gate is closed, so what is pinned here is that they answer
#: the source's empty value rather than refusing. The queue itself is driven in
#: ``DialogDecodeQueueTests``.
SERVED_BY_CATALOG = (
    ("get_dialog_info", lambda: dialog.PyDialog.get_dialog_info(1)),
    ("enumerate_available_dialogs", lambda: dialog.PyDialog.enumerate_available_dialogs()),
    ("get_dialog_text_decoded", lambda: dialog.PyDialog.get_dialog_text_decoded(1)),
    (
        "is_dialog_text_decode_pending",
        lambda: dialog.PyDialog.is_dialog_text_decode_pending(1),
    ),
    (
        "get_dialog_text_decode_status",
        lambda: dialog.PyDialog.get_dialog_text_decode_status(),
    ),
)

#: The thirteen the runtime's journals answer (``dialog.cpp:1693-1817``). The getters answer
#: the source's empty list with nothing recorded, and the clears answer by doing their job.
SERVED_BY_JOURNALS = (
    ("get_dialog_event_logs", lambda: dialog.PyDialog.get_dialog_event_logs()),
    (
        "get_dialog_event_logs_received",
        lambda: dialog.PyDialog.get_dialog_event_logs_received(),
    ),
    ("get_dialog_event_logs_sent", lambda: dialog.PyDialog.get_dialog_event_logs_sent()),
    ("clear_dialog_event_logs", lambda: dialog.PyDialog.clear_dialog_event_logs()),
    (
        "clear_dialog_event_logs_received",
        lambda: dialog.PyDialog.clear_dialog_event_logs_received(),
    ),
    ("clear_dialog_event_logs_sent", lambda: dialog.PyDialog.clear_dialog_event_logs_sent()),
    ("get_dialog_callback_journal", lambda: dialog.PyDialog.get_dialog_callback_journal()),
    (
        "get_dialog_callback_journal_received",
        lambda: dialog.PyDialog.get_dialog_callback_journal_received(),
    ),
    (
        "get_dialog_callback_journal_sent",
        lambda: dialog.PyDialog.get_dialog_callback_journal_sent(),
    ),
    ("clear_dialog_callback_journal", lambda: dialog.PyDialog.clear_dialog_callback_journal()),
    (
        "clear_dialog_callback_journal_received",
        lambda: dialog.PyDialog.clear_dialog_callback_journal_received(),
    ),
    (
        "clear_dialog_callback_journal_sent",
        lambda: dialog.PyDialog.clear_dialog_callback_journal_sent(),
    ),
    (
        "clear_dialog_callback_journal_filtered",
        lambda: dialog.PyDialog.clear_dialog_callback_journal_filtered(),
    ),
    ("terminate", lambda: dialog.PyDialog.terminate()),
)

#: Nothing refuses. The surface is complete: every one of the 32 bound methods answers, and the
#: only refusal left in this module is the facade helper that would reach a binding object by
#: dynamic name (``_call_native_dialog_method``, a documented divergence).
REFUSED_MEMBERS: tuple[tuple[str, Any], ...] = ()


def message(
    kind: int,
    arg0: int = 0,
    arg1: int = 0,
    arg2: int = 0,
    arg3: int = 0,
    text: Sequence[int] | None = None,
) -> EventRecord:
    """Build one UI-message event record.

    ``text`` is the copy the observer took of the string the message named, and it is what a
    body's or a button's label is read from now: the client's own code units, terminator
    included, exactly as ``DupWideStringSafe`` gives native them (``dialog.cpp:237-252``).
    ``None`` is a message with no string at all — the source's null pointer, or a copy that
    could not be made.
    """

    if text is None:
        return EventRecord(
            kind=EventKind.UI_MESSAGE,
            sequence=kind,
            arg0=arg0,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            tick=0,
        )
    return EventRecord(
        kind=EventKind.UI_MESSAGE,
        sequence=kind,
        arg0=arg0,
        arg1=arg1,
        arg2=arg2,
        arg3=arg3,
        tick=0,
        text_state=EventTextState.COPIED,
        text=tuple(text),
    )


class DialogGateTests(unittest.TestCase):
    """The map-transition gate: ``ObserveMapChange`` and ``PollMapChange``.

    ``dialog.cpp:548-588`` and ``1388-1409``. The gate is host logic over two inputs — the
    map's id and its readiness — so it is driven here with explicit values. The source
    starts with callbacks **suspended** (``dialog.cpp:107``) and only a ready map that has
    been observed for ``CALLBACK_RESUME_DELAY_MS`` releases them.
    """

    def setUp(self) -> None:
        dialog._reset()

    def tearDown(self) -> None:
        dialog._reset()

    def test_callbacks_start_suspended(self) -> None:
        """The source's own initialiser, before any map has been observed."""

        self.assertTrue(dialog._callbacks_suspended)
        self.assertEqual(dialog._last_observed_map_id, 0)
        self.assertFalse(dialog._last_observed_map_ready)

    def test_an_unchanged_map_does_nothing(self) -> None:
        dialog._observe_map_change(7, True)

        dialog._observe_map_change(7, True)

        self.assertTrue(dialog._callbacks_suspended)
        self.assertEqual(dialog._decode_epoch, 0)

    def test_a_map_change_suspends_but_does_not_wipe_on_the_first_observation(self) -> None:
        """``previous_map_id != 0`` is part of the invalidation rule."""

        dialog._on_body(241, 0, None)

        dialog._observe_map_change(7, True)

        self.assertTrue(dialog._callbacks_suspended)
        self.assertGreater(dialog._callbacks_resume_tick, 0)
        self.assertEqual(
            dialog._dialog_agent_id,
            241,
            "the first observation has no previous map to invalidate against",
        )

    def test_a_later_map_change_suspends_and_wipes(self) -> None:
        dialog._observe_map_change(7, True)
        dialog._on_body(241, 0, None)

        dialog._observe_map_change(8, True)

        self.assertTrue(dialog._callbacks_suspended)
        self.assertEqual(dialog._dialog_agent_id, 0)
        self.assertEqual(dialog._decode_epoch, 1)
        self.assertEqual(
            dialog._body_decode_nonce,
            2,
            "the body takes a nonce of its own (``dialog.cpp:820``) and the wipe takes the "
            "next one",
        )

    def test_a_map_that_stops_being_ready_suspends_and_wipes(self) -> None:
        dialog._observe_map_change(7, True)
        dialog._on_body(241, 0, None)

        dialog._observe_map_change(7, False)

        self.assertTrue(dialog._callbacks_suspended)
        self.assertEqual(dialog._dialog_agent_id, 0)

    def test_resume_waits_for_the_delay(self) -> None:
        dialog._observe_map_change(7, True)

        dialog._maybe_resume(7, True)

        self.assertTrue(dialog._callbacks_suspended, "the delay has not passed")

        dialog._callbacks_resume_tick = dialog._now_ms() - 1
        dialog._maybe_resume(7, True)

        self.assertFalse(dialog._callbacks_suspended)
        self.assertEqual(dialog._callbacks_resume_tick, 0)

    def test_resume_needs_a_ready_map(self) -> None:
        dialog._observe_map_change(7, True)
        dialog._callbacks_resume_tick = dialog._now_ms() - 1

        dialog._maybe_resume(7, False)

        self.assertTrue(dialog._callbacks_suspended)

    def test_resume_needs_the_currently_observed_map(self) -> None:
        """``last_observed_map_id != map_id`` returns before the resume."""

        dialog._observe_map_change(7, True)
        dialog._callbacks_resume_tick = dialog._now_ms() - 1

        dialog._maybe_resume(9, True)

        self.assertTrue(dialog._callbacks_suspended)

    def test_a_shutdown_stops_the_gate_from_resuming(self) -> None:
        dialog._observe_map_change(7, True)
        dialog._callbacks_resume_tick = dialog._now_ms() - 1
        dialog._shutdown_requested = True

        dialog._maybe_resume(7, True)

        self.assertTrue(dialog._callbacks_suspended)

    def test_clear_cache_takes_the_gate_from_the_map(self) -> None:
        """``ClearCache`` re-reads the map rather than leaving the gate wherever it was."""

        dialog._observe_map_change(7, True)
        dialog._callbacks_resume_tick = dialog._now_ms() - 1
        dialog._maybe_resume(7, True)
        self.assertFalse(dialog._callbacks_suspended)

        dialog.PyDialog.clear_cache()

        # With no connection the ported map reads answer "not loaded", so the gate is
        # suspended again and the observed map is the empty one.
        self.assertTrue(dialog._callbacks_suspended)
        self.assertEqual(dialog._last_observed_map_id, 0)
        self.assertFalse(dialog._last_observed_map_ready)


class DialogCaptureGuardTests(unittest.TestCase):
    """The guards ``OnDialogUIMessage`` applies before it looks at the message.

    ``dialog.cpp:592-603``: the map snapshot and its observation, a null packet, and the
    shutdown/suspended/map-ready check. Only a connected, ready client gets past them, which
    is why the state-machine tests drive :func:`py4gw.dialog._dispatch_message` instead.
    """

    def setUp(self) -> None:
        dialog._reset()
        # The capture refuses every message while callbacks are suspended, so the gate is open
        # in these tests exactly as it is when a client's message reaches the module.
        dialog._callbacks_suspended = False

    def tearDown(self) -> None:
        dialog._reset()

    def test_a_message_needs_a_map_that_is_ready(self) -> None:
        """With no client the ported map reads answer "not loaded", and the message is dropped."""

        dialog._capture_message(message(DIALOG_BODY, arg1=241, arg2=0x1000))

        self.assertEqual(dialog._dialog_agent_id, 0)

    def test_a_null_packet_word_is_dropped(self) -> None:
        """The source refuses a null ``wparam`` before anything else looks at it."""

        dialog._callbacks_suspended = False

        dialog._capture_message(message(DIALOG_BODY, arg1=241, arg2=0))

        self.assertEqual(dialog._dialog_agent_id, 0)

    def test_the_guard_runs_before_the_switch(self) -> None:
        """A message for a different message id is not dispatched either."""

        dialog._callbacks_suspended = False

        dialog._capture_message(message(0x100000FF, arg1=241, arg2=0x1000))

        self.assertEqual(dialog._dialog_agent_id, 0)


class DialogSurfaceTests(unittest.TestCase):
    """Every member the sources declare, present and accounted for."""

    def test_every_reforged_module_member_exists(self) -> None:
        for name in REFORGED_DIALOG_MEMBERS:
            with self.subTest(member=name):
                self.assertTrue(
                    hasattr(dialog, name),
                    f"Dialog.py declares {name} and this port must too",
                )

    def test_every_pydialog_method_exists_and_is_static(self) -> None:
        for name in PYDIALOG_MEMBERS:
            with self.subTest(member=name):
                self.assertTrue(hasattr(dialog.PyDialog, name))
                self.assertIsInstance(
                    inspect.getattr_static(dialog.PyDialog, name), staticmethod
                )

    def test_every_bound_record_class_exists(self) -> None:
        for name in PYDIALOG_RECORDS:
            with self.subTest(record=name):
                self.assertTrue(hasattr(dialog, name))

    def test_the_method_list_is_the_bindings_own(self) -> None:
        """32 static methods, no more and no fewer than the binding declares."""

        self.assertEqual(len(PYDIALOG_MEMBERS), 32)
        self.assertEqual(len(set(PYDIALOG_MEMBERS)), 32)

    def test_the_served_and_refused_sets_cover_the_surface(self) -> None:
        """This is what keeps a refactor from quietly dropping a member."""

        served = {name for name, _ in SERVED_BY_STATE}
        served |= {name for name, _ in SERVED_BY_TABLES}
        served |= {name for name, _ in SERVED_BY_FRAMES}
        served |= {name for name, _ in SERVED_BY_LIFECYCLE}
        served |= {name for name, _ in SERVED_BY_CATALOG}
        served |= {name for name, _ in SERVED_BY_JOURNALS}
        refused = {name for name, _ in REFUSED_MEMBERS}
        self.assertEqual(served & refused, set())
        self.assertEqual(served | refused, set(PYDIALOG_MEMBERS))

    def test_no_member_of_the_surface_refuses(self) -> None:
        """The whole surface answers; ``REFUSED_MEMBERS`` being empty is the claim, not a gap.

        Every member is called with the no-client values its own guards accept, and a
        ``NotImplementedError`` from any of them is the failure. This is what "the class is
        ported" means for the surface, and it is asserted rather than described.
        """

        self.assertEqual(REFUSED_MEMBERS, ())
        for name, call in (
            SERVED_BY_STATE
            + SERVED_BY_TABLES
            + SERVED_BY_FRAMES
            + SERVED_BY_LIFECYCLE
            + SERVED_BY_CATALOG
            + SERVED_BY_JOURNALS
        ):
            with self.subTest(member=name):
                try:
                    call()
                except NotImplementedError as error:
                    self.fail(f"{name} refuses: {error}")
                except Exception:
                    # A member that reads the client fails as a read when there is none; that
                    # is a missing connection, not a missing port.
                    pass

    def test_the_table_members_are_served_not_refused(self) -> None:
        """They read the client; without one they fail as reads, never as refusals."""

        for name, call in (
            SERVED_BY_TABLES
            + SERVED_BY_FRAMES
            + SERVED_BY_LIFECYCLE
            + SERVED_BY_CATALOG
            + SERVED_BY_JOURNALS
        ):
            with self.subTest(member=name):
                try:
                    call()
                except NotImplementedError as error:
                    self.fail(f"{name} refuses: {error}")
                except Exception:
                    pass

    def test_the_facade_helper_that_reached_a_binding_refuses(self) -> None:
        """It is declared for parity; there is no binding object to reach here."""

        with self.assertRaises(NotImplementedError) as caught:
            dialog._call_native_dialog_method("get_active_dialog", None)
        self.assertIn("Dialog._call_native_dialog_method", str(caught.exception))


class DialogServedMembersTests(unittest.TestCase):
    """The five members the captured state already answers."""

    def setUp(self) -> None:
        dialog._reset()
        # The send path is the source's handler case, whose outer guard refuses the
        # message while the map is not ready (`dialog.cpp:600-603`); these classes have no
        # client, so the map state is stubbed as the body tests stub it.
        self._map = mock.patch.object(dialog, "_map_state", return_value=(7, True))
        self._map.start()
        self.addCleanup(self._map.stop)
        # The capture refuses every message while callbacks are suspended, so the gate is open
        # in these tests exactly as it is when a client's message reaches the module.
        dialog._observe_map_change(*dialog._map_state())
        dialog._callbacks_suspended = False

    def tearDown(self) -> None:
        dialog._reset()

    def test_the_open_dialog_is_read_from_the_state(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        info = dialog.PyDialog.get_active_dialog()

        self.assertEqual(info.agent_id, 241)
        self.assertEqual(info.dialog_id, 0)

    def test_buttons_come_from_the_state(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg0=7, arg2=0x0A00002A))

        buttons = dialog.PyDialog.get_active_dialog_buttons()

        self.assertEqual([button.dialog_id for button in buttons], [0x0A00002A])

    def test_is_dialog_displayed_matches_the_open_dialog(self) -> None:
        """``dialog.cpp:1684-1692``: true for the id or the context id, false for zero."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        self.assertFalse(dialog.PyDialog.is_dialog_displayed(0))
        self.assertFalse(dialog.PyDialog.is_dialog_displayed(7))

        dialog._note_sent_dialog(0x0A00002A, DIALOG_SEND)
        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        self.assertTrue(dialog.PyDialog.is_dialog_displayed(0x0A00002A))

    def test_the_last_selected_dialog_id_is_what_was_sent(self) -> None:
        """``dialog.cpp:967``, set in the branch that handles a sent dialog."""

        self.assertEqual(dialog.PyDialog.get_last_selected_dialog_id(), 0)

        dialog._note_sent_dialog(0x0A00002A, DIALOG_SEND)

        self.assertEqual(dialog.PyDialog.get_last_selected_dialog_id(), 0x0A00002A)

    def test_clear_cache_empties_the_state(self) -> None:
        """``dialog.cpp:1819-1835`` clears the cache, the buttons and the sent id."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg2=7))
        dialog._note_sent_dialog(9, DIALOG_SEND)

        dialog.PyDialog.clear_cache()

        self.assertEqual(dialog.PyDialog.get_active_dialog().agent_id, 0)
        self.assertEqual(dialog.PyDialog.get_active_dialog_buttons(), [])
        self.assertEqual(dialog.PyDialog.get_last_selected_dialog_id(), 0)


class DialogStateTests(unittest.TestCase):
    """The state machine, as ``dialog.cpp`` drives it."""

    def setUp(self) -> None:
        dialog._reset()
        # The send path is the source's handler case, whose outer guard refuses the
        # message while the map is not ready (`dialog.cpp:600-603`); these classes have no
        # client, so the map state is stubbed as the body tests stub it.
        self._map = mock.patch.object(dialog, "_map_state", return_value=(7, True))
        self._map.start()
        self.addCleanup(self._map.stop)
        # The capture refuses every message while callbacks are suspended, so the gate is open
        # in these tests exactly as it is when a client's message reaches the module.
        dialog._observe_map_change(*dialog._map_state())
        dialog._callbacks_suspended = False

    def tearDown(self) -> None:
        dialog._reset()

    def test_a_body_records_the_agent_and_opens_the_dialog(self) -> None:
        """``DialogBodyInfo`` is ``{type, agent_id, message_enc}``: agent is word 1."""

        dialog._dispatch_message(message(DIALOG_BODY, arg0=1, arg1=241))

        active = dialog.get_active_dialog()
        assert active is not None
        self.assertEqual(active.agent_id, 241)
        self.assertEqual(active.dialog_id, 0)
        self.assertFalse(active.dialog_id_authoritative)

    def test_a_button_is_read_from_the_packet_it_arrives_in(self) -> None:
        """The client's ``DialogButtonInfo`` is ``{button_icon, message, dialog_id, skill_id}``.

        Sixteen bytes and four words, so the whole packet fits in the event — which is
        why a button's dialog id is exact without any decoding.
        """

        client = _FakeClient()
        with mock.patch("py4gw.client.require_client", return_value=client):
            dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
            dialog._dispatch_message(
                message(DIALOG_BUTTON, arg0=7, arg1=0x0A1F3828, arg2=0x0A00002A, arg3=42)
            )

        buttons = dialog.get_active_dialog_buttons()
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0].dialog_id, 0x0A00002A)
        self.assertEqual(buttons[0].button_icon, 7)

    def test_a_new_body_clears_the_buttons(self) -> None:
        """``dialog.cpp:822``. Without this, every dialog ever opened would accumulate."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg2=1))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg2=2))
        self.assertEqual(len(dialog.get_active_dialog_buttons()), 2)

        dialog._dispatch_message(message(DIALOG_BODY, arg1=242))

        self.assertEqual(dialog.get_active_dialog_buttons(), [])

    def test_buttons_keep_the_order_the_client_announced_them(self) -> None:
        """Button *n* is the one a caller asks for by position, so order is the contract."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        for dialog_id in (11, 22, 33):
            dialog._dispatch_message(message(DIALOG_BUTTON, arg2=dialog_id))

        self.assertEqual(
            [button.dialog_id for button in dialog.get_active_dialog_buttons()],
            [11, 22, 33],
        )

    def test_the_button_list_is_capped_and_drops_the_oldest(self) -> None:
        """``dialog.cpp:734-739``: ``kMaxActiveDialogButtons`` is 64, oldest out first.

        The source caps the list after the push and erases from the front, so the most
        recent buttons are the ones that survive. Without the cap a client that keeps
        announcing buttons would grow this list for as long as the controller lives.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        for dialog_id in range(1, 80):
            dialog._dispatch_message(message(DIALOG_BUTTON, arg2=dialog_id))

        buttons = dialog.get_active_dialog_buttons()
        self.assertEqual(len(buttons), dialog.MAX_ACTIVE_DIALOG_BUTTONS)
        self.assertEqual(
            [button.dialog_id for button in buttons],
            list(range(80 - dialog.MAX_ACTIVE_DIALOG_BUTTONS, 80)),
        )

    def test_a_sent_dialog_is_tied_to_the_body_that_answers_it(self) -> None:
        """``dialog.cpp:968-969`` then ``806-813``: the id is kept, then consumed."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._note_sent_dialog(0x0A00002A, DIALOG_SEND)

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        active = dialog.get_active_dialog()
        assert active is not None
        self.assertEqual(active.context_dialog_id, 0x0A00002A)

    def test_a_sent_dialog_is_dropped_when_a_different_agent_answers(self) -> None:
        """``dialog.cpp:806-810``: the pending id is used only for the same agent.

        The runtime clears the pending pair either way, so a body from another agent
        cannot pick up a dialog meant for the first one — and the body after that
        cannot either.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._note_sent_dialog(0x0A00002A, DIALOG_SEND)

        dialog._dispatch_message(message(DIALOG_BODY, arg1=999))

        active = dialog.get_active_dialog()
        assert active is not None
        self.assertEqual(active.agent_id, 999)
        self.assertEqual(active.context_dialog_id, 0)

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        again = dialog.get_active_dialog()
        assert again is not None
        self.assertEqual(
            again.context_dialog_id,
            0,
            "the pending id was cleared by the body that did not match it",
        )

    def test_a_send_takes_effect_before_any_body_arrives(self) -> None:
        """``dialog.cpp:967-972``: six assignments, and they are not all bookkeeping.

        The source's send branch does more than remember the pending id. Inside the same
        lock it also makes the sent id the context id, returns the dialog id to zero and
        clears the authoritative flag — before any body has answered.
        ``is_dialog_displayed`` reads exactly those two ids, so a dialog this project
        just sent counts as displayed immediately, and a body that arrives for a
        different agent takes that back. The agent recorded as pending is the one of the
        dialog that was **open** when the send happened (``dialog.cpp:955``), not the one
        being sent to.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        dialog._note_sent_dialog(0x0A00002A, DIALOG_SEND)

        active = dialog.get_active_dialog()
        assert active is not None
        self.assertEqual(active.dialog_id, 0)
        self.assertEqual(active.context_dialog_id, 0x0A00002A)
        self.assertFalse(active.dialog_id_authoritative)
        self.assertTrue(dialog.PyDialog.is_dialog_displayed(0x0A00002A))
        self.assertEqual(dialog._pending_context_dialog_id, 0x0A00002A)
        self.assertEqual(dialog._pending_context_agent_id, 241)

        dialog._dispatch_message(message(DIALOG_BODY, arg1=999))

        after = dialog.get_active_dialog()
        assert after is not None
        self.assertEqual(after.context_dialog_id, 0)
        self.assertFalse(dialog.PyDialog.is_dialog_displayed(0x0A00002A))

    def test_reset_empties_the_state(self) -> None:
        """A connection calls this at install so a previous one cannot be read as this one."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg2=7))

        dialog._reset()

        self.assertIsNone(dialog.get_active_dialog())
        self.assertEqual(dialog.get_active_dialog_buttons(), [])


class DialogTableTests(unittest.TestCase):
    """``DialogTables``: the port of ``dialog_patterns.cpp``.

    Native resolves the dialog metadata tables in two stages — the five hardcoded
    ``DialogMemory`` addresses rebased onto the live module and validated, then a
    heuristic ``.rdata`` scan that derives four of the five bases from the third — and
    the same two stages are exercised here against a synthetic client, because the
    rules are arithmetic and bounds rather than anything a live client has to agree to.
    """

    def _resolver(self, bases: dict[str, int] | None, mode: str) -> dialog.DialogTables:
        memory, scanner, patterns = _client_memory(bases, mode=mode)
        return dialog.DialogTables(
            cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
        )

    def test_the_static_rebase_is_used_when_it_validates(self) -> None:
        """``BuildStaticDialogTables`` (``dialog_patterns.cpp:175-197``)."""

        tables = self._resolver(STATIC_BASES, "valid").get()

        self.assertTrue(tables.resolved)
        self.assertEqual(tables.flags_base, STATIC_BASES["flags_base"])
        self.assertEqual(tables.frame_type_base, STATIC_BASES["frame_type_base"])
        self.assertEqual(tables.event_handler_base, STATIC_BASES["event_handler_base"])
        self.assertEqual(tables.content_id_base, STATIC_BASES["content_id_base"])
        self.assertEqual(tables.property_id_base, STATIC_BASES["property_id_base"])

    def test_the_fallback_scan_finds_the_flags_column(self) -> None:
        """``BuildResolvedDialogTables`` (``dialog_patterns.cpp:199-225``).

        With every static base failing, the scan finds the one column that looks like a
        flags table, and the other four are derived from it: handler ``-8``, frame type
        ``-4``, content id ``+4``, property id ``+8``.
        """

        tables = self._resolver(None, "valid").get()

        self.assertEqual(tables.flags_base, FLAGS_AT)
        self.assertEqual(tables.event_handler_base, FLAGS_AT - 0x8)
        self.assertEqual(tables.frame_type_base, FLAGS_AT - 0x4)
        self.assertEqual(tables.content_id_base, FLAGS_AT + 0x4)
        self.assertEqual(tables.property_id_base, FLAGS_AT + 0x8)

    def test_a_table_that_fails_validation_resolves_to_nothing(self) -> None:
        """Both stages failing leaves every base zero, and that is the answer."""

        tables = self._resolver(None, "empty").get()

        self.assertEqual(tables.flags_base, 0)
        self.assertEqual(tables.frame_type_base, 0)
        self.assertEqual(tables.event_handler_base, 0)
        self.assertEqual(tables.content_id_base, 0)
        self.assertEqual(tables.property_id_base, 0)
        self.assertTrue(
            tables.resolved,
            "native marks the tables resolved even when resolution found nothing, so "
            "a failure is not retried on every read",
        )

    def test_a_static_rebase_that_fails_validation_falls_through_to_the_scan(self) -> None:
        """The stages are ordered: a static address that does not validate is not used.

        The static bases here are shifted by two rows, so their flags column runs off
        the end of the table into the filler and the validation pass refuses them. What
        is left is the scan, which finds the column the table is actually at.
        """

        shifted = {
            name: value + 0x48 for name, value in STATIC_BASES.items()
        }
        tables = self._resolver(shifted, "valid").get()

        self.assertEqual(tables.flags_base, FLAGS_AT)
        self.assertNotEqual(
            tables.flags_base,
            shifted["flags_base"],
            "the static address failed validation and must not be the one in use",
        )

    def test_invalidate_forces_another_resolution(self) -> None:
        """``InvalidateDialogTables`` (``dialog_patterns.cpp:257-259``)."""

        resolver = self._resolver(STATIC_BASES, "valid")
        resolver.get()

        resolver.invalidate()
        again = resolver.get()

        self.assertEqual(again.flags_base, STATIC_BASES["flags_base"])

    def test_the_loader_address_survives_invalidation(self) -> None:
        """Native caches it in a function-static that ``InvalidateDialogTables`` leaves."""

        memory, scanner, patterns = _client_memory(STATIC_BASES, mode="valid")
        patterns.loader = TEXT_START
        offset = TEXT_START - memory.start
        memory.data[offset : offset + 3] = b"\x55\x8b\xec"
        resolver = dialog.DialogTables(
            cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
        )

        self.assertEqual(resolver.resolve_loader_get_text(), TEXT_START)

        resolver.invalidate()

        self.assertEqual(resolver.resolve_loader_get_text(), TEXT_START)

    def test_a_loader_that_does_not_begin_a_function_is_refused(self) -> None:
        """**This is the check that the crash of 2026-09-25 added.**

        On build 38888 the rebased constant ``0x0079EEF0`` lands in the middle of another
        function, and calling it faulted the client. A candidate whose bytes do not begin a
        function is answered as "no loader", which the queue already handles by caching empty
        text.
        """

        memory, scanner, patterns = _client_memory(STATIC_BASES, mode="valid")
        patterns.loader = TEXT_START
        # Text that is not a function entry: the address holds whatever the client's code has
        # there, and this port may not assume it is a prologue.
        memory.data[TEXT_START - memory.start : TEXT_START - memory.start + 4] = (
            b"\xc4\x10\x83\xf8"
        )
        resolver = dialog.DialogTables(
            cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
        )

        self.assertEqual(resolver.resolve_loader_get_text(), 0)

    def test_a_loader_that_begins_a_function_is_accepted(self) -> None:
        """``push ebp`` / ``mov ebp, esp`` — what this client's function entries look like."""

        for prefix in (
            b"\x55\x8b\xec\x83\xec\x0c",
            b"\x8b\xff\x55\x8b\xec\x83\xec\x0c",
        ):
            with self.subTest(prefix=prefix.hex(" ")):
                memory, scanner, patterns = _client_memory(STATIC_BASES, mode="valid")
                patterns.loader = TEXT_START
                offset = TEXT_START - memory.start
                memory.data[offset : offset + len(prefix)] = prefix
                resolver = dialog.DialogTables(
                    cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
                )

                self.assertEqual(resolver.resolve_loader_get_text(), TEXT_START)

    def test_a_loader_that_is_a_thunk_to_a_function_is_accepted(self) -> None:
        """Most of this client's dialog handlers are ``jmp rel32`` thunks, and those are callable.

        ``0x0070B8D0`` is ``E9 6B 00 00 00`` — a jump to ``0x0070B940`` — so an entry check that
        only accepted a prologue would refuse a real function pointer.
        """

        memory, scanner, patterns = _client_memory(STATIC_BASES, mode="valid")
        target = TEXT_START + 0x40
        thunk = TEXT_START + 0x10
        patterns.loader = thunk
        target_offset = target - memory.start
        memory.data[target_offset : target_offset + 3] = b"\x55\x8b\xec"
        thunk_offset = thunk - memory.start
        displacement = target - (thunk + 5)
        memory.data[thunk_offset : thunk_offset + 5] = b"\xe9" + displacement.to_bytes(
            4, "little", signed=True
        )
        resolver = dialog.DialogTables(
            cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
        )

        self.assertEqual(resolver.resolve_loader_get_text(), thunk)

    def test_a_thunk_that_leaves_the_code_section_is_refused(self) -> None:
        """A jump out of ``.text`` is not a function this project may call."""

        memory, scanner, patterns = _client_memory(STATIC_BASES, mode="valid")
        thunk = TEXT_START + 0x10
        patterns.loader = thunk
        thunk_offset = thunk - memory.start
        outside = RDATA_START + 0x100
        displacement = outside - (thunk + 5)
        memory.data[thunk_offset : thunk_offset + 5] = b"\xe9" + displacement.to_bytes(
            4, "little", signed=True
        )
        resolver = dialog.DialogTables(
            cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
        )

        self.assertEqual(resolver.resolve_loader_get_text(), 0)

    def test_a_thunk_to_something_that_is_not_a_function_is_refused(self) -> None:
        memory, scanner, patterns = _client_memory(STATIC_BASES, mode="valid")
        target = TEXT_START + 0x40
        thunk = TEXT_START + 0x10
        patterns.loader = thunk
        target_offset = target - memory.start
        memory.data[target_offset : target_offset + 4] = b"\xc4\x10\x83\xf8"
        thunk_offset = thunk - memory.start
        displacement = target - (thunk + 5)
        memory.data[thunk_offset : thunk_offset + 5] = b"\xe9" + displacement.to_bytes(
            4, "little", signed=True
        )
        resolver = dialog.DialogTables(
            cast(Any, memory), cast(Any, scanner), cast(Any, patterns)
        )

        self.assertEqual(resolver.resolve_loader_get_text(), 0)

    def test_a_word_that_cannot_be_read_is_none(self) -> None:
        """``TryReadU32`` reports failure by its result, not by raising."""

        resolver = self._resolver(STATIC_BASES, "valid")

        self.assertIsNotNone(resolver.read_uint32(RDATA_START))
        self.assertIsNone(resolver.read_uint32(0x7FFFFFFF))


class DialogGetterTests(unittest.TestCase):
    """``get_active_dialog`` and ``get_active_dialog_buttons``, as the source defines them."""

    def setUp(self) -> None:
        dialog._reset()
        # The capture refuses every message while callbacks are suspended, so the gate is open
        # in these tests exactly as it is when a client's message reaches the module.
        dialog._callbacks_suspended = False

    def tearDown(self) -> None:
        dialog._reset()

    def test_no_dialog_at_all_is_none(self) -> None:
        self.assertIsNone(dialog.get_active_dialog())
        self.assertEqual(dialog.get_active_dialog_buttons(), [])

    def test_an_agent_alone_is_a_dialog(self) -> None:
        """``Dialog.py:156-161`` reports nothing only when all three ids are zero.

        The body arrives before the buttons do, so a dialog with an agent and no id
        yet is a real dialog and must not be reported as absent.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        self.assertIsNotNone(dialog.get_active_dialog())

    def test_buttons_with_no_ids_are_not_offered(self) -> None:
        """``Player.SendAutomaticDialog`` drops them, and so does the fallback path."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg2=0))

        buttons = dialog.get_active_dialog_buttons()
        self.assertEqual(len(buttons), 1)
        self.assertEqual(
            [button for button in buttons if button.dialog_id != 0],
            [],
            "a button with no dialog id is announced but cannot be sent",
        )

    def test_the_text_fields_say_they_are_waiting_for_a_decode(self) -> None:
        """A button with no label and nothing decoded for its id answers as the source does.

        With no client there is no map, so ``IsDialogTextDecodePending`` is false and the catalog
        text for the button's dialog id is empty — which is what native reports in that state,
        not an empty string dressed up as a decode in flight.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg2=7))

        active = dialog.get_active_dialog()
        assert active is not None
        self.assertEqual(active.raw_message, "")
        self.assertEqual(active.message, "")

        button = dialog.get_active_dialog_buttons()[0]
        self.assertEqual(button.message, "")
        self.assertEqual(button.message_decoded, "")
        self.assertFalse(button.message_decode_pending)

    def test_the_fallback_reads_nothing_while_the_body_text_is_empty(self) -> None:
        """``Dialog.py:168-173`` needs the body text, which needs the decode.

        The branch is ported and behaves exactly as the source does for empty text;
        what it cannot do yet is find choices in text this project cannot decode.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=241))

        self.assertEqual(dialog.get_active_dialog_buttons(), [])

    def test_both_data_classes_keep_the_attribute_the_binding_would_have_filled(self) -> None:
        """``native`` exists and is ``None``: no PyDialog object can be built here."""

        active = dialog.ActiveDialogInfo(dialog_id=1)
        button = dialog.DialogButtonInfo(dialog_id=1)

        self.assertIsNone(active.native)
        self.assertIsNone(button.native)


class DialogTextTests(unittest.TestCase):
    """The pure half: ``Dialog.py``'s sanitiser and its inline-choice parser."""

    def test_sanitize_strips_colour_and_generic_tags(self) -> None:
        self.assertEqual(
            dialog.sanitize_dialog_text("<c=#FF0000>Hello</c> <b>there</b>"),
            "Hello there",
        )

    def test_sanitize_turns_bracket_tokens_into_brackets(self) -> None:
        self.assertEqual(
            dialog.sanitize_dialog_text("[lbracket]Quest[rbracket]"), "[Quest]"
        )

    def test_sanitize_normalises_line_endings_and_blank_lines(self) -> None:
        self.assertEqual(
            dialog.sanitize_dialog_text("a\r\n\r\n\r\n\r\nb"), "a\n\nb"
        )

    def test_sanitize_removes_control_characters(self) -> None:
        self.assertEqual(dialog.sanitize_dialog_text("a\x01\x02b"), "ab")

    def test_sanitize_of_nothing_is_empty(self) -> None:
        self.assertEqual(dialog.sanitize_dialog_text(None), "")
        self.assertEqual(dialog.sanitize_dialog_text(""), "")

    def test_inline_choices_are_parsed_from_a_body(self) -> None:
        """``Dialog.py:125-149``: the client writes some choices into the text."""

        choices = dialog.extract_inline_dialog_choices_from_text(
            "What do you want? <a=0x0A00002A>Learn a skill</a> "
            "or <a=0x2A>Leave</a>"
        )

        self.assertEqual(
            [(choice.dialog_id, choice.message) for choice in choices],
            [(0x0A00002A, "Learn a skill"), (0x2A, "Leave")],
        )
        self.assertFalse(choices[0].message_decode_pending)

    def test_inline_choices_ignore_a_body_without_any(self) -> None:
        self.assertEqual(
            dialog.extract_inline_dialog_choices_from_text("Nothing to choose here"),
            [],
        )

    def test_inline_choices_dedupe_the_same_id_and_label(self) -> None:
        choices = dialog.extract_inline_dialog_choices_from_text(
            "<a=7>Yes</a><a=7>Yes</a>"
        )

        self.assertEqual(len(choices), 1)


#: The pointer the fake loader hands back, and the address the fake tables resolve.
ENCODED_POINTER = 0x03000100
LOADER_ADDRESS = 0x0079EEF0


class _FakeDialogTables:
    """The four things the decode queue and the column readers ask the tables for."""

    def __init__(self, loader: int = LOADER_ADDRESS) -> None:
        self.loader = loader
        self.words: dict[int, int] = {}
        self.invalidated = 0

    def get(self) -> Any:
        """The rebased bases. All zero here, so every column reads zero, as with no tables."""

        return dialog.DialogTableAddrs()

    def resolve_loader_get_text(self) -> int:
        return self.loader

    def read_uint32(self, address: int) -> int | None:
        return self.words.get(address)

    def invalidate(self) -> None:
        self.invalidated += 1


class _FakeBridge:
    """The decode transport, as the client's own side of it behaves.

    The real bridge places an encoded string in a decode slot and waits for the client to call
    the emitted stub. Here the fake client's decoder answers when it is asked, which is what the
    client and the stub do between them; the completion is then delivered the way the listener
    delivers it (``EventRecord(STRING_DECODED, sequence=slot)``), so the module's own handler
    and every check in it are the real code.
    """

    #: Where the emitted decoder stub would be. Nothing calls it here: the fake client answers
    #: directly, which is what the stub exists to carry back.
    DECODER_ADDRESS = 0x00DEC0DE

    def __init__(self) -> None:
        self.answers: dict[int, str] = {}
        self.encoded: dict[int, bytes] = {}
        self.taken: list[int] = []

    @property
    def decoder_address(self) -> int:
        return self.DECODER_ADDRESS

    def begin_decode(self, encoded: bytes) -> int:
        slot = 0
        while slot in self.answers:
            slot += 1
        self.encoded[slot] = encoded
        return slot

    def decode_input_address(self, slot: int) -> int:
        return 0x03000000 + slot * 0x1000

    def decode_slot_address(self, slot: int) -> int:
        return 0x04000000 + slot * 0x1000

    def slot_for_address(self, address: int) -> int | None:
        for slot in list(self.answers) + list(self.encoded):
            if self.decode_slot_address(slot) == address:
                return slot
        return None

    def complete_decode(self, slot: int, text: str) -> None:
        """The decoder's own refusals answer through here, without a call."""

        self.answers[slot] = text

    def release_decode(self, slot: int) -> None:
        self.answers.pop(slot, None)
        self.encoded.pop(slot, None)

    def take_decoded_string(self, slot: int) -> tuple[str, bool]:
        self.taken.append(slot)
        self.encoded.pop(slot, None)
        return self.answers.pop(slot, ""), False

    def decodes_in_flight(self) -> int:
        return len(self.answers)

    def pending_slots(self) -> list[int]:
        """Return the slots whose decode has not been taken yet."""

        return sorted(self.answers)


class _FakeClient:
    """A client whose loader call and decoder the test answers.

    ``call_address`` is the one thing the catalog's queue asks a connection to do, and
    ``call_function`` is where the client's decoder is asked: it answers with ``decoded``, which
    is what the client and the emitted stub produce between them.
    """

    def __init__(self, pointer: int = ENCODED_POINTER, loader: int = LOADER_ADDRESS) -> None:
        self.dialog_tables = _FakeDialogTables(loader)
        self.value = pointer
        self.calls: list[tuple[int, Any, tuple[int, ...]]] = []
        self.bridge = _FakeBridge()
        #: What the client's decoder answers the next string with. Native's callback is handed
        #: the text the client produced; this is that text.
        self.decoded = "Foreman"

    def resolves(self, name: str) -> bool:
        return True

    def call_address(
        self, target: int, form: Any, *words: int
    ) -> Any:
        self.calls.append((target, form, tuple(words)))
        return _FakeCommand(self.value)

    def call_function(self, name: str, form: Any, *words: int) -> Any:
        """The client's decoder, as ``validate_async_decode_str_func`` runs it.

        Its last argument is the slot the host named, and what the client does with the string
        is what the emitted stub records: the text goes into that slot.
        """

        slot = self.bridge.slot_for_address(int(words[-1]))
        if slot is not None:
            self.bridge.answers[slot] = self.decoded
        return _FakeCommand(0)

    def read_agent_by_id(self, agent_id: int) -> Any:
        """No agent stands behind a fake client, so the row's model id is ``0``."""

        return None


class _FakeCommand:
    """What a call returns here: the callee's value word."""

    def __init__(self, value: int) -> None:
        self.value = value


def serve_encoded_text(
    tables: _FakeDialogTables, codepoints: list[int], address: int = ENCODED_POINTER
) -> None:
    """Place a wide string where the fake reader can find it, terminator included."""

    for index, codepoint in enumerate(codepoints + [0]):
        tables.words[address + index * 2] = codepoint


def deliver_decodes(client: _FakeClient) -> None:
    """Hand the module the completions its decodes produced, as the listener does.

    The client's decoder answers when it is asked, and the real listener delivers that as a
    ``STRING_DECODED`` event; this is the same call, made by the test instead of by a thread,
    so what runs is the module's own completion and every check inside it.
    """

    from py4gw.game_thread.shared_block import EventKind, EventRecord

    for slot in client.bridge.pending_slots():
        dialog._on_string_decoded(
            EventRecord(kind=EventKind.STRING_DECODED, sequence=slot)
        )


class DialogDecodeQueueTests(unittest.TestCase):
    """The catalog's decode queue (``dialog.cpp:1136-1254``) and the members around it.

    The client is faked at exactly two points — the loader call and the codepoint read — so the
    render, the table lookup and the queue's own state machine are the real ones: the string
    table holds a synthetic entry, and what the members return is what the port decoded.
    """

    #: A one-word string-table entry: ``[u16 size | u16 base_char | u8 bits | u8 flags | text]``.
    def entry(self, text: str) -> bytes:
        payload = text.encode("ascii")
        return struct.pack("<HHBB", 6 + len(payload), 0x20, 8, 0) + payload

    def setUp(self) -> None:
        dialog._reset()
        dialog._decoded_text_cache.clear()
        dialog._decoded_text_pending.clear()
        dialog._catalog_decode_epoch = 0
        dialog._catalog_pending_async_decode_count = 0
        dialog._catalog_shutdown_requested = False

        self.client = _FakeClient()
        self.tables = self.client.dialog_tables

        self.table_before = string_table._string_table
        self.loaded_before = string_table._string_table_loaded
        string_table._string_table = {5: self.entry("Foreman")}
        string_table._string_table_loaded = True

        self.addCleanup(self._restore_table)
        self._patch = mock.patch(
            "py4gw.client.require_client", return_value=self.client
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self._gate = mock.patch.object(
            dialog, "_is_dialog_map_ready", return_value=True
        )
        self._gate.start()
        self.addCleanup(self._gate.stop)
        # Native refuses to decode without a text parser (``ui_methods.cpp:2595``); a live
        # client has one, and the fake stands in for that client's whole context tree.
        self._parser = mock.patch(
            "py4gw.ui.async_decode._has_text_parser", return_value=True
        )
        self._parser.start()
        self.addCleanup(self._parser.stop)

    def _restore_table(self) -> None:
        string_table._string_table = self.table_before
        string_table._string_table_loaded = self.loaded_before
        dialog._decoded_text_cache.clear()
        dialog._decoded_text_pending.clear()

    def encoded(self, value: int) -> list[int]:
        """One base-0x7F00 run for a table index, terminator included by the caller."""

        run = uint32_to_enc_str(value, 8)
        assert run is not None, "the test's own encoding must fit"
        return run

    # -- the queue ---------------------------------------------------------

    def test_the_first_call_queues_the_decode_and_answers_nothing(self) -> None:
        serve_encoded_text(self.tables, self.encoded(5))

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(len(self.client.calls), 1)
        target, form, words = self.client.calls[0]
        self.assertEqual(target, LOADER_ADDRESS)
        self.assertEqual(form, CallFormat.U32)
        self.assertEqual(words, (9,))

    def test_the_second_call_answers_from_the_cache(self) -> None:
        """The first call queues the decode; the text is there once the client has answered."""

        serve_encoded_text(self.tables, self.encoded(5))

        dialog.PyDialog.get_dialog_text_decoded(9)
        deliver_decodes(self.client)
        text = dialog.PyDialog.get_dialog_text_decoded(9)

        self.assertEqual(text, "Foreman")
        self.assertEqual(len(self.client.calls), 1, "a cached dialog is not queued again")
        self.assertFalse(dialog.PyDialog.is_dialog_text_decode_pending(9))

    def test_the_queue_requests_nothing_for_an_id_past_the_maximum(self) -> None:
        self.assertEqual(
            dialog.PyDialog.get_dialog_text_decoded(dialog.MAX_DIALOG_ID + 1), ""
        )
        self.assertEqual(self.client.calls, [])

    def test_a_dialog_already_pending_is_not_queued_again(self) -> None:
        dialog._decoded_text_pending[9] = True

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(self.client.calls, [])

    def test_a_missing_loader_caches_empty_text(self) -> None:
        """``dialog.cpp:1166-1177``: no loader is an answer of "", not a refusal."""

        self.client.dialog_tables.loader = 0

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(dialog._decoded_text_cache.get(9), "")
        self.assertNotIn(9, dialog._decoded_text_pending)
        self.assertEqual(self.client.calls, [])

    def test_a_null_pointer_caches_empty_text(self) -> None:
        """``dialog.cpp:1179-1190``."""

        self.client.value = 0

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(dialog._decoded_text_cache.get(9), "")
        self.assertNotIn(9, dialog._decoded_text_pending)

    def test_a_string_that_cannot_be_read_caches_empty_text(self) -> None:
        """``dialog.cpp:1192-1203``: the copy failed, so nothing was decoded."""

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(dialog._decoded_text_cache.get(9), "")
        self.assertNotIn(9, dialog._decoded_text_pending)

    def test_a_string_without_a_terminator_is_not_read_as_text(self) -> None:
        """A pointer that is not a string is the failed copy, not a long string."""

        for index in range(dialog.MAX_DIALOG_TEXT_CODE_UNITS + 1):
            self.tables.words[ENCODED_POINTER + index * 2] = 0x41

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(dialog._decoded_text_cache.get(9), "")

    def test_a_string_that_is_not_an_encoded_reference_is_cached_as_it_stands(self) -> None:
        """``dialog.cpp:1205-1216``: the raw string, not a decode of it."""

        serve_encoded_text(self.tables, [0x41, 0x42])

        dialog.PyDialog.get_dialog_text_decoded(9)
        text = dialog.PyDialog.get_dialog_text_decoded(9)

        self.assertEqual(text, "AB")
        self.assertFalse(dialog.PyDialog.is_dialog_text_decode_pending(9))

    def test_the_queue_reads_the_codepoints_at_the_pointer_it_was_given(self) -> None:
        serve_encoded_text(self.tables, self.encoded(5), address=0x04000200)
        self.client.value = 0x04000200

        dialog.PyDialog.get_dialog_text_decoded(9)
        deliver_decodes(self.client)

        self.assertEqual(
            dialog.PyDialog.get_dialog_text_decoded(9), "Foreman"
        )

    # -- the epoch and the shutdown flag -----------------------------------

    def test_a_clear_during_the_decode_discards_the_result(self) -> None:
        """An epoch that moved means the cache was emptied for this decode, not by it."""

        serve_encoded_text(self.tables, self.encoded(5))
        original = self.client.call_address

        def clearing_call(target: int, form: Any, *words: int) -> Any:
            record = original(target, form, *words)
            dialog._clear_catalog_cache()
            return record

        self.client.call_address = clearing_call  # type: ignore[method-assign]

        with mock.patch("py4gw.client.current_client", return_value=self.client):
            self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        deliver_decodes(self.client)

        self.assertEqual(dialog._decoded_text_cache, {})
        self.assertEqual(dialog._decoded_text_pending, {})
        self.assertGreaterEqual(self.tables.invalidated, 1, "the tables go with it")

    def test_a_shutdown_before_the_read_stops_the_queue(self) -> None:
        """``dialog.cpp:1147-1149``."""

        serve_encoded_text(self.tables, self.encoded(5))
        dialog._catalog_shutdown_requested = True

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(self.client.calls, [])

    def test_a_shutdown_after_the_read_discards_the_result(self) -> None:
        """``dialog.cpp:1233-1240``: the second check, after the string is in hand."""

        serve_encoded_text(self.tables, self.encoded(5))
        original = self.tables.read_uint32

        def shutting_down_read(address: int) -> int | None:
            dialog._catalog_shutdown_requested = True
            return original(address)

        self.tables.read_uint32 = shutting_down_read  # type: ignore[method-assign]

        self.assertEqual(dialog.PyDialog.get_dialog_text_decoded(9), "")

        self.assertEqual(dialog._decoded_text_cache, {})

    # -- the members around it ---------------------------------------------

    def test_the_status_lists_cached_rows_and_pending_ones(self) -> None:
        serve_encoded_text(self.tables, self.encoded(5))
        dialog.PyDialog.get_dialog_text_decoded(9)
        deliver_decodes(self.client)
        dialog.PyDialog.get_dialog_text_decoded(9)
        dialog._decoded_text_pending[11] = True

        status = dialog.PyDialog.get_dialog_text_decode_status()

        self.assertEqual(
            [(row.dialog_id, row.text, row.pending) for row in status],
            [(9, "Foreman", False), (11, "", True)],
        )

    def test_a_pending_id_that_is_also_cached_is_reported_once(self) -> None:
        dialog._decoded_text_cache[9] = "Foreman"
        dialog._decoded_text_pending[9] = True

        status = dialog.PyDialog.get_dialog_text_decode_status()

        self.assertEqual([(row.dialog_id, row.pending) for row in status], [(9, False)])

    def test_a_cached_empty_string_is_a_cache_hit(self) -> None:
        """Which is what the pair ``TryGetCachedDialogTextDecoded`` returns exists for."""

        dialog._decoded_text_cache[9] = ""

        self.assertEqual(dialog._try_get_cached_dialog_text_decoded(9), (True, ""))
        self.assertEqual(dialog._try_get_cached_dialog_text_decoded(10), (False, ""))

    def test_get_dialog_info_carries_the_cached_text(self) -> None:
        dialog._decoded_text_cache[9] = "Foreman"

        info = dialog.PyDialog.get_dialog_info(9)

        self.assertEqual(info.dialog_id, 9)
        self.assertEqual(info.content, "Foreman")
        self.assertEqual(info.flags, 0, "no tables here, so the columns read zero")

    def test_enumerate_available_dialogs_returns_the_available_rows(self) -> None:
        dialog._decoded_text_cache[2] = "Foreman"

        with mock.patch.object(
            dialog.PyDialog, "read_dialog_flags", side_effect=lambda dialog_id: 1 if dialog_id == 2 else 0
        ):
            rows = dialog.PyDialog.enumerate_available_dialogs()

        self.assertEqual([(row.dialog_id, row.content) for row in rows], [(2, "Foreman")])

    def test_clear_cache_empties_the_catalog_cache_and_bumps_the_epoch(self) -> None:
        dialog._decoded_text_cache[9] = "Foreman"
        dialog._decoded_text_pending[10] = True
        epoch = dialog._catalog_decode_epoch

        dialog.PyDialog.clear_cache()

        self.assertEqual(dialog._decoded_text_cache, {})
        self.assertEqual(dialog._decoded_text_pending, {})
        self.assertEqual(dialog._catalog_decode_epoch, epoch + 1)


class DialogBodyTextTests(unittest.TestCase):
    """The body's text, which is the only text a dialog message carries.

    Both halves of ``dialog.cpp``'s body handling are here: the message that replaces the state
    and records how the text will be obtained (``774-927``), and the completion that writes the
    text into the open dialog and appends the row (``995-1054``). The text itself comes from the
    client's decoder, through the protocol the source uses — the copy is placed in a decode slot,
    the client is called, and the completion arrives as a ``STRING_DECODED`` event — and the fake
    client stands in for the client's side of that: it answers with ``decoded``, which is what
    the client and the emitted stub produce between them.

    The message's own read is faked at the codepoint array, and the gate is open, because a body
    only reaches the module with it open.
    """

    def setUp(self) -> None:
        dialog._reset()
        dialog._clear_event_logs()
        dialog._clear_callback_journal()

        self.client = _FakeClient()
        self.tables = self.client.dialog_tables

        self._client = mock.patch(
            "py4gw.client.require_client", return_value=self.client
        )
        self._client.start()
        self.addCleanup(self._client.stop)
        self._map = mock.patch.object(dialog, "_map_state", return_value=(7, True))
        self._map.start()
        self.addCleanup(self._map.stop)
        # Native refuses to decode without a text parser (``ui_methods.cpp:2595``); a live
        # client has one, and the fake stands in for that client's whole context tree.
        self._parser = mock.patch(
            "py4gw.ui.async_decode._has_text_parser", return_value=True
        )
        self._parser.start()
        self.addCleanup(self._parser.stop)

        # What the capture does before it dispatches: it observes the map snapshot the message
        # carried, which is the state the completion's own observation finds unchanged. The gate
        # is open, because a body only reaches the module with it open.
        dialog._observe_map_change(*dialog._map_state())
        dialog._callbacks_suspended = False

    def _restore(self) -> None:
        dialog._reset()
        dialog._clear_event_logs()
        dialog._clear_callback_journal()

    def encoded(self, value: int) -> list[int]:
        """One base-0x7F00 run for a table index, terminator added by ``serve_encoded_text``."""

        run = uint32_to_enc_str(value, 8)
        assert run is not None, "the test's own encoding must fit"
        return run

    def body(self, pointer: int = ENCODED_POINTER, agent_id: int = 17) -> None:
        """Send one body through the dispatch the client's own message goes through.

        The string the client has at ``pointer`` is what ``serve_encoded_text`` put there, and
        it travels with the event as the observer's copy of it — the observer reads it inside
        the client's own call, which is where the source reads it too (``dialog.cpp:832``).
        """

        dialog._dispatch_message(
            message(
                DIALOG_BODY,
                arg1=agent_id,
                arg2=pointer,
                text=self.client_copy(pointer),
            )
        )

    def client_copy(self, pointer: int) -> list[int] | None:
        """The string the fake client holds at ``pointer``, as the observer copies it.

        ``None`` is a pointer with no readable string behind it, which is the source's failed
        copy: ``DupWideStringSafe`` answers null for a null pointer and for a read that faulted
        (``dialog.cpp:237-252``), and here it is what the fake memory cannot answer.
        """

        if not pointer:
            return None
        units: list[int] = []
        for index in range(dialog.MAX_DIALOG_TEXT_CODE_UNITS):
            unit = self.tables.words.get(pointer + index * 2)
            if unit is None:
                return units or None
            units.append(int(unit))
            if unit == 0:
                return units
        return None

    def answer(self, text: str = "Foreman") -> None:
        """Let the client answer the decodes it was asked for, and deliver the completions."""

        self.client.decoded = text
        deliver_decodes(self.client)

    @staticmethod
    def rows() -> list[Any]:
        return dialog.PyDialog.get_dialog_callback_journal()

    # -- the three outcomes -------------------------------------------------

    def test_an_encoded_body_is_decoded_by_the_client_and_its_row_carries_the_text(self) -> None:
        """``dialog.cpp:856-901``, ``1037-1051``: the row comes from the decode's callback."""

        serve_encoded_text(self.tables, self.encoded(5))

        self.body()
        self.assertEqual(
            self.rows(), [], "the row waits for the client, as native's does"
        )

        self.answer()

        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].event_type, "recv_body")
        self.assertEqual(rows[0].text, "Foreman")
        self.assertEqual(rows[0].agent_id, 17)

    def test_the_string_the_client_is_handed_is_the_bodys_own_codepoints(self) -> None:
        """The copy ``DupWideStringSafe`` makes, placed where the client can read it."""

        serve_encoded_text(self.tables, self.encoded(5))

        self.body()

        served = self.encoded(5) + [0]
        self.assertEqual(len(self.client.bridge.encoded), 1)
        handed = next(iter(self.client.bridge.encoded.values()))
        self.assertEqual(
            handed,
            b"\x05\x01\x00\x00",
            "``DupWideStringSafe`` copies up to and including the terminator "
            f"(``dialog.cpp:242-247``), and the string served here starts {served[:2]!r}",
        )

    def test_the_open_dialog_reports_the_decoded_text(self) -> None:
        """``active_dialog_cache.message``, which is what the facade reads."""

        serve_encoded_text(self.tables, self.encoded(5))

        self.body()
        self.answer()

        active = dialog.PyDialog.get_active_dialog()
        self.assertEqual(
            active.raw_message,
            "Foreman",
            "the source assigns the decoded wide string whole, terminator included",
        )
        self.assertEqual(active.message, "Foreman", "and the facade sanitises it away")

    def test_a_body_whose_string_is_not_encoded_is_its_own_text(self) -> None:
        """``dialog.cpp:834-855``: the raw string is cached and the row carries it."""

        serve_encoded_text(self.tables, [ord("H"), ord("i")])

        self.body()

        self.assertEqual(self.rows()[0].text, "Hi")
        self.assertEqual(dialog.PyDialog.get_active_dialog().message, "Hi")

    def test_a_body_with_no_string_gets_a_row_and_no_text(self) -> None:
        """``dialog.cpp:831``: ``message_enc`` is null, so ``immediate_text`` stays empty."""

        self.body(pointer=0)

        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0].text, "")
        self.assertEqual(dialog.PyDialog.get_active_dialog().raw_message, "")

    def test_a_string_that_reads_empty_is_cached_as_the_empty_string(self) -> None:
        """``dialog.cpp:834-841``: a bare terminator is a plain string, and that is what it is."""

        serve_encoded_text(self.tables, [])

        self.body()

        self.assertEqual(self.rows()[0].text, "")
        self.assertEqual(
            dialog.PyDialog.get_active_dialog().raw_message,
            "",
            "the wide string is stored without its terminator, as std::wstring assign stores it",
        )

    def test_a_request_whose_state_moved_on_writes_nothing(self) -> None:
        """``dialog.cpp:1021-1025``: the epoch is what says the decode is no longer wanted."""

        serve_encoded_text(self.tables, self.encoded(5))
        self.body()
        dialog._observe_map_change(9, True)

        self.answer()

        self.assertEqual(self.rows(), [])
        self.assertEqual(
            dialog._body_decodes,
            {},
            "a decode whose epoch has moved on is dropped, not written",
        )
        self.assertEqual(
            self.client.bridge.decodes_in_flight(),
            0,
            "and the slot it was waiting in is given back",
        )

    def test_an_encoded_body_appends_no_row_until_its_decode_completes(self) -> None:
        """``dialog.cpp:884-887``: the row is the decode's, not the message's."""

        serve_encoded_text(self.tables, self.encoded(5))

        self.body()

        self.assertEqual(
            dialog._dialog_callback_journal,
            [],
            "an encoded body leaves the append to its decode, as native does",
        )
        self.assertEqual(len(dialog._body_decodes), 1)
        self.assertEqual(dialog._pending_decodes("dialog"), 1)

        self.answer()

        self.assertEqual(self.rows()[0].text, "Foreman")
        self.assertEqual(
            dialog._body_decodes, {}, "the completion takes the request with it"
        )
        self.assertEqual(dialog._pending_decodes("dialog"), 0)

    def test_a_string_that_cannot_be_read_is_the_failed_copy(self) -> None:
        """``dialog.cpp:832-833``: nothing is behind the pointer, so nothing is decoded."""

        self.body(pointer=0x0BAD0000)

        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0].text, "")
        self.assertEqual(dialog.PyDialog.get_active_dialog().raw_message, "")

    def test_the_text_a_dialog_advertises_is_readable_from_it(self) -> None:
        """The facade's inline-choice fallback has text to work on, because the body has it."""

        serve_encoded_text(self.tables, [ord(c) for c in "<a=7>Yes</a>"])

        self.body()

        choices = dialog.extract_inline_dialog_choices_from_text(
            dialog.PyDialog.get_active_dialog().raw_message
        )
        self.assertEqual([choice.dialog_id for choice in choices], [7])
        self.assertEqual(choices[0].message, "Yes")

    # -- the checks between the two halves ---------------------------------

    def test_a_decode_that_finishes_after_a_newer_body_writes_nothing_into_it(self) -> None:
        """``dialog.cpp:1026-1032``: the nonce decides the write, and only the write.

        The row is still appended — the source's two decisions are separate, and this is the
        one that shows it: a completion belonging to an older body is recorded, and is not
        allowed to overwrite the text of the body that replaced it.
        """

        serve_encoded_text(self.tables, self.encoded(5))
        self.body()
        self.answer()
        self.assertEqual(dialog.PyDialog.get_active_dialog().message, "Foreman")

        dialog._on_body_decoded(
            tick=dialog._now_ms(),
            request_epoch=dialog._decode_epoch,
            decode_nonce=dialog._body_decode_nonce - 1,
            agent_id=17,
            context_dialog_id=0,
            map_id=7,
            model_id=0,
            text="stale",
        )

        self.assertEqual(
            dialog.PyDialog.get_active_dialog().message,
            "Foreman",
            "the text belongs to the body whose nonce it carries",
        )
        self.assertEqual([row.text for row in self.rows()], ["Foreman", "stale"])

    def test_a_decode_from_a_cleared_epoch_appends_nothing(self) -> None:
        """``dialog.cpp:1021-1025``: an epoch that has moved on drops the whole completion."""

        rows_before = len(self.rows())

        dialog._on_body_decoded(
            tick=dialog._now_ms(),
            request_epoch=dialog._decode_epoch - 1,
            decode_nonce=dialog._body_decode_nonce,
            agent_id=17,
            context_dialog_id=0,
            map_id=7,
            model_id=0,
            text="stale",
        )

        self.assertEqual(len(self.rows()), rows_before)

    def test_a_decode_after_shutdown_appends_nothing_and_writes_nothing(self) -> None:
        dialog._shutdown_requested = True
        self.addCleanup(setattr, dialog, "_shutdown_requested", False)

        dialog._on_body_decoded(
            tick=dialog._now_ms(),
            request_epoch=dialog._decode_epoch,
            decode_nonce=dialog._body_decode_nonce,
            agent_id=17,
            context_dialog_id=0,
            map_id=7,
            model_id=0,
            text="stale",
        )

        self.assertEqual(self.rows(), [])
        self.assertEqual(dialog.PyDialog.get_active_dialog().raw_message, "")

    def test_a_body_that_arrives_suspended_appends_no_row(self) -> None:
        """``dialog.cpp:906-910``: the immediate append is guarded by the gate too."""

        dialog._callbacks_suspended = True
        serve_encoded_text(self.tables, [ord("H"), ord("i")])

        self.body()

        self.assertEqual(self.rows(), [])

    def test_a_decode_leaves_no_decode_in_flight(self) -> None:
        """The count ``Shutdown`` drains is taken back at the completion, however it ended."""

        serve_encoded_text(self.tables, self.encoded(5))

        self.body()
        self.assertEqual(dialog._pending_decodes("dialog"), 1)

        self.answer()

        self.assertEqual(dialog._pending_decodes("dialog"), 0)

    def test_a_decode_that_could_not_be_started_appends_the_empty_row(self) -> None:
        """``SafeAsyncDecodeStr``'s false, and what the source does with it.

        ``dialog.cpp:888-898``: the request is released and ``append_immediate`` stays as it
        was, so the row is appended here with the empty text. The call is refused by the
        capability layer — here by a client that will not take it — and nothing is claimed
        about text the client was never asked for.
        """

        serve_encoded_text(self.tables, self.encoded(5))

        def refuse(name: str, form: Any, *words: int) -> Any:
            raise RuntimeError("the call was refused")

        self.client.call_function = refuse  # type: ignore[method-assign]

        self.body()

        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0].text, "")
        self.assertEqual(dialog._body_decodes, {})
        self.assertEqual(dialog._pending_decodes("dialog"), 0)

    def test_the_body_takes_a_nonce_of_its_own(self) -> None:
        """``dialog.cpp:820``: what stops a late decode belongs to this body."""

        self.body(pointer=0)

        self.assertEqual(dialog._body_decode_nonce, 1)

        self.body(pointer=0)

        self.assertEqual(dialog._body_decode_nonce, 2)


class DialogButtonLabelTests(unittest.TestCase):
    """A button's caption: the third text path, and the one Route A could never render.

    The label pointer a button's packet carries is what native hands to the client's decoder
    (``dialog.cpp:692``) or takes as plain text (``641-644``), and the caption the facade reads
    is filled from that decode's cache (``1632-1664``). The client's side is faked exactly as it
    is for the body, so the module's own announcements, completion and getter are the real code.
    """

    def setUp(self) -> None:
        dialog._reset()
        dialog._clear_event_logs()
        dialog._clear_callback_journal()
        self.client = _FakeClient()
        self._client = mock.patch(
            "py4gw.client.require_client", return_value=self.client
        )
        self._client.start()
        self.addCleanup(self._client.stop)
        self._map = mock.patch.object(dialog, "_map_state", return_value=(7, True))
        self._map.start()
        self.addCleanup(self._map.stop)
        self._parser = mock.patch(
            "py4gw.ui.async_decode._has_text_parser", return_value=True
        )
        self._parser.start()
        self.addCleanup(self._parser.stop)
        dialog._observe_map_change(*dialog._map_state())
        dialog._callbacks_suspended = False

    def encoded(self, value: int) -> list[int]:
        run = uint32_to_enc_str(value, 8)
        assert run is not None, "the test's own encoding must fit"
        return run

    def button(self, dialog_id: int = 4484, pointer: int = ENCODED_POINTER) -> None:
        """Send one button message, with the label the client holds at ``pointer``.

        The label travels with the event as the observer's copy of it — taken inside the
        client's own call, which is where the source takes it (``dialog.cpp:639``).
        """

        dialog._dispatch_message(
            message(
                DIALOG_BUTTON,
                arg0=11,
                arg1=pointer,
                arg2=dialog_id,
                text=self.client_copy(pointer),
            )
        )

    def client_copy(self, pointer: int) -> list[int] | None:
        """The label the fake client holds at ``pointer``, as the observer copies it."""

        if not pointer:
            return None
        units: list[int] = []
        for index in range(dialog.MAX_DIALOG_TEXT_CODE_UNITS):
            unit = self.client.dialog_tables.words.get(pointer + index * 2)
            if unit is None:
                return units or None
            units.append(int(unit))
            if unit == 0:
                return units
        return None

    def answer(self, text: str) -> None:
        self.client.decoded = text
        deliver_decodes(self.client)

    def test_a_label_that_is_not_encoded_is_taken_as_it_stands(self) -> None:
        """``dialog.cpp:641-644``: no decoder is called for a plain label."""

        serve_encoded_text(self.client.dialog_tables, [ord(c) for c in "Accept"])

        self.button()

        buttons = dialog.PyDialog.get_active_dialog_buttons()
        self.assertEqual(buttons[0].dialog_id, 4484)
        self.assertEqual(buttons[0].message_decoded, "Accept")
        self.assertFalse(buttons[0].message_decode_pending)
        self.assertEqual(len(self.client.calls), 0, "a plain label is not decoded")
        self.assertEqual(
            [row.text for row in dialog.PyDialog.get_dialog_callback_journal()],
            ["Accept"],
            "the row carries the label the packet carried",
        )

    def test_an_encoded_label_is_handed_to_the_clients_decoder(self) -> None:
        """``dialog.cpp:646-708``: the label the client announced goes to its own decoder.

        This is the branch the port could not take while it read a buffer instead of the label:
        the announced pointer is reused by the client, and what was handed over asserted inside
        it (``IsParam(data)``, ``TextParser.cpp:724``, pid 30560 on 2026-09-25). What travels now
        is the observer's copy, taken inside the client's own call — measured live on 2026-09-25
        as the label itself, decoding to *"Would you tell me more about the Northern Support
        bonus?"* — so the source's branch is the one that runs.
        """

        serve_encoded_text(self.client.dialog_tables, self.encoded(5))
        # What the client's decoder will answer this label with. The fake records its answer when
        # the decoder is called — that is when the client produces it — so it is set first.
        self.client.decoded = "Tell me more"

        self.button()

        self.assertEqual(
            len(self.client.bridge.encoded), 1, "the label was handed over"
        )
        handed = next(iter(self.client.bridge.encoded.values()))
        self.assertEqual(
            handed,
            b"\x05\x01\x00\x00",
            "the copy goes to the client's decoder whole, terminator included, as the source "
            "hands over the copy ``DupWideStringSafe`` made (``dialog.cpp:242-247``)",
        )
        self.assertEqual(dialog._pending_decodes("dialog"), 1, "and counted in flight")
        self.assertEqual(dialog._decoded_button_label_pending, {4484: True})
        self.assertEqual(
            dialog._dialog_callback_journal,
            [],
            "an encoded label leaves the row to its completion, as native does",
        )
        self.assertEqual(
            [(button.message, button.message_decode_pending) for button in dialog._dialog_buttons],
            [("", True)],
            "the button is appended with the label state it has: none, and pending "
            "(`dialog.cpp:724-746`)",
        )

        self.answer("Tell me more")

        button = dialog.PyDialog.get_active_dialog_buttons()[0]
        self.assertFalse(button.message_decode_pending)
        self.assertEqual(button.message_decoded, "Tell me more")
        self.assertEqual(dialog._decoded_button_label_cache[4484], "Tell me more")
        self.assertEqual(dialog._decoded_button_label_pending, {})
        self.assertEqual(dialog._button_decodes, {})
        self.assertEqual(dialog._pending_decodes("dialog"), 0)
        rows = dialog.PyDialog.get_dialog_callback_journal()
        self.assertEqual([row.event_type for row in rows], ["recv_choice"])
        self.assertEqual(rows[0].text, "Tell me more")
        self.assertEqual(rows[0].dialog_id, 4484)

    def test_a_label_the_client_never_answers_for_leaves_the_button_pending(self) -> None:
        """``dialog.cpp:747-770``: the row waits for the label, so nothing is appended yet."""

        serve_encoded_text(self.client.dialog_tables, self.encoded(5))

        self.button()

        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal(), [])
        self.assertEqual(
            dialog._dialog_buttons[0].message_decode_pending,
            True,
            "the button is appended with the label state it has: none, and pending",
        )

    def test_a_full_pending_map_releases_the_label_instead_of_waiting(self) -> None:
        """``dialog.cpp:671-676``: at the cap a new id is not queued, and its row is appended."""

        serve_encoded_text(self.client.dialog_tables, self.encoded(5))
        for index in range(dialog.MAX_DECODED_BUTTON_LABEL_PENDING):
            dialog._decoded_button_label_pending[1000 + index] = True

        self.button()

        self.assertEqual(
            len(self.client.bridge.encoded),
            0,
            "the cap is reached, so no string was placed for a decode",
        )
        self.assertNotIn(4484, dialog._decoded_button_label_pending)
        self.assertEqual(dialog._button_decodes, {})
        self.assertEqual(dialog._pending_decodes("dialog"), 0)
        button = dialog.PyDialog.get_active_dialog_buttons()[0]
        self.assertFalse(button.message_decode_pending)
        self.assertEqual(
            len(dialog.PyDialog.get_dialog_callback_journal()),
            1,
            "a label that is not waited for is recorded here",
        )

    def test_the_label_the_packet_carried_is_the_caption_when_it_is_not_encoded(self) -> None:
        """``dialog.cpp:641-644``: a plain label is the text, and the row carries it."""

        serve_encoded_text(self.client.dialog_tables, [ord(c) for c in "Accept"])

        self.button()

        button = dialog.PyDialog.get_active_dialog_buttons()[0]
        self.assertTrue(button.message_decoded)
        self.assertEqual(button.message, button.message_decoded)
        self.assertFalse(button.message_decode_pending)
        rows = dialog.PyDialog.get_dialog_callback_journal()
        self.assertEqual([row.event_type for row in rows], ["recv_choice"])
        self.assertEqual(rows[0].text, button.message_decoded)
        self.assertEqual(rows[0].dialog_id, 4484)

    def test_the_caption_falls_back_to_the_catalogs_text_for_the_button_id(self) -> None:
        """``dialog.cpp:1655-1658``: no label, so the dialog id's own text is asked for.

        The id has to be one the catalog can answer for: ``GetDialogTextDecoded`` refuses past
        ``MAX_DIALOG_ID`` (``dialog.cpp:1459-1461``), and a button's own id — 4484 in the live
        dialog — is past it, which is why the fallback reaches only the low ids.
        """

        self.button(dialog_id=9, pointer=0)
        dialog._decoded_text_cache[9] = "Northern Support"

        with mock.patch.object(dialog, "_is_dialog_map_ready", return_value=True):
            button = dialog.PyDialog.get_active_dialog_buttons()[0]

        self.assertEqual(button.message_decoded, "Northern Support")

    def test_a_button_with_no_id_is_left_alone(self) -> None:
        """``dialog.cpp:1639-1641``: the getter skips it rather than captioning it."""

        self.button(dialog_id=0, pointer=0)

        self.assertEqual(dialog.PyDialog.get_active_dialog_buttons()[0].dialog_id, 0)
        self.assertEqual(dialog.PyDialog.get_active_dialog_buttons()[0].message_decoded, "")


class DialogJournalTests(unittest.TestCase):
    """The two journals (``dialog.cpp:457-544`` and the members that read them).

    The appenders are driven through the same dispatch the client's messages go through, so what
    is tested is the record the port keeps for a real message — the packet bytes, the direction,
    the caps, and the ordering the getters promise.
    """

    def setUp(self) -> None:
        dialog._reset()
        # The send path is the source's handler case, whose outer guard refuses the
        # message while the map is not ready (`dialog.cpp:600-603`); these classes have no
        # client, so the map state is stubbed as the body tests stub it.
        self._map = mock.patch.object(dialog, "_map_state", return_value=(7, True))
        self._map.start()
        self.addCleanup(self._map.stop)
        dialog._clear_event_logs()
        dialog._clear_callback_journal()

        # A body's third word is its text pointer, so a body message reads the client for the
        # string it carries. The fake answers those reads — with nothing behind most pointers,
        # which is the source's failed copy rather than an error. ``DialogBodyTextTests`` is
        # where a body with a real string behind it is tested.
        self.client = _FakeClient()
        self.tables = self.client.dialog_tables
        self._client = mock.patch(
            "py4gw.client.require_client", return_value=self.client
        )
        self._client.start()
        self.addCleanup(self._client.stop)

        # The gate is open, because that is the only way a message reaches the module: the
        # capture refuses a body while callbacks are suspended, and so does the row it appends.
        dialog._observe_map_change(*dialog._map_state())
        dialog._callbacks_suspended = False

    def tearDown(self) -> None:
        dialog._reset()
        dialog._clear_event_logs()
        dialog._clear_callback_journal()

    # -- the event log -----------------------------------------------------

    def test_a_body_is_recorded_with_its_packet_and_its_direction(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg0=1, arg1=241, arg2=0x1234))

        logs = dialog.PyDialog.get_dialog_event_logs()
        self.assertEqual(len(logs), 1)
        entry = logs[0]
        self.assertEqual(entry.message_id, DIALOG_BODY)
        self.assertTrue(entry.incoming)
        self.assertFalse(entry.is_frame_message)
        self.assertEqual(entry.frame_id, 0)
        self.assertEqual(
            entry.w_bytes,
            struct.pack("<3I", 1, 241, 0x1234),
            "a DialogBodyInfo is three words, and the whole packet is copied",
        )
        self.assertEqual(entry.l_bytes, b"")
        self.assertEqual(len(dialog.PyDialog.get_dialog_event_logs_received()), 1)
        self.assertEqual(dialog.PyDialog.get_dialog_event_logs_sent(), [])

    def test_a_button_is_recorded_with_its_whole_sixteen_byte_packet(self) -> None:
        dialog._dispatch_message(
            message(DIALOG_BUTTON, arg0=11, arg1=0x2222, arg2=4484, arg3=0)
        )

        entry = dialog.PyDialog.get_dialog_event_logs()[0]

        self.assertEqual(entry.message_id, DIALOG_BUTTON)
        self.assertEqual(
            entry.w_bytes, struct.pack("<4I", 11, 0x2222, 4484, 0)
        )

    def test_a_sent_dialog_is_recorded_as_outgoing_with_the_id_itself(self) -> None:
        """``dialog.cpp:933-942``: the source copies the id, not a pointer."""

        dialog._note_sent_dialog(4484, DIALOG_SEND)

        logs = dialog.PyDialog.get_dialog_event_logs()
        self.assertEqual(len(logs), 1)
        self.assertFalse(logs[0].incoming)
        self.assertEqual(logs[0].w_bytes, struct.pack("<I", 4484))
        self.assertEqual(dialog.PyDialog.get_dialog_event_logs_received(), [])
        self.assertEqual(len(dialog.PyDialog.get_dialog_event_logs_sent()), 1)

    def test_the_event_log_drops_the_oldest_entries_past_its_cap(self) -> None:
        for index in range(dialog.MAX_DIALOG_EVENT_LOGS + 3):
            dialog._dispatch_message(
                message(DIALOG_BODY, arg0=1, arg1=index, arg2=0)
            )

        logs = dialog.PyDialog.get_dialog_event_logs()
        self.assertEqual(len(logs), dialog.MAX_DIALOG_EVENT_LOGS)
        self.assertEqual(logs[0].w_bytes, struct.pack("<3I", 1, 3, 0), "the oldest went")
        self.assertEqual(
            len(dialog.PyDialog.get_dialog_event_logs_received()),
            dialog.MAX_DIALOG_EVENT_LOGS,
        )

    def test_the_returned_lists_are_copies(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=7))

        returned = dialog.PyDialog.get_dialog_event_logs()
        returned.clear()

        self.assertEqual(len(dialog.PyDialog.get_dialog_event_logs()), 1)

    # -- the callback journal ----------------------------------------------

    def test_a_body_records_the_context_it_answers(self) -> None:
        dialog._note_sent_dialog(4484, DIALOG_SEND)
        dialog._dispatch_message(message(DIALOG_BODY, arg0=1, arg1=17, arg2=0))

        entries = dialog.PyDialog.get_dialog_callback_journal()
        body = [entry for entry in entries if entry.event_type == "recv_body"][0]

        self.assertEqual(body.context_dialog_id, 4484)
        self.assertTrue(body.context_dialog_id_inferred)
        self.assertEqual(body.agent_id, 17)
        self.assertEqual(body.dialog_id, 0)
        self.assertFalse(body.dialog_id_authoritative)
        self.assertEqual(
            body.npc_uid,
            "7:0:17",
            "map and model are zero here — there is no client to read the agent model "
            "from — and the uid is still built from the agent id",
        )

    def test_a_button_records_its_own_id_as_authoritative(self) -> None:
        dialog._dispatch_message(message(DIALOG_BUTTON, arg0=11, arg2=4484))

        choice = [
            entry
            for entry in dialog.PyDialog.get_dialog_callback_journal()
            if entry.event_type == "recv_choice"
        ][0]

        self.assertEqual(choice.dialog_id, 4484)
        self.assertTrue(choice.dialog_id_authoritative)
        self.assertEqual(choice.message_id, DIALOG_BUTTON)
        self.assertTrue(choice.incoming)

    def test_a_send_records_the_previous_context_and_goes_to_the_sent_list(self) -> None:
        """``dialog.cpp:975-990``: the context is read *before* the send rewrites it."""

        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))
        dialog._note_sent_dialog(6020, DIALOG_SEND)

        sent = dialog.PyDialog.get_dialog_callback_journal_sent()
        self.assertEqual([entry.event_type for entry in sent], ["sent_choice"])
        self.assertEqual(sent[0].dialog_id, 6020)
        self.assertTrue(sent[0].dialog_id_authoritative)
        self.assertFalse(sent[0].incoming)

    def test_the_journal_is_sorted_by_tick_then_event_then_direction(self) -> None:
        """``DialogCallbackJournalChronologicalLess``: body, then choice, then sent."""

        dialog._append_dialog_callback_journal_entry(
            tick=1000,
            message_id=DIALOG_SEND,
            incoming=False,
            event_type="sent_choice",
            dialog_id=3,
            context_dialog_id=0,
            agent_id=0,
            dialog_id_authoritative=True,
            context_dialog_id_inferred=False,
        )
        dialog._append_dialog_callback_journal_entry(
            tick=1000,
            message_id=DIALOG_BUTTON,
            incoming=True,
            event_type="recv_choice",
            dialog_id=2,
            context_dialog_id=0,
            agent_id=0,
            dialog_id_authoritative=True,
            context_dialog_id_inferred=False,
        )
        dialog._append_dialog_callback_journal_entry(
            tick=1000,
            message_id=DIALOG_BODY,
            incoming=True,
            event_type="recv_body",
            dialog_id=0,
            context_dialog_id=0,
            agent_id=0,
            dialog_id_authoritative=False,
            context_dialog_id_inferred=False,
        )
        dialog._append_dialog_callback_journal_entry(
            tick=999,
            message_id=DIALOG_SEND,
            incoming=False,
            event_type="sent_choice",
            dialog_id=9,
            context_dialog_id=0,
            agent_id=0,
            dialog_id_authoritative=True,
            context_dialog_id_inferred=False,
        )

        self.assertEqual(
            [entry.event_type for entry in dialog.PyDialog.get_dialog_callback_journal()],
            ["sent_choice", "recv_body", "recv_choice", "sent_choice"],
            "the earlier tick first, then the event priority",
        )

    def test_the_journal_drops_the_oldest_entries_past_its_cap(self) -> None:
        for index in range(dialog.MAX_DIALOG_CALLBACK_JOURNAL + 2):
            dialog._dispatch_message(
                message(DIALOG_BODY, arg1=1, arg2=index)
            )

        self.assertEqual(
            len(dialog.PyDialog.get_dialog_callback_journal()),
            dialog.MAX_DIALOG_CALLBACK_JOURNAL,
        )

    def test_the_npc_uid_is_the_map_model_agent_triple(self) -> None:
        self.assertEqual(dialog._build_npc_uid(7, 12, 34), "7:12:34")
        self.assertEqual(
            dialog._build_npc_uid(7, 12, 0), "", "no agent is no uid, as the source says"
        )

    # -- the filtered clear ------------------------------------------------

    def test_a_filtered_clear_keeps_what_does_not_match_and_rebuilds_the_directions(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg0=11, arg2=4484))
        dialog._note_sent_dialog(6020, DIALOG_SEND)

        dialog.PyDialog.clear_dialog_callback_journal_filtered(incoming=True)

        remaining = dialog.PyDialog.get_dialog_callback_journal()
        self.assertEqual([entry.event_type for entry in remaining], ["sent_choice"])
        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal_received(), [])
        self.assertEqual(
            len(dialog.PyDialog.get_dialog_callback_journal_sent()),
            1,
            "the direction lists are rebuilt from what is left",
        )

    def test_a_filtered_clear_by_event_type_and_message_id(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))
        dialog._dispatch_message(message(DIALOG_BUTTON, arg0=11, arg2=4484))

        dialog.PyDialog.clear_dialog_callback_journal_filtered(event_type="recv_body")
        self.assertEqual(
            [entry.event_type for entry in dialog.PyDialog.get_dialog_callback_journal()],
            ["recv_choice"],
        )

        dialog.PyDialog.clear_dialog_callback_journal_filtered(
            message_id=DIALOG_BUTTON
        )
        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal(), [])

    def test_a_filtered_clear_with_no_filters_clears_everything(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))

        dialog.PyDialog.clear_dialog_callback_journal_filtered()

        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal(), [])
        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal_received(), [])
        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal_sent(), [])

    def test_an_empty_event_type_is_no_filter_and_so_removes_everything(self) -> None:
        """``dialog.cpp:1783``: an empty string is treated as absent.

        Which makes it a filter that matches everything, and the source's clear removes what
        matches — so ``event_type=""`` empties the journal, exactly as passing no filters at
        all does.
        """

        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))

        dialog.PyDialog.clear_dialog_callback_journal_filtered(event_type="")

        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal(), [])

    # -- the lifecycle -----------------------------------------------------

    def test_clear_cache_empties_both_journals_and_bumps_the_epochs(self) -> None:
        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))
        epoch = dialog._decode_epoch
        nonce = dialog._body_decode_nonce

        dialog.PyDialog.clear_cache()

        self.assertEqual(dialog.PyDialog.get_dialog_event_logs(), [])
        self.assertEqual(dialog.PyDialog.get_dialog_callback_journal(), [])
        self.assertEqual(dialog._decode_epoch, epoch + 1)
        self.assertEqual(dialog._body_decode_nonce, nonce + 1)

    def test_terminate_sets_the_flags_bumps_the_epochs_and_clears_the_catalog(self) -> None:
        dialog._decoded_text_cache[5] = "Foreman"
        dialog._decoded_text_pending[6] = True
        dialog._dispatch_message(message(DIALOG_BODY, arg1=17))

        dialog.PyDialog.terminate()

        self.assertTrue(dialog._shutdown_requested)
        self.assertTrue(dialog._catalog_shutdown_requested)
        self.assertEqual(dialog._decoded_text_cache, {})
        self.assertEqual(dialog._decoded_text_pending, {})
        self.assertEqual(dialog.PyDialog.get_dialog_event_logs(), [])

    def test_a_shutdown_stops_the_queue_from_running_again(self) -> None:
        """``ClearCatalogCache`` and the flag are what a later decode sees."""

        dialog.PyDialog.terminate()
        epoch = dialog._catalog_decode_epoch

        dialog._queue_dialog_text_decode(5)

        self.assertEqual(
            dialog._catalog_decode_epoch, epoch, "a shut-down queue changes nothing"
        )
        self.assertEqual(dialog._decoded_text_pending, {})
        self.assertEqual(dialog._decoded_text_cache, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
