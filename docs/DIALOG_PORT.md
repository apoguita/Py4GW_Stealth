# Dialog port

`py4gw/dialog.py` is the port of Reforged's `Py4GWCoreLib/Dialog.py` (173 lines) **and**
of the surface that module reaches: native `PyDialog` — 32 static methods bound at
`dialog_bindings.cpp:103-138`, plus six record classes at `dialog_bindings.cpp:14-82` —
backed by `src/GW/dialog/dialog.cpp`, 1,847 lines that keep dialog state by listening to
the client's own UI messages and decoding text asynchronously.

The class came in because one `Player` member needed it: `SendAutomaticDialog` calls
`Dialog.get_active_dialog_buttons()` (`Py4GWCoreLib/Player.py:854-900`). The port is the
whole class, not that member's slice — the facade, the surface, every record, and the
state behind them, with each member either serving the value the source serves or naming
exactly what it still needs.

**The plan for finishing it** — the seven features to port first, in dependency order, and
what each one unblocks beyond `Dialog` — is
[`DIALOG_MIGRATION_PLAN.md`](DIALOG_MIGRATION_PLAN.md).

## Source structure

| Layer | In the source | Here |
| --- | --- | --- |
| Facade | `Dialog.py` — 10 module members | module functions and two of the six records |
| Surface | `PyDialog` (32 statics + 6 records) | `class PyDialog` and the state it reads |
| State | `dialog.cpp` file-scope variables, written by four message handlers | module-level state in `dialog.py`, written by the connection's capture |

The facade is small and its member list is exact. `Dialog.py` declares ten: `_safe_call`,
`_call_native_dialog_method`, `_coerce_native_list`, `sanitize_dialog_text`,
`_parse_inline_choice_dialog_id`, `extract_inline_dialog_choices_from_text`,
`get_active_dialog`, `get_active_dialog_buttons`, and the two records `ActiveDialogInfo`
and `DialogButtonInfo`. **Nine work; one reports a divergence** (`_call_native_dialog_method`,
below).

The other four records — `DialogInfo`, `DialogTextDecodedInfo`, `DialogEventLog`,
`DialogCallbackJournalEntry` — are native-only. Reforged's Python wraps none of them,
and they are ported because they are the return types of surface members.

## Where each member reads from

Every value the facade returns is state in this module, and every piece of that state is
where `dialog.cpp` keeps its counterpart:

| State | Set by | Source |
| --- | --- | --- |
| `_dialog_agent_id` | the body that opened the dialog | `dialog.cpp:47-49` (`active_dialog_cache`), set at `803` |
| `_dialog_id` | a body and a send both return it to zero; nothing sets it otherwise | the same — its nonzero source is the metadata tables, so `_dialog_id_authoritative` stays `False` here |
| `_context_dialog_id` | the dialog this project sent, immediately, and again from the body that answers it | the same, set at `971` and `815` |
| `_dialog_id_authoritative` | cleared by a body and by a send | the same |
| `_dialog_message` | the body's text — empty until the decode exists | the same |
| `_dialog_buttons` | one append per button the client announces | `dialog.cpp:86` |
| `_last_selected_dialog_id` | the last dialog sent | `dialog.cpp:94`, set at `967` |
| `_pending_context_dialog_id`, `_pending_context_agent_id` | a send, cleared by the next body | `dialog.cpp:95-96`, set at `968-969` |

## The four messages, and which two are watched

`dialog.cpp:1273-1288` registers four UI-message callbacks. This project watches the two
that carry state, through the connection (`py4gw/client.py`):

| Message | Client packet | What happens |
| --- | --- | --- |
| `kDialogBody` (`0x100000A6`) | `DialogBodyInfo {type, agent_id, message_enc}` | the capture reads the agent from the packet's second word and replaces the whole state |
| `kDialogButton` (`0x100000A3`) | `DialogButtonInfo {button_icon, message, dialog_id, skill_id}` | the capture appends one button: icon, dialog id |
| `kSendAgentDialog` / `kSendGadgetDialog` | one word | **not watched** — see below |

The last two are not watched, and that is deliberate rather than a gap. The runtime sees
them because it *sends* them; this project calls the function the handler calls
(`agent.send_agent_dialog_func` / `agent.send_gadget_dialog_func`), so the message never
travels. What that handler does with it — six assignments inside one lock
(`dialog.cpp:967-972`) — happens instead in `_note_sent_dialog`, called by
`Player.SendDialog` where the send is made. Same values, same order.

**Which is why a button needs no decoder.** The packet is sixteen bytes, so the whole of
it fits in the four words the observer records, and the id a caller sends is a word in
the event rather than a string to decode. Only `message` — the label — is encoded, and
no ported caller reads it.

## The state machine

Transcribed from `dialog.cpp`, with the source's order and short-circuits:

1. **A body replaces everything** (`dialog.cpp:774-825`). It records the agent; then, if
   a dialog was just sent *and* the pending agent is either zero or this same agent, the
   sent dialog's id becomes the context id. Then the pending pair is cleared, the dialog
   id returns to zero, the button list is emptied, and the message is empty. An agent
   with no dialog id is still a dialog — the body arrives before the buttons do.
2. **A button appends** (`dialog.cpp:605-620`, `727-739`). One entry, in arrival order.
   The list is capped at `kMaxActiveDialogButtons` — 64 (`dialog.cpp:43`) — and an
   overflow drops the **oldest** entries first, as the source's erase-from-the-front
   does. The button's label is decoded asynchronously in the source and lands in the
   same record; here the entry says `message_decode_pending`, which is the source's own
   state while a decode is in flight.
3. **A send is remembered, and it takes effect at once** (`dialog.cpp:967-972`). The
   pending id and the pending agent (the agent of the dialog that was *open* when the
   send happened, read at `955`) are recorded for the body that answers it, and
   `last_selected_dialog_id` is set — that is what `Dialog.get_last_selected_dialog_id()`
   reports. In the same lock the sent id becomes the **context** id, the dialog id
   returns to zero, and the authoritative flag is cleared. So a dialog this project just
   sent is displayed right away as far as `is_dialog_displayed` is concerned, and the
   body that answers it for a different agent takes that back. This is six assignments,
   not three, and the offline suite pins the consequence.
4. **Clearing** (`dialog.cpp:1819-1845`). The connection calls `PyDialog.initialize()` when it
   installs — the source's `Initialize` → `ClearCache` — so state from an earlier connection in
   the same process cannot be read as if it belonged to the client now connected. `_reset()` is
   the *offline suite's* way back to the module's as-loaded state; the connection never calls it.

## The surface: 32 of 32 answer

Every name below is native's, in native's declaration order. Nothing is added. **No member
refuses**; the two items that are not finished work are named after the table and are both about
*what a member can read on this build*, not about the member being written.

| Member | State |
| --- | --- |
| `initialize` | **served** — clears the state and takes the gate from the live map; the connection registers the capture immediately after, which is the source's order |
| `terminate` | **served** — the source's ``Shutdown``: both flags, both epochs, the bounded drains, then the cache clear. The *unregistration* is `disconnect()`'s here, and the module says so |
| `clear_cache` | **served** — the state, both journals, both epochs, the gate, and the catalog cache (``ClearCache``, ``dialog.cpp:1819-1845``) |
| `get_active_dialog` | **served** |
| `get_active_dialog_buttons` | **served** |
| `get_last_selected_dialog_id` | **served** |
| `is_dialog_displayed` | **served** |
| `is_dialog_active` | **served** — the NPC Dialog frame by hash, through the frame array |
| `is_dialog_available` | **served** — flags column, `& 0x1` |
| `get_dialog_info` | **served** — the five columns, plus `content` from the catalog's decode cache |
| `enumerate_available_dialogs` | **served** — one `get_dialog_info` per available row, in id order |
| `read_dialog_flags` | **served** |
| `read_dialog_frame_type` | **served** |
| `read_dialog_event_handler` | **served** |
| `read_dialog_content_id` | **served** |
| `read_dialog_property_id` | **served** |
| `get_dialog_text_decoded` | **served** — the queue is ported; on this build it answers "" because `DialogLoader_GetText`'s address from the sources' table is stale and refused |
| `is_dialog_text_decode_pending` | **served** |
| `get_dialog_text_decode_status` | **served** — the cached rows, then the pending ones (`GetDecodedDialogTextStatus`) |
| `get_dialog_event_logs` | **served** — every recorded message, capped at 512 |
| `get_dialog_event_logs_received` | **served** |
| `get_dialog_event_logs_sent` | **served** |
| `clear_dialog_event_logs` | **served** — all three lists |
| `clear_dialog_event_logs_received` | **served** |
| `clear_dialog_event_logs_sent` | **served** |
| `get_dialog_callback_journal` | **served** — sorted by tick, then event, then direction |
| `get_dialog_callback_journal_received` | **served** |
| `get_dialog_callback_journal_sent` | **served** |
| `clear_dialog_callback_journal` | **served** — all three lists |
| `clear_dialog_callback_journal_received` | **served** |
| `clear_dialog_callback_journal_sent` | **served** |
| `clear_dialog_callback_journal_filtered` | **served** — no filter clears everything, and any filter rebuilds the direction lists from what is left (``dialog.cpp:1769-1817``) |

Two things a member cannot produce on this build yet, both named and both researched rather than
guessed at:

1. **A catalog dialog's text** — `get_dialog_info(...).content`, `get_dialog_text_decoded`, and
   the `content` of every row `enumerate_available_dialogs` returns are `""`, because
   `DialogLoader_GetText`'s address in the sources' table is stale here and the port refuses an
   unconfirmed address (see the section below).
2. **A button's label** — `DialogButtonInfo.message_decoded` is empty, because the pointer the
   client announces for a button does not carry a table reference (measured twice;
   [`RESEARCH.md`](RESEARCH.md)).


## The catalog decode queue, and the loader address it needs

`QueueDialogTextDecode` (`dialog.cpp:1136-1254`) and the members around it are ported: the map
gate, the id bound, the cache and pending checks, the epoch and shutdown re-checks, and every
failure branch that caches empty text, caches the raw string, or only clears the pending flag.
The text is the client's own: the copy is placed in a decode slot of the shared block and
`validate_async_decode_str_func` is called with the emitted stub as its callback, which is
`AsyncDecodeStr` handed the request its caller prepared (`dialog.cpp:1241`, `ui_methods.cpp:2582`).
The client decodes it and calls the stub back, the stub fills the slot, and the text arrives as a
completion event — the same three steps the source takes, with the process boundary in the middle.

**What it needs is one address: `DialogLoader_GetText`, and the sources' constant for it is stale
on this build.** `DialogMemory::DIALOG_LOADER_GETTEXT = 0x0079EEF0` rebased by
`ToRuntimeAddress` is `0x9AEEF0` here, and that is **inside** the function at `0x9AEEB0` — a
two-pointer container search (`mov ebx,[ebp+8]`, `mov edi,[ebx]`, `cmp esi,[ebp+0xc]`), not a
one-argument loader. The port therefore:

- **rebases with the sources' constant**, not with the module's header field — this client's own
  loader rewrites its header to the address it was loaded at, so a header-based rebase was a
  no-op and put the first call 0x210000 below the address the sources mean
  (`RemoteScanner._LINK_IMAGE_BASE`, and the crash record in [`RESEARCH.md`](RESEARCH.md));
- **confirms a candidate's entry bytes** (a prologue, or a `jmp rel32` thunk to one, inside
  `.text`) and answers `0` otherwise, which is the source's own "no loader" path — empty text,
  pending cleared (`dialog.cpp:1166-1177`);
- **does not walk back to a function start**, deliberately: `to_function_start(0x9AEEF0)` is
  `0x9AEEB0`, a real entry the check would accept, and calling *that* with a dialog id would
  dereference an integer.

So the remaining work is a **resolver for this build's `DialogLoader_GetText`** — identified by a
signature rather than by the table's address. The client carries its own dialog assertion strings
and source paths for exactly that kind of anchor (`dialog < DIALOGS`,
`DialogGetFrame(frame, dialog)`, `P:\Code\Gw\Ui\Dialog\DlgKey.cpp`, …); none is referenced by a
`push imm32`, so the next step is the catalog's `find_use_of_string` + `to_function_start` pair
over them, which is how the eight DAT resolvers find their functions.

## The metadata tables, and the work that opened them up

The tables were the largest single piece of outstanding work in the port — 8 members —
and the native source names the obstacle itself (`dialog.h:80-85`): *"HARDCODED client virtual addresses rebased
onto the live module, with a validation pass and a heuristic .rdata fallback scan ...
They cannot move into `offsets/*.json` because the pattern system has no
module-base-relative op."*

**That op now exists**, which is the whole fix: `module_relative` in
`py4gw/scanner/patterns.py`, with `RemoteScanner.to_module_address()` behind it. The five
`DialogMemory` addresses live in `offsets/dialog.json` exactly as the source keeps them
in `dialog.h:94-99`, and everything that is dialog semantics rather than pattern
mechanics — the two resolution stages, the validation pass, the derivation of the other
four bases — is `DialogTables` in `py4gw/dialog.py`, the port of `dialog_patterns.cpp`.

The arithmetic is the source's: `module_base + (va - kGwImageBase)`, the constant
`0x00400000` that `ToRuntimeAddress` uses (`dialog_patterns.cpp:23-31`). **The module's own
header is not that base on this client** — its mapped `OptionalHeader.ImageBase` reads the
load address (`0x610000`) because the client's own loader rewrites it, while the file's reads
`0x400000` — and rebasing from the header made the arithmetic a no-op until 2026-09-25, which
is what put the loader call 0x210000 below the address the sources mean (`RESEARCH.md`).

**And the fallback is not decoration — on this build it is what works.** Live, read-only,
`tests/probe_dialog_tables.py` against `Gw.exe` (pid 39188, module `0x00610000`):

| Base | Resolved | Static candidate (`ToRuntimeAddress`) |
| --- | --- | --- |
| `flags_base` | `0x00B5CF10` | `0x00913920` |
| `event_handler_base` | `0x00B5CF08` | `0x00913918` |
| `frame_type_base` | `0x00B5CF0C` | `0x0091391C` |
| `content_id_base` | `0x00B5CF14` | `0x00913924` |
| `property_id_base` | `0x00B5CF18` | `0x00913928` |

The five hardcoded addresses do **not** validate on this client, so the static stage is
rejected and the `.rdata` scan supplies the bases — which is the source's design working
as written, not a workaround. The scan's result then passes the source's own validation
rules over all 58 rows: **56 rows enabled**, every flags word within `0xFFFF`, and every
nonzero event handler inside `.text` (`0x0070B8D0`, `0x00AF3450`, …). `DialogLoader_GetText`
rebases to `0x0079EEF0`.

## What is still open, and it is not a member

**The journals are ported** — both of them, with the source's caps and ordering: each dialog
message appends a row to the whole log *and* to its direction's list (capped at 512 from the
front), and the callback journal records a richer row per announcement and per send (capped at
1000, sorted by tick, then by event — body, choice, sent — then incoming before sent). The rows
carry what the source's do: the packet bytes the client sent, the tick, the map and model ids,
and the ``map:model:agent`` uid.

**One thing no member can produce on this build yet**, and it is **deferred to a later pass by the
project owner**: this build's ``DialogLoader_GetText``, so a catalog dialog's ``content`` is empty
(the refusal is the source's own "no loader" value).
The button **caption** used to be listed here beside it, and it is the one item in this port whose
finding was wrong for a reason worth keeping: the label was read from the host, after the client's
own call, and what it read there was a buffer the client reuses. The paragraph below is what the
measurement replaced it with.

**What is left is the loader, and the caption is in.** The reason the caption took this long is
measured rather than argued (``tests/probe_dialog_label_fill.py``, 2026-09-25): **the pointer a
button announces is a buffer the client reuses.** Both buttons of one dialog announced the same
pointer, and it held 19 distinct contents in two seconds — heap-pointer heads, small numbers,
loading-screen tip text — so the string this port handed over was never the label, and the
client's parser asserted on a scratch buffer's contents. The source never reads there: its
handlers are registered at altitude ``0x1`` (``dialog.cpp:1273-1292``) and ``SendUIMessage`` runs
those **after** the original send returns (``ui_methods.cpp:1390-1404``), so
``DupWideStringSafe(info->message)`` (``dialog.cpp:639``) happens inside the client's own call.

**The port reads there too now, and the label is a real table reference.** The observer is placed
in the source's moment and its emitted code **copies the string** — at the offset each watched
message declares — into the event the host reads (``payload.build_observer``,
``EVENT_TEXT_WORDS``); ``_on_button`` takes that copy as the source's ``encoded_copy`` and runs
``dialog.cpp:641-708`` as written, including the handover. Live, 2026-09-25: the body's copy is
word-for-word what this side reads at its own pointer, the two buttons' copies decode to
*"Would you tell me more about the Northern Support bonus?"* (index 99994) and *"…the Guild versus
Guild bonus?"* (index 99946), and the module answers exactly those captions through the client's
own decoder, with both ``recv_choice`` rows carrying them. The announced pointer read from here
still holds ``743b c047 0a92 4006`` and names nothing — which is what the port was reading before.

**One item remains, and the project owner has deferred it to a later pass: this build's
`DialogLoader_GetText`.** Every member of the class answers, and a button's caption is produced; a
catalog dialog's `content` is empty because the client function the source calls through has not been
identified here yet. **The sources are complete and working** — `Reforged Native` resolves a loader
and calls it — so the function exists to find, and the last pass settled where to look. Until it is
identified the loader resolution answers the source's own "no loader" value, so the content is empty
rather than wrong. **It stopped asking the client and read the
file** (`Gw.exe` on disk, no hook, no elevation; `tools/dialog_loader_hunt.py` and
`tools/ghidra_scripts/`), and what it establishes sharpens the search:

- the port's own `ResolveFlagsBase`, run over the file, reproduces the live table exactly (flags
  `0x0094CF10` file = `0x00B5CF10` live, the module's `0x210000` relocation), so the file is the
  binary every live reading came from;
- **the client inlines the path a loader wraps on this build.** The only code that reads a dialog's
  text id (`row + 0x14`) is the dialog window itself (`0x004E2300`, `IUi::Game::DialogShow`), and
  Ghidra finds **exactly one** reference to the table's start in the entire module — inside that
  same function. So the loader is not a table reader here, and finding it means finding the function
  the client's *announce* path uses rather than one that indexes `s_floatingDialogs`;
- the client's text module *is* identified (`FUN_007c9860` → `FUN_007c9880` → `FUN_007cbbb0`: a
  shared buffer, an encoded string, `WORD_VALUE_RANGE = 0x7F00`), which is also why the pointer a
  dialog announces is a buffer the client reuses — the measurement that moved the label read inside
  the client;
- **Native's constant is stale for this build**, and here it lands in a packet deserializer:
  `0x0079EEF0` rebases to `0x9AEEF0`, inside `FUN_0079EEB0` (fixed-size records, an `alloca` probe, a
  security cookie). Refusing it is right on evidence, not on caution — and it is the reason the
  port's own resolution answers `0` today.

So until the function is identified, `resolve_loader_get_text` answers `0` and the catalog takes the
source's own missing-loader path (empty text cached, pending cleared — `dialog.cpp:1166-1177`), which
is one of the source's own cases rather than a substitute for one. **This is a work item, not a
divergence**: the sources resolve and call a loader, so the function is there, and the port's job is
to find it on this build. The two routes that remain are named in
[`RESEARCH.md`](RESEARCH.md) — a witness (hook the confirmed encoder and drive an interaction, which
names what builds a dialog's codepoints) and the client's announce path read statically from
`DialogShow`'s callers. The tooling and the decompiled row semantics (`+0x00` proc, `+0x04` name,
`+0x08` style, `+0x0C` create flags, `+0x10` availability, `+0x14`/`+0x18` text ids) are there too.
The reach of the item is unchanged: only ``get_dialog_text_decoded`` and
``get_dialog_info().content`` read through the loader, and the button-caption fallback cannot reach a
real button's id (`MAX_DIALOG_ID = 0x39`).

## Adaptations

| Member | Source | Here | Why |
| --- | --- | --- | --- |
| `_call_native_dialog_method` | looks the method up on `PyDialog.PyDialog` with `getattr`, falling back to `default` | **reports a divergence** | Both halves are unportable as written: there is no binding object outside the client (the reason `Player.player_instance` diverges), and this project does not reach a member through a dynamic name. The ported surface is `class PyDialog`, so the facade calls its methods directly and there is no absent case to fall back from. |
| `ActiveDialogInfo.__init__` | takes a `PyDialog` object and reads its fields with `getattr` | takes the five values, in the order the source reads them | `native` is kept and is always `None`, for the same reason as above. |
| `DialogButtonInfo.__init__` | a native button object's fields | the source's keyword form | The one this port can build. |
| `send` recording | the runtime's `kSendAgentDialog` handler | `_note_sent_dialog`, called by `Player.SendDialog` | The message is never sent, so its handler never runs. |
| Button `skill_id` | the packet's fourth word | not carried into the record | `DialogButtonInfo` in Reforged's Python has no such field, and the record is the facade's. The word is in the event, so a member that needs it has it. |
| Button label | the label decode, or the catalog's text for the button's id (`dialog.cpp:646-708`, `1632-1664`) | **ported as written**: the copy the observer takes inside the client's call is the source's `encoded_copy`, and `641-708` runs branch for branch — its own text when the check rejects it, otherwise the request, the pending map with its cap, the handover and the release path | The port's host-side read of the announced pointer had to go first, and that was the finding: the pointer is a buffer the client reuses (19 distinct contents in two seconds; both buttons named one address — `tests/probe_dialog_label_fill.py`), so handing over what this side read asserted inside the client (`IsParam(data)`, `TextParser.cpp:724`, pid 30560, fatal in this build) — **not** a check the client makes and the source does not. With the copy, the branch runs and the captions come back: live 2026-09-25, `'Would you tell me more about the Northern Support bonus?'` and `'…the Guild versus Guild bonus?'`. |
| Refusal diagnostics | reported through `PySystem.Console.Log` | not carried over | That is Reforged's console *inside* the client, and there is no external equivalent. The returns the diagnostics accompany are ported. |
| `clear_cache` | clears the cache, the buttons, the last id, the pending send, the two button-label caches, the decoded-text caches, the tables and the journals | clears the same set through `_clear_runtime_state`, plus the decoded-text caches, the journals and the table invalidation | `ClearCache` reaches `InvalidateDialogTables` through `ClearCatalogCache` (`dialog.cpp:1256-1262`), and the label caches are cleared there and in `ObserveMapChange` (`1829-1830`, `583-584`) — which is the same wipe here. |
| The map-transition **gate** | `PollMapChange` runs on the runtime's update loop (`dialog.cpp:1388-1409`); the message handler only *observes* (`594`) | `_maybe_resume` runs inside the capture and `_poll_map_change` inside the four state readers (`get_active_dialog`, `get_active_dialog_buttons`, `get_last_selected_dialog_id`, `is_dialog_displayed`) | **The one adaptation of execution model that reaches behaviour.** There is no frame loop here, so a gate a transition closed would never reopen and the next message would be refused; and a member called after a map change would report the state the wipe has not yet run on. The decisions are the source's, branch for branch, and the check can only ever run *later* than the source's. |
| The decode's **request and transport** | the request is a heap object, handed to `AsyncDecodeStr` as `param`, and the client calls back into the runtime (`dialog.cpp:863-882`, `1239`, `692`, `885`) | the request is recorded against a **decode slot** of the shared block, the copy is placed in that slot, `validate_async_decode_str_func` is called with the emitted stub as the callback, and the completion arrives as a `STRING_DECODED` event (`py4gw/ui/async_decode.py`) | Nothing of this project's runs inside the client, so the callback has to be machine code placed there and the text has to be carried out. The order is the source's — prepare the request, then call — and the wrapper's three refusals answer with the source's own values (`L""`, `L"!!!"`, `L""`). |
| The string a decode is handed | `DupWideStringSafe` copies a NUL-terminated wide string with `wcslen` inside a `__try` (`dialog.cpp:237-252`) | a bounded read of at most `MAX_DIALOG_TEXT_CODE_UNITS` (4096) units, no terminator inside it being the failed copy | This side has no SEH frame, so the read is bounded instead. The bound is far past any dialog text; a longer string is reported as a failed copy rather than read on. |
| The drain in `terminate` | waits on a condition variable its decode callbacks notify, logs past `kDialogAsyncDrainTimeout` and **keeps waiting** (`dialog.cpp:1343-1358`, `1367-1385`) | waits up to the same timeout, then raises naming the count | Waiting for ever would hang a disconnect on a stub the client may never call, and continuing past the timeout would free memory the client can still write into. The fail-closed part is kept; the log has no external equivalent (see the diagnostics row), so the report is the exception. |
| The loader's address | `ResolveDialogLoaderGetText` returns the rebased constant unconditionally (`dialog_patterns.cpp:261-269`) | the candidate's entry bytes are confirmed first, and a candidate that is not a function answers `0` | An address was called here that crashed the client on 2026-09-25; the sources' constant is stale on this build and lands inside a packet deserializer (`FUN_0079EEB0` — the file, decompiled, in [`RESEARCH.md`](RESEARCH.md)). The confirmation is this project's, and it is why every catalog id caches empty text today — the finding, with its search method, is in [`RESEARCH.md`](RESEARCH.md). **The four helpers it uses** (`_is_function_entry`, `_entry_kind`, `_is_prologue`, `_read_head`) have no source counterpart, and the check answers the source's own "no loader" branch (`1166-1177`), which is what keeps the behaviour legal: an unresolved loader is one of the source's cases, not a substitute for one. |
| The body case's **flow** | one `append_immediate` flag and one `immediate_text`, set by the branches and appended **once** under one guard at the end (`dialog.cpp:827-928`) | three early returns, each with its own guarded append (`_append_body_text_row`) | **A shape divergence with no value difference found**, named here as work rather than left implicit: the guards reproduce the source's, but the *flow* is not the source's, and the same applies to the button case (`_append_button_journal_entry`) and to the three row builders that carry both of the source's sites' guard sets. Closing it means the source's flag-and-append-once structure, one case at a time, verified as it moves. |

One facade behaviour is worth noting because it looks like a gap and is not:
`get_active_dialog_buttons()` falls back to parsing choices out of the body text when
the client announced no buttons (`Dialog.py:165-173`). The fallback is ported, and it
finds nothing today because the body text is empty. The source behaves the same way on
an empty body — this is a **pending decode**, not a missing branch.

## Verification

- `tests/test_dialog_offline.py` — **120 tests**. They pin the surface by name: the 32
  statics and their order (the list *is* the binding's, and the test fails if a member is
  dropped or added), the 6 record classes, that **no member of the surface refuses** — the
  one refusal left in the module is the facade helper that would reach a binding object by
  dynamic name, and it is a documented divergence, not a member —
  the facade's
  ten members exist with the source's shapes, and they drive the state machine through
  synthetic events: a body replacing a button list, buttons appending in order with the
  list staying capped at 64 from the front, a sent dialog being tied to the body that
  answers it and dropped when a different agent answers, the six assignments a send
  makes before any body arrives, `clear_cache`, the served getters' own cases, and the
  inline-choice parser and sanitiser on the source's.
- **The table resolver, offline but against a synthetic client** (`DialogTableTests`):
  the static rebase when it validates, the `.rdata` fallback when it does not, the
  derivation of the other four bases from the scanned one, a table that fails validation
  resolving to nothing (and staying marked resolved, as native does), a static stage that
  fails falling through to the scan, invalidation re-resolving, the loader address
  surviving invalidation, and an unreadable word reporting `None` rather than raising.
- **Live, read-only** (`tests/probe_dialog_tables.py`): the five bases, the stage that
  supplied them, and the 56 enabled rows — the table above.
- **Offline, against `Gw.exe` itself** (`tools/dialog_loader_hunt.py`; no client, no elevation):
  `rows` runs **the port's own** `ResolveFlagsBase` over the file and finds flags `0x0094CF10` with
  all 58 rows matching the live reading above; `table-users` finds exactly one reference to the
  table's start in the module and no pointer to it anywhere in the data sections; `constants`
  reports that Native's five data addresses describe none of the three `Gw.exe` images on this
  machine. The decompilation behind the row semantics is `tools/ghidra_scripts/DialogTableReaders.java`.
- **Live, in `tests/test_live_player.py`** (`test_z_interacting_reaches_the_client`):
  interacting with an agent makes the client report a dialog, and the test asserts the
  module captured **that same agent** out of the same message, then reads the announced
  buttons and asserts every one carries a nonzero dialog id.
- **Live, opening a real dialog** (`tests/probe_dialog_open.py`): the probe picks the
  closest NPC, interacts with it, and waits for the client to walk there and open the
  dialog — the only way to see the state, because nothing in the client offers a dialog
  on request. Against pid 39188 the closest NPC was agent `17` at 109.6 units; the dialog
  opened 0.2 s after the call, the module captured **agent 17**, and the client announced
  **2 buttons, ids 4484 and 6020, icon 11**, both with their label decode pending.
  `is_dialog_displayed(4484)` is `False`, which is native's answer rather than a miss:
  the open dialog's own id is zero until a send records one, and 4484 is a *button's* id.
- **Live probe** (`tests/probe_dialog_surface.py`, read-only): after an interaction the
  client reported agent `17`, and the button messages carried ids **4484** and **6020**,
  read from the packet words as they arrived.
