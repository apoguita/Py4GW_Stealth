# Packet Sniffer — port

**Status: ported; the offline checks pass; one live pass owed.** The class is
`py4gw/packet_sniffer.py` over the `PyPacketSniffer` binding in
`py4gw/native_src/packets/py_packet_sniffer.py`, with the capture it rests on in the capability layer
(`py4gw/game_thread/{shared_block,payload,packets,bridge}.py` and `ConnectedClient.install_send_capture`).
What the live pass has to prove is §8. §1-§6 are the analysis the port was built from, kept because
the code's docstrings cite them.

Sources read for it:

| Source | File | Shape |
| --- | --- | --- |
| Reforged | `Py4GWCoreLib/PacketSniffer.py` | 564 lines: 5 module constants, one frozen dataclass `PacketLogEntry`, `class PacketSniffer` (21 methods, 2 class attributes), module-level `SNIFFER` |
| Reforged | `Py4GWCoreLib/enums_src/Packet_enums.py` | `CTO_OPCODES` (118 entries) — already ported here as `py4gw/enums_src/packet_enums.py` |
| Native | `include/GW/packet_sniffer/packet_sniffer.h` | 60 lines: `PacketDirection`, `PacketLogEntry`, three bounds constants, 11 free functions, `SendPacketFn`, `ResolveCToSSendTarget` |
| Native | `src/GW/packet_sniffer/packet_sniffer.cpp` | 229 lines: the StoC callback over all headers, the CToS detour, lifecycle |
| Native | `src/GW/packet_sniffer/packet_sniffer_methods.cpp` | 58 lines: the shared log buffer under a mutex |
| Native | `src/GW/packet_sniffer/packet_sniffer_patterns.cpp` | 21 lines: `ResolveCToSSendTarget` → `packet_sniffer.ctos_send_target` |
| Native | `src/GW/packet_sniffer/packet_sniffer_bindings.cpp` | 91 lines: `PYBIND11_EMBEDDED_MODULE(PyPacketSniffer)`, `PacketSnifferFacade` with 12 methods |
| Native | `offsets/packet_sniffer.json` | the `ctos_send_target` resolver — **already copied here verbatim** as `offsets/packet_sniffer.json` |
| Native | `include/GW/stoc/stoc.h`, `src/GW/stoc/*.cpp` | the dependency: the handler array, `RegisterPacketCallback`, `GetPacketSize`'s field walk |
| Stubs | `stubs/PyPacketSniffer.pyi` | the binding surface in stub form |

The operator tool `Widgets/Coding/Debug/Guild Wars/PacketSnifferTester.py` is the only caller in
Reforged; it drives `initialize` → `get_logs`/`clear_logs` → `terminate` and prints
`get_packet_name`/`decode_packet` output. Everything else in the class is written for that flow.

## 1. The class is two layers, and the split is the whole analysis

`Reforged/PacketSniffer.py` is a **facade plus a decoder**, and the two halves have nothing in common:

- **The facade** — `initialize`, `terminate`, `get_logs`, `clear_logs` and the `_normalize_direction` /
  `_convert_entry` helpers — is a thin wrapper over `PyPacketSniffer.PacketSniffer.instance()`
  (`PacketSniffer.py:326-369`, `:387-396`). Ten lines of body each. Every one of them is a call
  across the process boundary into a runtime that is loaded in the client.
- **The decoder** — `get_packet_name`, `decode_packet`, and the seven private formatters behind it
  (`PacketSniffer.py:371-561`) — never touches the client at all. It is `struct` unpacking over bytes
  already in hand and three lookup tables in the module. **That half has no dependency on this
  project's capability layer at all**, and it is ~330 of the 564 lines.

So the port has one real capability question (the capture path) and one large pure-Python transcription.

### The capture path is *not* one mechanism; it is two

| Direction | Native mechanism | Where |
| --- | --- | --- |
| StoC (inbound) | **The client's own handler entry is replaced.** Not a function hook: `g_game_server_handlers->at(header).handler_func = &StoCHandler_Func`, for every header `0 .. kStoCHeaderCount-1`, at altitude `-0x8000` | `packet_sniffer.cpp:123-154`; `stoc_methods.cpp:32-61` |
| CToS (outbound) | **An entry hook on one function** — the outbound send wrapper, `void __cdecl(void* ctx, uint32_t size, const void* packet)`, resolved by byte pattern | `packet_sniffer.cpp:156-194`, `:81-98`; `packet_sniffer_patterns.cpp:10-19` |

They share nothing but `LogPacket`. They have separate initialize/terminate pairs, separate
`initialized` flags, and `Initialize()`/`Terminate()` are the two ordered pairs
(`packet_sniffer.cpp:112-121`, `:196-199`: StoC then CToS in; **CToS then StoC out**).

### What is captured, in the source's own numbers

- StoC: the packet's size comes from a **walk of the live handler's field template** —
  `GW::StoC::GetPacketSize(header, pak)` (`stoc.h:76-85`, `stoc_methods.cpp:239-262`), which decodes
  each `uint32_t` descriptor's kind and width and sums the wire width, replaying a trailing
  nested-struct `repeat` count **read from the packet's own bytes**. The copy is
  `min(packet_size, 512)` bytes (`kMaxStoCPacketBuffer`), and `entry.size` is the *walked* size even
  when it exceeds the copy (`packet_sniffer.cpp:141-145`).
- CToS: `size` is the wrapper's own argument; the header is `raw & 0xFFFF` read from the packet; the
  copy is the whole `size` bytes, bounded at 4096 (`kMaxReasonableCToSPacketSize`); a size under 4 is
  discarded; and the trampoline runs the client's wrapper unconditionally afterwards
  (`packet_sniffer.cpp:81-98`, `:35-66`).
- Both: `entry.tick = PY4GW::System::GetTickCount64()`, taken **inside the client at capture time**.
- The log is one `std::vector<PacketLogEntry>` under one mutex, capped at `kMaxLogs = 10000` by
  erasing from the **front** — a FIFO drop of the oldest entry, not a refusal of the newest
  (`packet_sniffer_methods.cpp:16-22`). `get_logs` returns a copy of the whole vector.

## 2. The Native surface (what the facade wraps)

`PacketSnifferFacade` (`packet_sniffer_bindings.cpp:15-42`) — the 12 methods Reforged calls, each a
one-line forward to the `GW::packet_sniffer` free functions. Record fields are `def_readonly`:
`tick` (u64), `direction`, `header` (u32), `size` (u32), `data` (vector<uint8_t> — a Python list of
ints in the binding, and `bytes(entry.data)` in Reforged's `_convert_entry`). `PacketDirection` is a
pybind enum with two values, `StoC = 0`, `CToS = 1`, `.export_values()`.

`PacketLogEntry.__repr__` is the binding's own (`packet_sniffer_bindings.cpp:68-75`):
`<Packet direction=StoC header=0x0084 size=36>`. Reforged's dataclass has no `__repr__` of its own, so
the port's dataclass keeps the default and only the binding-side shape is what `repr` would have shown.

## 3. Reforged's 21 members, and what each one needs

| Member | Line | What it does | Needs |
| --- | --- | --- | --- |
| `__init__` | 326 | `self._sniffer = PyPacketSniffer.PacketSniffer.instance()` | the binding equivalent (see §4) |
| `instance` (classmethod) | 329-333 | memoised singleton on `_instance` | nothing |
| `initialize(direction='both')` | 335-341 | normalize; `initialize()` / `initialize_stoc()` / `initialize_ctos()`; returns `bool(...)` | StoC: replace all header entries; CToS: hook the send wrapper |
| `terminate(direction='both')` | 343-350 | normalize; `terminate()` / `_stoc()` / `_ctos()` | the two restores |
| `get_logs(direction='both')` | 352-360 | `get_logs` / `get_stoc_logs` / `get_ctos_logs`, then `_convert_entry` per entry | the log, drained host-side |
| `clear_logs(direction='both')` | 362-369 | `clear_logs` / `_stoc_logs` / `_ctos_logs` | the log |
| `get_packet_name(direction, header)` | 371-374 | `STOC_HEADER_NAMES.get(h, f'0x{h:04X}')` / `CTO_OPCODES.get(h, …)` | **nothing — pure table lookup** |
| `decode_packet(direction, header, size, raw)` | 376-379 | dispatch to `_decode_stoc_packet` / `_decode_ctos_packet` | **nothing — pure bytes** |
| `_normalize_direction` (classmethod) | 381-385 | `ValueError(f'Unsupported packet direction: {direction!r}')` unless in `_VALID_DIRECTIONS` (`'CToS'`, `'StoC'`, `'both'`) | nothing |
| `_convert_entry` (staticmethod) | 387-396 | `PyPacketSniffer.PacketLogEntry` → this project's `PacketLogEntry`; `'StoC' if entry.direction == PyPacketSniffer.PacketDirection.StoC else 'CToS'`; `tick=int(getattr(entry, 'tick', 0))` | the binding record type and its enum |
| `_u32`, `_f32` | 398-408 | little-endian reads with a length check returning `None` | nothing |
| `_format_fields` | 410-414 | `', '.join(f'{k}={v}')` | nothing |
| `_format_u32_words` | 416-425 | `u32_1…` dict from offset 4 | nothing |
| `_format_u32_words_compact` | 427-437 | `@off=0xVAL …` up to 12 words then `'...'` | nothing |
| `_utf16le_fixed` | 439-449 | decode a fixed code-unit run, cut at the first NUL | nothing |
| `_utf16le_preview` | 451-476 | scan for printable UTF-16 runs (`min_chars=3`, `max_hits=6`) | nothing |
| `_name_re_probe` | 478-486 | `body_len` + the two probes above | nothing |
| `_find_known_subpackets` | 488-496 | scan 2-byte-aligned words for `KNOWN_CTOS_LENGTHS` headers | nothing |
| `_decode_stoc_packet` | 498-529 | 11 header-specific decoders + `NAME_RE_STOC_HEADERS` probe + base line | nothing |
| `_decode_ctos_packet` | 531-561 | 10 header-specific decoders + subpacket scan + probe + base line | nothing |
| module `SNIFFER = PacketSniffer.instance()` | 564 | the singleton Reforged imports | `instance` |

Constants to transcribe as written: `STOC_HEADER_NAMES` (**247** entries), `GENERIC_VALUE_IDS`
(**13**), `KNOWN_CTOS_LENGTHS` (**12**), `NAME_RE_STOC_HEADERS` (**15**), `PacketDirection = Literal['CToS','StoC']`.

Two source details to keep rather than tidy: `_utf16le_preview`'s f-string nests double quotes inside
double quotes (`f"@{offset}='{"".join(chars)}'"`, line 471 — PEP 701 syntax, fine on this project's
3.12/3.13), and `_decode_stoc_packet` gates header `0x0127` on `len(raw) >= 180` while reading a field
at `180` and `188` (lines 517-518). Both are the source's; neither is a defect to fix here.

## 4. What this project already has underneath it

Verified by reading the files; the live evidence is cited where it exists.

| Piece | Where | State |
| --- | --- | --- |
| StoC handler array resolution | `offsets/stoc.json` (`stoc.handler_table_addr`: scan + `dereference`) | present, and **live-verified**: game server `0x1D6BC90`, codec `0x1D63388`, array buffer `0x1DF1F40`, **capacity 504, size 487** (`tests/live_reports/stoc_handlers.json`) |
| Per-entry fields | `py4gw/game_thread/packets.py`: `ENTRY_TEMPLATE_OFFSET 0x0`, `ENTRY_FIELD_COUNT_OFFSET 0x4`, `ENTRY_HANDLER_OFFSET 0x8`, `ENTRY_SIZE 0xC` | read already; the live report shows real values per header (`packet_template`, `field_count`, `handler_func` in live code) |
| Replacing one header's handler with emitted code | `packets.PacketHooks.install/remove`, `payload.build_packet_stub` | working, used by `listeners.MerchantListener` and `merchant.py`; restores entries, frees code after an in-flight count drains, refuses a dead handler and repairs this project's own orphaned stubs |
| A hook on a client function with arguments forwarded | `game_thread/hooker.py` (`forwarded_arguments`, `build_stub`, `build_entry_patch`, trampoline) | working — the entry hook, the render hook and the post-call observer use it |
| The CToS send wrapper itself | `offsets/ctos.json` (`send_target`) **and** `offsets/packet_sniffer.json` (`ctos_send_target`) | **resolvable but never resolved by anything**: no code in `py4gw/` names either |
| The 18-word packet copy | `EVENT_WORDS = 18`, `EVENT_WORDS_OFFSET` in the event record (`shared_block.py:105-125`, `EventKind.PACKET = 5`) | working, bounded to what a merchant listener reads |
| A bounded copy of a client string with a runtime-length walk | `payload.build_observer`'s string copy loop (`payload.py:1011-1033`) | working — the closest existing form to a variable-length copy |
| A client tick on an event | event field `tick` exists; every stub writes **0** (`payload.py:440-445`: "nothing produces a tick yet") | **absent** |
| The opcode tables | `py4gw/enums_src/packet_enums.py` (`CTO_OPCODES`, `CTO_OPCODES_BY_NAME`, `get_opcode_name`, `get_opcode_header`) | ported already (2026-09-26 family), so `get_packet_name`'s CToS half is a lookup into an existing table |

So the "needs the packet hooks" note on `docs/CLASS_PORT_MAP.md:271` is **out of date in one
direction**: the hooks exist and are live-verified. What does not exist is the capture *width*, the
CToS detour, the size walk, and the log itself.

## 5. What is missing, precisely — the work items

Each is a named capability with the source line that requires it. None is a boundary; all are work.

1. **Capture width.** A sniffer packet is up to **512 bytes** (StoC) and **up to 4096** (CToS)
   (`packet_native.h:28-30`). An event record carries **18 words = 72 bytes**
   (`EVENT_WORDS`, `shared_block.py:115`) and is `2048` bytes total. So the sniffer's capture cannot
   travel in the existing word copy, and the `wanted: Mapping[int, int]` shape of
   `PacketHooks.install` (header → word count) cannot express it. What is required is a bounded
   byte-copy region in the block — this project's own mechanism, in the same sense the decode region
   is (`DECODE_REGION_OFFSET`, `shared_block.py:143-186`) — a `VERSION` bump, and an emitted copy
   whose length is either an immediate (StoC) or the wrapper's own `size` argument (CToS; the source's
   `SafeCopyCToSPacket`, `packet_native.cpp:51-66`).

2. **The StoC size walk (`GetPacketSize`).** `packet_native.cpp:141` asks for the packet's wire size
   before it copies, and reports that size even when the copy is clipped at 512. The walk
   (`stoc_methods.cpp:112-262`) decodes descriptor `type`/`size`/`count` bits against a trailing
   nested-struct `repeat` **read from the packet's bytes**, with hard ceilings
   (`kMaxComputedPacketBytes = 8192`, `kMaxNestedRepeatCount = 4096`) and a fallback to
   `sizeof(PacketBase)` = 4. Porting it needs (a) the walk itself, host-side, over the template the
   handler array already exposes, and (b) an answer for the live-bytes half: the repeat count is
   packet data, so either the copied prefix is walked after the fact or the walk runs before the copy
   — and the source does it **inside** the client (`packet_native.cpp:141-145`) with SEH around both
   the walk and the copy. **Emitted code here has no SEH**, so the port must decide, in writing on the
   member, how a template-derived size larger than the client's real buffer is kept from taking the
   client down — native's answer is the `__except` that falls back to a 4-byte copy.

3. **The CToS detour.** An entry hook on `packet_sniffer.ctos_send_target`
   (`patterns.cpp:17`), signature `void __cdecl(void* ctx, uint32_t size, const void* packet)`, which
   captures `min(size, 4096)` bytes from `packet`, reads the header as `raw & 0xFFFF`, discards a size
   below 4, and then **runs the original unconditionally** (`packet_native.cpp:81-98`). The hook
   machinery exists (§4), and the resolver file is already here — but no emitted form copies `size`
   bytes from an argument-pointed buffer: `build_packet_stub` copies a *fixed* word count from the
   argument the **dispatcher** pushed, and `hooker.forwarded_arguments` copies argument *words* into
   per-depth state, not a pointed-to buffer. This is the one genuinely new stub form.
   Note the two resolver spellings of the same target: native declares the wrapper with exact bytes in
   `packet_sniffer.json` and with wildcards in `ctos.json` — both are in this project's `offsets/`
   already, and the sniffer uses `packet_sniffer.ctos_send_target` because that is what
   `patterns.cpp:17` names.

4. **All 487/488 headers at once.** `InitializeStoC` loops `header < GW::StoC::kStoCHeaderCount`
   (`0x1e8` = 488, `stoc.h:24`) and registers one callback each. The live array holds **487** entries
   in 504 slots, so the loop's last registration is the one `RegisterPacketCallback` refuses
   (`g_game_server_handlers->size() > header`, `stoc_methods.cpp:55`) — and native ignores the
   callback's return, so `InitializeStoC` still answers `true`. Native needs one code address for all
   of them (one shared `StoCHandler_Func`); this port needs **one stub per header**
   (`packets.py:1146-1153`), so an all-headers install is ~487 allocations of ~220 bytes plus one
   entry write each — the install path already handles that shape but has never been driven at that
   size, and the per-header count of captured bytes has to be supplied per header
   (§1: the source's count is per-packet, not per-header).

5. **The log.** `g_logs` + mutex + `kMaxLogs = 10000` front-erase (`methods.cpp:13-56`). Host-side
   this is a list and a deque-style trim; the shape to keep is *oldest dropped first*, `get_logs`
   returning a **copy**, and `clear_*` being whole-log or per-direction. It also has to be fed by a
   drain of the capture region, which is where the **bounded-depth** difference appears: native never
   loses a packet until 10000 are held; here a packet recorded while the event/capture region is full
   is recorded nowhere (`payload.py:1218-1224`). That is a divergence to write on `get_logs`.

6. **`entry.tick`.** Native stamps `PY4GW::System::GetTickCount64()` inside the client
   (`packet_native.cpp:84`, `:137`). This project's event `tick` word is written as **0** by every
   stub and nothing produces one. `GetTickCount64` is a machine-wide clock, so the value is
   reproducible host-side — the port's question is only *when* it is read (at capture vs at drain),
   and that sentence belongs on `PacketLogEntry.tick` / `_convert_entry`. Note
   `native_src/base/perf_counter.py:271-279` uses `time.monotonic_ns()` as its stand-in, which is a
   **different epoch** from `GetTickCount64`; a faithful tick must not use it.

7. **The binding shape.** Reforged's facade sits on `PyPacketSniffer.PacketSniffer.instance()` with
   `initialize*`/`terminate*`/`get_*_logs`/`clear_*_logs`, a `PacketLogEntry` record and a
   `PacketDirection` enum whose `'StoC'`/`'CToS'` members `_convert_entry` compares against. Precedent
   for carrying a binding beside its ported class is `py4gw/effect.py` (the binding classes plus
   Reforged's `Effects` over them) and `py4gw/native_src/item/py_inventory.py`. Both names must come
   from the sources: `PacketSniffer` is Reforged's facade class in `Py4GWCoreLib/PacketSniffer.py`,
   and the 12-member facade under the `PyPacketSniffer` module is Native's — a port that gave both the
   same name would be the `PyDialog` mistake this project already made once.

8. **Lifecycle semantics to keep exactly.** `initialize`/`terminate` are idempotent per direction
   (`g_stoc_initialized`, `g_ctos_initialized`, `packet_native.cpp:125-127`, `:158-161`, `:203-205`,
   `:216-218`); `Initialize` = StoC then CToS and answers their `&&`; `Terminate` = **CToS then
   StoC**; a CToS initialize that fails to resolve its target answers `false` and leaves the StoC half
   in place (`packet_native.cpp:163-166`); and the sniffer starts **nothing** until asked — it is
   deliberately not in the initialization table (`packet_native.h:32-35`).

## 6. Not part of this class, but named by it

- `PyCtoS.SendPacket(words)` (`ctos_bindings.cpp`) composes an outbound packet. The sniffer only
  *observes* CToS, and nothing in this port composes one (`gwa3/core.py:387` refuses
  `Core_SendPacket`). Out of scope for the sniffer; recorded so the two are not confused.
- `GW::StoC::EmulatePacket` (`stoc_methods.cpp:264-266`) is the StoC module's, not the sniffer's.

## 7. What landed

| Piece | Where | What it is |
| --- | --- | --- |
| the facade and the decoder | `py4gw/packet_sniffer.py` | Reforged's file, transcribed: 5 constants (247 + 13 + 12 + 15 entries), `PacketLogEntry`, `PacketSniffer` (22 names), `SNIFFER`. `PyPacketSniffer` is imported under the name Reforged imports it by (`PacketSniffer.py:7`) |
| `PyPacketSniffer` | `py4gw/native_src/packets/py_packet_sniffer.py` | native's module: `PacketDirection`, `PacketLogEntry` (+ its `__repr__`), `LogPacket`/`GetLogs*`/`ClearLogs*`, `Initialize`/`Terminate` and the two pairs, `ResolveCToSSendTarget`, and the 12-member `PacketSniffer` facade |
| the capture width | `shared_block.py` (`VERSION = 7`, `EVENT_SIZE = 8192`, `EVENT_CAPTURE_*`) | a record carries up to 4096 bytes of the packet it is about; `EventRecord.capture` is that copy |
| the inbound stub | `payload.build_packet_stub(..., capture=PacketCapture)` | computes native's walked size **in the client** — template width, plus a nested struct's stride times the repeat count read out of the packet — then copies `min(size, cap)` bytes |
| the outbound stub | `payload.build_send_capture_stub` | native's `Detour_SendPacket`: the wrapper's two arguments, its guards (`packet && size >= 4 && size <= 4096`), the header as `raw & 0xFFFF`, and the bytes |
| the template walk | `packets.describe_template` / `decode_field_kind` / `read_template` | `DecodeFieldKind` and the template half of `WalkFields`, so each header's capture is described once at install rather than per packet |
| registration | `packets.PacketHooks.install(..., captures=)` | additive, as `RegisterPacketCallback` is: the sniffer's 487 headers and the merchant's five coexist — native's own arrangement |
| the CToS hook | `bridge.install_send_capture`, `ConnectedClient.install_send_capture` | placed on demand on `packet_sniffer.ctos_send_target`, and taken out by `TerminateCToS` or a disconnect |
| offline checks | `tests/test_packet_sniffer_offline.py` | 34 tests: the tables, both decoders, direction normalization, entry conversion, the log and its cap, the template walk, and the two stubs **executed** against a fake block |

### The divergences, recorded rather than smoothed

1. **`entry.tick` is taken at drain, not at capture.** Native stamps `PY4GW::System::GetTickCount64()`
   inside the client (`packet_sniffer.cpp:84`, `:137`). Nothing writes a tick in this block, so the host
   reads the same Windows function when the record arrives: the same clock, later by the drain.
2. **A full event region loses a packet; native loses nothing until 10000 are held.** Native appends to
   a vector in its own process and never waits (`packet_sniffer_methods.cpp:16-22`); here a record the
   ring cannot hold is written nowhere, and the stub does not make the client wait. The 10000 cap and its
   oldest-first drop are both kept.
3. **`event.arg1` is the size, computed in the client.** Native calls `GetPacketSize` per packet
   (`:141`); here the stub does the same arithmetic and the record carries the answer, so nothing
   re-walks it on the host. The walk's failure case is native's too: a repeat past its ceiling answers
   `sizeof(PacketBase)` (`stoc_methods.cpp:215-217`, `:240`).
4. **One stub per header carries what every registration needs.** Native keeps one callback list per
   header (`stoc.cpp:80-99`) and runs each callback; here one stub records once and the host dispatches,
   which keeps the source's observable order because the record is written before the chain runs.
5. **The merchant listener's `Uninstall` no longer restores the client's entries.** Native's
   `RemoveCallback` leaves `handler_func` replaced (`stoc_methods.cpp:70-87`) and only `DisableHooks`
   puts entries back (`stoc.cpp:130-140`); the port restored them, which would have taken out the
   sniffer's 487 headers when the merchant switched off. Corrected in this batch.

## 8. The live pass: what is settled, and what the first attempt cost

### Settled read-only, 2026-10-24 (pid 20600, `tests/probe_send_wrapper_entry.py`)

The send wrapper resolves at `0x00CEB0C0` on the primary pattern, and its entry is
`55 8B EC 83 EC 50 A1 00 85 10 01 33 C5 89 45 FC …` — the **five-byte** prologue shape, so
`_entry_span` displaces `55 8B EC 83 EC` and the install has a span to work with. (`tests/live_reports/send_wrapper_entry.json`.)
The same report lists `RTSSHooks.dll` at `0x10000000` in the client, which is the object-handle filter
this project already blames for `Access is denied` on suspend/write (`docs/RESEARCH.md`).

### The first live attempt, 2026-10-24 20:47:39 — one port defect and one unattributed crash

The elevated run found a **real defect in this port**, before any packet was captured:

- **`header 79's entry has no handler to chain to` aborted the whole install.** The client's handler
  array holds an entry per header, and a header the client never dispatches has a **null** handler.
  Native registers anyway — it snapshots the entry and inserts into `g_packet_entries[header]`, and a
  null `handler_func` simply never runs (`stoc_methods.cpp:41-61`) — and the emitted stub already had
  the no-chain form (`build_packet_stub`'s `if original:`). The refusal was this project's own
  invention, and it stopped 79 headers in. **Fixed**: a null handler is registered and restored to
  null, covered by two offline tests.

Then the client **exited**. The evidence, in its own words:

| Fact | Value |
| --- | --- |
| crash report | `F:\GW\GW1\crashes\py4gw-20261024-204739` (written by the injected runtime's handler) |
| exception | `c0000005`, "Memory at address `096d1000` could not be written" |
| `fault_address` | `0x096D0FFF` — **no module in the DLL list covers it**, so the faulting instruction ran from injected code |
| client | `Gw.exe` build 39112, base `0x00910000` |
| runtime's last operation | `Main.Update[15/16] → "Travel On Character Load"` |
| after the crash | `SuspendThread`/`WriteProcessMemory` → `Access is denied` (a terminated target's signature), then `ReadProcessMemory` → `ERROR_PARTIAL_COPY` on the next test |

**What is established:** the client died during the run, after the outbound hook was placed and before
any outbound packet was captured; and the faulting write was not to a documented target of this port
(the block's address was never printed by that run, so it cannot be ruled in or out). **What is not
established:** whether the faulting code was Reforged's or this project's. `0x096D0FFF` sits just below
the page it failed to write, which is the shape of a write one page past an allocation — the block is
597 KB and its event region is 512 KB, so a block allocated near `0x09650000` would end near there,
and so would an allocation of Reforged's. One more number settles it: the block's address.

**So the live suite is now staged and attributive** (`tests/test_live_packet_sniffer.py`):

1. it prints the block's address and span at connect, so a fault address either lands in this
   project's block or provably does not;
2. a **narrow** capture of five headers runs first — if the client dies there, the whole-array install
   is not the suspect;
3. the **outbound half is opt-in** (`PY4GW_LIVE_CTOS=1`), because it hooks the function every outbound
   packet goes through and must not be mixed into a run that is already suspect;
4. every entry it replaced is compared against a snapshot taken before the install.

`tests/probe_stoc_captures.py` is the read-only preflight for the same reason: it walks **every**
header's template with this port's own `describe_template` and reports the walk before anything is
placed — the null-handler headers, the nested-struct headers, the widest fixed template, and any
template the port cannot describe at all.

## 9. Verdict

**Both capture halves are live-verified, 2026-10-24** (client pid 6616, build 39112; the whole staged
suite with the outbound half opted into, `Ran 5 tests … OK (skipped=1)`, client alive at the end):

```
inbound   StoC 0x001E size=8  copied=8   head=1e 00 00 00 fd 01 00 00
outbound  CToS 0x0039 size=12 copied=12  head=39 00 00 00 12 00 00 00 00 00 00 00
lifecycle initialize() places both halves and terminate() takes them out, both idempotent
log       clear_logs / get_logs per direction over entries that arrived live
```

`0x001E` is `WORLD_SIMULATION_TICK` (8 bytes: the tick word) and `0x0039` is `INTERACT_LIVING`
(12 bytes: the agent id and its flag) — both the shape the decoders' branches expect. The one skip is
the five-header narrow capture, whose headers are merchant windows that carry no traffic in an
outpost; the install and restore it checks did run, and the whole-array test covers the same code path
with traffic.

### The three defects this live work found, all fixed

1. **A displaced span that cut an instruction in half** — the send wrapper's span was 5 bytes over
   `55 8B EC 83 EC 50`, whose instructions are 6, so `sub esp, 0x50` was split and every outbound send
   ran on a wrecked frame. It took the client down twice before the address arithmetic (`block
   0x4F730000`, fault `0x4F8A1000`, outside the block) showed the fault was a frame walking into
   garbage rather than a stray write. `EntrySpanTests` pins 6 and 9 bytes and refuses 5.
2. **Two of the wrapper's three words forwarded** — `SendPacket(ctx, size, packet)`, so the stub read
   `(ctx, size)`, its size guard saw a pointer and dropped every packet silently.
3. **The outbound half never subscribed to the event channel** — native's two paths call `LogPacket`
   themselves; here the records travel through the connection's registry, and only the inbound
   initializer registered it. A CToS-only start therefore drained and discarded its own events, which
   looks exactly like a client that sent nothing. Both halves register it now, once
   (`_register_handler`), and drop it when neither is capturing.

The stub's hit counter (`Bridge.send_capture_hits`) is what told the last two apart from silence, and
the test now fails — rather than skips — when the wrapper is reached and nothing is logged.

`py4gw.native_src.packets.py_packet_sniffer` (`PyPacketSniffer`), `py4gw.packet_sniffer` and
`py4gw.packet_sniffer.SNIFFER` are what this document is the port record for; the verdict line in
[`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) carries the same statement.
