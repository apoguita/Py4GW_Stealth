"""Readable values and printing for structures read out of the target process.

The context declarations deliberately keep the source field names and their raw
``ctypes`` types so the layouts stay a faithful port.  That makes the raw
attributes awkward to use directly: a wide-character buffer arrives as a
``c_ushort_Array_20`` and an embedded record arrives as another opaque object.

This module adds one shared base class so those values can be read and printed
as data:

    ctx.map_id             # unchanged: the raw field, 449
    ctx.to_dict()          # every field, decoded
    ctx.items()            # the same as (name, value) pairs
    print(ctx)             # every field, one per line

Nothing here changes a layout, an offset, or a field name.  The raw attributes
keep their source types; only the helpers interpret them.
"""

from __future__ import annotations

import ctypes
import sys
from typing import Any, Iterator


def _console_safe(text: str) -> str:
    """Escape characters the active console encoding cannot represent.

    Game text contains names, tags, and chat that a Windows console's default
    encoding cannot represent, and writing those raises ``UnicodeEncodeError``.
    Only the printed form is escaped: ``to_dict()`` and the raw attributes
    always return the real string, so nothing is lost to a program.
    """

    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return text
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return text.encode("ascii", "backslashreplace").decode("ascii")
    return text


def _to_ints(values: Any) -> list[int]:
    """Normalize array elements to integers.

    ``c_char`` arrays yield single-byte ``bytes`` objects rather than integers,
    so both forms have to be accepted.
    """

    result: list[int] = []
    for unit in values:
        if isinstance(unit, (bytes, bytearray)):
            result.append(unit[0])
        else:
            result.append(int(unit))
    return result


def _decode_units(values: Any, width: int) -> str | None:
    """Decode a character array to text, or return ``None`` if it is not text.

    ``None`` means "this is not text, render the numbers instead".  A buffer
    whose terminator is the first unit yields ``None``: it holds no characters,
    so treating it as an empty string would hide real binary content.
    """

    units = _to_ints(values)
    if 0 in units:
        units = units[: units.index(0)]
    if not units:
        return None
    try:
        if width == 1:
            text = bytes(units).decode("latin-1")
        else:
            text = b"".join(
                int(unit).to_bytes(2, "little") for unit in units
            ).decode("utf-16-le", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return None
    if not text:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        return None
    return text


def _is_character_type(element: Any) -> int | None:
    """Return the unit width for a text-capable element type, else ``None``.

    Only wide character types appear here.  ``c_char`` arrays never reach this
    path because ``ctypes`` returns those fields as ``bytes`` directly, and
    ``c_byte``/``c_ubyte`` buffers are binary far more often than textual, so
    they stay numeric.
    """

    if element in (ctypes.c_wchar, ctypes.c_ushort):
        return 2
    return None


def _describe_bytes(value: bytes) -> Any:
    """Return printable bytes as text, and anything else unchanged."""

    text = _decode_units(value, 1)
    return text if text is not None else value


def describe_value(value: Any) -> Any:
    """Return a field value as plain Python data.

    Scalars pass through.  Character arrays become text when they hold text and
    otherwise become a list of numbers.  Other arrays become lists.  Embedded
    records become dictionaries.  Anything else is returned unchanged so an
    unknown type is visible rather than silently rewritten.
    """

    if isinstance(value, ctypes.Array):
        element = getattr(value, "_type_", None)
        width = _is_character_type(element)
        raw = list(value)
        if width is not None:
            text = _decode_units(raw, width)
            if text is not None:
                return text
        if isinstance(element, type) and issubclass(element, ctypes.Structure):
            return [describe_value(item) for item in value]
        return raw
    if isinstance(value, bytes):
        return _describe_bytes(value)
    if isinstance(value, ctypes.Structure):
        return describe_structure(value)
    record = getattr(value, "to_dict", None)
    if callable(record) and isinstance(value, Describable):
        return value.to_dict()
    return value


def describe_structure(structure: ctypes.Structure) -> dict[str, Any]:
    """Return every field of one structure as decoded data."""

    result: dict[str, Any] = {}
    for entry in structure._fields_:
        name = entry[0]
        result[name] = describe_value(getattr(structure, name))
    return result


def _value_text(value: Any, limit: int = 8) -> str:
    """Render one decoded value compactly and safely for the console.

    Long sequences are shortened for the printed form only.  ``to_dict()`` and
    ``describe()`` always return the complete value, so the short form never
    hides data from a caller that asks for it.
    """

    return _console_safe(_render_value(value, limit))


def _render_value(value: Any, limit: int = 8) -> str:
    """Render one decoded value compactly for a single repr line."""

    if isinstance(value, dict):
        inner = ", ".join(f"{key}={_value_text(item)}" for key, item in value.items())
        return f"{{{inner}}}"
    if isinstance(value, (list, tuple)):
        opener, closer = ("(", ")") if isinstance(value, tuple) else ("[", "]")
        if len(value) > limit:
            head = ", ".join(_value_text(item, limit) for item in value[:limit])
            return f"{opener}{head}, ... +{len(value) - limit} more{closer}"
        return opener + ", ".join(_value_text(item, limit) for item in value) + closer
    nested = _nested_fields(value)
    if nested is not None:
        # A record nested inside another record stays on one line, so a large
        # sequence of records still reads as a glance rather than a page.
        inner = ", ".join(
            f"{key}={_value_text(item, limit)}" for key, item in nested.items()
        )
        return f"{type(value).__name__}({inner})"
    return repr(value)


def _nested_fields(value: Any) -> dict[str, Any] | None:
    """Return a nested record's fields as data, or ``None`` if it is not one."""

    if isinstance(value, ctypes.Structure):
        return describe_structure(value)
    if isinstance(value, Describable):
        return value.to_dict()
    return None


class TargetStruct(ctypes.Structure):
    """A target structure whose fields can be read and printed as data.

    Subclasses declare ``_fields_`` exactly as they did with
    ``ctypes.Structure``.  This base adds ``describe()``, ``to_dict()``,
    ``iter_fields()`` and a ``__repr__`` that prints every field, without
    changing the layout or the raw attribute values.

    The accessor is named ``iter_fields`` rather than ``items`` because
    several source layouts contain a field literally named ``items``, and a
    ``ctypes`` field of that name would shadow the method.
    """

    def describe(self) -> dict[str, Any]:
        """Return every field as plain Python data."""

        return describe_structure(self)

    def to_dict(self) -> dict[str, Any]:
        """Return every field as plain Python data.

        Kept alongside ``describe`` so callers can use either spelling.
        """

        return describe_structure(self)

    def iter_fields(self) -> Iterator[tuple[str, Any]]:
        """Yield ``(field_name, value)`` with decoded values, in layout order."""

        for entry in self._fields_:
            name = entry[0]
            yield name, describe_value(getattr(self, name))

    def __repr__(self) -> str:
        lines = [f"{type(self).__name__}("]
        for name, value in self.iter_fields():
            lines.append(f"    {name} = {_value_text(value)}")
        lines.append(")")
        return "\n".join(lines)


def format_value(value: Any, limit: int = 8) -> str:
    """Render one value compactly for display.

    This is the same short form ``repr`` uses, exposed so a caller printing
    values by hand gets the same readable result.  ``to_dict()`` and
    ``describe()`` stay complete, so display shortening never hides data from
    a program.
    """

    return _value_text(value, limit)


class Describable:
    """Mixin giving plain Python records the same data and glance API.

    Snapshots and small value records are ordinary dataclasses rather than
    ``ctypes`` structures, so they do not inherit :class:`TargetStruct`.  This
    mixin gives them the same ``to_dict``, ``iter_fields`` and ``__repr__`` so a
    caller never has to treat the two kinds differently.

    ``__slots__`` is empty on purpose: declaring it keeps slot-only dataclasses
    slot-only, instead of silently reintroducing a per-instance ``__dict__``
    for records that are created in bulk.
    """

    __slots__ = ()

    def iter_fields(self) -> Iterator[tuple[str, Any]]:
        """Yield ``(field_name, value)`` with decoded values."""

        names: list[str]
        dataclass_fields = getattr(type(self), "__dataclass_fields__", None)
        if dataclass_fields is not None:
            names = list(dataclass_fields)
        elif getattr(self, "__dict__", None):
            names = list(vars(self))
        else:
            names = []
            for klass in type(self).__mro__:
                for slot in getattr(klass, "__slots__", ()) or ():
                    if slot not in names:
                        names.append(slot)
        for name in names:
            yield name, describe_value(getattr(self, name, None))

    def describe(self) -> dict[str, Any]:
        """Return every field as plain Python data."""

        return dict(self.iter_fields())

    def to_dict(self) -> dict[str, Any]:
        """Return every field as plain Python data."""

        return dict(self.iter_fields())

    def __repr__(self) -> str:
        lines = [f"{type(self).__name__}("]
        for name, value in self.iter_fields():
            lines.append(f"    {name} = {_value_text(value)}")
        lines.append(")")
        return "\n".join(lines)


__all__ = [
    "Describable",
    "TargetStruct",
    "describe_structure",
    "describe_value",
    "format_value",
]
