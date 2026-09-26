# String decoding: where it happens, and what the port needs

**Why this document exists.** The first version of
[`DIALOG_MIGRATION_PLAN.md`](DIALOG_MIGRATION_PLAN.md) treated "the text decode" as one
feature behind one call, and dismissed the validity check as "a bounded read we can do
ourselves". That was wrong in both directions, and this document is the correction: string
decoding is a **subsystem with four distinct routes**, most of its consumers are not
`Dialog` at all, and its largest route is **pure Python that Reforged already ships** — so
the port's cheapest path to text is not the in-client callback the first plan centred on.

Nothing here is a new design. Every route below is one of the two source projects' own, with
the file and line it lives at.

---

## 1. The four routes

| Route | Where the decoding happens | Whose | Used by |
| --- | --- | --- | --- |
| **A · gw.dat + pure Python** | `Py4GWCoreLib/native_src/internals/string_table.py` (970 lines) + `internals/encoded_strings.py` | Reforged's own decoder | Reforged's `Agent.GetNameByID`, item names/descriptions, quest strings, chat text |
| **B · in-client async decode** | `GW::ui::AsyncDecodeStr` → `g_validate_async_decode_str_func` (`ui_methods.cpp:2582-2607`) | Native's | Native's dialog text and labels, agent name, item name, quest strings, chat log |
| **C · the client decodes a frame's label** | `PyUIManager.get_text_label_decoded_by_frame_id` | Native's | Reforged's frame tree (`FrameTree/frame.py:1297`) |
| **D · encoded-string arithmetic** | `GW::ui::UInt32ToEncStr` / `EncStrToUInt32` / `IsValidEncStr` (`ui_methods.cpp:2631-2656`, `2613-2629`) | Native's, **pure arithmetic, no client state** | ids embedded in text — including dialog inline choices |

A and B are not interchangeable implementations of one thing: A decrypts the game's string
tables out of `gw.dat` on the host, B asks the running client to render a message with its
own parameter substitution. Both are in production, in different projects, and both decode
the same family of encoded codepoints.

---

## 2. Route A — Reforged's decoder, and what it actually needs

This is the route the first plan barely mentioned, and it is the one that matters most,
because **it runs outside the client entirely**. Its pipeline, from the file's own header
(`string_table.py:1-24`):

```text
encoded codepoints ──_parse_codepoints──▶ (table_index, uint64_key)
gw.dat string table ──[table_index]────▶ raw entry bytes
raw entry ──key-derived RC4──▶ bit-unpacked ──▶ display text
```

with a 32-entry character table, `base_char`/`bits_per_char` handling, a special case for
raw UTF-16LE (`base_char=0, bpc=16`), player names bypassing all of it (prefix `0xBA9` +
inline ASCII), caching by codepoint tuple, and a formatted-expression grammar for
parameterised strings (`_decode_formatted_tree`, `_decode_formatted_stream`,
`_decode_codepoints_segment` — `string_table.py:497-660`).

**The only thing in that pipeline that touches the client is getting the table itself.** The
chain, exactly as the source runs it:

| Step | Source | What it needs from us |
| --- | --- | --- |
| 1. language + file slots | `TextParser` context: `language_id`, `entries_per_file`, `language_slots[language]`, `get_file_slot(slot_idx, language)` → `file_hash` (`string_table.py:700-722`) | **ported** — `py4gw/context/text_parser_context.py`, live: 11 languages × 99 slots, `entries_per_file` 1024 |
| 2. read a dat file | `_load_dat_file` → `PyDatReader.read_file_by_hash(file_hash)` (`string_table.py:665-666`) | **ported** — `py4gw/dat_reader.py`, live: 91,114 bytes read from the client |
| 3. parse entries | `_parse_string_file(file_data, slot_idx * epf, table)` → `{table_index: bytes}` | **ported** — `py4gw/internals/string_table.py`, live: 1024 entries |
| 4. decode | `decode(raw)` → `_parse_codepoints` → `_decode_entry` (RC4 + bit-unpack) | **ported**, live: a real dialog body rendered |
| 5. formatted strings | the grammar above, plus `GWStringEncoded.decode_with_amount/plain/rarity/singular` (`encoded_strings.py`) | **the grammar is ported**; `encoded_strings.py` is not |
| 6. when the load may run | `load_string_table` **enqueues on the game thread** (`PyGameThread.enqueue`, `string_table.py:775-776`) | ported, adapted: there is no frame loop, so the load runs at the point of request and every client call inside it is issued on the client's own thread |

**Step 2 is the whole external dependency, and it is four calls plus two pure functions.**
`PyDatReader.read_file_by_hash` is `dat_reader_bindings.cpp:11-18` → `GWDatReader::ReadDatFile`
(`gw_dat_reader.cpp:1441-1461`), and `EnsureHooks()` (`1472-1497`) turns out to resolve the
**same eight client functions our `offsets/gw_dat_reader.json` already holds** — it installs
no detours:

```text
FileHashToFileId(hash)                      pure computation, arenanet_file_parser.cpp
  ├─ OpenFileByFileId(...)      → RecObj*   value-returning call   (optional; the fallback is below)
  ├─ FileHashToRecObj(hash,1,0) → RecObj*   value-returning call
  ├─ ReadFileBuffer(rec, &size) → uint8_t*  value-returning call, writes size through a pointer
  ├─ CopyBytes(bytes, out, size)            a bounded read we already do
  ├─ FreeFileBuffer(rec, bytes)             call
  └─ CloseRecObj(rec)                       call
DecompressDatBlob / UnpackGWDat             pure decompressor (gw_dat_unpack.cpp, ~650 lines)
```

with `ReadDatRecord` (`gw_dat_reader.cpp:135-158`) making every failure path free-and-close
correctly — a sequence worth porting as written.

**So Route A needs: value-returning calls, a writable word inside the block (the `size_out`
pointer, and the hash string the record call takes), the eight already-catalogued DAT
resolvers, and two pure-Python ports. It does not need a callback stub, and it does not need
the client to decode anything.**

**What is now ported, and what it proved live.** The whole of Route A except
`encoded_strings.py`: `py4gw/internals/string_table.py` (89 offline tests) and `py4gw/dat_reader.py`
(the port of `PyDatReader` and the chain behind it, 31 offline tests), with
`py4gw/internals/helpers.py` for the substitute fallback's string read. `tests/test_live_dat.py`
ran the whole path against pid 39188 on 2026-09-25: one file read through the client (91,114
bytes, 1024 entries parsed, 944 of them rendering printable text with no key), and then a real
dialog body's codepoints — index 99942, key `0x1610C5A3EA63` — decrypted and rendered to
readable text. That is the render comparison this document asked for, and it is in
[`RESEARCH.md`](RESEARCH.md).

---

## 3. Route B — the in-client decode, and what the first plan got wrong

Native's decoder is one call with a callback, and the call itself is not the hard part:

```c
using DecodeStr_Callback  = void (__cdecl*)(void* param, const wchar_t* value);      // ui_methods.cpp:29, 189
void AsyncDecodeStr(const wchar_t* enc_str, DecodeStr_Callback cb, void* param);     // ui_methods.cpp:2582
```

`AsyncDecodeStr` is a **guard sequence** before the decode, and every branch is a result the
port must reproduce (`2583-2607`):

| Condition | Result |
| --- | --- |
| no `g_validate_async_decode_str_func`, no string, or no callback | `callback(param, L"")` |
| **`!IsValidEncStr(enc_str)`** | `callback(param, L"!!!")` |
| no `Context::GetTextParser()` | `callback(param, L"")` |
| otherwise | save `language_id`, call `g_validate_async_decode_str_func(enc_str, cb, param)`, restore it |

Two corrections to the first plan:

1. **`IsValidEncStr` is a grammar, not a walk.** `ui_methods.cpp:283-360` is a recursive
   validator — `EncStrValidate` ↔ `EncStrValidateWord` ↔ `EncStrValidateSingleWord` ↔
   `EncStrValidateTerminatedLiteral` — over a character classification
   (`EncChrIsParam`, `EncChrIsParamLiteral`, `EncChrIsParamSegment`, `EncChrIsParamNumeric`,
   `EncChrIsControlCharacter`) with seven constants: `TERM_FINAL 0x0000`,
   `TERM_INTERMEDIATE 0x0001`, the `0x0002` segment separator, `CONCAT_LITERAL 0x0003`,
   `STRING_CHAR_FIRST 0x0010`, `WORD_VALUE_BASE 0x0100`, `WORD_BIT_MORE 0x8000`,
   `WORD_VALUE_RANGE 0x7F00` (`152-159`). It is a port of its own, and it is a **precondition
   inside** the decode: get it wrong and every decode returns `L"!!!"`.
2. **Two decode functions are resolved; one is called.** `ui_patterns.cpp:210-211` resolves
   `g_validate_async_decode_str_func` **and** `g_async_decode_string_func` together, and
   requires both — while `AsyncDecodeStr` calls only the first (`2605`).
   `g_async_decode_string_func` (`DoAsyncDecodeStrFn`, `__fastcall`) is resolved, nulled and
   exported, and **called from nowhere in `src`**. Our catalog has both resolvers, and the
   port must know which one does the work before it calls either.

Route B also needs the resident callback stub and a buffer to receive the text — the two
pieces the first plan called F2/F3, which stay on the list but apply **only to this route**.

---

## 4. Route C — the frame label route

`PyUIManager.get_text_label_decoded_by_frame_id` is what Reforged's frame tree uses for a
frame's text (`FrameTree/frame.py:1297`, with a "do not decode arbitrary option-subtree
frames as text labels" caveat in `Inventory.py:505`). It is a binding that has the client
return a frame's label already decoded. It needs the frame array (ported) and the label
call's contract, which is not yet read in this project. Small, self-contained, and it is the
only route that produces a label the client has *rendered*, so it is the natural cross-check
for the other two.

---

## 5. Route D — the arithmetic, which is portable today

`UInt32ToEncStr` and `EncStrToUInt32` (`ui_methods.cpp:2631-2656`) are pure arithmetic over
the same `WORD_VALUE_BASE`/`WORD_VALUE_RANGE`/`WORD_BIT_MORE` constants Route B validates
against — base-`0x7F00` with a continuation bit. `IsValidEncStr` uses the same constants, so
porting the constants once serves both.

**This is directly relevant to `Dialog`**: dialog ids embedded in body text (`<a=...>`) are
exactly these encoded numbers, which is what `Dialog._parse_inline_choice_dialog_id` and
`extract_inline_dialog_choices_from_text` parse. Today that parser works on whatever the body
text contains and the body text is empty; with Route D ported, the ids in the text become
readable **without any client call at all**.

---

## 6. Consumers, so the leverage is visible

| Consumer | Source route |
| --- | --- |
| `Agent.GetNameByID` | A (`Agent.py:9,147` → `decode_raw`) · B (`agent_methods.cpp:323`) |
| item names and descriptions | A (`encoded_strings.py`, with amount/rarity/singular variants) · B (`item_methods.cpp:362`) |
| quest name, description, objectives, location, npc | B (`quest_methods.cpp:105-135`, `AsyncDecodeAnyEncStr`) · A for the Python wrappers |
| chat log text | B (`player_bindings.cpp:296`) · A for the Python wrappers |
| dialog body, button labels, catalog text | B (`dialog.cpp:641, 692, 834, 885, 1205, 1241`) |
| frame labels | C |
| dialog inline choice ids | D |

Route A is therefore not "the dialog decode" — it is the route that reaches **agent names,
item strings, quest strings and chat text** at once, on the host, with no in-client
decoding.

---

## 7. The work, in dependency order

Superseding the F-numbers in the Dialog plan where they overlap:

| # | Work | Route | Kind |
| --- | --- | --- | --- |
| **S1** | The encoded-string constants + `EncStrToUInt32` / `UInt32ToEncStr` / `IsValidEncStr` | D | **pure Python, done** — `py4gw/ui/encoded_str.py`, 20 offline tests, and the client's own dialog strings accepted live |
| **S2** | The eight DAT functions through the call path: `FileHashToRecObj` / `OpenFileByFileId` → `ReadFileBuffer(rec,&size)` → bounded copy → `FreeFileBuffer` → `CloseRecObj`, plus `FileHashToFileId` | A | **ported and live** — `py4gw/dat_reader.py`; the five calls each ran in the client, and the bytes came back |
| **S3** | The decompressor (`gw_dat_unpack.cpp` → `UnpackGWDat`) if entries are compressed | A | **not on this path** — nothing in `ReadDatFile`/`ReadDatRecord` decompresses, and the bytes the client handed over parsed as a string table directly. `UnpackGWDat` belongs to the direct-file path (`ReadDecodedMftBytes`), which reads `gw.dat` as a file for linked icon textures |
| **S4** | `_parse_string_file` + `_parse_codepoints` + `_decode_entry` + the formatted grammar | A | **pure Python, done** — `py4gw/internals/string_table.py`, 89 offline tests (the postprocessors, the grammar, the slot walk and `decode`/`decode_plain` are in it too) |
| **S5** | The game-thread load discipline: enqueue, load once per language, `switch_language` invalidation | A | **ported with one adaptation** — there is no frame loop, so the load runs at the point of request; the client calls inside it go through the capability layer, which executes on the client's own thread |
| **S6** | The value-returning call form (loader, `RecObj*`, buffer pointer) | A + B | **in the block and live** — the command record's `value` carries the callee's `eax`, and the DAT chain's record and buffer pointers came back through it |
| **S7** | A writable region in the block (hash string, `size_out`, and for B the encoded in / decoded out buffers) | A + B | **in the block and live** — `data_offset`/`write_data`/`read_data`; the hash string and the size word the client wrote both live there |
| **S8** | The callback stub for `DecodeStr_Callback` | **B only** | capability layer |

**S1 through S7 are done; S8 is the one left, and Route A never needed it.**
`encoded_strings.py` (Route A's formatted-string consumers, item amount/rarity/singular) is the
other pure-Python piece still to port, and it needs S4 only.

---

## 8. What this changes in the Dialog plan

- The decode workstream splits in two: **Route A for rendering** (S2–S5) and **Route B only
  if a member genuinely needs the client's own decode** (S8).
- `DialogLoader_GetText` still needs S6 — the loader is how the catalog text's codepoints are
  obtained — but the *render* of those codepoints can be Route A.
- The button labels and body text need **no client call at all**: their encoded pointers are
  already in the captured events (`DialogButtonInfo.message`, `DialogBodyInfo.message_enc`),
  so a bounded read plus S4 renders them.
- `IsValidEncStr` (S1) stops being a hand-wave and becomes a port with named constants.
- Route B's stub, block buffers and grammar remain on the list, but they are no longer on
  the critical path to `Dialog` reaching FULL.

## 9. What still has to be settled by reading or by test

Recorded so they are not mistaken for settled facts:

1. **Whether the dialog's codepoints feed Route A identically.** Native hands
   `DialogBodyInfo.message_enc` to the in-client decoder; Route A's `decode(raw)` takes
   "raw encoded-name bytes". **Answered, live:** the body's 22 codepoints named table index
   99942 with key `0x1610C5A3EA63`, and the 105-byte entry at that index decrypted and
   unpacked to `'I bring good tidings and announcements of exciting events! Right this very
   moment, you could be taking part in...'` — the same first four codepoints this project had
   already measured for a dialog body by an independent route. See [`RESEARCH.md`](RESEARCH.md).
2. **Whether the string-table DAT files are compressed.** **Answered for this path:** nothing
   between `ReadDatFile` and the copied bytes decompresses, and the 91,114 bytes the client
   handed over parsed as a string table directly (101,376 entries for a language, in 99 files of
   1024). `UnpackGWDat` is the direct-file path's, for linked icon textures.
3. **The exact return shape of `ReadFileBuffer`.** **Answered, live:** the buffer pointer comes
   back in `eax` (the command record's `value`), the size through the `size_out` word the client
   writes into the block's data region, and 91,114 bytes copied out of the pointer it named.
4. **Which resolved decode function does the work** (`g_validate_async_decode_str_func` is
   the one called; `g_async_decode_string_func` is resolved and unused in `src`), and whether
   anything in the client calls the second one. Only Route B needs the answer: Route A renders
   on the host and needs neither.
5. **Route C's label call contract** — unresolved until read.
6. **What a button label pointer carries.** Both of one dialog's buttons announced the same
   label pointer, and its codepoints named a table index far outside the table — recorded in
   [`RESEARCH.md`](RESEARCH.md) and in
   [`DIALOG_MIGRATION_PLAN.md`](DIALOG_MIGRATION_PLAN.md). Button text is the one piece of a
   dialog that Route A has not been shown to render.
7. **Where `DialogLoader_GetText` is on this build.** The source reaches it through a hardcoded
   client virtual address (`DialogMemory::DIALOG_LOADER_GETTEXT`, `dialog.h:96`) rebased by
   `ToRuntimeAddress` with the constant `kGwImageBase = 0x00400000`. Rebased correctly that is
   `0x9AEEF0` here, and it is **inside** another function (`0x9AEEB0`, a two-pointer container
   search), so the sources' constant is stale for this build. The port rebases with the same
   constant and confirms an entry's bytes before calling it, answering the source's own "no
   loader" value otherwise, so the catalog text is empty here until the loader is identified by a
   signature. [`RESEARCH.md`](RESEARCH.md) has the crash this came from and the two probes that
   narrowed it.
