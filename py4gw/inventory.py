"""Port of Reforged's ``Py4GWCoreLib/Inventory.py`` (1477 lines, 66 members).

**What the module is.** ``Inventory``: the bag-and-item convenience surface over the ``PyInventory``
binding — 9 class attributes, 57 static methods and the three ``TypedDict``s the salvage-choice dialog's
helpers are typed with. The methods fall into groups, and this file follows the source's own order:

- the binding (``inventory_instance``), space and counts (9), the four "first" finders, identify and
  salvage (4) — **ported**;
- the salvage-choice dialog (22, ``Inventory.py:392-1160``) — **fourteen ported** now that the ``FrameTree``
  package is (the frame lookups, the children map, the option text and the two entry helpers), with the
  three that need `Frame.rect`/`Frame.click` naming those features through the member they call, and the
  remaining eight as recorded below;
- the storage window (2), the item actions (6), gold (5) and move/find/storage (4) — **declared, each
  naming its work item**.

**What is ported, and how it reads.** The ported half is the source's own bodies over the ported
``ItemArray``, ``Item`` and the bag surface in ``py4gw/native_src/item/py_inventory.py``: ``GetItemArray`` supplies the
ids, ``ItemArray.Filter.ByCondition`` the selections, and ``Item.*`` the per-item answers. Every one of
those members answers.

**The one import this module had to adapt, and it is a substitution with a reason.** ``Inventory.py:5``
takes ``Bags`` from ``Py4GWCoreLib.enums_src.Item_enums`` — the declaring module — and this port imports
it from the same place (``.enums_src.item_enums``), which is a path adaptation only. Two members instead
do ``from .enums import Bags`` inside their bodies (``:76``, ``:110``): the source's ``enums.py`` is a
289-line re-export shim over ``enums_src``, and it also re-exports ``Texture_enums``/``Calendar_enums``,
neither of which this port has, so that module cannot be imported here. The port takes the name from the
module that declares it — the same class, from the same file — and records it rather than porting a shim
whose other half does not exist yet.

**The console, again.** ``IdentifyFirst`` and ``SalvageFirst`` log to ``PySystem.Console`` (``:334,340,
346,374,380,386``). No console is ported, so those members keep the source's **control flow and return
values** exactly — including ``SalvageFirst`` answering ``False`` on the path where it *acted*
(``:386-388``, the source's own behaviour, pinned by a test) — and the log lines are the part that cannot
be reproduced. Nothing is printed in their place.
"""

from __future__ import annotations

from typing import TypedDict, cast

from .enums_src.item_enums import Bags
from .frame_tree import Frame, FrameId, FrameKeyError, FrameTree
from .item import Item
from .item_array import ItemArray
from .native_src.item.py_inventory import Bag as PyInventoryBag
from .native_src.item.py_inventory import PyInventory

#: The three records the salvage-choice dialog's helpers are typed with (``Inventory.py:12-40``).


class VisibleFrameEntry(TypedDict):
    """``VisibleFrameEntry`` (``Inventory.py:12-22``)."""

    frame_id: int
    parent_id: int
    offset: int
    left: float
    top: float
    width: float
    height: float
    area: float
    template_type: int
    text: str


class SalvageChoiceEntry(VisibleFrameEntry, total=False):
    """``SalvageChoiceEntry`` (``Inventory.py:25-32``): the ten fields above, seven optional."""

    subtree_depth: int
    source_depth: int
    path: str
    path_root_frame_ids: list[int]
    group_frame_ids: list[int]
    group_size: int
    order: int


class SalvageChoiceOptionSource(TypedDict):
    """``SalvageChoiceOptionSource`` (``Inventory.py:35-40``)."""

    offset: int
    path_offsets: list[int]
    fallback_frame_id: int
    source_depth: int
    container_frame_id: int | None


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet."""

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


#: What the twenty-two salvage-choice dialog members need, named once because it is one mechanism.
_FRAME_ACTIONS = (
    "Reforged's FrameTree action surface (`Frame.from_label`, `FrameId.*`, `Frame.exists`, "
    "`Frame.click`, `Frame.mouse_action`) — this port's frame layer reads frames "
    "(`py4gw/ui/frame.py`, `py4gw/ui/frame_tree.py`) and has no click path"
)

#: What the three generator members need on top of that.
_ROUTINES = (
    _FRAME_ACTIONS
    + ", and Reforged's coroutine driver (`ActionQueueManager`, `Routines.Yield._wait_for_empty_queue`, "
    "`Routines.Yield.wait`), which this port's execution model has no dispatcher for"
)


class Inventory:
    """``Inventory`` (``Inventory.py:43-1471``), in the source's own order and grouping."""

    SALVAGE_CHOICE_DIALOG_LABEL = "Salvage Window"
    SALVAGE_CHOICE_OPTION_CONTAINER_LABEL = "Salvage Window.Options"
    SALVAGE_CHOICE_CONFIRM_LABEL = "Salvage Window.Salvage Button"
    SALVAGE_CHOICE_MATERIAL_CONFIRM_YES_LABEL = "Salvage Materials Dialog.Yes Button"
    SALVAGE_CHOICE_FALLBACK_DIALOG_HASH = 684387150
    SALVAGE_CHOICE_FALLBACK_OPTION_CONTAINER_OFFSET = 5
    SALVAGE_CHOICE_FALLBACK_CONFIRM_OFFSET = 2
    SALVAGE_CHOICE_FALLBACK_MATERIAL_CONFIRM_ROOT_OFFSET = 0
    SALVAGE_CHOICE_FALLBACK_MATERIAL_CONFIRM_YES_OFFSET = 6

    # -- the binding (``Inventory.py:54-56``) ------------------------------

    @staticmethod
    def inventory_instance():
        """``Inventory.inventory_instance`` (``Inventory.py:54-56``): a fresh binding instance."""

        return PyInventory()

    # -- space and counts (``Inventory.py:58-236``) ------------------------

    @staticmethod
    def GetInventorySpace():
        """``Inventory.GetInventorySpace`` (``Inventory.py:58-72``): bags 1, 2, 3 and 4."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)
        total_items = len(item_array)
        total_capacity = sum(
            PyInventoryBag(bag_enum.value, bag_enum.name).GetSize() for bag_enum in bags_to_check
        )

        return total_items, total_capacity

    @staticmethod
    def GetStorageSpace(Anniversary_panel=True, ExtraStoragePanes=0):
        """``Inventory.GetStorageSpace`` (``Inventory.py:74-102``).

        The source's first statement is the local import (``:76``), above its docstring; this port takes
        the same name from the module that declares it — see the module docstring.
        """

        if not Anniversary_panel:
            bags_to_check = ItemArray.CreateBagList(
                Bags.Storage1, Bags.Storage2, Bags.Storage3, Bags.Storage4
            )
        else:
            bags_to_check = ItemArray.CreateBagList(
                Bags.Storage1, Bags.Storage2, Bags.Storage3, Bags.Storage4, Bags.Storage5
            )

        item_array = ItemArray.GetItemArray(bags_to_check)

        total_items = len(item_array)

        total_capacity = sum(
            PyInventoryBag(bag_enum.value, bag_enum.name).GetSize() for bag_enum in bags_to_check
        )

        return total_items, total_capacity

    @staticmethod
    def GetZeroFilledStorageArray(Anniversary_panel=True, ExtraStoragePanes=0):
        """``Inventory.GetZeroFilledStorageArray`` (``Inventory.py:104-130``).

        A flat list of item ids by bag and slot, with ``0`` for an empty slot; a slot is only written
        when ``0 <= item.slot < size``, which is the source's own bound.
        """

        result: list[int] = []

        if not Anniversary_panel:
            bags_to_check = ItemArray.CreateBagList(
                Bags.Storage1, Bags.Storage2, Bags.Storage3, Bags.Storage4
            )
        else:
            bags_to_check = ItemArray.CreateBagList(
                Bags.Storage1, Bags.Storage2, Bags.Storage3, Bags.Storage4, Bags.Storage5
            )

        for bag_enum in bags_to_check:
            bag = PyInventoryBag(bag_enum.value, bag_enum.name)
            size = bag.GetSize()
            item_slots = [0] * size

            for item in bag.GetItems():
                if 0 <= item.slot < size:
                    item_slots[item.slot] = item.item_id

            result.extend(item_slots)

        return result

    @staticmethod
    def GetFreeSlotCount():
        """``Inventory.GetFreeSlotCount`` (``Inventory.py:136-145``): clamped at zero."""

        total_items, total_capacity = Inventory.GetInventorySpace()
        free_slots = total_capacity - total_items
        return max(free_slots, 0)

    @staticmethod
    def GetItemCount(item_id):
        """``Inventory.GetItemCount`` (``Inventory.py:147-164``): by item id, summing quantities."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)

        matching_items = ItemArray.Filter.ByCondition(item_array, lambda item: item == item_id)

        total_quantity = sum(Item.Properties.GetQuantity(item) for item in matching_items)

        return total_quantity

    @staticmethod
    def GetModelCount(model_id):
        """``Inventory.GetModelCount`` (``Inventory.py:166-182``): bags 1 to 4, by model id."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)

        matching_items = ItemArray.Filter.ByCondition(
            item_array, lambda item_id: Item.GetModelID(item_id) == model_id
        )
        total_quantity = sum(Item.Properties.GetQuantity(item_id) for item_id in matching_items)

        return total_quantity

    @staticmethod
    def GetModelCountInStorage(model_id):
        """``Inventory.GetModelCountInStorage`` (``Inventory.py:184-200``): bags 8 to 21."""

        bags_to_check = ItemArray.CreateBagList(8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21)
        item_array = ItemArray.GetItemArray(bags_to_check)

        matching_items = ItemArray.Filter.ByCondition(
            item_array, lambda item_id: Item.GetModelID(item_id) == model_id
        )
        total_quantity = sum(Item.Properties.GetQuantity(item_id) for item_id in matching_items)

        return total_quantity

    @staticmethod
    def GetModelCountInMaterialStorage(model_id):
        """``Inventory.GetModelCountInMaterialStorage`` (``Inventory.py:202-218``)."""

        bags_to_check = ItemArray.CreateBagList(Bags.MaterialStorage)
        item_array = ItemArray.GetItemArray(bags_to_check)

        matching_items = ItemArray.Filter.ByCondition(
            item_array, lambda item_id: Item.GetModelID(item_id) == model_id
        )
        total_quantity = sum(Item.Properties.GetQuantity(item_id) for item_id in matching_items)

        return total_quantity

    @staticmethod
    def GetModelCountInEquipped(model_id):
        """``Inventory.GetModelCountInEquipped`` (``Inventory.py:220-236``): bag 22."""

        bags_to_check = ItemArray.CreateBagList(22)
        item_array = ItemArray.GetItemArray(bags_to_check)

        matching_items = ItemArray.Filter.ByCondition(
            item_array, lambda item_id: Item.GetModelID(item_id) == model_id
        )
        total_quantity = sum(Item.Properties.GetQuantity(item_id) for item_id in matching_items)

        return total_quantity

    # -- the four "first" finders (``Inventory.py:238-306``) ---------------

    @staticmethod
    def GetFirstIDKit():
        """``Inventory.GetFirstIDKit`` (``Inventory.py:238-255``): the kit with the fewest uses."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)
        id_kits = ItemArray.Filter.ByCondition(item_array, Item.Usage.IsIDKit)

        if not id_kits:
            return 0
        id_kit_with_lowest_uses = min(id_kits, key=lambda item_id: Item.Usage.GetUses(item_id))

        return id_kit_with_lowest_uses

    @staticmethod
    def GetFirstUnidentifiedItem():
        """``Inventory.GetFirstUnidentifiedItem`` (``Inventory.py:258-270``)."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)

        unidentified_items = ItemArray.Filter.ByCondition(
            item_array, lambda item_id: not Item.Usage.IsIdentified(item_id)
        )

        return unidentified_items[0] if unidentified_items else 0

    @staticmethod
    def GetFirstSalvageKit(use_lesser=True):
        """``Inventory.GetFirstSalvageKit`` (``Inventory.py:272-290``): the fewest-uses kit."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)

        salvage_kits = ItemArray.Filter.ByCondition(item_array, Item.Usage.IsSalvageKit)
        if use_lesser:
            salvage_kits = ItemArray.Filter.ByCondition(
                salvage_kits, lambda item_id: Item.Usage.IsLesserKit(item_id)
            )

        if not salvage_kits:
            return 0
        salvage_kit_with_lowest_uses = min(
            salvage_kits, key=lambda item_id: Item.Usage.GetUses(item_id)
        )

        return salvage_kit_with_lowest_uses

    @staticmethod
    def GetFirstSalvageableItem():
        """``Inventory.GetFirstSalvageableItem`` (``Inventory.py:294-306``)."""

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)
        item_array = ItemArray.GetItemArray(bags_to_check)

        salvageable_items = ItemArray.Filter.ByCondition(item_array, Item.Usage.IsSalvageable)

        return salvageable_items[0] if salvageable_items else 0

    # -- identify and salvage (``Inventory.py:309-388``) -------------------

    @staticmethod
    def IdentifyItem(item_id, id_kit_id):
        """``Inventory.IdentifyItem`` (``Inventory.py:309-319``): kit first, item second."""

        inventory = PyInventory()
        inventory.IdentifyItem(id_kit_id, item_id)

    @staticmethod
    def IdentifyFirst():
        """``Inventory.IdentifyFirst`` (``Inventory.py:321-347``).

        The source logs before each guard return through ``PySystem.Console``; those logs have nowhere to
        go here (see the module docstring) and the guards and the return values are the source's own.
        """

        id_kit_id = Inventory.GetFirstIDKit()
        if id_kit_id == 0:
            return False

        unid_item_id = Inventory.GetFirstUnidentifiedItem()
        if unid_item_id == 0:
            return False

        inventory = PyInventory()
        inventory.IdentifyItem(id_kit_id, unid_item_id)
        return True

    @staticmethod
    def SalvageItem(item_id, salvage_kit_id):
        """``Inventory.SalvageItem`` (``Inventory.py:349-359``): kit first, item second."""

        inventory = PyInventory()
        inventory.Salvage(salvage_kit_id, item_id)

    @staticmethod
    def SalvageFirst():
        """``Inventory.SalvageFirst`` (``Inventory.py:361-388``).

        **The source answers ``False`` on the path where it acted** (``:386-388``): it logs the salvage it
        started and then falls through to ``return False``, while the two guard paths above it also answer
        ``False``. That is the behaviour, kept as written and pinned by a test.
        """

        salvage_kit_id = Inventory.GetFirstSalvageKit()
        if salvage_kit_id == 0:
            return False

        salvage_item_id = Inventory.GetFirstSalvageableItem()
        if salvage_item_id == 0:
            return False

        inventory = PyInventory()
        inventory.Salvage(salvage_kit_id, salvage_item_id)

        return False

    # -- the salvage-choice dialog (``Inventory.py:392-1160``) --------------

    @staticmethod
    def AcceptSalvageMaterialsWindow():
        """``Inventory.AcceptSalvageMaterialsWindow`` (``Inventory.py:392-405``).

        The source's own docstring: "Checks if the Salvage Materials Dialog frame exists and clicks it if it
        hasn't already been clicked.  Returns: bool: True if click was performed, False otherwise." — and its
        body returns nothing, which is what the code does; the `click` it makes is the game-thread action
        feature, so this member names that when it reaches it.
        """

        from .frame_tree import Frame, FrameId, FrameKeyError

        yes = Frame(FrameId.ScreenFrame.C6.SalvageMaterialsDialog.YesButton)
        if yes.exists:
            yes.click()

        #return Inventory.inventory_instance().AcceptSalvageWindow()

    @staticmethod
    def _frame_by_alias(frame_label: str):
        """``Inventory._frame_by_alias`` (``Inventory.py:407-413``).

        The source's own docstring: "Alias lookup that yields an inert handle rather than raising."
        """

        try:
            return Frame.from_label(frame_label)
        except FrameKeyError:
            return Frame.from_id(0)

    @staticmethod
    def _get_all_child_frame_ids_from_frame_id(root_frame_id: int, child_offsets: list[int]):
        """``Inventory._get_all_child_frame_ids_from_frame_id`` (``Inventory.py:415-419``)."""

        from .frame_tree import FrameTree

        return [f.frame_id for f in FrameTree.frames_under(root_frame_id, child_offsets)]

    @staticmethod
    def _salvage_material_confirm_yes():
        """``Inventory._salvage_material_confirm_yes`` (``Inventory.py:421-426``)."""

        frame = Inventory._frame_by_alias(Inventory.SALVAGE_CHOICE_MATERIAL_CONFIRM_YES_LABEL)
        if frame.exists:
            return frame
        return Frame(FrameId.SalvageWindow.OptionsWindowConfirmMaterialsWindow.Confirm)

    @staticmethod
    def IsSalvageChoiceMaterialConfirmVisible():
        """``Inventory.IsSalvageChoiceMaterialConfirmVisible`` (``Inventory.py:428-430``)."""

        return Inventory._salvage_material_confirm_yes().exists

    @staticmethod
    def _salvage_dialog():
        """``Inventory._salvage_dialog`` (``Inventory.py:432-437``)."""

        frame = Inventory._frame_by_alias(Inventory.SALVAGE_CHOICE_DIALOG_LABEL)
        if frame.exists:
            return frame
        return Frame(FrameId.SalvageWindow)

    @staticmethod
    def _salvage_option_container():
        """``Inventory._salvage_option_container`` (``Inventory.py:439-444``)."""

        frame = Inventory._frame_by_alias(Inventory.SALVAGE_CHOICE_OPTION_CONTAINER_LABEL)
        if frame.exists:
            return frame
        return Frame(FrameId.SalvageWindow.Options)

    @staticmethod
    def _salvage_confirm():
        """``Inventory._salvage_confirm`` (``Inventory.py:446-451``)."""

        frame = Inventory._frame_by_alias(Inventory.SALVAGE_CHOICE_CONFIRM_LABEL)
        if frame.exists:
            return frame
        return Frame(FrameId.SalvageWindow.Button)

    @staticmethod
    def IsSalvageChoiceDialogVisible():
        """``Inventory.IsSalvageChoiceDialogVisible`` (``Inventory.py:453-455``)."""

        return Inventory._salvage_dialog().exists

    @staticmethod
    def _build_frame_children_map():
        """``Inventory._build_frame_children_map`` (``Inventory.py:457-466``)."""

        from collections import defaultdict
        from .frame_tree import FrameTree

        children_map: dict[int, list[int]] = defaultdict(list)
        for parent_id, child_ids in FrameTree.children_map().items():
            children_map[parent_id].extend(child_ids)

        return children_map

    @staticmethod
    def _build_visible_frame_entry_map():
        """``Inventory._build_visible_frame_entry_map`` (``Inventory.py:468-501``).

        Every entry it builds carries `frame.rect`'s two numbers, so the member names the on-screen geometry
        requirement — the binding-side computation `Frame.rect`/`Frame.size` wait on — the moment it needs it.
        """

        from collections import defaultdict
        from .frame_tree import FrameTree

        visible_entries_by_parent: dict[int, list[VisibleFrameEntry]] = defaultdict(list)
        for frame in FrameTree.all_frames():
            if not frame.is_created or not frame.is_visible:
                continue

            left, top, _, _ = frame.rect
            frame_width, frame_height = frame.size
            width = float(frame_width)
            height = float(frame_height)
            if width <= 0 or height <= 0:
                continue

            visible_entries_by_parent[frame.parent_id].append({
                "frame_id": frame.frame_id,
                "parent_id": frame.parent_id,
                "offset": frame.code,
                "left": float(left),
                "top": float(top),
                "width": width,
                "height": height,
                "area": width * height,
                "template_type": frame.template_type,
                "text": "",
            })

        for child_entries in visible_entries_by_parent.values():
            child_entries.sort(key=lambda entry: (entry["offset"], entry["top"], entry["frame_id"]))

        return visible_entries_by_parent

    @staticmethod
    def _collect_frame_text(frame_id: int, children_map=None, max_depth: int = 1):
        """``Inventory._collect_frame_text`` (``Inventory.py:503-513``).

        The source's body discards its parameters and returns ``""`` — its docstring says why (decoding a
        non-text-label frame can dereference an invalid native type) — so this member answers ``""`` too.
        It is ported as written rather than as a raise, because the source itself does nothing.
        """

        _ = frame_id, children_map, max_depth
        return ""

    @staticmethod
    def _collect_salvage_choice_option_text(
        frame_ids: list[int], children_map=None, max_depth: int = 2
    ):
        """``Inventory._collect_salvage_choice_option_text`` (``Inventory.py:515-529``).

        It folds `_collect_frame_text`'s answer into one `" | "`-joined string, and that member answers `""`
        by the source's own design, so this answers `""` for the same reason the source does.
        """

        collected_text: list[str] = []
        for frame_id in frame_ids:
            frame_text = Inventory._collect_frame_text(frame_id, children_map=children_map, max_depth=max_depth)
            for text_part in frame_text.split(" | "):
                normalized_text = " ".join(text_part.split()).strip()
                if normalized_text and normalized_text not in collected_text:
                    collected_text.append(normalized_text)

        return " | ".join(collected_text)

    @staticmethod
    def _collect_visible_frame_subtree_entries(
        root_frame_ids: list[int], visible_entries_by_parent, max_depth: int = 2
    ):
        """``Inventory._collect_visible_frame_subtree_entries`` (``Inventory.py:531-569``).

        A breadth-first walk over the entry map `_build_visible_frame_entry_map` produced, tagging each entry
        with its `subtree_depth`; it is pure data work over whatever map it is handed.
        """

        from collections import deque

        visible_entries_by_frame: dict[int, SalvageChoiceEntry] = {
            int(entry["frame_id"]): cast(SalvageChoiceEntry, dict(entry))
            for child_entries in visible_entries_by_parent.values()
            for entry in child_entries
        }

        collected_entries: list[SalvageChoiceEntry] = []
        visited_frame_ids: set[int] = set()
        queued_frame_ids = deque((int(frame_id), 0) for frame_id in root_frame_ids)

        while queued_frame_ids:
            frame_id, depth = queued_frame_ids.popleft()
            if frame_id in visited_frame_ids:
                continue
            visited_frame_ids.add(frame_id)

            current_entry = visible_entries_by_frame.get(frame_id)
            if current_entry is None:
                continue

            current_entry = cast(SalvageChoiceEntry, dict(current_entry))
            current_entry["subtree_depth"] = depth
            collected_entries.append(current_entry)

            if depth >= max_depth:
                continue

            for child_entry in visible_entries_by_parent.get(frame_id, []):
                queued_frame_ids.append((int(child_entry["frame_id"]), depth + 1))

        return collected_entries

    @staticmethod
    def _pick_salvage_choice_click_entry(candidate_entries):
        """``Inventory._pick_salvage_choice_click_entry`` (``Inventory.py:571-592``).

        The source's own priority: a real button inside the option's subtree first, then any button, then a
        nested frame, then a plain one — and within a bucket the largest area, then depth, then top, then
        offset, then frame id.
        """

        if not candidate_entries:
            return None

        def _priority(entry: SalvageChoiceEntry) -> tuple[int, float, int, float, int, int]:
            template_type = int(entry.get("template_type", -1))
            subtree_depth = int(entry.get("subtree_depth", 0))
            priority_bucket = 0 if template_type == 1 and subtree_depth > 0 else 1 if template_type == 1 else 2 if subtree_depth > 0 else 3
            return (
                priority_bucket,
                -float(entry.get("area", 0.0)),
                subtree_depth,
                float(entry.get("top", 0.0)),
                int(entry.get("offset", -1)),
                int(entry.get("frame_id", 0)),
            )

        sorted_candidates = sorted(candidate_entries, key=_priority)
        return cast(SalvageChoiceEntry, dict(sorted_candidates[0]))

    @staticmethod
    def _get_salvage_choice_dialog_options(visible_entries_by_parent=None):
        """``Inventory._get_salvage_choice_dialog_options`` (``Inventory.py:595-737``).

        The option assembly: the container's direct children, the nested ones inside an offset-0 container,
        and for each source the clickable entry `_pick_salvage_choice_click_entry` picks. Every helper it
        calls answers now that the frames' geometry does — this member was the last of the three waiting on
        `Frame.rect`, through `_build_visible_frame_entry_map`.
        """

        option_parent = Inventory._salvage_option_container()
        if not option_parent.exists:
            return 0, [], []
        # this routine still keys its entry maps by id internally
        option_parent_id = option_parent.frame_id

        if visible_entries_by_parent is None:
            visible_entries_by_parent = Inventory._build_visible_frame_entry_map()

        direct_children = [
            cast(VisibleFrameEntry, dict(entry))
            for entry in visible_entries_by_parent.get(option_parent_id, [])
        ]

        direct_positive_entries = [
            entry
            for entry in direct_children
            if int(entry.get("offset", -1)) >= 1
        ]

        nested_option_sources: list[SalvageChoiceOptionSource] = []
        container_candidates = sorted(
            [entry for entry in direct_children if int(entry.get("offset", -1)) == 0],
            key=lambda entry: (
                0 if int(entry.get("template_type", -1)) == 1 else 1,
                -float(entry.get("area", 0.0)),
                float(entry.get("top", 0.0)),
                int(entry.get("frame_id", 0)),
            ),
        )
        for container_entry in container_candidates:
            nested_children = visible_entries_by_parent.get(int(container_entry["frame_id"]), [])
            positive_nested_children = [
                nested_entry
                for nested_entry in nested_children
                if int(nested_entry.get("offset", -1)) >= 1
            ]
            if not positive_nested_children:
                continue

            for nested_entry in positive_nested_children:
                nested_offset = int(nested_entry.get("offset", -1))
                nested_option_sources.append({
                    "offset": nested_offset,
                    "path_offsets": [0, nested_offset],
                    "fallback_frame_id": int(nested_entry["frame_id"]),
                    "source_depth": 2,
                    "container_frame_id": int(container_entry["frame_id"]),
                })

            if nested_option_sources:
                break

        option_sources: list[SalvageChoiceOptionSource] = []
        if nested_option_sources:
            option_sources.extend(nested_option_sources)
            nested_offsets = {int(source["offset"]) for source in nested_option_sources}
            for direct_entry in direct_positive_entries:
                direct_offset = int(direct_entry.get("offset", -1))
                if direct_offset in nested_offsets:
                    continue

                option_sources.append({
                    "offset": direct_offset,
                    "path_offsets": [direct_offset],
                    "fallback_frame_id": int(direct_entry["frame_id"]),
                    "source_depth": 1,
                    "container_frame_id": None,
                })
        else:
            for direct_entry in direct_positive_entries:
                direct_offset = int(direct_entry.get("offset", -1))
                option_sources.append({
                    "offset": direct_offset,
                    "path_offsets": [direct_offset],
                    "fallback_frame_id": int(direct_entry["frame_id"]),
                    "source_depth": 1,
                    "container_frame_id": None,
                })

        option_entries: list[SalvageChoiceEntry] = []
        seen_offsets: set[int] = set()
        for source in sorted(option_sources, key=lambda item: (int(item["offset"]), len(item["path_offsets"]))):
            option_offset = int(source["offset"])
            if option_offset in seen_offsets:
                continue
            seen_offsets.add(option_offset)

            path_offsets = [int(offset) for offset in source["path_offsets"]]
            path_root_frame_ids = Inventory._get_all_child_frame_ids_from_frame_id(option_parent_id, path_offsets)

            fallback_frame_id = int(source["fallback_frame_id"])
            if not path_root_frame_ids and fallback_frame_id != 0:
                path_root_frame_ids = [fallback_frame_id]

            candidate_entries = Inventory._collect_visible_frame_subtree_entries(
                path_root_frame_ids,
                visible_entries_by_parent,
                max_depth=2,
            )
            if not candidate_entries and fallback_frame_id != 0:
                candidate_entries = Inventory._collect_visible_frame_subtree_entries(
                    [fallback_frame_id],
                    visible_entries_by_parent,
                    max_depth=2,
                )
                if not path_root_frame_ids:
                    path_root_frame_ids = [fallback_frame_id]

            click_entry = Inventory._pick_salvage_choice_click_entry(candidate_entries)
            if click_entry is None:
                continue

            click_entry["offset"] = option_offset
            click_entry["source_depth"] = int(source["source_depth"])
            click_entry["path"] = "->".join(str(offset) for offset in path_offsets)
            click_entry["path_root_frame_ids"] = [int(frame_id) for frame_id in path_root_frame_ids]
            click_entry["group_frame_ids"] = [int(entry["frame_id"]) for entry in candidate_entries]
            click_entry["group_size"] = len(candidate_entries)
            option_entries.append(click_entry)

        if not option_entries:
            template_entries = [
                cast(SalvageChoiceEntry, dict(entry))
                for entry in direct_children
                if int(entry.get("template_type", -1)) == 1
            ]
            option_entries = template_entries or [cast(SalvageChoiceEntry, dict(entry)) for entry in direct_children]
            for entry in option_entries:
                if "path" not in entry:
                    entry["path"] = f"Options->{int(entry.get('offset', -1))}"
                if "group_frame_ids" not in entry:
                    entry["group_frame_ids"] = [int(entry["frame_id"])]
                if "group_size" not in entry:
                    entry["group_size"] = 1
                if "source_depth" not in entry:
                    entry["source_depth"] = 1

        option_entries.sort(key=lambda item: (int(item.get("offset", -1)), float(item.get("top", 0.0)), int(item["frame_id"])))
        return option_parent_id, direct_children, option_entries

    @staticmethod
    def _choose_salvage_choice_dialog_option(option_entries, strategy: int):
        """``Inventory._choose_salvage_choice_dialog_option`` (``Inventory.py:739-791``).

        Pure selection over the entries: strategy 0 prefers a crafting-material option by its text and falls
        back to the last visible one; strategy 1 prefers an upgrade/component and falls back to the first
        non-material one.  It reads `text` — which the source's own `_collect_frame_text` answers `""` — so
        the keyword matches find nothing and the documented fallbacks are what a caller actually gets.  That
        is the source's behaviour, not this port's simplification.
        """

        material_keywords = (
            "crafting material",
            "crafting materials",
            "materials",
            "material",
        )
        non_material_keywords = (
            "inscription",
            "grip",
            "haft",
            "snathe",
            "pommel",
            "hilt",
            "handle",
            "head",
            "wrapping",
            "string",
        )

        if not option_entries:
            return None, "no options"

        if strategy == 0:
            for entry in option_entries:
                option_text = str(entry.get("text", "")).lower()
                if any(keyword in option_text for keyword in material_keywords):
                    return entry, "prefer crafting materials (text match)"
            return option_entries[-1], "prefer crafting materials (last visible option fallback)"

        if strategy == 1:
            for entry in option_entries:
                option_text = str(entry.get("text", "")).lower()
                if any(keyword in option_text for keyword in non_material_keywords):
                    return entry, "prefer upgrades/components (text match)"

            material_frame_ids = {
                int(entry["frame_id"])
                for entry in option_entries
                if any(keyword in str(entry.get("text", "")).lower() for keyword in material_keywords)
            }
            if material_frame_ids and len(material_frame_ids) < len(option_entries):
                for entry in option_entries:
                    if int(entry["frame_id"]) not in material_frame_ids:
                        return entry, "prefer upgrades/components (non-material fallback)"

            return option_entries[0], "prefer upgrades/components (first visible option fallback)"

        return option_entries[0], "prefer upgrades/components (strategy fallback)"

    @staticmethod
    def _salvage_choice_debug_log(debug_enabled: bool, log_module: str, message: str):
        """``Inventory._salvage_choice_debug_log`` (``Inventory.py:793-801``).

        The source's first act is ``if not debug_enabled: return``, and a disabled log is the common case, so
        that guard is ported as written; only an **enabled** log needs the console Reforged logs through
        (``PySystem.Console`` → ``py4gwcorelib_src/Console.py``), which this port does not carry.
        """

        if not debug_enabled:
            return

        raise _unported(
            "Inventory._salvage_choice_debug_log",
            "PySystem.Console — the in-client ImGui console Reforged logs through "
            "(Inventory.py:799 → py4gwcorelib_src/Console.py), which this port does not carry; the disabled "
            "case returns before this, as the source's own guard does",
        )

    @staticmethod
    def _format_salvage_choice_option(option_entry, total_options: int):
        """``Inventory._format_salvage_choice_option`` (``Inventory.py:803-828``).

        A one-line summary of an entry, each optional key appended only when the entry carries it — the shape
        the source's debug block prints.
        """

        option_index = option_entry["order"] if "order" in option_entry else 0
        frame_id = option_entry["frame_id"]
        child_offset = option_entry["offset"]
        option_text = option_entry["text"].strip()
        source_depth = option_entry["source_depth"] if "source_depth" in option_entry else 1
        option_path = option_entry["path"].strip() if "path" in option_entry else ""
        group_size = option_entry["group_size"] if "group_size" in option_entry else 0
        subtree_depth = option_entry["subtree_depth"] if "subtree_depth" in option_entry else 0
        template_type = option_entry["template_type"]

        summary = f"index={option_index}/{max(1, total_options)} frame_id={frame_id} child_offset={child_offset}"
        if option_path:
            summary += f" path={option_path}"
        if group_size > 0:
            summary += f" group_frames={group_size}"
        if source_depth > 1:
            summary += f" depth={source_depth}"
        if subtree_depth > 0:
            summary += f" click_depth={subtree_depth}"
        if template_type >= 0:
            summary += f" template={template_type}"
        if option_text:
            summary += f" text='{option_text}'"
        return summary

    @staticmethod
    def HandleSalvageChoiceMaterialConfirmDialog(
        auto_confirm: bool = False,
        queue_name: str = "SALVAGE",
        log_module: str = "SalvageItems",
        queue_wait_timeout_ms: int = 5000,
        poll_ms: int = 50,
        close_timeout_ms: int = 1500,
        debug_enabled: bool = False,
        item_id: int = 0,
    ):
        """``Inventory.HandleSalvageChoiceMaterialConfirmDialog`` (``Inventory.py:831-897``).

        A generator over Reforged's ``Routines.Yield`` protocol with an ``ActionQueueManager`` queue; see
        the module docstring for why that driver is the missing piece.
        """

        raise _unported(
            "Inventory.HandleSalvageChoiceMaterialConfirmDialog", _ROUTINES
        )

    @staticmethod
    def _wait_for_salvage_choice_dialog_close(
        auto_confirm_materials_warning: bool = False,
        queue_name: str = "SALVAGE",
        log_module: str = "SalvageItems",
        queue_wait_timeout_ms: int = 5000,
        poll_ms: int = 50,
        close_timeout_ms: int = 1500,
        debug_enabled: bool = False,
        item_id: int = 0,
        after_action_label: str = "confirm click",
    ):
        """``Inventory._wait_for_salvage_choice_dialog_close`` (``Inventory.py:899-950``)."""

        raise _unported("Inventory._wait_for_salvage_choice_dialog_close", _ROUTINES)

    @staticmethod
    def HandleSalvageChoiceDialog(
        auto_handle: bool = False,
        strategy: int = 0,
        auto_confirm_materials_warning: bool = False,
        queue_name: str = "SALVAGE",
        log_module: str = "SalvageItems",
        queue_wait_timeout_ms: int = 5000,
        poll_ms: int = 50,
        close_timeout_ms: int = 1500,
        debug_enabled: bool = False,
        item_id: int = 0,
    ):
        """``Inventory.HandleSalvageChoiceDialog`` (``Inventory.py:952-1160``)."""

        raise _unported("Inventory.HandleSalvageChoiceDialog", _ROUTINES)

    # -- the storage window (``Inventory.py:1162-1177``) -------------------

    @staticmethod
    def OpenXunlaiWindow():
        """``Inventory.OpenXunlaiWindow`` (``Inventory.py:1162-1169``).

        It builds **two** binding instances — one to open the window, one to read whether it opened —
        which is the source's own body, and its second call raises until the storage path answers.
        """

        Inventory.inventory_instance().OpenXunlaiWindow()
        return Inventory.inventory_instance().GetIsStorageOpen()

    @staticmethod
    def IsStorageOpen():
        """``Inventory.IsStorageOpen`` (``Inventory.py:1171-1177``)."""

        return Inventory.inventory_instance().GetIsStorageOpen()

    # -- the item actions (``Inventory.py:1179-1239``) ---------------------

    @staticmethod
    def PickUpItem(item_id, call_target=False):
        """``Inventory.PickUpItem`` (``Inventory.py:1179-1188``): ``item_id`` is not an agent id."""

        Inventory.inventory_instance().PickUpItem(item_id, call_target)

    @staticmethod
    def DropItem(item_id, quantity=1):
        """``Inventory.DropItem`` (``Inventory.py:1190-1199``): the one action that returns its call."""

        return Inventory.inventory_instance().DropItem(item_id, quantity)

    @staticmethod
    def EquipItem(item_id, agent_id):
        """``Inventory.EquipItem`` (``Inventory.py:1201-1210``)."""

        Inventory.inventory_instance().EquipItem(item_id, agent_id)

    @staticmethod
    def UseItem(item_id):
        """``Inventory.UseItem`` (``Inventory.py:1212-1220``)."""

        Inventory.inventory_instance().UseItem(item_id)

    @staticmethod
    def DestroyItem(item_id):
        """``Inventory.DestroyItem`` (``Inventory.py:1222-1230``)."""

        Inventory.inventory_instance().DestroyItem(item_id)

    @staticmethod
    def GetHoveredItemID():
        """``Inventory.GetHoveredItemID`` (``Inventory.py:1232-1239``)."""

        return Inventory.inventory_instance().GetHoveredItemID()

    # -- gold (``Inventory.py:1241-1287``) --------------------------------

    @staticmethod
    def GetGoldOnCharacter():
        """``Inventory.GetGoldOnCharacter`` (``Inventory.py:1241-1248``): delegates to `GetGoldAmount`."""

        return Inventory.inventory_instance().GetGoldAmount()

    @staticmethod
    def GetGoldInStorage():
        """``Inventory.GetGoldInStorage`` (``Inventory.py:1250-1257``)."""

        return Inventory.inventory_instance().GetGoldAmountInStorage()

    @staticmethod
    def DepositGold(amount):
        """``Inventory.DepositGold`` (``Inventory.py:1259-1267``)."""

        Inventory.inventory_instance().DepositGold(amount)

    @staticmethod
    def WithdrawGold(amount):
        """``Inventory.WithdrawGold`` (``Inventory.py:1269-1277``)."""

        Inventory.inventory_instance().WithdrawGold(amount)

    @staticmethod
    def DropGold(amount):
        """``Inventory.DropGold`` (``Inventory.py:1279-1287``)."""

        Inventory.inventory_instance().DropGold(amount)

    # -- move, find and storage (``Inventory.py:1289-1471``) --------------

    @staticmethod
    def MoveItem(item_id, bag_id, slot, quantity=1):
        """``Inventory.MoveItem`` (``Inventory.py:1289-1300``).

        The delegation is the source's own; the raise comes from where the source's own call graph puts
        it — ``py_inventory.MoveItem`` names the four-word call form `item.move_item_func` needs.
        """

        Inventory.inventory_instance().MoveItem(item_id, bag_id, slot, quantity)

    @staticmethod
    def FindItemBagAndSlot(item_id):
        """``Inventory.FindItemBagAndSlot`` (``Inventory.py:1302-1323``).

        It seeds bags 1 to 4, re-queries each bag on its own, and answers ``(bag_id, slot)`` for the first
        match — or ``(None, None)``.
        """

        bags_to_check = ItemArray.CreateBagList(1, 2, 3, 4)

        for bag_enum in bags_to_check:
            bag_items = ItemArray.GetItemArray([bag_enum])
            for item in bag_items:
                if item == item_id:
                    slot = Item.GetSlot(item)
                    return bag_enum.value, slot
        return None, None

    @staticmethod
    def DepositItemToStorage(item_id, Anniversary_panel=True):
        """``Inventory.DepositItemToStorage`` (``Inventory.py:1325-1408``).

        The source opens with ``from .enums import Bags`` (``:1335``) and then builds its bag list from
        **capacity**, not from a fixed range: the storage bags' combined size divided by 25 is how many
        exist, and each is reached by name — ``getattr(Bags, f"Storage{i}")`` (``:1352-1354``), the
        source's own dynamic reach, ported as written. ``Bags`` itself comes from the module that declares
        it here, as at the top of this file.

        Partial stacks of the same model are filled first (``:1373-1388``, only when the item is
        stackable), then empty slots (``:1390-1406``), and the member answers ``True`` as soon as what was
        asked for has moved — or whether anything moved at all.
        """

        def GetBags():
            possible_bags = ItemArray.CreateBagList(
                Bags.Storage1,
                Bags.Storage2,
                Bags.Storage3,
                Bags.Storage4,
                *([Bags.Storage5] if Anniversary_panel else []),
                Bags.Storage6,
                Bags.Storage7,
                Bags.Storage8,
                Bags.Storage9,
                Bags.Storage10,
                Bags.Storage11,
                Bags.Storage12,
                Bags.Storage13,
                Bags.Storage14,
            )

            total_capacity = sum(
                PyInventoryBag(bag_enum.value, bag_enum.name).GetSize()
                for bag_enum in possible_bags
            )

            bags = total_capacity // 25

            storage_bags = []

            for i in range(1, bags + 1):
                bag = getattr(Bags, f"Storage{i}")
                storage_bags.append(bag)

            return storage_bags

        MAX_STACK_SIZE = 250

        is_stackable = Item.Properties.IsStackable(item_id)
        quantity = Item.Properties.GetQuantity(item_id)

        if quantity == 0:
            return False

        storage_bags = GetBags()

        remaining_quantity = quantity
        moved_any = False

        if is_stackable:
            for bag_enum in storage_bags:
                bag = PyInventoryBag(bag_enum.value, bag_enum.name)
                items = bag.GetItems()
                for item in items:
                    if item.model_id == Item.GetModelID(item_id):
                        item_qty = Item.Properties.GetQuantity(item.item_id)
                        if item_qty < MAX_STACK_SIZE:
                            space_left = MAX_STACK_SIZE - item_qty
                            to_move = min(space_left, remaining_quantity)
                            if to_move > 0:
                                Inventory.MoveItem(item_id, bag_enum.value, item.slot, to_move)
                                remaining_quantity -= to_move
                                moved_any = True
                                if remaining_quantity == 0:
                                    return True

        for bag_enum in storage_bags:
            bag = PyInventoryBag(bag_enum.value, bag_enum.name)
            size = bag.GetSize()
            items = bag.GetItems()

            occupied_slots = {item.slot for item in items}
            for slot in range(size):
                if slot in occupied_slots:
                    continue

                to_move = (
                    remaining_quantity
                    if not is_stackable
                    else min(remaining_quantity, MAX_STACK_SIZE)
                )
                Inventory.MoveItem(item_id, bag_enum.value, slot, to_move)
                remaining_quantity -= to_move
                moved_any = True
                if remaining_quantity == 0:
                    return True

        return moved_any

    @staticmethod
    def WithdrawItemFromStorage(item_id, quantity=250):
        """``Inventory.WithdrawItemFromStorage`` (``Inventory.py:1410-1471``).

        The same two passes over the four inventory bags — partial stacks of the same model first
        (``:1436-1451``), then empty slots (``:1453-1469``) — with the amount clamped to what the item
        actually holds (``:1424``), so a request of zero answers ``False``. Its ``from .enums import Bags``
        (``:1420``) is never referenced in the source's body either; here the name is already imported.
        """

        MAX_STACK_SIZE = 250

        is_stackable = Item.Properties.IsStackable(item_id)
        quantity = min(quantity, Item.Properties.GetQuantity(item_id))

        if quantity == 0:
            return False

        inventory_bags = ItemArray.CreateBagList(
            Bags.Backpack, Bags.BeltPouch, Bags.Bag1, Bags.Bag2
        )

        remaining_quantity = quantity
        moved_any = False

        if is_stackable:
            for bag_enum in inventory_bags:
                bag = PyInventoryBag(bag_enum.value, bag_enum.name)
                items = bag.GetItems()
                for item in items:
                    if item.model_id == Item.GetModelID(item_id):
                        item_qty = Item.Properties.GetQuantity(item.item_id)
                        if item_qty < MAX_STACK_SIZE:
                            space_left = MAX_STACK_SIZE - item_qty
                            to_move = min(space_left, remaining_quantity)
                            if to_move > 0:
                                Inventory.MoveItem(item_id, bag_enum.value, item.slot, to_move)
                                remaining_quantity -= to_move
                                moved_any = True
                                if remaining_quantity == 0:
                                    return True

        for bag_enum in inventory_bags:
            bag = PyInventoryBag(bag_enum.value, bag_enum.name)
            size = bag.GetSize()
            items = bag.GetItems()

            occupied_slots = {item.slot for item in items}
            for slot in range(size):
                if slot in occupied_slots:
                    continue

                to_move = (
                    remaining_quantity
                    if not is_stackable
                    else min(remaining_quantity, MAX_STACK_SIZE)
                )
                Inventory.MoveItem(item_id, bag_enum.value, slot, to_move)
                remaining_quantity -= to_move
                moved_any = True
                if remaining_quantity == 0:
                    return True

        return moved_any
