# The item port: `Item`, `ItemArray`, `Inventory`

**Status: steps 1, 1a, 2, 3, 4, 4a, 5 and 6 are ported — `enums_src/item_enums.py`,
`enums_src/model_enums.py`, `mods_types.py`, `mods_upgrades.py`, `mods_core.py`, `item.py` (**FULL**),
`item_array.py` (**FULL**), `py_inventory.py` (the bag surface and the action surface: 15 of 17
`PyInventory` members built and 3 of its 4 module functions, the 2 that raise naming the piece each needs)
and `py4gw/inventory.py` (66 members: 53 built, the 4 that raise documented divergences).** This doc is
the order of work and the exact surface, so the port cannot drift from the sources. Findings recorded
while porting are in § 3a.

**Sources.** `Py4GW_Reforged/Py4GWCoreLib/Item.py` (827 lines), `ItemArray.py` (212 lines),
`Inventory.py` (1477 lines), over `Py4GW_Reforged_Native`'s item module: `item_bindings.cpp`,
`inventory_bindings.cpp`, `item_methods.cpp`, `include/GW/item/item.h`, `include/GW/context/item.h`,
`src/GW/context/item.cpp`, `item_patterns.cpp`, `offsets/item.json`, and the Python stubs that
declare `PyItem`/`PyInventory`.

**What is already here.** `py4gw/context/item_context.py` reads the client's item context: the
``Item`` (0x54), ``Bag`` (0x28), ``Inventory`` (0x98), ``ItemModifier`` (0x04) and
``ItemContext`` (0x10C) records, the bag/item walks, the modifier array, and native's
``item::GetItemById``. The ported classes are the layer above it, and they are what this doc is about.

---

## 1. The exact surface (counted from the sources, member by member)

### `Item.py` — 122 members

| scope | lines | members | what they are |
| --- | --- | --- | --- |
| `class Bag(Enum)` | 13-37 | **24** | the bag ids `NoBag = 0` … `Max = 23` (enum members) |
| `class Item` (direct) | 40-689 | **23** | 17 staticmethods + 6 nested namespaces (`Mods`, `Rarity`, `Properties`, `Type`, `Usage`, `Dye`) |
| `Item.Mods` | 45-215 | **22** | 1 class attribute (`Slot = mods_core.Slot`) + 21 staticmethods |
| `Item.Rarity` | 366-400 | **6** | `GetRarity` + `IsWhite`/`IsBlue`/`IsPurple`/`IsGold`/`IsGreen` |
| `Item.Properties` | 402-556 | **21** | 21 staticmethods (`IsCustomized`, `GetValue`, `GetQuantity`, the seven modifier-derived readers, `IsMaxDamage`, …) |
| `Item.Type` | 558-597 | **8** | `IsWeapon`, `IsArmor`, `IsInventoryItem`, `IsStorageItem`, `IsMaterial`, `IsRareMaterial`, `IsZCoin`, `IsTome` |
| `Item.Usage` | 599-648 | **10** | `IsUsable`, `GetUses`, `IsSalvageable`, `IsMaterialSalvageable`, the four kit readers, `IsIDKit`, `IsIdentified` |
| `Item.Dye` | 650-689 | **4** | `GetInfo`, `GetColor`, `GetChannels`, `IsColor` |
| module constants | 692-711 | **3** | `SUMMONING_SICKNESS_EFFECT_ID`, `KNOWN_SUMMONING_STONE_CREATURE_MODEL_IDS`, `KNOWN_SUMMONING_STONE_CREATURE_ENC_NAMES` |
| module functions | 714-826 | **4** | `party_player_agent_ids`, `has_summoning_sickness`, `is_active_summoning_stone_ally`, `has_active_party_summon` |

The direct `Item` members in file order (source lines): `item_instance` 217, `GetAgentID` 227,
`GetAgentItemID` 232, `GetItemIdFromModelID` 237, `GetItemByAgentID` 253, `RequestName` 273,
`IsNameReady` 278, `GetName` 283, `GetItemType` 288, `IsArmorType` 293, `IsWeapon` 299,
`GetModelID` 305, `GetModelFileID` 310, `GetCompositeModelIDs` 315, `GetTrueModelFileID` 320,
`GetSlot` 341, `GetDyeColor` 346, `Rarity` 366, `Properties` 402, `Type` 558, `Usage` 599, `Dye` 650.

### `ItemArray.py` — 14 members

| scope | lines | members |
| --- | --- | --- |
| `class ItemArray` (direct) | 8-212 | **7** — `CreateBagList` 9, `GetItemArray` 28, `GetAllBags` 57, `GetBag` 75, `Filter` 93, `Manipulation` 132, `Sort` 184 |
| `ItemArray.Filter` | 93-128 | **2** — `ByAttribute` 94, `ByCondition` 117 |
| `ItemArray.Manipulation` | 132-182 | **3** — `Merge` 133, `Subtract` 150, `Intersect` 167 |
| `ItemArray.Sort` | 184-211 | **2** — `SortByAttribute` 185, `SortByCondition` 200 |

### `Inventory.py` — 66 members

| scope | lines | members |
| --- | --- | --- |
| `class Inventory` | 43-1471 | **66** — 9 class attributes (44-52) + 57 staticmethods |
| `VisibleFrameEntry(TypedDict)` | 12-22 | 10 fields |
| `SalvageChoiceEntry(VisibleFrameEntry, total=False)` | 25-32 | 7 optional fields |
| `SalvageChoiceOptionSource(TypedDict)` | 35-40 | 5 fields |

The 57 staticmethods in file order, with the group each belongs to:

| group | members | lines |
| --- | --- | --- |
| **the binding** | `inventory_instance` | 54 |
| **space and counts** | `GetInventorySpace`, `GetStorageSpace`, `GetZeroFilledStorageArray`, `GetFreeSlotCount`, `GetItemCount`, `GetModelCount`, `GetModelCountInStorage`, `GetModelCountInMaterialStorage`, `GetModelCountInEquipped` | 58-236 |
| **"first" finders** | `GetFirstIDKit`, `GetFirstUnidentifiedItem`, `GetFirstSalvageKit`, `GetFirstSalvageableItem` | 238-306 |
| **identify / salvage** | `IdentifyItem`, `IdentifyFirst`, `SalvageItem`, `SalvageFirst` | 309-388 |
| **the salvage-choice dialog** | `AcceptSalvageMaterialsWindow`, `_frame_by_alias`, `_get_all_child_frame_ids_from_frame_id`, `_salvage_material_confirm_yes`, `IsSalvageChoiceMaterialConfirmVisible`, `_salvage_dialog`, `_salvage_option_container`, `_salvage_confirm`, `IsSalvageChoiceDialogVisible`, `_build_frame_children_map`, `_build_visible_frame_entry_map`, `_collect_frame_text`, `_collect_salvage_choice_option_text`, `_collect_visible_frame_subtree_entries`, `_pick_salvage_choice_click_entry`, `_get_salvage_choice_dialog_options`, `_choose_salvage_choice_dialog_option`, `_salvage_choice_debug_log`, `_format_salvage_choice_option`, `HandleSalvageChoiceMaterialConfirmDialog`, `_wait_for_salvage_choice_dialog_close`, `HandleSalvageChoiceDialog` | 392-1160 |
| **storage window** | `OpenXunlaiWindow`, `IsStorageOpen` | 1162-1177 |
| **item actions** | `PickUpItem`, `DropItem`, `EquipItem`, `UseItem`, `DestroyItem`, `GetHoveredItemID` | 1179-1239 |
| **gold** | `GetGoldOnCharacter`, `GetGoldInStorage`, `DepositGold`, `WithdrawGold`, `DropGold` | 1241-1287 |
| **move / find / storage** | `MoveItem`, `FindItemBagAndSlot`, `DepositItemToStorage`, `WithdrawItemFromStorage` | 1289-1471 |

The 9 class attributes (44-52) are the salvage dialog's frame labels — `SALVAGE_CHOICE_DIALOG_LABEL
= "Salvage Window"`, `SALVAGE_CHOICE_OPTION_CONTAINER_LABEL = "Salvage Window.Options"`,
`SALVAGE_CHOICE_CONFIRM_LABEL = "Salvage Window.Salvage Button"`,
`SALVAGE_CHOICE_MATERIAL_CONFIRM_YES_LABEL = "Salvage Materials Dialog.Yes Button"` — and five
fallback offsets/hashes of which **no member reads any** (44-52).

---

## 2. The cascade, and the order the work has to happen in

None of the three classes can be ported alone, and neither can they be ported without four
dependencies that are not ported yet. The order below is dependency-first: every step is finished
before the step that needs it, and each step is its own round with its own tests.

1. **`py4gw/enums_src/item_enums.py`** — the port of `enums_src/Item_enums.py` (449 lines).
   `Item.py` needs `ItemType` (nine members call `ItemType(...)` and `.is_weapon_type()` /
   `.is_armor_type()`), `DAMAGE_RANGES` (`Item.Properties.IsMaxDamage`, 554), and `Bags`
   (`Inventory.py:5`, used by `GetModelCountInMaterialStorage:210`,
   `WithdrawItemFromStorage:1430`). `Rarity` is imported by `Item.py:9` but **no member uses it**
   (the five rarity readers resolve the nested `Item.Rarity`) — it is ported because the source
   file declares it, and the finding is recorded.

   **Ported, and verified by a declaration-level comparison rather than by reading**
   (`tests/test_item_enums_offline.py`): the test loads the source file itself and compares the two
   modules name by name — every enum's `__members__` in order, every constant, every table including
   key order, the two `Literal` aliases and the one module-level function. An AST-level pass over the
   two files first reported `28 source declarations compared, 0 problems`.

1a. **`py4gw/enums_src/model_enums.py`** — the port of `enums_src/Model_enums.py` (3139 lines), which
   is `Item_enums`' own import (`from .Model_enums import ModelID`, used by `MaterialMap`'s 36 keys).

   **This file is the reason `enums_src/__init__.py` listed it as unported, and the reason is now
   decided.** Its line 2 is `import PySkill` and it calls `PySkill.Skill("X").id.id` **52 times**,
   all inside `SPIRIT_BUFF_MAP`. `PySkill` is native's injected-runtime module, which this port does
   not have — but the call is not a mechanism of its own: native's constructor is
   ``PySkillID(const std::string& name) : id(static_cast<int>(GW::skillbar::GetSkillIDByName(name)))``
   (`skill_bindings.cpp:29-30`), and that generated table is already ported here as
   ``GetSkillIDByName`` (`py4gw/enums_src/skill_names.py:3079`, the port of `skill_names.cpp`). So the
   port keeps every key, every string and the order of `SPIRIT_BUFF_MAP`, and reaches the same lookup
   through the ported function: one substitution, in one place, recorded in the module's docstring.
   That is the native-import site `enums_src/__init__.py` said needed deciding "one at a time" —
   `Texture_enums.py` (`import PySystem`) is the other, and it is not part of this port.
2. **`py4gw/mods_types.py`** — the port of `mods_types.py` (1230 lines): `ModifierIdentifier`
   (`ModId`; `Item.Mods.GetMods:55` and the seven modifier-derived `Item.Properties` readers) and the
   catalog types the module declares.
3. **`py4gw/mods_core.py`** — the port of `mods_core.py` (494 lines): `Slot`, `decode_item`,
   `effect_name`, `describe_item`, `raw_dump`, `value_of`, `subtype_of`, `is_better`, `upgrades_on`,
   `known_upgrades`, `slot_of_upgrade`, `upgrade_is_maxed`, `find`. `Item.Mods` is 21 of its 22
   members over these, and four `Item.Properties` readers use `find`/`value_of`/`subtype_of`.
   The decoder reads the item's modifier words, which this port already has:
   `context/item_context.py`'s `ItemModifierStruct` (`identifier`, `arg1`, `arg2`, `arg`) and
   `ItemStruct.read_modifiers()`.
4. **`py4gw/item.py`** — **ported (2026-09-27)**: `Bag` (24), `Item` (23 direct: 17 static methods and
   the six nested namespaces, 22 + 6 + 21 + 8 + 10 + 4 members inside them), the three constants and
   the four module functions — 125 declarations in all, and the AST test in
   `tests/test_item_offline.py` compares every one of them against the source's own tree, nesting and
   decorators: nothing missing, and the port's only additions are the seven names of the binding it
   carries.

   **The binding is carried in the module.** Every `Item` member reads through `PyItem.PyItem(item_id)`
   — Native's binding class (`item_bindings.cpp:210-380`, bound at `:427-486`) — and this port defines it
   as `PyItem` here, the same answer `effect.py` gives for `PyEffects.PyEffects`, since `mods_core`
   needs the item's words before `Item.py` exists (it reaches them through the item context instead,
   which is recorded on it). `PyItem.GetContext` copies the same fields from the same record, with the
   record's own methods deciding the derived flags, and native's map gate becomes the ported
   `Map.IsMapReady()` — how `dialog.py` and `skillbar.py` already express that identical condition.

   **Two members still raise, and the reason is not a missing capability of this port but the next
   step's decision**: `GetItemIdFromModelID` and `GetItemByAgentID` walk four bags through native's
   `PyInventory.Bag.GetItems()`, and the two sources disagree about what that yields — native's binding
   returns `dict`s (`inventory_bindings.cpp:50-66`), Reforged's `Item` reads `item.item_id` off each
   element and its stub declares `List[PyItem]`. That is the Inventory step's question, so they raise
   naming it rather than guessing.

4a. **`py4gw/py_inventory.py`** — **ported (2026-09-27)**: Native's ``PyInventory`` module
   (`inventory_bindings.cpp`, 216 lines) — the bag surface, and where the two classes still to come get
   their bags from. It is a module of its own because in both sources it *is* one, and because three
   ported modules need it while `Inventory.py` imports `ItemArray`, so hosting it in either would make
   the import a cycle.

   **`Bag`** is complete: the seven fields, `GetContext`, `GetSize`, `GetItemCount` (the copied field,
   not a fresh read) and `GetItems`. **The shape decision, and it comes from Reforged**: native's
   `GetItems` builds ``dict``s, but Reforged's Python reads **attributes** off each element
   (``item.item_id`` in `ItemArray.py:49` and `Item.py:245,265`, ``item.slot`` in `Inventory.py:1396`)
   and its stub declares ``List[PyItem]`` — so this port's `GetItems` answers
   :class:`~py4gw.item.PyItem` objects, which carry every field native's dict carries. The dict shape is
   kept where the source keeps it: the module's ``get_bag`` snapshot.

   **`PyInventory`**: 10 of its 17 members answer — `GetIsStorageOpen`, `GetGoldAmount`,
   `GetGoldAmountInStorage`, `GetHoveredItemID` (the port of `GW::item::GetHoveredItem`, whose payload
   is a ``uint32_t*``, so its ``payload[1]``/``payload[2]`` are words: ``{item_id, 0xff}`` or
   ``{item_id, item_id, 0xff}``), `PickUpItem` (the `kSendInteractItem` message with the
   ``kInteractAgent`` packet the port's UI-message form carries), `DropItem`, `DestroyItem`, and the gold
   three with the methods layer's own limits, clamps and `ChangeGold` verification.

   **The seven that raise name four distinct missing pieces, and two of them are work items this port
   owns:** a **four-word call form** (native's `item.move_item_func` takes item id, quantity, bag index
   and slot; this port's forms stop at three words — `client.call_function` already takes five words, so
   the dispatcher form is what is missing), the **current map record's `region` field** (the interact
   guard `CanInteractWithItem` → `CanAccessXunlaiChest`, `item_methods.cpp:57-62`, which gates `UseItem`,
   `EquipItem`, `IdentifyItem`, `Salvage` and the module's `salvage`), a **StoC path**
   (`OpenXunlaiWindow` emulates a `DataWindow` packet) and a **frame-click path**
   (`AcceptSalvageWindow`, child 6.0x62.6 of the frame labelled "Game").

4b. **`item.py` is FULL.** Its last two members — `GetItemIdFromModelID` and `GetItemByAgentID` — walk
   four bags through this module's `Bag.GetItems()` and answer now, so the class has no raising member
   left and the AST test pins the whole surface.

   **One source quirk is pinned by that test**: `Item.Mods.ModifierExists` and `GetModifierValues`
   compare the binding's `GetIdentifier()` (`mod >> 16`) with the identifier the caller passes, while the
   decoder reads `(mod >> 16) >> 4` — a factor of sixteen apart, so those two members match only the
   binding's spelling of the identifier (`0x27A0` for the test's Damage word), never `ModId.Damage`
   (`0x27A`). The port keeps the source's comparison as it is.
5. **`py4gw/item_array.py`** — **ported (2026-09-27), FULL**: 14 declarations (`CreateBagList`,
   `GetItemArray`, `GetAllBags`, `GetBag` and the three nested namespaces `Filter` 2, `Manipulation` 3,
   `Sort` 2), AST-compared against the source name for name and nesting for nesting. It reads through the
   bag surface step 4a supplies, so `GetItemArray` answers `PyItem`s' ids.

   **Two adaptations, both recorded in the module:** the `@frame_cache` on `GetItemArray`, `GetAllBags`
   and `GetBag` is dropped — no frame loop to key a memo to, so the member reads when it is called (the
   test asserts the decorator is gone on exactly those three and nowhere else) — and the two
   `PySystem.Console.Log` calls have nowhere to go, so the source's **control flow** is kept (an invalid
   id is dropped, a bag that raises is skipped) and nothing is printed in the log's place.

   **Two source quirks, pinned by tests rather than tidied:** `GetBag` cannot answer a bag at all — an
   `int` makes `GetItemArray([bag])` come back empty (it reads `.value` off the argument) and a `Bag`
   member makes `PyInventory.Bag(bag, ...)` raise inside the source's own `except` — and the dotted
   attribute names the source's own docstrings pass to `Filter.ByAttribute`/`Sort.SortByAttribute`
   (`'Properties.GetValue'`) are not attributes of `Item`, because `getattr` does not walk the dot, so
   the filter excludes everything and the sort raises the source's own `ValueError`.
6. **`py4gw/inventory.py`** — the port of `Inventory.py`: the three TypedDicts, the nine class
   attributes, and the 57 staticmethods, in the source's order and grouping.

**The native bindings are part of the work, not a stand-in.** `PyItem.PyItem` (98 bound names) and
`PyInventory.PyInventory` / `PyInventory.Bag` (32 bound names) are what the three classes call; they
are ported the way `PyEffects` was — as the class in the ported module, over native's own method
layer (`item_methods.cpp`, `inventory_bindings.cpp`) and the context this port already reads. Native's
inventory methods are the ones that **act** (identify, salvage, move, equip, use, destroy, gold,
storage), so they are calls into the client's own functions and belong on the capability layer's call
path, exactly as `Effects.DropBuff` and `Effects.ApplyDrunkEffect` do.

---

## 3. What each group will need, stated before the work starts

| group | what it needs | state |
| --- | --- | --- |
| bag and item walks, counts, quantities, types, rarity, value, slot, agent id | the ports of steps 1-5 over `context/item_context.py` | work, no unknown |
| every modifier-derived reader (`Item.Mods`, `GetRequirement`, `GetDamage`, `GetArmor`, `GetShieldArmor`, `GetEnergy`, `IsMaxDamage`, `GetDyeColor`) | `mods_core` + `mods_types` (steps 2-3) | work, no unknown |
| `Item.GetName` / `RequestName` / `IsNameReady` | native's `PyItem` name binding. `Agent.GetNameByID` is already ported through the client's own decoder (`py4gw/ui/async_decode.py`), and native's item name path is the same `AsyncDecodeStr` route over the item's `name_enc`/`complete_name_enc` fields — to be confirmed against `item_methods.cpp` when this member is written | work, mechanism exists |
| `Item.GetCompositeModelIDs` / `GetTrueModelFileID` | native's composite-model lookup (`item.composite_model_info_array`, already resolved by `context/item_context.py`) | work, resolver exists |
| item actions (`PickUpItem`, `DropItem`, `EquipItem`, `UseItem`, `DestroyItem`, `MoveItem`, gold, identify, salvage) | native's inventory methods as calls on the client's thread — the port's call path (`client.call_function`) plus whatever resolvers `item_patterns.cpp`/`inventory_bindings.cpp` name | work, call path exists |
| the salvage-choice dialog (22 members, 392-1160) | **the `FrameTree` package — ported**: `py4gw/frame_tree/` supplies `Frame`, `FrameTree`, `FrameId` and the lookups, and the frames' on-screen geometry answers since round 37, so **17 of the 22 are in** (14 in round 31, the option assembly and its two helpers in round 38). `Frame.click` is what `AcceptSalvageMaterialsWindow` would still reach. `ActionQueueManager` and `Routines.Yield` exist **only in Reforged** — the three generator members (`HandleSalvageChoiceMaterialConfirmDialog`, `_wait_for_salvage_choice_dialog_close`, `HandleSalvageChoiceDialog`) are Reforged's coroutine protocol, which this port's execution model has no driver for. Those three are where the port's answer has to be written down, and it is not "invent a scheduler" | **17 of 22 ported; the 3 generators are a documented divergence** |
| `PySystem.Console.Log` error lines (`ItemArray.CreateBagList:24`, `GetItemArray:53`, `IdentifyFirst:335,341`, `SalvageFirst:375,381,386`) | the port's console/`PySystem` binding | not ported; each such member's error path is called out where it is written |
| `_collect_frame_text` (503-513) | nothing — the source itself returns `""` (its body discards its parameters, and its docstring says why) | ported as the source writes it |

---

## 3a. Findings recorded while porting (rounds 56-57)

**1. The bag-type defect — found and fixed in round 56.** Native's `Bag` declares its first field as
`GW::Constants::BagType bag_type` (`include/GW/context/item.h:54`), and every predicate over it compares
`BagType` members (`:62-64`, `:139-140`). This port's `py4gw/context/item_context.py` carried those same
predicates, but the comparisons written against `bag_type` were **bag ids** — `8` (`Bags.Storage1`), `6`
(`Bags.MaterialStorage`) and `22` (`Bags.EquippedItems`), against `BagType.Storage` `4`,
`BagType.MaterialStorage` `5` and `BagType.Equipped` `2`; only `1` agreed, and only because
`Bags.Backpack` and `BagType.Inventory` are both `1`. The consequence was a wrong value, not a missing
capability: `Bag.is_storage_bag` and `is_material_storage` (the binding fields of
`inventory_bindings.cpp:37-39`, `:141-143`) answered `False` for every real storage and material-storage
bag, and `Item.is_inventory_item` (`item_bindings.cpp:302`) missed equipped items.

Fixed by porting the enum the sources name (`BagType`, `include/GW/common/constants/item.h:7-14`, its zero
member spelled `None_`, which is the sources' own Python spelling for such a member —
`enums_src/Item_enums.py:25,34,155`), giving `BagStruct`'s and `ItemStruct`'s predicates native's own
bodies, and deleting the snake_case duplicates from the two context structs: those names are the
*binding's* fields, and this port already carries them where the binding declares them (`py4gw/item.py`,
`py4gw/py_inventory.py`). Pinned by `tests/test_item_records_offline.py` (all six `BagType` values against
all five predicates, plus the id-is-not-a-type regression) and by the corrected fixture values in
`tests/test_inventory_offline.py`.

**2. Recorded, not closed: `BagStruct`'s compatibility aliases.** `bag_id_value` (a property over
`bag_id()`, whose only caller is this project's own `main.py:2873`), `unknown_0` (a property over the
native `_unknown0` field) and `items_array` (a getter/setter pair over the native `items` header, used by
two tests) exist in neither source. Closing them means `main.py` calling `bag_id()` and the tests using
the native field's own name.

**3. Recorded: `BagStruct`'s member order differs from native's.** Native declares fields (`:54-60`), then
`IsInventoryBag`/`IsStorageBag`/`IsMaterialStorage` (`:62-64`), then `npos` (`:66`), then
`find_dye`/`find1`/`find2` (`:68-70`), then `bag_id()` (`:72`). The port's three predicates sit after
`find2`. Round 56 corrected their bodies, not their place.

**4. Recorded: the same duplicate-spelling question across `ItemStruct`.** Most of the native methods
there have a snake_case property twin (`is_stackable` beside `GetIsStackable`, and so on). Round 56
removed only the two whose twin duplicated a native predicate long enough to disagree with it
(`IsInventoryItem`, `IsStorageItem`); the rest predate this review and have not been checked against
native's own names.

**5. The guard's map read — one divergence, recorded in round 57.** `GW::item::CanAccessXunlaiChest`
(`item_methods.cpp:57-62`) takes the current map record from `map::GetCurrentMapInfo()`, which is
`GetMapInfo(GetMapID())` → `Context::GetAreaInfoArray()[map_id]` (`map_methods.cpp:203-213`). This port has
no `AreaInfo` array — it is what `Map.GetUnloadedMapInfo` raises for — so `_can_access_xunlai_chest` reads
the same record through the instance-info record's own pointer
(`GWContext.InstanceInfo().GetMapInfo()`), the route Reforged's own Python uses for the *current* map
(`Map.py:690`). Both answer the same `AreaInfo` for the current map. When the array lands — its pattern and
resolver are already in `offsets/map.json` (`area_info_ref` → `area_info_addr`) — the guard can take
native's own route, and that work belongs to `Map.GetUnloadedMapInfo`, not to this module.

---

## 4. Verification plan

- **Offline, per step**: member-shape AST checks (every member of the source's surface declared, in
  the source's nesting), value checks against fixture records, and the `@frame_cache` finding
  (three `ItemArray` members read when called).
- **Live — the reads are verified (round 60: `tests/probe_items_live.py`, `tests/live_reports/items_live.json`)**:
  connected **read-only** (`game_thread=False` — no hook, no patch, no call) and walked the client's own bags.
  `ItemArray.GetAllBags()` answered **20 bags**, `GetItemArray(bags)` **342 item ids**, and `Inventory`
  cross-checked the walk: `GetInventorySpace()` `[39, 60]` with `GetFreeSlotCount()` **21** (39 + 21 = 60).
  Twelve items were described and every read agreed with the client's data (a `[29, 'Kit']` at slot 3 with
  model 5899 — the same id `GetFirstIDKit` answers — `[11, 'Materials_Zcoins']` stacks of 44 and 59, a Gold
  `[30, 'Trophy']` of quantity 2, slots 0-11, values 3…1000). The source's own finders answered what the
  character actually carries: ID kit **12374**, unidentified item **20112**, salvage kit **18957**. Two
  corrections were the *probe's*, not the port's: `Bag` members need `.value`, and **`CreateBagList()` with
  no ids is `[]` in the source's own body** (`ItemArray.py:9-26` — there is no default), so the walk passes
  `GetAllBags()`'s list.
- **`UseItem` is live-verified — the owner's own experiment (round 61, `tests/live_reports/use_item_live.json`).**
  A **Hard Apple Cider** stack (`ModelID.Hard_Apple_Cider` = `28435`, item **237**, slot 3) read **223**
  before the call and **222** after it, 0.79 s later, through two independent reads
  (`Inventory.GetModelCount` and `Item.Properties.GetQuantity`). One number proves the whole chain at once:
  `Inventory.UseItem` (``Inventory.py:1212-1220``) → `inventory_instance()` → the binding's `UseItem`
  (`inventory_bindings.cpp:90-93`) → `GW::item::UseItem` (`item_methods.cpp:114-121`) — **round 57's interact
  guard and the `item.use_item_func(item->item_id)` call, on a real item, in the client.**
- **The other three actions stay offline-verified only — the owner's call (round 60)**: no disposable items
  to spend on `IdentifyItem`/`Salvage`/`EquipItem`. The ids that would prove `IdentifyItem` are in the report
  above (kit **12374**, unidentified item **20112**).
- **Still unverified live**: the item-name decode through the client (`GetName`/`RequestName` needs the write
  connection's decode stub) and the mods decoder against a known weapon.

