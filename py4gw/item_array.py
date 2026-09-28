"""Port of Reforged's ``Py4GWCoreLib/ItemArray.py`` (212 lines).

**What the module is.** ``ItemArray``: the four static methods that turn bag ids into item-id lists —
``CreateBagList`` (a list of ``Bag`` members from ints), ``GetItemArray`` (the ids across those bags),
``GetAllBags`` (the bags that hold anything) and ``GetBag`` (one bag's binding instance) — and the three
nested namespaces behind them: ``Filter`` (2 members), ``Manipulation`` (3) and ``Sort`` (2). Fourteen
declarations in all, and every one of them is here with the source's name, signature, nesting and order.

**Two adaptations, both recorded rather than smoothed over.**

1. **``@frame_cache`` is dropped, and the three members read when they are called.** ``GetItemArray``,
   ``GetAllBags`` and ``GetBag`` carry Reforged's ``@frame_cache(category="ItemArray", ...)``, whose only
   invalidator is that library's per-frame tick (``py4gwcorelib_src/FrameCache.py``). This port has no
   frame loop, so there is no frame boundary to key a memo to and a verbatim copy would never invalidate:
   the first call would pin an item list for the life of the process, which is the stale read the port's
   rules forbid (``AGENTS.md`` § Caching, ``docs/PORTING_RULES.md``). So the decorator is gone and the
   member reads when it is called — the behaviour the source's own callers observe.
2. **The two ``PySystem.Console.Log`` calls have nowhere to go.** ``CreateBagList`` logs an invalid bag
   id and drops it (``ItemArray.py:23-24``); ``GetItemArray`` logs a bag whose read raised and carries on
   to the next bag (``:52-53``). No console is ported — *a library with no console reports through its
   return values and its exceptions*, which is ``dialog.py``'s own wording for the same situation — so the
   **control flow is kept exactly** (the id is dropped, the bag is skipped) and the log line is the part
   that cannot be reproduced. Nothing is printed in its place: a logger of this project's own invention
   would be a member the sources do not have.

**One source behaviour kept as written, not tidied.** ``Filter.ByAttribute`` and ``Sort.SortByAttribute``
reach ``Item``'s members **by name** — ``hasattr``/``getattr(Item, attribute)`` — because their callers
pass strings such as ``"Properties.GetValue"`` (``ItemArray.py:189``). That dynamic reach is the source's
own dispatch, so it is ported as it stands. It follows that ``GetBag``, whose annotation says ``int``
while its body hands the value to ``GetItemArray`` as a ``Bag`` (``:77,82``), answers ``None`` for an int:
the attribute error inside ``GetItemArray``'s own ``try`` skips that bag, so the list comes back empty —
the source's behaviour, pinned by a test.
"""

from __future__ import annotations

from .item import Bag, Item
from .py_inventory import Bag as PyInventoryBag


class ItemArray:
    """``ItemArray`` (``ItemArray.py:8-211``), in the source's own nesting and order."""

    @staticmethod
    def CreateBagList(*bag_ids: int) -> list[Bag]:
        """``ItemArray.CreateBagList`` (``ItemArray.py:9-26``).

        Each id becomes a ``Bag`` member; an id that is not one raises ``ValueError`` inside the source's
        own ``try`` and is dropped. The source logs the drop to Reforged's console; see the module
        docstring for why this port keeps the drop and not the log.
        """

        bags_to_check: list[Bag] = []

        for bag_id in bag_ids:
            try:
                bags_to_check.append(Bag(bag_id))
            except ValueError:
                pass

        return bags_to_check

    @staticmethod
    def GetItemArray(bags_to_check):
        """``ItemArray.GetItemArray`` (``ItemArray.py:28-55``): every item id in those bags.

        The source carries ``@frame_cache(category="ItemArray", source_lib="GetItemArray")``; the
        decorator is dropped and the member reads when called — see the module docstring. A bag whose read
        raises is skipped, as the source's own ``except`` does.
        """

        all_item_ids: list[int] = []

        for bag_enum in bags_to_check:
            try:
                bag_instance = PyInventoryBag(bag_enum.value, bag_enum.name)

                items_in_bag = bag_instance.GetItems()

                item_ids_in_bag = [item.item_id for item in items_in_bag]
                all_item_ids.extend(item_ids_in_bag)

            except Exception:
                continue

        return all_item_ids

    @staticmethod
    def GetAllBags() -> list[Bag]:
        """``ItemArray.GetAllBags`` (``ItemArray.py:57-73``): the bags that hold anything.

        ``@frame_cache(category="ItemArray", source_lib="GetAllBags")`` in the source, dropped here.
        """

        valid_bags: list[Bag] = []

        for bag in Bag:
            if bag == Bag.NoBag:
                continue
            items = ItemArray.GetItemArray([bag])
            if items:
                valid_bags.append(bag)

        return valid_bags

    @staticmethod
    def GetBag(bag: int):
        """``ItemArray.GetBag`` (``ItemArray.py:75-91``).

        ``@frame_cache(category="ItemArray", source_lib="GetBag")`` in the source, dropped here.

        **A source finding, pinned by the test: this member cannot answer a bag either way.** Its
        annotation says ``int``, and through an ``int`` the first line — ``GetItemArray([bag])`` — already
        comes back empty, because ``ItemArray.py:43`` reads ``bag_enum.value`` off the argument and an
        ``int`` has none, which ``GetItemArray``'s own ``except`` swallows. Through a ``Bag`` member the
        first line works, but ``PyInventory.Bag(bag, str(bag))`` (``:87``) cannot take one: ``Bag`` is a
        plain ``Enum`` (``Item.py:13``), so the binding's ``int`` conversion raises, and the source's own
        ``except Exception: return None`` (``:90-91``) turns that into ``None`` as well. Both paths are
        reproduced exactly, and neither is "fixed" here.
        """

        items = ItemArray.GetItemArray([bag])
        if not items:
            return None

        try:
            bag_instance = PyInventoryBag(bag, str(bag))
            bag_instance.GetContext()
            return bag_instance
        except Exception:
            return None

    class Filter:
        """``ItemArray.Filter`` (``ItemArray.py:93-128``)."""

        @staticmethod
        def ByAttribute(item_array, attribute, condition_func=None, negate=False):
            """``ItemArray.Filter.ByAttribute`` (``ItemArray.py:94-114``).

            The attribute is reached on ``Item`` **by name**, as the source does it; a name ``Item`` does
            not carry excludes the item, or includes it when ``negate`` is set. The name must be one
            attribute of ``Item`` itself: the source's own docstring example passes
            ``'Properties.GetValue'``, and ``hasattr(Item, 'Properties.GetValue')`` is false because
            ``getattr`` does not walk the dot — so that example excludes every item. The port keeps the
            comparison the source makes, and the test pins both behaviours.
            """

            def attribute_filter(item_id: int) -> bool:
                if hasattr(Item, attribute):
                    attr_value = getattr(Item, attribute)(item_id)

                    result = condition_func(attr_value) if condition_func else bool(attr_value)

                    return not result if negate else result

                return False if not negate else True

            return list(filter(attribute_filter, item_array))

        @staticmethod
        def ByCondition(item_array, filter_func):
            """``ItemArray.Filter.ByCondition`` (``ItemArray.py:117-128``)."""

            return list(filter(filter_func, item_array))

    class Manipulation:
        """``ItemArray.Manipulation`` (``ItemArray.py:132-182``)."""

        @staticmethod
        def Merge(array1, array2):
            """``ItemArray.Manipulation.Merge`` (``ItemArray.py:133-148``): the union, deduplicated."""

            return list(set(array1).union(set(array2)))

        @staticmethod
        def Subtract(array1, array2):
            """``ItemArray.Manipulation.Subtract`` (``ItemArray.py:150-165``): the difference."""

            return list(set(array1) - set(array2))

        @staticmethod
        def Intersect(array1, array2):
            """``ItemArray.Manipulation.Intersect`` (``ItemArray.py:167-182``): the intersection."""

            return list(set(array1).intersection(set(array2)))

    class Sort:
        """``ItemArray.Sort`` (``ItemArray.py:184-211``)."""

        @staticmethod
        def SortByAttribute(item_array, attribute, reverse=False):
            """``ItemArray.Sort.SortByAttribute`` (``ItemArray.py:185-198``).

            An attribute name ``Item`` does not carry raises ``ValueError``, with the source's own
            message — which is what its docstring example (``'Properties.GetValue'``) gets, since
            ``getattr`` does not walk the dot.
            """

            def get_attribute_value(item_id):
                if hasattr(Item, attribute):
                    return getattr(Item, attribute)(item_id)
                raise ValueError(f"Invalid attribute: {attribute}")

            return sorted(item_array, key=get_attribute_value, reverse=reverse)

        @staticmethod
        def SortByCondition(item_array, condition_func, reverse=False):
            """``ItemArray.Sort.SortByCondition`` (``ItemArray.py:200-211``)."""

            return sorted(item_array, key=condition_func, reverse=reverse)
