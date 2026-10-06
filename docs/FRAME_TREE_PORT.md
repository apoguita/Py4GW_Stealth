# The `FrameTree` port: Reforged's `Py4GWCoreLib/FrameTree/` package

**Status: all seven of the package's modules are ported, and both of `frame.py`'s classes are declared in
full, in the source's own order.** `py4gw/frame_tree/` holds `frame_window_keys`, `frame_names`,
`frame_aliases`, `frame_registry`, `frame_ids` (5,010 lines, verbatim), `frame.py` — `_FrameTree`'s 41 members
(35 answering) and `Frame`'s 115 (96 answering), checked against both ASTs rather than by eye — and the
source's own `__init__` re-export list, compared name for name against the source's `__all__`. **Round 90
(2026-09-30) closed four of them and fixed a defect**, all of it reached from `Party.ReturnToOutpost`:
`hash_for_label` and `by_label` answer over the client's own `CreateHashFromWChar` (the wide label placed in
the block's data region — the mechanism `UIManager.SetStringPreference` proved in round 65, so the bodies
were the whole of the work), `child_native` answers over `g_get_child_frame_id_func` behind `GetFrameById`'s
own validity test, and `_FrameTree.root` was reading the **command's status word** instead of the callee's
return register — see §9, where the defect and its fix are written down. What is left is the tree's four
(`enable`/`disable` (`PyCallback`), `child_by_parent_hash` (the same `g_get_child_frame_id_func` walk,
one hash in), and `color_frames`/`overlay` (the injected `PyOverlay`)) and `anchor_ids`, which names only its
*label fallback* and answers on its snapshot and hash paths. `root` answers since round 36 (the catalog's
`ui.get_root_frame_func`, native's `GetRootFrame`), so
`viewport_height` reads through it and `sort_by_vertical` delegates to `rect`. `send_message` and `click`
answer since round 59 — both over the client's own `__thiscall` sender, live-verified. `Frame`'s 19 fall
into four features: the **game-thread frame actions** (`set_visible`, `set_disabled`, `show`, `set_layer`,
`set_opacity`, `double_click`, `mouse_action`, `mouse_click_action`,
`send_message_text`, `set_text`), the **root-frame geometry** (`rect`, `size`, `viewport_scale`,
`content_coords`), the **client's own text and input** (`label` and `title` through its title table,
`is_mouse_over` through its ImGui) plus the **overlay** (`draw`, `draw_outline`), and the lookups that call the
client directly (`child_path_native`, `item`, `tab`, `io_events`). Every one is written down in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md); nothing is stubbed.

**Sources.** `Py4GW_Reforged/Py4GWCoreLib/FrameTree/` — 5,444 lines across seven files: `frame.py` 1620,
`frame_ids.py` 1648, `frame_registry.py` 1588, `frame_aliases.py` 1216, `frame_names.py` 538,
`__init__.py` 70, `frame_window_keys.py` 20.

**Why this package is being ported at all.** It is the dependency of the last 21 members of `Inventory`
(see [`ITEM_PORT.md`](ITEM_PORT.md)): the salvage-choice dialog reaches frames through
`Frame.from_label`, `Frame.from_id`, `Frame(FrameId.X)`, `Frame.exists`, `Frame.is_created`,
`Frame.is_visible`, `Frame.is_usable`, `Frame.rect`, `Frame.size`, `Frame.click`, `Frame.mouse_action` and
`Frame.mouse_click_action`, and through `FrameTree.all_frames()`, `FrameTree.children_map()` and
`FrameTree.frames_under()`. This port's existing frame layer (`py4gw/ui/frame.py`,
`py4gw/ui/frame_tree.py`) is a **reader** — its own module docstring says it "adds the relationships the
array alone does not express" and that nothing in it "creates, destroys, relabels, or dispatches a frame" —
so it is not this surface, and the two live at different paths (`py4gw/ui/frame_tree.py` versus the
package `py4gw/frame_tree/`).

## 1. What is ported (2026-09-27)

| module | lines | what it is | how it was ported |
| --- | --- | --- | --- |
| `frame_window_keys.py` | 20 | `WINDOW_FRAME_KEYS` — the window names frames are reached by | verbatim (no imports, no computation) |
| `frame_names.py` | 538 | `FRAME_NAMES_CONFIRMED`, `FRAME_NAMES_OBSERVED`, `FRAME_NAMES_HARVESTED`, `FRAME_NAMES_RECONSTRUCTED`, the merged `FRAME_NAMES`, and the reversed `NAME_TO_HASH` | verbatim |
| `frame_aliases.py` | 1216 | `FRAME_ALIASES` — the readable alias for each frame path | verbatim |
| `frame_registry.py` | 1588 | `REGISTRY` (195 entries) and `DYNAMIC_KEYS` — the known frames and the keys resolved dynamically | verbatim |
| `frame_ids.py` | 1648 | `FrameId` — the frame-id hierarchy (`FrameId.ScreenFrame.C6.SalvageMaterialsDialog.YesButton` is the salvage dialog's own address) | verbatim |

All five are transcription, not reasoning: none of them imports anything, calls anything or computes
anything beyond the two derived tables the source itself builds (`NAME_TO_HASH` from `FRAME_NAMES`). So the
body of each is the source's own bytes with the port's header
(`tests/scratch\1port_frame_tree_tables.py`), exactly as `mods_upgrades` and `model_enums` were done.

**Verification.** `tests/test_frame_tree_tables_offline.py`: the public names of all five modules against
the sources, every table entry for entry, **dict key order included**, `FrameId` member for member and
recursively — its nested classes are compared by shape, because the source's class and this port's are two
different objects — and a measured size floor per table so an empty transcription cannot pass. The same
file states the two modules that are *not* ported, rather than skipping them silently.

## 2. `frame.py`, section by section

The module is 1620 lines and its shape is: three exception classes (79-88), `resolve_key` (92-118), the two
reverse-identity lookups (130-174), `_position_unusable` (178-198), `FrameState` (202-269), `_FrameTree`
(273-672, **41 members**), the `FrameTree = _FrameTree()` singleton (675), and `Frame` (679-1620,
**115 members**).

**Ported: lines 44-269 (2026-09-27)** — the constants (`_MOUSE_HOVER_STATE`, the four `RELATION_*` values),
`FrameError`/`FrameKeyError`/`FrameNotFound`, `resolve_key`, `_path_of`/`alias_by_path`/`key_by_path` and
`_position_unusable`, and `FrameState` with its `landed`/`blank`/`position` members. That section is
**dependency-free except for one read**, which the source's own docstring names: "constructing this is the
*only* place a ``PyUIManager.UIFrame`` comes into existence" (`frame.py:205-207`). The port answers it with
the read that binding wraps — native's frame record by id — which here is
``client.frame_array.get(frame_id)`` (``py4gw/ui/frame.py``, documented there as "matching the native
``GetFrameById``"). ``__all__`` is the source's list minus the two names the later sections bring, so a star
import cannot name something this file does not define.

**`_FrameTree` (273-672, 41 members) — mapped, and 28 of the 41 need nothing injected.** Measured from the
source (an AST pass that records, per member, which injected calls its body contains):

| lines | member | injected calls |
| --- | --- | --- |
| 288-303 | `__init__` | — |
| 306-314 | `enable` | — |
| 316-322 | `disable` | — |
| 324-326 | `_on_tick` | — |
| 329-370 | `rebuild` | `PyUIManager.UIFrame`, `PyUIManager.UIManager` |
| 372-375 | `ensure` | — |
| 378-406 | `state` | — |
| 408-412 | `_prune` | — |
| 414-423 | `invalidate` | — |
| 426-460 | `anchor_ids` | `PyUIManager.UIManager` |
| 462-464 | `child_of` | — |
| 466-468 | `children_at` | — |
| 470-474 | `children_of` | — |
| 476-477 | `child_codes_of` | — |
| 479-480 | `parent_of` | — |
| 482-483 | `hash_of` | — |
| 485-486 | `code_of` | — |
| 488-489 | `known` | — |
| 491-509 | `live` | `PyUIManager.UIFrame` |
| 512-515 | `all_ids` | — |
| 517-518 | `all_frames` | — |
| 520-526 | `children_map` | — |
| 529-533 | `_as_id` (staticmethod) | — |
| 535-537 | `descendants` | — |
| 539-552 | `descendants_of` | — |
| 554-560 | `root` | `PyUIManager.UIManager` |
| 562-567 | `viewport_height` | — |
| 569-571 | `hierarchy` | `PyUIManager.UIManager` |
| 573-574 | `overlay_frames` | `PyUIManager.UIManager` |
| 576-577 | `popup_frames` | `PyUIManager.UIManager` |
| 579-581 | `by_hash` | `PyUIManager.UIManager` |
| 583-585 | `by_label` | `PyUIManager.UIManager` |
| 587-588 | `hash_for_label` | `PyUIManager.UIManager` |
| 590-591 | `coords_for_hash` | `PyUIManager.UIManager` |
| 593-596 | `child_by_parent_hash` | `PyUIManager.UIManager` |
| 598-606 | `frames_at_path` | — |
| 608-614 | `frames_under` | — |
| 616-632 | `_frames_at` | — |
| 634-636 | `sort_by_vertical` | — |
| 638-665 | `color_frames` | — |
| 669-672 | `overlay` (`@property`) | `PyOverlay.Overlay` |

**The thirteen that reach the injected runtime are, one by one:** `rebuild` (which builds the tree from
`UIManager`/`UIFrame`), `anchor_ids`, `live`, `root`, `hierarchy`, `overlay_frames`, `popup_frames`,
`by_hash`, `by_label`, `hash_for_label`, `coords_for_hash`, `child_by_parent_hash` (all `UIManager`) and the
`overlay` property (`PyOverlay.Overlay`). Each is a native `ui::*` call to be resolved when it is ported —
those are the call sites that decide how much of this class is portable, and they are worked through one at a
time. The other twenty-eight are pure tree bookkeeping over the structures `rebuild` fills, so they follow
it. **The tick-keyed snapshot below is the decision that governs all 41 of them.**

### The tick-keyed snapshot, and what this port does about it

Reading `rebuild` and `ensure` (2026-09-27) settled the question that decides how **every one of the 41
members** is ported, so it is recorded before any of them is written.

**The source's model is tick-keyed.** `__init__` holds `version`, `tick`, `_built_tick`, the six structure
dicts and `_state` (`:288-303`); `_on_tick` bumps `tick` and does nothing else (`:324-326`); `rebuild`
snapshots the whole frame array into those dicts and stamps `self._built_tick = self.tick` (`:362`); and
`ensure` is `self.enable(); if self._built_tick != self.tick: self.rebuild()` (`:372-375`) — rebuild **once
per tick** and serve the snapshot in between. `enable`/`disable` are where that tick comes from: they
register `self._on_tick` with the injected `PyCallback.PyCallback` at `Phase.PreUpdate, priority=6`
(`:306-322`).

**This port has no tick, so `ensure` as written would pin the tree forever.** With nothing bumping `tick`,
`_built_tick != self.tick` is false after the first rebuild, so a second call would answer the *first*
snapshot for the life of the process — a dereferenced-pointer cache that never clears, which is exactly
what ``AGENTS.md`` § Caching forbids. The resolution is the one already used for `@frame_cache`: **the
member reads when it is called**. So the port's `ensure` rebuilds on the call, `enable` and `disable` raise
naming the missing registration (they are the frame-loop halves, the same class as `Agent.enable` and
`Agent._invalidate_property_cache`), and `_on_tick` is ported as written even though nothing calls it.

**What is *not* changed, and why it matters.** `rebuild`'s own staleness rule stays exactly as the source
writes it (`:356-369`): an empty frame array is "we cannot see the UI this tick", not "the UI is gone", so
the last good tree is kept and `stale` is set. That is the source's check, on the source's own terms, and it
is the reason overlays do not flicker; it is not the tick gate and is not touched by the adaptation above.

**The one call the section needs, resolved.** `rebuild` calls `PyUIManager.UIManager.get_frame_array()` and
then `PyUIManager.UIFrame(fid)` per id to read `parent_id`, `child_offset_id` and `frame_hash` (`:337-346`).
Both are native reads this port already has: `client.frame_array` (`py4gw/ui/frame.py`) walks the same array,
and its `iter_frames()` yields exactly a frame id and the record for it — so the port's loop reads the
record's own fields instead of constructing a wrapper, one pass, nothing added.

### The per-frame state cache is tick-keyed too, in two more places

`state`, `_prune` and `invalidate` (`:378-423`) are the tree's per-frame live copies, and they carry the same
adaptation as `ensure` — found by reading them (2026-09-27), so it is decided here before the members are
written:

1. **The per-tick memo** — ``previous = self._state.get(frame_id); if previous is not None and
   previous.tick == self.tick: return previous`` (`:387-389`). Untouched, this pins the first copy of every
   frame for the life of the process, because nothing advances `tick`. The port drops that test for the same
   reason it drops `ensure`'s: **the member reads when it is called**.
2. **The buffer's bound** — a blank read inherits the last good copy while
   ``previous.served < self.BUFFER_TICKS``, bumping ``served`` and stamping ``previous.tick = self.tick``
   (`:392-401`). That logic is kept as written; what it counts is *polls*, which the source's own comment
   says explicitly ("Counted in polls, not time"), so it needs no tick to keep its meaning.
3. **The age-based prune** — ``cutoff = self.tick - 240`` (`:410`). With no ticker that cutoff never
   advances, so `_prune` can never fire, and the `len(self._state) > 4096` guard at `:404-405` would call it
   in vain. This is the one piece of the cache that genuinely cannot work without a tick; it is recorded as
   such, and the member is ported as written rather than given an invented clock.

**The structure queries are clean by comparison**: `child_of`, `children_at`, `children_of`,
`child_codes_of`, `parent_of`, `hash_of`, `code_of`, `known`, `all_ids`, `all_frames`, `children_map`,
`descendants`, `descendants_of`, `viewport_height`, `frames_at_path`, `frames_under`, `_frames_at` and
`sort_by_vertical` (`:462-570`, `:598-636`) read the snapshot dicts `rebuild` fills and touch neither the
tick nor the injected runtime, which makes them the next section to port — and `all_frames`, `children_map`
and `frames_under` are three of the calls the salvage-choice dialog makes.

### The boundary at 24 members: the rest of `_FrameTree` needs `Frame`

Eleven of those eighteen queries are ported (`child_of`, `children_at`, `children_of`, `child_codes_of`,
`parent_of`, `hash_of`, `code_of`, `known`, `live`, `all_ids`, `children_map`, `:462-526`). Reading the other
seven (2026-09-27) showed that **every one of them goes through the `Frame` class**, which is not ported yet:

| member | what it needs from `Frame` |
| --- | --- |
| `all_frames` (`:517-518`) | `[Frame.from_id(f) for f in self.all_ids()]` |
| `_as_id` (`:528-533`) | `isinstance(frame_or_id, Frame)` and `frame_or_id._target_id()` |
| `descendants` (`:535-537`) | `Frame.from_id(i)` per descendant |
| `descendants_of` (`:539-552`) | `self._as_id(frame_id)` |
| `root` (`:554-560`) | `PyUIManager.UIManager.get_root_frame_id()` and `Frame.from_id(...)` |
| `viewport_height` (`:562-567`) | `self.root().viewport_dimensions()` |
| `frames_at_path` (`:598-606`) | `self.anchor_ids(anchor)` (an injected member) and `Frame`s |
| `frames_under` (`:608-614`) | `self._as_id(...)` and `Frame`s |
| `_frames_at` (`:616-632`) | `[Frame.from_id(f) for f in out]` |
| `sort_by_vertical` (`:634-636`) | each `Frame`'s `rect` |

**So `_FrameTree` is as complete as it can be without `Frame`**, and the order of work for the rest of this
package is settled: **`Frame` first** (`:679-1620`, 115 members, and the class that holds the remaining
injected `UIManager` calls), then the thirteen members above, then the source's own `__init__`. No further
member of `_FrameTree` can be written before it.

**Correction, measured against both trees (2026-09-27):** the "17 of 41" this section was written with left
out the three per-frame-copy members — `state`, `_prune`, `invalidate` (`:378-423`), ported in rounds 32-33 —
so the arithmetic above over-counted what is missing. What the trees actually hold is **`_FrameTree` 24 of 41
members** and **`Frame` 23 of its 115**, i.e. seventeen `_FrameTree` members remain, not twenty-four. Of the
eleven that call the client directly, two now answer (`anchor_ids`, `by_hash`, through the `GetFrameIDByHash`
read), two are declared and name their need (`by_label`, `hash_for_label` — `GetHashByLabel`), and seven are
still to declare: `root`, `overlay_frames`, `popup_frames`, `hierarchy`, `coords_for_hash`,
`child_by_parent_hash`, `child_with_hash`. The members the table above lists as waiting on `Frame`'s reads are
still waiting on them.

### `Frame` mapped: 74 of its 115 members call nothing injected

`Frame` (`frame.py:684-1620`) is next, and it was mapped the way `_FrameTree` was (2026-09-27) before any of it
is written. The count that matters is **not** 115 members against the runtime — it is the opposite:

| | |
| --- | --- |
| members | **115** (`__init__` at `:684` through `:1620`), of which **30** are `@property` and **2** are `@staticmethod` |
| **call nothing injected** | **74** — the whole constructor-and-identity core, the tree-backed readers, the child/parent navigation and the dunders |
| **call the injected runtime** | **41** — **39** are one-liners over `PyUIManager.UIManager`, **2** are draws (`draw`, `draw_outline`, `PyOverlay.Vec2f` + `FrameTree.overlay`) |

So the class is not 115 injected calls; it is **39 one-line properties, each wrapping exactly one distinct
`UIManager` member** — 39 call sites, 39 names, and no two properties sharing one (measured against the source,
2026-09-27) — and everything else is composition over `FrameTree.state()` and over other `Frame` members.

**39 is what `Frame` reaches; the file reaches 49.** The other ten are called from `_FrameTree`'s own members,
not from `Frame`'s: `get_frame_array` from `rebuild` (ported), `get_root_frame_id` from `root`,
`get_overlay_frame_ids` from `overlay_frames`, `get_popup_frame_ids` from `popup_frames`,
`get_frame_hierarchy` from `hierarchy`, `get_frame_coords_by_hash` from `coords_for_hash`,
`get_hash_by_label` from `hash_for_label`, `get_frame_id_by_hash` from `by_hash` and `anchor_ids`,
`get_frame_id_by_label` from `by_label` and `anchor_ids`, `get_child_frame_id` from `child_by_parent_hash` and
`child_with_hash`. Those **eleven** of `_FrameTree`'s remaining 24 touch the client directly and read no
`Frame` — `root` alone also returns one (`Frame.from_id(...)`) — so their only dependency on the class is that
it exists, while the rest of the 24 need its reads. That is the split to act on before `Frame`'s 39 properties
are written.

The 74 that need nothing injected, in the source's own order — this is the writable list:

`__init__`, `from_id`, `from_hash`, `from_label`, `_under`, `skill`, `hero_skill`, `bag_slot`, `_bag_offset`,
`inventory_bag`, `inventory_bag_slot`, `_storage_offset`, `storage_tab`, `storage_slot`, `material_slot`,
`party_list`, `party_member`, `effect`, `trainer_skill`, `capture_skill`, `dialog_option`, `_resolve`, `exists`,
`frame_id`, `_target_id`, `_state`, `blackboard`, `refresh`, `key`, `hash`, `name`, `code`, `alias`,
`registry_key`, `describe`, `widget_id`, `matches`, `is_anonymous`, `path`, `is_created`, `is_visible`,
`is_usable`, `template_type`, `type`, `visibility_flags`, `frame_layout`, `siblings`, `frame_callbacks`,
`frame_state`, `fields`, `parameters`, `parent_id`, `hover`, `position`, `rect`, `size`, `coords`,
`content_coords`, `viewport_scale`, `viewport_dimensions`, `is_mouse_over`, `parent`, `children`, `child_codes`,
`child`, `find_child`, `child_named`, `io_events`, `__iter__`, `__eq__`, `__hash__`, `__bool__`, `__str__`,
`__repr__`.

The 41 that name a call, grouped as the injected surface groups them: **identity and lookup** (`label`,
`state_bit`, `user_param`, `context`, `parent_id_native`, `parent_direct`, `child_native`, `child_path_native`,
`child_with_hash`, `first_child`, `last_child`, `next_sibling`), **mutation** (`set_visible`, `set_disabled`,
`show`, `set_layer`, `set_opacity`, `set_text`), **read of a frame property** (`layer`, `opacity`, `text`,
`encoded`, `title`, `min_size`, `native_size`, `client_border`, `clip_rect`, `position_ex`), **dispatch**
(`click`, `double_click`, `mouse_action`, `mouse_click_action`, `send_message`, `send_message_text`), and
**draw** (`draw`, `draw_outline`).

The **49** `UIManager` members `frame.py` reaches in total — the 39 above, plus the ten that `_FrameTree`'s
members reach — are
`get_frame_array`, `get_frame_hierarchy`, `get_frame_id_by_hash`, `get_frame_id_by_label`,
`get_hash_by_label`, `get_frame_label_by_frame_id`, `get_frame_state_bit_by_frame_id`,
`get_frame_user_param_by_frame_id`, `get_frame_context`, `get_frame_layer_by_frame_id`,
`set_frame_layer_by_frame_id`, `get_frame_opacity_by_frame_id`, `set_frame_opacity_by_frame_id`,
`set_frame_visible_by_frame_id`, `set_frame_disabled_by_frame_id`, `show_frame_by_frame_id`,
`get_frame_title_by_frame_id`, `get_frame_min_size_by_frame_id`,
`get_frame_native_size_by_frame_id`, `get_frame_client_border_by_frame_id`, `get_frame_clip_rect_by_frame_id`,
`get_frame_position_ex_by_frame_id`, `get_frame_coords_by_hash`, `get_text_label_encoded_by_frame_id`,
`get_text_label_decoded_by_frame_id`, `set_text_label_by_frame_id`, `SendFrameUIMessage`,
`SendFrameUIMessageWString`, `button_click`, `button_double_click`, `test_mouse_action`,
`test_mouse_click_action`, `get_parent_frame_id`, `get_parent_frame_id_direct`, `get_child_frame_id`,
`get_child_frame_by_frame_id`, `get_child_frame_path_by_frame_id`, `get_child_frame_id_from_name_hash`,
`get_first_child_frame_id`,
`get_last_child_frame_id`, `get_next_child_frame_id`, `get_prev_child_frame_id`, `get_root_frame_id`,
`get_related_frame_id`, `get_tab_frame_id`, `get_item_frame_id`, `get_overlay_frame_ids`, `get_popup_frame_ids`,
`is_ancestor_of_by_frame_id`.

**Each of those 48 is resolved to the native function it wraps when the property that calls it is written** —
member by member, the same rule the other injected modules were ported under, never as a group. That is the
inside-out order this class is ported in: the 74 composition members first (they are what the thirteen blocked
`_FrameTree` members and the salvage-choice dialog actually need), then the 41 runtime-backed properties with
their `UIManager` members resolved one at a time.

### `Frame`'s read surface funnels through `_resolve`, and `_resolve` needs `anchor_ids`

`Frame` is ported to `:890`: the constructor and every handle builder, then the twelve named indexed
accessors — `inventory_bag`, `inventory_bag_slot`, `_storage_offset`, `storage_tab`, `storage_slot`,
`material_slot`, `party_list`, `party_member`, `effect`, `trainer_skill`, `capture_skill`, `dialog_option`
(`:794-890`) — which is **22 of the source's 116 declarations** (`__slots__` plus 21 members).

Reading the section after it settled what the next work item is. **`_resolve` (`:893-917`) is the funnel every
read goes through, and it calls `FrameTree.anchor_ids(self._anchor)` (`:907`)** — one of the eleven `_FrameTree`
members that calls `PyUIManager.UIManager` directly (`get_frame_id_by_hash` / `get_frame_id_by_label`). Its
wrapped-id branch above that needs only `FrameTree.known(fid)` / `FrameTree.live(fid)`, both ported. So:

- a `Frame.from_id(...)` handle could resolve today;
- a registered **key or hash** handle cannot, because resolving its path needs `anchor_ids`, and `anchor_ids`
  needs two injected `UIManager` members resolved.

**So the next feature is the injected `UIManager` layer, not more of `Frame`.** `anchor_ids` is its smallest
entry (two members), and `_resolve`, `exists`, `frame_id`, `_target_id`, `_state` and every read above them
follow once it answers. The port's own module docstring already fixes the shape that takes — the read each
`PyUIManager.UIManager` member wraps, resolved one member at a time, exactly as `PyUIManager.UIFrame(fid)` was
resolved to `client.frame_array.get(fid)`.

**A source detail this slice pinned:** `FrameId` leaves are not uniform — `…C0.C0` is a node carrying `KEY`,
while `…C0.C0.Parent` is already the key string. That is what `getattr(key, "KEY", key)` (`:694`) is for, and
`party_list` / `party_member` reach both kinds.

### The two injected lookups in `anchor_ids`, resolved one at a time

`anchor_ids` (`:426-460`) is where the tree first needed the injected UI manager, and both of its calls were
resolved to the native function each wraps (2026-09-27):

| source call | native | what the port does |
| --- | --- | --- |
| `PyUIManager.UIManager.get_frame_id_by_hash(h)` | **`GetFrameIDByHash`** (`ui_methods.cpp:575-588`): after `if (!(hash && frame_array)) return 0`, scan the array by frame id and take the first valid frame whose `relation.frame_hash_id` matches. Validity is native's `IsFrameValid` (`:405-407`), a null/`-1` record pointer — here a slot that read back `None`. | **Ported as a read**, in `anchor_ids` and in `by_hash`: the same scan over `client.frame_array`. |
| `PyUIManager.UIManager.get_frame_id_by_label(label)` | **`GetFrameIDByLabel`** (`:570-573`) → `GetFrameByLabel` (`:556-568`) → **`GetHashByLabel`** (`:542-546`) = the client's own `CreateHashFromWChar(label, -1)`, then the same scan. | **Not portable yet**: it is a call into the client with a **wide string**, a form the capability layer does not have. |

`hash_for_label` (`:587-588`) is the same `GetHashByLabel` and nothing else, so it cannot be answered from any
read either.

**What each member does about it.** `by_label` (`:583-585`) and `hash_for_label` have no fallback in the
source, so they raise `_unported`, naming `CreateHashFromWChar` and the wide-string call form.
`anchor_ids` is different and the difference matters: the source wraps that lookup in `try/except Exception`
and uses 0, so the port's raise lands inside the source's own failure path and the hash read underneath still
answers — the member keeps working for every anchor the snapshot knows, which is what a registry key is.
Label addressing is not lost either: `Frame.from_label` is the source's *own* offline-table route
(`NAME_TO_HASH`, `:736-744`) and is ported; what waits is the client's runtime hashing of labels that table
does not know. The work item is on the target-side list, [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md).

**And the funnel above them now works**: `Frame._resolve` (`:893-917`) and `Frame.exists` (`:919-925`) are
ported, so an anchor plus child codes resolves to a frame id through the snapshot and `child_of`. The source's
per-tick resolution memo (`if self._version == FrameTree.version: return self._fid`) is dropped for the reason
`ensure`'s gate is — nothing advances `tick`, so the test could never hold — which leaves the member resolving
when it is called.

### `label` and `title` are one client call — and it is a call, not a read

`Frame.label` (`:987-995`) binds `PyUIManager.UIManager.get_frame_label_by_frame_id`; the later `Frame.title`
binds `get_frame_title_by_frame_id`. In native those are **the same function**: `ui_bindings.cpp:817-821`
wraps `GW::ui::GetFrameTitle(GW::ui::GetFrameById(frame_id))` twice, once through `SafeWide` and once through
`WideToUtf8`. And `GetFrameTitle` (`ui_methods.cpp:1784` and on) is not a read — it reads the frame's
**non-client word at `+0xCC`** and binary-searches the client's **title table** with
`g_title_binary_search_func`, against a table address the client's own context owns, then takes the wide
string through the title getter.

So `label` is declared with the requirement named (the title-table entry in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md)), and the source's own `except Exception` makes it report *no
label* rather than a stand-in — which is also what it does in Reforged when that lookup fails. `title` will
carry the same requirement when it is reached, since it is the same call.

**Everything else in the read surface needed nothing injected.** `frame_id`, `_target_id`, `_state`,
`blackboard`, `refresh`, `key`, `hash`, `name`, `code`, `alias`, `registry_key`, `describe`, `widget_id`,
`matches`, `is_anonymous`, `path`, `is_created`, `is_visible`, `is_usable`, `template_type`, `type`,
`visibility_flags` and `frame_layout` (`:927-1126`) are composition over `_resolve`, the tree's snapshot and
the migrated name/registry/alias tables — and the two inversions are now tested against the walk itself: a
real `key_by_path()` / `alias_by_path()` entry is rebuilt as a frame chain and must answer its own dotted key
and prose alias.

### Three more injected reads, each resolved to one record field

`siblings`, `frame_callbacks`, `frame_state`, `fields`, `parameters` and `parent_id` (`:1128-1212`) read
through `_state()` and needed nothing new — `fields()` is the inspection surface that walks the record's own
scalars, ordering the undocumented `field*_0x..` slots by struct offset. The three that follow them bind the
injected UI manager, and all three turned out to be reads of one frame record:

| source call | native | the port's read |
| --- | --- | --- |
| `get_frame_state_bit_by_frame_id(fid, bit)` | `GetFrameStateBit` (`ui_methods.cpp:1829-1831`): `frame && (frame->frame_state & bit) != 0` | the record's `frame_state` word, declared at offset `0x18C` (`py4gw/ui/frame.py:234`) |
| `get_frame_user_param_by_frame_id(fid)` | `GetFrameUserParam` (`:1825-1827`): `frame ? frame->field105_0x1c4 : 0` | the record's field at that offset (`py4gw/ui/frame.py:248`) |
| `get_frame_context(fid)` | `GetFrameContext` (`:758-772`): walk `frame_callbacks` from the end and return the last non-null `uictl_context`, null when the array is empty | `FrameArray.frame_context_address` (`py4gw/ui/frame.py:569-579`), which is that walk, documented there as the same rule |

All three fetch the record the way the binding does — `client.frame_array.get(fid)`, native's
`GetFrameById` — rather than through `_state()`, because `FrameState`'s held copy is Reforged's own
Python-side buffer while these three read the array.

### Next: the `UIManager` surface as a class of its own

**Landed 2026-09-27 (round 63): `py4gw/ui_manager.py` holds `class UIManager`, 48 of its 55
declarations answering.** The plan below was carried out in the order it sets out — the surface
enumerated and pinned member by member, the class declared in the source's own order, and the bodies
where the two meet — and [`UIMANAGER_PORT.md`](UIMANAGER_PORT.md) is now the record: the binding map,
what answers, what raises with its reason, and the live pass still owed. **Its step 3 does not apply,
and that is measured, not assumed (round 69):** this package's members do **not** go through that
class. `frame.py` calls **49 distinct `PyUIManager.UIManager.<name>`** binding members and **none of
them is a member of Reforged's `class UIManager`** — the class is the source's Python class (the
preference surface, the built-in windows, the dialog helpers, the frame-IO events) while this package
calls the injected *module* (`button_click`, `SendFrameUIMessage`, `get_text_label_*`,
`get_frame_array`, the traversal family). Re-pointing this package at that class would have meant
calling members it does not have, or adding members the sources do not declare. What the two share is
the native function behind each binding, and both resolve it where they use it.

Owner's direction (round 59): *the UI class — the one the frame click belongs to — needs porting too, and it
should be planned rather than drifted into.* What that class **is**, in each source:

- **Reforged**: `PyUIManager.UIManager`, the injected runtime's singleton. `Frame`/`_FrameTree` reach it 52
  times; the members are named in this document, and the full list of the 49 this package touches is above.
- **Native**: that singleton is the embedded binding's `UIManager` class over the `GW::ui` free functions —
  `ui_bindings.cpp` binds it and `ui_methods.cpp` carries the bodies.

Where this port stood: it had **no** such class, and every member resolves the native function its binding
wraps, one member at a time (the rule this package is ported by — `PyUIManager` is an injected module, so
each call is resolved to the function behind it, never guessed as a group). That is why `Frame.click` today
spells out `ButtonClick` itself.

**The plan, in order.** 1) Enumerate the surface from both sources and pin it: the `UIManager` members
`frame.py` calls, and for each one the native function or record write behind it (the table above is the
starting point; `ui_bindings.cpp` names the rest). 2) Port the class where the sources put it — its own
module, since Reforged imports it as a module and Native binds it as one — with every member declared in the
source's own order, each one the call it wraps (**no** re-derivation, and no member that the sources do not
have). 3) Points 1-2 are pure declaration work; the bodies are already built for the members this package
uses, so this is where the two meet: `Frame`'s members delegate to it rather than spelling out the native
call. 4) Verdict row in [`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md), and the same two gates as every other
class here: offline tests over the ported records, then the live client for anything that acts on it.

**What it must not become**: a second place where a call is derived (`no new layers`), and not a reason to
re-open members that already answer.

**Owner's scope for the UI surface (2026-09-27), and it is the rule that section is judged by:**
*"nothing from creating in-game windows, no dropdown, no create window, not even the class that handles
them, no singletons, no handlers — only primitives."* Applied to the 303 bindings in native's
`ui_bindings.cpp`, section by section (the source's own section headers):

- **Kept** — `UI messages / input` (11: `SendUIMessage`, `SendUIMessageRaw`, `SendFrameUIMessage`,
  `SendFrameUIMessageWString`, `button_click`, `button_double_click`, `test_mouse_action`,
  `test_mouse_click_action`, `key_down`, `key_up`, `key_press`); `Global state / language` (6);
  `Enc-string helpers` (3); `Preferences` (9 — the settings); `Built-in window (WindowID)
  position/visibility` (6); the **record classes** bound at the top of the file —
  `UIInteractionCallback` (the consumers), `FramePosition`, `FrameRelation`, **`UIFrame`** (the frame
  handles); `Frame tree traversal / discovery` (24); `Frame metadata / geometry` (14); and the primitive
  frame-state setters and label reads inside `Frame state setters` and `Text labels`.
- **Dropped** — `Widget creation (native component factories)` (14), every per-widget family
  (`Dropdown` 11, `Button` 3, `Checkbox` 4, `Slider` 2, `Editable text` 7, `Progress bar` 5, `Tabs` 13,
  `Scrollable` 13), the item-frame tint/pop/shader family inside `Frame state setters` (native's own
  hooks, i.e. handlers), and anything above the primitive level in the sections not yet printed
  (overlay and draw among them).
- **The UI class is ported, and the cut is by class — the owner's criterion, verbatim (2026-09-27):**
  *"the class is mostly ok up until line 611 where `InventoryBagWindow` starts, those classes we don't
  need."* On the source that is exact: Reforged's `UIManager.py` (1302 lines) is **`class UIManager`,
  lines 29-618, 53 methods** — ported — then **14 window classes, lines 619-1302, 56 methods**
  (`InventoryBagWindow`, `InventoryBagsWindow`, `XunlaiStorageWindow`, `SkillTrainerWindow`,
  `TraderWindow`, `MerchantWindow`, `CollectorWindow`, `CrafterWindow`, `UpgradeWindow`,
  `SalvageOptionsWindow`, `SalvageConfirmationPopup`, `LesserSalvageWindow`,
  `ExpertSalvageUnidentifiedWindow`, `AnySalvageWindow`) — **not ported**. No singleton instance and no
  handler class is added beside it, and **no per-widget class at all** (*"not even the class that handles
  them"*). **The class's surface, pinned from the source (2026-09-27): 55 declarations, lines 43-618** — every one
below is a `def` in `class UIManager`, in the source's own order, with the ``PyUIManager.UIManager`` member
it wraps where the body is a one-liner over the binding:

`RegisterFrameIOEventCallback` (43), `UnregisterFrameIOEventCallback` (53), `_UpdateFrameIOEvents` (66),
`_add_event` (92, nested), `GetIOEventsForFrame` (132), `RegisterFrameIOCallbacks` (146) — **the frame-IO
event family: not wrappers**; `GetFrameLogs`→`get_frame_logs` (161), `ClearFrameLogs` (170),
`GetUIMessageLogs` (177), `ClearUIMessageLogs` (186), `GetTextLanguage` (194), `SendUIMessage` (199),
`SendUIMessageRaw` (203), `DrawOnCompass` (208), `LoadSettings` (212), `GetSettings` (216),
`GetCurrentTooltipAddress` (220), `IsWorldMapShowing` (237), `IsUIDrawn` (246), `AsyncDecodeStr` (250),
`IsValidEncStr` (254), `IsValidEncBytes` (258), `UInt32ToEncStr` (262), `EncStrToUInt32` (266),
`SetOpenLinks` (270), `IsShiftScreenshot` (274), `GetFPSLimit` (283), `SetFPSLimit` (292),
`GetPreferenceOptions` (302), `GetEnumPreference` (306), `GetIntPreference` (310), `GetStringPreference`
(314), `GetBoolPreference` (318), `SetEnumPreference` (322), `SetIntPreference` (326),
`SetStringPreference` (330), `SetBoolPreference` (334), `GetKeyMappings` (338), `SetKeyMappings` (342),
`Keydown` (346), `Keyup` (350), `Keypress` (354), `GetWindoPosition` (358 — the source's own spelling),
`IsWindowVisible` (367), `SetWindowVisible` (376), `SetWindowPosition` (386) — **plain wrappers**;
`IsLockedChestWindowVisible` (397), `IsNPCDialogVisible` (407), `FindDialogOffset` (416),
`GetDialogButtons` (457), `_is_button` (466, nested), `ClickDialogButton` (494), `GetDialogButtonCount`
(516), `GetDialogButtonFrames` (536), `ConfirmMaxAmountDialog` (598) — **the dialog family: frames walked
and a button clicked, which this port already does with `Frame`/`FrameTree` and the live-verified
`Frame.click`**.

The port is written in that order, each member the source's own body: the wrapper group resolves its
binding member to the `ui::` function behind it (`ui_bindings.cpp` → `ui_methods.cpp`), and the two
non-wrapper families are ported as the source writes them — the frame-IO events over Reforged's own
mechanism, the dialog members over `Frame`/`FrameTree`.

### The action members are game-thread enqueues — and that is one feature, not fourteen

`mouse_action`, `mouse_click_action`, `send_message`, `send_message_text`, `set_text` and `title`
(`:1273-1321`) are the first members that *act* on the client rather than read it. Resolving each binding
showed a single shape: **native runs every one of them through `GW::game_thread::Enqueue`**, so the work
happens on the client's own thread.

**`send_message` and `click` are built (rounds 58-59), and between them they settled that shape for the
whole group.** The client's own callbacks-based sender is resolved (`ui.send_frame_ui_message_func`, native's
`g_send_frame_ui_message_original`) and called with `CallForm.FASTCALL_U32_U32_U32` — `&frame->frame_callbacks`
in **ECX**, the dummy second word in EDX, and the message plus two caller words on the stack. That is the
client's own `__thiscall` method, which Native declares `void(__fastcall*)(callbacks, void* edx, message_id,
wparam, lparam)` for its detour ABI (`ui_patterns.cpp:32`): the live read of the resolved function shows
`mov edi, ecx` and `ret 0xc`, so the first word is `this` and the callee pops its three words. A five-word
cdecl call — what round 58 first wrote, from Native's declaration read as a plain argument list — would have
put the callbacks pointer on the stack and taken the host's frame apart. `click` then uses it for
`ui::ButtonClick`: both `IsCreated` checks, the `MouseAction`/`ButtonParam` pair in the block's data region,
and `kMouseClick2` sent to the **parent's** callbacks. Both were driven against the live client in round 59 —
the click on a real dialog button advanced the dialog. The rest of the group still names its call.

| binding | what the enqueue does |
| --- | --- |
| `test_mouse_action` / `test_mouse_click_action` (`ui_bindings.cpp:1093-1103`) | `ui::TestMouseAction` / `ui::TestMouseClickAction(frame_id, current_state, wparam, lparam)` — the frame **id**, not a pointer |
| `SendFrameUIMessage` (`:1066-1071`) | `ui::SendFrameUIMessage(GetFrameById(fid), message, wparam, lparam)`, which requires a non-empty callback array and then calls the client's own `g_send_frame_ui_message_original(&frame->frame_callbacks, nullptr, message_id, wparam, lparam)` (`ui_methods.cpp:1332-1352`) — **five** words, the first an address *inside* the frame record, which the port declares at `0xA8` |
| `SendFrameUIMessageWString` (`:1073-1078`) | the same call carrying a wide string |
| `set_text_label_by_frame_id` (`:1447-1452`) | sets the encoded label on the `TextLabelFrame` — a write |
| `set_frame_visible_by_frame_id` (`:833-837`) | `ui::SetFrameVisible(frame, flag)` = `frame->frame_state &= ~0x200u` (or sets it) (`ui_methods.cpp:1739`) — a record write; `SetFrameLayer` is `frame->field10_0x28 = layer` (`:654-660`) |
| `button_click` (`:1080-1084`) | `ui::ButtonClick(frame)` (`ui_methods.cpp:1249+`): frame and parent must be `IsCreated()`, then a `packet::MouseAction{frame_id, child_offset_id}` and a `ButtonParam{unk, wparam, lparam}` go out through the parent |

The port's `py4gw/game_thread` layer **is** the analogue of that enqueue, and the vocabulary already carries
the five-word form the message send needs — so this is one feature (game-thread frame actions) rather than
fourteen members, and it is recorded as one item in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md). The members are declared and name it; the source's own
`is_usable` guard still runs first, so an unusable frame returns without an action, exactly as written.

**The two label reads needed none of it.** `text()` and `encoded()` (`:1294-1308`) bind
`get_text_label_decoded_by_frame_id` / `get_text_label_encoded_by_frame_id`, which native resolves as
`FrameAs<TextLabelFrame>(frame_id)` plus `SafeWide(label->GetDecodedLabel())` / `GetEncodedLabel()`
(`ui_bindings.cpp:1439-1446`) — and this port already performs exactly that read in
`FrameArray.decoded_label` / `encoded_label` (`py4gw/ui/frame.py:605`, `621`). Both members answer from the
port's own reader. The geometry that follows (`position`, `rect`, `size`, `coords`, `viewport_scale`,
`viewport_dimensions`, `:1324-1413`) reads the position struct and needed nothing new; `coords`/`rect`/`size`
therefore answer today, while `content_coords` — which needs `FrameTree.viewport_height()` → `root()` → the
client's root frame — is the next member and is not ported yet.

### Correction: the source's `position` is a wrapper, and three geometry members had to be re-pointed

**Found by tracing the binding after the members were written (2026-09-27), and corrected here.** The first
cut of `rect`, `size` and `viewport_scale` read `left_on_screen` / `top_on_screen` / `width_on_screen` /
`viewport_scale_x` / `viewport_scale_y` off `self.position` — the source's own field names, and wrong for this
port in two ways:

1. **This port's `position` is the raw record.** ``PyUIManager.UIFrame.position`` in Reforged is a wrapper the
   binding builds: it copies the record's fields and then, **only when the UI root exists**, computes
   `left_on_screen` / `top_on_screen` / `right_on_screen` / `bottom_on_screen` from
   `frame->position.GetTopLeftOnScreen(root)` / `GetBottomRightOnScreen(root)`, `width_on_screen` /
   `height_on_screen` from `GetSizeOnScreen(root)`, and `viewport_scale_x` / `viewport_scale_y` from
   `GetViewportScale(root)` (`ui_bindings.cpp:445-462`). The port's `FrameState.position` is the
   `FramePosition` record itself (`py4gw/ui/frame.py:65-87`), and that record **has no such field**.
2. **The tests could not catch it, because the fixture was built from the source's names too.** The fake
   position object was given `left_on_screen` and `viewport_scale_x` to match the source's field list, so the
   members passed against a shape no record has.

So `rect`, `size` and `viewport_scale` now **name the computation they need** (the wrapper's four methods,
which take the root frame, and for the scale the render context — the entry in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md)), and the tests were rebuilt on the **real** ctypes records:
`tests/test_frame_tree_frame_offline.py`'s `TestFrameRecordReadsOffline` constructs an actual `FrameStruct` /
`FramePositionStruct` and asserts both that the fields the port now reads are there and that the wrapper's
names are **not** — a fixture cannot hide that class of error again. `coords` keeps the source's body: zeros
for a frame that is absent, `rect` behind it for one that is present.

**What the raw record does answer** is now ported and tested: `position_ex` (`screen_left`, `screen_bottom`,
`screen_right - screen_left`, `screen_top - screen_bottom`, `flags`), `native_size` (the same width and
height), `viewport_dimensions` (`viewport_width` / `viewport_height`), and `min_size` / `client_border` —
which native reads as floats at `frame + 0x50`‑`0x64` by **reinterpretation** (`ui_methods.cpp:680-702`), the
same reinterpretation the members perform on this port's `field20_0x50` … `field24a_0x64` words.

The navigation that follows (`:1476-1515`) needed nothing: `parent`, `children`, `child_codes`, `child` and
`find_child` are the tree snapshot's own walk, and they are ported.

### The native walkers: two pointer rules, and five bindings over one function

The navigation members that read the *client* rather than the snapshot (`:1482-1588`) all rest on two rules
that native's own code states:

1. **`FrameRelation::GetParent()` is the stored word minus an offset** (`ui_methods.cpp:414-416`): the
   `relation.parent` field points at the **parent's relation member**, not at the parent record, so
   ``parent_frame = relation.parent - FrameStruct.relation.offset`` and the parent's frame id is one word read
   at ``relation.parent - relation.offset + FrameStruct.frame_id.offset``. Both offsets are already declared
   here (`py4gw/ui/frame.py:300-303`). One step up the chain then costs **one word read at the current
   relation pointer**, because a record's relation address is the record's own address plus the relation
   offset.
2. **The parent test compares relation pointers.** ``candidate.relation.GetParent() == frame`` (`:485`, `:515`)
   is ``candidate.relation.parent == this_frame_address + relation.offset``, so a walk needs the address each
   record was read from — which the port already binds (`FrameArray.get` / `iter_frames`,
   `py4gw/ui/frame.py:518`, `:525`).

With those two rules, ten members become reads and are ported and tested against **real records bound to
addresses**: `parent_id_native` and `parent_direct` (`GetParentFrameId`, `:1813-1819`), `child_with_hash` and
`child_named` (`GetChildFromNameHash`, `:609-621`), `first_child`, `last_child`, `next_sibling`,
`prev_sibling` and `related` (`GetRelatedFrameById`, `:465-533`), and `is_ancestor_of` (`IsAncestorOf`,
`:662-675`).

**One deliberate choice, recorded here.** The source's five relation members each call a *different* binding
(`get_first_child_frame_id`, `get_last_child_frame_id`, `get_next_child_frame_id`,
`get_prev_child_frame_id`, `get_related_frame_id`), and all five bindings are thin wrappers over the **same**
native function, `GetRelatedFrameById`. The port therefore reproduces that walk **in each of the five
members** rather than adding a helper the sources do not have — the same choice `anchor_ids` / `by_hash` made
for the hash read, and the walk is documented once, in the comment above them, where the tree's snapshot
walkers end. Its four branches differ in exactly two ways: whether the comparison is against this frame's
child codes or a start frame's, and whether the winner is the smallest or the largest offset.

The rest of the navigation names its requirement: `child_native` and `child_path_native` go through the
client's own `g_get_child_frame_id_func` (`ui_methods.cpp:435-441`, `:589-607`) — a call, not an array read —
while `item`, `tab` and `io_events` name `GetOrderedChildFrameId` (`ui_bindings.cpp:758`),
`TabsFrame::GetTabFrameId` (`:1523-1527`) and Reforged's unported `UIManager.py` (`frame.py:1594`).

### The tree's queries finish — and its order is corrected to the source's

With `Frame` declared, the eight members that were blocked on the class existing are ported (`:517-636`):
`all_frames`, `_as_id`, `descendants`, `descendants_of`, `frames_at_path`, `frames_under` and `_frames_at` are
snapshot walks over `_order`/`_parent`/`_code`/`children_map`, and `sort_by_vertical` sorts by `Frame.rect[1]`
— so it raises exactly where `rect` does, and **the dependency names itself** rather than the member failing
obscurely.

**A structural correction came with them.** The port had grown its query section *above* the per-frame live
copy, while the source puts `state`/`_prune`/`invalidate` (`:378-423`) **before** the queries (`:426` onward).
One three-member move fixed the whole class, and both `_FrameTree`'s and `Frame`'s members now appear in the
source's order — verified by comparing the port's AST against the source's, not by reading. That check is what
caught the deviation; it is the same check that caught a duplicated member in `Frame` the round before, and it
is now the first thing run after any structural edit here.

### What the last geometry members actually wait on

Tracing the four methods the wrapper uses settles why `rect`, `size`, `viewport_scale` and `content_coords`
cannot answer from the record (`include/GW/ui/ui.h:498-533`):

```cpp
inline GW::Vec2f FramePosition::GetTopLeftOnScreen(const Frame* frame) const {
    const auto viewport_scale = GetViewportScale(frame);
    const auto height = frame ? frame->position.viewport_height : viewport_height;
    return { screen_left * viewport_scale.x, (height - screen_top) * viewport_scale.y };
}
```

Three things follow. The Y flip uses **the root's** `viewport_height` (that is the `frame` argument, the root
itself). The scale is `GetViewportScale(frame)`, which divides the **render** viewport by the frame's own
viewport size — the DX context item. And the root comes from `GetRootFrame()` → `g_get_root_frame_func()`
(`ui_methods.cpp:415`), a **client call**. So this feature is exactly two client-side inputs — the root frame
and the render viewport — and the arithmetic between them is already written down here from the source. Both
inputs are on [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) (the root read and the `GwDxContext` capture), and
`Frame.viewport_dimensions` already answers from the record's own `viewport_width`/`viewport_height`, which is
the same value the root branch above would use when no root is passed.

### The tree's last members: three scans, one coordinate read, and four client-side inputs

With those ported, `_FrameTree`'s surface is complete (`:554-672`), and the round produced three findings
worth keeping:

1. **`hierarchy`'s docstring disagrees with the function it binds, and the function wins.** The source's
   docstring says "(frame_id, parent_id, code, hash) rows"; ``GetFrameHierarchy``
   (`ui_methods.cpp:1866-1884`) skips frames that are not valid, created **and visible**, and pushes
   ``(parent->relation.frame_hash_id, frame->relation.frame_hash_id, parent->frame_id, frame->frame_id)`` —
   parent hash, own hash, parent id, own id. Recorded here factually; the port returns what the function
   returns.
2. **`GetOverlayFrames` and `GetPopupFrames` are byte-identical bodies** (`:622-634`, `:636-648`): valid and
   *created* frames, in array order. Two bindings, one function — as with `label`/`title` and
   `set_visible`/`show`. The port keeps each member's own scan rather than adding a shared helper the sources
   do not have.
3. **`coords_for_hash` is a hash lookup plus two corner pairs**: ``GetFrameIDByHash`` (the scan `by_hash`
   makes, hash `0` answering nothing) and then ``(screen_left, screen_top)``, ``(screen_right,
   screen_bottom)``, each word **cast to `uint32_t`** — a truncating cast the port reproduces.

The four that remain name a client-side input: `root` the client's `g_get_root_frame_func`,
`child_by_parent_hash` its `g_get_child_frame_id_func`, and `overlay`/`color_frames` the injected
`PyOverlay` manager (`FrameTree.overlay`, `:669-672`, which every drawing member goes through).

## 3. Then the salvage-choice dialog

Seventeen of `Inventory`'s 21 raising members are gated on this package and nothing else; the other four are
documented divergences rather than work (three generators over Reforged's per-frame coroutine driver, one
logging through the injected console). See [`ITEM_PORT.md`](ITEM_PORT.md).

## 4. The native surface behind the actions

`Frame.click` and the mouse members dispatch to frames, and where they dispatch is a native UI function:
`ui::ButtonClick` → `SendFrameUIMessage` (`ui_methods.cpp:1249-1274`, `1332`) in Native, and
`ui::GetFrameByLabel` / `ui::GetFrameById` / `ui::GetChildFrame` for the lookups. This port's call
vocabulary already carries the packed UI-message form those needs, and the catalog carries the `ui`
resolvers the ported modules use; **which resolver each action needs, and whether it is present, is
established when `frame.py` is ported** — recorded here as the open question rather than guessed at now.

## 5. Round 90: the label lookup, the child walk, and one wrong word

**Three members landed, and they were the last bodies `Party.ReturnToOutpost` was waiting on**
(`party_methods.cpp:119-121`, ``return ui::ButtonClick(ui::GetChildFrame(ui::GetFrameByLabel(L"DlgRedirect"), 0));``).

| member | what it now does |
| --- | --- |
| `_FrameTree.hash_for_label` (`:587-588`) | ``PyUIManager.UIManager.get_hash_by_label`` → ``GW::ui::GetHashByLabel`` (`ui_methods.cpp:542-546`), i.e. ``g_create_hash_from_wchar_func(label, -1)``: the label is placed in the block's data region as UTF-16 code units with the terminator (`std::wstring::c_str()`'s), its address passed, and the client's answer read from the **return register**. Native's own guard — an unresolvable function or a missing label answers `0` — is kept |
| `_FrameTree.by_label` (`:583-585`) | ``get_frame_id_by_label`` → ``GetFrameIDByLabel`` (`:570-573`) → ``GetFrameByLabel`` (`:556-568`): the hash, then native's **own loop** over the frame array for the first valid frame whose ``relation.frame_hash_id`` matches. The source writes that loop twice (once for the label form, once for ``GetFrameIDByHash``), so the port keeps this member's own copy rather than delegating to `by_hash` |
| `Frame.child_native` (`:1517-1521`) | ``get_child_frame_by_frame_id`` (`ui_bindings.cpp:707-710`) = ``GetChildFrame(GetFrameById(parent_frame_id), child_offset)``: the port's ``FrameArray.get`` answers native's ``GetFrameById`` (out-of-range, null and the deleted sentinel are all ``None``, i.e. ``nullptr``), and ``GetChildFrame`` (`:444-449`) refuses a null parent, otherwise calling ``g_get_child_frame_id_func(parent->frame_id, child_offset)`` once |

**No new mechanism was needed for any of them**, which is what round 65 established when it corrected this
project's own record: ``ConnectedClient.bridge.write_data`` places arbitrary bytes **inside the client** and
answers their address, which is exactly what a pointer argument needs. The two steps the client is asked for
are ``ui.create_hash_from_wchar_func`` and ``ui.get_child_frame_id_func``, both already in the catalog and
both already driven by ``UIManager.Keydown``'s button-action frame (``py4gw/ui_manager.py``).

**The label's region is the gap between the UI payload and the map travel words (``0xE40``, 192 bytes).**
The first choice was ``0x340``, right after the click's two structs — and the block-region guard in
``tests/test_map_offline.py`` refused it: ``0x340`` is inside ``chat.LOG_MESSAGE_OFFSET``'s
``0x200..0x600`` span. The guard caught what a reading of one module's constants would not.

### The defect: `_FrameTree.root` read the status word

`root` (`:554-560`) is ``PyUIManager.UIManager.get_root_frame_id()`` → ``ui::GetRootFrame``
(`ui_methods.cpp:415-417`), and the port drives it with the catalog's ``ui.get_root_frame_func``. It read
``record.result`` — the **command's own status code** — where the callee's return register lives in
``record.value`` (``payload._capture_return``: *"Store the callee's `eax` in the command's `value` word"*).
So the member resolved the root from a status word: it answered ``Frame.from_id(0)`` on a fresh tree and the
last cached id afterwards, and ``viewport_height`` — which reads through it — was along for the ride.

**It survived because its test fixture encoded the same mistake**: ``_CallRecord`` carried one word and the
test read it, so member and fixture agreed with each other and neither with the dispatcher. The fixture now
models **both** words (``value`` the return, ``result`` the status), which is the part that matters: a
member reading the wrong one cannot pass any more, and a second test pins that a **nonzero status** (a
refused command) does not replace the return it carries. Every other caller in this port already read
``.value`` — ``dat_reader``, ``ui/preferences``, ``ui_manager``, ``memory_manager``, ``dialog`` — and the
DAT read is live-verified, so the convention was never in doubt; this one member was simply wrong.

### The divergence: `Frame.click` answers native's bool

``ui::ButtonClick`` ends ``return SendFrameUIMessage(parent_frame, kMouseClick2, &action);``
(`ui_methods.cpp:1273`), so it answers ``false`` for a frame or parent that is not created and for a parent
with no callbacks (``SendFrameUIMessage``'s guard, `:1332-1335`), and ``true`` once the client has been
handed the action. Reforged's ``Frame.click`` is declared ``-> None`` (`FrameTree/frame.py:1260`) and the
port matched that — until round 90, where a real consumer appeared:
``GW::party::return_to_outpost`` returns that bool and Reforged's ``Party.ReturnToOutpost`` passes it on
(``Party.py:388``). An external port has no in-process ``PyParty`` to reach, so the value has to come from
the click, and the port's click **is** ``ui::ButtonClick``'s body.

So ``Frame.click`` now returns it. That is a **recorded divergence from Reforged's wrapper**, and its blast
radius was checked rather than assumed: every other caller in this port discards the answer (``Map``'s
cancel/confirm buttons, ``Inventory``'s salvage dialog, ``UIManager.ClickDialogButton``). The guard
``is_usable`` is Reforged's own and stays ahead of native's, so a created-but-hidden frame answers ``false``
where native's own ``ButtonClick`` would have clicked — that ordering is this member's pre-existing shape and
is unchanged.
