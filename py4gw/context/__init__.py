"""Guild Wars context readers and external array views."""

from . import char_context
from . import cinematic_context
from . import game_context
from . import gameplay_context
from . import pre_game_context
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

__all__ = [
    "CharContext",
    "CharContextStruct",
    "Cinematic",
    "CinematicStruct",
    "GameContext",
    "GameContextStruct",
    "GameplayContext",
    "GameplayContextStruct",
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
    "char_context",
    "cinematic_context",
    "game_context",
    "gameplay_context",
    "pre_game_context",
    "charcontext",
    "cinematic",
    "gamecontext",
    "gameplaycontext",
    "pregamecontext",
    "get",
]

# Keep the short facade spelling while using one implementation file.
charcontext = char_context
cinematic = cinematic_context
gamecontext = game_context
gameplaycontext = gameplay_context
pregamecontext = pre_game_context
