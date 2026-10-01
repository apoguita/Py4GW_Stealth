# Handover — Guild Wars client update of 2026-09-30

**Status:** open, unstarted in this new project
**Prepared:** 2026-10-01
**Subject:** `Gw.exe` build 38974 (`F:\GW\GW1\Gw.exe`, file modified 2026-09-30 13:40:06) broke
`Py4GW_Reforged_Native` (the injected `Py4GW.dll`) and `Py4GW_Reforged` (its Python library and
deployed runtime). This document is the complete handover for fixing them.

Everything below is either **VERIFIED** (I ran it or read the line), **REPORTED** (stated by a third
party in the upstream tracker and consistent with what I measured), or **UNRESOLVED**. Nothing is
presented as fact without one of those labels.

---

## 1. Objective and scope of this project

**Objective:** make the injected `Py4GW.dll` and its deployed offset catalogue work against `Gw.exe`
build 38974, and make a startup failure *produce evidence* instead of dying silently.

**In scope**

- `C:\Users\Apo\Py4GW_Reforged_Native` — the C++ DLL source (authoritative for the patch work).
- `C:\Users\Apo\Py4GW_Reforged\offsets` — the offset catalogue the DLL actually loads at runtime
  (see §3 — this is the trap).
- The upstream tracker items: PR #9 and issue #8 of `apoguita/Py4GW_Reforged_Native`.

**Out of scope**

- `C:\Users\Apo\Py4GW_Stealth` — a separate research project. It is **not** a fix target. It may be
  used read-only as a reverse-engineering instrument (§8); no change belongs in it.
- Gameplay features, new bindings, refactors, build-system work.

**Definition of done**

1. PR #9's changes are reviewed, and its contents are present in both the Native repo *and* the
   deployed catalogue directory (§5).
2. §6 is resolved: a panic that happens during startup produces a crash report on disk.
3. §7's decision is recorded: how `.dmp` generation is meant to be reached, if at all.
4. The known-damage list in §9 is re-run and every remaining item is either fixed or explicitly
   accepted with a reason.

---

## 2. The trigger

Guild Wars shipped a client update on **2026-09-30**. The client binary changed and a number of
hard-coded constants, structure layouts and byte patterns stopped matching.

**VERIFIED, client identity:**

| Fact | Value |
| --- | --- |
| Path | `F:\GW\GW1\Gw.exe` |
| Size | 10,506,432 bytes |
| File modified | 2026-09-30 13:40:06 |
| Build number reported by the client | **38974** (`0x983E`, read from `memory.gw_version_func`) |
| Image base | `0x00400000` |
| `.text` | `0x00401000` .. `0x0093A400` |

The last successful injection recorded in the log is dated 2026-09-30 11:52–11:54, i.e. **against
the pre-update client**. Every injection since the update fails (§6).

---

## 3. Runtime topology — read this before patching anything

Three checkouts exist and they are not interchangeable:

| Checkout | Role | `offsets/` contents |
| --- | --- | --- |
| `C:\Users\Apo\Py4GW_Reforged_Native` | **DLL source.** Builds `Py4GW.dll`. | 29 `*.json` — the *source* copy |
| `C:\Users\Apo\Py4GW_Reforged` | **Deployed runtime.** Holds `Py4GW.dll`, the Python library, and the catalogue the DLL loads. | 30 `*.json` — the *loaded* copy |
| `C:\Users\Apo\Py4GW_Stealth` | Separate research project. | 31 `*.json` — a mirror. Not a fix target. |

**The critical fact.** The catalogue is loaded from the *DLL's own directory*:

```cpp
// C:\Users\Apo\Py4GW_Reforged_Native\src\base\patterns.cpp:660-662
const std::filesystem::path pattern_directory = directory.empty()
    ? process_manager::GetModuleDirectory() / "offsets"
    : directory;
```

and `GetModuleDirectory()` is the DLL's directory:

```cpp
// C:\Users\Apo\Py4GW_Reforged_Native\src\base\process_manager.cpp:38-40
std::filesystem::path GetModuleDirectory() {
    return g_module_path.empty() ? std::filesystem::path{} : g_module_path.parent_path();
}
```

The deployed DLL is `C:\Users\Apo\Py4GW_Reforged\Py4GW.dll` (13,737,984 bytes, 2026-08-26 20:09:06 —
**VERIFIED byte-for-byte identical in size and timestamp** to the copy in the Native repo). The live
injection log confirms the module directory: `[python] module directory: C:\Users\Apo\Py4GW_Reforged`.

**Therefore the runtime catalogue is `C:\Users\Apo\Py4GW_Reforged\offsets\`.**

**VERIFIED:** for all 29 files that exist in both directories, `Py4GW_Reforged_Native\offsets` and
`Py4GW_Reforged\offsets` are **byte-identical** (SHA-256 compared for `render.json`, `ui.json`,
`stoc.json`, `item.json`, `map.json`, `agent.json`). The one delta is `agent_recolor.json`, which
exists **only** in the deployed copy (§6.2).

**Consequence — the deployment trap.** PR #9 edits `Py4GW_Reforged_Native\offsets\render.json` and
`offsets\ui.json`. Merging it changes the *repo* copy only. Unless the same two files are also
updated in `C:\Users\Apo\Py4GW_Reforged\offsets\`, **the running client keeps loading the broken
patterns and the fix appears to do nothing.** Treat "sync the deployed catalogue" as a required step
of every offsets change, not an afterthought.

> **INFERRED:** the mirroring is manual (the byte-identity across 29 files implies a copy step that
> is not automated in either repo). I did not find a script that performs it. Confirm before relying
> on it.

---

## 4. Upstream tracker state

**Issue #8** — *"2026-09-30 GW update breaks native build"*, opened by `rishi-kulkarni`, 2026-10-01,
still open, 1 comment. Its body is the original diagnosis; each of its six claims is quoted and
cross-checked in §5. The only comment is the maintainer (`apoguita`, 2026-10-01) saying he will look
once the client is reported stable again.

**PR #9** — *"Fix compatibility with September 30 Guild Wars update"* by `Wellwisher533`, branch
`codex/gw-patch-20260930-compat` → `apoguita:main`, head `95671877864a7eb9d3056947ec087e5f92dd5438`,
base `ba51f6ecd68cc36729f243f179b1dd761e0fd9c5`. **Open, not a draft, `mergeable_state: clean`,
7 files, +146 −135.** No review comments. Its stated verification: a clean Win32 RelWithDebInfo build,
exact clean DLL injected, character and map load OK, a Shards of Orr Heroes run, and an automatic
travel to Vlox's Falls.

Local checkout state: `Py4GW_Reforged_Native` is clean on `main` at `7a70e52`. PR #9 is **not**
merged. Obtaining it: the sandbox on this machine cannot `git fetch` into that repo (writes outside
the working directory are denied). Fetch PR #9's head from an unrestricted shell, or reconstruct the
patch from §5, which contains all seven file diffs in full.

---

## 5. Work item A — the seven changes in PR #9

These are **REPORTED** by PR #9 and **VERIFIED** by me where a check was possible (marked). They are
the necessary minimum; §6 and §7 are *not* covered by them.

### A1 · `include/GW/stoc/stoc.h` — header count (the cause of the silent death)

```diff
-constexpr uint32_t kStoCHeaderCount = 0x1e7;
+constexpr uint32_t kStoCHeaderCount = 0x1e8;
```

**VERIFIED.** The client reported 488 (`0x1E8`) in the live injection log, against the hard-coded
487 (`0x1E7`). This is the assert that kills the client — see §6.1.

### A2 · `include/GW/common/opcodes.h` — server messages shifted by one

One unidentified SMSG was inserted after the known `0x0190` entry and before the old `0x0195`, so
every entry from the old `0x0195` upward moves by **+1**:

| Name | old | new |
| --- | --- | --- |
| `GAME_SMSG_INSTANCE_LOAD_SPAWN_POINT` | `0x0195` | `0x0196` |
| `GAME_SMSG_INSTANCE_LOAD_INFO` | `0x0199` | `0x019A` |
| `GAME_SMSG_CREATE_MISSION_PROGRESS` | `0x01A0` | `0x01A1` |
| `GAME_SMSG_UPDATE_MISSION_PROGRESS` | `0x01A2` | `0x01A3` |
| `GAME_SMSG_TRANSFER_GAME_SERVER_INFO` | `0x01A5` | `0x01A6` |
| `GAME_SMSG_READY_FOR_MAP_SPAWN` | `0x01AB` | `0x01AC` |
| `GAME_SMSG_DOA_COMPLETE_ZONE` | `0x01AF` | `0x01B0` |
| `GAME_SMSG_INSTANCE_TRAVEL_TIMER` | `0x01BB` | `0x01BC` |
| `GAME_SMSG_INSTANCE_CANT_ENTER` | `0x01BC` | `0x01BD` |
| `GAME_SMSG_PARTY_SET_DIFFICULTY` | `0x01BE` | `0x01BF` |
| `GAME_SMSG_PARTY_HENCHMAN_ADD` | `0x01BF` | `0x01C0` |
| `GAME_SMSG_PARTY_HENCHMAN_REMOVE` | `0x01C0` | `0x01C1` |
| `GAME_SMSG_PARTY_HERO_ADD` | `0x01C2` | `0x01C3` |
| `GAME_SMSG_PARTY_HERO_REMOVE` | `0x01C3` | `0x01C4` |
| `GAME_SMSG_PARTY_INVITE_ADD` | `0x01C4` | `0x01C5` |
| `GAME_SMSG_PARTY_JOIN_REQUEST` | `0x01C5` | `0x01C6` |
| `GAME_SMSG_PARTY_INVITE_CANCEL` | `0x01C6` | `0x01C7` |
| `GAME_SMSG_PARTY_REQUEST_CANCEL` | `0x01C7` | `0x01C8` |
| `GAME_SMSG_PARTY_REQUEST_RESPONSE` | `0x01C8` | `0x01C9` |
| `GAME_SMSG_PARTY_INVITE_RESPONSE` | `0x01C9` | `0x01CA` |
| `GAME_SMSG_PARTY_YOU_ARE_LEADER` | `0x01CA` | `0x01CB` |
| `GAME_SMSG_PARTY_PLAYER_ADD` | `0x01CB` | `0x01CC` |
| `GAME_SMSG_PARTY_PLAYER_REMOVE` | `0x01D0` | `0x01D1` |
| `GAME_SMSG_PARTY_PLAYER_READY` | `0x01D1` | `0x01D2` |
| `GAME_SMSG_PARTY_CREATE` | `0x01D2` | `0x01D3` |
| `GAME_SMSG_PARTY_MEMBER_STREAM_END` | `0x01D3` | `0x01D4` |
| `GAME_SMSG_PARTY_DEFEATED` | `0x01D8` | `0x01D9` |
| `GAME_SMSG_PARTY_LOCK` | `0x01D9` | `0x01DA` |
| `GAME_SMSG_PARTY_SEARCH_REQUEST_JOIN` | `0x01DB` | `0x01DC` |
| `GAME_SMSG_PARTY_SEARCH_REQUEST_DONE` | `0x01DC` | `0x01DD` |
| `GAME_SMSG_PARTY_SEARCH_ADVERTISEMENT` | `0x01DD` | `0x01DE` |
| `GAME_SMSG_PARTY_SEARCH_SEEK` | `0x01DE` | `0x01DF` |
| `GAME_SMSG_PARTY_SEARCH_REMOVE` | `0x01DF` | `0x01E0` |
| `GAME_SMSG_PARTY_SEARCH_SIZE` | `0x01E0` | `0x01E1` |
| `GAME_SMSG_PARTY_SEARCH_TYPE` | `0x01E1` | `0x01E2` |

Also in the diff: the comment above `GAME_SMSG_PARTY_SEARCH_REQUEST_JOIN` is corrected
(`// 474 happend when…` → `// 475 happens when…`).

> **UNRESOLVED:** whether `0x0191` itself moved. The reporter explicitly was not sure. Nothing above
> `0x0190` and below `0x0195` was checked.

### A3 · `include/GW/context/character.h` — `CharContext` grew to `0x458`

This is a **layout shift, not an append**, and it is the highest-risk change in the PR: a wrong
offset here does not crash, it silently reads the wrong field.

| Field | old offset | new offset |
| --- | --- | --- |
| *(new)* `uint32_t h0228` | — | `0x228` |
| `district_number` | `0x228` | `0x22C` |
| `language` | `0x22C` | `0x230` |
| `observe_map_id` | `0x230` | `0x234` |
| `current_map_id` | `0x234` | `0x238` |
| `observe_map_type` | `0x238` | `0x23C` |
| `current_map_type` | `0x23C` | `0x240` |
| `h0240[5]` → `h0244[5]` | `0x240` | `0x244` |
| `observer_matches` | `0x254` | `0x258` |
| `h0264[17]` → `h0268[17]` | `0x264` | `0x268` |
| `player_flags` | `0x2A8` | `0x2AC` |
| `player_number` | `0x2AC` | `0x2B0` |
| `h02B0[40]` → `h02B4[43]` | `0x2B0` | `0x2B4` |
| `progress_bar` | `0x350` | `0x360` |
| `h0354[29]` → `h0364[29]` | `0x354` | `0x364` |
| `player_email` | `0x3C8` | `0x3D8` |
| **`sizeof`** | `0x448` | `0x458` |

The PR replaces the single size `static_assert` with offset asserts as well, which is the right
instinct and should be kept:

```cpp
static_assert(offsetof(CharContext, district_number) == 0x22C, "CharContext district offset mismatch");
static_assert(offsetof(CharContext, progress_bar) == 0x360, "CharContext progress bar offset mismatch");
static_assert(offsetof(CharContext, player_email) == 0x3D8, "CharContext email offset mismatch");
static_assert(sizeof(CharContext) == 0x458, "struct CharContext has incorrect size");
```

> **REPORTED, not independently verified by me:** whether `h02B4` is 43 dwords and whether `h0228`
> is truly a distinct field rather than two dwords of padding. The email offset `0x3D8` and the total
> `0x458` are the load-bearing numbers; ask the PR author, or confirm against the client.

### A4 · `include/GW/context/item.h` — `ItemFormula` grew to `0x18`

```diff
         MaterialCost* material_cost_buffer;
+        uint32_t h0014;
     };
-    static_assert(sizeof(ItemFormula) == 0x14, "ItemFormula size mismatch");
+    static_assert(offsetof(ItemFormula, h0014) == 0x14, "ItemFormula tail offset mismatch");
+    static_assert(sizeof(ItemFormula) == 0x18, "ItemFormula size mismatch");
```

**Why this one matters more than it looks:** the extra dword is a **stride** change. Any code that
walks the formula array by `sizeof(ItemFormula)` will read every record after the first from the
wrong address, with no error. `item.item_formulas_count` resolves to **1509** (`0x5E5`) on this
build, so there are ~1,508 misaligned records behind that one stride.

### A5 · `include/GW/common/constants/ui.h` — three new UI messages, shifting the old ids

Three messages were inserted at `0x10000113`, `0x10000148` and `0x10000181`. Everything at or above
the first shifts by **+1**; at or above the second by **+2**; at or above the third by **+3**.
`kMapChange = 0x10000111` and everything below it is **unchanged** — which is why the dialog, chat
and target-change paths are not affected.

Selected entries (the full diff in PR #9 rewrites the whole block from `kCalledTargetChange` to
`kTemplateRelated_4`):

| Name | old | new | shift |
| --- | --- | --- | --- |
| `kCalledTargetChange` | `0x10000115` | `0x10000116` | +1 |
| `kErrorMessage` | `0x10000119` | `0x1000011A` | +1 |
| `kPartyAddHero` | `0x1000011E` | `0x1000011F` | +1 |
| `kPreBuildLoginScene` | `0x10000144` | `0x10000145` | +1 |
| `kQuestAdded` | `0x1000014E` | `0x10000150` | +2 |
| `kDestroyUIPositionOverlay` | `0x1000017D` | `0x1000017F` | +2 |
| `kGuildHall` | `0x10000180` | `0x10000183` | +3 |
| `kTravel` | `0x10000183` | `0x10000186` | +3 |
| `kAppendMessageToChat` | `0x10000194` | `0x10000197` | +3 |
| `kHideHeroPanel` | `0x100001A2` | `0x100001A5` | +3 |
| `kInitiateTrade` | `0x100001B1` | `0x100001B4` | +3 |
| `kInventoryAgentChanged` | `0x100001C1` | `0x100001C4` | +3 |
| `kTemplateRelated_4` | `0x100001CC` | `0x100001CF` | +3 |

The PR adds explanatory comments at the three insertion points, e.g.
`// 0x10000113 is a newly inserted, currently unidentified UI message.` — keep them.

> **UNRESOLVED:** the identity of the three new messages. They are placed by inference from the
> shift, not identified. `0x10000181` landing between `kEnableUIPositionOverlay` and `kGuildHall`
> suggests a UI-position or guild-hall neighbour, but that is a guess.

**Not affected — do not "fix" these:** `kWriteToChatLog = 0x1000007F`,
`kDialogButton = 0x100000A3`, `kDialogBody = 0x100000A6`, `kChangeTarget = 0x10000020`,
`kMapChange = 0x10000111`, and every `0x3000xxxx` send message. All are below the first insertion.

Also **not** affected: the frame-message bound. **VERIFIED** — `ui.send_ui_message_func` still begins
`55 8b ec 8b 45 08 83 f8 56 73 16` (`cmp eax, 0x56`) at `0x006345F0`.

### A6 · `offsets/render.json` — `get_transform_target` became ambiguous

```diff
     "get_transform_target": {
-      "pattern": "\\x7C\\x14\\x68\\xDB\\x02\\x00\\x00",
-      "mask": "xxxxxxx",
+      "pattern": "\\x83\\xFE\\x05\\x7C\\x14\\x68\\xDB\\x02\\x00\\x00",
+      "mask": "xxxxxxxxxx",
       "offset": "0x0",
       "section": "text"
     },
```

**VERIFIED by direct measurement against the new client.** This is the important class of failure and
it deserves emphasis: the engine's `scan` op takes the **lowest-addressed** match and reports
success, so an ambiguous pattern fails *silently*.

| Pattern | matches | addresses |
| --- | --- | --- |
| old | **2** | `0x004DB18D`, `0x00675AEA` |
| new (PR #9) | **1** | `0x00675AE7` |

The old pattern's first match resolves via `to_function_start` to `0x004DB180`. PR #9 reports that
lands in `CrContext.cpp` — i.e. **the wrong function**, and the resolver cannot tell. The new pattern
picks the correct site, and its function start is `0x004DB180`'s counterpart at `0x00675ACA` region.

### A7 · `offsets/ui.json` — `load_settings` became ambiguous

```diff
     "load_settings": {
-      "pattern": "\\xE8\\x00\\x00\\x00\\x00\\xFF\\x75\\x0C\\xFF\\x75\\x08\\x6A\\x00",
-      "mask": "x????xxxxxxxx",
+      "pattern": "\\xE8\\x00\\x00\\x00\\x00\\xFF\\x75\\x0C\\xFF\\x75\\x08\\x6A\\x00\\xE8\\x00\\x00\\x00\\x00\\x83\\xC4\\x0C",
+      "mask": "x????xxxxxxxxx????xxx",
       "offset": "0x0",
       "section": "text"
     },
```

**VERIFIED by direct measurement.**

| Pattern | matches | addresses |
| --- | --- | --- |
| old | **2** | `0x004752A6`, `0x0049BD7E` |
| new (PR #9) | **1** | `0x0049BD7E` |

PR #9 reports the old pattern's first match lands in `ExeFile.cpp` — again the **wrong function**,
again silently. Note the two PR fixes are the same failure mode with two different disambiguation
techniques (a prefix on one, a suffix on the other); neither generalises, so **every pattern must be
re-checked for ambiguity, not just these two** (§8, §9).

---

## 6. Work item B — the app dies silently, and the crash handler cannot see it

**This is not in PR #9. It is the reason there is no dump, and it is the most important item here**,
because until it is fixed every other bug is diagnosed blind.

### 6.1 The death, in full

`GW::StoC::Initialize()` does **not** run its init inline. It defers it onto the game thread and
returns success:

```cpp
// C:\Users\Apo\Py4GW_Reforged_Native\src\GW\stoc\stoc.cpp:184-198
bool Initialize() {
    CrashContextScope context("startup", "stoc", "initialize");
    if (g_initialized) return true;
    PY4GW_ASSERT(PY4GW::Scanner::Initialize());
    PY4GW_ASSERT(PY4GW::Patterns::Initialize());
    SafeInitializeCriticalSection(&g_mutex);
    game_thread::Enqueue([] { Init(); });     // <-- deferred
    return true;
}
```

The enqueued `Init()` runs later, on the client's own thread, where it asserts:

```cpp
// C:\Users\Apo\Py4GW_Reforged_Native\src\GW\stoc\stoc.cpp:152-154
g_stoc_handler_count = g_game_server_handlers->size();
Logger::Instance().LogInfo("STOC_HEADER_COUNT [" + std::to_string(g_stoc_handler_count) + "]");
PY4GW_ASSERT(g_stoc_handler_count == kStoCHeaderCount);   // 488 != 487
```

The assert takes this path:

```
PY4GW_ASSERT  (include/base/panic.h:6)
  -> PY4GW::FatalAssert              src/base/panic.cpp:33
  -> PY4GW::FatalAssertMsg           src/base/panic.cpp:41
       if (s_panic_handler) ...      src/base/panic.cpp:47   <-- nullptr, skipped
       CrashHandler::Instance().OnException(&pointers, "panic", false)   src/base/panic.cpp:62
       ::TerminateProcess(::GetCurrentProcess(), 1);                     src/base/panic.cpp:63
```

and inside `OnException`:

```cpp
// src/base/CrashHandler.cpp:631-651
if (::InterlockedCompareExchange(&s_shutting_down, 0, 0) != 0) return false;   // not shutting down
if (s_rtl_dll_shutdown_in_progress && s_rtl_dll_shutdown_in_progress()) return false;  // ptr still null
const bool write_dump = s_dump_generation_enabled && ShouldWriteDumpForSource(source); // false (§7)
...
if (s_crash_dir_ready) {            // <-- FALSE
    ... write json / stack / pytrace / dump ...
}
```

`s_crash_dir_ready` is set **only** by `EnsureCrashDir()`, which is called **only** from
`CrashHandler::Initialize()`:

```cpp
// src/base/CrashHandler.cpp:384-410 (EnsureCrashDir) and :419-438 (Initialize)
s_crash_dir_ready = true;            // :410
...
PY4GW::RegisterPanicHandler(&CrashHandler::OnPanic, this);   // :434
s_vectored_handler = ::AddVectoredExceptionHandler(1, ...);  // :435
InstallPathA();                                              // :436  (SEH filter)
InstallPathC();                                              // :437  (GW anchor detour)
Logger::Instance().LogInfo("[CrashHandler] installed.");     // :438
```

**And `Initialize()` is never reached**, because of the order in `Py4GW_Initialize()`:

```cpp
// src/Py4GW.cpp
:378   Scanner::Initialize()
:385   Patterns::Initialize()
:392   python_runtime::Initialize()
:400   GW::Initialize()                            // <-- kInitSteps; enqueues the fatal StoC assert
:407   listeners::Initialize()
:409-432 shared memory
:436   CrashHandler::Instance().Initialize()       // <-- NEVER REACHED
```

`GW::Initialize()` walks `kInitSteps` (`src/GW/GuildWars.cpp:56-86`), where `stoc` is index 2 and
`render` is index 3. Because `StoC::Initialize()` returns `true` after *enqueuing*, the render step is
announced next, and the fatal `Init()` then runs asynchronously on the game thread.

**Net result: no SEH filter, no vectored handler, no panic handler, no crash directory — nothing is
installed — and the process dies with `TerminateProcess`. No report of any kind is written, and
nothing is logged.**

**VERIFIED evidence.** `F:\GW\GW1\Py4GW_injection_log.txt` contains two injection attempts
(11:52:20 and 11:54:32 on 2026-09-30). Both end with exactly:

```
[gw] Initializing ctos.
[ctos] CToS sender initialized.
[gw] Initializing stoc.
[gw] Initializing render.
STOC_HEADER_COUNT [488]
```

No `Initializing crash handler.`, no `[CrashHandler] installed.`, no `CRASH` line, no error line
after it. Logging is flushed per line (`src/base/logger.cpp:181-186`), so the absence is meaningful
rather than a buffering artefact. `F:\GW\GW1\crashes` **exists and is empty**. There are **zero
`.dmp` files anywhere under `F:\GW`**.

This independently confirms issue #8's opening sentence — *"the client was getting killed right after
inject. that's the assert in stoc.cpp, the handler count is 0x1e8 now so kStoCHeaderCount needs
bumping"* — and explains why the reporter could reach that conclusion without a dump: the log tail is
the only evidence available.

### 6.2 A second, independent drift: `agent_recolor.json`

`offsets/agent_recolor.json` exists **only** in the deployed catalogue
(`C:\Users\Apo\Py4GW_Reforged\offsets\agent_recolor.json`, 5,380 bytes, 2026-07-22). It is **absent
from `Py4GW_Reforged_Native\offsets\`** — which is misleading, because a Native header points at it:

```cpp
// include/GW/agent_recolor/agent_recolor.h:37
// Scan inputs live in offsets/agent_recolor.json.
```

and `src/GW/agent_recolor/agent_recolor_patterns.cpp` resolves **seven names by string** from that
namespace, e.g.:

```cpp
PY4GW::Patterns::Resolve("agent_recolor.find_char_func", &g_find_char);
PY4GW::Patterns::Resolve("agent_recolor.consider_color_resolver_func", &g_resolver);
```

Two of those seven are driven by an **assertion line number**, and it moved:

```json
"av_char_get_consider_color_assertion": {
  "assertion_file": "AvApi.cpp",
  "assertion_message": "agent",
  "line_number": "0x1e9"
}
```

**VERIFIED by direct measurement against the new client:**

```
find_assertion('AvApi.cpp', 'agent', 0x1e9) -> None
find_assertion('AvApi.cpp', 'agent', 0x1ea) -> None
find_assertion('AvApi.cpp', 'agent', 0x1f0) -> None
find_assertion('AvApi.cpp', 'agent', 0x1f3) -> None
find_assertion('AvApi.cpp', 'agent', 0x1f4) -> 0x7dfe15     <-- the new line
find_assertion('AvApi.cpp', 'agent', 0x1f5) -> None
```

`0x1e9 + 11 = 0x1f4`, matching issue #8's *"agent recolor's AvApi.cpp assertion moved down 11 lines,
0x1e9 -> 0x1f4"* exactly.

**Required actions:**

1. Change `line_number` to `"0x1f4"` in the **deployed** file
   `C:\Users\Apo\Py4GW_Reforged\offsets\agent_recolor.json` — without this, `find_char_func` and
   `consider_color_resolver_func` both fail to resolve on every start.
2. **Add the file to `Py4GW_Reforged_Native\offsets\`** so the repo copy matches what is deployed.
   Its absence means the repo cannot rebuild a working catalogue from scratch, and the header comment
   at `agent_recolor.h:37` is currently false.
3. Both resolvers carry `"on_fail": "continue"`, so this failure is **silent** — the module reports
   nothing and recolor simply degrades.

Note that issue #8 flagged this and then set it aside (*"that json only lives in Py4GW_Reforged/offsets
though"*), which is why PR #9 does not carry it. It is fixed in the *deployed* directory, not the repo.

### 6.3 Recommended fix for 6.1

The goal is narrow: **a failure during `Py4GW_Initialize()` must produce a report.** Two changes, and
they are independent.

1. **Move the crash handler install earlier.** Call `CrashHandler::Instance().Initialize()` as the
   first thing in `Py4GW_Initialize()` — before `Scanner::Initialize()` at `src/Py4GW.cpp:378` — and
   keep the existing `SetContext` stamps. Everything the handler needs (`GetProcessDirectory`,
   DbgHelp, `ntdll!RtlDllShutdownInProgress`) is independent of the scanner and the pattern
   catalogue, so there is no ordering dependency preventing this. `InstallPathC()` already degrades
   gracefully when it cannot find its anchor (`src/base/CrashHandler.cpp:528`, `:534`, `:541`), so it
   is safe to install before `Patterns::Initialize()`.

2. **Make a pre-init panic observable regardless of ordering.** The deeper defect is that
   `OnException` writes *nothing at all* when `s_crash_dir_ready` is false
   (`src/base/CrashHandler.cpp:651`) — not even a line to the injection log, which is opened
   separately and is available from `src/Py4GW.cpp:374`. A minimal fallback — append the panic
   expression, file, line and exception code to `Py4GW_injection_log.txt` when the crash directory is
   not ready — would have turned these two dead injections into a two-line diagnosis. Consider
   making `EnsureCrashDir()` callable independently of full `Initialize()` so the directory is
   available as early as the log file is.

**Test for the fix:** re-inject with `kStoCHeaderCount` still deliberately wrong, and confirm that
`F:\GW\GW1\crashes\py4gw-<timestamp>\` now appears with a `.json` and a `-stack.txt` naming the
`g_stoc_handler_count == kStoCHeaderCount` assertion. Then fix A1 and confirm a clean start.

> **Caution:** `FatalAssertMsg` calls `OnException` and *then* `TerminateProcess`. Because
> `ShouldWriteDumpForSource("panic")` is true but `s_dump_generation_enabled` is false, fixing 6.1
> yields a JSON sidecar and a stack trace, **not** a `.dmp`. See §7.

---

## 7. Work item C — `.dmp` generation is unreachable by design and by omission

**VERIFIED.** Three independent facts:

1. The flag defaults off: `bool s_dump_generation_enabled = false;`
   (`src/base/CrashHandler.cpp:51`).
2. Its only writer is `SetDumpGenerationEnabled` (`src/base/CrashHandler.cpp:475-477`) — and a
   repository-wide search finds **no call site at all**: only the header declaration
   (`include/base/CrashHandler.h:42`), the definition, and two manuals.
3. Only two sources are eligible anyway:
   ```cpp
   // src/base/CrashHandler.cpp:125-130
   bool ShouldWriteDumpForSource(const char* source) {
       if (!source) return false;
       return strcmp(source, "panic") == 0 || strcmp(source, "seh") == 0;
   }
   ```
   `"veh"` (first-chance vectored) and `"gw_engine"` (the client's own handler detour) are permanently
   excluded.

**Empirical confirmation:** of nine historic report folders under
`F:\GW\GW1\Gw2Launcher\<N>\crashes\py4gw-20260710-*`, one sidecar from a dump-**eligible** crash reads
`"source": "structured_exception_handler"`, `"crash_class": "access_violation"`,
`"exception_code": "0xC0000005"`, **`"dump_generated": false`, `"dump_file": ""`** — and contains no
`.dmp`. There is not a single `.dmp` file anywhere under `F:\GW`.

**So "no dump" predates the client update and is not a regression of it.** It is a design choice whose
opt-in was never wired up.

**There is no user-facing way to turn it on:** no pybind binding, no `Py4GW.ini` key, no flag file, no
console command. `Py4GW.ini` sits next to the deployed DLL; search it for a dump key before assuming
one exists (I did not find one in the source).

**Decision required.** Pick one and record it:

- **(a) Leave it opt-in, and call the setter during startup** (e.g. immediately after
  `CrashHandler::Instance().Initialize()`, or gated on a debug/ini switch). Dumps are large and were
  deliberately made opt-in — the LLM manual says *"Do not silently re-enable dumps by default. They
  are intentionally expensive and large."* Respect that: if you enable them by default you are
  overriding a documented decision, so do it deliberately and say why.
- **(b) Keep it unreachable and fix the docs.** The user manual presents
  `SetDumpGenerationEnabled(true)` as the supported way to get a dump when nothing can call it. Either
  way, the JSON sidecar and stack trace are the artefacts that actually exist — make sure §6.1 is
  fixed so they are produced.

**Two documentation defects to fix in the same pass** (both **VERIFIED** against the code):

- `docs/manuals/py4gw/crashhandler-user-manual.md` says reports go to `<current working directory>\crashes`
  with a fallback to the module directory. The code does the **opposite** and refuses both: the only
  accepted base is Gw.exe's own folder (`src/base/CrashHandler.cpp:389-404`), and if
  `GetProcessDirectory()` is empty it returns false with no fallback (`:397-399`).
- The same manual and `docs/callback-crash-isolation-plan.md` name the folder
  `py4gw-YYYYMMDD-HHMMSS-PID-TID`. The code emits `py4gw-YYYYMMDD-HHMMSS` with **no PID/TID**
  (`src/base/CrashHandler.cpp:255-266`).

**Where reports actually go:** `<Gw.exe folder>\crashes\py4gw-<stamp>\` →
`<name>.json`, `<name>-stack.txt`, `<name>-pytrace.txt`, `<name>-gwtext.txt` (only when the GW text
was captured), and `<name>.dmp` (only per the decision above). A one-line `CRASH` notice is appended
to `<Gw.exe folder>\Py4GW_injection_log.txt`.

`offsets/crash.json` is **dead configuration**: all three of its entries are mirrored by hard-coded
literals in `InstallPathC()`, and nothing in the codebase resolves the `crash` namespace. Worth knowing
before you spend time editing it. (Its `append_stack_anchor` pattern *does* still exist on the new
client, but now matches **twice** — `0x00942668` and `0x009426D0` — which is a latent ambiguity in
`FindUseOfString` if it is ever wired up.)

---

## 8. Method — how to check a build without a live client

The techniques below are what produced every measurement in this document. They need **no client, no
elevation and no writes** — only `Gw.exe` on disk. Reimplement them in this project; do not depend on
another repository for them.

1. **Map the PE.** Parse section headers to get `.text` (here `0x00401000`..`0x0093A400`) and the
   image base (`0x00400000`). Read the file's bytes at `raw_offset + (rva - virtual_address)`.
2. **Resolve a pattern.** Match `pattern` + `mask` (`x` = must match, `?` = wildcard), then apply the
   entry's `offset`. This is exactly what the DLL's `Patterns::Resolve` does, against the file instead
   of the process.
3. **Check for ambiguity — do this every time.** A pattern that matches more than once is a resolver
   that answers by scan order. **Count matches; never trust a bare "it resolved".** This is the single
   highest-value check on a new build, because §5's A6 and A7 both failed this way and both reported
   success.
4. **Check the answer looks like a function.** On this client a function entry begins `55 8B EC`, often
   preceded by the hot-patch padding `8B FF`. An "answer" that is mid-instruction means a resolver is
   walking back to the wrong prologue.
5. **Check assertion-driven resolvers separately.** For an entry with `assertion_file` /
   `assertion_message` / `line_number`, search `.text` for the x86 shape
   `[6A <line8> | 68 <line32>] BA <file_literal_addr> B9 <message_literal_addr>`. A source-line shift
   breaks these with no other symptom — that is §6.2.

**A reference implementation exists** at `C:\Users\Apo\Py4GW_Stealth\tools\resolve_offline.py` and
`live_reports\_pattern_match_check.py` — the former sweeps every resolver in a catalogue against
`Gw.exe` on disk, the latter enumerates *all* match sites for one pattern and has a `--sweep` mode and
an `--assertion <file> <message> <line>` mode. They are read-only instruments and are mentioned only
so you can port the technique quickly. **They are not a dependency and nothing in that project is a
fix target.**

**Do this first:** run a full ambiguity sweep over all patterns on the new client. Only two are known
(§5 A6, A7), but issue #8's phrasing — *"two patterns still resolve but match twice now"* — suggests a
manual pass that found two, not an exhaustive one. A sweep costs minutes and can find more.

---

## 9. Known damage list on build 38974

From a full offline sweep of the 235-resolver catalogue against the new client. **Use this as the
starting checklist**, then re-derive it yourself with §8's method.

**Broken — resolver answers nothing:**

| Resolver | Cause | Fix |
| --- | --- | --- |
| `agent_recolor.find_char_func` | `AvApi.cpp` line moved | §6.2 — `0x1e9` → `0x1f4` |
| `agent_recolor.consider_color_resolver_func` | same assertion | §6.2 |

**Silently wrong — resolver succeeds, answers the wrong function:**

| Resolver | Cause | Fix |
| --- | --- | --- |
| `render.get_transform_func` | pattern matches twice, first is wrong | §5 A6 |
| `ui.load_settings_func` | pattern matches twice, first is wrong | §5 A7 |

**Suspicious — needs a look, cause not established:**

| Resolver | Observation |
| --- | --- |
| `map.cancel_enter_challenge_mission_func` | resolves to `0x0047F660`, which is **mid-instruction**; nearest real entry `0x0047F5E0` |
| `ui.trigger_terrain_rerender_func` | resolves to `0x0047F660` — *the same mid-instruction address*, from a different resolver. Two resolvers landing on one non-entry is a strong smell; at least one is wrong |
| `ui.set_game_renderer_mode_func` | resolves to `0x00895420`, mid-instruction; nearest entry `0x00895250` |
| `memory.gw_version_func` | resolves to `0x004729E0`, which is `B8 3E 98 00 00 C3` — `mov eax, 0x983E; ret`. This is a legitimate 6-byte leaf function returning build **38974**, not a bug; listed so it is not mistaken for one |

**Not bugs — tooling artefacts.** Four resolvers legitimately answer a small integer rather than an
address, so an address-shaped check reports them as failures:
`item.item_formulas_count` = `0x5E5` (1509), `item.pvp_item_array_size` = `0x157`,
`item.pvp_item_upgrade_array_size` = `0x186`, `map.map_type_instance_infos_size` = `0x1E`. Expect these
and do not "fix" them.

---

## 10. Open questions

1. **Did `0x0191` move?** Issue #8 was unsure. Only the range `0x0195` and above is accounted for.
2. **What are the three new UI messages** at `0x10000113`, `0x10000148`, `0x10000181`? Unidentified.
3. **Is `CharContext`'s new `h0228` a real field** or padding, and is `h02B4` really 43 dwords? The
   email offset and total size are what matter; the interior layout rests on the PR author's word.
4. **Are there more ambiguous patterns?** Only a full sweep will say. Two are known.
5. **Is the `offsets/` mirroring between the Native repo and the deployed directory automated?** The
   byte-identity suggests a manual copy. Confirm, because every offsets fix depends on it.
6. **Why is `agent_recolor.json` missing from the Native repo** while a Native header comment claims it
   is there? Drift, or a deliberate split?
7. **Is the deployed `Py4GW_Reforged\Py4GW.dll` built from `main` (`7a70e52`)** or from something else?
   Same size and timestamp as the repo copy, which suggests it is, but that is not proof.
8. **Should `.dmp` be enabled?** §7 needs a decision, not a default.

---

## 11. Environment notes for this machine

- **Elevation is required** for any live injection (`PROCESS_VM_WRITE`, `PROCESS_VM_OPERATION`,
  `PROCESS_CREATE_THREAD`, `PROCESS_SUSPEND_RESUME`). The shell used to prepare this document is
  **not** elevated, so no live run was performed. Everything here is source reading, file reading, and
  offline scanning — which need no elevation.
- **`gh` is not installed.**
- **PowerShell's TLS stack and `curl.exe` are broken** in the sandbox used here
  (`schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`). **Python `urllib` works** — use
  it for the GitHub API. `git`'s own HTTPS also works.
- **`git fetch` into `C:\Users\Apo\Py4GW_Reforged_Native` was denied** (writes outside the working
  directory). Read the PR through the API or from an unrestricted shell.
- The client currently running (PID 21592, started 2026-10-01 09:10:15) has **no Py4GW modules
  loaded** — it is a clean process and safe to inject into once the fixes are built.

---

## 12. Quick file reference

| Concern | Path |
| --- | --- |
| Deferred StoC init and the fatal assert | `src/GW/stoc/stoc.cpp:142-198` |
| Hard-coded header count | `include/GW/stoc/stoc.h` |
| Init sequence and crash-handler ordering | `src/Py4GW.cpp:368-446` (`GW::Initialize()` :400, `CrashHandler::Initialize()` :436) |
| Module init step table (stoc=2, render=3) | `src/GW/GuildWars.cpp:56-86`, loop `:101-112` |
| Panic path | `src/base/panic.cpp:41-64`; macro `include/base/panic.h:6` |
| Crash handler install / three paths | `src/base/CrashHandler.cpp:419-549` |
| Report gate (the reason nothing is written) | `src/base/CrashHandler.cpp:624-651` |
| Dump flag, never set | `src/base/CrashHandler.cpp:51`, `:475-477`, `:643`; `include/base/CrashHandler.h:42` |
| Dump eligibility | `src/base/CrashHandler.cpp:125-130` |
| Crash output directory | `src/base/CrashHandler.cpp:384-417`, name `:255-266` |
| Catalogue load directory | `src/base/patterns.cpp:655-698`; `src/base/process_manager.cpp:38-40` |
| Deployed catalogue (what actually loads) | `C:\Users\Apo\Py4GW_Reforged\offsets\` (30 files) |
| Repo catalogue | `C:\Users\Apo\Py4GW_Reforged_Native\offsets\` (29 files) |
| agent_recolor resolvers and the false header comment | `src/GW/agent_recolor/agent_recolor_patterns.cpp`; `include/GW/agent_recolor/agent_recolor.h:37` |
| Live injection log | `F:\GW\GW1\Py4GW_injection_log.txt` |
| Crash output root | `F:\GW\GW1\crashes\` (exists, empty) |
| Client | `F:\GW\GW1\Gw.exe` (build 38974, 2026-09-30 13:40:06) |
