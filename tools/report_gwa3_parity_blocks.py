"""Render `docs/GWA3_PARITY_BLOCKS.md`: whole GwAu3 bodies beside the Python that ports them.

The owner asked to see a *block* of AutoIt beside a *block* of the ported code to judge how similar
they are, so this prints the complete source of a few routines in both languages -- the AutoIt body
read out of `external/GwAu3`, the Python body read out of the layer by `inspect.getsource`, so neither
side can drift from the code.
"""

from __future__ import annotations

import inspect
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

GWAU3 = REPO / "external" / "GwAu3" / "API"
OUT = REPO / "docs" / "GWA3_PARITY_BLOCKS.md"

#: ``(AutoIt file under external/GwAu3, GwAu3 function, the layer's Python member)``. Chosen to cover
#: the shapes a reviewer meets: an action, a two-word predicate, a field-name reader over a record, and
#: a decision with guards.
PAIRS: tuple[tuple[str, str, str], ...] = (
    ("Cmd/GwAu3_Cmd_Map.au3", "Map_Move", "Map_Move"),
    ("Modules/Data/GwAu3_Data_Merchant.au3", "Merchant_IsValidQuote", "Merchant_IsValidQuote"),
    ("Modules/Data/GwAu3_Data_World.au3", "World_IsSkillLearnt", "World_IsSkillLearnt"),
    ("Modules/Data/GwAu3_Data_Map.au3", "Map_GetCharacterInfo", "Map_GetCharacterInfo"),
    ("Modules/Data/GwAu3_Data_Party.au3", "Party_GetMoraleInfo", "Party_GetMoraleInfo"),
)


def autoit_body(relative: str, function: str) -> str:
    """The whole ``Func function(...)`` .. ``EndFunc`` block, as the source writes it."""

    for path in GWAU3.rglob(pathlib.Path(relative).name):
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(
            rf"^Func\s+{re.escape(function)}\s*\(.*?^EndFunc[^\n]*",
            text,
            re.S | re.M,
        )
        if match:
            return match.group(0).rstrip()
    return f"; {function} not found in {relative}"


def python_body(function: str) -> str:
    """The layer's own source for that name -- whatever module of the layer defines it."""

    from py4gw.gwa3.bridge import layer_surface

    member = layer_surface().get(function)
    if member is None:
        return f"# {function} is not a member of the layer"
    return inspect.getsource(member).rstrip()


def main() -> int:
    lines: list[str] = []
    lines.append("# The same routine, in AutoIt and in the port\n")
    lines.append(
        "**Generated** by `python tools/report_gwa3_parity_blocks.py` -- the AutoIt side is read from "
        "`external/GwAu3`, the Python side from the layer with `inspect.getsource`, so this cannot "
        "describe anything but the code as it stands.\n"
    )
    lines.append(
        "A migrated script keeps its own AutoIt body; these pairs put GwAu3's routine beside the "
        "Stealth member that answers the same call, so the shape can be compared directly.\n"
    )
    for relative, function, member in PAIRS:
        lines.append(f"## `{function}`\n")
        lines.append(f"*AutoIt: `external/GwAu3/API/{relative}`*\n")
        lines.append("```autoit")
        lines.append(autoit_body(relative, function))
        lines.append("```\n")
        lines.append("*Ported:*\n")
        lines.append("```python")
        lines.append(python_body(member))
        lines.append("```\n")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n... wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
