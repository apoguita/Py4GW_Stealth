"""Port of Reforged's ``Py4GWCoreLib/enums_src/Player_enums.py``.

The source file is transcribed as it stands: the same names in the same order, the same
members, the same comments. Nothing is added and nothing is renamed.

**Enums:** ``PlayerStatus``.

Imported the way Reforged imports it — ``from .enums_src.Player_enums import X`` there,
``from .enums_src.player_enums import X`` here — by the modules that use those names.
"""
from enum import IntEnum


class PlayerStatus(IntEnum):
    Offline = 0
    Online = 1
    DoNotDisturb = 2
    DND = 2
    Away = 3

    @classmethod
    def from_value(cls, status):
        if isinstance(status, cls):
            return status
        if isinstance(status, str):
            normalized = status.strip().lower().replace(" ", "_").replace("-", "_")
            if normalized == "offline":
                return cls.Offline
            if normalized == "online":
                return cls.Online
            if normalized in ("do_not_disturb", "donotdisturb", "dnd"):
                return cls.DoNotDisturb
            if normalized == "away":
                return cls.Away
            return None
        try:
            return cls(int(status))
        except Exception:
            return None

    @property
    def display_name(self) -> str:
        if self == PlayerStatus.DoNotDisturb:
            return "do_not_disturb"
        return self.name.lower()
