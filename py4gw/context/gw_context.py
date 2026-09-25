"""Port of Reforged's ``Py4GWCoreLib/Context.py``.

That file declares the ``GWContext`` namespace: one nested class per game context,
each inheriting ``GetPtr`` / ``GetContext`` / ``IsValid`` from ``_GWContextBase``,
plus ``InstanceInfo.GetMapInfo()``. Every ``Map`` member reaches its context
through it, so its absence is why ``Map`` grew stand-in helpers.

**One line is not literal, and it is the lazy-load rule.** Reforged runs a
perpetual per-frame loop, and each facade's cache is refreshed from it::

    PyCallback.PyCallback.Register(InstanceInfo._callback_name,
                                   InstanceInfo._update_ptr,
                                   priority=3, context=PyCallback.Context.Draw)

Stealth has no loop and no dispatcher, so nothing refreshes that cache in the
background. ``GetContext`` therefore loads **lazily**: it calls the source's own
``_update_ptr`` at the point of use and then returns the context. Without it the
cache is never filled and ``GetContext`` would answer ``None`` forever, which is
not what the source does. See ``docs/PORTING_RULES.md``, "There is no dispatcher:
every read is lazy".

The three contexts whose ``_update_ptr`` refuses (``MissionMap``, ``WorldMap``,
``SalvageSessionInfo``) are published by an in-process shared-memory callback;
their external read goes through the frame-array walk instead. Their
``GetContext`` therefore raises the module's own refusal until that read is wired.
"""

from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar

from .acc_agent_context import AccAgentContext, AccAgentContextStruct
from .agent_array import AgentArray, AgentArrayStruct
from .available_character_context import (
    AvailableCharacterArray,
    AvailableCharacterArrayStruct,
)
from .char_context import CharContext, CharContextStruct
from .cinematic_context import Cinematic, CinematicStruct
from .gameplay_context import GameplayContext, GameplayContextStruct
from .guild_context import GuildContext, GuildContextStruct
from .instance_info_context import (
    AreaInfoStruct,
    InstanceInfo,
    InstanceInfoStruct,
)
from .map_context import MapContext, MapContextStruct
from .mission_map_context import MissionMapContext, MissionMapContextStruct
from .party_context import PartyContext, PartyContextStruct
from .pre_game_context import PreGameContext, PreGameContextStruct
from .server_region_context import ServerRegion, ServerRegionStruct
from .world_context import WorldContext, WorldContextStruct
from .world_map_context import WorldMapContext, WorldMapContextStruct

# the struct type
TStruct = TypeVar("TStruct")


class _GWContextBase(Generic[TStruct]):
    """
    Base class for context facades.
    Subclasses must set:
      _struct_type: the ctypes.Structure
      _facade:      facade class w/ get_ptr() and get_context()
    """
    _struct_type: Type[TStruct]
    _facade: Any   # facade like InstanceInfo, MapContext, CharContext...

    @classmethod
    def GetPtr(cls) -> int:
        return cls._facade.get_ptr()

    @classmethod
    def GetContext(cls) -> Optional[TStruct]:
        # Source body is ``return cls._facade.get_context()``. The source's cache
        # is refreshed every frame by an in-process callback; Stealth has no
        # dispatcher, so the read is lazy -- refresh here, at the point of use,
        # through the source's own _update_ptr.
        cls._facade._update_ptr()
        return cls._facade.get_context()

    @classmethod
    def IsValid(cls) -> bool:
        return cls.GetContext() is not None


class GWContext:
    class AccAgent(_GWContextBase[AccAgentContextStruct]):
        _struct_type = AccAgentContextStruct
        _facade = AccAgentContext

    class AgentArray(_GWContextBase[AgentArrayStruct]):
        _struct_type = AgentArrayStruct
        _facade = AgentArray

    class AvailableCharacterArray(_GWContextBase[AvailableCharacterArrayStruct]):
        _struct_type = AvailableCharacterArrayStruct
        _facade = AvailableCharacterArray

    class Char(_GWContextBase[CharContextStruct]):
        _struct_type = CharContextStruct
        _facade = CharContext

    class Cinematic(_GWContextBase[CinematicStruct]):
        _struct_type = CinematicStruct
        _facade = Cinematic

    class Gameplay(_GWContextBase[GameplayContextStruct]):
        _struct_type = GameplayContextStruct
        _facade = GameplayContext

    class Guild(_GWContextBase[GuildContextStruct]):
        _struct_type = GuildContextStruct
        _facade = GuildContext

    class InstanceInfo(_GWContextBase[InstanceInfoStruct]):
        _struct_type = InstanceInfoStruct
        _facade = InstanceInfo

        def GetMapInfo(self) -> Optional[AreaInfoStruct]:
            instance_info = self.GetContext()
            if not instance_info:
                return None
            return instance_info.current_map_info

    class Map(_GWContextBase[MapContextStruct]):
        _struct_type = MapContextStruct
        _facade = MapContext

    class MissionMap(_GWContextBase[MissionMapContextStruct]):
        _struct_type = MissionMapContextStruct
        _facade = MissionMapContext

    class Party(_GWContextBase[PartyContextStruct]):
        _struct_type = PartyContextStruct
        _facade = PartyContext

    class PreGame(_GWContextBase[PreGameContextStruct]):
        _struct_type = PreGameContextStruct
        _facade = PreGameContext

    class ServerRegion(_GWContextBase[ServerRegionStruct]):
        _struct_type = ServerRegionStruct
        _facade = ServerRegion

    class World(_GWContextBase[WorldContextStruct]):
        _struct_type = WorldContextStruct
        _facade = WorldContext

    class WorldMap(_GWContextBase[WorldMapContextStruct]):
        _struct_type = WorldMapContextStruct
        _facade = WorldMapContext
