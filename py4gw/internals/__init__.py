"""Reforged's ``native_src/internals`` package, ported.

The source keeps game-format helpers that are not contexts and not bindings here: the
string table and its decoder, and the encoded-string wrappers built on it. The port
mirrors that path so a reader can find the same file in the same place.

Whether the class or module here has a public entry point yet, and what is still to port
from the same source file, is stated in each module's own docstring.
"""

from __future__ import annotations

__all__: list[str] = []
