"""Guild Wars context readers and external array views."""

from . import char_context
from . import cinematic_context
from . import game_context
from . import gameplay_context
from . import pre_game_context
from . import server_region_context
from . import instance_info_context
from . import text_parser_context
from . import available_character_context
from . import party_context
from . import guild_context
from . import acc_agent_context
from .char_context import (
    CharContext,
    CharContextStruct,
    ObserverMatch,
    ObserverMatchFlags,
    ProgressBar,
    get,
)
from .cinematic_context import Cinematic, CinematicStruct
from .game_context import GameContext, GameContextStruct
from .gameplay_context import GameplayContext, GameplayContextStruct
from .pre_game_context import (
    LoginCharacter,
    PreGameContext,
    PreGameContextStruct,
)
from .server_region_context import ServerRegion, ServerRegionStruct
from .instance_info_context import (
    AreaInfoStruct,
    InstanceInfo,
    InstanceInfoStruct,
    MapDimensionsStruct,
)
from .text_parser_context import (
    TextCacheStruct,
    TextParser,
    TextParserStruct,
    TextParserSubStructStruct,
)
from .available_character_context import (
    AvailableCharacterArray,
    AvailableCharacterArrayStruct,
    AvailableCharacterInfoStruct,
)
from .party_context import (
    HenchmanPartyMemberStruct,
    HeroPartyMemberStruct,
    PartyContext,
    PartyContextStruct,
    PartyInfoStruct,
    PartySearchStruct,
    PlayerPartyMemberStruct,
)
from .guild_context import (
    CapeDesign,
    CapeDesignStruct,
    GHKey,
    GHKeyStruct,
    Guild,
    GuildContext,
    GuildContextStruct,
    GuildHistoryEvent,
    GuildHistoryEventStruct,
    GuildPlayer,
    GuildPlayerStruct,
    GuildStruct,
    TownAlliance,
    TownAllianceStruct,
)
from .acc_agent_context import (
    AccAgentContext,
    AccAgentContextStruct,
    AgentContext,
    AgentContextStruct,
    AgentMovement,
    AgentMovementStruct,
    AgentSummaryInfo,
    AgentSummaryInfoStruct,
    AgentSummaryInfoSub,
    AgentSummaryInfoSubStruct,
    Vec3f,
    Vec3fStruct,
)
from .gw_array import (
    GW_Array,
    GW_Array_Value_View,
    GW_Array_View,
    GW_BaseArray,
    GWArray,
    GWArrayValueView,
    GWArrayView,
    GWBaseArray,
)
from .gw_list import GWLinkStruct, GWListStruct, RemoteGWListView

__all__ = [
    "CharContext",
    "CharContextStruct",
    "Cinematic",
    "CinematicStruct",
    "GameContext",
    "GameContextStruct",
    "GameplayContext",
    "GameplayContextStruct",
    "ServerRegion",
    "ServerRegionStruct",
    "InstanceInfo",
    "InstanceInfoStruct",
    "MapDimensionsStruct",
    "AreaInfoStruct",
    "TextParser",
    "TextParserStruct",
    "TextCacheStruct",
    "TextParserSubStructStruct",
    "AvailableCharacterArray",
    "AvailableCharacterArrayStruct",
    "AvailableCharacterInfoStruct",
    "PartyContext",
    "PartyContextStruct",
    "PartyInfoStruct",
    "PartySearchStruct",
    "PlayerPartyMemberStruct",
    "HeroPartyMemberStruct",
    "HenchmanPartyMemberStruct",
    "PreGameContext",
    "PreGameContextStruct",
    "LoginCharacter",
    "ObserverMatch",
    "ObserverMatchFlags",
    "ProgressBar",
    "GWArray",
    "GWBaseArray",
    "GWArrayView",
    "GWArrayValueView",
    "GW_Array",
    "GW_BaseArray",
    "GW_Array_View",
    "GW_Array_Value_View",
    "GWLinkStruct",
    "GWListStruct",
    "RemoteGWListView",
    "GuildContext",
    "GuildContextStruct",
    "GHKeyStruct",
    "CapeDesignStruct",
    "TownAllianceStruct",
    "GuildHistoryEventStruct",
    "GuildStruct",
    "GuildPlayerStruct",
    "GHKey",
    "CapeDesign",
    "TownAlliance",
    "GuildHistoryEvent",
    "Guild",
    "GuildPlayer",
    "AccAgentContext",
    "AccAgentContextStruct",
    "AgentContext",
    "AgentContextStruct",
    "AgentMovementStruct",
    "AgentSummaryInfoStruct",
    "AgentSummaryInfoSubStruct",
    "Vec3fStruct",
    "Vec3f",
    "AgentSummaryInfoSub",
    "AgentSummaryInfo",
    "AgentMovement",
    "char_context",
    "cinematic_context",
    "game_context",
    "gameplay_context",
    "pre_game_context",
    "server_region_context",
    "instance_info_context",
    "text_parser_context",
    "available_character_context",
    "party_context",
    "guild_context",
    "acc_agent_context",
    "charcontext",
    "cinematic",
    "gamecontext",
    "gameplaycontext",
    "pregamecontext",
    "serverregion",
    "instanceinfo",
    "textparser",
    "availablecharacters",
    "partycontext",
    "guildcontext",
    "accagentcontext",
    "get",
]

# Keep the short facade spelling while using one implementation file.
charcontext = char_context
cinematic = cinematic_context
gamecontext = game_context
gameplaycontext = gameplay_context
pregamecontext = pre_game_context
serverregion = server_region_context
instanceinfo = instance_info_context
textparser = text_parser_context
availablecharacters = available_character_context
partycontext = party_context
guildcontext = guild_context
accagentcontext = acc_agent_context
