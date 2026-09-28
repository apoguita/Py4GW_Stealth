"""``UIManager``, the class: the source's surface, the members that answer, and the ones that name work.

The class is the port of Reforged's ``Py4GWCoreLib/UIManager.py``, ``class UIManager`` (lines 29-618,
**55 declarations**; the fourteen window classes from line 619 on are out of scope permanently). The
checks here are the ones this project's classes carry:

- **the surface is the source's** — every declaration, its nesting and its order, compared against
  Reforged's own file by ``ast``, not by eye;
- **the raising set is pinned** — the members whose body raises are listed exactly, so a member that
  starts or stops raising is a failing test rather than a quiet drift;
- **the members that answer are checked against what the client sees**: the three state words and
  their masks and defaults from ``ui_methods.cpp:1724-1737``, the window-position record from
  ``context/ui.h:532-537``, the encoded-string four, and the actions' call shapes.

A fixture client answers the reads and records what the actions asked for, the way every class test in
this suite does it.
"""

from __future__ import annotations

import ast
import pathlib
import struct
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw import ui_manager as ui_manager_module
from py4gw.context.gw_array import GWArray
from py4gw.game_thread.shared_block import CallForm, Operation
from py4gw.ui.frame import FrameStruct, is_valid_frame_pointer
from py4gw.ui_manager import UIManager

MODULE_PATH = pathlib.Path(__file__).resolve().parent.parent / "py4gw" / "ui_manager.py"
SOURCE_ROOT = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib")
SOURCE_UI_MANAGER = SOURCE_ROOT / "UIManager.py"

#: The seven members whose body contains a raise, with the reason each one gives. **None of them
#: raises on a branch any more** — `Keydown`/`Keyup`'s ``frame_id == 0`` path is built — so this set
#: is also the set of members that raise unconditionally. A member that starts or stops raising is
#: meant to change this list, which is the point of pinning it.
RAISING_MEMBERS = {
    "RegisterFrameIOCallbacks",
    "SetOpenLinks",
    "ClearFrameLogs",
    "ClearUIMessageLogs",
    "GetFrameLogs",
    "GetUIMessageLogs",
    "_UpdateFrameIOEvents",
}

#: The members above whose raise is conditional. Empty since round 67, and kept so a new conditional
#: raiser is a deliberate change to this file.
BRANCH_RAISERS: set[str] = set()


def _class_members(path: pathlib.Path, name: str = "UIManager") -> list[str]:
    """Every declaration of a class in a file — nested ones included — in source order."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == name
    )
    functions = [node for node in ast.walk(cls) if isinstance(node, ast.FunctionDef)]
    return [node.name for node in sorted(functions, key=lambda node: node.lineno)]


def _source_members() -> list[str]:
    """Every declaration of the source's class, nested members included, in source order."""

    return _class_members(SOURCE_UI_MANAGER)


def _port_members() -> list[str]:
    return _class_members(MODULE_PATH)


# --------------------------------------------------------------------------
class _FakeReader:
    """A flat memory: the fixture's spans, keyed by address."""

    def __init__(self, spans: dict[int, bytes]) -> None:
        self.spans = spans

    def read(self, address: int, size: int) -> bytes:
        for start, payload in self.spans.items():
            if start <= address and address + size <= start + len(payload):
                offset = address - start
                return payload[offset : offset + size]
        raise OSError(f"no fixture span covers {address:#x}+{size}")


class _FakeBridge:
    """The data region, so an action's placements can be inspected."""

    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []
        self.commands: list[tuple[Any, int, int, int]] = []

    def write_data(self, offset: int, payload: bytes) -> int:
        self.writes.append((offset, bytes(payload)))
        return 0x70000000 + offset

    def submit(
        self,
        operation: Any,
        arg0: int = 0,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
        timeout_ms: int | None = None,
    ) -> None:
        self.commands.append((operation, arg0, arg1, arg2))


class _FakeTooltip:
    def __init__(self, address: int) -> None:
        self.address = address

    def resolve_address(self) -> int:
        return self.address


class _FakeFrameArray:
    """Only the two reads the key action makes, plus the wide-string read."""

    def __init__(self, pointer: int, callbacks_size: int, wide: str = "") -> None:
        self.pointer = pointer
        self.callbacks_size = callbacks_size
        self.wide = wide
        #: ``frame_id_by_hash``'s answers, for the button-action frame's label lookup.
        self.parent_by_hash: dict[int, int] = {}

    def read_frame_pointer(self, frame_id: int) -> int:
        return self.pointer

    def get(self, frame_id: int) -> Any:
        if not self.pointer:
            return None
        record = FrameStruct()
        record.frame_callbacks = GWArray(0x00300000, self.callbacks_size, self.callbacks_size, 0)
        return record

    def frame_id_by_hash(self, frame_hash: int) -> int:
        return self.parent_by_hash.get(int(frame_hash), 0)

    def read_wide_string(self, address: int, limit: int) -> str:
        return self.wide


class _FakeClient:
    """A client stand-in: the addresses, the reader, the bridge, and the calls it was asked for."""

    def __init__(
        self,
        addresses: dict[str, int] | None = None,
        spans: dict[int, bytes] | None = None,
        frame_pointer: int = 0,
        callbacks_size: int = 0,
        wide: str = "",
    ) -> None:
        self._addresses = dict(addresses or {})
        self._spans = spans or {}
        self.reader = _FakeReader(self._spans)
        #: ``py4gw/ui/preferences.py`` reads through the connection's private attribute, so the
        #: fixture answers both names.
        self._reader = self.reader
        self.bridge = _FakeBridge()
        self.frame_array = _FakeFrameArray(frame_pointer, callbacks_size, wide)
        self.current_tooltip = _FakeTooltip(self._addresses.get("ui.current_tooltip_ptr", 0))
        self.calls: list[tuple[str, CallForm, tuple[int, ...]]] = []
        self.ui_messages: list[tuple[int, int, int]] = []
        self.raw_messages: list[tuple[int, int, int]] = []
        #: What a called function answers in ``eax``, by resolver name.
        self.values: dict[str, int] = {}
        #: What a called *address* answers, for the client's own function pointers.
        self.address_value = 0

    def resolves(self, name: str) -> bool:
        return name in self._addresses

    def _resolve(self, name: str) -> int:
        return self._addresses.get(name, 0)

    def call_function(self, name: str, form: CallForm, *args: int, **_: Any) -> Any:
        self.calls.append((name, form, tuple(int(arg) for arg in args)))
        value = self.values.get(name, 0)

        class _Record:
            pass

        record = _Record()
        record.value = value  # type: ignore[attr-defined]
        return record

    def call_address(self, target: int, form: CallForm, *args: int, **_: Any) -> Any:
        self.calls.append((f"address:{target:#x}", form, tuple(int(arg) for arg in args)))

        class _Record:
            pass

        record = _Record()
        record.value = self.address_value  # type: ignore[attr-defined]
        return record

    def send_ui_message(self, message_id: int, wparam: int = 0, lparam: int = 0) -> Any:
        self.ui_messages.append((int(message_id), int(wparam), int(lparam)))
        return None

    def send_ui_message_raw(self, message_id: int, wparam: int = 0, lparam: int = 0) -> Any:
        """``ConnectedClient``'s three-word call — the client's own sender, unwrapped."""

        self.raw_messages.append((int(message_id), int(wparam), int(lparam)))
        return None


# --------------------------------------------------------------------------
class UIManagerSurfaceTests(unittest.TestCase):
    """The source's surface, in the source's order, with the raising set pinned."""

    def test_every_source_declaration_is_present_in_the_source_order(self) -> None:
        source = _source_members()
        self.assertEqual(len(source), 55, f"the source declares 55: {source}")
        self.assertEqual(_port_members(), source)
    def test_the_two_nested_members_are_nested_where_the_source_nests_them(self) -> None:
        source = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        cls = next(node for node in source.body if isinstance(node, ast.ClassDef))
        top = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
        self.assertNotIn("_add_event", top, "the source nests it inside _UpdateFrameIOEvents")
        self.assertNotIn("_is_button", top, "the source nests it inside GetDialogButtons")
        for owner, nested in (
            ("_UpdateFrameIOEvents", "_add_event"),
            ("GetDialogButtons", "_is_button"),
        ):
            member = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == owner)
            inner = {node.name for node in ast.walk(member) if isinstance(node, ast.FunctionDef)}
            self.assertIn(nested, inner)

    def test_the_class_attributes_are_the_sources(self) -> None:
        self.assertIsNone(UIManager._overlay, "no overlay object exists here (UIManager.py:30)")
        self.assertEqual(UIManager._devtext_dialog_proc_cache, 0)
        self.assertEqual(UIManager.frame_callbacks, [])
        self.assertEqual(dict(UIManager.frame_io_events), {})
        self.assertEqual(
            sorted(UIManager.IOEvent.__annotations__),
            ["details", "event_type", "mouse_pos", "timestamp"],
        )

    def test_the_module_constants_are_the_sources(self) -> None:
        self.assertEqual(ui_manager_module.NPC_DIALOG_HASH, 3856160816)
        self.assertEqual(ui_manager_module.DEFAULT_OFFSET, [2, 0, 0, 1])
        self.assertEqual(ui_manager_module.DIALOG_CHILD_OFFSET, [2, 0, 0, 1])

    def test_the_raising_set_is_exactly_this(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        raisers: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Name) and inner.id == "_unported":
                    raisers.append(node.name)
        self.assertEqual(set(raisers), RAISING_MEMBERS)
        self.assertEqual(len(raisers), len(RAISING_MEMBERS), "no member raises twice")
        self.assertTrue(
            BRANCH_RAISERS <= RAISING_MEMBERS,
            "the conditional raisers are a subset of the raisers",
        )
        #: The arithmetic the port doc and the class map carry, from the AST rather than by hand:
        #: 55 declarations, 7 of them with a raise, none of those conditional.
        self.assertEqual(len(_source_members()) - len(RAISING_MEMBERS), 48)
        self.assertEqual(len(RAISING_MEMBERS) - len(BRANCH_RAISERS), 7)

    def test_every_raiser_names_the_work_it_needs(self) -> None:
        """A raise is never bare: `_unported` is called with a member name and a requirement."""

        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and getattr(inner.func, "id", "") == "_unported":
                    self.assertEqual(len(inner.args), 2, f"{node.name}: member and requirement")
                    self.assertIsInstance(inner.args[0], ast.Constant)
                    self.assertIsInstance(inner.args[1], ast.Constant)
                    requirement = inner.args[1]
                    self.assertIsInstance(requirement, ast.Constant)
                    self.assertGreaterEqual(len(str(getattr(requirement, "value", ""))), 40)


# --------------------------------------------------------------------------
class UIManagerReadTests(unittest.TestCase):
    """The reads: the client's own words, with native's masks, defaults and bounds."""

    def _client(self, **kwargs: Any) -> _FakeClient:
        return _FakeClient(**kwargs)

    def _patch(self, client: _FakeClient) -> None:
        patcher = mock.patch("py4gw.client.require_client", return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_is_world_map_showing_is_the_mask(self) -> None:
        """``ui_methods.cpp:1736``: ``(*state & 0x80000) != 0``, and ``False`` with no address."""

        address = 0x00500000
        for word, expected in ((0x80000, True), (0x80001, True), (0x7FFFF, False), (0, False)):
            client = self._client(
                addresses={"ui.world_map_state_addr": address},
                spans={address: struct.pack("<I", word)},
            )
            self._patch(client)
            self.assertIs(UIManager.IsWorldMapShowing(), expected)
        self._patch(self._client())
        self.assertFalse(UIManager.IsWorldMapShowing())

    def test_is_ui_drawn_is_inverted_and_defaults_true(self) -> None:
        """``ui_methods.cpp:1726``: ``ui_drawn ? (*ui_drawn == 0) : true``."""

        address = 0x00501000
        for word, expected in ((0, True), (1, False), (7, False)):
            client = self._client(
                addresses={"ui.ui_drawn_addr": address},
                spans={address: struct.pack("<I", word)},
            )
            self._patch(client)
            self.assertIs(UIManager.IsUIDrawn(), expected, f"word {word}")
        self._patch(self._client())
        self.assertTrue(UIManager.IsUIDrawn(), "an unresolved address is the source's true")

    def test_is_shift_screenshot_is_a_nonzero_word(self) -> None:
        address = 0x00502000
        client = self._client(
            addresses={"ui.shift_screenshot_addr": address},
            spans={address: struct.pack("<I", 1)},
        )
        self._patch(client)
        self.assertTrue(UIManager.IsShiftScreenshot())
        self._patch(self._client())
        self.assertFalse(UIManager.IsShiftScreenshot())

    def test_get_current_tooltip_address_reads_the_global_once(self) -> None:
        """The port's recorded divergence: the global holds the tooltip pointer itself."""

        global_address = 0x00503000
        record = 0x10040000
        client = self._client(
            addresses={"ui.current_tooltip_ptr": global_address},
            spans={global_address: struct.pack("<I", record)},
        )
        self._patch(client)
        self.assertEqual(UIManager.GetCurrentTooltipAddress(), record)
        self._patch(self._client())
        self.assertEqual(UIManager.GetCurrentTooltipAddress(), 0)

    def test_get_windo_position_is_the_records_four_floats(self) -> None:
        """``ui_bindings.cpp:673-677`` reads ``p1.x``, ``p1.y``, ``p2.x``, ``p2.y``."""

        base = 0x00504000
        entry = base + 3 * 0x14
        client = self._client(
            addresses={"ui.window_positions_array": base},
            spans={entry: struct.pack("<Iffff", 0x9, 1.5, 2.5, 3.5, 4.5)},
        )
        self._patch(client)
        self.assertEqual(UIManager.GetWindoPosition(3), [1.5, 2.5, 3.5, 4.5])
        self.assertEqual(UIManager.GetWindoPosition(0x66), [], "ui.h:109: the bound is 0x66")

    def test_is_window_visible_is_state_bit_zero(self) -> None:
        base = 0x00505000
        for state, expected in ((1, True), (0, False), (0x1F, True), (2, False)):
            client = self._client(
                addresses={"ui.window_positions_array": base},
                spans={base: struct.pack("<Iffff", state, 0.0, 0.0, 0.0, 0.0)},
            )
            self._patch(client)
            self.assertIs(UIManager.IsWindowVisible(0), expected, f"state {state:#x}")
        self._patch(self._client())
        self.assertFalse(UIManager.IsWindowVisible(0))

    def test_get_preference_options_reads_the_client_entry(self) -> None:
        """``ui_methods.cpp:1438-1448``: ``options_count`` and the words ``options`` points at."""

        base = 0x00506000
        options = 0x00507000
        entry = base + 2 * 0x14
        client = self._client(
            addresses={"ui.enum_preference_options_addr": base},
            spans={
                entry: struct.pack("<IIIII", 0, 3, options, 0, 0),
                options: struct.pack("<III", 10, 20, 30),
            },
        )
        self._patch(client)
        self.assertEqual(UIManager.GetPreferenceOptions(2), [10, 20, 30])
        self.assertEqual(UIManager.GetPreferenceOptions(8), [], "EnumPreference.Count is 8")
        self._patch(self._client())
        self.assertEqual(UIManager.GetPreferenceOptions(0), [])

    def test_get_settings_reads_the_array_the_address_holds(self) -> None:
        """``ui_methods.cpp:1720-1722`` hands out ``GW::Array<unsigned char>*``."""

        address = 0x00508000
        buffer = 0x00509000
        client = self._client(
            addresses={"ui.game_settings_addr": address},
            spans={
                address: struct.pack("<IIII", buffer, 4, 3, 0),
                buffer: b"\x01\x02\x03",
            },
        )
        self._patch(client)
        self.assertEqual(UIManager.GetSettings(), [1, 2, 3])
        self._patch(self._client())
        self.assertEqual(UIManager.GetSettings(), [])


# --------------------------------------------------------------------------
class UIManagerEncStrTests(unittest.TestCase):
    """The encoded-string four, at the member's own boundary: a ``str`` in, a ``str`` out."""

    def test_a_string_is_validated_with_the_terminator_its_conversion_adds(self) -> None:
        """The conversion's terminator is what the grammar needs; the empty string is not valid."""

        self.assertTrue(UIManager.IsValidEncStr(chr(0x100)), "one word and its terminator")
        self.assertTrue(UIManager.IsValidEncStr(chr(0x100) + chr(0x100)))
        self.assertFalse(UIManager.IsValidEncStr(""), "a lone terminator is not a word")
        self.assertFalse(UIManager.IsValidEncStr("A"), "0x41 is under WORD_VALUE_BASE")

    def test_bytes_are_validated_by_the_three_preconditions(self) -> None:
        """``py_ui.h:4606-4615``: non-empty, a whole number of units, and a final ``0x0000``."""

        self.assertFalse(UIManager.IsValidEncBytes(b""), "empty is refused first")
        self.assertFalse(UIManager.IsValidEncBytes(b"\x00"), "one byte is not a wchar_t")
        self.assertFalse(UIManager.IsValidEncBytes(b"\x01\x02"), "no terminator")
        self.assertFalse(UIManager.IsValidEncBytes(b"\x00\x00"), "a lone terminator is not valid")
        self.assertTrue(UIManager.IsValidEncBytes(b"\x00\x01\x00\x00"), "0x100 then the terminator")

    def test_a_number_round_trips_through_the_two_enc_str_members(self) -> None:
        for value in (1, 2, 0xFF, 0x7EFF, 0x378F9, 0x37900):
            encoded = UIManager.UInt32ToEncStr(value)
            self.assertEqual(UIManager.EncStrToUInt32(encoded), value, f"value {value:#x}")

    def test_the_binding_s_own_count_bounds_what_can_be_encoded(self) -> None:
        """``ui_bindings.cpp:1132-1136`` passes count ``8``, and ``UInt32ToEncStr`` needs
        ``ceil(value / WORD_VALUE_RANGE) + 1`` code units (``ui_methods.cpp:2631-2635``), so
        ``7 * WORD_VALUE_RANGE`` is the last value that fits; past it the call refuses, the buffer
        keeps its zeros, and the binding's ``std::wstring(buffer)`` is the empty string.
        """

        from py4gw.ui.encoded_str import WORD_VALUE_RANGE

        boundary = 7 * WORD_VALUE_RANGE
        self.assertNotEqual(UIManager.UInt32ToEncStr(boundary), "", f"{boundary:#x} fits")
        self.assertEqual(
            UIManager.UInt32ToEncStr(boundary + 1), "", f"{boundary + 1:#x} does not"
        )

    def test_zero_encodes_to_nothing_and_decodes_to_the_sources_wrapped_value(self) -> None:
        """``ui_methods.cpp:2631-2656``, the encoder's own arithmetic: 0 needs no digits, so the
        buffer is only its terminator, and the decoder then reads that terminator as a digit —
        ``(0 - WORD_VALUE_BASE)`` in ``uint32``. Both halves are the source's, not this port's.
        """

        self.assertEqual(UIManager.UInt32ToEncStr(0), "")
        self.assertEqual(UIManager.EncStrToUInt32(""), 0xFFFFFF00)


# --------------------------------------------------------------------------
class UIManagerActionTests(unittest.TestCase):
    """The actions: the call each one makes, with the source's own arguments and bounds."""

    def _patch(self, client: _FakeClient) -> None:
        patcher = mock.patch("py4gw.client.require_client", return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_send_ui_message_builds_natives_payload_and_answers_early_for_the_masked_range(self) -> None:
        """``ui_bindings.cpp:60-74`` (sixteen zeroed words, values in front) and
        ``ui_methods.cpp:250-252`` (the masked id is ``true`` without a send).
        """

        client = _FakeClient(addresses={"ui.send_ui_message_func": 0x00600000})
        self._patch(client)
        self.assertTrue(UIManager.SendUIMessage(0x10000020, [17, 0, 3]))
        offset, payload = client.bridge.writes[0]
        self.assertEqual(offset, 0xE00)
        self.assertEqual(len(payload), 64, "native's sixteen words")
        self.assertEqual(
            struct.unpack("<III", payload[:12]), (17, 0, 3), "the values go into the front"
        )
        self.assertEqual(payload[12:], bytes(52), "the rest is zeroed")
        self.assertEqual(client.raw_messages, [(0x10000020, 0x70000000 + 0xE00, 0)])

        self.assertTrue(UIManager.SendUIMessage(0x30000000, [1, 2]))
        self.assertEqual(len(client.raw_messages), 1, "the masked id is answered without sending")

    def test_send_ui_message_refuses_when_the_client_has_no_sender(self) -> None:
        """``RawSendUiMessage``'s own first check (``ui_methods.cpp:246-248``)."""

        client = _FakeClient()
        self._patch(client)
        self.assertFalse(UIManager.SendUIMessage(0x10000020, [17]))
        self.assertFalse(UIManager.SendUIMessageRaw(0x10000020, 17, 0))
        self.assertEqual(client.raw_messages, [])

    def test_send_ui_message_raw_passes_the_callers_words_untouched(self) -> None:
        """``ui_bindings.cpp:1062-1065``: the two words are the caller's, not a payload's address."""

        client = _FakeClient(addresses={"ui.send_ui_message_func": 0x00600000})
        self._patch(client)
        self.assertTrue(UIManager.SendUIMessageRaw(0x10000020, 0x1234, 0x5678))
        self.assertEqual(client.raw_messages, [(0x10000020, 0x1234, 0x5678)])
        self.assertEqual(client.bridge.writes, [], "nothing is placed for the raw form")

    def test_set_window_visible_is_four_words_and_bounded(self) -> None:
        """``ui_methods.cpp:1690-1696``: ``(window_id, is_visible ? 1 : 0, nullptr, nullptr)``."""

        client = _FakeClient(addresses={"ui.set_window_visible_func": 0x00600000})
        self._patch(client)
        UIManager.SetWindowVisible(5, True)
        self.assertEqual(
            client.calls[0],
            ("ui.set_window_visible_func", CallForm.U32_U32_U32_U32, (5, 1, 0, 0)),
        )
        UIManager.SetWindowVisible(0x66, True)
        self.assertEqual(len(client.calls), 1, "ui.h:109: the bound is 0x66")

    def test_draw_on_compass_places_the_points_and_passes_the_count(self) -> None:
        """``ui_methods.cpp:1706-1712``: ``(session_id, point_count, points)``."""

        client = _FakeClient(addresses={"ui.draw_on_compass_func": 0x00601000})
        self._patch(client)
        self.assertTrue(UIManager.DrawOnCompass(4, [(1, 2), (3, 4)]))
        self.assertEqual(client.bridge.writes[0][1], struct.pack("<iiii", 1, 2, 3, 4))
        self.assertEqual(
            client.calls[0],
            ("ui.draw_on_compass_func", CallForm.U32_U32_U32, (4, 2, 0x70000000 + 0x400)),
        )
        client2 = _FakeClient()
        self._patch(client2)
        self.assertFalse(UIManager.DrawOnCompass(4, [(1, 2)]), "no function, no call")

    def test_load_settings_hands_over_the_size_and_the_bytes(self) -> None:
        client = _FakeClient(addresses={"ui.load_settings_func": 0x00602000})
        self._patch(client)
        UIManager.LoadSettings([1, 2, 3])
        self.assertEqual(client.bridge.writes[0][1], b"\x01\x02\x03")
        self.assertEqual(
            client.calls[0],
            ("ui.load_settings_func", CallForm.U32_U32, (3, 0x70000000 + 0xC40)),
        )

    def test_keydown_sends_the_key_packet_to_the_frames_callbacks(self) -> None:
        """``ui_methods.cpp:1408-1411``: a one-word ``KeyAction`` as ``kKeyDown``, to the frame."""

        pointer = 0x00200000
        client = _FakeClient(
            addresses={"ui.send_frame_ui_message_func": 0x00603000},
            frame_pointer=pointer,
            callbacks_size=1,
        )
        self.assertTrue(is_valid_frame_pointer(pointer))
        self._patch(client)
        UIManager.Keydown(0x1B, 1)
        self.assertEqual(client.bridge.writes[0][1], struct.pack("<I", 0x1B))
        self.assertEqual(
            client.calls[0],
            (
                "ui.send_frame_ui_message_func",
                CallForm.FASTCALL_U32_U32_U32,
                (
                    pointer + FrameStruct.frame_callbacks.offset,
                    0,
                    ui_manager_module._K_KEY_DOWN,
                    0x70000000 + 0xC20,
                    0,
                ),
            ),
        )

    def test_keydown_with_no_frame_id_walks_to_the_button_action_frame(self) -> None:
        """``frame_id == 0`` is the client's button-action frame: ``GetFrameByLabel(L"Game")``
        (``ui_methods.cpp:542-546`` + ``:556-568``) and then ``GetChildFrame(frame, 6)``
        (``:589-607``, ``g_get_child_frame_id_func``). The chain is asserted call by call, in
        native's own order, and then the key packet goes to the frame the walk answered.
        """

        hash_value = 0xDEADBEEF
        parent = 101
        target = 202
        pointer = 0x00200000
        client = _FakeClient(
            addresses={
                "ui.send_frame_ui_message_func": 0x00603000,
                "ui.create_hash_from_wchar_func": 0x00604000,
                "ui.get_child_frame_id_func": 0x00605000,
            },
            frame_pointer=pointer,
            callbacks_size=1,
        )
        client.values["ui.create_hash_from_wchar_func"] = hash_value
        client.values["ui.get_child_frame_id_func"] = target
        client.frame_array.parent_by_hash[hash_value] = parent
        self._patch(client)

        UIManager.Keydown(0x1B, 0)

        offset, payload = client.bridge.writes[0]
        self.assertEqual(offset, 0xB00, "the label is placed for the client to hash")
        self.assertEqual(payload, "Game".encode("utf-16-le") + b"\x00\x00")
        self.assertEqual(
            client.calls[0],
            ("ui.create_hash_from_wchar_func", CallForm.U32_U32, (0x70000000 + 0xB00, 0xFFFFFFFF)),
            "the label's hash, with native's -1",
        )
        self.assertEqual(
            client.calls[1],
            ("ui.get_child_frame_id_func", CallForm.U32_U32, (parent, 6)),
            "the button-action frame's child",
        )
        self.assertEqual(client.calls[2][0], "ui.send_frame_ui_message_func")
        self.assertEqual(client.calls[2][2][2], ui_manager_module._K_KEY_DOWN)
        self.assertEqual(client.calls[2][2][3], 0x70000000 + 0xC20, "the key packet")
        self.assertEqual(client.bridge.writes[1][1], struct.pack("<I", 0x1B))

    def test_keydown_with_no_frame_id_stops_when_the_label_does_not_resolve(self) -> None:
        """Every step of the walk answers 0 on failure, and no key is sent."""

        client = _FakeClient(
            addresses={
                "ui.send_frame_ui_message_func": 0x00603000,
                "ui.create_hash_from_wchar_func": 0x00604000,
                "ui.get_child_frame_id_func": 0x00605000,
            },
            frame_pointer=0x00200000,
            callbacks_size=1,
        )
        self._patch(client)
        UIManager.Keyup(0x1B, 0)
        self.assertEqual(
            [call[0] for call in client.calls],
            ["ui.create_hash_from_wchar_func"],
            "the hasher answered 0, so the walk ends there",
        )

        client2 = _FakeClient(
            addresses={
                "ui.send_frame_ui_message_func": 0x00603000,
                "ui.create_hash_from_wchar_func": 0x00604000,
                "ui.get_child_frame_id_func": 0x00605000,
            },
            frame_pointer=0x00200000,
            callbacks_size=1,
        )
        client2.values["ui.create_hash_from_wchar_func"] = 0xDEADBEEF
        self._patch(client2)
        UIManager.Keydown(0x1B, 0)
        self.assertEqual(
            [call[0] for call in client2.calls],
            ["ui.create_hash_from_wchar_func"],
            "the hash found no frame, so the child walk never runs",
        )

    def test_keypress_is_the_down_then_the_up(self) -> None:
        pointer = 0x00200000
        client = _FakeClient(
            addresses={"ui.send_frame_ui_message_func": 0x00603000},
            frame_pointer=pointer,
            callbacks_size=1,
        )
        self._patch(client)
        UIManager.Keypress(0x1B, 1)
        self.assertEqual(
            [call[2][2] for call in client.calls],
            [ui_manager_module._K_KEY_DOWN, ui_manager_module._K_KEY_UP],
        )

    def test_set_fps_limit_writes_the_command_line_buffer_word(self) -> None:
        """``ui_methods.cpp:1862``: the FPS index of the command-line array. The member returns
        nothing — Reforged's ``SetFPSLimit`` (``:292-298``) discards the binding's answer."""

        buffer = 0x0050A000
        client = _FakeClient(addresses={"ui.command_line_number_buffer": buffer})
        self._patch(client)
        self.assertIsNone(UIManager.SetFPSLimit(45))
        offset, payload = client.bridge.writes[0]
        self.assertEqual(payload, struct.pack("<I", 45))
        self.assertEqual(offset, 0x280)
        operation, target, region, size = client.bridge.commands[0]
        self.assertEqual(int(operation), int(Operation.WRITE_MEMORY))
        self.assertEqual(target, buffer + 3 * 4, "NumberCommandLineParameter::FPS is 3")
        self.assertEqual((region, size), (0x280, 4))


# --------------------------------------------------------------------------
class _FakeFrame:
    """One dialog frame: what the dialog family reads of it."""

    def __init__(
        self,
        frame_id: int = 1,
        exists: bool = True,
        visible: bool = True,
        usable: bool = True,
        template_type: int = 1,
        rect: tuple[int, int, int, int] = (0, 0, 0, 0),
    ) -> None:
        self.frame_id = frame_id
        self.exists = exists
        self.is_visible = visible
        self.is_usable = usable
        self.template_type = template_type
        self.rect = rect
        self.clicks = 0
        self.parent_frame: "_FakeFrame" = self

    def click(self) -> None:
        self.clicks += 1

    def parent(self) -> "_FakeFrame":
        return self.parent_frame


class _FakeFrameTree:
    """The tree reads the dialog family makes."""

    def __init__(self, path: list[_FakeFrame], descendants: list[_FakeFrame]) -> None:
        self._path = path
        self._descendants = descendants

    def frames_at_path(self, anchor: int, codes: list[int]) -> list[_FakeFrame]:
        return self._path

    def descendants(self, frame: Any) -> list[_FakeFrame]:
        return self._descendants

    def sort_by_vertical(self, frames: list[_FakeFrame]) -> list[_FakeFrame]:
        return list(frames)

    def children_map(self) -> dict[int, list[int]]:
        return {}


class UIManagerDialogTests(unittest.TestCase):
    """The dialog family: the source's own walk, its guards, and `Frame.click`."""

    def setUp(self) -> None:
        """``DIALOG_CHILD_OFFSET`` is module state — ``FindDialogOffset`` writes it — so it is put
        back after every test here, or one test's walk would decide another's constant."""

        self._offset = list(ui_manager_module.DIALOG_CHILD_OFFSET)
        self.addCleanup(self._restore_offset)

    def _restore_offset(self) -> None:
        ui_manager_module.DIALOG_CHILD_OFFSET[:] = self._offset

    def _patch(self, frames: dict[Any, _FakeFrame], tree: _FakeFrameTree) -> None:
        def factory(key: Any) -> _FakeFrame:
            return frames.get(key, _FakeFrame(exists=False))

        for target, value in (
            ("py4gw.ui_manager.Frame", factory),
            ("py4gw.ui_manager.FrameTree", tree),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_two_visibility_members_are_frame_usability(self) -> None:
        root = _FakeFrame(usable=True)
        chest = _FakeFrame(usable=False)
        self._patch(
            {ui_manager_module.FrameId.NpcDialog: root,
             ui_manager_module.FrameId.NpcDialog.UseLockpickButton: chest},
            _FakeFrameTree([], []),
        )
        self.assertTrue(UIManager.IsNPCDialogVisible())
        self.assertFalse(UIManager.IsLockedChestWindowVisible())

    def test_get_dialog_buttons_is_the_offset_walk_then_the_fallback(self) -> None:
        buttons = [_FakeFrame(frame_id=1, template_type=1), _FakeFrame(frame_id=2, template_type=2)]
        self._patch({}, _FakeFrameTree(buttons, buttons))
        self.assertEqual([f.frame_id for f in UIManager.GetDialogButtons()], [1])

    def test_click_dialog_button_is_one_based_and_bounded(self) -> None:
        buttons = [_FakeFrame(frame_id=7, template_type=1), _FakeFrame(frame_id=8, template_type=1)]
        self._patch({}, _FakeFrameTree(buttons, buttons))
        self.assertTrue(UIManager.ClickDialogButton(2))
        self.assertEqual((buttons[0].clicks, buttons[1].clicks), (0, 1))
        self.assertFalse(UIManager.ClickDialogButton(0))
        self.assertFalse(UIManager.ClickDialogButton(3))

    def test_get_dialog_button_count_is_the_list_length(self) -> None:
        buttons = [_FakeFrame(template_type=1), _FakeFrame(template_type=1)]
        self._patch({}, _FakeFrameTree(buttons, buttons))
        self.assertEqual(UIManager.GetDialogButtonCount(), 2)

    def test_get_dialog_button_frames_pairs_each_handle_with_its_rect(self) -> None:
        """The source returns the ``(Frame, rect)`` pair, not the frame's id (``:547-551``)."""

        buttons = [_FakeFrame(frame_id=3, template_type=1, rect=(5, 6, 7, 8))]
        self._patch({}, _FakeFrameTree(buttons, buttons))
        self.assertEqual(UIManager.GetDialogButtonFrames(), [(buttons[0], (5, 6, 7, 8))])

    def test_confirm_max_amount_clicks_the_buttons_that_exist(self) -> None:
        max_button = _FakeFrame(exists=True)
        ok_button = _FakeFrame(exists=False)
        self._patch(
            {ui_manager_module.FrameId.MaxButton: max_button,
             ui_manager_module.FrameId.OkButton: ok_button},
            _FakeFrameTree([], []),
        )
        UIManager.ConfirmMaxAmountDialog()
        self.assertEqual((max_button.clicks, ok_button.clicks), (1, 0))

    def test_find_dialog_offset_walks_the_tree_and_writes_the_global(self) -> None:
        """The source's own BFS (``:416-454``): the path it builds is the global it assigns.

        The fixture gives the walk a container whose two children are both visible buttons, so the
        "most ``template_type == 1`` children" rule picks it and the path back up to the root is one
        sibling index.
        """

        root = _FakeFrame(frame_id=100)
        container = _FakeFrame(frame_id=101, template_type=2)
        buttons = [_FakeFrame(frame_id=102), _FakeFrame(frame_id=103)]
        container.parent_frame = root
        by_id = {101: container, 102: buttons[0], 103: buttons[1]}

        class _Factory:
            """``Frame`` as the walk uses it: a constructor for the root, ``from_id`` below it."""

            def __call__(self, key: Any) -> _FakeFrame:
                return root

            @staticmethod
            def from_id(frame_id: int) -> _FakeFrame:
                return by_id[int(frame_id)]

        class _Tree(_FakeFrameTree):
            def children_map(self) -> dict[int, list[int]]:
                return {100: [101], 101: [102, 103]}

        patchers = [
            mock.patch("py4gw.ui_manager.Frame", _Factory()),
            mock.patch("py4gw.ui_manager.FrameTree", _Tree([], [])),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        UIManager.FindDialogOffset()
        self.assertEqual(ui_manager_module.DIALOG_CHILD_OFFSET, [0])
        self.assertIsNot(ui_manager_module.DIALOG_CHILD_OFFSET, ui_manager_module.DEFAULT_OFFSET)


class UIManagerPreferenceSetterTests(unittest.TestCase):
    """The three typed setters: native's own guard, validation, write and follow-up calls.

    ``SetPreference``'s bodies (``ui_methods.cpp:1468-1677``) live in ``py4gw/ui/preferences.py`` —
    the home this port keeps the ``GW::ui`` preference functions in — and each ``UIManager`` member
    is the source's one-line wrapper over it, so the checks here drive both levels.
    """

    PREFERENCES_INITIALIZED = 0x00510000
    ENUM_OPTIONS = 0x00511000
    ENUM_VALUES = 0x00513000
    NUMBER_OPTIONS = 0x00512000
    CLAMP_PROC = 0x00640000

    def _client(
        self,
        *,
        options: tuple[int, ...] = (0, 1, 2, 3),
        preference: int = 1,
        number_flags: int = 0,
        renderer_mode: int = 0,
    ) -> _FakeClient:
        addresses = {
            "ui.preferences_initialized_addr": self.PREFERENCES_INITIALIZED,
            "ui.enum_preference_options_addr": self.ENUM_OPTIONS,
            "ui.number_preference_options_addr": self.NUMBER_OPTIONS,
            "ui.get_enum_preference_func": 0x00610000,
            "ui.get_number_preference_func": 0x00611000,
            "ui.get_flag_preference_func": 0x00612000,
            "ui.get_game_renderer_mode_func": 0x00613000,
            "ui.set_enum_preference_func": 0x00620000,
            "ui.set_number_preference_func": 0x00621000,
            "ui.set_string_preference_func": 0x00621500,
            "ui.set_flag_preference_func": 0x00622000,
            "ui.set_graphics_renderer_value_func": 0x00630000,
            "ui.set_game_renderer_mode_func": 0x00631000,
            "ui.set_volume_func": 0x00632000,
            "ui.set_master_volume_func": 0x00633000,
            "ui.set_in_game_static_preference_func": 0x00634000,
            "ui.set_in_game_shadow_quality_func": 0x00635000,
            "ui.set_in_game_ui_scale_func": 0x00636000,
            "ui.trigger_terrain_rerender_func": 0x00637000,
        }
        spans = {
            self.PREFERENCES_INITIALIZED: struct.pack("<I", 1),
            self.ENUM_OPTIONS + preference * 0x14: struct.pack(
                "<IIIII", 0, len(options), self.ENUM_VALUES, 0, 0
            ),
            self.ENUM_VALUES: b"".join(struct.pack("<I", value) for value in options),
        }
        #: The number-preference info array is one span long enough for every index, with the
        #: flags and the clamp pointer at the entry the clamp test asks about.
        number_options = bytearray(44 * 0x18)
        number_options[8 * 0x18 + 0x4 : 8 * 0x18 + 0x8] = struct.pack("<I", number_flags)
        number_options[8 * 0x18 + 0x10 : 8 * 0x18 + 0x14] = struct.pack("<I", self.CLAMP_PROC)
        spans[self.NUMBER_OPTIONS] = bytes(number_options)
        client = _FakeClient(addresses=addresses, spans=spans)
        client.address_value = 0
        client.values["ui.get_game_renderer_mode_func"] = renderer_mode
        return client

    def _patch(self, client: _FakeClient) -> None:
        patcher = mock.patch("py4gw.client.require_client", return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_set_enum_preference_validates_rewrites_writes_and_follows_up(self) -> None:
        """``ui_methods.cpp:1479-1537``: the option-list scan, the ``2 -> 1`` rewrite for
        anti-aliasing, the write, then the two renderer values re-read from the client.
        """

        from py4gw.ui import preferences

        client = self._client(options=(0, 1, 2, 3), preference=1)
        client.values["ui.get_enum_preference_func"] = 3
        self._patch(client)
        preferences.set_enum_preference(1, 2)
        self.assertEqual(
            client.calls[0],
            ("ui.set_enum_preference_func", CallForm.U32_U32, (1, 1)),
            "AntiAliasing 2 is written as 1",
        )
        self.assertEqual(
            client.calls[1:],
            [
                ("ui.get_enum_preference_func", CallForm.U32, (1,)),
                ("ui.set_graphics_renderer_value_func", CallForm.U32_U32_U32_U32, (0, 2, 5, 3)),
                ("ui.set_graphics_renderer_value_func", CallForm.U32_U32_U32_U32, (0, 0, 5, 3)),
            ],
            "the follow-up re-reads the preference and drives both renderer paths",
        )

    def test_set_enum_preference_refuses_a_value_the_client_does_not_offer(self) -> None:
        from py4gw.ui import preferences

        client = self._client(options=(0, 1, 3), preference=6)
        self._patch(client)
        self.assertFalse(preferences.set_enum_preference(6, 9))
        self.assertEqual(client.calls, [], "no write, no follow-up")

    def test_a_client_without_the_preferences_is_refused(self) -> None:
        from py4gw.ui import preferences

        client = self._client()
        self._patch(client)
        client._spans[self.PREFERENCES_INITIALIZED] = struct.pack("<I", 0)
        self.assertFalse(preferences.set_enum_preference(1, 1))
        self.assertFalse(preferences.set_number_preference(8, 50))
        self.assertFalse(preferences.set_flag_preference(0x2E, True))
        self.assertEqual(client.calls, [])

    def test_set_number_preference_clamps_through_the_clients_own_proc(self) -> None:
        """``ui_methods.cpp:385-395``: ``flags & 0x1`` and the entry's ``clamp_proc``."""

        from py4gw.ui import preferences

        client = self._client(number_flags=0x1)
        client.address_value = 77
        client.values["ui.get_number_preference_func"] = 77
        self._patch(client)
        preferences.set_number_preference(8, 500)
        self.assertEqual(
            client.calls[0],
            (f"address:{self.CLAMP_PROC:#x}", CallForm.U32_U32, (8, 500)),
            "the clamp is the client's own function pointer",
        )
        self.assertEqual(client.calls[1][0], "ui.set_number_preference_func")
        self.assertEqual(client.calls[1][2], (8, 77), "the clamped value is what is written")

    def test_a_volume_preference_drives_its_own_channel_and_the_float_word(self) -> None:
        """``ui_methods.cpp:1566``: ``g_set_volume_func(0, current / 100.f)`` for effects volume."""

        from py4gw.ui import preferences

        client = self._client()
        client.values["ui.get_number_preference_func"] = 50
        self._patch(client)
        preferences.set_number_preference(preferences.NP_EFFECTS_VOLUME, 50)
        half = struct.unpack("<I", struct.pack("<f", 0.5))[0]
        self.assertEqual(client.calls[1], ("ui.get_number_preference_func", CallForm.U32, (24,)))
        self.assertEqual(
            client.calls[2],
            ("ui.set_volume_func", CallForm.U32_U32, (0, half)),
        )

    def test_the_python_table_and_native_disagree_about_two_volume_members(self) -> None:
        """The finding this round pinned: native's (and GWCA's) ``EffectsVolume`` is ``24`` and
        ``BackgroundVolume`` is ``26``, while Reforged's ``enums_src/UI_enums.py:387-389`` — ported
        verbatim into ``enums_src/ui_enums.py`` — has them the other way round. The switch is
        native's own body, so the *number* a Reforged caller passes reaches the other branch: ``24``
        drives channel ``0`` (native's effects) and ``26`` drives channel ``1`` (native's
        background).
        """

        from py4gw.enums_src import ui_enums
        from py4gw.ui import preferences

        self.assertEqual(ui_enums.NumberPreference.BackgroundVolume, 24)
        self.assertEqual(ui_enums.NumberPreference.EffectsVolume, 26)
        self.assertEqual(preferences.NP_EFFECTS_VOLUME, 24)
        self.assertEqual(preferences.NP_BACKGROUND_VOLUME, 26)
        self.assertEqual(ui_enums.NumberPreference.Count, 41)
        self.assertEqual(preferences.NUMBER_PREFERENCE_COUNT, 44)

        client = self._client()
        client.values["ui.get_number_preference_func"] = 100
        self._patch(client)
        preferences.set_number_preference(24, 100)
        self.assertEqual(client.calls[2][2][0], 0, "24 is native's effects channel")
        client.calls.clear()
        preferences.set_number_preference(26, 100)
        self.assertEqual(client.calls[2][2][0], 1, "26 is native's background channel")

    def test_set_bool_preference_is_windowed_reads_then_writes_the_renderer_mode(self) -> None:
        """``ui_methods.cpp:1664-1672``: the mode is only written when it differs."""

        from py4gw.ui import preferences

        client = self._client(renderer_mode=0)
        self._patch(client)
        preferences.set_flag_preference(preferences.FLAG_IS_WINDOWED, True)
        self.assertEqual(
            client.calls[0],
            ("ui.set_flag_preference_func", CallForm.U32_U32, (0x2E, 1)),
        )
        self.assertEqual(
            client.calls[1:],
            [
                ("ui.get_game_renderer_mode_func", CallForm.U32, (0,)),
                ("ui.set_game_renderer_mode_func", CallForm.U32_U32, (0, 2)),
            ],
        )

        client2 = self._client(renderer_mode=2)
        self._patch(client2)
        preferences.set_flag_preference(preferences.FLAG_IS_WINDOWED, True)
        self.assertEqual(len(client2.calls), 2, "the mode already matches, so it is not written")

    def test_set_string_preference_places_the_wide_text_and_passes_its_address(self) -> None:
        """``ui_methods.cpp:1639-1651``: the guard, then ``g_set_string_preference_func(pref,
        value)`` over the caller's own wide buffer (``ui_bindings.cpp:1055-1057``).

        The port's transport is the block's data region — memory inside the client — so the test
        asserts the bytes that land there are UTF-16 code units plus the terminator the
        ``std::wstring`` keeps, and that the address is what the call carries.
        """

        from py4gw.ui import preferences

        client = self._client()
        self._patch(client)
        self.assertIsNone(UIManager.SetStringPreference(1, "Guild Wars"))
        offset, payload = client.bridge.writes[0]
        self.assertEqual(offset, 0xD00)
        self.assertEqual(payload, "Guild Wars".encode("utf-16-le") + b"\x00\x00")
        self.assertEqual(
            client.calls[0],
            ("ui.set_string_preference_func", CallForm.U32_U32, (1, 0x70000000 + 0xD00)),
        )

    def test_set_string_preference_is_refused_without_the_client_side(self) -> None:
        from py4gw.ui import preferences

        client = self._client()
        client._addresses.pop("ui.set_string_preference_func")
        self._patch(client)
        self.assertFalse(preferences.set_string_preference(1, "x"))
        self.assertEqual(client.bridge.writes, [], "nothing is placed when the call cannot be made")

    def test_the_members_are_the_sources_wrappers_over_those_bodies(self) -> None:
        """``UIManager``'s three setters call the preferences functions and return nothing — the
        source's own annotations are ``-> None`` (``UIManager.py:322,326,334``)."""

        client = self._client()
        self._patch(client)
        self.assertIsNone(UIManager.SetEnumPreference(1, 1))
        self.assertIsNone(UIManager.SetIntPreference(8, 50))
        self.assertIsNone(UIManager.SetBoolPreference(0x2E, True))
        written = [call[0] for call in client.calls]
        self.assertIn("ui.set_enum_preference_func", written)
        self.assertIn("ui.set_number_preference_func", written)
        self.assertIn("ui.set_flag_preference_func", written)
        self.assertEqual(
            written[0], "ui.set_enum_preference_func", "the source's own member order"
        )


class UIManagerKeyMappingTests(unittest.TestCase):
    """The client's key-remap table: the ``0x75``-word read, and the bounded write.

    The table's address comes from the catalog (``ui.key_mappings_table``, derived offline by
    ``tools/key_mappings_hunt.py``); a fixture answers it with a span, so the member's own arithmetic
    is what is under test.
    """

    TABLE = 0x00C14C58
    WORDS = 0x75

    def _client(self, resolvable: bool = True) -> _FakeClient:
        addresses = {"ui.key_mappings_table": self.TABLE} if resolvable else {}
        span = b"".join(struct.pack("<I", index) for index in range(self.WORDS))
        return _FakeClient(addresses=addresses, spans={self.TABLE: span})

    def _patch(self, client: _FakeClient) -> None:
        patcher = mock.patch("py4gw.client.require_client", return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_key_mappings_reads_the_table_the_resolver_derived(self) -> None:
        client = self._client()
        self._patch(client)
        mappings = UIManager.GetKeyMappings()
        self.assertEqual(len(mappings), self.WORDS)
        self.assertEqual(mappings[:4], [0, 1, 2, 3])
        self.assertEqual(mappings[-1], self.WORDS - 1)

    def test_get_key_mappings_answers_empty_without_the_table(self) -> None:
        """The older runtime's own answer when its scan found nothing: an empty vector."""

        self._patch(self._client(resolvable=False))
        self.assertEqual(UIManager.GetKeyMappings(), [])

    def test_set_key_mappings_writes_the_min_of_the_table_and_the_list(self) -> None:
        """``min(0x75, len(mappings))`` words into the client, on the game's own thread."""

        client = self._client()
        self._patch(client)
        UIManager.SetKeyMappings([7, 8, 9])
        offset, payload = client.bridge.writes[0]
        self.assertEqual(offset, 0x900)
        self.assertEqual(payload, struct.pack("<III", 7, 8, 9))
        operation, target, region, size = client.bridge.commands[0]
        self.assertEqual(int(operation), int(Operation.WRITE_MEMORY))
        self.assertEqual(target, self.TABLE)
        self.assertEqual((region, size), (0x900, 12))

    def test_set_key_mappings_truncates_a_longer_list_at_the_table(self) -> None:
        client = self._client()
        self._patch(client)
        UIManager.SetKeyMappings(list(range(self.WORDS + 5)))
        _, payload = client.bridge.writes[0]
        self.assertEqual(len(payload), self.WORDS * 4, "the table's own size is the bound")

    def test_set_key_mappings_writes_nothing_for_an_empty_list(self) -> None:
        """``std::copy`` over ``min(...) == 0`` copies nothing — and the scan is not repeated."""

        client = self._client()
        self._patch(client)
        UIManager.SetKeyMappings([])
        self.assertEqual(client.bridge.writes, [])
        self.assertEqual(client.bridge.commands, [])


if __name__ == "__main__":
    unittest.main()
