"""Generate ``py4gw/gwa3/constants.py`` from the local GwAu3 checkout.

The GwAu3-compatible layer in ``py4gw/gwa3`` accepts the same constants a GwAu3 AutoIt script
passes: ``$GC_I_ALLEGIANCE_ENEMY``, ``$GC_I_SKILL_*``, ``$GC_I_QUEST_*`` and the rest. Those
constants are not ours to invent. GwAu3's own include files define them, and this tool copies
their values from ``external/GwAu3/API/Constants`` so the numbers are the numbers GwAu3 uses.

Run it from the project root:

    python tools/generate_gwa3_constants.py

It reads ``Global Const $NAME = <expression>`` declarations from the constant include files,
resolves each expression to a literal value (``$`` references are resolved from constants already
seen, arithmetic is evaluated), and writes the module with one section per source file plus a
provenance header naming the file.

**Why the values are copied rather than re-derived.** These are GwAu3's names for the client's own
values. Re-deriving them from this project's catalogs would produce a table that mostly agrees and
occasionally does not, and a constant that disagrees is worse than one that is absent: a script
passes it straight into a game call. So the rule is the one the AutoIt GUI layer's generator uses --
take the values from the source that defines them, with the source recorded.

**The one thing this tool does not do is check whether a value is *correct*.** Several of these
tables are GwAu3's own and have been found to disagree with the client (`docs/RESEARCH.md:4362-4368`,
the `CharContext` offset four bytes low). A name and its value are copied as GwAu3 writes them; the
route map decides, per use, whether a number may be trusted.

Five facts about the source, all measured, which is what the parser below is shaped for:

* Constants are declared in **two** forms, and both are read: 7,017 ``Global Const`` declarations and
  176 names inside eight ``Global Enum`` blocks, across 34 constant-carrying files, every name unique.
  (The directory holds 35 ``.au3`` files; ``_Constants.au3`` is the include list and declares nothing.)
  An earlier count said 7,020 "across 35" -- the total was right and the file count was not, because
  ``_Constants.au3`` was counted as carrying constants and declares none. **The ``Global Enum`` form
  was not read at all until ``tools/analyze_gwa3_example_parity.py`` found 129 names missing from a
  module that claimed to be the complete surface**: every ``$GC_I_INVENTORY_*`` field key, every
  ``$GC_I_HERO_ID_*``, the ``$GC_I_SKILL_*`` and ``$GC_S_SKILL_*`` field keys, the
  ``$GC_E_TITLEID_*`` ids. Enum assigns sequentially -- first name zero or its own value, each after it
  one more -- and ``Enum Step`` does not appear in these files.
* No function calls appear in any initialiser -- no ``BitOR``, no ``BitShift``.
* 220 ``Global`` declarations are *not* ``Const`` (mutable library state) and are skipped.
* An initialiser may continue onto following lines with a trailing ``_``, and may carry a trailing
  ``;`` comment -- including *inside* an array, after a continued element, and after an Enum
  continuation marker. Comments are therefore stripped quote-aware and only outside string literals.
* Four array families exist, not two: ``$GC_AI_*``, ``$GC_AS_*``, and the **2-D** ``$GC_AI2_*``,
  ``$GC_AM2_*`` and ``$GC_AMX2_*``. A dimension may itself be a reference to another constant
  (``[$GC_I_SKILL_DATA_ROWS][$GC_I_SKILL_DATA_COLUMNS]``), and a declaration's dimension count
  includes the element itself -- ``[40][2]`` is 40 elements of 2.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GWAU3_API_ROOT = REPO_ROOT / "external" / "GwAu3" / "API"
GWAU3_CONSTANTS_DIR = GWAU3_API_ROOT / "Constants"
OUTPUT_PATH = REPO_ROOT / "py4gw" / "gwa3" / "constants.py"

# The constant include files, in the order the checkout's own `_Constants.au3` includes them.
# Order matters for the same reason it matters in AutoIt: an initialiser may reference a constant
# an earlier file defined.
SOURCE_FILES: tuple[str, ...] = (
    "GwAu3_Const_Account.au3",
    "GwAu3_Const_Agents.au3",
    "GwAu3_Const_ASM.au3",
    "GwAu3_Const_Attribute.au3",
    "GwAu3_Const_Camera.au3",
    "GwAu3_Const_Chat.au3",
    "GwAu3_Const_Cinematic.au3",
    "GwAu3_Const_ControlAction.au3",
    "GwAu3_Const_Core.au3",
    "GwAu3_Const_Effect.au3",
    "GwAu3_Const_Friend.au3",
    "GwAu3_Const_Game.au3",
    "GwAu3_Const_Gui.au3",
    "GwAu3_Const_Guild.au3",
    "GwAu3_Const_Item.au3",
    "GwAu3_Const_LogMessage.au3",
    "GwAu3_Const_Map.au3",
    "GwAu3_Const_Match.au3",
    "GwAu3_Const_Memory.au3",
    "GwAu3_Const_Merchant.au3",
    "GwAu3_Const_Other.au3",
    "GwAu3_Const_PacketHeader.au3",
    "GwAu3_Const_Party.au3",
    "GwAu3_Const_Path.au3",
    "GwAu3_Const_Player.au3",
    "GwAu3_Const_PreGame.au3",
    "GwAu3_Const_Quest.au3",
    "GwAu3_Const_Scanner.au3",
    "GwAu3_Const_Skill.au3",
    "GwAu3_Const_Title.au3",
    "GwAu3_Const_Trade.au3",
    "GwAu3_Const_Ui.au3",
    "GwAu3_Const_Util.au3",
    "GwAu3_Const_World.au3",
)


class ConstantParseError(RuntimeError):
    """A declaration the generator could not resolve.

    Raised rather than skipped, deliberately: a constant silently dropped is a name a migrated
    script would call and not find, which is the failure this whole layer exists to prevent.
    """


@dataclass(frozen=True)
class Declaration:
    """One ``Global Const``: its name, its source file and line, and its resolved value."""

    name: str
    source_file: str
    line: int
    value: object


@dataclass(frozen=True)
class SizeMismatch:
    """An array whose declared dimension(s) do not match the elements written.

    GwAu3 has two of these -- ``$GC_AI_EL_TONICS`` declares ``[68]`` and writes 67, and
    ``$GC_AI_MONSTER_TROPHIES`` declares ``[188]`` and writes 187 -- so it is a fact about the source
    rather than a parse failure. It is reported and the **elements written are what is copied**: a
    name maps to the values the source gives it, and padding an array to a declared length would be
    inventing a value the source does not contain. AutoIt does not enforce the bound either.
    """

    name: str
    source_file: str
    line: int
    declared: str
    written: str


_DECLARATION = re.compile(
    r"""^\s*Global\s+Const\s+\$(?P<name>[A-Za-z_]\w*)\s*(?P<dims>(?:\[[^\]]*\])*)\s*=\s*(?P<rhs>.*)$""",
    re.VERBOSE,
)

#: AutoIt's `Global Enum`, which is the second way GwAu3 declares a constant and which this
#: generator did not read at all until the parity analysis found the loss.
#:
#: **129 names were missing from the module**, and they are not a corner of the surface: all 50
#: `$GC_I_INVENTORY_*` field keys, the 39 `$GC_I_HERO_ID_*` hero ids, the 30 `$GC_I_SKILL_*` and
#: `$GC_S_SKILL_*` field keys, the 9 `$GC_E_TITLEID_*` title ids and `$GC_I_LOG_MSGTYPE_DEBUG`. The
#: offline parity test could not see it, because it compared the module against the generator's own
#: extraction in both directions -- an index checked against an index -- so a declaration form the
#: generator never learned was invisible to both. `tools/analyze_gwa3_example_parity.py` found it by
#: reading the *scripts* and asking which constants they use.
#:
#: AutoIt's Enum assigns sequentially: the first name takes its own `= value` or **zero**, and each
#: following name takes one more than the last, unless it gives its own value. `Enum Step` does not
#: appear in these files (measured), so it is not supported, and a file that grew one would fail
#: loudly here rather than be assigned wrongly.
_ENUM = re.compile(r"^\s*Global\s+Enum\s+(?P<body>.+)$", re.IGNORECASE)
_ENUM_ITEM = re.compile(r"^\s*\$(?P<name>[A-Za-z_]\w*)\s*(?:=\s*(?P<value>.+?))?\s*$")

_DIMENSION = re.compile(r"\[([^\]]*)\]")

_INTEGER_LITERAL = re.compile(r"^-?(?:0[xX][0-9a-fA-F]+|\d+)$")
_FLOAT_LITERAL = re.compile(r"^-?(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?$")

# AutoIt's own arithmetic, limited to what a constant initialiser can contain. `BitOR` and friends
# do not appear in these files (measured), so they are not supported -- and a file that grew one
# would fail loudly here rather than be parsed wrongly.
_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
}
_UNARYOPS = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}


def _strip_comment(text: str) -> str:
    """Remove an AutoIt ``;`` comment, ignoring semicolons inside string literals.

    GwAu3 writes comments into the middle of continued array initialisers, so this cannot be a
    plain split on the first semicolon: a ``;`` inside a quoted string is data.
    """

    quote: str | None = None
    index = 0
    while index < len(text):
        character = text[index]
        if quote is not None:
            if character == quote:
                # A doubled quote inside a string is an escaped quote, not the end of it.
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 2
                    continue
                quote = None
        elif character in ("'", '"'):
            quote = character
        elif character == ";":
            return text[:index]
        index += 1
    return text


def _logical_lines(path: Path) -> list[tuple[int, str]]:
    """Join AutoIt continuation lines into one logical line each, keeping the first line's number."""

    joined: list[tuple[int, str]] = []
    pending: str | None = None
    pending_line = 0

    for offset, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        text = _strip_comment(raw).rstrip()
        if pending is not None:
            text = pending + " " + text.strip()
            start = pending_line
        else:
            start = offset + 1

        if text.endswith("_"):
            pending = text[:-1].rstrip()
            pending_line = start
            continue

        pending = None
        if text.strip():
            joined.append((start, text))

    if pending is not None:
        joined.append((pending_line, pending))
    return joined


def _split_array_items(inner: str) -> list[str]:
    """Split an array initialiser's body on commas that separate *items*.

    Two kinds of comma must not split: one inside a string literal, and one inside a nested
    ``[...]``. GwAu3's 2-D tables are written as multiple rows on one logical line
    (``[39, 1], [1, "Norgu"], [2, "Goren"]``), so both cases are load-bearing.
    """

    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    index = 0
    while index < len(inner):
        character = inner[index]
        if quote is not None:
            current.append(character)
            if character == quote:
                if index + 1 < len(inner) and inner[index + 1] == quote:
                    current.append(inner[index + 1])
                    index += 2
                    continue
                quote = None
        elif character in ("'", '"'):
            quote = character
            current.append(character)
        elif character == "[":
            depth += 1
            current.append(character)
        elif character == "]":
            depth -= 1
            if depth < 0:
                raise ConstantParseError(f"unbalanced ']' in an array initialiser: {inner!r}")
            current.append(character)
        elif character == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        index += 1

    if depth != 0:
        raise ConstantParseError(f"unbalanced '[' in an array initialiser: {inner!r}")
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def _evaluate_arithmetic(expression: str, constants: dict[str, object], context: str) -> object:
    """Evaluate an arithmetic initialiser, with ``$NAME`` resolved from constants already read."""

    python_expression = re.sub(r"\$([A-Za-z_]\w*)", r"\1", expression)
    try:
        tree = ast.parse(python_expression, mode="eval")
    except SyntaxError as error:
        raise ConstantParseError(f"{context}: cannot parse {expression!r}: {error}") from error

    def walk(node: ast.AST) -> object:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, str)):
                return node.value
            raise ConstantParseError(f"{context}: unsupported literal {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id in constants:
                return constants[node.id]
            raise ConstantParseError(f"{context}: reference to unknown constant ${node.id}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left = walk(node.left)
            right = walk(node.right)
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise ConstantParseError(f"{context}: arithmetic on non-numbers in {expression!r}")
            return _BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            operand = walk(node.operand)
            if not isinstance(operand, (int, float)):
                raise ConstantParseError(f"{context}: unary operator on a non-number in {expression!r}")
            return _UNARYOPS[type(node.op)](operand)
        raise ConstantParseError(f"{context}: unsupported expression {expression!r}")

    return walk(tree)


def _extract_array_body(text: str) -> str:
    """Return the inside of an ``[...]`` initialiser, matching nested brackets.

    A plain ``text[1:-1]`` is wrong the moment an element is itself an array, which is exactly what
    GwAu3's 2-D tables are: ``[[1, "a"], [2, "b"]]`` would come out with its brackets mismatched.
    """

    if not text.startswith("["):
        raise ConstantParseError(f"not an array initialiser: {text!r}")
    depth = 0
    for index, character in enumerate(text):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                if text[index + 1 :].strip():
                    raise ConstantParseError(f"trailing text after an array initialiser: {text!r}")
                return text[1:index]
    raise ConstantParseError(f"array initialiser is not closed: {text!r}")


def _flatten(items: list[object]) -> list[object]:
    """Every leaf, depth first. Order is preserved, which is what makes a reshape lossless."""

    flat: list[object] = []
    for item in items:
        if isinstance(item, list):
            flat.extend(_flatten(item))
        else:
            flat.append(item)
    return flat


def _reshape(items: list[object], shape: list[int]) -> list[object]:
    """Fold resolved items into the dimensions the source declares.

    GwAu3 writes a 2-D table as one row per continuation line (``[39, 1], _``), and inside an
    initialiser that is indistinguishable from a 1-D list of lists. The declared dimensions settle
    it: **flatten to the leaves, then cut back into exactly the declared shape.**

    That is what makes ``[[39, 1], [1, "Norgu"], ...]`` -- 20 *rows* of 2, after the count row --
    come out as the 40x2 table the source declares, instead of a 20x2 one with each pair wrapped in a
    list it should not have. Note that a declaration's dimension count includes the element itself
    (``[40][2]`` on a 1-based table), so the number of cuts is ``len(shape)``, not ``len(shape) - 1``.

    A source whose dimensions are unusable, or whose leaf count does not fill the declared shape,
    keeps the nested list it was written as.
    """

    if len(shape) <= 1:
        return items

    leaves = _flatten(items)
    # The declared dimensions are the element's own size followed by each nested array's size
    # (`[40][2]` = 40 elements of 2), so the number of cuts is one less than the dimension count.
    expected = 1
    for dimension in shape[1:]:
        expected *= dimension
    if expected != len(leaves):
        return items

    result: list[object] = leaves
    for dimension in reversed(shape[1:]):
        result = [result[index : index + dimension] for index in range(0, len(result), dimension)]
    return result


def _shape_matches(value: object, shape: list[int]) -> bool:
    """True when ``value`` has the declared dimensions.

    A length is accepted when it is the declared one **or** when it is divisible by it. The second
    case is not slack: it is how a row of 5 items declared as ``[5]`` reads, because the declared
    size counts items and a nested item is one. It is also why a genuinely short array -- 67 items
    declared ``[68]`` -- still fails, which is the report that matters.
    """

    if not shape:
        return True
    if not isinstance(value, list):
        return False
    dimension = shape[0]
    if dimension <= 0:
        return False
    if len(value) not in (dimension, dimension + 1) and len(value) % dimension != 0:
        return False
    if len(shape) == 1:
        return True
    if not value:
        return False
    return all(_shape_matches(item, shape[1:]) for item in value)


def _resolve_value(rhs: str, constants: dict[str, object], context: str) -> object:
    """Resolve one initialiser: a literal, an array, a ``$`` reference, or arithmetic."""

    text = rhs.strip()
    if not text:
        raise ConstantParseError(f"{context}: empty initialiser")

    if text.startswith("["):
        # A bare `[]` is not valid AutoIt, but GwAu3 contains one (GwAu3_Const_Item.au3, the
        # `$GC_AI_EVENT_ITEMS` declaration). It is parsed as a 1-D list: the elements written are
        # the values, and the missing dimension is reported rather than guessed at.
        body = _extract_array_body(text)
        if not body.strip():
            return []
        return [_resolve_value(item, constants, context) for item in _split_array_items(body)]

    if _INTEGER_LITERAL.match(text):
        return int(text, 0)
    if _FLOAT_LITERAL.match(text):
        return float(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1].replace(text[0] * 2, text[0])

    return _evaluate_arithmetic(text, constants, context)


def _shape_of(value: object) -> str:
    """Render an array's dimensions the way a declaration writes them: ``[40][2]``.

    Follows the first element of each level, which is what a *declared* shape describes: every row of
    a well-formed table has the row's length, so the first one speaks for them.
    """

    dimensions: list[int] = []
    current: object = value
    while isinstance(current, list):
        dimensions.append(len(current))
        if not current:
            break
        current = current[0]
    return "".join(f"[{n}]" for n in dimensions) if dimensions else "a scalar"


def _parse_dimensions(dims: str, constants: dict[str, object], context: str) -> list[int] | None:
    """Resolve a declaration's ``[a][b]`` dimensions, or ``None`` when they are not usable.

    A dimension may be a literal (``[40][2]``) or a reference to another constant
    (``[$GC_I_SKILL_DATA_ROWS][$GC_I_SKILL_DATA_COLUMNS]``, which GwAu3 uses), so it goes through the
    same evaluator an initialiser does. An **empty** ``[]`` -- which GwAu3 contains once, on
    ``$GC_AI_EVENT_ITEMS``, and which is not valid AutoIt -- yields ``None``: the declaration is
    reported as having no usable dimension rather than being given one.
    """

    if not dims:
        return None

    resolved: list[int] = []
    for raw in _DIMENSION.findall(dims):
        text = raw.strip()
        if not text:
            raise ConstantParseError(f"{context}: a dimension is empty ('[]')")
        value = _resolve_value(text, constants, context)
        if not isinstance(value, int):
            raise ConstantParseError(f"{context}: dimension {text!r} resolved to a non-integer {value!r}")
        resolved.append(value)
    return resolved


def _parse_enum(
    body: str,
    path: Path,
    line_number: int,
    constants: dict[str, object],
) -> list[Declaration]:
    """One `Global Enum` block's names, with AutoIt's own sequential assignment.

    The block arrives here as a single logical line: `_logical_lines` has already joined its `_`
    continuations, so `body` is everything after ``Global Enum`` -- ``$A, $B = 7, $C``. AutoIt's rule
    is applied literally and in order: a name with no value takes **one more than the name before it**,
    and the first such name takes zero.
    """

    declarations: list[Declaration] = []
    next_value = 0

    for item in _split_array_items(body):
        item = item.strip()
        if not item:
            continue
        match = _ENUM_ITEM.match(item)
        if match is None:
            raise ConstantParseError(
                f"{path.name}:{line_number}: `Global Enum` item this generator cannot read: {item!r}"
            )
        name = match.group("name")
        context = f"{path.name}:{line_number} (${name})"
        if match.group("value") is not None:
            value = _resolve_value(match.group("value"), constants, context)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ConstantParseError(
                    f"{context}: an Enum member's value must be an integer, got {value!r}"
                )
            next_value = value
        value = next_value
        next_value += 1

        if name in constants:
            raise ConstantParseError(f"{context}: ${name} is declared twice")
        constants[name] = value
        declarations.append(
            Declaration(name=name, source_file=path.name, line=line_number, value=value)
        )

    return declarations


def parse_file(
    path: Path,
    constants: dict[str, object],
    mismatches: list[SizeMismatch],
    *,
    strict: bool = False,
) -> list[Declaration]:
    """Read one constant include file, adding nothing to ``constants`` until its value resolves."""

    declarations: list[Declaration] = []
    for line_number, text in _logical_lines(path):
        enum = _ENUM.match(text)
        if enum is not None:
            declarations.extend(_parse_enum(enum.group("body"), path, line_number, constants))
            continue

        match = _DECLARATION.match(text)
        if match is None:
            continue
        name = match.group("name")
        context = f"{path.name}:{line_number} (${name})"

        resolved_dimensions: list[int] | None = None
        dimensions_error: str | None = None
        try:
            resolved_dimensions = _parse_dimensions(match.group("dims"), constants, context)
        except ConstantParseError as error:
            dimensions_error = str(error)

        value = _resolve_value(match.group("rhs"), constants, context)

        if isinstance(value, list) and resolved_dimensions is not None:
            value = _reshape(value, resolved_dimensions)

        if dimensions_error is not None:
            mismatches.append(
                SizeMismatch(
                    name=name,
                    source_file=path.name,
                    line=line_number,
                    declared=match.group("dims"),
                    written="dimension not usable: " + dimensions_error.split(": ", 1)[-1],
                )
            )
            if strict:
                raise ConstantParseError(dimensions_error)
        elif resolved_dimensions is not None:
            if not _shape_matches(value, resolved_dimensions):
                declared_display = "".join(f"[{n}]" for n in resolved_dimensions)
                mismatches.append(
                    SizeMismatch(
                        name=name,
                        source_file=path.name,
                        line=line_number,
                        declared=declared_display,
                        written=_shape_of(value),
                    )
                )
                if strict:
                    raise ConstantParseError(
                        f"{context}: declared {declared_display} but the value is {_shape_of(value)}"
                    )

        if name in constants:
            raise ConstantParseError(f"{context}: ${name} is declared twice")
        constants[name] = value
        declarations.append(Declaration(name=name, source_file=path.name, line=line_number, value=value))

    return declarations


def _format_value(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    return repr(value)


def _wrap_array(name: str, value: list[object]) -> str:
    """Render an array, one element per line when a single line would be too long.

    A nested array is written one **row** per line, which is how GwAu3 writes its 2-D tables and
    keeps a row readable as a row.
    """

    one_line = f"{name} = {_format_value(value)}"
    if len(one_line) <= 100:
        return one_line + "\n"

    lines = [f"{name} = ["]
    for item in value:
        lines.append(f"    {_format_value(item)},")
    lines.append("]\n")
    return "\n".join(lines)


def render_module(
    per_file: dict[str, list[Declaration]],
    total: int,
    mismatches: list[SizeMismatch],
) -> str:
    mismatch_note = ""
    if mismatches:
        rows = "\n".join(
            f"* ``{m.source_file}:{m.line}`` -- ``{m.name}`` declares ``{m.declared}``; the values "
            f"written give ``{m.written}``."
            for m in mismatches
        )
        mismatch_note = f'''
Declarations whose values do not fill the declared dimensions
-------------------------------------------------------------

{rows}

**The values written are what is copied.** A declaration that states one dimension and receives
another is a fact about GwAu3's source, and resolving it here would mean choosing between the
declaration and the data -- and the data is what a script reads. Padding a short array would invent a
value the source does not contain, and AutoIt does not enforce the bound either, so a caller that
iterates to the declared length reads past the end in GwAu3 for the same reason.
'''

    header = f'''"""GwAu3's constant surface, as ``py4gw/gwa3`` presents it.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_constants.py``.

This module is the constant half of the GwAu3-compatible layer (see
``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names are kept with the leading ``$`` removed, so an AutoIt
line ``$GC_I_ALLEGIANCE_ENEMY`` reads ``GC_I_ALLEGIANCE_ENEMY`` here -- the same rule the AutoIt GUI
layer's generated module uses.

Provenance
----------

* Source: ``external/GwAu3/API/Constants/*.au3`` (GwAu3, MIT, ``Copyright (c) 2025 JAG-GW``).
* {total} constants from {len(per_file)} files, copied value for value.
* GwAu3's naming scheme is preserved, not reinterpreted: ``GC_I_*`` integer, ``GC_S_*`` string,
  ``GC_AI_*`` array of integers, ``GC_AS_*`` array of strings.

A name and its value are reproduced exactly as GwAu3 writes them, **including where GwAu3's own
table is known to disagree with the client** (``docs/RESEARCH.md:4362-4368``). This module is the
name table, not a verified catalog: whether a number may be trusted is decided per use, by the route
map.
{mismatch_note}"""

from __future__ import annotations
'''

    sections: list[str] = [header]
    # **Every file that declared something, not only the constant files.** The wide scan adds the
    # plugin and module sources to `per_file` under their own path, and an earlier version rendered
    # only `SOURCE_FILES`: those constants landed in `__all__` and not in the module body, which the
    # offline test caught as "in __all__ and not defined" -- a name a migrating script would import
    # and not find.
    for file_name, declarations in per_file.items():
        sections.append(f"\n\n# --- {file_name}: {len(declarations)} constants " + "-" * 20 + "\n")
        if not declarations:
            sections.append("\n# (this file declares no constants)\n")
            continue
        for declaration in declarations:
            if isinstance(declaration.value, list):
                sections.append("\n" + _wrap_array(declaration.name, declaration.value))
            else:
                sections.append(f"\n{declaration.name} = {_format_value(declaration.value)}\n")

    names = [d.name for declarations in per_file.values() for d in declarations]
    sections.append("\n\n__all__ = [\n")
    for name in names:
        sections.append(f'    "{name}",\n')
    sections.append("]\n")
    return "".join(sections)


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    missing = [name for name in SOURCE_FILES if not (GWAU3_CONSTANTS_DIR / name).is_file()]
    if missing:
        raise SystemExit(
            f"GwAu3 constant sources are not where they are expected ({GWAU3_CONSTANTS_DIR}).\n"
            f"Missing: {', '.join(missing)}"
        )

    constants: dict[str, object] = {}
    per_file: dict[str, list[Declaration]] = {}
    mismatches: list[SizeMismatch] = []
    for file_name in SOURCE_FILES:
        per_file[file_name] = parse_file(
            GWAU3_CONSTANTS_DIR / file_name, constants, mismatches, strict=strict
        )

    # **`API/Constants` is not where all of GwAu3's constants live.** Plugins and modules declare
    # their own, and a migrated script and this layer's own generated wrappers use them:
    # `$GC_UAI_TARGET_MODE_CALL` and `$GC_I_UAI_WARDTYPE_DEFENSIVE` are declared in
    # `API/Plugins/UtilityAI/UtilityAI_Const.au3`, and GwAu3's own parameter defaults name them
    # (`UAI_Fight(..., $a_i_FightMode = $g_i_FinisherMode)`). Reading only `Constants/` left 183
    # `GC_*` names undeclared, which Au3Check reports as an undeclared global on a line a migrating
    # script never changed. The rest of the tree is scanned after the constant files, so a reference
    # to a constant declared there still resolves.
    for path in sorted(GWAU3_API_ROOT.rglob("*.au3")):
        if path.parent == GWAU3_CONSTANTS_DIR:
            continue
        found = parse_file(path, constants, mismatches, strict=strict)
        if found:
            per_file[str(path.relative_to(GWAU3_API_ROOT)).replace("\\", "/")] = found

    total = len(constants)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_module(per_file, total, mismatches), encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} -- {total} constants from "
        f"{len(SOURCE_FILES)} constant files and {len(per_file) - len(SOURCE_FILES)} other sources."
    )

    if mismatches:
        print(f"\n{len(mismatches)} array size mismatch(es) in the source. The elements written are copied:")
        for mismatch in mismatches:
            print(
                f"  {mismatch.source_file}:{mismatch.line} ${mismatch.name} "
                f"declares [{mismatch.declared}] and writes {mismatch.written}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
