"""Port of Reforged's ``Py4GWCoreLib/enums_src/Py4GW_enums.py``.

The source file is transcribed as it stands: the same names in the same order, the same
members, the same comments. Nothing is added and nothing is renamed.

**Enums:** ``Console``.

Imported the way Reforged imports it — ``from .enums_src.Py4GW_enums import X`` there,
``from .enums_src.py4gw_enums import X`` here — by the modules that use those names.
"""
from enum import Enum
from enum import IntEnum

# region Console
class Console:
    class MessageType:
        Info = 0
        Warning = 1
        Error = 2
        Debug = 3
        Success = 4
        Performance = 5
        Notice = 6
