"""Project tooling that is not part of the ported surface.

Nothing in this package exists in Reforged or Native. It is here so that
project-owned conveniences live outside the ported modules and are never
mistaken for the source. See ``docs/PORTING_RULES.md``. If a member here
starts to look like part of the accessor contract, that is the signal it
does not belong in this project at all.
"""

from .target_struct import (
    Describable,
    TargetStruct,
    describe_structure,
    describe_value,
    format_value,
)

__all__ = [
    "Describable",
    "TargetStruct",
    "describe_structure",
    "describe_value",
    "format_value",
]
