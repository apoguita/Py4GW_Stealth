"""Measure how close a GwAu3 script is to the same script running on this layer.

The whole point of ``py4gw/gwa3`` is *parity of usage*: a GwAu3 author should be able to keep their
script, change as little as possible, and have it run here. This tool answers that with numbers rather
than an impression, by reading GwAu3's own scripts and this layer's surface and reporting:

1. **Name parity** -- of every ``$GC_*`` constant the scripts use, how many does the layer define?
2. **Call parity** -- of every GwAu3 routine they call, how many has the layer addressed at all (a
   declared wrapper), and how many does it actually implement? Measured by **distinct routine** and by
   **call site**, because a script that calls one built routine 80 times is in a different position
   from one that calls 80 unbuilt routines once each.
3. **Text parity** -- how many lines survive a migration unchanged, measured by producing the migrated
   script and diffing it. This number is high *by construction*, and that is the point of keeping
   GwAu3's names: it is not evidence that the script works, and the report says so.

Nothing here judges whether a routine *works*; that is the route map's job, and the live run's.

    python tools/analyze_gwa3_example_parity.py            # print
    python tools/analyze_gwa3_example_parity.py --write     # also write the report and examples

Output: ``docs/GWA3_EXAMPLE_PARITY.md``; with ``--write``, ``tools/gwa3_examples/`` holds each script
with the one edit a migration needs.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GWAU3_ROOT = REPO_ROOT / "external" / "GwAu3"
SCRIPTS_ROOT = GWAU3_ROOT / "Scripts"
API_ROOT = GWAU3_ROOT / "API"
LAYER_ROOT = REPO_ROOT / "py4gw" / "gwa3"
AUTOIT_UDF = REPO_ROOT / "tools" / "autoit" / "Stealth_GwAu3.au3"
CONSTANTS = LAYER_ROOT / "constants.py"
OUTPUT_PATH = REPO_ROOT / "docs" / "GWA3_EXAMPLE_PARITY.md"
MIGRATED_ROOT = REPO_ROOT / "tools" / "gwa3_examples"

#: Where the migrated copy of a script goes: **beside the original**, with a `_stealth` suffix.
#:
#: A GwAu3 script's include graph is relative to its own directory -- the multi-launcher pulls in
#: `../../Utilities/_GUICtrlEmoji/_GUICtrlEmoji.au3`, the ImGui example pulls in
#: `../../Utilities/ImGui/ImGui.au3` -- so a copy placed anywhere else compiles to a wall of
#: `undeclared global variable` on lines the migration never touched. Measured: the launcher checked
#: clean as shipped and reported 22 undeclared globals when copied to `tools/gwa3_examples/`, all of
#: them the emoji constants from the include that could no longer be found. Migrating *in place* is
#: both what this measures honestly and what a migrating user actually does.
MIGRATED_SUFFIX = "_stealth"

#: `Func Name(` -- GwAu3's own declaration, which is the only record of its surface.
FUNC_DECL = re.compile(r"^Func\s+(?P<name>[A-Za-z_]\w*)\s*\(", re.MULTILINE)

#: A constant the layer is supposed to carry.
CONSTANT = re.compile(r"\$GC_[A-Za-z0-9_]+")

#: `GC_X = 1` -- a module-level assignment in `constants.py`.
PY_CONSTANT = re.compile(r"^(?P<name>GC_[A-Za-z0-9_]+)\s*=", re.MULTILINE)

#: The AutoIt UDF's own markers, so its implemented block can be read without parsing AutoIt.
AUTOIT_IMPLEMENTED_MARK = "; --- implemented by py4gw/gwa3 ---"
AUTOIT_UNBUILT_MARK = "; --- declared by GwAu3, not built by this layer yet ---"

#: The include line a migration edits.
INCLUDE_LINE = re.compile(r"^\s*#\s*include\s+.*$", re.MULTILINE)


@dataclass
class Example:
    """One GwAu3 script and what it asks of the API."""

    path: Path
    text: str
    calls: Counter[str] = field(default_factory=Counter)
    constants: set[str] = field(default_factory=set)

    @property
    def relative(self) -> str:
        return str(self.path.relative_to(GWAU3_ROOT)).replace("\\", "/")

    @property
    def lines(self) -> int:
        return len(self.text.splitlines())

    @property
    def call_sites(self) -> int:
        return sum(self.calls.values())

    @property
    def distinct_calls(self) -> int:
        return len(self.calls)

    def implements(self, implemented: set[str]) -> tuple[int, int]:
        """``(distinct implemented, call sites implemented)``."""

        names = [name for name in self.calls if name in implemented]
        return len(names), sum(self.calls[name] for name in names)


def gwau3_surface() -> dict[str, tuple[str, int]]:
    """Every function GwAu3 declares, from its own ``Func`` lines."""

    surface: dict[str, tuple[str, int]] = {}
    for path in sorted(API_ROOT.rglob("*.au3")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in FUNC_DECL.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            surface.setdefault(
                match.group("name"),
                (str(path.relative_to(GWAU3_ROOT)).replace("\\", "/"), line),
            )
    return surface


def layer_constants() -> set[str]:
    """The `$GC_*` names this layer defines, read from the generated constants module."""

    text = CONSTANTS.read_text(encoding="utf-8")
    return {f"${match.group('name')}" for match in PY_CONSTANT.finditer(text)}


def autoit_surface() -> tuple[set[str], set[str]]:
    """``(implemented, declared)`` for the AutoIt UDF, read from its own two marker comments.

    **The hand-written AutoIt block counts as implemented, and that was a measurement defect until
    now.** ``tools/autoit/generate_stealth_udf.py`` emits three regions: the routines whose work is
    AutoIt-side (`Core_AutoStart` calls the script's own `StartBot()`, `Log_*` renders into the script's
    control, `Core_GetGuildWarsWindow` asks Windows for the client's window), then the bridged wrappers,
    then the declared-but-unbuilt ones. The two markers delimit the middle region, so every function
    *before* the first marker was counted as neither implemented nor built -- and five names a script
    calls (`Core_AutoStart`, `Log_SetDebugMode`, `Log_SetCallback`, `Log_Message`,
    `Core_GetGuildWarsWindow`) were reported as gaps for months while being complete. They are `Func`
    bodies in the same file; a script that calls them works.
    """

    text = AUTOIT_UDF.read_text(encoding="utf-8")
    implemented_at = text.index(AUTOIT_IMPLEMENTED_MARK)
    unbuilt_at = text.index(AUTOIT_UNBUILT_MARK)
    hand_written = set(re.findall(r"Func\s+([A-Za-z_]\w*)\s*\(", text[:implemented_at]))
    bridged = set(re.findall(r"Func\s+([A-Za-z_]\w*)\s*\(", text[implemented_at:unbuilt_at]))
    implemented = hand_written | bridged
    declared = implemented | set(re.findall(r"Func\s+([A-Za-z_]\w*)\s*\(", text[unbuilt_at:]))
    return implemented, declared


def python_surface() -> set[str]:
    """Every name the layer's Python modules export."""

    names: set[str] = set()
    for path in sorted(LAYER_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        block = re.search(r"__all__\s*=\s*\[(?P<body>.*?)\]", text, re.DOTALL)
        if block is None:
            continue
        names.update(re.findall(r'"([^"]+)"', block.group("body")))
    return names


def read_example(path: Path, surface: dict[str, tuple[str, int]]) -> Example:
    """One script's call sites and constants, comments excluded."""

    text = path.read_text(encoding="utf-8", errors="replace")
    example = Example(path=path, text=text)
    for line in text.splitlines():
        code = line.split(";", 1)[0]
        for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", code):
            if name in surface:
                example.calls[name] += 1
        example.constants.update(CONSTANT.findall(code))
    return example


def migrate(example: Example, implemented: set[str], declared: set[str]) -> str:
    """The same script pointed at this layer, with the changes a migration actually needs.

    **One line changes**: the include. GwAu3's own ``#include "../../API/_GwAu3.au3"`` becomes a
    relative path to this layer's UDF, and a header says which of the script's calls the layer answers
    today. Everything else -- every identifier, every argument, every ``$GC_*`` -- is untouched, and
    that is the paragraph this exercise exists to be able to write.
    """

    target = example.path.with_name(example.path.stem + MIGRATED_SUFFIX + example.path.suffix)
    relative_include = os.path.relpath(AUTOIT_UDF, target.parent).replace("\\", "/")

    missing = sorted(name for name in example.calls if name not in implemented)
    unknown = sorted(name for name in example.calls if name not in declared)
    header = [
        "; ---- migrated to Py4GW_Stealth by tools/analyze_gwa3_example_parity.py ----",
        "; The only edit is the include: GwAu3's API module is replaced by this layer's UDF, which",
        "; declares the same names. Of the "
        f"{example.distinct_calls} GwAu3 routines this script calls, "
        f"{example.distinct_calls - len(missing)} "
        f"{'is' if example.distinct_calls - len(missing) == 1 else 'are'} implemented by the layer and "
        f"{len(missing)} {'is' if len(missing) == 1 else 'are'}",
        "; declared but not built yet -- a call to one of those sets @error and returns GwAu3's own",
        "; empty shape, so a script that checks @error can tell.",
        ";",
    ]
    if missing:
        header.append("; Not built yet: " + ", ".join(missing))
    if unknown:
        header.append("; ** Not declared by this layer's UDF at all: " + ", ".join(unknown))
    header.append("; ---------------------------------------------------------------------------")

    body = INCLUDE_LINE.sub(f'#include "{relative_include}"', example.text, count=1)
    return "\n".join(header) + "\n" + body


def migrated_path(example: Example) -> Path:
    """Where the migrated copy of one script is written."""

    return example.path.with_name(example.path.stem + MIGRATED_SUFFIX + example.path.suffix)


def diff_counts(original: str, migrated: str) -> tuple[int, int]:
    """``(identical, total)`` lines between the original and the migrated script."""

    before = original.splitlines()
    after = migrated.splitlines()
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    identical = sum(block.size for block in matcher.get_matching_blocks())
    return identical, len(before)


def called_surface() -> Counter[str]:
    """Every GwAu3 function the whole checkout *calls*, declarations excluded.

    Wider than the example scripts on purpose: this is the surface a wrapper would have to exist for
    before an arbitrary GwAu3 script can so much as load.
    """

    declared = gwau3_surface()
    called: Counter[str] = Counter()
    for path in sorted(GWAU3_ROOT.rglob("*.au3")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            code = line.split(";", 1)[0]
            if code.lstrip().lower().startswith("func "):
                continue  # a declaration is not a call
            for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", code):
                if name in declared:
                    called[name] += 1
    return called


def analyse() -> tuple[str, list[str]]:
    """The report, and the lines to print."""

    surface = gwau3_surface()
    constants = layer_constants()
    implemented, declared = autoit_surface()
    py_names = python_surface()
    # Every name GwAu3 mentions as a declaration, so a constant this layer does not define can be
    # told apart from one GwAu3 never declared at all.
    declared_names: set[str] = set()
    for path in sorted(API_ROOT.rglob("*.au3")):
        body = path.read_text(encoding="utf-8", errors="replace")
        declared_names.update(re.findall(r"\$(GC_[A-Za-z0-9_]+)", body))

    examples = [
        read_example(path, surface) for path in sorted(SCRIPTS_ROOT.rglob("*.au3")) if path.is_file()
    ]

    per_example = []
    union: Counter[str] = Counter()
    for example in examples:
        distinct_done, sites_done = example.implements(implemented)
        missing = sorted(name for name in example.calls if name not in implemented)
        unknown = sorted(name for name in example.calls if name not in declared)
        identical, total = diff_counts(example.text, migrate(example, implemented, declared))
        per_example.append(
            {
                "example": example,
                "distinct_done": distinct_done,
                "sites_done": sites_done,
                "missing": missing,
                "unknown": unknown,
                "identical": identical,
                "total": total,
                "constants": len(example.constants),
                "constants_done": len(example.constants & constants),
            }
        )
        union.update(example.calls)

    out: list[str] = []
    out.append("# How close a GwAu3 script is to running on this layer\n")
    out.append(
        "**Generated** by `python tools/analyze_gwa3_example_parity.py` — do not edit by hand.\n"
    )
    out.append(
        "This is the measurement behind the layer's stated purpose: *GwAu3 supplies the names and the "
        "usage; this project supplies the implementation*. It reads GwAu3's own scripts from "
        "`external/GwAu3/Scripts/`, counts what they call, and resolves every name against this "
        "layer's surface. It is a **static** measurement: it says what would resolve, not what works. "
        "What works is the route map's per-function tier and the live run's evidence.\n"
    )
    out.append("## The two surfaces\n")
    out.append("| | Count |")
    out.append("| --- | --- |")
    out.append(f"| Functions GwAu3 declares (`external/GwAu3/API/**/*.au3`) | {len(surface)} |")
    out.append(f"| `$GC_*` constants this layer defines (`py4gw/gwa3/constants.py`) | {len(constants)} |")
    out.append(
        f"| Names this layer's Python modules export | {len(py_names)} |"
    )
    out.append(
        f"| AutoIt wrappers `tools/autoit/Stealth_GwAu3.au3` declares | {len(declared)} |"
    )
    out.append(f"| — of those, **implemented** | **{len(implemented)}** |")
    out.append("")

    out.append("## What the scripts call\n")
    out.append(
        "| Script | Lines | Distinct calls | Call sites | Routines implemented | Call sites implemented | Constants used | Constants defined | Lines unchanged by migration |"
    )
    out.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in per_example:
        example: Example = row["example"]
        out.append(
            f"| `{example.relative}` | {example.lines} | {example.distinct_calls} | "
            f"{example.call_sites} | {row['distinct_done']} | {row['sites_done']} | "
            f"{row['constants']} | {row['constants_done']} | "
            f"{row['identical']}/{row['total']} |"
        )
    out.append("")

    sites = sum(row["example"].call_sites for row in per_example)
    sites_done = sum(row["sites_done"] for row in per_example)
    distinct = len(union)
    distinct_done = len([name for name in union if name in implemented])
    constants_used = set()
    for row in per_example:
        constants_used |= row["example"].constants

    out.append("## The number that matters\n")
    out.append(
        f"Across every script in `external/GwAu3/Scripts/`, **{distinct} distinct GwAu3 routines** are "
        f"called, in **{sites} call sites**. This layer implements **{distinct_done} of those "
        f"{distinct} routines** ({100.0 * distinct_done / max(1, distinct):.1f}%), covering "
        f"**{sites_done} of {sites} call sites** "
        f"({100.0 * sites_done / max(1, sites):.1f}%). Of the "
        f"**{len(constants_used)} distinct `$GC_*` constants** they use, this layer defines "
        f"**{len(constants_used & constants)} ({100.0 * len(constants_used & constants) / max(1, len(constants_used)):.1f}%)**.\n"
    )
    out.append(
        "**Text parity is high and that is by construction, not by achievement.** A migration edits "
        "the `#include` and nothing else, so nearly every line is identical -- that is precisely what "
        "keeping GwAu3's names and argument order buys. A script can be pointed at this layer, load, "
        "and call routines that are not built yet; those calls set `@error` and return GwAu3's empty "
        "shape. **Text parity is not call parity**, and call parity is the table above.\n"
    )

    out.append("## What the scripts call that this layer does not answer\n")
    out.append(
        "Grouped by what the routines are, because the groups are the work in different sizes. The "
        "`Cmd_*` and `Data_*` families are the layer's declared scope; the framework groups below are "
        "**not in it yet** and are what a real script reaches for first.\n"
    )
    groups: Counter[str] = Counter()
    for name in union:
        if name in implemented:
            continue
        prefix = name.split("_", 1)[0]
        groups[prefix] += union[name]
    out.append("| Prefix | Call sites not answered |")
    out.append("| --- | --- |")
    for prefix, count in groups.most_common(20):
        out.append(f"| `{prefix}_` | {count} |")
    out.append("")

    called = called_surface()
    undeclared_calls = sorted(name for name in called if name not in declared)
    out.append("## The wrapper surface a migration needs before a script will even load\n")
    out.append(
        f"AutoIt resolves function names when it compiles a script, and a call to a function that is "
        f"declared **nowhere** is a **fatal error, not a call that returns zero** — measured: "
        f"`tools/autoit/probe_undeclared_call.au3` calls `Core_Initialize` and the interpreter answers "
        f"`Unknown function name.` and exits 1 without running the file (`tools/autoit/READINGS.md`). "
        f"So a migration needs a wrapper to *exist* for every GwAu3 function a script calls, whether or "
        f"not this layer can answer it: a declared wrapper returns GwAu3's empty shape and sets `@error` "
        f"with the reason, which a script can act on; an undeclared one stops the script cold.\n"
    )
    out.append("| | Count |")
    out.append("| --- | --- |")
    out.append(f"| GwAu3 functions the whole checkout calls | {len(called)} |")
    out.append(f"| — declared by this layer's UDF | {len(called) - len(undeclared_calls)} |")
    out.append(f"| — **called and not declared at all** | **{len(undeclared_calls)}** |")
    out.append("")
    prefixes: Counter[str] = Counter()
    for name in undeclared_calls:
        prefixes[name.split("_", 1)[0]] += 1
    out.append("| Prefix | Named and not declared |")
    out.append("| --- | --- |")
    for prefix, count in prefixes.most_common(20):
        out.append(f"| `{prefix}_` | {count} |")
    out.append("")

    undefined = sorted(constants_used - constants)
    out.append("## Constants the scripts use that this layer does not define\n")
    if not undefined:
        out.append("_(none)_\n")
    else:
        declared_anywhere = {
            name for name in undefined if name.lstrip("$") in declared_names
        }
        out.append("| Constant | Declared by GwAu3? |")
        out.append("| --- | --- |")
        for name in undefined:
            out.append(
                f"| `{name}` | {'yes — a gap in this layer' if name in declared_anywhere else '**no** — a dangling use in GwAu3 itself, so there is nothing to copy'} |"
            )
        out.append("")
        if not declared_anywhere:
            out.append(
                "All of them are **used by GwAu3's own scripts and declared nowhere in its API**: they "
                "are dangling references in the source, not names this layer dropped. Defining them "
                "here would invent a value GwAu3 never states, which is the one thing this layer will "
                "not do.\n"
            )

    for row in per_example:
        example = row["example"]
        if not example.distinct_calls:
            out.append(
                f"### `{example.relative}`\n\n"
                "Calls no GwAu3 API function: it is a standalone launcher that does not include the "
                "API module. Nothing to migrate.\n"
            )
            continue
        out.append(f"### `{example.relative}`\n")
        out.append(
            f"* **Implemented ({row['distinct_done']}):** "
            + (", ".join(f"`{n}`" for n in sorted(n for n in example.calls if n in implemented)) or "—")
        )
        out.append(
            f"* **Declared but not built ({len(row['missing'])}):** "
            + (", ".join(f"`{n}`" for n in row["missing"]) or "—")
        )
        out.append(
            f"* **Not in this layer's UDF at all ({len(row['unknown'])}):** "
            + (", ".join(f"`{n}`" for n in row["unknown"]) or "—")
        )
        out.append("")

    return "\n".join(out) + "\n", [
        f"{row['example'].relative}: {row['example'].distinct_calls} distinct calls, "
        f"{row['distinct_done']} implemented, {row['sites_done']}/{row['example'].call_sites} call "
        f"sites answered"
        for row in per_example
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the report and the migrated scripts")
    args = parser.parse_args()

    report, lines = analyse()
    for line in lines:
        print(line)

    if args.write:
        OUTPUT_PATH.write_text(report, encoding="utf-8")
        print(f"\nwrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")

        if MIGRATED_ROOT.is_dir():
            for stale in MIGRATED_ROOT.glob("*.au3"):
                stale.unlink()
            MIGRATED_ROOT.rmdir()

        surface = gwau3_surface()
        implemented, declared = autoit_surface()
        written = 0
        for path in sorted(SCRIPTS_ROOT.rglob("*.au3")):
            if not path.is_file():
                continue
            # **A migrated copy is not an input.** Without this skip the walk rewrites its own output as
            # `<name>_stealth_stealth.au3`, and the next run doubles it again -- measured 2026-10-10.
            if path.stem.endswith(MIGRATED_SUFFIX):
                continue
            example = read_example(path, surface)
            migrated_path(example).write_text(
                migrate(example, implemented, declared), encoding="utf-8"
            )
            written += 1
        print(
            f"wrote {written} migrated scripts beside their originals in "
            f"{SCRIPTS_ROOT.relative_to(REPO_ROOT)} as <name>{MIGRATED_SUFFIX}.au3"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
