# Porting progress (live)

**This file is rewritten as work happens, so it can be read at any moment without asking.** If a
line in "Now" is older than the rounds below it, or the timestamp is stale, that is the signal that
something stopped — not something to wait on.

| | |
| --- | --- |
| **Goal** | `goal-856c3b8b-da31-4f92-bbd0-0a7c9db6bcc7` (was `goal-5bdc438e-712d-4582-bc5a-947069da6a92`, `Inventory` + `Item` + `ItemArray`, completed) — **port `UIManager` faithfully** |
| **Round** | 77 (**the value-preserving acting members are live-verified: 22 members now have live evidence.** tests/probe_ui_manager_writes_live.py runs each write with the value it just read, elevated on the write connection (pid 31024): **SetFPSLimit** 60 -> 60, **SetWindowVisible(0, visible)** true -> true, **SetEnumPreference(FrameLimiter, 2)** 2 -> 2, **SetIntPreference(TextLanguage, 0)** 0 -> 0, **SetBoolPreference(IsWindowed, true)** true -> true, and **SetStringPreference(0, ...)** returning apoguita@gmail.com - all six called without an exception, and **before == after: unchanged true**. So the call path is exercised end to end - game-thread connection, call form, the client own setter, the follow-ups - while the client state stays as it was, and the hooks came out cleanly (exit 0, same pid). What is left is the game-changing set: SendUIMessage/SendUIMessageRaw, Keydown/Keyup/Keypress, SetWindowPosition, and the dialog clicks, which need the owner watching the client. Reports: live_reports/ui_manager_writes_live.json) |
| **Round (prev)** | 76 (**the calling reads are live-verified, and two of them cross-check each other.** With the owner approving UAC, the probe ran elevated with the write connection (game_thread=True, pid 31024): **GetTextLanguage 0**, **GetFPSLimit 60**, **GetEnumPreference(FrameLimiter) 2**, **GetIntPreference(TextLanguage) 0**, **GetBoolPreference(IsWindowed) true**, and **GetStringPreference(0) = apoguita@gmail.com** - a real wide string read from the client own pointer. The cross-checks are the sources own arithmetic: the frame-limiter preference is 2 and GetFrameLimit maps 2 to 60, which is what GetFPSLimit answered; and GetTextLanguage IS GetPreference(NumberPreference::TextLanguage), where both routes read 0. The write connection also installed and removed its hooks cleanly (exit 0), and the four pure reads repeated their earlier answers exactly. **16 members are now live-verified**; what remains is the members that act, which change the client and so get an owner-present run, smallest effect first. Reports live_reports/ui_manager_calls_live.json and ui_manager_reads_live.json) |
| **Round (prev)** | 75 (**doc drift from my own later edits, found and fixed.** The owner ruling of round 72 changed this class verdict, but two places written before it still said the opposite: the Handoff section called CLASS_PORT_MAP INCOMPLETE and told a fresh session the class is never called ported until all 55 answer, and the doc closing **Do not** list repeated it. Both now say what the record says - **COMPLETE for this port purposes**, with the seven divergences named beside it - and the Do not entry is rewritten to forbid the real hazard: describing the class as ported *without* naming the seven, or filling them in with stand-ins. No code changed; a grep for any remaining UIManager-INCOMPLETE claim across docs now returns nothing. Suite OK; scoped pyright 0 errors. The only item still outstanding is the elevated call-based run, which needs the owner) |
| **Round (prev)** | 74 (**the unelevated live probe reaches ten members, and the preference options are the cross-check the setters needed.** Three more reads joined tests/probe_ui_manager_reads_live.py: **GetPreferenceOptions**, and the two dialog visibility members - which the probe can now drive because a FrameArray is constructible from the read-only reader, scanner and catalog the connection itself uses. Against Gw.exe pid 31024 (elevated: false): **FrameLimiter -> [0, 1, 2, 3]** - exactly the list SetPreference own follow-up switches on (1 -> 30, 2 -> 60, 3 -> the monitor rate, ui_methods.cpp:1840-1852) - and **AntiAliasing -> [0, 1, 2, 3, 4]**, both read from the client EnumPreferenceInfo entries; **IsNPCDialogVisible and IsLockedChestWindowVisible both false**, which is the correct answer with no dialog in flight and proves the members resolve the frame tree rather than raising. Ten members of this class are now live-verified unelevated; the members that call the client still need the elevated connection. Report live_reports/ui_manager_reads_live.json; suite OK; scoped pyright 0 errors) |
| **Round (prev)** | 73 (**the read half is verified against the live client - unelevated, and the key table is confirmed.** The elevation check of round 72 was true but incomplete: the project already had a route that needs none - the direct-memory probe shape probe_agent_effects_live.py established (ProcessMemoryReader plus RemoteScanner over the main module, a stand-in where require_client looks), which reads the client without connecting. tests/probe_ui_manager_reads_live.py runs the six pure-read members through it, and every one answered against Gw.exe pid 31024 with elevated: false: **all seven resolvers resolved**; IsWorldMapShowing false; IsUIDrawn **true** (the inverted flag); IsShiftScreenshot false; GetCurrentTooltipAddress 0x253D373C; GetSettings **798 bytes**; GetWindoPosition/IsWindowVisible real rects over six ids (window 0 [332, 76, 183, 140] visible, 0x40 [43, 237, 586, 732] not); and **GetKeyMappings 117 words - arrsize(s_remapTable) exactly - all 117 non-zero, max 260**. That closes round 66 derivation with live evidence, and the address cross-checks it a second way: the file preferred base gives 0x00C14C58, the live client at base 0x610000 answers 0x00E24C58 - the same RVA 0x814C58 rebased. Report live_reports/ui_manager_reads_live.json; suite OK; scoped pyright 0 errors. Still owed: the members that **call** the client (preference getters, GetFPSLimit, the senders, the keys, the window setters, the dialog clicks), which need the elevated connection) |
| **Round (prev)** | 72 (**the scope ruling lands and the class is closed out: UIManager is COMPLETE for this port purposes.** The owner ruled on the seven that raise - what is left is not applicable here, we do not have frame logs - so the six members that consume or publish the injected runtime own state (GWCA frame_logs journal, native g_ui_message_logs deque, its g_open_links flag, its PyCallback dispatcher) and the seventh, whose only consumer is the source own deactivated IO path, are recorded as **documented divergences on their members** - the form Player.player_instance, Agent.GetProfessionsTexturePaths and Dialog._call_native_dialog_method carry - not pending work. Each still raises and names what it needs; none returns a stand-in. **48 of 55 answer** and the verdict moved to COMPLETE for this port purposes in CLASS_PORT_MAP (both rows) and in the port doc. **The live pass is the only thing still owed, and this shell cannot run it: Win32.is_elevated() is False** while the client is up (Gw.exe pid 31024), and py4gw.connect() asserts elevation - a process cannot elevate itself, so the probe must be launched from an elevated shell by the owner. Suite OK; scoped pyright 0 errors) |
| **Round (prev)** | 71 (**the seven are enumerated in the port doc, one row each, so the scope decision no longer needs this conversation.** docs/UIMANAGER_PORT.md gains a table with, per member: its source line, the binding behind it, exactly what it needs, and the callers it has **in Reforged itself** — which is what says whether a mechanism is worth building. The split it makes plain: **six of the seven consume or publish the injected runtime own state** (its journal, its deque, its flag, its dispatcher) — the kind AGENTS.md records as a documented divergence, with Player.player_instance, Agent.GetProfessionsTexturePaths and Dialog._call_native_dialog_method as the three precedents — while **one (_UpdateFrameIOEvents) reads the client own ImGui context**, which is a real investigation. The two members of that family with genuine consumers answer already. No code changed: 48 of 55 answer, suite OK, scoped pyright 0 errors) |
| **Round (prev)** | 70 (**the live pass is wired into the project's own runner, so it cannot be forgotten.** tools/run_live_suites.ps1's default set gains tests/probe_ui_manager_live.py as its **second** entry - read-only and probe-shaped, so it belongs with the other read-only entries, ahead of everything that touches the client's state. One run of that script now covers every read this class answers, including the key-remap table whose 0x75 words exist only at runtime, and it writes live_reports/probe_ui_manager_live.py.log beside the others. The runner parses clean and the entry is in place. No class code changed this round: UIManager remains 48 of 55 with 7 target-side raises, the offline suite is OK and scoped pyright reports 0 errors. What the class still needs from a human is one elevated run and the scope decision on the three runtime-state members) |
| **Round (prev)** | 69 (**a wrong instruction is out of this project's own queue, and it was found by measuring rather than by reading.** Two documents — `FRAME_TREE_PORT.md`'s "Next" section and `UIMANAGER_PORT.md`'s queue — said that once the class landed, `Frame`/`_FrameTree`'s members should "delegate to `UIManager`". **The premise is false**: measured against the source, `FrameTree/frame.py` calls **49 distinct `PyUIManager.UIManager.<name>`** binding members and **the intersection with Reforged's `class UIManager` is empty — not one**. The class is the source's *Python* class (the preference surface, the built-in windows, the dialog helpers, the frame-IO events); `Frame` calls the injected *module's* binding (`button_click`, `SendFrameUIMessage`, `get_text_label_*`, `get_frame_array`, the traversal family), which that class never wraps. Acting on the instruction would have broken a cornerstone in one of two ways — calling a member the class does not have, or adding members the sources do not declare. Both documents now say what is true, `Agent.GetInstanceUptime`'s re-pointing (round 68) stands as the one that was real, and **the class is unchanged at 48 of 55 with 7 target-side raises** — this round added no code and removed a trap. Suite OK, scoped `pyright` **0 errors**) |
| **Round (prev)** | 68 (**the source's own route is restored, and the live pass has a probe ready to run.** Two small items off the queue, and both exist only because a class arrived late. **`Agent.GetInstanceUptime` now calls `UIManager.GetFPSLimit()`** — the source's own body (`Agent.py:280-294`) — where it had been reaching `GW::ui::GetFrameLimit` one layer lower through `py4gw/ui/preferences.py`, which was correct only while this class had no ported home; the member's docstring says so and the value is unchanged. **And `tests/probe_ui_manager_live.py` is written**: a read-only probe (`game_thread=False`, no hook, no patch, no call) that asks the client for every read this class answers — the three state words, the tooltip address, the text language, the option list and the four typed getters, the frame limit, the settings array's length, `GetWindoPosition`/`IsWindowVisible` over six window ids, the two dialog visibility reads, and **the key-remap table**, whose `0x75` words exist only at runtime because the table sits in `.data`'s uninitialised tail — so round 66's offline derivation finally has a witness. The command is in the port doc: `python tests/probe_ui_manager_live.py live_reports/ui_manager_live.json`, elevated; the acting members are a separate run with the owner present. **Suite 1538 tests OK**, scoped `pyright` **0 errors** on both files) |
| **Round (prev)** | 67 (**`Keydown`/`Keyup` answer on both branches, and the class has no conditional raise left: `UIManager` is 48 of 55 with 7 raises, all of them target-side.** The remaining branch was `frame_id == 0` — the client's own button-action frame (`ui_methods.cpp:161-164`: `GetFrameByLabel(L"Game")` then `GetChildFrame(frame, 6)`) — and it needed **no new mechanism**: both of its steps are `GW::ui` functions the catalog already carries. The label is hashed **by the client**, the wide label placed in the block's data region and passed to `g_create_hash_from_wchar_func(label, -1)` (`ui.create_hash_from_wchar_func`, the shape round 65 proved), then `GetFrameIDByHash`'s scan (the port's `FrameArray.frame_id_by_hash`), then one `g_get_child_frame_id_func` call (`ui.get_child_frame_id_func`, `:589-607`) — which is also the function `FRAME_TREE_PORT.md` had called a call this port could not make. The key packet is then sent to that frame's callbacks with `kKeyDown`/`kKeyUp` as before. **The finding is that two documented gaps were the same non-gap**: the label hash and the child walk both had resolvers and both are plain calls. **Suite 1538 tests OK** (+1 net), the UIManager file's 52 tests walk the zero-frame path call by call (the label's bytes and address, the `-1`, the child call, then the packet) and pin the walk stopping at each failed step, with the AST-derived counts **48 answer, 7 raise, 0 conditional**; scoped `pyright` **0 errors**. What remains is the runtime's own journals, its link-opening flag and the two frame-loop members — all target-side, all named) |
| **Round (prev)** | 66 (**the key-remap table is derived offline and both members answer: `UIManager` is 48 of 55.** The class's last *plain porting* gap is closed, and it was closed by reading the file rather than the client: Native binds no `get_key_mappings`/`set_key_mappings` at all, and the older runtime reaches the table through GWCA's `FindAssertion("FrKey.cpp", "count == arrsize(s_remapTable)", 0, 0x13)` — **whose own offset does not land on the table on this build**. So the resolver was derived instead (`ui.key_mappings_table` in `offsets/ui.json`): read the assertion's message literal out of `.rdata`, find its `.text` uses, and read the code around them — the `FrKey` entry asserts `count == 0x75` and then loads the table as an immediate — which gives a fixed **+0xD** from the message's use to that immediate, validated by a `.data` check on the result. **Measured, not guessed**: `tools/key_mappings_hunt.py` (offline, no client, no elevation) shows both uses read `0x00C14C58`, inside `.data`, and it honours GWCA's own comment — *"this address is fond twice, we only care about the first"*. **The same run produced a second fact worth keeping**: that address sits in `.data`'s **uninitialised tail**, so the table's contents are not in the file at all and only a live read sees them — which is exactly what the member does, and what the owed live pass has to confirm. `GetKeyMappings`/`SetKeyMappings` are in the class: `0x75` words read, `min(0x75, len(mappings))` written through `WRITE_MEMORY`. **Suite 1537 tests OK** (+5), the UIManager file's 51 tests carry the AST-derived counts — **48 answer, 7 raise, 2 of them only on a branch** — and scoped `pyright` **0 errors** on the class, its tests and the new tool. Every remaining item is target-side work with a name; there is no plain porting gap left in this class) |
| **Round (prev)** | 65 (**the wide-string item turns out not to exist, and `SetStringPreference` answers: `UIManager` is 46 of 55.** The queue's top item was "the wide-string argument form — one mechanism item that closes three members", and reading the port's own mechanism before building anything settled it in the opposite direction: **`ConnectedClient.bridge.write_data` places arbitrary bytes in the block's data region — memory *inside* the client — and answers that address**, which is exactly what a pointer argument needs, and it has been there since the block did. So there was no missing form: `UIManager.SetStringPreference` is now the caller's UTF-16 buffer written there with its address passed to `g_set_string_preference_func` (native's own shape, `ui_methods.cpp:1639-1651` ← `ui_bindings.cpp:1055-1057`'s `value.data()`), and the finding is recorded as **a correction of this project's own record** — the claim was in `TARGET_SIDE_WORK.md`, `FRAME_TREE_PORT.md` and `UIMANAGER_PORT.md`'s queue, and all three now say what is true. **What that leaves is precise rather than vague**: `_FrameTree.hash_for_label`/`by_label` are one call each over `ui.create_hash_from_wchar_func` (already in the catalog) with the label placed the same way, and `Frame.set_text` is the only member of the original three still blocked — on the client's own `TextLabelFrame::SetLabel` (`ui_bindings.cpp:1447-1452`), a method inside the client rather than a `cdecl` function a catalog can name. **Suite 1532 tests OK** (+2: the text's bytes and address, and the refusal when the setter is unresolvable), the UIManager file's 46 tests carry the corrected AST-derived counts — **46 answer, 9 raise, 2 of them only on a branch** — and scoped `pyright` **0 errors**. Next: the key-mapping resolver (the one item needing new offline pattern work), then the runtime-state captures, the frame-loop members, the two re-pointings and the live pass) |
| **Round (prev)** | 64 (**the preference setters and the UI-message senders: `UIManager` is 45 of 55.** Two items off the queue in one round, both of them porting rather than design. **The three typed `SetPreference` bodies are ported**, branch for branch, into `py4gw/ui/preferences.py` — the home this port already keeps the `GW::ui` preference functions in — so `SetEnumPreference`, `SetIntPreference` and `SetBoolPreference` answer with native's own guard, validation, clamp and follow-up: the option-list scan and the `AntiAliasing 2 -> 1` / `TerrainQuality`/`ShaderQuality 0 -> 1` rewrites, `ClampPreference` through **the client's own `clamp_proc`** (a function pointer called with `call_address`), and the follow-ups that drive the two renderer paths, the shadow quality, the terrain rerender, the reflections, the UI scale, the five volume channels, the master volume and the eleven renderer metrics. **The finding that came out of it is the sharpest this port has recorded about the two sources**: Reforged's `NumberPreference` **swaps `EffectsVolume` and `BackgroundVolume`** (`UI_enums.py:387-389` has `BackgroundVolume = 24 … EffectsVolume = 26`) where native (`common/constants/ui.h:261-266`) *and* the older runtime's GWCA (`UIMgr.h:912-914`) both have `EffectsVolume, DialogVolume, BackgroundVolume`, and Reforged's table stops at `Count = 41` where both others say `44` — so the member's switch (native's own body) sends the number a Reforged caller passes to the *other* branch; the port uses native's values and a test pins both tables. **`SendUIMessageRaw` answers, and `SendUIMessage` lost its two-word limit**: `ConnectedClient.send_ui_message_raw` is the raw three-word call of the **held** sender address (`CallForm.U32_U32_U32` — the one route that must not re-resolve a patched entry), and `SendUIMessage` now builds native's **sixteen-word** payload in the block's data region, copies `values` into the front and calls that path, with `RawSendUiMessage`'s own `false`-without-a-sender and masked-`true`-without-sending answers. Both members' `skip_hooks` is recorded as the divergence it is (this port has neither the runtime's message log nor its callback registry). **Suite 1530 tests OK** (+9), the UIManager file's 44 tests include the corrected AST-derived counts — **45 answer, 10 raise, 2 of them only on a branch** — and scoped `pyright` **0 errors** on `ui_manager.py`, `ui/preferences.py`, `client.py` and the test file) |
| **Round (prev)** | 63 (**`UIManager` lands as a class: 55 declarations, 35 answering, 17 naming their work.** The owner asked for the pending porting work and settled the two open calls — the class lands as `py4gw/ui_manager.py` holding **`class UIManager`** (the sources' own class name; `PyUIManager` is the injected *module*), and the port is offline-first with the live passes named rather than started. **Step 1 of the plan — pin the binding map member by member — is done and is a table in `docs/UIMANAGER_PORT.md`**: for each of the wrapped members, its binding in `ui_bindings.cpp`, the `GW::ui` function in `ui_methods.cpp` behind it, and the port's route. **The measurement that mattered: eleven of Reforged's 41 `PyUIManager.UIManager` calls have no `.def_static` in native's current revision** — native's own audit lists several as pending quick wins (`docs/binding-parity-audit.md:29`), so those members resolve the function the binding *would* wrap (`async_decode_str` → `AsyncDecodeStr`, `draw_on_compass` → `DrawOnCompass`, `set_window_position` → `SetWindowPosition`, `load_settings`/`get_settings` → `LoadSettings`/`GetSettings`, `get_current_tooltip_address` → `GetCurrentTooltip`), and the five with nothing behind them at all — `get_frame_logs`, `clear_frame_logs`, `get_key_mappings`, `set_key_mappings`, and `SetOpenLinks`'s effect — raise with the reason on the member. **What answers**: both IO registries and the event read, the three state words (`IsWorldMapShowing`'s `0x80000` mask, `IsUIDrawn` **inverted** with `true` for an unresolved address, `IsShiftScreenshot`), the tooltip address, the settings pair, the four preference getters and the options list, the frame limit pair, the four enc-string members, `AsyncDecodeStr`, `DrawOnCompass`, the window trio, `SendUIMessage`, `Keydown`/`Keyup`/`Keypress` (the frame's own callbacks with a one-word `KeyAction`), and **all nine dialog members** — `ClickDialogButton` is the live-verified `Frame.click`. **Five findings, all recorded**: three of Reforged's Python enum tables disagree with native's C++ constants (`WindowID_Count` 0x69 vs **0x66**, `NumberPreference.Count` 41 vs **44**, `FlagPreference.Count` 0x5D vs **0x5E**) and the members use native's where the check is native's; `GetWindoPosition` means raw `p1`/`p2` in native and derived viewport axes in the older runtime (the port ports native's, which needs no DX context); `SetWindowPosition`'s shipped binding wrote the four floats into the client in place before calling, and this port passes the struct to the client's setter instead; `UInt32ToEncStr` cannot encode past `7 * WORD_VALUE_RANGE` (227584) because the binding passes count 8; and `GetDialogButtonFrames`'s own annotation says ids while its body returns handles. `py4gw/ui/preferences.py` grew the three remaining typed getters and `set_frame_limit` (the `WRITE_MEMORY` write) for the members that reach it. **Suite 1521 tests OK** (+35 in `tests/test_ui_manager_offline.py`, which AST-compares the 55 declarations and their nesting against Reforged's own file and pins the raising set), scoped `pyright` **0 errors**. Next: the four preference-setter bodies, the raw/wide UI-message forms, the key-mapping resolver, then the two re-pointings (`Agent.GetInstanceUptime` → `UIManager.GetFPSLimit`, `Frame`'s members → this class) and the live pass) |
| **Round (prev)** | 62 (**the client crashed inside this project's injected code — recorded, and write tests are on hold until the effects observer is fixed.** Dump: `c0000005` reading address `00000006`, `eip=03e900b0` — an address **outside `Gw.exe`** (base `00610000`), i.e. dynamically allocated code — with `ebx=03720000` pointing at memory whose first bytes are `4b4c4253` (**"SBLK"**, this project's shared block) and a trace of our code ← `009eca36` (in the client). The faulting bytes at `03e900b0` are `8b 4a 00 / 89 4f 08 / 8b 4a 04 / 89 4f 0c …` — a multi-dword copy **from `[edx]` into `[edi+8…]`** with **`edx=00000006`**: a small integer dereferenced as a pointer. That is the shape the port's own raise text on `Effects.GetAlcoholLevel` already describes as unbuilt — *the observer reads the hooked function's second argument as a packet pointer, while native's post-process handler stores the two plain word arguments* (`payload.py:762-765` vs `effects.cpp:24-41`) — so the leading candidate is **the effects observer dereferencing a word argument (6) as a packet**. The run immediately before was the `UseItem` probe, whose **disconnect then failed to drain** (`observe_effects still had 1 call(s) inside its stub 2.0 s after its entry was restored; nothing was freed`), which is a second candidate: a hook left installed while the host is gone. **Nothing of this project's is in the client now** — the owner restarted it at 17:49:51 (pid 31024) — but **no write connection should be made until the observer's argument shape is fixed**, because connecting is what installs it. **Fixed the wrong read in the same round**: the effects hook is no longer handed a packet watch list (`py4gw/game_thread/bridge.py`, the dump evidence written into the code comment), so the emitted observer validates and returns instead of dereferencing a word — the crash is no longer reachable from a connect; suite **1594 tests OK**, `pyright` 0 errors. **What remains is the shape, not a workaround**: an observer that carries the call's own two words into the event, which is native's own handler (`OnPostProcessEffect(uint32_t intensity, uint32_t tint)` stores `intensity` and calls the original, `effects.cpp:32-41`); until it is built `Effects.GetAlcoholLevel` keeps raising — and now names a *missing shape* rather than sitting behind a read that faults. **And the live re-run closes the analysis (round 62)**: the cider experiment repeated cleanly — **222 → 221** in 0.75 s (`live_reports/use_item_live2.json`), `hooks after disconnect = []`, **no drain error at all**, and the client alive afterwards (pid 31024). That the drain failure vanished together with the dereference is the evidence the two were **one event**: the observer call that faulted was the call the drain was waiting on, so the counted path is not separately wrong — and the earlier "still to check" is answered. `Effects.GetAlcoholLevel` still raises, now naming the unbuilt words-carrying shape rather than sitting behind a read that faults) |
| **Round (prev)** | 61 (**`UseItem` is live-verified: 223 → 222.** The owner's experiment, and it proves the whole chain in one number — a **Hard Apple Cider** stack (`ModelID.Hard_Apple_Cider` = 28435, item **237**, slot 3, found with `ItemArray.GetItemArray` over `GetAllBags()`) read **223** before and **222** after `Inventory.UseItem(237)`, 0.79 s later, through `Inventory.GetModelCount` **and** `Item.Properties.GetQuantity`. That is the Reforged member → `inventory_instance()` → the binding's `UseItem` → `GW::item::UseItem` → **round 57's interact guard and `item.use_item_func(item->item_id)`**, on a real item. `IdentifyItem`/`Salvage`/`EquipItem` stay offline-verified by the owner's call (no disposable items). **Two findings from the same run:** (a) the disconnect refused to free — `observe_effects still had 1 call(s) inside its stub 2.0 s after its entry was restored`, so the round-55 fix did what it is for: the entry went back, nothing was unmapped under a live instruction pointer, and the probe reported it instead of dying; (b) `Effects.GetAlcoholLevel` raises — the effects observer's **second event shape** (the call's own words, rather than a dereferenced packet) is still unbuilt, which is that module's recorded divergence, not the trio's) |
| **Round (prev)** | 60 (**the item trio's reads are live-verified, and the owner's call settles the actions** — `tests/probe_items_live.py` (read-only: `game_thread=False`, no hook, no patch, no call) walked the client's own bags: **20 bags**, **342 item ids**, cross-checked against `Inventory` (`[39, 60]` space with **21** free — 39 + 21 = 60), twelve items described with coherent client data (a `[29, 'Kit']` of model 5899, `[11, 'Materials_Zcoins']` stacks of 44 and 59, a Gold `[30, 'Trophy']`), and the source's own finders answering real ids (ID kit 12374, unidentified item 20112, salvage kit 18957). Two corrections were the probe's, neither a port defect: `Bag` members need `.value`, and **`CreateBagList()` with no ids is `[]` in the source itself** (`ItemArray.py:9-26`, no default), so the walk passes `GetAllBags()`. **The four action members stay offline-verified only** — the owner has no disposable items to spend on them and ruled them assumed-working-but-untested; the ids that would prove them are recorded in `ITEM_PORT.md` §4. **A naming finding is open and measured**: the library carries **8 `Py*` classes** (`PyEffects`, `PyItemType`, `PyDyeColor`, `PyDyeInfo`, `PyItem`, `PyInventory`, `PySkill`, `PySkillbar`), which the cornerstone forbids (a source's injected-module name on one of this project's classes — the `PyDialog` precedent); six have an unambiguous target, while `PyItem`/`PyInventory` need the owner's naming call, because native's *class* names are literally those and `Item`/`Inventory` are already the Reforged classes here) |
| **Round (prev)** | 59 (**live: the frame-message call is the client's `__thiscall` shape, `Frame.click` works, and the client acts on it.** The read-only probe resolved `ui.send_frame_ui_message_func` on the 2026-09-27 client at `0x85cd80`, read its prologue (`mov esi,[ebp+8]`, `mov edi,ecx`) and its `ret 0xc`, and confirmed the first word's arithmetic against five live frames — native declares that target `void(__fastcall*)(callbacks, void* edx, message_id, wparam, lparam)` (`ui_patterns.cpp:32`), so round 58's five-pushed-word cdecl call was **wrong** and is now `CallForm.FASTCALL_U32_U32_U32` (arg1→ECX, arg2→EDX, three stack words, and the callee pops them), covered offline by a witness that releases its own words. **`Frame.click`** (native `ui::ButtonClick`, `ui_methods.cpp:1249-1274`) is built on it: the parent is reached by relation pointer, both `IsCreated` checks are made, and `MouseAction{child_offset_id, child_offset_id, MouseUp, &ButtonParam{0, field105_0x1c4, 0}, 0}` is placed in the block's data region and sent as `kMouseClick2` to the **parent's** callbacks. **Two defects the live runs found and fixed**: the dialog handler read `player_number` off the *base* agent record — native takes the living view (`GetAgentModelIdSafe`, `dialog.cpp:201-218`) — which killed the listener the moment a dialog opened; and the probe's tree diff was keyed by frame *hash*, which collapses every unnamed frame (most carry hash `0`), so it could not see a new window at all. **The live click, driven exactly as directed**: 597 created frames → interact with agent 17 → 609 in 0.52 s (name tag + two `template 1` dialog buttons) → click on button frame 599 → the client **advanced the dialog** (609 → 625 frames, the window's children 3 → 2), then a clean disconnect with no hooks left. Suite **1594 tests OK**, `pyright` 0 errors) |
| **Round (prev)** | 58 (**the whole-project `pyright` gate is clean, and `Frame.send_message` answers** — the seven errors that were outstanding were all in this project's own example/probe/test files: `examples/context/agent_array.py` called `py4gw.context.agent_array.get()`, which does not exist (the accessor is `client.agent_array.get_context()`, as `examples/all_contexts.py:43` already uses); `tests/probe_alcohol_live.py` read `client._bridge`'s members through an `Optional`; and `tests/test_mods_types_offline.py` iterated a value typed as `type`. All three corrected, so **`pyright` over the whole project reports 0 errors**. Then the first member of the frame-action group: **`Frame.send_message`** calls the client's own callbacks-based sender (`ui.send_frame_ui_message_func`, native's `g_send_frame_ui_message_original`) with native's own **five** words — `&frame->frame_callbacks` (the frame record's address plus the field's `0xA8`), a null second word, the message id and the caller's two words — behind native's own guard (`frame && frame->frame_callbacks.size()`), and answers the binding's `true` (`ui_bindings.cpp:1066-1072` → `ui_methods.cpp:1332-1345`). **`Frame` is 94 of 115**; the remaining frame actions are `click`/`double_click`/`mouse_action`/`mouse_click_action`/`send_message_text`/`set_text` plus the five setters. Suite **1585 tests OK**) |
| **Round (prev)** | 57 (**the interact guard is ported, and the four members it held act** — `CanAccessXunlaiChest`, `IsStorageBag`, `IsStorageItem` and `CanInteractWithItem` are in `py4gw/py_inventory.py` in native's own order (`item_methods.cpp:52-74`), over native's `Context::Region` (`context/map.h:56-85`, 28 members, now ported with its stub). **`UseItem`, `EquipItem`, `IdentifyItem` and `Salvage` answer** — one catalog call each, plus the `kPreStartSalvage` packet and the salvage session for `Salvage` — and so does the module function `salvage`, which native gives the same body. **`PyInventory` is 15 of 17 members + 3 of 4 module functions**; the two that raise are the StoC emulation and the frame click. **One divergence is recorded on `_can_access_xunlai_chest`**: native reads `Context::GetAreaInfoArray()[GetMapID()]`, this port reads the instance-info record's own pointer — the same `AreaInfo` for the current map; the global array is what `Map.GetUnloadedMapInfo` still raises for. Suite **1581 tests OK**, scoped `pyright` **0 errors**) |
| **Round (prev)** | 56 (**the bag predicates were answering the wrong question, and it is fixed** — native's `bag_type` *is* `Constants::BagType` (`context/item.h:54`) and every predicate over it compares `BagType` members (`:62-64`, `:139-140`), but this port compared it against `Bags` **ids**: `8` is `Storage1`, `6` is `MaterialStorage`, `22` is `EquippedItems`, where native compares `Storage` `4`, `MaterialStorage` `5`, `Equipped` `2`. So `is_storage_bag`/`is_material_storage` answered **False for every real storage and material-storage bag** and `is_inventory_item` missed equipped items — a wrong value returned to callers, not a gap. `BagType` is now ported (`py4gw/context/item_context.py`, zero member spelled `None_` as the sources spell it), `BagStruct`'s and `ItemStruct`'s predicates carry native's own bodies, the invented snake_case duplicates that held the wrong constants are gone from both context structs (those names belong to the binding, which this port already carries on `item.py`), and the fixtures that encoded `bag_type=8` now use `BagType.Storage`. Suite **1566 tests OK**, `pyright` **0 errors**) |
| **Round (prev)** | 55 (**the crash's fix, not the porting** — hook stubs now count the calls they hold and `remove` waits for that count to reach zero before freeing any generated code, native's own answer; the trampoline is never freed. Verified by running the stub offline: the payload sees the count at 1, a disabled hook is never counted, a stuck count raises with nothing freed. The replay did **not** reproduce the crash, and it stays recorded as unattributed) |
| **Round (prev)** | 54 (**the salvage dialog closes: `Inventory` is 53 of 57** — the option assembly, the click strategy and the formatter are ported, and the four that raise are all documented divergences (Reforged's coroutine protocol, the injected console). The class is COMPLETE for this port's purposes) |
| **Round (prev)** | 53 (**the geometry answers** — `rect`, `size`, `coords`, `viewport_scale` and `content_coords` are native's own `FramePosition` methods over the root frame and the captured render viewport, so **`Frame` is 93 of 115** and the feature list is down to three. The arithmetic is ported where native puts it, and the render accessors as `get_viewport_size()`) |
| **Round (prev)** | 52 (**`FrameTree.root()` answers** — the catalog's `ui.get_root_frame_func` called on the client's own thread, native's `GetRootFrame`, with the id read at `+0xBC` and the source's cache kept; `viewport_height` reads through it, so the tree is 33 of 41. A wrong claim of mine is corrected in the same round: the geometry needs the root *and* the capture, not the capture alone) |
| **Round (prev)** | 51 (**the DX-context capture is live-verified** — the read-only probe pinned EndScene's prologue, then the write connection captured the client's own context: viewport **1678×1368**, device `0xA9B7C40`, 4512 bytes read there, and the hook came back out on disconnect. The geometry's last input is in hand; its consumers are next) |
| **Round (prev)** | 50 (the DX-context capture is **wired into the bridge** — a third hook, entered rather than observed-after, keeping the argument in a data-region slot with `observing_render`/`render_context_address()` and the removal ordered first; offline-verified in `CaptureTests`. One live-derived value is left: EndScene's five-plus whole-instruction prologue, which the other three hooks pin as constants read from the client) |
| **Round (prev)** | 49 (the DX-context capture starts: native's capture is a **variable, not a queue** — `g_dx_context = ctx` on every `OnEndScene`/`OnReset`, `render.cpp:88`/`:103` — so a **slot-capture stub** is added to the payload and offline-verified (it keeps one argument of a per-frame function in a block slot and appends no event); wiring it into the bridge and the live run are next) |
| **Round (prev)** | 48 (the geometry's open question is closed by reading the code to its last hop: the on-screen arithmetic is pure, and it needs exactly two client-side inputs — the root frame and the DX context; `Map.MissionMap.GetScale` needs only the second, so the detour capture unblocks it first) |
| **Round (prev)** | 47 (**`Inventory` jumps from 36 to 50 of its 57 methods** — the `FrameTree` package paid off: 14 salvage-dialog members ported, including the frame lookups, the children map, the option text and the entry helpers; the 7 that remain are measured and named) |
| **Round (prev)** | 46 (**the `FrameTree` package is complete** — its seventh module, the source's own `__init__` re-export list, is ported and compared name for name against the source's `__all__`; all seven modules are now in place, and both classes carry their verdict rows in the class map) |
| **Round (prev)** | 45 (**`_FrameTree` is declared in full too** — 41 of 41, in source order, 32 answering — so both classes' surfaces are complete; the round's finds: `hierarchy`'s docstring disagrees with the native function it binds, `GetOverlayFrames` and `GetPopupFrames` are byte-identical, and `coords_for_hash` is a hash scan plus two truncated corners) |
| **Round (prev)** | 44 (`_FrameTree` reaches **32 of 41** — the eight members that waited on `Frame` existing are in — and **both classes' members are now in the source's own order**, verified against both ASTs; the last geometry members are pinned to exactly two client-side inputs: the root frame and the render viewport) |
| **Round (prev)** | 43 (`Frame` is declared **in full** — all 115 members, in the source's own order, verified against the source's AST — with **89 answering**; `layer`, `opacity`, `clip_rect` and `hover` land, and the 26 that cannot answer are grouped into four features) |
| **Round (prev)** | 42 (**all 115 of `Frame`'s members are declared**, 100 built — the native walkers land: parent pointers, child-by-hash, the four relation branches and the ancestor chain, every one a read once two pointer rules from native are applied; five bindings turn out to be one native walker) |
| **Round (prev)** | 41 (`Frame` reaches its navigation (**79 of 115**) — and a defect from round 40 is found and corrected: the source's `position` is a *binding-side wrapper*, so `rect`/`size`/`viewport_scale` now name the root-frame computation they need, and the geometry tests are rebuilt on the **real** ctypes records so that class of error cannot hide again) |
| **Round (prev)** | 40 (`Frame` reaches its geometry — `text`, `encoded`, `rect`, `size`, `coords`, the two viewport reads; **70 of 115** — and every action/setter binding is found to be a **game-thread enqueue** in native, so those members are declared and name the one call each needs) |
| **Round (prev)** | 39 (`Frame` reaches its inspection members — siblings, `fields`, parameters, the record reads; **56 of 115** — and the three injected calls behind `state_bit`/`user_param`/`context` are each resolved to one record field, so they answer) |
| **Round (prev)** | 38 (`Frame`'s read surface lands — identity, path, the registry/alias inversions, the state and record reads; **`Frame` is 47 of 115** — and the label/title pair is found to be one client call: the title-table binary search) |
| **Round (prev)** | 37 (the two injected frame lookups resolved: `GetFrameIDByHash` is a read and `anchor_ids`/`by_hash` answer with it, `GetHashByLabel` is the client hashing a wide string and the three members that need it say so; `Frame._resolve` and `Frame.exists` land) |
| **Round (prev)** | 36 (`Frame`'s twelve indexed accessors land — 22 of its 116 declarations in; and the funnel is found: `_resolve` needs `anchor_ids`, so the injected `UIManager` layer is the next feature) |
| **Round (prev)** | 35 (`Frame` starts — the constructor and every handle builder, `:678-793`, with 14 tests; the class is grown in source order) |
| **Round (prev)** | 34 (`Frame` mapped before it is written: 74 of its 115 members call nothing injected, 39 properties wrap one `UIManager` member each; and 11 of `_FrameTree`'s remaining 24 call the client directly, so they do not wait on `Frame`) |
| **Round (prev)** | 33 (`_FrameTree` stops at 24 members — every remaining one needs `Frame`, so the order flips) |
| **Round (prev)** | 32 (the per-frame state cache: `state`, `_prune`, `invalidate`, with the memo dropped and the buffer kept) |
| **Round (prev)** | 31 (`_FrameTree`'s structure queries: `all_ids`, `children_map`, `live` and eight more answer) |
| **Round (prev)** | 30 (the state cache is tick-keyed in two more places — decided, so the queries can follow) |
| **Round (prev)** | 29 (`_FrameTree`'s lifecycle and snapshot are in — `rebuild` over the port's frame-array read) |
| **Round (prev)** | 28 (`_FrameTree`'s snapshot is tick-keyed — the decision that governs all 41 members is recorded) |
| **Round (prev)** | 27 (`_FrameTree` mapped member by member: 28 of its 41 need nothing injected, 13 name their call) |
| **Round (prev)** | 26 (`frame.py`'s first section ported: `FrameState`, `resolve_key` and the two reverse lookups) |
| **Round (prev)** | 25 (`FrameTree`'s five table modules ported — 5,010 lines, parity-checked; the logic is next) |
| **Round (prev)** | 24 (the dialog's cascade measured: `Inventory` is 36 of 57, and the 21 that raise split 17 / 3 / 1) |
| **Round (prev)** | 23 (the two storage walkers: both in, and only the salvage-choice dialog left) |
| **Round (prev)** | 22 (the four-word call form: the capability layer gains it, verified by its own witness, and `MoveItem` answers) |
| **Round (prev)** | 21 (`Inventory`'s storage, action, gold and find bodies: 33 of 57 methods now answer, 24 named) |
| **Round (prev)** | 20 (`Inventory` starts: 66 declarations, 18 of its 57 methods built, 39 named) |
| **Round (prev)** | 19 (`ItemArray` is FULL — 14 declarations, and both of its source quirks pinned by tests) |
| **Round (prev)** | 18 (the bag surface: `py_inventory.py`, and **`Item` is FULL** — no raising member left) |
| **Round (prev)** | 17 (`Item` ported: 125 declarations, and the binding it reads through carried with it) |
| **Round (prev)** | 16 (`mods_types`, `mods_upgrades` and `mods_core` — the item vocabulary and the decoder, ported ahead of the class that needs them) |
| **Round (prev)** | 15 (the item port: the three classes' surfaces pinned, the cascade and the order of work written down) |
| **Round (prev)** | 14 (`Effects`' alcohol capture: native's own hook is in the client, and the live run showed exactly which one piece is left) |
| **Round (prev)** | 12 (a name is decoded by the client: 15x faster than the dat route, and no dat record at all) |
| **Round (prev)** | 11 (the dat handling moved off the call path: pre-cached at connect, on a worker) |
| **Round (prev)** | 10 (the owner's second catch: the agent viewer's own scheme, and one name end to end) |
| **Phase** | **a name is decoded by the client** (`Agent.GetNameByID` = Native's `AsyncGetAgentName` route): ~115 ms the first time, 0.09 ms cached, **no dat read at all**; the connect-time dat warm-up is off, `dialog._on_string_decoded` no longer steals other modules' decodes, and a disconnect gives unclaimed name slots back (1074 tests OK) |
| **Phase (prev)** | **the GW.dat work is off the call path**: the connection starts the source's own load on one worker, the table is readable file by file, a decode asks for the one slot it needs instead of reading it, and `disconnect` joins the worker (1073 tests OK) |
| **Phase (prev)** | live: the viewer's scheme read member by member; **one name tested alone** (agent 15, gadget, `\x0C6E` -> "Random Arenas"), six agents put through the port's decoder and the client's; the slot mapping verified live for the first time; the ring cost measured (~1.0 s per string file) |
| **Phase (prev 2)** | live: names walked on all four branches with 0 byte mismatches; two client crashes traced to a killed run's orphaned patch |
| **Phase** | **`Camera` is FULL**: 46/46 members answer, live-verified (reads median 5 us, a write read back from the client's own struct, the camera-unlock patch proven byte-for-byte); the payload gained `WRITE_MEMORY` so a member can change client state on the game's own thread, and the class now caches a patch's address *and* bytes the way `MemoryPatcher` does |
| **Verdicts** | **`Agent`: COMPLETE for this port's purposes** (148 declared, 145 answer; the 3 that raise are two frame-loop halves and the injected-runtime artifact), **`AgentArray`: FULL**, **`Camera`: FULL (2026-09-27)**, **`Inventory`: COMPLETE for this port's purposes (53 of 57 methods; the 4 that raise are Reforged's three coroutine generators and the injected console's log)**, **`Item`: FULL**, **`ItemArray`: FULL**, **`FrameTree` package: all seven modules in, neither class FULL** (`_FrameTree` 33 of 41 answering, `Frame` 93 of 115) -- all counted from the modules' own ASTs |
| **Package status** | **`FrameTree`: the package is complete** — all seven of its modules are in place (the five tables verbatim, `frame.py` with both classes declared in full in the source's own order, and the source's own `__init__` re-export list). `_FrameTree` 41/41 declared (**32 answering**), `Frame` 115/115 (**89 answering**); both counts measured from the module's AST, order compared against the source's. **Neither class is FULL** — what is left is named, not unknown: the game-thread frame actions, the root-frame geometry, the client's title table + ImGui + the overlay, and the client-call lookups ([`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md)). Next: the salvage dialog's 17 `Inventory` members, which is why the package was ported. |
| **Verdicts (prev)** | **`Agent`: COMPLETE for this port's purposes** (148 declared, 145 answer; the 3 that raise are two frame-loop halves and the injected-runtime artifact) and **`AgentArray`: FULL** (no raising member) -- both from the modules' own AST, 2026-09-27 |
| **Updated** | 2026-09-27 (round 55 — the teardown fix: 1454 offline tests OK, pyright clean; a replay of the crash sequence did not reproduce it, and the client has been untouched since) |

## Now (round 33 - the next seven queries all need `Frame`, so the order of work flips)

**What this round established.** Round 31 named eighteen "clean" queries and ported eleven of them. Reading
the other seven (`frame.py:517-636`) showed that **every one goes through the `Frame` class**, which is not
ported:

- `all_frames` (`:517-518`) is `[Frame.from_id(f) for f in self.all_ids()]`;
- `_as_id` (`:528-533`) is an `isinstance(..., Frame)` test plus `frame_or_id._target_id()`;
- `descendants` (`:535-537`) wraps `Frame.from_id` around each id, and `descendants_of` (`:539-552`) starts
  with `self._as_id(frame_id)`;
- `root` (`:554-560`) needs `PyUIManager.UIManager.get_root_frame_id()` **and** `Frame.from_id`;
- `viewport_height` (`:562-567`) is `self.root().viewport_dimensions()`;
- `frames_at_path` (`:598-606`) needs `self.anchor_ids(anchor)` — an injected member — and returns `Frame`s;
  `frames_under` (`:608-614`) and `_frames_at` (`:616-632`) are the same shape;
- `sort_by_vertical` (`:634-636`) sorts by each `Frame`'s `rect`.

**So `_FrameTree` is as far as it can go**: 17 of its 41 members are ported (the lifecycle, the snapshot, the
eleven structure queries and the state cache) and **all 24 that remain need `Frame`** — thirteen of them
directly, eleven through the injected `UIManager` calls `Frame` will hold. The order of work for the rest of
the package is therefore settled: **`Frame` (`:679-1620`, 115 members) first**, then those thirteen, then the
source's own `__init__`.

**Why that is worth a round rather than a guess.** Writing `all_frames` "for now" without `Frame.from_id`
would mean inventing a stand-in for a source class — the exact failure `docs/PORTING_RULES.md` records from
`Context.py`/`_area` — and porting the queries in a different order would have produced members that cannot
run. The boundary is now measured and recorded in [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) §2, with each of
the seven and the `Frame` member it needs.

**No code changed this round.** Suite unchanged at **1319 tests OK**, `pyright` clean. Next: `Frame` — its
`from_id`/`from_hash`/`from_label` constructors, `_target_id`, `rect`, `viewport_dimensions` and the rest of
its 115 members, resolving the remaining `PyUIManager.UIManager` call sites one at a time.

## Now (round 32 - the per-frame state cache is in, written to the decision rather than around it)

**What moved.** `state`, `_prune` and `invalidate` (`frame.py:378-423`) — the tree's per-frame live copies,
which every geometry read behind it goes through. The port follows the round-30 decision exactly:

- **the per-tick memo is gone** (`:387-389`): with nothing advancing `tick`, that test would hand back the
  *first* copy of a frame for the life of the process, so the member reads when it is called, as `ensure`
  does. The docstring marks the dropped test and why, so the divergence is on the member and not only in a
  doc;
- **the buffer rule is kept exactly** (`:392-401`): a blank read inherits the last good copy while
  `previous.served < BUFFER_TICKS`, bumping `served` and stamping `previous.tick`. What it counts is polls,
  which the source's own comment states ("Counted in polls, not time"), and polls still exist here;
- **the age-based prune is ported as written** (`cutoff = self.tick - 240`) with the limitation recorded on
  the member: without a ticker the cutoff never advances, so it cannot fire. It is the one piece of the cache
  that genuinely depends on the frame loop, and it is not given an invented clock.

**Verification.** `tests/test_frame_tree_frame_offline.py` grew to **41 tests**, six of them new: a landed
read being stored; **a second call reading again** — which is the adaptation made observable, since the
source's memo would have answered the first copy forever; the buffer driven **to its bound and past it**
(the good copy stands in for exactly `BUFFER_TICKS` polls, then the blank read is stored and the truth is
told); a frame that was never good getting the blank read rather than a stand-in; `invalidate` dropping one
copy, then all of them, and tolerating an id with nothing cached; and `_prune`'s cutoff rule exercised on
both sides of `self.tick - 240` — which is the only way that rule can be shown to be the source's, since
nothing in the port will ever call it.

**Suite: 1319 tests OK** (was 1313); `pyright` 0 errors on `frame.py`. Next: the remaining queries
(`descendants`, `descendants_of`, `viewport_height`, `frames_at_path`, `frames_under`, `_frames_at`,
`sort_by_vertical`, `color_frames`), then the twelve injected members and `Frame.from_id` — which `all_frames`
and `_as_id` are waiting on.

## Now (round 31 - `_FrameTree`'s structure queries are in: eleven members answer, including the two the dialog walks)

**What moved.** The clean section I named last round — the queries that read the snapshot and touch neither
the tick nor the injected runtime — is ported (`frame.py:462-526`): **`child_of`, `children_at`,
`children_of`, `child_codes_of`, `parent_of`, `hash_of`, `code_of`, `known`, `live`, `all_ids` and
`children_map`**. Eleven members, and two of them — `all_ids` and `children_map` — are calls the
salvage-choice dialog makes; the third it makes, `all_frames`, cannot be written yet because its body is
`[Frame.from_id(f) for f in self.all_ids()]` and **`Frame` is the 115-member class still to come**. The same
is true of `_as_id`, whose body type-tests a `Frame`.

**`live` is the section's one resolved call, and the source's own comment says how.** It asks the engine
whether a frame is real, and insists on a **raw** read — "never the retained copy, or existence would feed on
the very cache it is meant to validate and a removed frame would never die" (`:503-505`). The port's raw read
is the one `rebuild` already uses: `client.frame_array.get(int(frame_id))`, which re-reads the array slot and
consults nothing this class kept. That is exactly the distinction the source draws, so the substitution is
not a softening — it is the same read the injected `PyUIManager.UIFrame(fid)` wraps.

**Verification.** `tests/test_frame_tree_frame_offline.py` grew to **35 tests** (41 with the tables file),
seven of them new, over a four-frame fixture with a **code collision** (`1` has children `2` and `3`, both
code `6`) so the collision note in `rebuild` is exercised rather than described: `child_of` taking the first
of the pair and answering `None` for a code with no child; `children_at` keeping both siblings; `children_of`
flattened and sorted across codes; `child_codes_of`; the three single-value lookups with their zero defaults
and `known`; `all_ids` in array order; `children_map` grouped by parent; and `live` proving the raw-read
behaviour — an id the snapshot **never saw** answers `true` while one the engine does not have answers
`false`. The boundary test was updated to name members that are genuinely still absent (`state`, `_prune`,
`invalidate`, `descendants`, `frames_under`, `root`, `by_label`).

**Suite: 1313 tests OK** (was 1306); `pyright` 0 errors on `frame.py`. Next: the per-frame state cache
(`state`, `_prune`, `invalidate`) against the round-30 decision, then the remaining queries, then `Frame`.

## Now (round 30 - the per-frame state cache is tick-keyed in two more places, and both are decided)

**Reading `state`, `_prune` and `invalidate` (`frame.py:378-423`) found the same adaptation as `ensure`, in
two more places — so it is settled here rather than discovered halfway through writing them.**

1. **The per-tick memo** — ``if previous is not None and previous.tick == self.tick: return previous``
   (`:387-389`) pins the first copy of every frame for the life of the process when nothing advances `tick`.
   The port drops that test, for exactly the reason it drops `ensure`'s: **the member reads when it is
   called**.
2. **The buffer's bound is *not* dropped** — a blank read inherits the last good copy while
   ``previous.served < self.BUFFER_TICKS``, bumping `served` and stamping `previous.tick` (`:392-401`). The
   source's own comment says what it counts: "Counted in polls, not time". Polls still exist here, so that
   logic keeps its meaning untouched.
3. **The age-based prune genuinely cannot work** — ``cutoff = self.tick - 240`` (`:410`) never advances
   without a ticker, so `_prune` cannot fire and the `len(self._state) > 4096` guard at `:404-405` would
   call it in vain. This one is recorded as a limitation, and the member is ported as written rather than
   handed an invented clock.

**And the section that *is* clean is now named.** `child_of`, `children_at`, `children_of`,
`child_codes_of`, `parent_of`, `hash_of`, `code_of`, `known`, `all_ids`, `all_frames`, `children_map`,
`descendants`, `descendants_of`, `viewport_height`, `frames_at_path`, `frames_under`, `_frames_at` and
`sort_by_vertical` (`:462-570`, `:598-636`) read the snapshot dicts `rebuild` fills, and touch **neither the
tick nor the injected runtime** — so they are the next section, and three of them (`all_frames`,
`children_map`, `frames_under`) are calls the salvage-choice dialog makes.

**No code changed this round**; the deliverable is the decision and the boundary, in
[`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) §2. Suite unchanged at **1306 tests OK**, `pyright` clean.

## Now (round 29 - `_FrameTree` lives: its lifecycle and snapshot are ported, and `rebuild` reads this port's frame array)

**What moved.** `frame.py` is now ported to **line 375 of 1620**: after `FrameState` and the reverse lookups,
`_FrameTree`'s own spine — `__init__` (`:288-303`), `enable` (`:306-314`), `disable` (`:316-322`), `_on_tick`
(`:324-326`), `rebuild` (`:329-370`) and `ensure` (`:372-375`) — and the `FrameTree = _FrameTree()`
singleton (`:675`). The class's two constants are the source's own: `_CALLBACK = "FrameTree.Tick"` and
`BUFFER_TICKS = 5` (`:282-286`). I had invented a value for the first before reading the class head and
corrected it — the source's spelling is `Tick`, not `tick`.

**The one call in the section is resolved, not guessed.** The source walks
`PyUIManager.UIManager.get_frame_array()` and constructs a `PyUIManager.UIFrame` per id to read `parent_id`,
`child_offset_id` and `frame_hash` (`:337-346`). The port walks the same array through
`client.frame_array.iter_frames()`, which yields a frame id **with** its record — one pass, the record's own
fields, nothing constructed — so `rebuild` is the source's body with that single read answered.

**The two adaptations recorded last round are now in the code, and both are narrow.** `enable` and `disable`
— whose whole job is to make and drop the `PyCallback` registration that *is* the tick — raise and name it,
the same class of thing as `Agent.enable`. `ensure` rebuilds on the call, since with no ticker the source's
`_built_tick != self.tick` test would be false after the first rebuild and the tree would be pinned for the
life of the process. **`rebuild`'s own staleness rule is untouched** (`:356-369`): an empty array keeps the
last good tree and sets `stale`, because an array the engine cannot see is not an empty UI — and the test
drives exactly that, plus the collide-on-code case the source comments on (`:350-352`).

**Verification.** `tests/test_frame_tree_frame_offline.py` grew to **28 tests**, eight of them new: the
initial fields and the two class constants; a three-frame snapshot (order, parents, codes, hashes, the
sibling collision, `by_hash`, version bump); an empty array keeping the last good tree without bumping the
version; an empty *first* rebuild being taken rather than stale; `ensure` rebuilding twice in a row (which is
the adaptation made observable); `enable`/`disable` naming `PyCallback`; `_on_tick` bumping only the counter;
and the singleton's type. The section-boundary tests in both frame-tree files were updated rather than
"fixed" — they asserted `_FrameTree` was absent, which was true one round ago.

**Suite: 1306 tests OK** (was 1297); `pyright` 0 errors. Next: `_FrameTree`'s 35 remaining members — the
queries (`state`, `_prune`, `invalidate`, `child_of`, `children_at`, `children_of`, `children_map`,
`all_ids`, `all_frames`, `descendants`, `frames_at_path`, `frames_under`, `_frames_at`, `sort_by_vertical`,
`color_frames`, …) and the twelve other injected ones, one call site at a time — then `Frame`.

## Now (round 28 - `_FrameTree` is tick-keyed, and the port's answer is recorded before the members are written)

**Reading `rebuild` and `ensure` settled the thing that governs all 41 members of `_FrameTree`, so it is
written down first.** The source's tree is a **tick-keyed snapshot**: `__init__` holds `version`, `tick`,
`_built_tick`, the six structure dicts and `_state` (`frame.py:288-303`); `_on_tick` bumps `tick` and does
nothing else (`:324-326`); `rebuild` snapshots the whole frame array and stamps `self._built_tick =
self.tick` (`:362`); and `ensure` is `self.enable(); if self._built_tick != self.tick: self.rebuild()`
(`:372-375`) — rebuild once per tick, serve the snapshot in between. The tick comes from `enable`, which
registers `self._on_tick` with the injected `PyCallback` at `Phase.PreUpdate, priority=6` (`:306-322`).

**This port has no tick, so `ensure` as written would pin the tree for the life of the process**: with
nothing bumping `tick`, `_built_tick != self.tick` is false after the first rebuild, and every later call
would answer that first snapshot — a dereferenced-pointer cache that never clears, which `AGENTS.md` §
Caching forbids. The resolution is the one already settled for `@frame_cache`: **the member reads when it is
called** (so the port's `ensure` rebuilds on the call), `enable`/`disable` raise naming the missing
registration — they are the frame-loop halves, the same class as `Agent.enable` and
`Agent._invalidate_property_cache` — and `_on_tick` is ported as written even though nothing calls it.

**`rebuild`'s own staleness rule is *not* touched by that adaptation, and this is the part worth being
careful about.** Lines `356-369` say an empty frame array is "we cannot see the UI this tick", not "the UI is
gone": the last good tree is kept and `stale` is set, which is why overlays do not flicker. That is the
source's own check on its own terms, and it stays exactly as written.

**The section's one call is resolved, not guessed.** `rebuild` needs
`PyUIManager.UIManager.get_frame_array()` plus `PyUIManager.UIFrame(fid)` per id for `parent_id`,
`child_offset_id` and `frame_hash` (`:337-346`). Both are reads this port already has: `client.frame_array`
walks the same array and its `iter_frames()` yields a frame id together with its record, so the port's loop
reads the record's own fields in one pass and adds nothing.

**No code changed this round** — the deliverable is the decision and its bounds, in
[`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) §2. Suite unchanged at **1297 tests OK**, `pyright` clean. Next:
`__init__`, `rebuild`, `ensure`, `invalidate` and `_prune` written against that decision, then the twenty-eight
bookkeeping members behind them.

## Now (round 27 - `_FrameTree` mapped: 28 of the 41 members need nothing injected)

**This round measured the next section instead of starting it blind, and the measurement changes its shape.**
`_FrameTree` (273-672) has **41 members**, and an AST pass that records which injected calls each body
contains says: **28 have none at all** — `__init__`, `enable`, `disable`, `_on_tick`, `ensure`, `state`,
`_prune`, `invalidate`, `child_of`, `children_at`, `children_of`, `child_codes_of`, `parent_of`, `hash_of`,
`code_of`, `known`, `all_ids`, `all_frames`, `children_map`, `_as_id`, `descendants`, `descendants_of`,
`viewport_height`, `frames_at_path`, `frames_under`, `_frames_at`, `sort_by_vertical`, `color_frames` — and
**13 reach the injected runtime**: `rebuild` (which fills the tree from `UIManager`/`UIFrame`),
`anchor_ids`, `live`, `root`, `hierarchy`, `overlay_frames`, `popup_frames`, `by_hash`, `by_label`,
`hash_for_label`, `coords_for_hash`, `child_by_parent_hash` (all `UIManager`) and the `overlay` property
(`PyOverlay.Overlay`).

**Why that matters for the order of work.** The twenty-eight are pure bookkeeping over the structures
`rebuild` fills, so they cannot be *driven* before `rebuild` exists — but they also need no new capability,
while the thirteen are the call sites that decide how much of this class is portable at all. The full table
(with line ranges and per-member injected calls) is in [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) §2, so the
next round starts from the map rather than re-reading 400 lines to rebuild it.

**No code changed this round**; the deliverable is the member map and the order of work it implies — first
`rebuild` and the twelve other injected members (each resolved as a native `ui::*` call, one at a time), with
the twenty-eight following. Suite unchanged at **1297 tests OK**, `pyright` clean.

## Now (round 26 - `frame.py` starts: its first section is in, down to `FrameState`)

**What moved.** The `FrameTree` package's logic module is 1620 lines, shaped as: three exception classes,
`resolve_key`, the two reverse-identity lookups, `_position_unusable`, `FrameState` (202-269), `_FrameTree`
(**41 members**, 273-672), the `FrameTree` singleton, and `Frame` (**115 members**, 679-1620). This round
ported the section up to `FrameState` — **lines 44-269** — verbatim: the constants
(`_MOUSE_HOVER_STATE`, the four `RELATION_*` values), `FrameError`/`FrameKeyError`/`FrameNotFound`,
`resolve_key` (the registry walk, both of its `FrameKeyError` paths), `_path_of`/`alias_by_path`/
`key_by_path` (the two inversions, built once and kept) and `_position_unusable`, plus `FrameState` with its
`landed`, `blank` and `position` members — including the inheritance rule that hands back the last good
geometry instead of zeros.

**The section is dependency-free except for one read, and the source's own docstring points at it.**
`FrameState.__init__` is, in the source's words, "the *only* place a ``PyUIManager.UIFrame`` comes into
existence" (`frame.py:205-207`). The port answers that with the read the binding wraps — native's frame
record by id — which here is ``client.frame_array.get(frame_id)``, whose own docstring in
``py4gw/ui/frame.py`` already says it matches the native ``GetFrameById``. The source's try/except around
it, and the defaults it leaves behind, are kept as written.

**What is left, and it is the two sections built on the injected runtime:** ``PyUIManager.UIManager`` is
reached **52 times** across `_FrameTree` and `Frame`, ``PyUIManager.UIFrame`` five times and
``PyOverlay.Vec2f`` eight. Each of those 52 call sites is a native ``ui::*`` function, so each gets resolved
member by member the way ``PySkill`` was in ``model_enums`` — established when the member is ported, never
guessed as a group. That is recorded in [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) §2, which now carries the
module's section map with what is ported and what is not.

**Verification.** `tests/test_frame_tree_frame_offline.py` (19 tests): the exception hierarchy, the four
relation constants against their native values, `resolve_key` over the **ported** registry (an unknown
top-level key, a string entry, a nested key's child codes in order, and a missing child segment — the
second `FrameKeyError`), both inversions checked structurally (every alias path names a real alias, every
registry path resolves to a real key, and every path's first field is a hash `NAME_TO_HASH` knows), and
`FrameState` over a fixture frame: no read at all, a landed read, a zeroed position, the inheritance from a
previous good read, and that a landed read is *not* replaced. Three more tests state what is absent —
`_FrameTree`, `Frame`, and the injected imports — so the gap cannot be mistaken for done, and one asserts
`__all__` names only what this file defines so a star import cannot fail. One failure on the first run was
mine: a bogus patcher that tried to replace the module's `__dict__`.

**Suite: 1297 tests OK** (was 1278); `pyright` 0 errors. One test in the tables file needed updating rather
than fixing: it asserted that importing `py4gw.frame_tree.frame` **failed**, which was true last round and
is not now — it asserts the section boundary instead.

## Now (round 25 - the `FrameTree` cascade starts: its five table modules are ported, 5,010 lines)

**What moved.** The next feature is Reforged's `FrameTree` package — the dependency of the item port's last
17 members — and this round ported the half of it that is data. `py4gw/frame_tree/` now holds
`frame_window_keys` (20 lines), `frame_names` (538), `frame_aliases` (1216), `frame_registry` (1588) and
`frame_ids` (1648): **5,010 lines**, all verbatim transcriptions, because none of the five imports anything,
calls anything or computes anything beyond the two derived tables the source itself builds
(`NAME_TO_HASH` from `FRAME_NAMES`, and `FrameId`'s nested hierarchy). The port keeps the source's own
module file names, since inside a module every name is the source's and the package's modules are reached by
those names.

**What is *not* ported, and is not stubbed:** `frame.py` (1620 lines — the logic: `Frame`, `FrameTree`,
`FrameState`, `resolve_key`, the alias lookups) and the source's `__init__` (70 lines, which re-exports what
`frame.py` provides, so it follows it). The package's own `__init__` here says exactly that, and the test
asserts that importing `py4gw.frame_tree.frame` still fails, so the gap cannot be mistaken for done.

**A naming collision worth knowing about, since it exists either way.** The source keeps this package at its
library root (`Py4GWCoreLib/FrameTree/`), so the port mirrors it at `py4gw/frame_tree/`. The port *also* has
`py4gw/ui/frame_tree.py`, which is a different thing with a confusingly similar name: a **read-only
traversal** module (its docstring: nothing in it "creates, destroys, relabels, or dispatches a frame"), not
this action surface. Both are the sources' own; neither is renamed here.

**Verification.** `tests/test_frame_tree_tables_offline.py` (6 tests): the public names of all five modules
against the sources, every table entry for entry, dict key order included, `FrameId` **member for member and
recursively** — its nested classes are compared by shape, because the source's class and this port's are two
different objects — and a measured size floor per table (the source's `REGISTRY` holds 195 entries and
`FrameId` ~195 nested members, whatever their line counts suggest; my first floors were guesses and the test
caught them). Three failures on the first run were all mine: class identity across two modules, and those
guessed floors.

**Suite: 1278 tests OK** (was 1272); docs: new [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) with the module
table, the order of work and the open question about the native UI functions behind `Frame.click`. Next:
`frame.py` — its logic, its two injected imports (`PyOverlay`/`PyUIManager`, the same class of problem as
`PySkill` in `model_enums`), and then the 17 dialog members it unblocks.

## Now (round 24 - the dialog's cascade, measured: 17 are real work, 3 are the frame loop, 1 is the console)

**This round measured what the last 21 members of `Inventory` actually need, instead of assuming.** The
answer changes the plan for the item port, so it is worth stating exactly.

**A count of mine, corrected again, and this one is now measured rather than reasoned.** The class has 57
methods: **36 answer and 21 raise** (round 23 said 35/22 — the member I had missed is `_collect_frame_text`,
which the source itself answers `""` (`Inventory.py:503-513`) and which was ported as written). The tooling
for this is a script over `inspect.getsource`: built versus raising, by name.

**The 21 split three ways.**

1. **17 are gated on Reforged's `FrameTree` package, which is 5,444 lines** — `frame.py` 1620,
   `frame_ids.py` 1648, `frame_registry.py` 1588, `frame_aliases.py` 1216, `frame_names.py` 538,
   `__init__.py` 70. Note what my first look got wrong: `FrameTree` is a **package**, not a module (my glob
   for `FrameTree.py` reported "missing" and I nearly wrote that down as a source defect). The dialog uses
   `Frame.from_label`/`Frame.from_id`/`Frame(FrameId.X)`, `.exists`, `.is_created`, `.is_visible`,
   `.is_usable`, `.rect`, `.size`, `.click`, `.mouse_action`, `.mouse_click_action`, and `FrameTree`'s
   `all_frames()`, `children_map()`, `frames_under()`. **That package is the next feature**, and this port's
   frame layer is a reader (`py4gw/ui/frame.py`, `py4gw/ui/frame_tree.py`), not that action surface.
2. **3 are generators over Reforged's coroutine driver, and that is not work this port can do.** They are
   `HandleSalvageChoiceDialog`, `HandleSalvageChoiceMaterialConfirmDialog` and
   `_wait_for_salvage_choice_dialog_close`, and they `yield from` `Routines.Yield`, whose implementation
   (`Routines.py` → `routines_src/{Yield,Sequential,BehaviourTrees,…}` plus `GLOBAL_CACHE`) is that
   library's per-frame task framework — the driver *is* Reforged's update loop. This is the same class of
   thing as `@frame_cache` and `GLOBAL_CACHE`: a feature of the source's execution model, which this port
   deliberately does not have. It is a **documented divergence**, like `Agent.enable` and
   `Agent._invalidate_property_cache` (the two frame-loop halves), not pending work.
3. **1 needs the injected console.** `_salvage_choice_debug_log` logs through `ConsoleLog`/`Console`, and
   Reforged's `py4gwcorelib_src/Console.py` is 38 lines that *are* the in-client console — `Console =
   PySystem.Console`, with `PySystem.Console.get_gw_window_handle()` and `MessageType` coming from the
   injected runtime. There is nothing to port it *to* from outside the client, which is the same finding
   the rest of this port already carries: a library with no console reports through its return values and
   its exceptions.

**So the item port's portable work is now one package away from done.** `Item` is FULL, `ItemArray` is FULL,
`Inventory` is 36 of 57 with 17 of the remainder gated on `FrameTree`, `PyInventory` is 11 of 17 with its
remaining six gated on the same UI surface (the frame-click path), the map record's `region` field (the
interact guard) and a StoC path. **Next: port the `FrameTree` package**, starting with its table modules
(`frame_ids`, `frame_aliases`, `frame_names`, `frame_registry` — transcription with parity tests, as
`mods_upgrades` and `model_enums` were done), then `frame.py`'s logic and its actions, which is where the
native UI functions behind them get resolved.

**Suite: 1272 tests OK**; `pyright` clean. No code changed this round — the deliverable is the corrected
count and the measured cascade, in `CLASS_PORT_MAP.md` and here.

## Now (round 23 - both storage walkers are in: `Inventory` is 35 of 57, and only the dialog is left)

**What moved.** `DepositItemToStorage` and `WithdrawItemFromStorage` (`Inventory.py:1325-1471`) — the two
members round 21 left raising on the four-word call form, which round 22 built. They are the source's own
bodies: the item's stackability and quantity, the same two passes over the target bags (partial stacks of
the same model first when the item stacks, then empty slots), the same early `True` when what was asked for
has moved, and the same `moved_any` fall-through.

**Two details the port keeps, because the source has them.** `DepositItemToStorage` derives its bag list
from **capacity**, not from a fixed range — the storage bags' combined `GetSize()` divided by 25 is how many
exist — and reaches each one **by name**, ``getattr(Bags, f"Storage{i}")`` (`:1352-1354`). That is a dynamic
reach in the source, so it is a dynamic reach here: the rule against `getattr` dispatch is about this port
inventing one, and this one is the specification. Both members also open with ``from .enums import Bags``
(`:1335`, `:1420`), settled the same way as the rest of this file — the name comes from the module that
declares it — and in `WithdrawItemFromStorage` the source never uses the imported name, which is kept too.

**`Inventory` now stands at 35 of its 57 methods, and the 22 that raise are exactly the salvage-choice
dialog** — the ten helpers, the four frame lookups, the three coroutine handlers and the two visibility
members, each naming the same two missing pieces: Reforged's `FrameTree` action surface and, for the
generators, its `ActionQueueManager`/`Routines.Yield` driver.

**A count of mine, corrected.** Round 22 changed `py_inventory.MoveItem` (a binding member), not an
`Inventory` member — `Inventory.MoveItem` was already built in round 21 as the source's own delegation — so
the class went 33 → 35 across these two rounds, not 34 → 35. `CLASS_PORT_MAP.md` now says 35 with 22 raising.

**Verification.** `tests/test_inventory_offline.py` grew to **38 tests**, five of them for the walkers over a
fixture built to make the source's capacity rule fire (a 25-slot storage bag, so `total_capacity // 25` is 1
and `getattr(Bags, "Storage1")` names the bag the fixture has): the empty-slot deposit with its exact
four-word move call, the stackable path filling a partial stack first, the withdraw with its
`min(asked, held)` clamp, and both "nothing to move" guards answering `False` with no call made. The test
fake grew the call path (`resolves`, `call_function`, `calls`) because these members move items through
`py_inventory.MoveItem`, which is where the four-word form is used.

**Suite: 1272 tests OK** (was 1267); `pyright` clean. Next: the salvage-choice dialog — the last 22 members
of the class, and the two pieces they need are the largest remaining work in the item port.

## Now (round 22 - the four-word call form exists, and the member that needed it answers)

**What moved: the capability layer gained a call form, which is porting work and not a workaround.**
Native's `MoveItemFn` is `void __cdecl(uint32_t, uint32_t, uint32_t, uint32_t)`, and the item methods
layer calls it with exactly four words — ``g_move_item_func(from->item_id, quantity, bag->index, slot)``
(``item_methods.cpp:164``). This port had no four-word form, and the five-word one cannot stand in for it:
a fifth pushed word is an argument the callee does not take, and the release would then be a word too
long. So:

- ``CallForm.U32_U32_U32_U32 = 8`` (``shared_block.py``), documented with the declaration it answers and
  the reason the five-word form is not it;
- the dispatcher emits it (``payload.py``): the four words pushed right to left, the call, ``add esp, 16``,
  the completion state — the same shape as the three- and five-word blocks beside it, and it appears in the
  dispatch chain before the unknown-form fallthrough, so an unrecognised form is still refused rather than
  guessed at;
- **``py_inventory.MoveItem`` is built** — the binding's item lookup, the methods layer's bag lookup, its
  `bag->items.size() < slot` refusal, its quantity clamp (``<= 0`` means all of it, and more than it holds
  means all of it), then the four-word call. ``Inventory.MoveItem`` (the source's own one-line delegation)
  reaches it and answers too, so the raise it used to pass through is gone. ``py_inventory`` is down from
  7 raising members to **6** (the interact guard's four, the StoC path, the frame-click path).

**Verification, and it is the kind emitted code needs.** The payload suite already executes the dispatcher
against **witness targets** that record the stack pointer and the words they were entered with, and the new
form is covered the same way: it gets its own four-word witness and descriptor, a test that the words
arrive in the source's order, a test that a fifth command word is **not** an argument, a test that the stack
is left exactly where the form found it (sixteen bytes released, not twenty), a completion test, and its own
line in the measurement that distinguishes "pushed the right number" from "pushed the right values"
(``entry_esp() == empty - 16``). ``MoveItem`` itself is tested over the fixture: the resolver name, the
four-word form and every argument, both clamp paths, the slot bound, and the missing-item and missing-bag
refusals.

**Suite: 1267 tests OK** (was 1259); `pyright` 0 errors on the payload, the block, `py_inventory` and
`inventory`. ``AGENTS.md`` had said the vocabulary covers *seven* forms; it says **eight** now, which is
what the code has.

Next: `DepositItemToStorage` and `WithdrawItemFromStorage` (`Inventory.py:1325-1471`), which name the
four-word form today and no longer need to.

## Now (round 21 - `Inventory`'s action half is in: 33 of 57 methods answer)

**What moved.** The fourteen bodies round 20's raises named (`Inventory.py:1162-1323`) are read and
written, and one more went with them: **15 members** now answer, taking `Inventory` from 18 to **33 of its
57 methods**:

- the **storage window** — `OpenXunlaiWindow` (which builds *two* binding instances, the source's own
  body: one to open, one to read whether it opened) and `IsStorageOpen`;
- the **six item actions** — `PickUpItem`, `DropItem` (the one action that returns its call),
  `EquipItem`, `UseItem`, `DestroyItem`, `GetHoveredItemID`;
- the **five gold members** — `GetGoldOnCharacter` (which delegates to `GetGoldAmount`, as the source's
  body does), `GetGoldInStorage`, `DepositGold`, `WithdrawGold`, `DropGold`;
- **`MoveItem`** and **`FindItemBagAndSlot`** (the second re-queries each bag on its own and answers
  `(bag_id, Item.GetSlot(item))`, or `(None, None)`).

**Three of those are delegations whose raise belongs to the callee, not a refusal here.** `EquipItem`,
`UseItem` and `MoveItem` are the source's own one-line bodies pointing at binding members the bag surface
still owes (the interact guard, the four-word call form); the members themselves are ported, and the
raise comes from where the source's own call graph puts it. The two storage walkers
(`DepositItemToStorage`, `WithdrawItemFromStorage`) still raise and name the four-word call form, which
is what actually blocks them.

**Twenty-four methods raise, and every one names its work item**: the 22 salvage-choice dialog members
(Reforged's `FrameTree` action surface, plus the coroutine driver for the three generators) and those two
storage walkers.

**Verification.** `tests/test_inventory_offline.py` grew to **33 tests**: the fifteen new members are
driven over the same real-record fixture — the storage flag and the two gold reads answer the record's
fields, the delegating members are checked by patching the binding's methods and asserting the arguments
that arrive (`PickUpItem`'s `call_target`, `DropItem`'s return, the three gold calls) — and the three
that pass a raise through are asserted to name the *callee's* requirement, so a pass-through cannot be
mistaken for a refusal. The 24 raising members keep their one-call-per-member check.

**Suite: 1259 tests OK** (was 1250); `pyright` 0 errors on `inventory.py` and its test. Next: the two
storage walkers (`Inventory.py:1325-1471`) once the four-word call form exists, then the salvage-choice
dialog, which needs the frame-action and coroutine pieces before porting it is worth anything.

## Now (round 20 - `Inventory` starts, and its whole surface is declared)

**What moved.** `py4gw/inventory.py` — Reforged's `Inventory.py` (1477 lines, **66 declarations**),
written in the source's own order and grouping: the three `TypedDict`s (`VisibleFrameEntry` 10 fields,
`SalvageChoiceEntry` 7 optional, `SalvageChoiceOptionSource` 5), the **9 class attributes** (the salvage
dialog's four labels and five fallback offsets), and all **57 static methods declared**.

**Eighteen of those 57 answer**, and they are the read/count half: `inventory_instance`, the nine
space-and-count members (`GetInventorySpace`, `GetStorageSpace`, `GetZeroFilledStorageArray`,
`GetFreeSlotCount`, `GetItemCount`, `GetModelCount`, `GetModelCountInStorage`,
`GetModelCountInMaterialStorage`, `GetModelCountInEquipped`), the four "first" finders (`GetFirstIDKit`,
`GetFirstUnidentifiedItem`, `GetFirstSalvageKit`, `GetFirstSalvageableItem`) and identify/salvage
(`IdentifyItem`, `IdentifyFirst`, `SalvageItem`, `SalvageFirst`). They are the source's own bodies over
the ported `ItemArray`, `Item` and bag surface, so the item ids, the selections and the per-item answers
all come through the same path a live client would take.

**The other 39 raise, and each names its work item — not a vague one.** Twenty-two are the
salvage-choice dialog (`Inventory.py:392-1160`): they need **Reforged's `FrameTree` action surface**
(`Frame.from_label`, `FrameId.*`, `Frame.exists`, `Frame.click`, `Frame.mouse_action`), which this port's
frame layer does not carry — it reads frames (`py4gw/ui/frame.py`, `py4gw/ui/frame_tree.py`) and has no
click path — and the three generator members (`HandleSalvageChoiceMaterialConfirmDialog`,
`_wait_for_salvage_choice_dialog_close`, `HandleSalvageChoiceDialog`) additionally need Reforged's
coroutine driver (`ActionQueueManager`, `Routines.Yield`), which this port's execution model has no
dispatcher for. `MoveItem`, `DepositItemToStorage` and `WithdrawItemFromStorage` name the **four-word call
form** `item.move_item_func` needs. The remaining fourteen name their own bodies and the exact line range
this port has not read and written yet.

**Three source facts, recorded rather than smoothed over.**

1. **`.enums` is a shim, and a half-unportable one.** `Inventory.py:76` and `:110` do
   `from .enums import Bags`; the source's `enums.py` is a 289-line re-export over `enums_src` **and** over
   `Texture_enums`/`Calendar_enums`, neither of which this port has. So `Bags` is taken from the module
   that declares it (`enums_src/item_enums.py:43`) — the same class, from the same file — and the shim is
   not ported until its other half exists.
2. **`SalvageFirst` answers `False` on the path where it acted** (`Inventory.py:386-388`): it starts the
   salvage, logs it, then falls through to `return False`, and its two guard paths also answer `False`.
   Kept as written.
3. **`_collect_frame_text` does nothing** (`Inventory.py:503-513`): its body discards its parameters and
   returns `""`, by the source's own design (its docstring says decoding a non-text-label frame can
   dereference an invalid native type). Ported as written — it answers `""` — rather than raised, because
   the source itself does nothing.

**Verification.** `tests/test_inventory_offline.py`, 24 tests: the AST surface comparison (**66 members on
both sides**, the 57 methods all `@staticmethod` as in the source, and the port's module-level additions
named one by one), the three `TypedDict`s' fields, the nine attribute values, the behaviour of all
eighteen built members over a real-record bag fixture, `_collect_frame_text`'s empty answer, and — for
**every one of the 39 raising members** — a call that must raise and a distinctive phrase from its
requirement, so a raise can never quietly become a wrong answer.

**Suite: 1250 tests OK** (was 1226); `pyright` 0 errors on `inventory.py` and its test. Next: read and
write the fourteen bodies the raises name (`Inventory.py:1162-1471`), then the salvage-choice dialog,
which needs the frame-action and coroutine pieces to be worth porting at all.

## Now (round 19 - `ItemArray` is FULL, and both of its quirks are pinned instead of tidied)

**What moved.** `py4gw/item_array.py` — Reforged's `ItemArray.py` (212 lines, 14 declarations):
`CreateBagList` (ints to `Bag` members), `GetItemArray` (the ids across those bags), `GetAllBags` (the
bags that hold anything) and `GetBag`, plus the three nested namespaces `Filter` (2), `Manipulation` (3)
and `Sort` (2). It reads through the bag surface round 18 supplied, so `GetItemArray` answers the ids of
`PyItem` objects. **Every one of the 14 members answers: `ItemArray` is FULL**, joining `Item`,
`AgentArray` and `Camera`.

**Two adaptations, both recorded in the module and asserted by tests.**

- **`@frame_cache` is dropped on exactly the three members that carry it** — no frame loop means no frame
  boundary to key a memo to, so each reads when it is called (and the test proves a second call reaches
  the client again, which is the observable difference).
- **The two `PySystem.Console.Log` calls have nowhere to go.** The source logs an invalid bag id and
  drops it, and logs a bag whose read raised and skips it. The port keeps the **control flow exactly** and
  replaces the log with nothing: *a library with no console reports through its return values and its
  exceptions* (`dialog.py`'s own wording for the same situation). An invented logger would be a member the
  sources do not have.

**Two source quirks, found while writing the tests and pinned rather than tidied.**

1. **`GetBag` cannot answer a bag at all.** An `int` (which its annotation names) makes the first line —
   `GetItemArray([bag])` — come back empty, because that member reads `bag_enum.value` off its argument and
   an `int` has none; a `Bag` member (which its docstring names) passes that line but makes
   `PyInventory.Bag(bag, str(bag))` raise, because `Bag` is a plain `Enum` and the binding's `int`
   conversion refuses it. Both land in the source's own `except Exception: return None`.
2. **The dotted attribute names the source's own docstrings use are not attributes.** `Filter.ByAttribute`
   and `Sort.SortByAttribute` do `hasattr(Item, attribute)` with names like `'Properties.GetValue'`, and
   `getattr` does not walk the dot — so the filter excludes every item and the sort raises the source's own
   `ValueError: Invalid attribute: Properties.GetValue`. A test asserts both, and the mechanism tests use a
   flat member name (`GetModelID`), which is what actually works.

**One defect of mine, caught before it shipped:** the first draft added a `_Condition` type alias and
parameter annotations the source does not have. That is exactly the kind of addition the porting rules
forbid, the surface test caught it as an extra name, and it is gone — the signatures are the source's own,
unannotated ones.

**Verification.** `tests/test_item_array_offline.py`, 25 tests: the AST surface comparison (classes,
nesting, member names, and the decorator difference asserted to be *only* the three `frame_cache` drops),
the bag-id list, the skip and drop paths, `GetAllBags`, both `GetBag` quirk paths, `Filter`/`Sort` by name
with the dotted-name quirk pinned, `Manipulation`'s three set operations, and the no-memo behaviour.

**Suite: 1226 tests OK** (was 1201); `pyright` 0 errors on `item_array.py` and its test. Next:
`inventory.py` (66 members) — the last of the three classes, and where the salvage-choice dialog question
and `py_inventory`'s seven raising members land.

## Now (round 18 - the bag surface is ported, and `Item` has no member left that raises)

**What moved.** `py4gw/py_inventory.py` — Native's `PyInventory` module (`inventory_bindings.cpp`, 216
lines) — which is where all three item classes get their bags from. It is a module of its own because in
both sources it *is* one (`inventory_bindings.cpp:157` embeds it; Reforged's Python imports it), and
because `Inventory.py` imports `ItemArray`, so hosting the binding in either of them would make the
import a cycle.

- **`Bag` is complete**: the seven fields, `GetContext`, `GetSize`, `GetItemCount` (the copied field, not
  a fresh read) and `GetItems`.
- **The shape decision, and it comes from Reforged**: native's `GetItems` builds `dict`s, while
  Reforged's Python reads **attributes** off each element (`item.item_id` at `ItemArray.py:49` and
  `Item.py:245,265`; `item.slot` at `Inventory.py:1396`) and its stub declares `List[PyItem]`. So this
  port's `GetItems` answers `PyItem` objects — every field native's dict carries, and the rest of the
  record. Native's dict shape is kept where the source keeps it: the module's `get_bag` snapshot.
- **`PyInventory`**: 10 of 17 members answer — the three reads, `GetHoveredItemID` (the port of
  `GW::item::GetHoveredItem`, whose payload is a `uint32_t*`, so `payload[1]`/`payload[2]` are *words*:
  `{item_id, 0xff}` or `{item_id, item_id, 0xff}`), `PickUpItem` (the `kSendInteractItem` message with
  the `kInteractAgent` packet), `DropItem`, `DestroyItem`, and the gold three with the methods layer's own
  limits, clamps and `ChangeGold` verification.
- **`Item` is FULL.** Its last two members, `GetItemIdFromModelID` and `GetItemByAgentID`, walk four bags
  through this module and answer, so the class has **no raising member left** and joins `AgentArray` and
  `Camera` in the FULL column.

**The seven members that raise name four pieces, and two of them are this port's own work items**: a
**four-word call form** for `item.move_item_func` (native passes item id, quantity, bag index and slot;
the call vocabulary stops at three words, while `call_function` already accepts five — so what is missing
is the dispatcher form), the **current map record's `region` field** (the interact guard
`CanInteractWithItem` → `CanAccessXunlaiChest`, `item_methods.cpp:57-62`, which gates `UseItem`,
`EquipItem`, `IdentifyItem`, `Salvage` and the module's `salvage`), a **StoC path** (`OpenXunlaiWindow`
emulates a `DataWindow` packet) and a **frame-click path** (`AcceptSalvageWindow`).

**Verification.** `tests/test_py_inventory_offline.py` (32 tests) drives `Bag` over **real** ported
records — `BagStruct` and two `ItemStruct`s built from bytes behind a reader, the same construction the
item-record tests use — and records the actions through a fake client: the resolver name, the call form
and every argument, plus `PickUpItem`'s message, the gold limits on both sides of each boundary, the
tooltip payload cases, `get_bag`'s dict shape, and each raising member's own named requirement. Four
failures along the way were mine: two missing `require_client` patches (each module reaches the client
through its own import), a `cast` import, and one test whose calls sat outside the `with` block that
closed the map gate.

**A real defect, caught by the type check and not by the tests.** ``ItemContext`` (the client's reader)
owns ``storage_open_address``/``is_storage_open``/``get_composite_model_ids``/``read`` — while
``GetItemById`` and ``read_inventory`` belong to the **record** that ``read()`` hands out
(``ItemContextStruct``). Three files called them flat (``item.py`` twice, ``py_inventory.py``, and the
generated ``mods_core.py``), which no live run had reached yet and which **every fake client in the
tests agreed with**, because the fakes had the same flat shape — so the tests passed while production
code would have raised ``AttributeError`` on the first real read. ``pyright`` on the whole item port
found it (2 errors in ``item.py``), and the fix was three call sites plus **four test fakes reshaped to
mirror the real reader**. ``mods_core.py`` is generated, so its generator (``live_reports/port_mods_core.py``)
was corrected and the file regenerated rather than hand-patched. The item port is now ``pyright`` clean:
**0 errors** on `item.py`, `py_inventory.py`, `mods_core.py`, `mods_types.py`, `mods_upgrades.py`,
`enums_src/item_enums.py` and `enums_src/model_enums.py`.

**Suite: 1201 tests OK** (was 1169). Next: `item_array.py` (14 members — it needs exactly this bag
surface), then `inventory.py` (66), which is also where the salvage-choice dialog question lands.

## Now (round 17 - `Item` is ported, and so is the binding it reads through)

**What moved.** `py4gw/item.py` — Reforged's `Item.py` (827 lines, 125 declarations): the `Bag` enum
(24), the `Item` class (23 direct: 17 static methods and the six nested namespaces — `Mods` 22,
`Rarity` 6, `Properties` 21, `Type` 8, `Usage` 10, `Dye` 4), the three constants and the four module
functions. Behind it, the three steps it needed first are already in: `mods_types.py` (80 identifiers,
283 upgrades), `mods_upgrades.py` (704 catalog entries) and `mods_core.py` (the decoder), plus
`enums_src/item_enums.py` and `enums_src/model_enums.py`.

**The binding is part of the port.** Every `Item` member reads through `PyItem.PyItem(item_id)` —
Native's binding class (`item_bindings.cpp:210-380`, bound at `:427-486`) — so this module carries it as
`PyItem`: 48 fields, `GetContext` copying them from the ported item record with the record's own methods
deciding the 30 derived flags, the four encoded-string accessors, `IsItemValid`,
`GetCompositeModelIDs` and the name trio. Native's map gate (`GetIsMapLoaded() && !GetIsObserving() &&
instance != Loading`) is the ported `Map.IsMapReady()`, which is how `dialog.py` and `skillbar.py`
already express that same condition. The item name is the one mechanism that differs and it is written
down on the member: native spawns a thread that enqueues `AsyncGetItemName` and polls it for a second;
this port drives the same client decoder directly (`py4gw/ui/async_decode.py`, the route
`Agent.GetNameByID` uses) and keeps native's three outcomes — not ready, the name, `"No Item"` — with
native's own one-second `"Timeout"` kept as a wall-clock check.

**Verification.** `tests/test_item_offline.py` (29 tests) does two things: it compares the module
against the **source's own AST** — every class, member, nesting and decorator, nothing missing, and the
port's only additions are the seven names of the binding, asserted name by name — and it drives the
reads over a fixture built from the **real** ported item record (`ItemStruct` from bytes, with a real
modifier array behind it, bound to the same trade stand-in the item-record tests use), so the field
copies, all 30 derived flags, the modifier readers, the requirement/damage readers, the dye namespace
and `GetDyeColor` are exercised against real record logic.

**Two members raise, and both name the next step.** `GetItemIdFromModelID` and `GetItemByAgentID` walk
four bags through native's `PyInventory.Bag.GetItems()`; the two sources disagree about what that
returns (native's binding: `dict`s; Reforged's `Item` and its stub: item objects), so which shape this
port reproduces is the Inventory step's decision. `Item` therefore stands at **INCOMPLETE, 2 members**,
which is what `CLASS_PORT_MAP.md` now says.

**Two findings, recorded where they were found.** The test caught a count I had written into the docs —
`Item` has 17 static methods and six nested namespaces, not 18 and five — and it pinned a source quirk:
`Item.Mods.ModifierExists`/`GetModifierValues` compare the binding's `GetIdentifier()` (`mod >> 16`) with
the caller's identifier while the decoder reads `(mod >> 16) >> 4`, so those two members match only the
binding's spelling (`0x27A0`), never `ModId.Damage` (`0x27A`). Both are the source's own behaviour, kept
as it is.

**Suite: 1169 tests OK** (was 1140), including the 29 new ones. Next: `ItemArray` (14 members), then
`Inventory` (66), which is also where the two raising members and the salvage-dialog question land.

## Now (round 15 - the item port starts: three classes, 202 members, and the order they have to be built in)

**The next port is `Inventory` + `Item` + `ItemArray`, and this round pinned it exactly.** Every member
of all three source files was read and counted, member by member, in file order, with its line range
and every external name its body calls: `Item.py` (827 lines) is **122 members**, `ItemArray.py`
(212 lines) is **14**, `Inventory.py` (1477 lines) is **66** — **202 in total**, and the whole surface
with its grouping is in [`ITEM_PORT.md`](ITEM_PORT.md).

**What the reconnaissance settled, and it is the part that usually goes wrong:**

- **The cascade is four files, not three classes.** `Item.py` needs `enums_src/Item_enums.py`
  (`ItemType`, `DAMAGE_RANGES`, `Bags` — 449 lines), `mods_types.py` (`ModifierIdentifier`, 1230
  lines) and `mods_core.py` (494 lines: the 13 functions `Item.Mods`' 21 members and four
  `Item.Properties` readers are built on). None of the three classes can be ported without them, so
  they come first, in that order.
- **The native bindings are work, not a stand-in.** `PyItem.PyItem` and `PyInventory.PyInventory` /
  `PyInventory.Bag` are what the three classes call, and native's inventory methods are the ones that
  **act** (identify, salvage, move, equip, use, destroy, gold, storage); they are ported the way
  `PyEffects` was — the class in the ported module, over `item_methods.cpp` and the item context this
  port already reads.
- **The one open question, named before the code rather than after it**: 22 of `Inventory`'s members
  (392-1160) are the salvage-choice dialog, and three of them
  (`HandleSalvageChoiceMaterialConfirmDialog`, `_wait_for_salvage_choice_dialog_close`,
  `HandleSalvageChoiceDialog`) are **generators over Reforged's `Routines.Yield` coroutine protocol**
  with `ActionQueueManager` queues. This port has neither, and the answer is not to invent a
  scheduler. That is written down in `ITEM_PORT.md` §3 as the port's one design question, to be
  answered with the source in hand when those members are written.
- **Two source facts recorded, not smoothed over**: `Item.py` imports `Rarity` (line 9) and no member
  uses it (the five rarity readers resolve the nested `Item.Rarity`), and the three `ItemArray`
  members that carry Reforged's `@frame_cache` (`GetItemArray`, `GetAllBags`, `GetBag`) drop it and
  read when called — the port's settled rule for a decorator whose only invalidator is a frame loop
  this port does not have.
- **What is already here**: `py4gw/context/item_context.py` reads the client's item context (the
  `Item` 0x54, `Bag` 0x28, `Inventory` 0x98, `ItemModifier` 0x04 and `ItemContext` 0x10C records,
  the bag/item walks, the modifier array, native's `item::GetItemById`), and `py4gw/ui/frame_tree.py`
  + `py4gw/ui/frame.py` are ported — so the dialog's frame lookups have a home.

**No port code is written yet, and the doc says so in its first line.** The order is: `item_enums` →
`mods_types` → `mods_core` → `item.py` → `item_array.py` → `inventory.py`, each step finished with
its own offline tests, then the live probe (`tests/probe_items_live.py`) over the character's real
bags. 1099 offline tests still OK; nothing in this round touched the existing code.

## Now (round 14 - `Effects`' alcohol hook: it is in the client, and one event shape is left)

**What moved.** ``Effects`` has been 13 of 15 members for two rounds because ``GetAlcoholLevel`` is
not a read: native's number is the ``intensity`` argument of the client's own post-process effect
call, stored by an entry hook (``effects.cpp:15,26-41``) and returned by the binding
(``effects_bindings.cpp:37-39``). That hook is now installed. What it took, all of it our own
capability layer and none of it invented behaviour:

- ``Bridge.install`` takes a **second observed function**, in native's shape — one hook per function,
  each with its own watch list (``effects.cpp:51-55``) — with its own hook name, watch list,
  observer stub and teardown, and the install rollback removes hooks before it frees anything (the
  rule that crash taught).
- ``build_observer`` takes the **event kind** it publishes, and ``EventKind.EFFECT_INTENSITY`` (= 4)
  is that kind, so no other module's handler sees these events.
- The connection resolves ``effects.post_process_effect_func`` read-only first, checks the entry
  against its own bytes, and patches it with the displaced bytes pinned to whole instructions
  (``55 8B EC 83 EC 08`` — ``push ebp; mov ebp, esp; sub esp, 8``; the next instruction is where the
  arguments are read).
- ``py4gw/effect.py`` holds native's state and handler: ``_alcohol_level`` (``effects.cpp:15``),
  ``_on_post_process_effect`` (``effects.cpp:26-41``), ``_reset_alcohol_state`` (``effects.cpp:81``,
  called on close). Native's ``intensity <= 5`` test is the watch list (``_WATCHED_INTENSITIES``).

**The live run** (`tests/probe_alcohol_live.py`, pid 35416, exit clean, three hooks in and every
entry restored on disconnect): the level read ``0``, ``Effects.ApplyDrunkEffect(3, 0)`` ran, the level
stayed ``0``. **The reason is in the emitted observer** and it is now written down precisely: it takes
the hooked function's first argument as the id to match and its **second as a pointer to a packet**,
and drops the event when that pointer is null (``payload.py:762-765``) — the UI path's own check. The
post-process function's two arguments are plain words and its second is ``0`` for a plain drunk level,
so nothing is ever published. **One stub is the whole remainder**: an observer that carries the
hooked call's own word arguments instead of dereferencing one (``docs/TARGET_SIDE_WORK.md``,
2026-09-27). Until it exists the member raises naming it — it does not answer a number nothing stored.

**Verdicts are unchanged** by this round: ``Effects`` is still 13 of 15 (the two alcohol members), and
``Agent`` (COMPLETE for this port's purposes), ``AgentArray`` and ``Camera`` (both FULL) are untouched.
1099 offline tests OK.

## Now (round 12 - the client decodes the name, and it is 15x cheaper)

- **The owner's instruction:** *"i thought you were already using the AsyncGetAgentName path, okay we need
  to do that"* -- and it is done, for the reason the measurements had been pointing at: Reforged's table
  is free only because Reforged runs *inside* the client.
- **The change, and the divergence it carries.** ``Agent.GetNameByID`` keeps Reforged's name and
  two-call shape, but the *decode* is Native's: the encoded string is handed to the client's own decoder
  (``py4gw/ui/async_decode.py``, the port of ``ui::AsyncDecodeStr``) and the text comes back from its
  completion. ``agent_methods.cpp:318-325`` is the source line; Reforged's ``string_table.decode``
  remains in the tree and is still what a caller uses when a table entry has to be rendered on the host
  (``load_string_table``), but **no member reads that table any more**.
- **Measured, same client, side by side** (``live_reports/name_scheme8.txt``, ``find_npc*.txt``):
  a name is **~115 ms** the first time and **0.09-0.5 ms** afterwards, against **~2.1 s** for the first
  name in a slot on the dat route (one record opened ~1.1 s, 91 KB read and decompressed ~0.9 s). The
  texts agree on every agent sampled -- and the client even resolves ``Pet - My Pet`` where the table
  decode stops at ``Pet - %str1%``.
- **The whole run the owner timed** (find the closest "Master of Winds", target it, interact), process
  start to interact: **8974 ms -> 7955 ms -> 4018 ms**. The last step came from two fixes rather than
  from the name route itself: the connect-time dat warm-up is gone (it was competing with the decodes
  for the game thread, which is why target/interact fell from ~70 ms to ~32 ms), and the probe stopped
  burning a 3 s deadline polling for a target announcement that is a separate client notice.
- **What is left, stated plainly:** a *cold* map-wide sweep is still **~2.9 s**, because it is ~41
  first-time decodes at ~115 ms each (17 ms ring pickup + the client's own decode), serialised -- the
  client answers during the call. Two levers, both the owner's to pick: filter the candidates with the
  source's own arrays (``AgentArray.GetAllyArray``/``GetNPCMinipetArray``, a distance cut) so fewer names
  are asked for, or persist the string table so a sweep is the table's 0.1 ms per name.
- **Three real defects found on the way, all fixed and live-relevant:**
  1. **``dialog._on_string_decoded`` consumed decodes it did not own.** It called ``decoded_text(slot)``
     before checking its own three request queues, so any other module's decode (an agent's name!) was
     taken and its text discarded -- measured live, a name reached ``DONE`` and was then read as
     ``FREE`` with nothing cached. It now returns without taking, the rule ``chat._on_string_decoded``
     already followed.
  2. **A disconnect could fail and orphan the block** when names were left in flight: the bridge refuses
     to free a block with decodes outstanding. The name module now gives those slots back in
     ``ConnectedClient.close``, which is what lets the removal complete (``exit=0`` since).
  3. **The client answers only a few decodes at once.** A sweep that placed one per slot (32) answered
     **none** -- ``_name_requests`` now holds at most ``MAX_NAME_DECODES_IN_FLIGHT`` (8) and the rest
     answer ``""`` for the caller to ask again, which is the source's own two-call contract.
- **Also established this round, and it changes the dat picture:** the ring is *not* the cost. One
  command (PING) is **3.3 ms min / 16.6 ms median**, 60 hits/s; a dat record is ~1115 ms to open and
  close, and a whole ``read_file_by_hash`` ~2066 ms -- the client's own work. Batching commands (my
  earlier idea) would have saved ~50 ms per file, which is why it was dropped.
- **Evidence:** **1074 tests OK** (1.4 s), `pyright` on the touched files `0 errors`; the client was read
  back after each run and its two hook targets carry their own bytes; reports under ``live_reports/``
  (``find_npc11.txt``, ``name_member3.txt``, ``name_scheme8.txt``, ``perf_live.txt``).

## Now (round 11 - the dat handling pre-cached at connect, and nobody waits for it)

- **What was asked, in the owner's words:** *"the issue is not the reads, its the handling of the dats,
  what can we do, can we pre cache that on connect or map change so when the user gets a name doesnt
  have to pass trough the long warmup? could we fire a thread that does that on connect? would that
  make the connect take longer?"* — and then the requirement itself: *"if the dats were already
  previously dealt we shouldnt have those multiple secods but a 150 ms operation"*.
- **Both answers, and both are now in the tree.**
  1. **A thread does not make the connect longer.** The trigger in the `TextParser` refresh (which is
     what connect runs) now calls the source's own enqueue, `load_string_table(language_id)`
     (`text_parser_context.py:274-282`), and that returns immediately: the load runs on one daemon
     worker (`_start_warmup` -> `_warmup_worker`). The only connect-side work added is nothing at all —
     the language is already in hand at that point.
  2. **No caller ever reads a file again.** The table is parsed into `_string_table` **file by file as
     the worker reads them** (`_read_slot`), so a name whose entry has been read answers while the rest
     of the language is still loading; and a decode whose entry is *not* in it yet asks the worker for
     the one slot that entry lives in (`_request_slot`) and answers `""` — the source's own pending
     value — instead of reading it itself. A slot somebody is waiting for is read **next**
     (`_slot_order` checks for a request before every yield).
- **A map change needs nothing.** The table is the client's *language* table: same files, same entries,
  for the session. What a map change changes is which slots the names in play need, and those are read
  on demand (asked for, and served next). The per-language table is already kept across reconnects
  inside one controller process (`_string_tables_by_language`).
- **Two members the earlier rounds had invented for the on-demand path are gone** with it:
  `use_string_table_language` (the trigger's stand-in) and `_ensure_entry_loaded` (the inline read).
  What replaced them is the source's own call and one worker.
- **`disconnect` stops the worker before the block goes away** (`ConnectedClient.close`, right after the
  listener stops): the warm-up reads GW.dat through that connection, and a worker left running would
  also leave the record it was reading open in the client — the client's own `Gw.dat still open`
  assertion of round 10.
- **Evidence:** **1073 tests OK** (1.0 s; +2, the new `WarmupTests`), `pyright` on the five touched files
  `0 errors`. The two new tests pin exactly what was asked: `load_string_table` returns **while the
  worker is still inside its first read** (the connect does not wait), and a slot a decode asks for is
  read before the ones nobody wants (`calls[:3] == ["a", "c", "b"]`).
- **Still to measure live** (the client was closed): the first-name latency with the warm-up running,
  and how long the 99-file load takes in practice. One run of
  `python tests\perf_access_cost.py --live` prints the PING pickup, the hook-hit rate, the dat chain
  phase by phase and the first-vs-cached decode; `tests/probe_name_scheme.py` prints the whole table of
  names beside the viewer's own rows. Both are launched with one UAC prompt and need the game running.

## Now (round 10 - the owner pointed at the agent viewer, and was right to)

- **What the owner said, and where it sent me.** *"you will need to see the agent viewer in the reforged
  branch, it has a table where the agent names are displayed, you need to follow the exact scheme or
  else it wont work"*, and before that *"they keep a table of loaded names, the process is fairly fast,
  i think you might be doing something completely different"*. Both point at the sources' own name path.
  Here it is, read line by line, and here is one name taken through it live.
- **The agent viewer is `Widgets/Coding/Debug/Guild Wars/Agent Info.py`** (`MODULE_NAME = "Agent Info
  Viewer"`, 625 lines). Its scheme, which is the scheme to follow:
  - rows come from `AgentArray.GetAgentArray()` + `Agent.GetAgentByID(agent_id)` (`:519-524`), with the
    nearest enemy/ally/item/gadget/NPC/target rows above them (`:465-486`);
  - the **name column is `Agent.GetNameByID(agent.agent_id)`** (`:53`, `:77`);
  - the encoded column is `Agent.GetEncNameByID` / `Agent.GetEncNameStrByID` (`:49`, `:90`);
  - and its diagnostic variant prints exactly the state the port's table carries --
    `string_table._string_table_loaded`, `_load_enqueued`, `_last_load_status`, and
    `raw in string_table._pending` (`:61-68`).
  **That is the port's member set and the port's body**: `GetNameByID` = `PyAgent.get_agent_enc_name`
  + `string_table.decode` (`Agent.py:142-179`), implemented as written (`py4gw/agent.py:109-160`,
  `508-566`; `py4gw/internals/string_table.py:1143-1205`). Nothing in the scheme needed changing --
  which is why this round was spent **proving it**, not rewriting it.
- **Reforged and Native gather a name in the same two steps and differ only in the decoder:**
  | | fetch | decode |
  | --- | --- | --- |
  | Reforged (Python) | `PyAgent.get_agent_enc_name` (`agent_bindings.cpp:216-224`) | `string_table.decode` -- a table read out of GW.dat **in process**, so it is free |
  | Native | the same C++ `GW::agent::GetAgentEncName` (`agent_methods.cpp:249-316`) | `ui::AsyncDecodeStr` -- **the client decodes** (`agent_methods.cpp:318-325`, `ui_methods.cpp:2582-2607`) |
  The port has both mechanisms: the table (`py4gw/internals/string_table.py`) and the client's decoder
  (`py4gw/ui/async_decode.py`, the dialog and chat port). This round put a single name through both.
- **One name, alone, live** (`tests/probe_name_scheme.py`, new): the owner's instruction was *"grab a
  single npc name and test if it works"*, so the probe prints every intermediate value. Agent **15**,
  client `Gw.exe` pid 20496:

  ```text
  {"stage": "agent", "agent_id": 15, "type": 512, "is_gadget": true,
   "name_bytes": [110, 12, 0, 0], "pointer": 672027352}
  {"stage": "compare", "agent_id": 15, "client_name": "",
   "port_name": "Random Arenas", "port_ms": 2067.753, "agree": false}
  {"stage": "gadget_walk_record", "agent_id": 15, "record": true, "extra_info_sub_ptr": 663221008}
  {"stage": "gadget_walk_sub", "agent_id": 15, "sub": true, "gadget_name_enc": 0, "gadget_id": 75}
  {"stage": "gadget_walk_info", "agent_id": 15, "gadget_info_valid": true, "gadget_info_size": 9524,
   "gadget_id": 75}
  {"stage": "gadget_walk_info_record", "agent_id": 15, "record": true, "name_enc": 672027352}
  ```

  Read the way native reads it (`agent_methods.cpp:290-307`): `type = 0x200` is a **gadget**
  (`agent.h:136`), `gadget_name_enc` is **null**, so the name comes from `gadget_info[gadget_id].name_enc`
  with `gadget_id = 75` out of a 9524-entry table -- and the pointer the port read from that record **is
  the pointer the walk names**. The row is the source's, branch for branch.
- **Six agents, and four of them prove the decode.** Same run, same client:

  | id | type | encoded | the port's text | what it is |
  | ---: | --- | --- | --- | --- |
  | 15 | `0x200` gadget | `\x0C6E` | `Random Arenas` | a portal prototype |
  | 16 | `0x200` gadget | `\x0C9E` | `Great Temple of Balthazar` | a portal prototype |
  | 26 | `0xDB` living | `\x8102\x064F` | `Vekk` | a hero, by name |
  | 27 | `0xDB` living | `\x8101\x38AA` | `Dunkoro` | a hero, by name |
  | 28 | `0xDB` living | `\x0BAA\x0107...` | `Pet - %str1%` | a pet-name pattern |
  | 29 | `0x200` gadget | `\x8102\x35B5\xE9AA...` | `Zaishen Chest` | the chest |

  `Vekk`, `Dunkoro` and `Zaishen Chest` are the client's own names for those records, and two of them
  come through the table's RC4 path -- a wrong index or a wrong key cannot produce them. So the decoder
  is not "gathering whatever": it renders four independent records correctly, one of them a hero and one
  of them a chest.
- **`Random Arenas` is a map name, out of the sources' own table** --
  `Py4GW_Reforged_Native/include/GW/common/constants/maps.h:954` (`"Random Arenas"`, in the outpost
  list, with `Great Temple of Balthazar` beside it). The objects that carry such a name are the client's
  **gadget prototypes named after their destination** -- the portals. The string is therefore the
  client's own name for the prototype that record points at: a portal gadget in a Battle Isles map, in
  the same map as the Zaishen Chest. The probe prints the map id (next run), which will name the map.
- **The slot mapping was verified live for the first time, and it is the source's.** The probe prints
  what `_load_table_for_language` rests on (`string_table.py:766-805`): `language_id = 0`,
  `entries_per_file = 1024`, `slot_count = 99`, and slots 0-7 each carry
  `start_index == slot_index * 1024`, `end_index == start_index + 1024`, `lang_id = 0`. Entry 2926 is
  therefore in slot 2 at `2 * 1024` -- exactly the file the port read, and exactly what Reforged reads
  for that entry.
- **The client's own decoder, called for the first time, and it answered empty.**
  `py4gw/ui/async_decode.py` is Native's route; every precondition was there
  (`ui.validate_async_decode_str_func` resolves, the decoder stub is placed at `0x035F0000`, the
  `TextParser` address is live) and each call round-tripped in **~130 ms**, but the answer was `""` for
  all six strings. Empty is also what the wrapper's own three refusals write, so the next run prints
  `decode_state(slot)` plus the preconditions before the call, which tells those two apart. **Open, and
  this is the work item.**
- **Why a name costs what it costs here, measured.** The dispatcher takes **one command per hit**
  (`py4gw/game_thread/payload.py:978-996`) and one command round trip measures **~130 ms**; the GW.dat
  chain is four of them. Live, per string file: **1055 / 1060 / 1066 ms** for three *new* slots,
  **20.7 ms** for a slot already in the table, **0.104 ms** for a cached decode. Reforged pays none of
  this -- its dat read is in-process -- and the source's eager load of all 99 files would cost **~100 s**
  through this ring, which is why the port reads the one file an entry names and keeps it. That is a
  **mechanism divergence and it is recorded as one**.
- **The map was the Isle of the Nameless, and that is what makes the two names readable.** The run
  printed `map_id = 280`; the sources' own table says `NAME_FROM_ID[280] = "Isle of the Nameless"`
  (`Py4GW_Reforged_Native/include/GW/common/constants/maps.h`, the array at line 765; the `MapID` enum
  agrees: 279 `Leviathan Pits`, 280 `Isle_of_the_Nameless`, 281 `Zaishen_Challenge_outpost`). That map
  is where the **Zaishen Chest** stands (`settings ... items.json`: *"The Battle Isles / Isle of the
  Nameless / Zaishen Chest"*) and where the **portals to the Battle Isles outposts** are -- so the two
  gadget names are the destinations those portals lead to, which is what the client's gadget-prototype
  table calls them. The owner's objection -- *"there no random arenas anywhere in this map"* -- is
  answered by the map itself: the *portal* to Random Arenas is in the Isle of the Nameless, and the
  Zaishen Chest standing beside it is the proof that the decoded names are the client's own.
- **The fetch is cross-validated by a second client field.** `Agent.GetGadgetID` (Reforged
  `Agent.py:1600-1606`, the agent record's own `gadget_id` at `+0x0D0`, `agent.h:177`) answers
  **75** for agent 15 and **3651** for agent 16 -- exactly the `gadget_id` the summary sub-record
  carries, which is the field native's walk indexes `gadget_info` with. Two independent client fields
  agree, so the record the port indexed is the record native indexes.
- **The client's own decoder is not a proven route on this build, and that reframes the empty answer.**
  `tests/test_live_dialog_text.py` records that the dialog step that fills `AsyncDecodeStr` is *blocked*
  on this client (`DialogLoader_GetText` is not the loader here, and calling it faulted the client on
  2026-09-25), so **the client-decode route has never been live-exercised with an expected text** --
  before this round it had never been called at all. The six empty answers are therefore at least as
  likely to be this side of the boundary (the emitted stub, or the slot the host reads) as the client
  refusing a valid string, and the probe now carries a **control**: the local player's own encoded name,
  which the client renders on the nameplate. If that one also comes back empty, the stub/slot path is
  the defect; if it comes back as the character's name, the client is refusing these particular strings.
  The probe also reports the call's three timings apart (placement, call, wait for the callback), which
  is what tells a host-side refusal (completed during the call) from the client answering later.
- **The run that carried this vanished mid-way, and the owner's crash log names the damage.** `Gw.exe`
  pid 20496 stayed alive and responsive and the probe's console stops after agent 27 with no traceback
  and no `done` marker, i.e. the Python process was terminated externally. Sixteen minutes later, when
  the client was closed, it asserted: **`Error: file 'F:\GW\GW1\Gw.dat' still open`
  (`NtFile.cpp(321)`, 19:39:35)**. That is this project's footprint and nothing else: the only thing
  here that opens a dat record is the string-table chain (`py4gw/dat_reader.py`), and a controller that
  dies between `ReadFileBuffer` and `CloseRecObj` leaves the record open in the client until it exits.
  Confirmed read-only before the client closed: the entry hook was still installed
  (`leave_game_thread_func` at `0x00845880` = `BaseAddr + 0x235880` read `e9 7b a7 74 03 90 90 90`).
  **Full analysis, including what a crash log does and does not reveal about this project's traces, is
  in [`RESEARCH.md`](RESEARCH.md) § *The 2026-09-26 19:39 client exit assertion*.** The operational rule
  is unchanged and now has a second reason behind it: **a live run must be allowed to finish**, and a
  run that dies leaves a client to be restarted.
- **Next:** start the client again (a restart clears the hook and the record), then one elevated run of
  `tests/probe_name_scheme.py` (`live_reports/name_scheme7*`), which prints the map id, the decode
  preconditions, the three decode timings per string, the **control string**, the gadget walk, and the
  viewer's own rows — so the port's table can be put beside the viewer's and read off. The open item
  behind it: if the control answers text, the client-decode route is the one-command name path
  (~130 ms, no GW.dat) and the stub's empty answers for agent names become a specific finding; if it
  answers empty, the stub/slot path is the work item.

## Now (round 9 — live)

- **The owner's catch, and it was two real defects — both about how the sources gather a name:**
  1. **Reforged loads the string table once, on the first frame** (`TextContext.py:152-155`, inside the
     `TextParser` refresh) and then every name is a dictionary hit. This port had the same trigger but
     nothing fired it until a *decode* did, so the whole GW.dat chain ran **inside the first
     `Agent.GetNameByID`** — and again on every later read while a load had not succeeded
     (`load_string_table` resets its flag on failure). Fixed: `ConnectedClient.__init__` refreshes the
     `TextParser` context once, right after the capability layer is installed — this port's startup,
     where Reforged's first frame would be. Pinned by
     `test_the_string_table_is_loaded_by_the_connection`.
  2. **The record behind a name is a table index, not a rebuilt cache.** Native's
     `GetAgentEncName(id)` reaches the record through `GW::agent::GetAgentByID` — *one index* into the
     client's agent table plus the movement check (`agent_methods.cpp:73-88`). This port called
     Reforged's **Python** `Agent.GetAgentByID`, whose view answers from `_build_allegiance_cache`: a
     traversal of every slot (975) to answer one id. Now ported as native writes it —
     `_get_agent_by_id` in `py4gw/agent.py`, with **both** halves indexed (the movement array too;
     the first attempt still materialized it). Live A/B on the same client, 25 agents:
     **0.09 ms** per name against **2.10 ms** for the view-cache path cold — 22× for the case that
     matters, a caller asking for one name — with **0 byte mismatches** and all four branches intact.
- **The client crashed twice, and neither crash was a read path.** Both came from a run being
  **killed without `disconnect()`**, which leaves this project's entry patch live in the client; the
  next connect then refuses to patch the stale target (fail-closed — *"expected 55 8b ec 8b 45 08 83
  f8 56, observed 55 8b ec 83 ec 2c 53 8b 5d. Nothing was written."* at `0x008440C0`) while the
  client's game thread is still running the orphaned stub, and the client dies at `eip=01b00000`.
  Restarting the client clears it. Full timeline, trace and evidence: [`RESEARCH.md`](RESEARCH.md).
  **Consequence for how live runs are done: a run must be allowed to finish.**
- **What the live runs proved before that:**
  - `tests.test_agent_array` — **6 tests OK (2 skipped)** on a real connection (client pid 47456):
    resolver `0x00E0C714`, header `size=188, capacity=251`, categories **all=43, ally=3, enemy=10,
    gadgets=3**, `Agent.GetAgentByID(15)` → gadget at `(-1943, -1725, 0)`. That is the live proof of
    the point-of-use `AccAgentContext` refresh.
  - `tests.test_live_agent_effects` — `test_encoded_names_are_the_clients_own_bytes` **ok** on the
    same connection (the binding's bytes, terminator included).
  - **The names, unelevated and complete** (`tests/probe_agent_effects_live.py`, every present
    agent): branches **player array 1 / world `agent_infos` 35 / NPC record 4 / gadget context 3**,
    43 named records, **0 byte mismatches** between the ported `get_agent_enc_name` and an
    independent read, and `IsMartial`/`IsMelee` over **23 armed agents with 0 mismatches** against
    the source's own body.
- **Two live-test defects found and fixed** (both mine, neither the port's): the martial test compared
  the `ILLUSIONARY_WEAPONRY_ID` memo before anything had written it (it is `0` until
  `IsMartial`/`IsMelee` runs, `Agent.py:1340-1342`); and the name tests retried per agent, which
  multiplied the table-load wait by the sample size and made a slow run look hung.
- **Next:** restart the client, then the suite in one uninterrupted elevated run:
  `pwsh -NoProfile -File tools\run_live_suites.ps1 tests.test_live_agent_effects tests.test_agent_array`

- **The live run happened, without elevation.** `py4gw.connect()` is a write and asserts elevation,
  so the probe reads **directly** instead: `tests/probe_agent_effects_live.py` opens the read-only
  reader, builds the same facades `ConnectedClient` builds, registers that stand-in as the current
  client, and lets the ported members run unmodified. Client: `Gw.exe` pid 46544
  (`F:\GW\GW1\Gw.exe`). Full output: `live_reports/probe_agent_effects_live.txt`.
- **The agent name — all four branches of the source's walk answered:**
  | branch (`agent_methods.cpp:263-316`) | agents |
  | --- | ---: |
  | player array (`players[login_number].name_enc`) | 55 |
  | world `agent_infos[agent_id].name_enc` | 26 |
  | NPC record (`GetNPCByID(player_number).name_enc`) | 7 |
  | gadget context (`gadget_info[id].name_enc`) | 2 |
  90 of the 93 non-null records carried a name, and **the ported `get_agent_enc_name` returned
  exactly the bytes an independent read of the same pointer returned for every one of them**
  (`port_bytes_mismatches: []`).
- **55 player names decoded through `Agent.GetNameByID`**, with no string table at all — the inline
  `0x0BA9` form: `Blacki D Dragon`, `Twiddly Knobs`, `Zero Refrain`, `Soul Hanako`,
  `Ragnarok Windwalker`, `Smeagol The Sinless`, `Hammers Are Amazing`, … The live byte shape is
  `0x0BA9` + `0x0107` + UTF-16LE text + `0x0001` + terminator (38 bytes for 15 characters), and the
  offline fixture in `tests/test_agent_offline.py` now reproduces it exactly — including why that
  word must be nonzero: the binding's copy stops at the first zero **code unit**.
- **The names that are not player names are string-table indices** (`\x8102\x3B6F…`), so their text
  needs the table GW.dat fills — a call into the client. That half is
  `tests/test_live_agent_effects.py` (the elevated suite, written this round).
- **The skill timer is the client's clock:** `2202888165 → 2202888416`, **+251 ms** across a 250 ms
  sleep; `GetGWWindowHandle()` = `592774`.
- **The array view reads as the source describes:** `agent.agent_array_addr` = `0xE0C714`, header
  `buffer=0x31411068, size=975, capacity=1024`, 975 slots → 93 non-null (91 living, 2 gadgets),
  categories **all 93, ally 56, enemy 0, items 0, gadgets 2**, and `view.GetAgentByID(10)` =
  `Agent.GetAgentByID(10)` = record 10.
- **One live defect, found and fixed:** the view's cache gate read `AccAgentContext.get_context()`,
  a class cache nothing refreshed outside Reforged's frame loop — live, every category list answered
  **empty** (including `GetAgentArray()`). Fixed by the port's own point-of-use rule
  (`AccAgentContext._update_ptr()` before `get_context()`, exactly as `string_table` refreshes
  `TextParser`), and the literals above are the post-fix readings. Recorded in `docs/RESEARCH.md`.
- **The effects array was null at run time** (`buffer=0x0, size=0, capacity=0`): the character had no
  effects or buffs running, so the walk correctly answered empty/`0`/`False`. The elevated suite
  compares block for block when blocks exist and skips with that reason when they do not.
- **What only the elevated suite can do:** the GW.dat string-table decode (non-player names), and
  everything through the real `ConnectedClient`. Run:
  `pwsh -NoProfile -File tools\run_live_suites.ps1 tests.test_live_agent_effects tests.test_agent_array`
  — the runner's default list now includes both (and the probe). **Two runner defects were fixed so
  the probes actually run:** its `*.py` branch built the path with a dot-to-backslash replacement
  that mangled the extension (`…_live\py`), and its per-suite log name embedded the entry's slashes,
  so a probe's report could not be written. A probe entry is now a path (`tests/probe_x.py`) and the
  log is named for the suite's leaf (`live_reports\probe_x.py.log`) — verified by running the probe
  through the runner: `exit=0, 2s`.
- **Evidence:** the probe's report file (above); `1070 tests OK` after the fixture was corrected to
  the live byte shape; scoped `pyright` on the live files, the probe and the touched library files
  `0 errors`. The probe was run twice, in two different districts (93 then 43 non-null records,
  55 then 1 other player), and **both runs reported zero byte mismatches** — the walk is not
  state-specific.

## Now (round 8)

- **`py4gw/effect.py` landed**: Reforged's `Effects` (15 members) over Native's `PyEffects` binding
  over the `GW::effects` walk — **12 of the 15 work**. The walk is `Context::GetPartyEffectsArray()`
  scanned for the matching `agent_id` (`effects_methods.cpp:29-55`), which this port already reads
  (`WorldContextStruct.party_effects` → `AgentEffectsStruct.effects`/`.buffs`; native's layouts
  0x24/0x18/0x10 all match), so every effect and buff answer is a read: the counts, both `*Exists`
  walks, `HasEffect`, `EffectAttributeLevel`, `GetEffectTimeRemaining`, `GetBuffID`, `get_instance`
  and the two list builders.
- **The skill timer landed with it** — `py4gw/memory/memory_manager.py`, the port of
  `PY4GW::MemoryManager` (7 members): `GetSkillTimer` = `timeGetTime() + *g_skill_timer_ptr`
  (`memory_manager.cpp:69-71`, the global the catalog names `memory.skill_timer_ptr`),
  `GetGWWindowHandle` (`*window_handle_ptr`), `GetGWVersion`/`MemAlloc`/`MemRealloc`/`MemFree` as
  typed calls on the client's own thread, and `Scan` as the source's resolve-once step. Reached as
  `client.memory_manager`.
- **What that closed:** `Agent.IsMartial`, `Agent.IsMelee` (**`Agent` 145 of 148**, three left:
  the console path and the two frame-loop members), the effect snapshot's two computed fields, and
  **`Skillbar.SkillbarSkill.get_recharge`** — which had been raising with exactly this requirement
  in its message since the `Skillbar` port. `DropBuff` and `ApplyDrunkEffect` are the two client
  calls (`effects.drop_buff_func` / `effects.post_process_effect_func`, forms `U32` and `U32_U32`).
- **Two findings, both on their member:** `GetAlcoholLevel` is *not* a read — native captures the
  client's post-process argument with an entry hook (`effects.cpp:24-41`), so the member raises and
  the entry is now in `docs/TARGET_SIDE_WORK.md` with its next step; and `GetAlcoholTimeRemaining`
  calls `PyEffects.PyEffects.GetAlcoholTimeRemaining()`, **which the binding does not implement**
  (`effects_bindings.cpp:181-183`) — the stub declares it and native tracks no alcohol time, so the
  member reports that disagreement rather than inventing a clock.
- **Evidence:** `1070 tests OK` (1.0 s; +19 this round, `tests/test_effects_offline.py` is 16 of
  them); scoped `pyright` on the nine touched files `0 errors`; `Agent`'s raising set pinned at
  **3** from the module's own `ast`; the skillbar slot's recharge pinned against a fixture timer
  (both branches: a zero recharge answers `0` without asking, a real one is the masked `DWORD`
  subtraction).
- **The last port-side helper in the context module is gone.** `_timed` — a `contextmanager` the
  deleted layer had introduced to time the resolver — is removed, with the `perf_counter` parameters
  it fed on `AgentArray.resolve_address`/`initialize`/`read_context`; `client.py` calls
  `initialize()` like every other facade. The definition inventory of
  `py4gw/context/agent_array.py` against the pre-deletion backup now reads: **nothing added, and
  every missing name is an invented one**. `_memory_reader` stays, and deliberately: it is the
  annotation-only `Protocol` the same module uses for its reader parameters, declared identically in
  20 other ported context modules — no behaviour, nothing calls it, and the module has carried it as
  its annotation shape throughout.
- **Agent's remaining three are now classified, and none of them is porting work.**
  `enable`/`_invalidate_property_cache` are the two halves of Reforged's per-frame cache
  registration — no frame loop here, and `PORTING_RULES.md` forbids standing in a throttle of our
  own. `GetProfessionsTexturePaths` prefixes its paths with
  `PySystem.Console.get_projects_path()`, which native defines as
  **the injected runtime's own module directory** (`system_bindings.cpp:72-74` →
  `process_manager.cpp:38-40`, where its `Assets/Textures/Profession_Icons` live): this project is a
  controller package with no such module and no such assets, so there is no path to build. The
  member is the **third of the artifact kind** — `AGENTS.md` § *the unit of work is the class* now
  names all three, with `Player.player_instance` and `Dialog._call_native_dialog_method` — and it
  reports that rather than returning a string the source never produces. `AGENT_PORT.md` carries the
  table.
- **Next:** (1) **the module-level `get()` sweep** — still the open cornerstone violation, 24
  context modules and ~60 call sites, and it needs the owner's call; (2) **`Quest`**, the next class
  in the friction order (the async-decode path a dialog caption already uses); (3) the alcohol hook
  (`TARGET_SIDE_WORK.md`) and the frame loop (structural); (4) back to `Player`.

## Now (round 7)

- **`PyAgent.get_agent_enc_name` is ported, and it was never target-side work** — the note that
  called it that was wrong. The binding (`agent_bindings.cpp:216-224`) calls **native's own**
  `GW::agent::GetAgentEncName` (`agent_methods.cpp:249-316`), which is Py4GW's C++ over client state
  this port already reads, so the port is read-only: no `game_thread` call, no patch. What it needed
  was the cascade, and every step of it is now in place —
  `py4gw/agent.py` carries `get_agent_enc_name` plus native's two functions as
  `_get_agent_enc_name_by_id` / `_get_agent_enc_name_by_agent` (the agent record, the world's
  agent-name array, the player array by login number, the NPC fallback, the agent-summary gadget
  entry, the gadget context, the item array), and `item::GetItemById`
  (`item_methods.cpp:109-112`) was added to `py4gw/context/item_context.py` because the item branch
  needs it.
- **What it closed:** `Agent.GetNameByID`, `GetEncNameByID`, `GetEncNameStrByID` and, through them,
  `IsNameReady`, `GetAgentIDByName`, `GetAgentIDByEncString`, `GetModelIDByEncString` and the
  `RequestName` alias — **8 of the 13 raisers**, so `Agent` is **143 of 148**, and the five that
  remain are the two `Effects.HasEffect` members, the console-path one and the two frame-loop ones.
  **`Player.GetName` is the source's body again** (`Agent.GetNameByID(Player.GetAgentID())`); it had
  been adapted to read the character context's name field only because this binding was missing.
- **The one divergence, and it is the external read's:** the binding walks the client's `wchar_t*`
  to its terminator (that pointer is in its own process); this port reads it through a bounded
  `ReadProcessMemory`, so the copy stops at the terminator or at `MAX_ENC_NAME_CODE_UNITS` (256 code
  units). Documented on `get_agent_enc_name` and in `AGENT_PORT.md`.
- **Evidence:** `1051 tests OK` (1.0 s) — 10 more than last round, all of them new; scoped `pyright`
  on `py4gw/agent.py`, `py4gw/context/item_context.py`, `py4gw/player.py` and the test file
  `0 errors`. New offline coverage: `AgentEncNameTests` (11 tests) drives **every branch** of the
  walk against records a fixture builds and a reader that serves them — the agent record, the world
  agent-name array, the player array by login number (and the null answer past its size), the NPC
  fallback, the agent-summary gadget entry, `gadget_info`, the item array by item id, the bound, and
  the four members that call it. The raising-set test now pins **5**, from the module's own `ast`.
- **Next, in the order I would take it:** (1) **`Effect`/`Effects`** — the class map's next class,
  closing `IsMartial`/`IsMelee` (2 of the 5) and the last offline dependency `Agent` has;
  (2) the **module-level `get()` sweep** (24 context modules, ~60 call sites — the owner's call is
  still open on it); (3) the console path and the frame loop, both of which are structural rather
  than porting work; (4) back to `Player`.

## Now

- **Step 3 done: `py4gw/context/agent_array.py` holds only the sources' own surface.** The module
  went 2639 → 1569 lines (28 definitions deleted): `AgentReference`, `AgentArraySnapshot`,
  `LivingAgentSnapshot`, `StaleAgentReferenceError`, `AgentKind`, the four `Reforged*Struct`
  duplicates, `_agent_record_type`, and the facade members that existed for them (`read`,
  `read_agent`, `read_agent_by_id`, `snapshot`, `living_snapshot`,
  `refresh_living_agents`, `get_living_agent`, `_read_snapshot`, `_validate_reference_current`,
  `_read_record`, `_read_pointer_values`, `_read_pointer_at`, `_kind_from_type_flags`,
  `max_pointer_slots`, `max_references`, the dead offset constants and their `__init__` arguments).
- **A name-based deletion removed 8 members it should not have, and they are back**: the AST pass
  matched any definition called `snapshot`, so `AgentStruct.snapshot`, `DyeInfoStruct.snapshot`,
  `ItemDataStruct.snapshot`, `EquipmentItemsUnionStruct.snapshot`, `EquipmentItemIDsUnionStruct.snapshot`,
  `EquipmentStruct.snapshot`, `TagInfoStruct.snapshot` and `VisibleEffectStruct.snapshot` went with
  the facade's `snapshot` property. All eight are restored verbatim, and the check is now an **AST
  inventory diff** against the pre-deletion backup: every name that is missing is an invented one,
  and every name that is present is the source's. That is the gate for the next deletion too.
- **Consumers re-pointed** (nothing in the tree references a deleted name):
  `examples/all_contexts.py` → `client.agent_array.get_context`; `tests/test_agent_array.py` — the
  live suite's subject *was* the invented API, so it is rewritten on the source surface
  (`read_context()` header + `Get*Array()` + `Agent.GetAgentByID`); `tests/perf_agent_array.py` —
  same, it now measures the view read and nested record access; `tests/test_agent_array_offline.py`
  — the three tests that pinned the snapshot's truncation/staleness guards are replaced by
  `GWArrayView` boundary tests (the place the port actually keeps the bounded-read decision);
  `AGENTS.md` step 1 of the live-dialog procedure named `client.read_agent_array()` and now names
  the source idiom. Both `__init__.py` export lists lost the deleted names.
- **Evidence:** `1039 tests OK` (1.0 s); scoped `pyright` on the 8 touched files `0 errors`.
- **Findings recorded this round, both new:**
  - Reforged's *Python* declarations of `ItemData`/`Equipment`/`AgentLiving` (0x13 / 0xF3 / 0x1C2)
    disagree with native's own `static_assert`s (0x10 / 0xD8 / 0x1C4), which is what the deleted
    `Reforged*` duplicates existed to keep visible. The port reads with native's sizes; the
    disagreement is written down in `AGENT_PORT.md` and in the struct test instead of kept as a
    second set of structs.
  - **The module-level `get()` helpers are a port-side invention.** 24 of the 25 ported
    `py4gw/context/*.py` modules end with `def get()` ("the context of the current selected
    client"); Reforged's `native_src/context/*.py` declare **no** module-level functions at all
    (only `MapContext.py`'s private `_file_hash_to_file_id` / `_get_prop_model_file_id`, which the
    port has). This is the same shape as the cornerstones' worked failures and it is the next
    question to settle — see the open items.
- **Step 4 done: docs rewritten, and `Agent`'s 13 raisers re-walked member by member.** Every
  recorded requirement was checked against the line it cites — `Agent.py:40-50` (the four caches
  `_invalidate_property_cache` clears), `Agent.py:52-60` (`enable`'s `PyCallback.Register`),
  `agent_bindings.cpp:216` + `stubs/PyAgent.pyi:98` (`get_agent_enc_name`, which wraps the client's
  own `GW::agent::GetAgentEncName`), `Effect.py:102` (`Effects.HasEffect`), `stubs/PySystem.pyi:105`
  (`get_projects_path`) — and all of them are accurate. The split is **8 direct + 4 transitive + the
  `RequestName` alias = 13 of 148**, computed from the port's own `ast`, not counted by hand.
  **Two checks came out of the walk and are now tests** (`tests/test_agent_offline.py`,
  `AgentSourceReferenceTests`): every member's docstring reference must be its own block in the
  source (that caught a real off-by-one — `GetRotationSin` named `750` for a member starting at
  `751`), and the raising set must be exactly those 13 names.
- **Evidence:** `1041 tests OK` (1.0 s); scoped `pyright` on the touched files `0 errors`;
  reference audit: 146 members point at their `@staticmethod` line and 2 (`GetModelID`, `GetXY`) at
  their two-decorator block start, because they are the two `@frame_cache` members.
- **Step 5 needs the owner's call — the four candidates, in the order I would take them:**
  1. **`Effect`/`Effects`** (item 2 of the class map's handoff queue) — closes `Agent.IsMartial` and
     `Agent.IsMelee`, i.e. 2 of the 13, and it is the last *offline* dependency `Agent` has. Its
     mechanism is native's `PyEffects`/`effects_bindings.cpp` over the effect array the ported
     `AgentLivingStruct` already reads.
  2. **The module-level `get()` sweep** — the cornerstone violation found this round: 24 context
     modules carry a `def get()` with no counterpart in either source (Reforged's context modules
     declare none), and ~60 call sites read them. Delete-and-route-through-`client.*`, or record
     them as the port's documented accessor divergence. Cheap to start, wide in reach.
  3. **`PyAgent.get_agent_enc_name`** — closes 3 direct + 4 transitive raisers (7 of the 13), but it
     is **target-side** work: it needs the client's own `GetAgentEncName` driven through
     `py4gw/game_thread` (`docs/TARGET_SIDE_WORK.md`), which is the largest item here.
  4. **Back to `Player`** — the original scope: `Player` is INCOMPLETE and its remaining members are
     named in `PLAYER_PORT.md`.

## Rules this file follows

- **A line is written before anything slow starts**, and rewritten when it finishes — no silent
  minutes.
- **Every claim carries its evidence** (the command, its result and how long it took), so nothing
  here has to be taken on faith.
- **Type-checking is scoped** to the files a change touches (`pyright <files>`, ~1 s). A whole-repo
  `pyright` (4–5 min) is run **only when the user asks**, and never twice at once.
- The test suite is the other gate: `python -m unittest discover -s tests -p 'test_*offline*.py'`
  (~1 s).

## Round log

| round | when | what changed | evidence | verdict |
| --- | --- | --- | --- | --- |
| 12 | 2026-09-27 04:30 | **a name is decoded by the client.** `Agent.GetNameByID` now hands the encoded string to the client's decoder (Native's `AsyncGetAgentName` route, `agent_methods.cpp:318-325`) and takes the text from its completion: **~115 ms** first time, **0.09-0.5 ms** cached, against ~2.1 s for the dat route's first name in a slot — and with no dat record at all. The table route stays in the tree for a caller that wants a table entry rendered on the host, and **no member reads it any more**, so the connect-time warm-up is off (it was competing with the decodes for the game thread: target/interact 70 ms -> 32 ms). Three defects fixed: `dialog._on_string_decoded` was taking decodes it did not own (consuming agent names and discarding their text), a disconnect could fail with names in flight (block orphaned), and the client answers only a few decodes at once (32 at once answered none; capped at 8). The owner's timed run: 8974 -> 7955 -> **4018 ms** process-start-to-interact | `1074 tests OK`; `pyright` `0 errors`; `live_reports/find_npc11.txt`, `name_member3.txt`, `name_scheme8.txt`, `perf_live.txt`; hook targets read back clean after every run | landed; cold map-wide sweep still ~2.9 s (levers named) |
| 11 | 2026-09-27 02:30 | **the GW.dat handling left the call path.** The `TextParser` trigger (connect) now calls the source's own enqueue `load_string_table(language_id)`; the load runs on one daemon worker (`_start_warmup`/`_warmup_worker`), the table is parsed in file by file (`_read_slot`, so a name answers as soon as its file has been read), a decode whose entry is missing *asks* for the slot it needs (`_request_slot`) and is served next (`_slot_order`), and `ConnectedClient.close` joins the worker before the block it reads through is released. The two members invented for the on-demand path (`use_string_table_language`, `_ensure_entry_loaded`) are deleted. Nothing is re-read on a map change (the table is the client's language table) | `1073 tests OK` (1.0 s; `WarmupTests` pins the non-blocking enqueue and the requested-slot-first order); scoped `pyright` on 5 files `0 errors`; `docs/STRING_DECODE_PLAN.md` § 10.1 | landed, live timing to measure |
| 10 | 2026-09-27 01:00 | **the owner's catch followed to the line**: the Reforged agent viewer (`Widgets/Coding/Debug/Guild Wars/Agent Info.py`) read member by member -- its rows, its name column (`Agent.GetNameByID`), its encoded column and its string-table state, which is the port's own scheme; `tests/probe_name_scheme.py` added and run live -- **one name alone** (agent 15: type `0x200` gadget, `\x0C6E`, entry 2926, slot 2, "Random Arenas") with native's gadget walk printed beside it (`gadget_name_enc = 0`, `gadget_id = 75`, `gadget_info` size 9524, the record's `name_enc` = the pointer read), six agents put through the port's decoder (Vekk, Dunkoro, Pet - %str1%, Zaishen Chest -- four correct records, two of them through RC4) and through the client's own decoder (native's route, first call: preconditions live, ~130 ms per call, answer empty -- open); **the slot mapping verified live for the first time** (`entries_per_file 1024`, `slot_count 99`, slots 0-7 `start_index == slot*1024`); the ring cost measured (one command per dispatcher hit, ~130 ms per command, ~1.0 s per string file, 0.104 ms cached) | `live_reports/name_scheme.txt`, `live_reports/name_scheme2*` (probe output); `pyright tests/probe_name_scheme.py` 0 errors; the sources' own tables quoted (`maps.h:954`, `agent.h:136`, `payload.py:978-996`, `Agent Info.py:42-90`, `:465-524`) | live: single name walked end to end; client-decode comparison open |
| 9 | 2026-09-26 22:40 | **live verification** (no elevation): `tests/probe_agent_effects_live.py` added — it builds the client's facades over the read-only reader, registers the stand-in as the current client, and runs the ported members unmodified against `Gw.exe` pid 46544; the agent-name walk answered on **all four branches** (player 55 / world agent_infos 26 / NPC 7 / gadget 2), 90 of 93 named records matched an independent read byte for byte, **55 player names decoded** through `Agent.GetNameByID`, the skill timer advanced **+251 ms** over 250 ms; `tests/test_live_agent_effects.py` added for the elevated half (GW.dat decode, the real connection); the runner's default list now includes both plus `tests.test_agent_array`; **one live defect found and fixed** (the view's category lists were empty because `AccAgentContext`'s class cache was never refreshed outside a frame loop); the offline name fixture corrected to the live byte shape | `live_reports/probe_agent_effects_live.txt`; `1070 tests OK`; scoped `pyright` `0 errors`; `docs/RESEARCH.md` carries the observations | live, elevated suite still to run |
| 8 | 2026-09-26 21:40 | `py4gw/effect.py` — Reforged's `Effects` (15 members, 12 working) over Native's `PyEffects` binding over the `GW::effects` walk of the ported `WorldContext.party_effects` array; `py4gw/memory/memory_manager.py` — the whole `PY4GW::MemoryManager` (the skill timer `timeGetTime() + *g_skill_timer_ptr`, the window handle, the version call and the three allocators), reached as `client.memory_manager`; `Agent.IsMartial`/`IsMelee` answer (**`Agent` 143 → 145 of 148**); `Skillbar`'s `get_recharge` closed with the timer; the last port-side helper in `context/agent_array.py` (`_timed`, with the `perf_counter` parameters it fed) removed, so the module's definition inventory now adds nothing over the sources; `Agent.GetProfessionsTexturePaths` classified as the third injected-runtime artifact member; two findings recorded on their members (the alcohol level needs the entry hook → `TARGET_SIDE_WORK.md`; the alcohol time calls a binding member that does not exist) | `1070 tests OK` (1.0 s; +19, incl. `tests/test_effects_offline.py`'s 16); scoped `pyright` on 15 files `0 errors`; the raising set pinned at 3 from `ast`; the definition inventory diff vs the pre-deletion backup adds nothing | landed |
| 7 | 2026-09-26 19:25 | `PyAgent.get_agent_enc_name` ported in `py4gw/agent.py` over native's own `GW::agent::GetAgentEncName` walk (agent record → world agent-name array → player array → NPC → agent-summary gadget entry → gadget context → item array), with `item::GetItemById` added to `py4gw/context/item_context.py`; the three name readers and the five members that called them answer (**8 of the 13 raisers closed**, `Agent` 135 → **143 of 148**); `Player.GetName` restored to the source's body; `AgentEncNameTests` (11 tests) drives every branch of the walk offline, and the raising-set test now pins 5 | `1051 tests OK` (1.0 s); scoped `pyright` on 4 files `0 errors`; the walk's own branches each have a test | landed |
| 6 | 2026-09-26 18:25 | steps 3–4: the invented layer is deleted (2639 → 1569 lines) and the 8 source `snapshot` methods the name-based deletion took with it are restored (AST inventory diff against the backup is clean); both export lists, `examples/all_contexts.py`, the two array test files and `AGENTS.md` step 1 re-pointed; `AGENT_PORT.md`/`CLASS_PORT_MAP.md` rewritten; `Agent`'s 13 raisers re-walked — every cited line verified, 8 direct + 4 transitive + the `RequestName` alias, now pinned by `AgentSourceReferenceTests` (reference audit + raising set from `ast`) | `1041 tests OK` (1.0 s); scoped `pyright` `0 errors`; 148/148 member references verified against the source's own lines; one real off-by-one found and fixed | steps 1–4 done |
| 5 | 2026-09-26 17:05 | steps 1–2: the record chain is the source's own (`Agent.GetAgentByID` → `AgentArray.GetAgentByID` → `client.agent_array.get_context()` → the view); all 13 class getters route through `get_context()`, item/owned-item/gadget names bridged as `AgentArray.py:145` does; the facade's twelve port-side `Get*Array` members, `client.read_agent_array`/`read_agent`/`read_agent_by_id`/`living_snapshot`/`refresh_living_agents`/`get_living_agent` and the context's module-level `get()` all **deleted**; every probe and live suite converted to the source's idiom (`AgentArray.Get*Array` + `Agent.*` fields + `view.GetAgentByID`) | `1042 tests OK` (1.1 s); scoped `pyright` on 11 files `0 errors` (2.5 s), and each converted live file checks clean on its own | steps 1–2 done, step 3 open |
| 4 | 2026-09-26 15:35 | context rebuilt on the source's own logic: `raw_agents` walks the array through the ported `GWArrayView`; `_build_allegiance_cache` is `AgentContext.py:1160-1256` (valid-agents gate, `is_*_type` flags, owned items, the allegiance switch with dead lists); `GetAgentByID` answers from that cache with a recorded divergence where the source reads shared memory; `AgentArrayStruct` no longer touches the snapshot at all; `tests/test_agent_array_offline.py` rewritten to pin the array-driven buckets and the context gate | `1042 tests OK` (0.9 s); scoped `pyright` on 4 files `0 errors` (1.2 s) | done |
| 3 | 2026-09-26 15:00 | `py4gw/agent_array.py` added — every member of Reforged's `AgentArray.py`; package root now exports the class (Reforged `__init__.py:101`), context view at `py4gw.context.AgentArray`; the context's three copied helper groups (`Manipulation`/`Sort`/`Filter`) deleted; `tests/test_agent_array_class_offline.py` added | `1041 tests OK` (0.9 s); scoped `pyright` on 7 touched files `0 errors` (1.2 s) | done |
| 2 | 2026-09-26 14:45 | agent records read through the ported `internals/types.py` (`Vec2f`/`Vec3f`/`GamePos`); `Vec2fStruct`/`GamePositionStruct` gone; every field offset verified against the sources' own comments and native's `static_assert`s | `1032 tests OK`; layout check: `AgentStruct` `0xC4`, `AgentLivingStruct` `0x1C4`, `allegiance` `0x1B5` | done |
| 1 | 2026-09-26 14:20 | invented `AgentAllegiance` deleted (26 call sites in 15 files now read the sources' `Allegiance` with its own member names); `py4gw/internals/types.py` ported (Reforged's `native_src/internals/types.py`) | `1032 tests OK`; scoped `pyright` `0 errors` | done |

## Open items, with their size

| item | where | size |
| --- | --- | --- |
| **module-level `get()` helpers** — no counterpart in Reforged's context modules | 24 `py4gw/context/*.py` modules + their exports | 24 members, ~60 call sites (tests, probes, examples); **needs the owner's decision**: delete and route through `client.*`, or record as the port's accessor divergence |
| `Agent`'s remaining raisers | `py4gw/agent.py` | **3 of 148, and none is portable work**: the frame loop 2 (the port's execution model; `PORTING_RULES.md` forbids a stand-in) and `GetProfessionsTexturePaths` 1 (the injected runtime's own module directory — the third artifact member) |
| `Effects`' remaining members | `py4gw/effect.py` | 3 of 15: `GetAlcoholLevel` (the entry hook, in `TARGET_SIDE_WORK.md`), `GetAlcoholTimeRemaining` (a binding member that does not exist), and the alcohol time it would need |
| frame-loop members | `Agent.enable`, `Agent._invalidate_property_cache`, `AgentArray.enable` | 3 — all three are Reforged's per-frame registration/clearing (`Agent.py:40-60`, `AgentContext.py:1443-1452`), which the port's execution model has no dispatcher for; each names its source lines and the reason |
| package-root exports are uneven | `py4gw/__init__.py` | `AgentArray` is exported (Reforged `__init__.py:101`) but `Agent`, `Dialog`, `Skill`, `Skillbar` and `Effects` are not, though Reforged's own `__init__.py` star-imports each module (`:106-108`). Not this round's business, but it is drift worth settling in one pass |
| whole-repo `pyright` on the current tree | — | never completed (the run was killed); unknown, will be run on request |
| **the client's own decoder (Native's route) answered empty** | `py4gw/ui/async_decode.py` via `tests/probe_name_scheme.py` | 6 strings, all empty, with every precondition live (`validate_async_decode_str_func` resolves, stub placed, TextParser live) and ~130 ms per call. Empty is also the wrapper's own refusal answer, so the next run prints `decode_state(slot)` to tell them apart. If the client really refuses these strings, that is a finding about the strings, not about the port's table decode (four of six names are provably right) |
| live verification of the two new read paths | `tests/test_live_player.py`, a probe | `Agent.GetNameByID`/`Player.GetName` and `Effects` are offline-verified against records; a live client would confirm the client's own buffers decode to real names and that the skill timer matches the client's clock (needs the user and an elevated shell) |
