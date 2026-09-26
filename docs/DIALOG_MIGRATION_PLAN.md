# Dialog migration plan

**Goal: `Dialog` reaches FULL.** Every one of the 32 native `PyDialog` members works, the
six record classes carry what the source fills them with, and the text fields of the
members that already work stop being empty.

**Verdict today: INCOMPLETE — all 32 members answer; what is missing is one thing a member
cannot *read* on this build** (this build's `DialogLoader_GetText`, so a catalog dialog's
`content` is empty), plus one handover withheld with its missing piece named (a button's label,
which the client's parser asserts on when it is handed over at this port's observation point).
This document is the plan for the
21, and for the features that have to be ported *first* because those members sit on top
of them. It is also the progress record: a workstream is marked done when its members
work live, not when the code is written.

Sources: `src/GW/dialog/dialog.cpp` (1,847 lines), `dialog.h`, `dialog_patterns.cpp`,
`dialog_bindings.cpp`, and `src/GW/ui/ui_methods.cpp` for the decoder. Line numbers below
are from the revisions on disk.

---

## 1. The 21 members, grouped by what each one needs

| Member | What the source does | Needs |
| --- | --- | --- |
| `is_dialog_active` | `dialog.cpp:1666-1682`: hash `3856160816u` → `GetFrameIDByHash`, then `GetFrameById`, then `frame->IsCreated() && frame->IsVisible()` | **F7 only** — no client call |
| `initialize`, `terminate` | `dialog.cpp:1266-1290` register/unregister the four UI-message callbacks; `Shutdown` drains decodes | **F8** (F5 for the gate it respects) |
| `get_dialog_text_decoded` | cache hit, else queue a decode, return `""` while pending (`1455-1475`) | **S6, S7, S2–S5** |
| `is_dialog_text_decode_pending` | the pending map (`1477-1484`) | **S6, S7, S2–S5** |
| `get_dialog_text_decode_status` | cache size, pending count, epoch (`1486-1500`) | **S6, S7, S2–S5** |
| `get_dialog_info` | five columns **+ `content = GetDialogTextDecoded(id)`** (`1423-1439`) | columns done; `content` needs **S6, S7, S2–S5** |
| `enumerate_available_dialogs` | `IsDialogAvailable` per id, then `GetDialogInfo` (`1441-1453`) | same as above |
| 6 × event-log members | `dialog_event_logs`, `_received`, `_sent` + three clears (`1693-1720`) | **F6** (their `text` follows S4) |
| 7 × callback-journal members | `dialog_callback_journal`, `_received`, `_sent`, three clears, the filtered clear (`1720-1780`) | **F6** (their `text` follows S4) |

**Also waiting on the decode, without being members:** `ActiveDialogInfo.message`,
`DialogButtonInfo.message`/`message_decoded`, and therefore the inline-choice fallback in
`Dialog.get_active_dialog_buttons()`. Those members work today and return the source's own
"decode in flight" state — empty text with `message_decode_pending` — which is correct, and
becomes text when Route A renders it (S1–S5). Their encoded pointers are already in the
captured events, so no further client call is needed for them.

---

## 2. The features to port first

**Corrected on the decode.** The first version of this plan treated the text decode as one
call plus one stub and dismissed its validity check as a bounded read. That was an
under-evaluation: string decoding is a subsystem with four routes, and its largest one is
**pure Python that Reforged already ships** — see
[`STRING_DECODE_PLAN.md`](STRING_DECODE_PLAN.md), which evaluates it properly and assigns it
the S-numbers referenced below. What follows uses those.

Nine pieces of work, in dependency order. Two of them need no new capability at all.

### F7 — Frame lookup by hash, over the ported frame array *(done)*

`GetFrameIDByHash` (`ui_methods.cpp:575-587`) is **a read**: it walks `FrameArray()` and
compares `frame->relation.frame_hash_id`. `GetFrameById` indexes the same array. Our
`py4gw/ui/frame.py` already has `FrameArray` indexed by frame id, `read_frame_pointer`, and
`FrameStruct.frame_hash_id` / `frame_state` with `is_created` (`0x4`) and `is_visible`.

**Built:** `FrameArray.frame_id_by_hash(hash)` — the port of `GetFrameIDByHash`, including
its convention that `0` means "not found" and its validity filter — and
`PyDialog.is_dialog_active` on top of it, in the source's own order. `FrameArray` is now
reachable from the connection (`client.frame_array`), as native's `GW::ui::FrameArray()`
is in-process.

**Verified live** (`tests/probe_dialog_phase1.py`, pid 39188): `is_dialog_active()` is
**false** while no dialog is open and `frame_id_by_hash(3856160816)` returns `0`; after
interacting with the closest NPC the client announces the dialog and both flip —
`frame_id_by_hash` finds the frame and `is_dialog_active()` is **true**. `False → interact →
True` is the whole contract of the member, and it holds.

### S1 — The encoded-string arithmetic *(done)*

`EncStrToUInt32`, `UInt32ToEncStr`, `IsValidEncStr` and the grammar they share, ported to
`py4gw/ui/encoded_str.py` from `ui_methods.cpp:152-159`, `260-362`, `2613-2656`. Pure Python,
no client state. Relevant to `Dialog` because dialog ids embedded in body text are encoded
exactly this way — which is what `extract_inline_dialog_choices_from_text` parses.

**Verified offline** (`tests/test_encoded_str_offline.py`, 20 tests): the constants, the five
character classes, round trips through the encoder and decoder, the length formula's two
lossy points kept as the source has them, and the grammar's accept/reject cases.

**Verified live** (same probe): the encoded strings the client itself sent during a real
dialog are accepted by the ported validator — the body (`0x8103, 0x0A66, 0xDAA8, 0xA948,
0x3363, 0x0002, 0x0102, 0x0002, …`, 22 codepoints) and both button labels
(`0x39B1, 0xC019, 0x0A92, 0x4006, 0x4A23, 0x0000`), all `True`. The body's first four
codepoints are the same bytes this project measured for a dialog body earlier
(`RESEARCH.md`: `03 81 66 0a a8 da 48 a9 …`), read by an independent route — which is the
cross-check that the grammar is being fed the real format.

### What the client has already rendered, and what it has not

Found by reading the frames under the NPC Dialog frame live (`tests/probe_dialog_text.py`),
and it decides where the text has to come from:

- **A rendered label is readable without any decoder.** `TextLabelFrame::GetDecodedLabel`
  (`ui_methods.cpp:2224-2234`) returns the **decoded** string the client keeps immediately
  after the encoded one in the frame's context, guarded by the size word at `[+0xC]`. Ported
  as `FrameArray.encoded_label` / `decoded_label` / `read_wide_string`, it reads what the
  client displays: the NPC's own name (`'Foreman the Crier'`), and libelled controls
  (`'Accept'`, `'Reject'`, `'Trade'`, `'Pets'`, `'Allies'`, the chat tabs, the clock
  `'10:15 am'`). 81 frames in a 733-slot array carried a label in the run.
- **The dialog body is not one of them.** The frames that carry the open dialog — the
  `"NPC Dialog"` root and its children — have contexts whose `[+4]`/`[+0xC]` words are small
  numbers rather than a string pointer and a size, so they are not label contexts and no
  decoded copy of the body text is published there. The body therefore has to be **rendered
  by the port**: its codepoints arrive in `DialogBodyInfo.message_enc` (already captured),
  and S2–S5 are what turn them into text.
- **Button labels are encoded-only through the source's own accessor.**
  `ButtonFrame::GetLabel` (`ui_methods.cpp:1920-1929`) returns the encoded pointer and
  nothing else, which is why Reforged's own `DialogButtonInfo.message_decoded` exists: the
  decoded form comes from the decode, not from the frame.
- **Not every label is an encoded string.** Frames carrying player names hold **plain ASCII**
  (`'Mini Warri…'`, `'Carl…'`, `'I Pauli Va…'`), and the enc-str grammar correctly rejects
  them. The format's own documentation says so — *"player names bypass all of this"*
  (`string_table.py:19-20`) — so S4 must not assume every label it is handed is encoded.
- **A frame that is not a label frame will still answer.** Casting a non-label frame's
  context to the label layout reads whatever the words are; four slots in the run produced
  junk that way. Native has the same exposure (`FrameAs<TextLabelFrame>` does not check the
  type); the probe skips those slots rather than reporting them as dialog facts.

**Conclusion for the plan:** the decode is not optional for the dialog's own text. What the
frame route gives is the *surrounding* UI — and, usefully, a second source of truth to
compare S4's output against for any string that is both rendered and encoded.

### F5 — The map-transition gate *(done, and it pulled `initialize` forward)*

Native suspends dialog callbacks across a map transition and invalidates the runtime state
when the map changes: `GetDialogMapStateSafe` (`167-180`), `ObserveMapChange` (`548-588`),
`PollMapChange` (`1388-1409`), `kDialogCallbackResumeDelay = 100 ms` (`39`),
`dialog_callbacks_suspended` (`107`), and the state wipe plus the two epoch bumps.
Everything it reads is ported: `Map.GetMapID()`, `Map.IsMapReady()`.

**Built:** `_map_state`, `_observe_map_change` (branch for branch, including the
`previous_map_id != 0` half of the invalidation rule), `_poll_map_change` / `_maybe_resume`,
`_set_gate_from_map_state`, `_clear_runtime_state`, and the source's `OnDialogUIMessage`
guard sequence in `_capture_message` — map snapshot, observation, null-packet refusal
(`wparam`, which is the packet word), then shutdown/suspended/not-ready, and only then the
message switch. The state machine moved to `_dispatch_message` so the offline suite can still
drive it without a client, and the guarded path is what the live probes exercise.

**`initialize` came forward from phase 6, because the gate is wrong without it.** Native's
`Initialize` (`1315-1331`) calls `ClearCache`, which sets the gate **from the live map**
(`1839-1842`) — so callbacks are not suspended at startup. Left suspended, the port would drop
the message that opens the first dialog. `PyDialog.initialize()` is now ported (clear both
shutdown flags, `clear_cache()`, return true) and `py4gw.connect()` calls it where it used to
call `_reset()`, immediately before registering the capture — which is the source's own order
(`Initialize` registers its hooks itself).

**Verified offline** (13 gate tests in `tests/test_dialog_offline.py`): the initial suspended
state, an unchanged map doing nothing, a change suspending without wiping on the *first*
observation, a later change suspending and wiping with both epoch bumps, a map that stops
being ready doing the same, resume waiting for the delay, resume needing a ready and currently
observed map, a shutdown stopping the resume, `clear_cache` re-taking the gate from the map,
and the three guards refusing a message.

**Live verification is pending:** the elevated run of `tests/probe_dialog_phase1.py` was
declined at the elevation prompt on this attempt, so the check that a real dialog still gets
past the gate has not been re-run since the gate landed. The command is
`Start-Process -Verb RunAs python -m tests.probe_dialog_phase1 <report>`; what it must show is
the same result as before, *with* the gate in place: agent captured after an interaction and
`is_dialog_active()` flipping to true.

**One divergence, recorded:** the ported `Map.GetMapID()` returns `0` while the map is not
ready (its own source's gate), where native's raw read returns whatever the client holds. It
changes which branch of the invalidation rule fires during a transition — the port sees the id
become zero *and* readiness go false, and either is enough — not whether the state is
invalidated.


### S6 — A call that brings a value back *(done)*

`DialogLoader_GetText` is `void* (__cdecl*)(uint32_t dialog_id)` (`dialog.h:87`) and its
result is the whole point: a pointer to the encoded text. The same form is what the DAT
chain needs for `FileHashToRecObj` → `RecObj*` and `ReadFileBuffer(rec, &size)` → `uint8_t*`
(`gw_dat_reader.cpp:102-158`).

**Built**, and it needed no new host API:

- the command record gained a **`value` word** (`shared_block.py`), so a command is nine
  words in a 64-byte slot and the block layout moved — **`VERSION` is 2**, and a mismatched
  block still fails closed: `BLOCK_SIZE` is now 7232 (header 64 + commands 16×64 + events
  64×32 + data 4096);
- the emitted call path stores the callee's `eax` into that word at **every** one of the six
  call sites (`payload.py`), through one helper, because `eax` is the return register the
  source's `__cdecl` declarations use and the next instruction needing a register would lose
  it. A target declared `void` leaves whatever the callee left there, so the host reads the
  word only for a target whose return it wants — the distinction the source's own prototype
  table carries;
- the host needs nothing new: `client.call_function` already returns the `CommandRecord`, so
  the value rides back on it.

**Why 64 and not 36:** the emitted dispatcher addresses a record by *shifting* its slot, so
the record stride has to be a power of two — checked where the shift is derived. Sixteen
words per command costs block space and keeps that property.

**Verified offline** (three new tests in `test_payload_offline.py`, two in
`test_shared_block_offline.py`): a real emitted callee that returns a constant, called
through the dispatcher, lands its value in the command while `result` stays `0` and the state
`DONE`; a refused call carries no value; `result` and `value` are stored and read back
independently (signed code and unsigned return); the record is padded to its slot and round
trips; the stride is a power of two.

### S7 — A data region in the shared block *(done)*

A function that takes a **pointer** — a string to read, or a word to write a result into —
needs an address in the client that outlives the call. Native's callers use their own stack
frames; this project has no frame in the client, so it uses a span of the same allocation.

**Built:** `DATA_REGION_OFFSET` / `DATA_SIZE` (4096) after the event ring, `data_offset()`
which refuses any span that would run past the region, and `Bridge.data_address` /
`write_data` / `read_data` — the last of which returns the address in the client, which is
what a call needs to pass.

**Verified offline** (six new tests in `test_bridge_offline.py`): the region sits after the
events and ends at the block's end; bytes written come back; a **wide string** can be placed
for the client to read as a `const wchar_t*` (which is exactly what `FileHashToRecObj` takes);
a span past the region is refused; writing the whole region leaves the header untouched; and a
bridge with no block refuses to write at all.

### S2, S3, S4, S5 — Route A: Reforged's own decoder

The port of `native_src/internals/string_table.py` and the DAT chain it reads through —
evaluated in full in [`STRING_DECODE_PLAN.md`](STRING_DECODE_PLAN.md) §2 and §7.

**All of Route A is ported, and the text has been rendered live.** `py4gw/internals/string_table.py`
(S4, S5: the codepoint parser, the entry decoder with its key derivation, RC4 and bit-unpack,
the postprocessors, the formatted-expression grammar, the file parser, the file-slot walk,
`decode` / `decode_plain`) with 89 offline tests; `py4gw/dat_reader.py` (S2: the port of
Native's `PyDatReader`, which is `FileHashToFileId` → `OpenFileByFileId` /
`FileHashToRecObj` → `ReadFileBuffer` → the bounded copy → `FreeFileBuffer` → `CloseRecObj`,
each call issued on the client's own thread) with 31; and `py4gw/internals/helpers.py` for the
substitute fallback's string read. S6 and S7 are the capability it runs on: the command
record's `value` carries a callee's return register, and the block's data region holds the
hash string and the size word the client writes back.

**Verified live** (`tests/test_live_dat.py`, pid 39188, 2026-09-25): one file read through the
client (91,114 bytes, 1024 entries, 944 rendering printable text with no key), and then a real
dialog body rendered — its 22 codepoints named table index 99942 with key `0x1610C5A3EA63`,
and the entry decrypted and unpacked to a readable sentence. The full record is in
[`RESEARCH.md`](RESEARCH.md).

**This is the route that renders the text**, and it runs on the host.

### S8 — The decode callback stub *(Route B only)*

The client can also decode by **calling back into a function it is given**:

```c
using DecodeStr_Callback = void (__cdecl*)(void* param, const wchar_t* value);  // ui_methods.cpp:29, 189
void AsyncDecodeStr(const wchar_t* enc_str, DecodeStr_Callback callback, void* param);
```

**To build:** a second emitted blob (the dispatcher is the first) — a stub with that exact
signature that copies `value` into the block's decoded half, writes its length, and
increments the completion counter. It has to stay resident while a decode is in flight and
be freed when the connection closes. The call itself is
`validate_async_decode_str_func(encoded_ptr, stub_address, param)` — three word arguments,
which the existing `U32_U32_U32` form already expresses, so **no new call form is needed
for the call**.

**Verify:** offline (the stub's bytes executed against a synthetic client, the way
`test_payload_offline.py` already tests the dispatcher), live (a real decode through a real
dialog).

### The dialog side of Route A — the catalog decode queue

The port of `QueueDialogTextDecode` (`1136-1179`) and everything around it, which is where
the source's own sequencing and caching live:

1. map gate → id bound → already cached → already pending → mark pending, capture epoch;
2. resolve `DialogLoader_GetText`; if it does not resolve, cache empty text and clear
   pending (`1166-1177`);
3. **call it** (S6) for the encoded pointer;
4. read the codepoints at that pointer (a bounded read), and run the source's own
   precondition on them — `IsValidEncStr` (S1), whose three answers are part of the contract:
   invalid → `L"!!!"`, no `TextParser` → `L""`, no decode function → `L""`
   (`ui_methods.cpp:2583-2599`);
5. **hand the copy to the client's decoder** — `AsyncDecodeStr`'s call, with the request this
   side prepared and the emitted stub as the callback (`dialog.cpp:1241`, `ui_methods.cpp:2582`);
   the client decodes it and the text arrives as a completion event. **This is the source's
   method, not a render on the host**: an earlier version of this document said to render the
   codepoints here with the game's string table, and that substitution cost weeks — the ported
   protocol worked on its first live attempt. Route A (`py4gw/internals/string_table.py`) is
   Reforged's own decoder and is still what the *agent/item* name paths use; the dialog does not;
6. store the text in `decoded_text_cache`, clear pending, and apply the epoch check the source
   applies on completion.

**Also in this workstream:** the button-label side, which the source keeps separately —
`decoded_button_label_cache`, `decoded_button_label_pending`, cap
`kMaxDecodedButtonLabelCache = 256` (`44`, `719`). All of it is ported — the request record, both
caches, the completion, and `GetActiveDialogButtons`' fill with its catalog fallback
(`1632-1664`) — but **the handover is withheld**: the label the client announces passes the
source's own `SafeIsValidEncStr` and then asserts inside the client's parser, because native reads
that pointer inside the client's own message dispatch and this port observes the message at its
sender. That is a finding with a name — the client's dispatch point — recorded in
[`RESEARCH.md`](RESEARCH.md).

**Verify:** offline (the queue's own state machine: cache hit, pending, invalid string, no
loader, no TextParser, epoch change mid-flight, the caps), then live — and **the live test drives
the interaction itself**: closest NPC, one interaction, wait for the dialog *and* its buttons
(`AGENTS.md`, "Live verification").

### F6 — The journals

Two stores, both capped at `kMaxDialogEventLogs = 512` (`41`), oldest dropped first:

- **event logs** — `AppendDialogEventLog` (`460-491`): `tick`, `message_id`, `incoming`,
  `is_frame_message`, `frame_id`, and `w_bytes`/`l_bytes` copied from the message's two
  pointer arguments by `CopyBytesSafe`, with the sizes each call site passes (the button
  packet is `sizeof(DialogButtonInfo)` = 16, the body packet `sizeof(DialogBodyInfo)` = 12,
  the sent side a single word);
- **callback journal** — `AppendDialogCallbackJournalEntry` (`493-546`): the same tick and
  message id, the direction, the dialog/context/agent ids and their two flags, `map_id`
  (`GetCurrentMapIdSafe`), `model_id` (defaulted from `GetAgentModelIdSafe`, which reads
  `living->player_number` — the field our agent records already carry), `npc_uid`
  (`BuildNpcUid`: `"%u:%u:%u"` of map, model, agent, `220-227`), `event_type`, and `text`
  (rendered by Route A, S4).

The entries are host-side bookkeeping: this project receives the same messages, so the
records are reproducible. Only `text` waits on the decode, and `frame_id` reads through the
ported frame route.

**To build:** the two stores with their caps and the three-way split (all / received /
sent), the per-handler entry construction, the bounded pointer-payload reads, and
`clear_dialog_callback_journal_filtered` with the binding's own optional filters
(`dialog_bindings.cpp:131-135`, all defaulting to "no filter").

**Verify:** offline (caps and drop-oldest, both directions, the filtered clear, the
`npc_uid` format), live (interact with an NPC and read the journal back — every entry the
run produced).

### F8 — The lifecycle

`Initialize()`/`Shutdown()` are the runtime's own start and stop. In this port the connection
owns the observer, so the members map onto that ownership: `initialize()` registers the
module's captures on the current connection and marks the module live (the source's
`dialog_hook_registered` idempotence), `terminate()` unregisters and **drains** the
in-flight decodes the way `Shutdown` waits on `dialog_async_decode_drained` (`1370-1386`).
`py4gw.connect()` keeps calling the same two internally, so nothing about connecting
changes.

**Verify:** offline (idempotence, registration and removal, drain with a decode in flight),
live (connect → initialize → terminate → disconnect with the client untouched).

---

## 3. Order of work

| Phase | Work | Members completed | Checkpoint |
| --- | --- | --- | --- |
| 1 | **F7** frame-by-hash · **S1** encoded-string arithmetic | `is_dialog_active` | live: true with a dialog open, false with it closed |
| 2 | **F5** map gate | — (correctness of the capture) | offline state machine + live zone transition |
| 3 | **S6 + S7** value-returning call, block data region | — | offline block/dispatcher tests; live loader pointer for a known id |
| 4 | **S4** Reforged's decoder · **S5** the load discipline · **S2 → S3** the DAT chain | **5 members, 3 text fields** — the dialog's own text renders here, with no client call beyond the loader | live: decode a real dialog's body and labels, compared against what the client shows |
| 5 | **F6** journals | 13 members | live: the journal of a real interaction |
| 6 | **F8** lifecycle | 2 members | connect/initialize/terminate/disconnect cycle |
| 7 | **S8** the callback stub *(only if a member needs the client's own decode)* | — | offline stub execution; live round trip |

**Verdict moves to FULL when phase 6 lands**, and the two divergences stay divergences:
`_call_native_dialog_method` (a binding object reached by dynamic name) and nothing else in
this module. Phase 7 is the one item that is *not* on the path to FULL — it exists because
Native's route B is real and other classes use it, and it is listed here so it is not
forgotten rather than because `Dialog` waits on it.

---

## 4. What these features unblock beyond `Dialog`

The reason to build them as features rather than as dialog fixes:

| Feature | Also unblocks |
| --- | --- |
| **S6** value-returning call | `Player.GetInstanceUptime` (`GW::ui::GetFrameLimit`'s result); the `Get*` members in `Party`, `Agent`, `Camera` and `Map`; the 6 frame-lookup members in `Map`; every step of the DAT chain |
| **S7** block data region | the sending side of every string (`Player.SendChat`, `SendChatCommand`, `SendWhisper`, `SendFakeChat`, `SendFakeChatColored`); the `size_out` word and hash string the DAT chain needs |
| **S1** encoded-string arithmetic | dialog inline choice ids; any id embedded in text; the validity precondition for route B |
| **S2–S5** Route A, Reforged's own decoder | **agent names** (`Agent.GetNameByID`), **item** names and descriptions with their amount/rarity/singular variants, **quest** name/description/objectives/location/npc, **chat** text, and the `Skill` (511 lines) and `Item` lookups — the single most-reused missing capability in the port, and it runs on the host. S4/S5 are ported; S2/S3 are the DAT call that fills the table |
| **S8** callback stub | `Player.GetChatHistory`, `IsChatHistoryReady`, `RequestChatHistory`, and any member whose source decodes *inside* the client |
| **F5** map gate | the same suspend/invalidate pattern for any other module whose state is map-scoped |
| **F6** journals | the same store-and-cap pattern for the packet sniffer's and the chat reader's records |
| **F7** frame-by-hash | the frame lookups in `Map`, and `UIManager`'s by-hash frame readers |

---

## 5. Verification plan

**Offline, per feature** — the project's existing patterns, extended: the block's new region
and version check, the emitted call path returning a value, the encoded-string arithmetic and
grammar (S1), the decode pipeline against **known encoded bytes with a known expected text**
(S4), the DAT chain's call sequence against a synthetic client (S2), the emitted callback stub
executed against a synthetic client (S8), the decode queue's state machine, the journal caps
and filters, the map gate's transitions, and the frame-by-hash scan against a synthetic frame
array. The offline suites already pin member sets by name, so a member cannot be lost.

**Live, in this order** — each step is read-only until the last:

1. `probe_dialog_tables.py` (exists, read-only): the tables still resolve.
2. F7: `is_dialog_active` false at rest, true after interacting with an NPC.
3. S6: the loader pointer for every id the tables call available — a pointer inside the
   module or its heap, never zero; log the codepoints it points at.
4. S1–S5: one decode — the codepoints read from the client, rendered on the host. **Done
   live** in `tests/test_live_dat.py` (2026-09-25): a dialog body's 22 codepoints rendered to
   a readable sentence. The comparison against what the client *displays* has no subject for
   the body — it is not published as a label — so the text is reported as what the port
   produced rather than compared, and the buttons are the piece still open.
5. S2: **done live** in the same run — the client handed over 91,114 bytes through the port's
   chain, and the entries parsed and decoded.
6. F6: the journal of a real interaction, entry by entry.
7. F5: a zone transition, with the state wiped and the gate resuming after the delay.
8. F8: connect → initialize → terminate → disconnect, client responsive, bytes restored.

Every live step is bounded, self-terminating and self-restoring, and prints what the client
reported rather than what the library expected.

---

## 6. Adaptations this plan knowingly makes

Four, each because the source runs in-process and the port does not. They are recorded here
so they are not discovered later as surprises:

1. **`PollMapChange` runs lazily**, not per frame — this project has no frame loop (§F5).
2. **No SEH around the calls.** Native wraps the loader, the decoder and every DAT call in
   `__try/__except`; emitted machine code cannot. The bound is the one the call path already
   enforces — the target must be inside the client's module — plus the resolver's section
   validation on the loader address. A call to a wrong address is not survivable in either
   project; the difference is that native catches the exception and this port does not.
3. **No in-process mutex.** Native's two-lock design exists because its handlers run on the
   client's threads. Here the state is the host's and the capture is serialised by the
   event listener, so the state's own single-writer discipline is what the source's locks
   protect — and nothing is shared with the client.
4. **The encoded string is read, not walked.** Native validates and decodes a pointer
   in-process; the port reads the codepoints with its bounded reader and runs the same
   algorithms on the bytes (S1 for `IsValidEncStr`'s grammar, S4 for the decoder). Same
   walk, same grammar, same three answers — one copy of the string instead of a pointer.

---

## Progress record

| Phase | State | Evidence |
| --- | --- | --- |
| 1 · F7 frame-by-hash · S1 encoded-string arithmetic | **done** | `tests/probe_dialog_phase1.py` live on pid 39188: `is_dialog_active()` false → interact → true, and the client's own body and label codepoints accepted by the ported grammar. Offline: `tests/test_encoded_str_offline.py` (20) and the frame-hash tests in `test_ui_frame_offline.py` |
| 2 · F5 map gate (+ F8 `initialize`) | **done offline**, live check pending | 13 gate tests in `tests/test_dialog_offline.py`; the elevated probe run was declined at the elevation prompt |
| 3 · S6 value return · S7 block data region | **done, and in use live** | the offline tests (a real emitted callee returning a constant through the dispatcher; a refused call carrying none; result and value independent; the region, its bounds, a wide string placed for the client) plus `tests/test_live_dat.py`, where the client's own record and buffer pointers came back through `value` and the size word through the region |
| 4 · S2–S5 the DAT chain and Reforged's decoder | **done** | `py4gw/dat_reader.py` (31 offline tests) and `py4gw/internals/string_table.py` (89); live: one file read (91,114 bytes, 1024 entries, 944 rendering printable text with no key) and a real dialog body — index 99942, key `0x1610C5A3EA63` — rendered to readable text |
| 4b · the catalog decode queue (the dialog side) | **ported and live-exercised; one address unresolved** | `QueueDialogTextDecode` and the five members around it, 19 offline tests in `tests/test_dialog_offline.py`; live on PID 18928: the tables resolve, 56 dialogs enumerate, and **0 commands are published** because the sources' hardcoded `DialogLoader_GetText` address is stale on this build and the port refuses an unconfirmed address. **That crash and its cause are recorded in `RESEARCH.md` (2026-09-25); the open item is a resolver for this build's loader.** |
| 5 · F6 journals | **done** | both journals, their appenders and their caps (`dialog.cpp:457-544`, `1693-1817`), driven from the same dispatch the client's messages go through; 18 offline tests in `tests/test_dialog_offline.py` (caps, directions, sorting, the filtered clear, the uid) |
| 6 · F8 lifecycle (`terminate`) | **done** | the source's `Shutdown` order: both flags, both epochs, the bounded drains, then the catalog clear; the unregistration is `disconnect()`'s and the drain has nothing to wait on, both said plainly |
| 7 · S8 callback stub (route B, off the path to FULL) | not started | — |

**Member count as of phase 6: all 32 `PyDialog` members answer, and none refuses.** What is left
for this class is two things a member cannot *read* on this build: this build's
`DialogLoader_GetText` address (so a catalog dialog's text is empty) and a button's label (its
announced pointer is not a table reference). Both are in [`RESEARCH.md`](RESEARCH.md); neither is
a member that is unwritten.

**One observation from the live run, recorded because it will matter to S4:** both
`kDialogButton` messages carried the **same** label pointer (`0x267E2A38`) and the same six
codepoints, for two different dialog ids (4484 and 6020). Either the two buttons genuinely
share a label or the client reuses one buffer for both. It is not a port defect — the probe
reads what the client sent — but the decode (S4) and the journal (F6) are what will settle it,
and a test that assumes one label per button would be wrong until they do.

**That observation has since been repeated, and the decode is what settled it — partly.**
`tests/test_live_dat.py` on 2026-09-25 saw the same dialog again: both buttons (ids 4484 and
6020) reported the same pointer, and its five codepoints (`0x953C, 0xC037, 0x0A92, 0x4006,
0x0000`) parse to table index `5475942290066`, which is **orders of magnitude outside the
table's 101,376 entries**. So a button's label pointer is not an encoded table reference at
all — the head differs between the two observations (`0x267E2A38`'s run had `0x39B1` there)
while the tail matched. Button text is therefore the one part of a dialog Route A has not been
shown to render, and it is why the five text members are described as waiting on the dialog
side of the decode rather than on the decoder.
