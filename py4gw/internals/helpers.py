"""Shared helpers, ported from Reforged's ``native_src/internals/helpers.py`` (33 lines).

Two functions, and both are used by name across the ported library: ``read_wstr`` for a
client string at a pointer a structure handed over, ``encoded_wstr_to_str`` for making an
*encoded* string readable by escaping the codepoints that are not printable.

**One adaptation, and it is the execution model.** The source's ``read_wstr`` is
``ctypes.wstring_at(ptr)``: it runs inside the client, so the pointer is an address in its own
process and the read is a dereference. This port runs outside the client, so the read goes
through the connected client's reader — and because that reader is a bounded
``ReadProcessMemory``, it stops at the terminator or after ``limit`` code units, one code unit
at a time. Reading a chunk ahead would speculate past the terminator into a page that may not
be mapped, which is a failure ``wstring_at`` cannot have; ``FrameArray.read_wide_string``
reads a client string the same way.
"""

from __future__ import annotations

#: ``wchar_t`` on the x86 client: a UTF-16 code unit.
_WIDE_CHAR_SIZE = 2

#: The cap on one ``read_wstr``. The client's own labels are read under the same order of
#: limit (``py4gw/ui/frame.py``), and a pointer that is not a string costs this many code
#: units rather than an unbounded walk.
WIDE_STRING_LIMIT = 32768


def read_wstr(ptr: int, limit: int = WIDE_STRING_LIMIT) -> str | None:
    """Read the NUL-terminated UTF-16 string at ``ptr``, or ``None`` when there is none.

    ``None`` for a null pointer, which is the source's own answer, and also when no client is
    connected — the source cannot be in that state, because it is running inside one.
    """

    if not ptr:
        return None

    from ..client import current_client

    client = current_client()
    if client is None:
        return None
    reader = client.reader

    code_units: list[int] = []
    for index in range(limit):
        raw = reader.read(ptr + index * _WIDE_CHAR_SIZE, _WIDE_CHAR_SIZE)
        unit = int.from_bytes(raw, "little")
        if unit == 0:
            break
        code_units.append(unit)

    return "".join(chr(value) for value in code_units)


def encoded_wstr_to_str(s: str | None) -> str | None:
    """
    Make GW encoded strings visible by escaping
    control / non-printable characters.
    """
    if s is None:
        return None

    out = []
    for ch in s:
        o = ord(ch)

        # Printable ASCII
        if 32 <= o <= 126:
            out.append(ch)
        # Newlines / tabs (keep readable)
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        # Everything else: escape
        else:
            out.append(f"\\x{o:04X}")

    return "".join(out)
