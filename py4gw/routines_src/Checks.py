"""External port of Reforged's ``routines_src/Checks.py``.

**Scope: the cascade `Map` reaches, and nothing else.** ``Map.Pathing.GetPathingMaps`` and
``GetPathingMapsRaw`` guard on ``Checks.Map.MapValid()`` (``Map.py:2107, 2117``), so the ``Checks``
class is ported here with its ``Map`` namespace complete — all seven members, every one of them a
guard over the already-ported ``Map`` and ``Party``.

**The rest of the class is that class's own migration, not this one's.** ``Checks.py`` is 1,426
lines and declares eight namespaces — ``Player`` (4), ``Party`` (8), ``Map`` (7), ``Inventory``
(7), ``Items`` (1), ``Effects`` (2), ``Agents`` (24) and ``Skills`` (12). ``Map`` reaches none of
the other seven, and none of them is declared here, because declaring a member whose body cannot
be written yet is work belonging to ``Checks``'s own port and not to this cascade. That is
recorded, not hidden: ``docs/CLASS_PORT_MAP.md`` carries a row for ``Checks`` saying exactly what
is in and what is not.

**The one name the port does not carry.** The source's module-level ``Routines = _RProxy()`` is a
lazy proxy into ``Py4GWCoreLib.Routines``; ``Checks``'s ``Map`` members use none of it, so it is
not ported here. A member that needs it, when one is reached, is where it goes.

**No ``__init__.py``.** ``routines_src`` is a namespace package in the source — it has no
``__init__.py`` — and it is imported the same way here (``py4gw.routines_src.Checks``).

Nothing here is invented: see ``docs/PORTING_RULES.md``.
"""

from __future__ import annotations

from typing import Optional, Tuple  # noqa: F401  (the source's own module-level imports, kept)

from ..enums_src.game_data_enums import Range  # noqa: F401  (``checks.py:6``, for the rest of the class)


class Checks:
    # region Map
    class Map:
        @staticmethod
        def MapValid():
            """``checks.py:352-367`` — the guard every pathing read goes through."""

            from ..map import Map
            from ..party import Party

            if not Map.IsMapReady():
                return False

            if Map.IsInCinematic():
                return False

            if not Party.IsPartyLoaded():
                return False

            return True

        @staticmethod
        def IsExplorable():
            """``checks.py:369-374``."""

            from ..map import Map

            if not Checks.Map.MapValid():
                return False
            return Map.IsExplorable()

        @staticmethod
        def IsOutpost():
            """``checks.py:376-381``."""

            from ..map import Map

            if not Checks.Map.MapValid():
                return False
            return Map.IsOutpost()

        @staticmethod
        def IsLoading():
            """``checks.py:383-389``."""

            from ..map import Map

            if not Checks.Map.MapValid():
                return True

            return Map.IsMapLoading()

        @staticmethod
        def IsMapReady():
            """``checks.py:391-394``."""

            from ..map import Map

            return Map.IsMapReady()

        @staticmethod
        def IsInCinematic():
            """``checks.py:397-402``."""

            from ..map import Map

            if not Checks.Map.MapValid():
                return False
            return Map.IsInCinematic()

        @staticmethod
        def IsCombatReady():
            """``checks.py:404-409``."""

            from ..map import Map

            if not Checks.Map.MapValid():
                return False
            return Map.IsExplorable()


__all__ = ["Checks"]
