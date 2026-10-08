"""Generate ``py4gw/gui/constants.py`` from the local AutoIt v3 installation.

The AutoIt-compatible GUI layer in ``py4gw/gui`` accepts the same style, state and
event constants an AutoIt GUI script passes. Those constants are not ours to invent:
AutoIt's own include files define them, and this tool copies their values from the
AutoIt installation on this machine so the numbers are the numbers AutoIt uses.

Run it from the project root:

    python tools/generate_autoit_gui_constants.py

It reads ``Global Const $NAME = <expression>`` lines from a curated list of AutoIt
include files, resolves each expression to a literal value (``BitOR`` and friends are
evaluated, ``$`` references are resolved from constants already seen), and writes the
module with one section per source file plus a provenance header naming the file and
the AutoIt version recorded inside it.

The ``@SW_*`` show-state macros are a second, separate source: AutoIt's interpreter
defines them, not an include file, so their values are read from the interpreter by
``tests/autoit_reference/probe_autoit_constants.au3`` and are recorded here as literals.
"""

from __future__ import annotations

import re
from pathlib import Path

AUTOIT_INCLUDE_DIR = Path(r"C:\Program Files (x86)\AutoIt3\Include")

# The include files whose constants the AutoIt GUI reference's controls and styling
# use. Order matters: a constant defined in an earlier file may be referenced by a
# later one.
INCLUDE_FILES: tuple[str, ...] = (
    "GUIConstantsEx.au3",
    "AutoItConstants.au3",
    "WindowsConstants.au3",
    "BorderConstants.au3",
    "FrameConstants.au3",
    "ButtonConstants.au3",
    "StaticConstants.au3",
    "EditConstants.au3",
    "ComboConstants.au3",
    "ListBoxConstants.au3",
    "ListViewConstants.au3",
    "TreeViewConstants.au3",
    "TabConstants.au3",
    "ProgressConstants.au3",
    "SliderConstants.au3",
    "UpDownConstants.au3",
    "DateTimeConstants.au3",
    "AVIConstants.au3",
    "MenuConstants.au3",
    "ToolTipConstants.au3",
    "RichEditConstants.au3",
    "ScrollBarConstants.au3",
    "FontConstants.au3",
    "ColorConstants.au3",
)

# The show-state macros, read from the AutoIt interpreter itself by
# tests/autoit_reference/probe_autoit_constants.au3 (ConsoleWrite of each macro). AutoIt does not
# publish these numbers in its help file, so the interpreter is the only authority.
SHOW_STATE_MACROS: tuple[tuple[str, int], ...] = (
    ("SW_HIDE", 0),
    ("SW_SHOWNORMAL", 1),
    ("SW_SHOWMINIMIZED", 2),
    ("SW_MAXIMIZE", 3),
    ("SW_SHOWMAXIMIZED", 3),
    ("SW_SHOWNOACTIVATE", 4),
    ("SW_SHOW", 5),
    ("SW_MINIMIZE", 6),
    ("SW_SHOWMINNOACTIVE", 7),
    ("SW_SHOWNA", 8),
    ("SW_RESTORE", 9),
    ("SW_SHOWDEFAULT", 10),
    ("SW_ENABLE", 64),
    ("SW_DISABLE", 65),
    ("SW_LOCK", 66),
    ("SW_UNLOCK", 67),
)

_CONFIG_LINE = re.compile(r"^\s*Global\s+Const\s+\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")
_VERSION_LINE = re.compile(r"^\s*;\s*AutoIt Version\s*:\s*(.+?)\s*$")
_TITLE_LINE = re.compile(r"^\s*;\s*Title\s*\.+:\s*(.+?)\s*$")
_NAME_REFERENCE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_BIT_FUNCTION = re.compile(r"\b(BitOR|BitAND|BitXOR|BitNOT|BitShift)\s*\(")
_SAFE_EXPRESSION = re.compile(r"^[0-9a-fA-FxX\s|&^~()<>+\-*/'\"A-Za-z_,.$]*$")
_STRING_LITERAL = re.compile(r"^'(.*)'$", re.DOTALL)


class _Unresolved(Exception):
    """An AutoIt expression references something this generator cannot resolve."""


def _strip_comment(line: str) -> str:
    """Remove an AutoIt line comment, ignoring a ``;`` inside a single-quoted string."""

    in_string = False
    for index, character in enumerate(line):
        if character == "'":
            in_string = not in_string
        elif character == ";" and not in_string:
            return line[:index]
    return line


def _split_arguments(text: str) -> list[str]:
    """Split an AutoIt call's argument list on top-level commas."""

    arguments: list[str] = []
    depth = 0
    current = ""
    for character in text:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character == "," and depth == 0:
            arguments.append(current)
            current = ""
            continue
        current += character
    arguments.append(current)
    return [argument.strip() for argument in arguments]


def _translate_call(name: str, arguments: list[str]) -> str:
    """Translate one AutoIt bit function call into a Python expression."""

    if name == "BitNOT":
        if len(arguments) != 1:
            raise _Unresolved(f"BitNOT with {len(arguments)} arguments")
        return f"(~{arguments[0]})"
    if name == "BitShift":
        if len(arguments) != 2:
            raise _Unresolved(f"BitShift with {len(arguments)} arguments")
        amount = arguments[1]
        if amount.startswith("-"):
            return f"({arguments[0]} >> {amount[1:]})"
        return f"({arguments[0]} << {amount})"
    operator = {"BitOR": "|", "BitAND": "&", "BitXOR": "^"}[name]
    if not arguments:
        raise _Unresolved(f"{name} with no arguments")
    return "(" + f" {operator} ".join(arguments) + ")"


def _to_python(expression: str) -> str:
    """Translate an AutoIt constant expression into an equivalent Python one."""

    expression = _STRING_LITERAL.sub(lambda match: repr(match.group(1)), expression)
    expression = _NAME_REFERENCE.sub(lambda match: f"__c_{match.group(1)}", expression)

    while True:
        match = _BIT_FUNCTION.search(expression)
        if match is None:
            return expression
        start = match.end()
        depth = 1
        index = start
        while index < len(expression) and depth:
            if expression[index] == "(":
                depth += 1
            elif expression[index] == ")":
                depth -= 1
            index += 1
        if depth:
            raise _Unresolved(f"unbalanced call in {expression!r}")
        arguments = _split_arguments(expression[start : index - 1])
        translated = _translate_call(match.group(1), arguments)
        expression = expression[: match.start()] + translated + expression[index:]


def _resolve(expression: str, known: dict[str, int | str]) -> int | str:
    """Resolve one AutoIt constant expression to a Python int or str."""

    if not _SAFE_EXPRESSION.match(expression):
        raise _Unresolved(f"unsupported expression {expression!r}")
    namespace = {f"__c_{name}": value for name, value in known.items()}
    try:
        return eval(_to_python(expression), {"__builtins__": {}}, namespace)  # noqa: S307
    except NameError as error:
        raise _Unresolved(str(error)) from error
    except SyntaxError as error:
        raise _Unresolved(f"syntax: {expression!r}") from error


def _read_include(path: Path) -> tuple[str, str, list[tuple[str, str, str]]]:
    """Read one include file into (title, AutoIt version, constants)."""

    title = ""
    version = ""
    constants: list[tuple[str, str, str]] = []
    in_function = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        title_match = _TITLE_LINE.match(line)
        if title_match and not title:
            title = title_match.group(1)
        version_match = _VERSION_LINE.match(line)
        if version_match and not version:
            version = version_match.group(1)
        lowered = line.strip().lower()
        if lowered.startswith("func "):
            in_function = True
            continue
        if lowered.startswith("endfunc"):
            in_function = False
            continue
        if in_function:
            continue
        match = _CONFIG_LINE.match(_strip_comment(line).rstrip())
        if match:
            constants.append((match.group(1), match.group(2), line.strip()))
    return title, version, constants


def build_module() -> str:
    """Build the text of ``py4gw/gui/constants.py``."""

    # Read every file first: AutoIt's include files reference constants defined later in
    # the same file (RichEditConstants.au3 does), so all names have to be collectable
    # before any of them can be resolved.
    headers: list[str] = []
    entries_by_file: list[list[tuple[str, str, str]]] = []
    missing: list[str] = []

    for file_name in INCLUDE_FILES:
        path = AUTOIT_INCLUDE_DIR / file_name
        if not path.is_file():
            missing.append(file_name)
            continue
        title, version, entries = _read_include(path)
        header = f"# --- {file_name}"
        if title:
            header += f" ({title})"
        if version:
            header += f" - AutoIt Version : {version}"
        header += " ---"
        headers.append(header)
        entries_by_file.append(entries)

    known: dict[str, int | str] = {}
    resolved: list[dict[str, tuple[int | str, str]]] = [dict() for _ in entries_by_file]
    for _ in range(len(entries_by_file) * 4 + 4):
        progress = False
        for index, entries in enumerate(entries_by_file):
            for name, expression, source_line in entries:
                if name in resolved[index]:
                    continue
                try:
                    value = _resolve(expression, known)
                except _Unresolved:
                    continue
                known[name] = value
                resolved[index][name] = (value, source_line)
                progress = True
        if not progress:
            break

    sections: list[str] = []
    total = 0
    unresolved: list[str] = []
    for index, entries in enumerate(entries_by_file):
        lines: list[str] = []
        for name, expression, source_line in entries:
            if name not in resolved[index]:
                try:
                    _resolve(expression, known)
                except _Unresolved as error:
                    reason = error
                else:
                    reason = "unresolved reference"
                unresolved.append(
                    f"{INCLUDE_FILES[index]}:{name} ({source_line}) -> {reason}"
                )
                continue
            value, _ = resolved[index][name]
            comment = f"  # {expression}"
            if _strip_comment(source_line).rstrip() != f"Global Const ${name} = {expression}":
                comment = f"{comment}  [{source_line}]"
            lines.append(f"{name} = {value!r}{comment}")
            total += 1
        sections.append("\n".join([headers[index], *lines]))

    macro_lines = [f"{name} = {value}" for name, value in SHOW_STATE_MACROS]

    body = "\n\n\n".join(sections)
    document = f'''r"""AutoIt GUI constants, copied from the local AutoIt v3 installation.

Provenance
----------
Names and values come from the AutoIt include files named in each section below, read
from ``{AUTOIT_INCLUDE_DIR}`` by ``tools/generate_autoit_gui_constants.py``. The AutoIt
version recorded in each source file's own header is kept in that section's comment.

The ``@SW_*`` show-state macros are defined by the AutoIt interpreter rather than by an
include file. Their values below were read from the interpreter with
``tests/autoit_reference/probe_autoit_constants.au3`` (one ``ConsoleWrite`` per macro), because
AutoIt's help file documents the macro names but not their numbers.

Spelling follows AutoIt: a constant keeps AutoIt's name with the leading ``$`` removed,
so an AutoIt line ``GUISetState(@SW_SHOW)`` reads ``GUISetState(SW_SHOW)`` here. The
macro names keep their ``@`` dropped for the same reason (``@SW_SHOW`` becomes
``SW_SHOW``).

Values are written as literals: where AutoIt writes the expression
(``BitOR($WS_CAPTION, $WS_SYSMENU)``), the resolved number is emitted and the original
AutoIt text is kept in the trailing comment.
"""

from __future__ import annotations

# --- @SW_* macros (read from the AutoIt interpreter) ---
{chr(10).join(macro_lines)}


{body}
'''

    if missing:
        document += f"\n\n# Missing include files: {', '.join(missing)}\n"
    if unresolved:
        document += "\n\n# Unresolved constants:\n" + "\n".join(
            f"#   {item}" for item in unresolved
        ) + "\n"
    document += f"\n# {total} constants generated.\n"
    return document


def main() -> int:
    """Write ``py4gw/gui/constants.py`` and report what was generated."""

    target = Path(__file__).resolve().parent.parent / "py4gw" / "gui" / "constants.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    document = build_module()
    target.write_text(document, encoding="utf-8")
    line_count = document.count("\n") + 1
    print(f"wrote {target} ({line_count} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
