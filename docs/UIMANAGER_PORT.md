# The `UIManager` port

## Handoff — read this first (2026-09-27, after round 71)

**What is done.** `py4gw/ui_manager.py` holds Reforged's `class UIManager` (`UIManager.py:29-618`)
declared **in full, in the source's own order** — all 55 declarations, AST-compared name for name and
nesting for nesting, with the class attributes. **48 answer**; **7 raise**, and each raise names its
work. The binding map is pinned member by member below; the verdict row is in
[`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) (**COMPLETE for this port's purposes** — the owner's ruling of
2026-09-27, with the seven divergences named) and the
rounds are in [`PORTING_PROGRESS.md`](PORTING_PROGRESS.md) (63-71).

**What is left, and it is not porting work.** The seven are enumerated one by one in the next section
with what each needs and **who consumes it in Reforged**. Six consume or publish the injected
runtime's own state (its journal, its deque, its flag, its dispatcher); the seventh reads the client's
own ImGui context. The two members of that family with real consumers — `GetIOEventsForFrame` and
`RegisterFrameIOEventCallback` — already answer.

**The one open decision.** Whether to (a) record those six as documented divergences on their members —
the form `Player`, `Agent` and `Dialog` already carry — and set the verdict to *COMPLETE for this
port's purposes*, or (b) build one of the captures first. **Whichever is chosen, the evidence is in
this document**, and nothing here needs re-reading a conversation to act on.

**The one command owed.** `python tests/probe_ui_manager_live.py tests/live_reports/ui_manager_live.json`
from an **elevated** shell (also in `tools/run_live_suites.ps1`'s default set) — read-only, no hook, no
patch, no call. It covers every read this class answers, including the key-remap table whose `0x75`
words exist only at runtime because the table sits in `.data`'s uninitialised tail.

**Status: landed 2026-09-27 (rounds 63-71) — `py4gw/ui_manager.py`. 48 of the 55 declarations answer;
the 7 that raise are the injected runtime's own surface and are recorded as documented divergences by
the owner's ruling of 2026-09-27 (*"whats left is not applicable here, we dont have frame logs"*), so
the class is COMPLETE for this port's purposes.** The counts are computed from the module's AST by
`tests/test_ui_manager_offline.py`, so they cannot drift from the code; each of the seven names exactly
what it needs, and the live pass below is the one verification still owed.

## Sources

- **Reforged**: `Py4GWCoreLib/UIManager.py` — 1302 lines. `class UIManager` is lines **29-618**,
  **55 declarations** (43-618) — 53 class-level members plus the two the source nests inside them
  (`_add_event` in `_UpdateFrameIOEvents`, `_is_button` in `GetDialogButtons`).
- **Native**: `src/GW/ui/ui_bindings.cpp` — `py::class_<UIManagerShim>(m, "UIManager")` (`:660`),
  the bodies in `src/GW/ui/ui_methods.cpp` (2836 lines).
- **The older runtime, only where Native's current revision has nothing** (`C:\Users\Apo\Py4GW` —
  `include/py_ui.h` shim, `src/py_ui.cpp` bindings, vendored GWCA). It is used for the six members
  Native neither binds nor implements, and each use is marked below; `AGENTS.md` treats that tree as
  research leads, so every one of those resolutions is recorded as what it is.

## Scope — the class boundary (owner's criterion, verbatim)

> *"the class is mostly ok up until line 611 where `InventoryBagWindow` starts, those classes we
> don't need."*

| lines | what | ported? |
| --- | --- | --- |
| 29-618 | `class UIManager` — **55 declarations** (43-618) | **yes** |
| 619-1302 | **14 window classes**, 56 methods | **no — and permanently** |

Also out of scope from the same ruling: **no singleton instance**, **no handler class**, and **no
per-widget class at all**. The section-by-section keep/drop table for native's 303 bindings is in
[`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md).

**The class's landed name (owner's call, 2026-09-27).** `py4gw/ui_manager.py` holding
`class UIManager` — the sources' own class name from both sides (`class UIManager` in Reforged;
`py::class_<UIManagerShim>(m, "UIManager")` in native), in the scheme every other ported class uses
(`Player` in `py4gw/player.py`, `Effects` in `py4gw/effect.py`). `PyUIManager` is the injected
*module* and is not used as a class name here — the shape `AGENTS.md` rejects for `PyDialog`.

## Step 1, done: the binding map

Every wrapped member, resolved one at a time. **Native's binding** is the `.def_static` in
`ui_bindings.cpp`; **behind it** is the `GW::ui` function in `ui_methods.cpp`; **the port** is what
`py4gw/ui_manager.py` does instead.

| member (source line) | binding | behind it | the port |
| --- | --- | --- | --- |
| `GetFrameLogs` (161) | `get_frame_logs` | **none in native** — the older shim's `GW::UI::GetFrameLogs` = GWCA's `frame_logs` (`UIMgr.cpp:106`, filled only by its `CreateUIComponent` detour, `:160`) | **raises** — the injected runtime's own journal |
| `ClearFrameLogs` (170) | `clear_frame_logs` | `frame_logs.clear()` (`UIMgr.cpp:1235-1237`) | **raises** — same buffer |
| `GetUIMessageLogs` (177) | `get_ui_message_logs` (`:663`) | `GW::ui::GetUIMessageLogs` (`ui.cpp:1155-1163`) | **raises** — the runtime's own deque (`ui.cpp:1077`) |
| `ClearUIMessageLogs` (186) | `clear_ui_message_logs` (`:664`) | `ui.cpp:1165-1170` | **raises** — same deque |
| `GetTextLanguage` (194) | `get_text_language` (`:662`) | `GetPreference(NumberPreference::TextLanguage)` (`ui_methods.cpp:1428-1430`) | `preferences.get_number_preference(TEXT_LANGUAGE)` |
| `SendUIMessage` (199) | `SendUIMessage` → `SendUIMessagePacked` (`:60-74`) | `GW::ui::SendUIMessage(msgid, &payload, nullptr, skip_hooks)` (`:1374-1406`) | native's **sixteen-word** payload in the data region, then `client.send_ui_message_raw` |
| `SendUIMessageRaw` (203) | `SendUIMessageRaw` (`:1062-1065`) | the same function with the caller's raw words | `client.send_ui_message_raw` — the held sender, three words, unwrapped |
| `DrawOnCompass` (208) | *(unbound; audit `:29`)* | `GW::ui::DrawOnCompass` (`:1706-1712`), `CompassPoint{int x, y}` (`ui.h:292-297`) | points into the data region, then `ui.draw_on_compass_func` |
| `LoadSettings` (212) | *(unbound)* | `GW::ui::LoadSettings(size, uint8*)` (`:1714-1718`) | bytes into the region, then `ui.load_settings_func` |
| `GetSettings` (216) | *(unbound)* | `GW::ui::GetSettings()` = `Context::GetGameSettingsAddress()` (`:1720-1722`) | the `GWArray<unsigned char>` at `ui.game_settings_addr` |
| `GetCurrentTooltipAddress` (220) | *(unbound)* | `GW::ui::GetCurrentTooltip` (`:2658-2661`) | the port's one-dereference read (`ui/tooltip.py`'s recorded divergence) |
| `IsWorldMapShowing` (237) | `is_world_map_showing` (`:665`) | `(*state & 0x80000) != 0` (`:1734-1737`) | the word at `ui.world_map_state_addr` |
| `IsUIDrawn` (246) | `is_ui_drawn` (`:666`) | `*word == 0`, `true` when unresolved (`:1724-1727`) | the word at `ui.ui_drawn_addr`, inverted |
| `AsyncDecodeStr` (250) | *(unbound; audit `:29`)* | `GW::ui::AsyncDecodeStr` (`:2572-2607`) | `ui/async_decode.py`'s slot, read once after the call |
| `IsValidEncStr` (254) | `is_valid_enc_str` (`:1131`) | `GW::ui::IsValidEncStr` (`:2613-2629`) | `ui/encoded_str.py`, with the terminator the conversion adds |
| `IsValidEncBytes` (258) | *(unbound; audit `:29` names a line that is not this function)* | **none** — no `IsValidEncBytes` in native | `encoded_str.is_valid_enc_str` behind the older shim's three checks (`py_ui.h:4606-4615`) |
| `UInt32ToEncStr` (262) | `uint32_to_enc_str` (`:1132-1136`) | `GW::ui::UInt32ToEncStr(value, buffer, 8)` (`:2631-2646`) | `encoded_str.uint32_to_enc_str(value, 8)` |
| `EncStrToUInt32` (266) | `enc_str_to_uint32` (`:1137`) | `GW::ui::EncStrToUInt32` (`:2648-2656`) | `encoded_str.enc_str_to_uint32` |
| `SetOpenLinks` (270) | `set_open_links` (`:684-687`) | `g_open_links = toggle` (`:1679-1681`) — the **module's own** flag | **raises** — nothing in the client holds it |
| `IsShiftScreenshot` (274) | `is_shift_screenshot` (`:667`) | `*word != 0` (`:1729-1732`) | the word at `ui.shift_screenshot_addr` |
| `GetFPSLimit` (283) | `get_frame_limit` (`:688`) | `GW::ui::GetFrameLimit` (`:1833-1858`) | `preferences.get_frame_limit()` |
| `SetFPSLimit` (292) | `set_frame_limit` (`:689-692`) | `g_command_line_number_buffer[FPS] = value` (`:1860-1864`) | `preferences.set_frame_limit()` — `WRITE_MEMORY` on the game thread |
| `GetPreferenceOptions` (302) | `get_preference_options` (`:1025-1033`) | `GW::ui::GetPreferenceOptions` (`:1438-1448`) | `preferences.get_enum_preference_options()` |
| `GetEnumPreference` (306) | `get_enum_preference` (`:1034-1036`) | `GetPreference(EnumPreference)` (`:1432-1436`) | `preferences.get_enum_preference()` (landed 2026-09-26) |
| `GetIntPreference` (310) | `get_int_preference` (`:1037-1039`) | `GetPreference(NumberPreference)` (`:1450-1454`) | `preferences.get_number_preference()` |
| `GetStringPreference` (314) | `get_string_preference` (`:1043-1045`) | `GetPreference(StringPreference)` (`:1456-1460`) | `preferences.get_string_preference()` |
| `GetBoolPreference` (318) | `get_bool_preference` (`:1040-1042`) | `GetPreference(FlagPreference)` (`:1462-1466`) | `preferences.get_flag_preference()` |
| `SetEnumPreference` (322) | `set_enum_preference` (`:1046-1048`) | `SetPreference(EnumPreference, value)` (`:1468-1540`) | `preferences.set_enum_preference()` (round 64) |
| `SetIntPreference` (326) | `set_int_preference` (`:1049-1051`) | `SetPreference(NumberPreference, value)` (`:1542-1637`) | `preferences.set_number_preference()` (round 64) |
| `SetStringPreference` (330) | `set_string_preference` (`:1055-1057`) | `SetPreference(StringPreference, wchar_t*)` (`:1639-1651`) | `preferences.set_string_preference()` — the UTF-16 text in the data region (round 65) |
| `SetBoolPreference` (334) | `set_bool_preference` (`:1052-1054`) | `SetPreference(FlagPreference, bool)` (`:1653-1677`) | `preferences.set_flag_preference()` (round 64) |
| `GetKeyMappings` (338) | **none in native** | the older shim: the `FrKey.cpp` assertion scan + `0x75` words (`py_ui.h:4757-4772`) | **built (round 66)** over the new `ui.key_mappings_table` resolver — the same assertion, the table's own immediate, `0x75` words |
| `SetKeyMappings` (342) | **none in native** | the same scan + a copy into the client (`py_ui.h:4774-4790`) | **built (round 66)** — `min(0x75, len(mappings))` words through `WRITE_MEMORY` |
| `Keydown` (346) | `key_down` (`:1105-1112`) | `ui::Keydown(key, target)` → `SendFrameUIMessage(target, kKeyDown, &KeyAction{key})` (`:1408-1411`) | the frame's callbacks, one-word packet in the region; `frame_id == 0` walks to the button-action frame (round 67) |
| `Keyup` (350) | `key_up` (`:1113-1120`) | `ui::Keyup` (`:1413-1416`) | as above with `kKeyUp`, and the same walk |
| `Keypress` (354) | `key_press` (`:1121-1128`) | `ui::Keypress` (`:1418-1426`) | down then up — the binding's own `Enqueue` runs inline on the game thread (`game_thread_methods.cpp:33-45`) |
| `GetWindoPosition` (358) | `get_window_position` (`:673-677`) | `GW::ui::GetWindowPosition` (`:1683-1688`) | the `Context::WindowPosition` record (`context/ui.h:532-537`) |
| `IsWindowVisible` (367) | `is_window_visible` (`:669-672`) | `pos->visible()` = `(state & 1) != 0` | the state word at the same entry |
| `SetWindowVisible` (376) | `set_window_visible` (`:678-683`) | `g_set_window_visible_func(id, flag, nullptr, nullptr)` (`:1690-1696`) | `CallForm.U32_U32_U32_U32` |
| `SetWindowPosition` (386) | *(unbound)* | `g_set_window_position_func(id, info, nullptr, nullptr)` (`:1698-1704`) | the struct into the region, then the four-word call |
| the 6 frame-IO members (43-157) | — | no binding: the source's own Python over `PyImGui`/`PySystem`/`PyCallback` | 4 answer (registration + reads); 2 raise |
| the 9 dialog members (396-609) | — | no binding: the source's own Python over `Frame`/`FrameTree` | all 9 answer |

**Eleven of Reforged's 41 `PyUIManager.UIManager` calls have no `.def_static` in native's current
revision.** Native's own audit lists several as pending quick wins
(`docs/binding-parity-audit.md:29`, `docs/native-binding-coverage-audit.md:81`), which is why most of
them still resolve: the binding is a wrapper, and what it wraps is in `ui_methods.cpp`. The
exceptions are the five with nothing behind them at all — `get_frame_logs`, `clear_frame_logs`,
`get_key_mappings`, `set_key_mappings` and `SetOpenLinks`'s effect — and each of those raises with
the reason on it.

## What answers, what raises

**48 of 55 declarations answer, all of them unconditionally, and 7 raise.** The answering set is the
two IO registries and the event read (4 + the nested recorder), the three state reads, the tooltip
address, the settings pair, the four preference getters, the option list and **all four typed
setters**, the frame limit pair, the four enc-string members, the key-mapping pair, `AsyncDecodeStr`,
`DrawOnCompass`, the three window members, both message senders, **the three key members in full**
(with and without a frame id), and all nine dialog members.

**7 raise, and every one names its work**: `_UpdateFrameIOEvents` and `RegisterFrameIOCallbacks`
(the injected ImGui/clock and `PyCallback`); the four runtime journals (`GetFrameLogs`,
`ClearFrameLogs`, `GetUIMessageLogs`, `ClearUIMessageLogs`) and `SetOpenLinks` (the runtime's own
link-opening hook). Every one of those is **target-side work with a name** in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) — there is no plain porting gap left in this class.

## Findings this round

0. **Round 69: the class and the binding are two different surfaces, and this port's own queue had
   them confused.** Two documents said `Frame`/`_FrameTree`'s members should "delegate to
   `UIManager`" once the class landed (`FRAME_TREE_PORT.md` § "Next", step 3, and this doc's queue),
   and that is **false**: measured against the source, `FrameTree/frame.py` calls **49 distinct
   `PyUIManager.UIManager.<name>`** members and **the intersection with Reforged's `class UIManager`
   is empty** — not one. The class is the source's *Python* class (`UIManager.py:29-618`: the
   preference surface, the built-in windows, the dialog helpers, the frame-IO events); `Frame` calls
   the *injected module's* binding (`button_click`, `SendFrameUIMessage`, `get_text_label_*`,
   `get_frame_array`, the frame-tree traversal family), which Reforged's class never wraps. So there
   was nothing to re-point, and doing it would have broken the cornerstones in one of two ways —
   calling a member this class does not have, or adding members to it that the sources do not
   declare. **What the two surfaces do share is the function behind each binding, and the port already
   resolves those one at a time where they are used** — `Frame.click` spells out `ui::ButtonClick`
   and this class spells out `GW::ui`'s preference and window functions, which is the same rule
   applied to two different source classes.
1. **Round 67: `GetButtonActionFrame()` needed no new mechanism either — both of its steps are native
   functions the catalog already carries.** ``Keydown``/``Keyup``'s ``frame_id == 0`` is the client's
   own button-action frame (``ui_methods.cpp:161-164``: ``GetFrameByLabel(L"Game")`` then
   ``GetChildFrame(frame, 6)``), and the port reaches it exactly as native does: the label is hashed
   **by the client** — the wide label placed in the block's data region and passed to
   ``g_create_hash_from_wchar_func(label, -1)`` (``ui.create_hash_from_wchar_func``, ``:542-546``),
   which is the shape round 65 proved — then ``GetFrameIDByHash``'s array scan (the port's
   ``FrameArray.frame_id_by_hash``, ``:575-588``), then one call of ``g_get_child_frame_id_func``
   (``ui.get_child_frame_id_func``, ``:589-607``). The two last paragraphs of
   ``FRAME_TREE_PORT.md``'s "the native walkers" section treat those functions as a *call* this port
   could not make; it can, and this member is the proof.
1. **Round 66: the client's key-remap table is located and derived, and the legacy route is not the
   one that finds it.** GWCA's `FindAssertion("FrKey.cpp", "count == arrsize(s_remapTable)", 0, 0x13)`
   is what the older runtime calls (``py_ui.h:4762``); **its own offset does not land on the table on
   this build**, so the resolver was derived from the file instead, and the derivation is recorded in
   the catalog next to it (``ui.key_mappings_table``): read the assertion's message literal, take the
   *first* of the two ``.text`` uses of it (GWCA's own comment: *"this address is fond twice, we only
   care about the first"*), step **+0xD** to the immediate of the ``mov`` that loads the table — the
   entry asserts ``count == 0x75`` two instructions above it — read that immediate, and require it to
   land in ``.data``. Measured offline on this build by ``tools/key_mappings_hunt.py``: **both uses
   read ``0x00C14C58``, inside ``.data``** (``.rdata`` holds the message at ``0x00A5B51C`` and
   ``FrKey.cpp`` at ``0x00A5B475``; the two uses are at ``0x00644084`` and ``0x00645144``). The
   distance is the same at both sites, which is what makes it a derivation rather than a coincidence.
2. **That table's bytes are not in the file.** ``0x00C14C58`` lies in ``.data``'s **uninitialised
   tail** — ``read_va`` refuses it, because ``.data``'s file bytes cover ``0x16A00`` of a ``0x560538``
   virtual size — so the client fills the table at runtime and only a live read sees its contents. The
   member's read is exactly that, and nothing here is inferred from the file's zeros.
3. **Round 65's finding is a correction of this port's own record: there was never a missing
   "wide-string argument form".** The label hash (`_FrameTree.hash_for_label`, `by_label`,
   `anchor_ids`' fallback), `Frame.send_message_text` and `UIManager.SetStringPreference` were all
   filed as blocked on "a text region in the shared block and a pointer form"
   ([`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md), [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md), and this
   doc's own queue). **`ConnectedClient.bridge.write_data` places arbitrary bytes in the block's data
   region — memory inside the client — and answers that address**, which is exactly what a pointer
   argument needs, and it has been there since the block did. `SetStringPreference` is built on it and
   answers (`ui_methods.cpp:1639-1651`: write the caller's UTF-16 buffer, pass its address, call
   `g_set_string_preference_func`); what was missing was the body and nothing else. **What that leaves
   is precise, not vague**: `_FrameTree.hash_for_label`/`by_label` are now one call each over
   `ui.create_hash_from_wchar_func` (a resolver the catalog already carries) with the label placed the
   same way, and `Frame.set_text` is the only member of the three still genuinely blocked — it needs
   the client's own `TextLabelFrame::SetLabel`, a method inside the client rather than a `cdecl`
   function the catalog can name.
4. **Reforged's `NumberPreference` table is the outlier.** `EffectsVolume` and `BackgroundVolume` are
   **swapped** between the sources — Reforged's `enums_src/UI_enums.py:387-389` has
   `BackgroundVolume = 24, DialogVolume = 25, EffectsVolume = 26` while native
   (`common/constants/ui.h:261-266`) and the older runtime's GWCA
   (`vendor/gwca/Include/GWCA/Managers/UIMgr.h:912-914`) both have `EffectsVolume, DialogVolume,
   BackgroundVolume` — and Reforged's table stops at `Count = 41` where both others say `44`. The
   member's follow-up switch is native's own body, so the **number** a Reforged caller passes reaches
   the *other* branch: `NumberPreference.BackgroundVolume` (24) drives native's effects channel and
   `EffectsVolume` (26) drives background's. The port uses native's values and a test pins the
   disagreement from both tables. (`WindowID_Count` and `FlagPreference.Count` disagree the same way.)
3. **Three of Reforged's Python enum tables disagree with native's C++ constants**, and the port uses
   native's where a member makes the check: `WindowID_Count` `0x69` vs **`0x66`** (`ui.h:109`),
   `NumberPreference.Count` `41` vs **`44`**, `FlagPreference.Count` `0x5D` vs **`0x5E`** — and, for
   `NumberPreference`, two *member values* as well (finding 0). GWCA agrees with native on all three,
   so the Python table is the outlier in each case; the port's `enums_src/ui_enums.py` keeps
   Reforged's values (it is a verbatim port of that file) and the members' checks are native's.
4. **`GetWindoPosition` means two different things in the two sources**, and the port ports native's:
   native's binding reads the record's raw `p1`/`p2` (`ui_bindings.cpp:673-677`), while the older
   runtime's derived `left/top/right/bottom` through `WindowPosition::xAxis`/`yAxis`
   (`py_ui.h:4843-4855` → `UIMgr.cpp:2513-2568`) — which need `Render::GetViewportWidth/Height`,
   i.e. the DX context. Native's is both the higher authority and the one this port can read.
   **Fixed 2026-10-05:** the body cast all four values to `int`, which the binding does not — it
   returns `py::make_tuple(pos->p1.x, pos->p1.y, pos->p2.x, pos->p2.y)`, four floats. The port's own
   offline test had been reporting it as a pre-existing failure (a record holding `1.5, 2.5, 3.5,
   4.5` came back as `1, 2, 3, 4`); the casts are gone and the values now travel as the binding hands
   them over. The source's annotation (`list[int]`) is kept verbatim, and the port answers a list
   where the binding answers a tuple — both recorded rather than quietly carried.
5. **`SetWindowPosition`'s caller passes four numbers and no state**, and the shipped binding kept
   the client's own word by writing `p1`/`p2` in place before the call (`py_ui.h:4873-4889`). The
   port reads that word and passes the whole struct to the client's setter, which is what native's
   function does with the pointer; the extra in-place write is the recorded difference.
6. **`UInt32ToEncStr` cannot encode much.** Native's binding calls it with a count of 8
   (`ui_bindings.cpp:1134`) and the function needs `ceil(value / WORD_VALUE_RANGE) + 1` code units
   (`ui_methods.cpp:2631-2635`), so everything above `7 * WORD_VALUE_RANGE` (**227584**) comes back
   as the empty string. Pinned by a test rather than left to look like a port defect.
7. **The source's own annotation on `GetDialogButtonFrames` does not describe its body**: it says
   `list[tuple[int, …]]` and both comprehensions build `(f, f.rect)` — the handle. The same member's
   docstring says "sorted by their vertical position" while the key is the **left** edge
   (`:560-561`). The port's annotation states the handle, and the docstring records both.
8. **The volume follow-ups pass a `float`** (`g_set_volume_func(0, current_value / 100.f)`,
   `ui_methods.cpp:1566`), and the call vocabulary's one float form is a *pointer* to four floats.
   The port passes the bit pattern as the word, which is the same four bytes a `cdecl` callee reads
   off the stack; the helper that does it says so.

## The seven that raise, one by one (round 71)

**The owner's ruling on this table (2026-09-27):** *"whats left is not applicable here, we dont have
frame logs."* So the seven are **documented divergences on their members, not pending work** — the form
`Player.player_instance`, `Agent.GetProfessionsTexturePaths` and `Dialog._call_native_dialog_method`
already carry — and the class's verdict is **COMPLETE for this port's purposes**. Each member still
raises and names the runtime state behind it, which is what the rules ask of a member that cannot
answer; none of them returns a stand-in.

The enumeration the scope decision rests on. Every row is the member's own raise text, its binding,
and the callers it has **in Reforged itself** — because a mechanism is worth building only if
something consumes it.

| # | member (source line) | what its binding resolves to | what it needs | callers in Reforged |
| --- | --- | --- | --- | --- |
| 1 | `GetFrameLogs` (161) | GWCA's `GW::UI::GetFrameLogs()` — its own `frame_logs` vector | **the injected runtime's own journal**: filled only by *its* `CreateUIComponent` detour (`UIMgr.cpp:106`, `:160`); nothing in the client holds it. Reproducing it is a new capture (an entry hook plus a bounded label copy inside the client) | 5, all debug tooling (`frame_log_dump.py`, `uimanager_demo.py`) |
| 2 | `ClearFrameLogs` (170) | `frame_logs.clear()` (`UIMgr.cpp:1235-1237`) | the same buffer's other half | (same tooling) |
| 3 | `GetUIMessageLogs` (177) | `GW::ui::GetUIMessageLogs` (`ui.cpp:1155-1163`) | **the runtime's own deque** `g_ui_message_logs`, filled by *its* message hook (`ui.cpp:1077`, `:1136-1150`); the seven-field entry needs variable-length byte capture the port's event ring does not have | 3, debug widgets (`uimanager_demo.py`, `Frame_Showcase.py`, `UI_Listener.py`) |
| 4 | `ClearUIMessageLogs` (186) | `ui.cpp:1165-1170` | the same deque | (same widgets) |
| 5 | `SetOpenLinks` (270) | `g_open_links = toggle` (`ui_methods.cpp:1679-1681`) | **the runtime's own flag**, which only its `kOpenTemplate` handler reads — and that handler *blocks* a message, which this port's observer cannot do (it runs before the trampoline but cannot suppress the original) | **none** |
| 6 | `RegisterFrameIOCallbacks` (146) | `PyCallback.PyCallback.Register(…)` | **the runtime's per-frame dispatcher** — the frame loop this port does not have (`AGENTS.md` § Caching) | **one, and it is the source's own commented-out line** (`UIManager.py:617`) |
| 7 | `_UpdateFrameIOEvents` (66) | the source's own Python over `PyImGui`/`PySystem` | **the client's own ImGui context** (`io.mouse_pos_x/y`, `mouse_wheel`, `mouse_wheel_h`, `is_mouse_clicked`, `is_mouse_double_clicked`) and a tick clock; `offsets/native_ui.json` holds 15 resolvers for ImGui *wrapper procs* and none for the context, so this is an investigation rather than a lookup | only through #6 — the same deactivated path |

**The split that matters.** #1–#6 consume or publish the *injected runtime's* own state — its journal,
its deque, its flag, its dispatcher — which is the kind `AGENTS.md` records as a documented divergence
when a member consumes something the injected runtime owns in-process (`Player.player_instance`,
`Agent.GetProfessionsTexturePaths`, `Dialog._call_native_dialog_method` are the three precedents).
#7 is the only one that reads the **client's** own surface. And the members of this family with genuine
consumers — `GetIOEventsForFrame` (used by `Frame.io_events`) and `RegisterFrameIOEventCallback` —
**already answer** here.

## Who consumes the seven (measured 2026-09-27, round 70)

The seven members still raising were searched for their callers **in Reforged itself**, because that
is what says whether the mechanism behind them is worth building:

| member | callers in Reforged |
| --- | --- |
| `GetFrameLogs` | **5, all debug tooling** — `frame_log_dump.py`, `uimanager_demo.py` |
| `GetUIMessageLogs` | **3, all debug widgets** — `uimanager_demo.py`, `Frame_Showcase.py`, `UI_Listener.py` |
| `SetOpenLinks` | **none** |
| `RegisterFrameIOCallbacks` | **one, and it is the source's own commented-out line** (`UIManager.py:617`, *"autiomatic IO events was deactivated due to instability over long sessions"*) |
| `_UpdateFrameIOEvents` | only through `RegisterFrameIOCallbacks` — i.e. the same deactivated path |
| `GetIOEventsForFrame`, `RegisterFrameIOEventCallback` | real consumers (`Frame.io_events`, `Frame_Showcase.py`) — **and both already answer here** |

So the two members with genuine consumers answer, and everything still raising is either Reforged's
own debug surface or a feature its own author switched off. That is the fact the scope decision rests
on: building the captures these need (a `CreateUIComponent` journal, variable-length message capture,
the client's ImGui context, message blocking) would be **new capability for a debug surface**, not
porting work — and `AGENTS.md`'s rule is that the sources decide, not convenience.

## Order of work — what is left

**Every remaining item is target-side work with a name; there is no plain porting gap left in this
class.** In the order the port doc's own queue puts them:

1. **The runtime's own state** — the four journals and the link-opening flag: each is a capture on
   this project's own hook layer, not a client read, and only worth taking if a consumer appears.
2. **`_UpdateFrameIOEvents` / `RegisterFrameIOCallbacks`** — the client's ImGui reads (mouse position,
   wheel, click state) and Reforged's per-frame registration. `offsets/native_ui.json` holds 15
   resolvers for the client's ImGui *wrapper* procs, none for its ImGui context, so the reads are an
   investigation rather than a lookup; the registration is the frame loop this port does not have.
3. **The adjacent members the same two mechanisms unblock** (not `UIManager`'s own, and each one body
   over a resolver that already exists): `_FrameTree.hash_for_label` and `_FrameTree.by_label`
   (`ui.create_hash_from_wchar_func` + the label placed in the data region, then the array scan
   `by_hash` already performs), which also makes `_FrameTree.anchor_ids`' label fallback live; and
   `Frame.child_native` / `Frame.child_path_native`, which are `ui.get_child_frame_id_func` called
   once or walked — the function this class now calls for its own key path.
4. **The two re-pointings the plan named, and one of them was a wrong instruction.** **The first is
   done (round 68)**: `Agent.GetInstanceUptime` now calls `UIManager.GetFPSLimit()` — the source's own
   route (`Agent.py:280-294`) — instead of reaching `GW::ui::GetFrameLimit` one layer lower through
   `py4gw/ui/preferences.py`, which it did while this class had no ported home. **The second is
   withdrawn (round 69), because the premise was false: there is nothing of `Frame`'s to re-point.**
   The class and the binding are *different surfaces* — see finding 0 below. `Frame`/`_FrameTree` call
   the injected **module** directly (`button_click`, `get_text_label_decoded_by_frame_id`,
   `get_frame_array`, …) and **not one of the 49 binding members they use is a member of Reforged's
   `class UIManager`**. Delegating them here would have meant either calling a member this class does
   not have or adding members the source's class does not declare — a cornerstone violation either
   way. What those members do share with this class is the *function* behind the binding, and the
   port already resolves each one where it is used.
5. **Live verification** (owed, one pass, elevated). **The read half has a probe ready to run, and it
   is in the project's own runner (round 70)**: `tools/run_live_suites.ps1`'s default set now lists
   `tests/probe_ui_manager_live.py` second, so one `pwsh -NoProfile -File tools\run_live_suites.ps1`
   covers it beside the other read-only suites. Run alone, it is
   `python tests/probe_ui_manager_live.py tests/live_reports/ui_manager_live.json` from an **elevated**
   shell (the connection asserts elevation). It connects with `game_thread=False` — no hook, no
   patch, no call — and asks the client for every read this class answers: the three state words, the
   tooltip address, the text language, the option list and the four typed getters, the frame limit,
   the settings array's length, `GetWindoPosition`/`IsWindowVisible` over six window ids, the two
   dialog visibility reads, and **the key-remap table**, whose ``0x75`` words exist only at runtime
   because the table sits in ``.data``'s uninitialised tail. **The acting half is a second, separate
   run** and needs the owner present: `SendUIMessage`/`SendUIMessageRaw`, `Keydown`/`Keypress` (which
   moves the game), `SetWindowVisible`, `SetWindowPosition`, `SetFPSLimit` read back, and
   `ClickDialogButton` (which is `Frame.click`, already live-verified); the four preference setters
   should be set and read back through the matching getter with the original values restored.

## Live verification: the read half, unelevated (round 73)

`tests/probe_ui_manager_reads_live.py` — a **direct-memory** probe in the shape
`probe_agent_effects_live.py` established (a `ProcessMemoryReader` and a `RemoteScanner` over the
client's main module, a stand-in registered where `require_client` looks) — ran against the live
client **without elevation** (`elevated: false`, pid 31024) and answered every read it covers. Report:
`tests/live_reports/ui_manager_reads_live.json`.

| member | live answer |
| --- | --- |
| the seven resolvers it needs | **all resolved** — `world_map_state_addr`, `ui_drawn_addr`, `shift_screenshot_addr`, `game_settings_addr`, `window_positions_array`, `key_mappings_table`, `current_tooltip_ptr` |
| `IsWorldMapShowing` | `false` — no world map open |
| `IsUIDrawn` | `true` — the inverted flag, so the client's own word is `0` |
| `IsShiftScreenshot` | `false` |
| `GetCurrentTooltipAddress` | `0x253D373C` — a plausible pointer, from the port's one-dereference read |
| `GetSettings` | **798 bytes** — the `GW::Array` header's own size |
| `GetWindoPosition` / `IsWindowVisible` | real rects over six ids: `0` → `[332, 76, 183, 140]` visible, `0x16` → zeros, `0x40` → `[43, 237, 586, 732]` **not** visible |
| `GetPreferenceOptions` | `FrameLimiter` → **`[0, 1, 2, 3]`** and `AntiAliasing` → **`[0, 1, 2, 3, 4]`** — the first is the list `SetPreference`'s own follow-up switches on (`1 → 30`, `2 → 60`, `3 → the monitor rate`, `ui_methods.cpp:1840-1852`), read from the client's `EnumPreferenceInfo` |
| `IsNPCDialogVisible` / `IsLockedChestWindowVisible` | both **`false`**, correctly: the members resolved the frame tree and answered "not usable" — a dialog exists only while an interaction is in flight (`AGENTS.md` § Live verification) |
| **`GetKeyMappings`** | **117 words — `arrsize(s_remapTable)` exactly — all 117 non-zero, max 260** |

**The key table is confirmed, twice over.** Round 66 derived it offline from the `FrKey.cpp` assertion
and predicted `0x75` (117) words; the live table holds exactly that, every word non-zero, and its
maximum exceeds 255 the way extended key codes do. The address is a second cross-check: the file's
preferred base gives `0x00C14C58`, and the live client — loaded at base `0x610000` — answers
`0x00E24C58`, the same RVA (`0x814C58`) rebased. The resolver finds the literal in the live image and
reads the live immediate, so it follows the load base; the file's number is only where the file would
put it.

**What this does not cover, and the run that does:** every member that *calls* the client — the
preference getters, `GetFPSLimit`, `SendUIMessage`, `Keydown`, `SetWindowVisible`, the four setters,
the dialog clicks — needs the game thread and the write path, i.e. an **elevated** connection:
`tests/probe_ui_manager_live.py` (the same command as above with that script).

## Live verification: the calling reads (round 76)

The same probe with the **write** connection (py4gw.connect(..., game_thread=True), elevated, pid 31024)
runs the members that call the client through ConnectedClient.call_function. Report:
tests/live_reports/ui_manager_calls_live.json.

| member | live answer |
| --- | --- |
| GetTextLanguage | **0** - Language 0, English |
| GetFPSLimit | **60** |
| GetEnumPreference(FrameLimiter) | **2** |
| GetIntPreference(NumberPreference.TextLanguage) | **0** |
| GetBoolPreference(FlagPreference.IsWindowed) | **true** |
| GetStringPreference(0) | **<email redacted>** - a real wide string, read from the client own pointer |

**Two independent cross-checks, both of them the sources own arithmetic.** The frame-limiter
preference reads 2, and GetFrameLimit own switch maps 2 to 60 (ui_methods.cpp:1840-1852) - which is
exactly the 60 GetFPSLimit answered. And GetTextLanguage **is** GetPreference(NumberPreference::
TextLanguage) - the number preference reads 0 and the language reads 0, the same value by both
routes. The string preference proves the wide-string read end to end: a real value, not a fixture.

Also verified by the same run: the write connection installs and removes its hooks cleanly (the probe
exits 0 through the context manager), and the four pure reads repeat their earlier answers exactly
(settings 798 bytes, key table 117 words, the same six window rects).

**What is still owed**: the members that ACT - SendUIMessage / SendUIMessageRaw, Keydown / Keyup /
Keypress, SetWindowVisible, SetWindowPosition, SetFPSLimit, the four setters, and the dialog clicks.
They change the client, so they are a deliberate, owner-present run, smallest effect first.

## Live verification: the value-preserving writes (round 77)

tests/probe_ui_manager_writes_live.py, elevated, write connection, pid 31024. Every write puts back the
value it just read, so the call path is exercised end to end while the client state stays as it was.

| member | call | before -> after |
| --- | --- | --- |
| SetFPSLimit | ok (no exception) | 60 -> 60 |
| SetWindowVisible(0, visible) | ok | true -> true |
| SetEnumPreference(FrameLimiter, 2) | ok | 2 -> 2 |
| SetIntPreference(TextLanguage, 0) | ok | 0 -> 0 |
| SetBoolPreference(IsWindowed, true) | ok | true -> true |
| SetStringPreference(0, ...) | ok | <email redacted> -> <email redacted> |

**unchanged: true** - the whole set read back byte-identical, and the connection installed and removed
its hooks cleanly (exit 0, same pid). Report: tests/live_reports/ui_manager_writes_live.json.

**Still owed, and only these**: the members that change the game - SendUIMessage / SendUIMessageRaw,
Keydown / Keyup / Keypress, SetWindowPosition, and the dialog clicks (ClickDialogButton /
ConfirmMaxAmountDialog, which need a dialog open). They are one owner-present run, because a key press
moves the character and a UI message does whatever the client listens for.

## Owed live pass: the game-changing members (owner-sanctioned later pass, 2026-09-27)

The owner ruled that the members not yet exercised live are **noticed here for a later pass** rather
than run now. These are the only members of the class with no live execution behind them, and each is
named so a later session can take it deliberately, one at a time, with the client watched:

| member | why it was not run | what a later pass asserts |
| --- | --- | --- |
| `SendUIMessage` | a UI message does whatever the client listens for — the source's own callers include `kLogout` | the message reaches the client and its effect is observed |
| `SendUIMessageRaw` | the same, with the caller's raw words | a raw word reaches the client's sender unchanged |
| `Keydown` / `Keyup` / `Keypress` | a control action moves the character | the client acts on the key, then the pair is released |
| `SetWindowPosition` | moves a built-in window — a visible change | the rect reads back as the one passed |
| `ClickDialogButton` / `ConfirmMaxAmountDialog` | need a dialog open | the dialog advances, as the already-live-verified `Frame.click` did in round 59 |

**What makes that pass small.** Four of the nine ride primitives that **are** live-verified: the dialog
clicks are `Frame.click` (a real dialog advanced, round 59), and `Keydown`'s key packet goes to a
frame's callbacks through the same sender `Frame.send_message` uses (rounds 58-59). `SetWindowPosition`
is the same four-word call as `SetWindowVisible`, which round 77 verified live. So the genuinely
unexercised surface is the two **message senders**.

**Live evidence the class does have**: 22 members — the four pure reads, the six calling reads, the
key-remap table (runtime-only), the dialog visibility pair, the window position/visibility pair, the
preference options, and the six value-preserving writes. Reports:
`tests/live_reports/ui_manager_reads_live.json`, `ui_manager_calls_live.json`, `ui_manager_writes_live.json`.

## Do not

- Do not port the 14 window classes (619-1302) — permanently out of scope.
- Do not add a singleton instance, a handler class, or any per-widget class.
- Do not re-derive a member's function; resolve it, cite it, and port it as the source writes it.
- Do not describe this class as ported without the seven divergences named beside it: it is **COMPLETE
  for this port's purposes** (owner's ruling, 2026-09-27) because each of the seven raises and names the
  injected runtime's own surface behind it — never because they were quietly filled in or stood in for.
  If the runtime's own journals, its link-opening flag or the client's ImGui ever arrive, those members
  stop being divergences and this doc says so.
