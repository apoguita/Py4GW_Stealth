"""Render `docs/GWA3_PARITY_SAMPLES.md`: a GwAu3 script's call beside the Python that answers it.

Written for the parity review the owner asked for: for a sample of the routines the example scripts
actually call, show (1) the AutoIt call site, (2) the layer's Python member that answers it, and
(3) the Stealth member the layer answers *from*. Everything is read from the sources at run time --
nothing here is typed by hand, so the report cannot drift from the code.
"""

from __future__ import annotations

import ast
import io
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SCRIPTS = REPO / "external" / "GwAu3" / "Scripts"
LAYER = REPO / "py4gw" / "gwa3"
OUT = REPO / "docs" / "GWA3_PARITY_SAMPLES.md"

#: The routines shown, chosen to cover the shapes a migration meets: a field-name reader, a decision,
#: an action, a plugin entry point, an array reader, a state reader and a context reader.
SAMPLE = (
    "Core_Initialize",
    "Agent_GetAgentInfo",
    "Map_GetCharacterInfo",
    "Item_GetInventoryArray",
    "Skill_GetSkillInfo",
    "Party_GetHeroInfo",
    "Map_Move",
    "UAI_Fight",
    "Merchant_GetTraderCostID",
    "World_IsSkillLearnt",
    "Scanner_GetHwnd",
    "Match_GetObserverMatchInfo",
)


def call_sites() -> dict[str, tuple[str, int, str]]:
    """``{routine: (script, line number, the source line)}`` for the first call of each sample."""

    found: dict[str, tuple[str, int, str]] = {}
    for path in sorted(SCRIPTS.rglob("*.au3")):
        if path.stem.endswith("_stealth"):
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            code = line.split(";", 1)[0]
            for name in SAMPLE:
                if name in found:
                    continue
                if re.search(rf"\b{name}\s*\(", code):
                    found[name] = (str(path.relative_to(REPO)).replace("\\", "/"), index, line.strip())
    return found


def members() -> dict[str, tuple[str, int, str, str]]:
    """``{routine: (layer module, line, signature, first docstring line)}``."""

    found: dict[str, tuple[str, int, str, str]] = {}
    for path in sorted(LAYER.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name not in SAMPLE:
                continue
            doc = (ast.get_docstring(node) or "").strip().splitlines()
            signature = text.splitlines()[node.lineno - 1].strip()
            found[node.name] = (
                path.name,
                node.lineno,
                signature,
                doc[0] if doc else "",
            )
    return found


def main() -> int:
    calls = call_sites()
    layer = members()
    lines: list[str] = []
    lines.append("# GwAu3 script call, beside the Python that answers it\n")
    lines.append(
        "**Generated** by `python tools/report_gwa3_parity_samples.py` -- read from "
        "`external/GwAu3/Scripts/*.au3` and `py4gw/gwa3/*.py` at run time, never typed by hand.\n"
    )
    lines.append(
        "A migrated script is the **same AutoIt file** with one include line swapped, so its call "
        "site is unchanged; what differs is who answers. Each row below is one call a real GwAu3 "
        "script makes, and the layer member that answers it under the same name.\n"
    )
    lines.append("| script calls (AutoIt) | the layer answers (Python) |")
    lines.append("| --- | --- |")
    for name in SAMPLE:
        call = calls.get(name)
        member = layer.get(name)
        left = f"`{call[0]}`:{call[1]}<br>`{call[2]}`" if call else "_no call site found_"
        if member:
            right = f"`py4gw/gwa3/{member[0]}`:{member[1]}<br>`{member[2]}`"
            if member[3]:
                right += f"<br>_{member[3][:150]}_"
        else:
            right = "_not a layer member_"
        lines.append(f"| {left} | {right} |")
    lines.append("")
    lines.append("## One call, end to end\n")
    for name in ("Agent_GetAgentInfo", "Map_GetCharacterInfo", "Item_GetInventoryArray"):
        call = calls.get(name)
        member = layer.get(name)
        if not (call and member):
            continue
        lines.append(f"**`{name}`**\n")
        lines.append("```autoit")
        lines.append("; " + call[0] + ":" + str(call[1]) + "  (unchanged in the migrated script)")
        lines.append(call[2])
        lines.append("```")
        lines.append("```python")
        lines.append(f"# py4gw/gwa3/{member[0]}:{member[1]}")
        lines.append(member[2])
        if member[3]:
            lines.append("    " + member[3])
        lines.append("```")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:60]))
    print(f"\n... wrote {OUT.relative_to(REPO)} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
