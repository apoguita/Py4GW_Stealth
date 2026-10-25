"""Offline checks for the packet sniffer: the facade, the decoder, and the capture stub.

Two kinds of test live here and they are deliberately different.

* The **decoder** is pure Python over bytes, so it is tested against the source's own tables and
  against captures written out by hand — nothing about it needs a client, and a wrong field name or a
  wrong offset is caught here.
* The **capture stub** is machine code, so it is **executed**: allocated as executable memory in the
  test process, copied there, and called against a fake block exactly as the client's dispatcher
  would call it. That is the same discipline ``tests/test_payload_offline.py`` holds its stubs to,
  and it is the only way to check that emitted code walks a field template the way native's walk does.
"""

from __future__ import annotations

import ctypes
import struct
import unittest
from dataclasses import dataclass

import py4gw.packet_sniffer as packet_sniffer
from py4gw.client import _entry_span
from py4gw.game_thread import payload
from py4gw.game_thread import shared_block as sb
from py4gw.game_thread.packets import (
    FieldKind,
    decode_field_kind,
    describe_template,
)
from py4gw.native_src.packets import py_packet_sniffer as binding

_SNIFFER = packet_sniffer.SNIFFER


class DecoderTablesTests(unittest.TestCase):
    """The four tables are the source's, which is what every answer below is built from."""

    def test_the_tables_are_the_sources(self) -> None:
        self.assertEqual(len(packet_sniffer.STOC_HEADER_NAMES), 247)
        self.assertEqual(len(packet_sniffer.GENERIC_VALUE_IDS), 13)
        self.assertEqual(len(packet_sniffer.KNOWN_CTOS_LENGTHS), 12)
        self.assertEqual(len(packet_sniffer.NAME_RE_STOC_HEADERS), 15)

        # The same entries Reforged declares, at the values it declares them at.
        self.assertEqual(packet_sniffer.STOC_HEADER_NAMES[0x0084], "WINDOW_ADD_ITEMS")
        self.assertEqual(packet_sniffer.STOC_HEADER_NAMES[0x009F], "AGENT_PROPERTY_UPDATE_INT")
        self.assertEqual(packet_sniffer.STOC_HEADER_NAMES[0x01E1], "PARTY_SEARCH_TYPE")
        self.assertEqual(packet_sniffer.GENERIC_VALUE_IDS[58], "skill_finished")
        self.assertEqual(packet_sniffer.KNOWN_CTOS_LENGTHS[0x45], 264)
        self.assertIn(0x017D, packet_sniffer.NAME_RE_STOC_HEADERS)

    def test_a_name_that_is_not_in_the_table_is_the_hex_of_the_header(self) -> None:
        """``get_packet_name``'s fallback is ``f'0x{header:04X}'`` for both directions."""

        self.assertEqual(_SNIFFER.get_packet_name("StoC", 0xFFFF), "0xFFFF")
        self.assertEqual(_SNIFFER.get_packet_name("CToS", 0x1234), "0x1234")
        self.assertEqual(_SNIFFER.get_packet_name("CToS", 0x39), "INTERACT_LIVING")


class DirectionTests(unittest.TestCase):
    """``_normalize_direction`` is the source's own check, including its refusal."""

    def test_the_three_spellings_are_kept(self) -> None:
        for direction in ("CToS", "StoC", "both"):
            with self.subTest(direction=direction):
                self.assertEqual(_SNIFFER._normalize_direction(direction), direction)

    def test_anything_else_is_refused_with_the_sources_message(self) -> None:
        with self.assertRaises(ValueError) as caught:
            _SNIFFER._normalize_direction("both " if True else "StoC")  # type: ignore[arg-type]
        self.assertIn("Unsupported packet direction", str(caught.exception))


class StoCDecoderTests(unittest.TestCase):
    """``_decode_stoc_packet``'s header-specific branches, over bytes written by hand."""

    def decode(self, header: int, raw: bytes) -> str:
        return _SNIFFER.decode_packet("StoC", header, len(raw), raw)

    def test_the_generic_int_packet_names_its_type(self) -> None:
        raw = struct.pack("<4I", 0x009F, 60, 0x1234, 7)
        self.assertEqual(
            self.decode(0x009F, raw),
            "AGENT_PROPERTY_UPDATE_INT size=16 | type=skill_activated, agent_id=4660, value=7",
        )

    def test_the_generic_float_packet_reads_a_float(self) -> None:
        raw = struct.pack("<3I", 0x00A2, 3, 0x99) + struct.pack("<f", 1.5)
        text = self.decode(0x00A2, raw)
        self.assertIn("type=3", text)
        self.assertIn("agent_id=153", text)
        self.assertIn("value=1.5", text)

    def test_a_move_packet_carries_its_two_floats(self) -> None:
        """``{0x0029, 0x002B, 0x002E}`` is the source's own set for the mover branch (``:521``).

        The branch is gated on ``len(raw) >= 16`` — it reads two floats at offsets 8 and 12 — so a
        twelve-byte packet falls through to the base line, which is the source's behaviour and not a
        truncation of it.
        """

        raw = struct.pack("<IIff", 0x0029, 0, 100.5, -20.25)
        self.assertEqual(
            self.decode(0x0029, raw),
            "AGENT_MOVE_TO_POINT size=16 | agent_id=0, x=100.5, y=-20.25",
        )
        self.assertEqual(self.decode(0x0029, raw[:12]), "AGENT_MOVE_TO_POINT size=12")

    def test_a_name_probe_header_finds_the_utf16_run(self) -> None:
        """``NAME_RE_STOC_HEADERS`` takes the probe path: printable UTF-16 runs, and the length."""

        name = "Apo Son".encode("utf-16-le") + b"\x00\x00"
        raw = struct.pack("<I", 0x0031) + bytes(8) + name
        text = self.decode(0x0031, raw)
        self.assertIn("CHARACTER_UPDATE_NAME", text)
        self.assertIn("body_len=24", text)
        self.assertIn("utf16=@12='Apo Son'", text)

    def test_a_known_packet_with_no_decoder_is_its_name_and_size(self) -> None:
        raw = struct.pack("<2I", 0x001E, 5)
        self.assertEqual(
            self.decode(0x001E, raw),
            "WORLD_SIMULATION_TICK size=8 | delta_or_tick=5",
        )


class CToSDecoderTests(unittest.TestCase):
    """``_decode_ctos_packet``'s branches, including the subpacket scan."""

    def decode(self, header: int, raw: bytes) -> str:
        return _SNIFFER.decode_packet("CToS", header, len(raw), raw)

    def test_interact_living_is_the_agent_and_its_flag(self) -> None:
        raw = struct.pack("<3I", 0x39, 0x40000001, 0)
        self.assertEqual(
            self.decode(0x39, raw), "INTERACT_LIVING size=12 | agent_id=1073741825, flag=0"
        )

    def test_a_use_skill_packet_reads_four_words(self) -> None:
        raw = struct.pack("<5I", 0x46, 12, 0, 0x40000001, 1)
        self.assertEqual(
            self.decode(0x46, raw),
            "USE_SKILL size=20 | skill_id=12, type=0, target_id=1073741825, flags=1",
        )

    def test_a_stream_fragment_finds_the_subpackets_inside_it(self) -> None:
        """``_find_known_subpackets`` walks 2-byte-aligned words for a header it can name."""

        raw = struct.pack("<3I", 0x00C1, 0x0026, 0) + bytes(4)
        text = self.decode(0x00C1, raw)
        self.assertIn("TRAVEL_INIT", text)
        self.assertIn("u32_1=38", text)

    def test_an_unknown_stream_fragment_is_scanned_and_then_probed(self) -> None:
        raw = struct.pack("<4I", 0x00FF, 0xDEADBEEF, 0, 0)
        text = self.decode(0x00FF, raw)
        self.assertIn("size=16", text)
        self.assertIn("body_len=12", text)


class EntryConversionTests(unittest.TestCase):
    """``_convert_entry`` over the binding's record, which is what the facade hands back."""

    def test_the_binding_entry_becomes_this_projects_record(self) -> None:
        native = binding.PacketLogEntry(
            tick=1234,
            direction=binding.PacketDirection.CToS,
            header=0x39,
            size=12,
            data=b"\x39\x00\x00\x00",
        )
        entry = packet_sniffer.PacketSniffer._convert_entry(native)
        self.assertEqual(entry.direction, "CToS")
        self.assertEqual(entry.tick, 1234)
        self.assertEqual(entry.header, 0x39)
        self.assertEqual(entry.size, 12)
        self.assertEqual(entry.data, b"\x39\x00\x00\x00")

    def test_stoc_is_the_other_direction(self) -> None:
        native = binding.PacketLogEntry(
            direction=binding.PacketDirection.StoC, header=0x84, size=36
        )
        self.assertEqual(
            packet_sniffer.PacketSniffer._convert_entry(native).direction, "StoC"
        )

    def test_the_record_is_frozen(self) -> None:
        entry = packet_sniffer.PacketLogEntry(
            direction="StoC", tick=0, header=0, size=0, data=b""
        )
        with self.assertRaises(Exception):
            entry.header = 1  # type: ignore[misc]


class LogTests(unittest.TestCase):
    """``LogPacket`` and the ``Get*Logs``/``ClearLogs`` pair, which is ``g_logs`` under its mutex."""

    def setUp(self) -> None:
        binding.ClearLogs()

    def tearDown(self) -> None:
        binding.ClearLogs()

    def entry(self, header: int, direction: binding.PacketDirection) -> binding.PacketLogEntry:
        return binding.PacketLogEntry(
            tick=0, direction=direction, header=header, size=4, data=b"\0\0\0\0"
        )

    def test_the_log_keeps_order_and_copies_on_read(self) -> None:
        for header in (0x84, 0x85):
            binding.LogPacket(self.entry(header, binding.PacketDirection.StoC))
        logs = binding.GetLogs()
        self.assertEqual([entry.header for entry in logs], [0x84, 0x85])
        logs.append(self.entry(0x86, binding.PacketDirection.StoC))
        self.assertEqual(len(binding.GetLogs()), 2)

    def test_the_oldest_entry_is_dropped_past_the_cap(self) -> None:
        """``while (g_logs.size() > kMaxLogs) g_logs.erase(g_logs.begin())`` (``:19-21``)."""

        for index in range(binding.K_MAX_LOGS + 3):
            binding.LogPacket(self.entry(index, binding.PacketDirection.StoC))
        logs = binding.GetLogs()
        self.assertEqual(len(logs), binding.K_MAX_LOGS)
        self.assertEqual(logs[0].header, 3)

    def test_the_direction_filters_and_clears_are_per_direction(self) -> None:
        binding.LogPacket(self.entry(1, binding.PacketDirection.StoC))
        binding.LogPacket(self.entry(2, binding.PacketDirection.CToS))
        binding.LogPacket(self.entry(3, binding.PacketDirection.StoC))

        self.assertEqual(
            [entry.header for entry in binding.GetLogsByDirection(binding.PacketDirection.StoC)],
            [1, 3],
        )
        binding.ClearLogsByDirection(binding.PacketDirection.StoC)
        self.assertEqual(
            [entry.header for entry in binding.GetLogs()], [2]
        )
        binding.ClearLogs()
        self.assertEqual(binding.GetLogs(), [])

    def test_a_recorded_packet_becomes_a_log_entry(self) -> None:
        """The event a stub writes is what ``LogPacket`` is handed, for either direction."""

        event = sb.EventRecord(
            kind=sb.EventKind.PACKET,
            sequence=0x39,
            arg0=sb.PACKET_DIRECTION_CTOS,
            arg1=12,
            capture=struct.pack("<3I", 0x39, 7, 0),
        )
        binding._capture_record(event)
        entries = binding.GetLogs()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].direction, binding.PacketDirection.CToS)
        self.assertEqual(entries[0].header, 0x39)
        self.assertEqual(entries[0].size, 12)
        self.assertEqual(entries[0].data, event.capture)
        self.assertGreater(entries[0].tick, 0)

        inbound = sb.EventRecord(
            kind=sb.EventKind.PACKET,
            sequence=0x84,
            arg0=sb.PACKET_DIRECTION_STOC,
            arg1=36,
            capture=bytes(36),
        )
        binding._capture_record(inbound)
        self.assertEqual(binding.GetLogs()[-1].direction, binding.PacketDirection.StoC)

    def test_the_binding_repr_is_the_sources(self) -> None:
        entry = self.entry(0x84, binding.PacketDirection.StoC)
        self.assertEqual(repr(entry), "<Packet direction=StoC header=0x0084 size=4>")


class TemplateWalkTests(unittest.TestCase):
    """``describe_template`` — the template-only half of ``GetPacketSize``'s walk."""

    def test_the_header_word_is_skipped_and_the_widths_are_summed(self) -> None:
        # field 0 describes the header word, which the packet pointer already accounts for
        # (stoc_methods.cpp:246-248); the walk starts past it and the base is that word's four bytes.
        capture = describe_template((0x1, 0x0, 0x1, 0x2))
        self.assertEqual(capture.fixed_bytes, 4 + 4 + 4 + 8)
        self.assertFalse(capture.has_nested_struct)
        self.assertEqual(capture.cap, 512)

    def test_a_template_sized_region_uses_its_count(self) -> None:
        # string16 with count 3 (bits 8-23) is six bytes; array32 with count 2 is eight
        capture = describe_template((0x1, (3 << 8) | 0x7, (2 << 8) | 0xB | (4 << 4)))
        self.assertEqual(capture.fixed_bytes, 4 + 6 + 8)

    def test_ignore_fields_contribute_nothing(self) -> None:
        self.assertEqual(describe_template((0x1, 0x6, 0xA)).fixed_bytes, 4)

    def test_a_trailing_nested_struct_hands_the_repeat_to_the_stub(self) -> None:
        # header, agent id, then a nested struct of two words
        capture = describe_template((0x1, 0x0, 0xC, 0x4, 0x4))
        self.assertEqual(capture.fixed_bytes, 8)
        self.assertEqual(capture.nested_stride, 8)
        self.assertEqual(capture.repeat_offset, 8)
        self.assertTrue(capture.has_nested_struct)

    def test_a_nested_struct_inside_a_nested_struct_is_refused_by_name(self) -> None:
        with self.assertRaises(ValueError) as caught:
            describe_template((0x1, 0xC, 0xC))
        self.assertIn("nested struct", str(caught.exception))

    def test_every_descriptor_kind_is_decoded_as_native_decodes_it(self) -> None:
        cases = (
            (0x0, FieldKind.AgentId),
            (0x1, FieldKind.Float),
            (0x2, FieldKind.Vect2),
            (0x3, FieldKind.Vect3),
            (0x4, FieldKind.Fixed4),
            (0x8, FieldKind.Fixed4),
            (0x5, FieldKind.Blob),
            (0x9, FieldKind.Blob),
            (0x6, FieldKind.Ignore),
            (0xA, FieldKind.Ignore),
            (0x7, FieldKind.String16),
            (0xB | (1 << 4), FieldKind.Array8),
            (0xB | (2 << 4), FieldKind.Array16),
            (0xB | (4 << 4), FieldKind.Array32),
            (0xC, FieldKind.NestedStruct),
            (0xD, FieldKind.Unknown),
        )
        for descriptor, expected in cases:
            with self.subTest(descriptor=hex(descriptor)):
                self.assertEqual(decode_field_kind(descriptor), expected)


# -- the emitted capture, executed -------------------------------------------

kernel32 = ctypes.windll.kernel32
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = (
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_uint32,
    ctypes.c_uint32,
)
kernel32.VirtualFree.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32)

_MEM_COMMIT_RESERVE = 0x3000
_PAGE_EXECUTE_READWRITE = 0x40
_MEM_RELEASE = 0x8000


@dataclass
class _Buffer:
    """One span of memory the emitted code can write into, and read back through."""

    buffer: ctypes.Array

    @property
    def address(self) -> int:
        return ctypes.addressof(self.buffer)

    @property
    def raw(self) -> bytes:
        return bytes(self.buffer.raw)

    def write(self, offset: int, data: bytes) -> None:
        ctypes.memmove(self.address + offset, data, len(data))


class _Block(_Buffer):
    """A block with its counters readable, which is what the stubs advance."""

    def __init__(self) -> None:
        super().__init__(ctypes.create_string_buffer(sb.BLOCK_SIZE))
        image = sb.empty_block(0x5150)
        self.write(0, image)

    def header(self) -> sb.BlockHeader:
        return sb.read_header(self.raw[: sb.HEADER_SIZE])

    def event(self, index: int = 0) -> sb.EventRecord:
        start = sb.event_offset(index)
        return sb.EventRecord.from_bytes(self.raw[start : start + sb.EVENT_SIZE])


class _Code:
    """Emitted code placed in executable memory, freed when the test is done."""

    def __init__(self, code: bytes) -> None:
        self._address = int(
            kernel32.VirtualAlloc(
                None, len(code), _MEM_COMMIT_RESERVE, _PAGE_EXECUTE_READWRITE
            )
        )
        if not self._address:
            raise OSError("VirtualAlloc failed")
        ctypes.memmove(self._address, code, len(code))

    @property
    def address(self) -> int:
        return self._address

    def close(self) -> None:
        if self._address:
            kernel32.VirtualFree(self._address, 0, _MEM_RELEASE)
            self._address = 0

    def __enter__(self) -> '_Code':
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class CaptureStubTests(unittest.TestCase):
    """What the emitted capture does, by executing it.

    A packet handler is ``__cdecl`` and the client's dispatcher pushes the packet and calls it
    (``stoc_methods.cpp:7``), so the inbound stub is called with one argument. The outbound stub is
    the hooker's payload, which the stub calls as ``__stdcall(block, size, packet)``
    (``hooker.build_stub``'s forwarded arguments), so it is called that way here.
    """

    HEADER = 0x84

    def inbound(self, block: _Block, packet: _Buffer, capture) -> sb.EventRecord:
        code = payload.build_packet_stub(
            block.address, self.HEADER, 0, 0, capture=capture
        )
        with _Code(code) as stub:
            call = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p)(stub.address)
            self.assertEqual(call(packet.address), 1)
        return block.event(block.header().event_taken % sb.EVENT_DEPTH)

    def outbound(self, block: _Block, size: int, packet: _Buffer) -> sb.BlockHeader:
        """Run the send capture the way the hooker's stub calls it.

        The wrapper is ``void __cdecl SendPacket(void* ctx, uint32_t size, const void* packet)``
        (``packet_sniffer.h:51-52``), and the payload is entered with the block **first** and then the
        hooked function's own arguments in order (``hooker.build_stub``), so it is called with four
        words and pops sixteen bytes.
        """

        code = payload.build_send_capture_stub(block.address)
        with _Code(code) as stub:
            call = ctypes.WINFUNCTYPE(
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_void_p,
            )(stub.address)
            call(block.address, 0x00AB0000, size, packet.address)
        return block.header()

    def test_a_fixed_width_template_copies_exactly_its_bytes(self) -> None:
        block = _Block()
        packet = _Buffer(ctypes.create_string_buffer(600))
        body = struct.pack("<6I", self.HEADER, 0x11, 0x22, 0x33, 0x44, 0x55) + bytes(576)
        packet.write(0, body)

        event = self.inbound(block, packet, sb.PacketCapture(fixed_bytes=24))

        self.assertEqual(event.kind, sb.EventKind.PACKET)
        self.assertEqual(event.sequence, self.HEADER)
        self.assertEqual(event.arg0, sb.PACKET_DIRECTION_STOC)
        self.assertEqual(event.arg1, 24)
        self.assertEqual(event.capture, body[:24])

    def test_a_nested_struct_takes_its_width_from_the_packet(self) -> None:
        """The repeat count is packet data, which is why the stub reads it (``stoc_methods.cpp:213``)."""

        block = _Block()
        packet = _Buffer(ctypes.create_string_buffer(600))
        body = struct.pack("<6I", self.HEADER, 3, 0xAA, 0xBB, 0xCC, 0xDD) + bytes(576)
        packet.write(0, body)

        event = self.inbound(
            block, packet, sb.PacketCapture(fixed_bytes=4, nested_stride=8, repeat_offset=4)
        )

        self.assertEqual(event.arg1, 4 + 3 * 8)
        self.assertEqual(len(event.capture), 4 + 3 * 8)

    def test_a_walk_that_cannot_finish_answers_a_bare_header(self) -> None:
        """``uint32_t size = sizeof(PacketBase)`` is what native falls back to (``:240``)."""

        block = _Block()
        packet = _Buffer(ctypes.create_string_buffer(600))
        packet.write(0, struct.pack("<2I", self.HEADER, 99999) + bytes(592))

        event = self.inbound(
            block, packet, sb.PacketCapture(fixed_bytes=4, nested_stride=8, repeat_offset=4)
        )

        self.assertEqual(event.arg1, 4)
        self.assertEqual(len(event.capture), 4)

    def test_the_inbound_capture_is_clipped_the_way_native_clips_it(self) -> None:
        block = _Block()
        packet = _Buffer(ctypes.create_string_buffer(1024))
        packet.write(0, struct.pack("<2I", self.HEADER, 0) + bytes(1016))

        event = self.inbound(block, packet, sb.PacketCapture(fixed_bytes=1000, cap=512))

        self.assertEqual(event.arg1, 1000)
        self.assertEqual(len(event.capture), 512)

    def test_an_outbound_packet_is_recorded_with_its_header_and_its_bytes(self) -> None:
        block = _Block()
        packet = _Buffer(ctypes.create_string_buffer(64))
        body = struct.pack("<4I", 0x39, 0xDEAD, 0xBEEF, 0x1234)
        packet.write(0, body)

        header = self.outbound(block, len(body), packet)

        self.assertEqual(header.event_written, 1)
        event = block.event(0)
        self.assertEqual(event.kind, sb.EventKind.PACKET)
        self.assertEqual(event.sequence, 0x39)
        self.assertEqual(event.arg0, sb.PACKET_DIRECTION_CTOS)
        self.assertEqual(event.arg1, len(body))
        self.assertEqual(event.capture, body)

    def test_an_outbound_packet_the_source_drops_is_not_recorded(self) -> None:
        """A size below ``sizeof(uint32_t)`` or past the ceiling is dropped, not clipped (``:82``)."""

        for size in (0, 3, sb.EVENT_CAPTURE_SIZE + 1):
            with self.subTest(size=size):
                block = _Block()
                packet = _Buffer(ctypes.create_string_buffer(8192))
                packet.write(0, struct.pack("<4I", 0x39, 1, 2, 3))
                header = self.outbound(block, size, packet)
                self.assertEqual(header.event_written, 0)

    def test_the_largest_packet_the_source_allows_is_copied_whole(self) -> None:
        block = _Block()
        packet = _Buffer(ctypes.create_string_buffer(sb.EVENT_CAPTURE_SIZE))
        body = struct.pack("<I", 0x39) + bytes(sb.EVENT_CAPTURE_SIZE - 4)
        packet.write(0, body)

        self.outbound(block, len(body), packet)
        event = block.event(0)

        self.assertEqual(len(event.capture), sb.EVENT_CAPTURE_SIZE)
        self.assertEqual(event.capture, body)


class EntrySpanTests(unittest.TestCase):
    """The span an entry patch replaces must be **whole instructions**.

    This is the defect that crashed a client twice on 2026-10-24: a five-byte span over
    ``55 8B EC 83 EC 50`` splits ``sub esp, 0x50`` after ``83 EC``, so the trampoline replays a
    ``sub esp`` that eats the first byte of the jump as its immediate, the body resumes in the middle
    of a ``push``, and the frame is wrecked on every call. The live bytes below are what
    ``tests/probe_send_wrapper_entry.py`` read from the send wrapper.
    """

    LIVE_HEAD = bytes.fromhex("55 8b ec 83 ec 50 a1 00 85 10 01 33 c5")

    def test_the_measured_send_wrapper_span_is_six_bytes(self) -> None:
        span = _entry_span(self.LIVE_HEAD)
        self.assertIsNotNone(span)
        # push ebp (1) + mov ebp, esp (2) + sub esp, imm8 (3)
        self.assertEqual(len(span), 6, "the span must cover the whole ``sub esp, 0x50``")
        self.assertEqual(span, bytes.fromhex("55 8b ec 83 ec 50"))
        self.assertNotEqual(
            len(span),
            5,
            "five bytes is the bug: it cuts ``sub esp, imm8`` in half",
        )

    def test_a_four_byte_frame_setup_takes_nine(self) -> None:
        head = bytes.fromhex("55 8b ec 81 ec 00 01 00 00 53 8b 5d 10")
        self.assertEqual(
            _entry_span(head), bytes.fromhex("55 8b ec 81 ec 00 01 00 00")
        )

    def test_anything_else_is_refused_rather_than_guessed(self) -> None:
        for head in (
            bytes.fromhex("55 8b ec 56 8b 75 0c"),  # push esi after the frame: not a known shape
            bytes.fromhex("8b ff 55 8b ec 83 ec"),  # no prologue at all
            bytes.fromhex("55 8b ec"),
        ):
            with self.subTest(head=head.hex(" ")):
                self.assertIsNone(_entry_span(head))


if __name__ == "__main__":
    unittest.main()
