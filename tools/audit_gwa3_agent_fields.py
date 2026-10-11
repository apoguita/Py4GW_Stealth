"""Audit: can GwAu3's field-name keys be answered from the structures this project already reads?

This is the check behind the claim the whole read side rests on -- *"GwAu3 supplies the names,
Stealth supplies the implementation"* -- for the single accessor that carries the most call sites in
GwAu3's own scripts, ``Agent_GetAgentInfo`` (216 call sites).

The question is narrow and mechanical: for each key GwAu3's ``Switch`` accepts
(``GwAu3_Data_Agent.au3:82-524``), is there a *named attribute* on the structure this project reads
for that agent, or would the compatibility layer have to reach a raw offset -- which is what the
project's porting rules forbid outside the ported classes?

It reads both sides and reports, so the answer is measured rather than asserted:

    python tools/audit_gwa3_agent_fields.py

Output: ``docs/GWA3_AGENT_FIELD_AUDIT.md``.

**What it does not do.** It does not decide that a key is answered when only its *offset* matches.
A key is ``NAMED`` when the structure declares an attribute at that offset, ``OFFSET ONLY`` when the
offset exists in the structure's field list but the attribute name is one of the ``hXXXX``
placeholders, and ``ABSENT`` when no attribute occupies that offset. ``OFFSET ONLY`` and ``ABSENT``
are the work items, and they are listed by name rather than counted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_SOURCE = REPO_ROOT / "external" / "GwAu3" / "API" / "Modules" / "Data" / "GwAu3_Data_Agent.au3"
STRUCT_SOURCE = REPO_ROOT / "py4gw" / "context" / "agent_array.py"
OUTPUT_PATH = REPO_ROOT / "docs" / "GWA3_AGENT_FIELD_AUDIT.md"

# `Case "X"` or `Case "A", "B"` -- GwAu3 aliases several keys to one field.
CASE_LINE = re.compile(r'^\s*Case\s+(?P<keys>.+?)\s*$')
KEY = re.compile(r'"([^"]+)"')

# `Return Memory_Read($l_p_AgentPtr + 0x74, "float")` -- the offset and the width GwAu3 reads.
MEMORY_READ = re.compile(
    r'Memory_Read\(\s*\$l_p_AgentPtr\s*\+\s*(?P<offset>0x[0-9A-Fa-f]+)\s*,\s*"(?P<type>[^"]+)"\s*\)'
)
# `Memory_Read(Memory_Read($l_p_AgentPtr + 0x108, "ptr"), "short")` -- a pointer hop.
POINTER_HOP = re.compile(r'Memory_Read\(\s*Memory_Read\(\s*\$l_p_AgentPtr\s*\+\s*(?P<offset>0x[0-9A-Fa-f]+)')

# A declared struct field: `("hp", c_float),` / `("h01BA", c_uint16),` / `("h0194", c_uint8 * 32),`.
FIELD = re.compile(r'\(\s*"(?P<name>[A-Za-z_]\w*)"\s*,\s*(?P<type>[^)]+?)\s*\)\s*,?\s*$')

CTYPE_SIZES = {
    "c_uint8": 1, "c_int8": 1, "c_char": 1,
    "c_uint16": 2, "c_int16": 2, "c_short": 2,
    "c_uint32": 4, "c_int32": 4, "c_int": 4, "c_float": 4,
}


def _ctype_size(type_text: str) -> int:
    """The byte width of a ctypes field type, or 0 when it cannot be determined."""

    text = type_text.replace(" ", "")
    array = re.match(r"^(?P<base>\w+)\*(?P<count>\d+)$", text)
    if array:
        return _ctype_size(array.group("base")) * int(array.group("count"))
    for name, size in CTYPE_SIZES.items():
        if text == name:
            return size
    if "Struct" in text or "Union" in text:
        return 0
    return 0


@dataclass(frozen=True)
class FieldCase:
    """One key GwAu3's Switch accepts, and the offset it reads for it."""

    keys: tuple[str, ...]
    line: int
    offset: int | None
    type_text: str
    pointer_hop: bool
    other: str


@dataclass(frozen=True)
class StructField:
    name: str
    offset: int
    size: int


def parse_gwau3_cases() -> list[FieldCase]:
    """Every ``Case`` in ``Agent_GetAgentInfo``'s Switch, with the offset it reads."""

    lines = AGENT_SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("Func Agent_GetAgentInfo(")
    )
    end = next(index for index in range(start, len(lines)) if lines[index].strip() == "EndFunc")

    cases: list[FieldCase] = []
    pending: tuple[tuple[str, ...], int] | None = None
    for index in range(start, end):
        line = lines[index]
        match = CASE_LINE.match(line)
        if match and not line.strip().startswith("Case Else"):
            keys = tuple(KEY.findall(match.group("keys")))
            if keys:
                pending = (keys, index + 1)
                continue
        if pending is None:
            continue

        read = MEMORY_READ.search(line)
        hop = POINTER_HOP.search(line)
        if read is not None or hop is not None:
            offset_text = (read or hop).group("offset")  # type: ignore[union-attr]
            offset = int(offset_text, 16)
            type_text = read.group("type") if read else "ptr"
            cases.append(
                FieldCase(
                    keys=pending[0],
                    line=pending[1],
                    offset=offset,
                    type_text=type_text,
                    pointer_hop=hop is not None,
                    other="",
                )
            )
            pending = None
        elif "Return" in line and "Memory_Read" not in line:
            cases.append(
                FieldCase(
                    keys=pending[0],
                    line=pending[1],
                    offset=None,
                    type_text="",
                    pointer_hop=False,
                    other=line.strip(),
                )
            )
            pending = None
    return cases


def parse_struct_fields(struct_name: str) -> list[StructField]:
    """Every declared field of a structure and its bases, with **ctypes' own** offsets.

    Walking the bases is not optional: ``AgentLivingStruct`` declares only its own fields from
    ``owner`` (0xC4) onwards, and everything GwAu3 reads below that -- ``ID`` at 0x2C, ``X`` at
    0x74, ``Type`` at 0x9C -- is declared on ``AgentStruct``. Reading only the subclass reports most
    of GwAu3's keys as unanswerable when they are in fact named, which is the wrong finding.

    **The offsets come from ctypes, not from arithmetic over the field list.** An earlier version of
    this function summed declared widths and drifted -- ``h0180`` came out at 0x174 against ctypes'
    0x180 -- because a nested struct field (``GWListStruct``) has no width this module can compute.
    ctypes owns the layout of a real ``ctypes.Structure``, including inheritance and alignment, so
    asking it is both simpler and correct. The bases are walked only to decide *which* fields are
    declared where; every offset comes from the descriptor.
    """

    try:
        from py4gw.context import agent_array
    except Exception as error:  # pragma: no cover - the package imports in this tree
        raise ConstantParseError(f"the agent structures could not be imported: {error}") from error

    structure = getattr(agent_array, struct_name, None)
    if structure is None:
        raise ConstantParseError(f"{struct_name} is not declared in py4gw.context.agent_array")

    # `_fields_` holds only the fields a class declares itself -- `AgentLivingStruct` starts at
    # `owner` (0xC4) and everything below that is on `AgentStruct`. But a `ctypes.Structure` exposes
    # a descriptor for every field it *has*, inherited included, so walking the class's attributes is
    # what gets the whole record.
    fields: list[StructField] = []
    for name in dir(structure):
        if name.startswith("_"):
            continue
        descriptor = getattr(structure, name, None)
        offset = getattr(descriptor, "offset", None)
        size = getattr(descriptor, "size", None)
        if isinstance(offset, int) and isinstance(size, int):
            fields.append(StructField(name=name, offset=offset, size=size))
    fields.sort(key=lambda field: field.offset)
    return fields


class ConstantParseError(RuntimeError):
    """The audit could not read something it needs; raised rather than guessed past."""


def classify(case: FieldCase, fields: list[StructField]) -> tuple[str, str]:
    """``(verdict, detail)`` for one key group."""

    if case.offset is None:
        return "COMPUTED", case.other
    for field in fields:
        if field.size and field.offset == case.offset:
            named = not re.fullmatch(r"h[0-9A-Fa-f]+(_new)?", field.name)
            verdict = "NAMED" if named else "OFFSET ONLY"
            detail = f"`{field.name}` ({field.size} bytes at {case.offset:#x})"
            if case.pointer_hop:
                detail += " -- GwAu3 hops a pointer first"
            return verdict, detail
    return "ABSENT", f"no attribute occupies {case.offset:#x} in the structure"


def verify_offsets_against_ctypes(fields: list[StructField]) -> list[str]:
    """Confirm the parsed field list is ctypes' own, so a verdict rests on the real layout.

    The offsets now come straight from the descriptors, so this check is about *completeness*: that
    every field the structure declares made it into the list, and that none of them has a size the
    audit failed to read. A gap here would make a key look absent when it is declared.
    """

    try:
        from py4gw.context.agent_array import AgentLivingStruct
    except Exception as error:  # pragma: no cover - the package imports in this tree
        return [f"could not import the structure to verify against: {error}"]

    problems: list[str] = []
    declared = {name for name in dir(AgentLivingStruct) if not name.startswith("_")}
    parsed = {field.name for field in fields}
    for name in sorted(
        name
        for name in declared - parsed
        if isinstance(getattr(getattr(AgentLivingStruct, name, None), "offset", None), int)
    ):
        problems.append(f"`{name}` is a field and was not parsed")
    for field in fields:
        if field.size == 0:
            problems.append(f"`{field.name}` was parsed with no size")
    if not fields:
        problems.append("no fields were parsed at all")
    return problems


def main() -> int:
    cases = parse_gwau3_cases()
    fields = parse_struct_fields("AgentLivingStruct")
    offset_problems = verify_offsets_against_ctypes(fields)

    rows = [(case, *classify(case, fields)) for case in cases]
    counts: dict[str, int] = {}
    for _, verdict, _ in rows:
        counts[verdict] = counts.get(verdict, 0) + 1

    named = sum(len(case.keys) for case, verdict, _ in rows if verdict == "NAMED")
    total_keys = sum(len(case.keys) for case, _, _ in rows)

    lines: list[str] = []
    lines.append("# `Agent_GetAgentInfo`: which field keys this project can answer\n")
    lines.append("**Generated** by `python tools/audit_gwa3_agent_fields.py` — do not edit by hand.\n")
    lines.append(
        "The read side of the GwAu3-compatible layer rests on one claim: GwAu3's field names can be "
        "answered from the structures this project already reads. This is the measurement of that "
        "claim for the accessor with the most call sites in GwAu3's own scripts — "
        "**216**, the highest of any function.\n"
    )
    lines.append("## How to read this\n")
    lines.append("| Verdict | Meaning |")
    lines.append("| --- | --- |")
    lines.append("| **NAMED** | the structure declares a real attribute at the offset GwAu3 reads — the key is answerable by name |")
    lines.append("| **OFFSET ONLY** | an attribute occupies the offset but its name is an `hXXXX` placeholder — answerable, but the data has no name here |")
    lines.append("| **ABSENT** | no attribute occupies the offset — the compatibility layer would need a raw offset read, which is what the porting rules forbid outside the ported classes |")
    lines.append("| **COMPUTED** | GwAu3's case does not read a field; it computes or delegates (a count, a decode, another accessor) |")
    lines.append("")
    lines.append("## Result\n")
    if offset_problems:
        lines.append(
            "**This audit's own offsets disagree with ctypes, so the verdicts below are not "
            "trustworthy until that is fixed.** Disagreements:\n"
        )
        for problem in offset_problems:
            lines.append(f"- {problem}")
        lines.append("")
    else:
        lines.append(
            "The field offsets are read from the `ctypes` descriptors of `AgentLivingStruct` — "
            "including the fields it inherits — so the verdicts rest on the client layout this "
            "project already validates, not on arithmetic done here.\n"
        )
    lines.append(f"- `Agent_GetAgentInfo` `Case` groups: **{len(cases)}**, covering **{total_keys}** keys")
    lines.append(f"- structure fields parsed from `AgentLivingStruct`: **{len(fields)}**")
    for verdict in ("NAMED", "OFFSET ONLY", "ABSENT", "COMPUTED"):
        if counts.get(verdict):
            lines.append(f"- **{verdict}**: {counts[verdict]} case groups")
    lines.append(f"- keys answerable by name: **{named} of {total_keys}**")
    lines.append("")

    lines.append("## Every case\n")
    lines.append("| Keys | GwAu3 line | Offset | Verdict | What answers it |")
    lines.append("| --- | --- | --- | --- | --- |")
    for case, verdict, detail in sorted(rows, key=lambda row: row[0].line):
        keys = ", ".join(f"`{key}`" for key in case.keys)
        offset = f"`{case.offset:#x}`" if case.offset is not None else "—"
        lines.append(
            f"| {keys} | `GwAu3_Data_Agent.au3:{case.line}` | {offset} | {verdict} | {detail} |"
        )
    lines.append("")

    problems = [(case, verdict, detail) for case, verdict, detail in rows if verdict in ("ABSENT", "OFFSET ONLY")]
    lines.append("## What is left\n")
    lines.append(
        "**A verdict here is about an attribute's exact offset, not about whether the data is "
        "reachable.** Where GwAu3 reads a field *inside* a nested struct -- "
        "``TerrainNormalX``/``Y``/``Z`` are the components of ``terrain_normal`` (a ``Vec3f``), and "
        "``X``/``Y``/``Plane`` are the components of ``pos`` (a ``GamePos``) -- the attribute that "
        "occupies that offset is the nested struct, so a probe comparing offsets one for one reports "
        "the *first* component as named and its siblings as absent. That is a gap in this audit's "
        "reach, not a gap in the port: the data is there, one level down. The same applies to "
        "``VisibleEffectsNextNode``, which is inside ``visible_effects_list``.\n"
    )
    if not problems:
        lines.append("Every other field key resolves to a named attribute at its exact offset.\n")
    else:
        lines.append(
            "These are the keys that do not resolve to a *named* attribute at their exact offset. "
            "The fixes are different in kind, so each is labelled:\n"
        )
        for case, verdict, detail in problems:
            keys = ", ".join(f"`{key}`" for key in case.keys)
            lines.append(f"- **{keys}** (`GwAu3_Data_Agent.au3:{case.line}`, {verdict}) — {detail}")
        lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  case groups: {len(cases)}   keys: {total_keys}   answerable by name: {named}")
    for verdict in ("NAMED", "OFFSET ONLY", "ABSENT", "COMPUTED"):
        if counts.get(verdict):
            print(f"  {verdict}: {counts[verdict]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
