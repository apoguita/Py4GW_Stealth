"""Generate the UtilityAI **strategy** functions -- ``BestTarget_*``, ``CanUse_*`` and ``Anti_*``.

**What this is, measured first (``docs/GWA3_COMPAT_SPEC.md``).** The two ranking tables
(`py4gw/gwa3/uai_best_target_cache.py`, `uai_can_use_cache.py`) answer a slot's skill id with the *name*
of a strategy function; GwAu3's engine resolves that name with AutoIt's ``Call``. ``Skills/`` holds
**4,572** of those functions across 21 files -- 2,277 ``BestTarget_*``, 2,274 ``CanUse_*`` and 21
``Anti_*`` -- in 20,115 lines, but with only 283 distinct bodies: 1,934 are ``Return`` plus one call,
1,784 are a single ``Anti_*`` guard, 404 are a literal.

**So they are generated, and nothing is invented.** Each body is transcribed statement by statement by
:data:`RULES` and :func:`translate_expression`; a body the translator cannot read, **or one that calls a
name this layer does not implement**, is emitted as a **refusal** naming its source file and line and
quoting the line that stopped it. That second check is what makes a generated body safe to run: a
strategy that would reach an unported member says so instead of raising ``NameError`` in a fight.

**Four rules were added on 2026-10-10, and each closed a shape GwAu3 writes and this translator could
not read** (the shapes are measured in ``tests/scratch/_unreadable_shapes.py``, which prints every
refused body's first unreadable line with its source context):

* ``For $i = 1 To $g_i_AgentCacheCount`` -- **34 bodies**, the largest single blocker. The bound is the
  plugin's own per-frame cache count; this layer keeps no cache and has no rows, so the loop walks the
  **live agent ids** (`_cached_ids`) and the body's ``UAI_GetAgentInfo($i, <column>)`` reads become reads
  *by id*, which is the substitution `py4gw/gwa3/uai_get_agent.py` documents. That is safe **because the
  loop variable is used for nothing else**: all 34 bodies were checked, and every use of ``$i`` is one of
  those reads (``tests/scratch/_loop_variable_uses.py``);
* ``<expr> += <expr>`` on its own line, ``Return`` with no value, ``UBound($x)``, and a call whose answer
  is discarded -- the accumulating form the damage pricing uses, and three statement shapes;
* ``_`` at the end of a line, which AutoIt continues: the logical lines are joined **before** any rule
  sees them, so ``If A And _`` / ``<next line> Then`` is one ``If`` (two `Anti_*` bodies write that);
* and an **inline statement** after ``If ... Then`` translated *as a statement*
  (:func:`_translate_inline_statement`), because ``translate_expression`` rewrites a lone ``=`` into
  ``==`` -- right for a condition, wrong for the assignment ``If $a = 0 Then $a = $b``
  (``UtilityAI_EchoRefrain.au3:393``).

**Three landmines came out of that work, all of them the same species -- a generated body that would
raise at run time instead of refusing:**

1. **A refused agent column was read by transcribed bodies.** Nine of them read
   ``$GC_UAI_AGENT_Distance`` (which the layer refuses as cache-only) or one of the three columns GwAu3's
   two files disagree about, and would have raised the refusal in a fight. ``Distance`` now has a
   *rewrite* -- ``UAI_GetAgentInfo(<agent>, $GC_UAI_AGENT_Distance)`` becomes ``_cached_distance(<agent>)``,
   the same number the cache filled -- and every other refused column makes its body **refuse**, with the
   column named as the reason (:func:`refused_column_reads`, whose set is read from `py4gw/gwa3/uai_agent.py`
   rather than restated here).
2. **A refused predicate was still "available".** 1,099 bodies guard on ``Anti_Attack``/``Anti_Hex``/
   ``Anti_ItemSpell``/``Anti_Spell``; the names were in ``uai_anti.__all__``, so the caller check passed
   and the bodies were transcribed into calls that raised inside the predicate. The anti pass now returns
   the names whose own body refused, and the strategy pass treats those as unavailable.
3. **``ContinueLoop`` after an inline ``Then``** was emitted as a bare expression -- 78 lines across the
   four bodies the new loop rule un-refused, every one of them an undefined name at run time. pyright's
   ``reportUndefinedVariable`` found them. The fix also uncovered #4 above (the inline assignment).

**The measurement that came out of it: 4,571 of the 4,572 strategies are transcribed and 1 refuses** (it
was 4,507 and 65 before that work). The one is `BestTarget_YouAreAllWeaklings`, which calls
``SetExtended`` -- the AutoIt channel this layer has no twin for. The seventeen that read one of the
three **disagreeing** model-state columns were un-refused once this project's own authority settled them
(Reforged Native's ported members use the same three sets as ``GwAu3_Data_Agent.au3``, so the plugin's
cache decoder is the outlier: `py4gw/gwa3/uai_agent.py` carries the comparison and the live
measurement), and `BestTarget_HeroicRefrain` -- the last one blocked by a data member -- was un-refused
by porting ``Attribute_GetPartyAttributeInfo`` and its six siblings
(`py4gw/gwa3/data_attribute.py`).


**Two module shapes.** The 21 ``Anti_*`` predicates go to ``uai_anti.py`` -- they are the shared
dependency of the 1,784 anti-guard bodies, and one module keeps them out of every file's import cycle.
The rest go one module per source file, each importing the predicates it may call.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI" / "Skills"
OUTPUT_DIR = REPO_ROOT / "py4gw" / "gwa3"

FUNC = re.compile(r"(?m)^Func\s+(?P<name>(?:BestTarget|CanUse|Anti)_\w+)\s*\((?P<params>[^)]*)\)\s*$")

#: Python names a transcribed body may use without them being this layer's routines.
_LANGUAGE_NAMES: frozenset[str] = frozenset(
    {
        "abs", "bool", "float", "int", "len", "list", "max", "min", "print", "range", "round",
        "sorted", "str", "sum", "tuple", "Any", "True", "False", "None", "math", "if", "else",
        "return", "and", "or", "not", "in", "is",
    }
)

_OPERATORS: tuple[tuple[str, str], ...] = (
    (r"\bBitAND\(", "("),
    (r"\bBitOR\(", "("),
    # `UBound($x)` is an array's length, which is what `len` answers for the port's list twin.
    (r"\bUBound\(", "len("),
    (r"\bMod\b", "%"),
    (r"<>", "!="),
    (r"\bAnd\b", "and"),
    (r"\bOr\b", "or"),
    (r"\bNot\b", "not"),
)

RULES: tuple[tuple[str, str, str], ...] = (
    ("local", r"^Local\s+\$(?P<name>\w+)\s*=\s*(?P<expr>.+)$", "{name} = {expr}"),
    ("assign", r"^\$(?P<name>\w+)\s*=\s*(?P<expr>.+)$", "{name} = {expr}"),
    # `$x += <expr>` -- the accumulating form GwAu3's damage pricing and its counts use. The inline
    # form (`If c Then $x += e`) is handled by `if-stmt`, which passes the statement through
    # `translate_expression`; this is the standalone line.
    (
        "assign-op",
        r"^\$(?P<name>\w+)\s*(?P<op>\+=|-=|\*=|/=)\s*(?P<expr>.+)$",
        "{name} {op} {expr}",
    ),
    ("return", r"^Return\s+(?P<expr>.+)$", "return {expr}"),
    # `Return` with nothing after it -- a bare early exit, which `UtilityAI_Core.au3:293` uses.
    ("return-bare", r"^Return$", "return"),
    ("if-return", r"^If\s+(?P<cond>.+?)\s+Then\s+Return\s+(?P<expr>.+)$", "if {cond}:\n    return {expr}"),
    # `If cond Then <statement>` -- the shape GwAu3's `Anti_*` predicates use to accumulate, and the one
    # whose absence made `Anti_Enchantment` refuse on the first run.
    ("if-stmt", r"^If\s+(?P<cond>.+?)\s+Then\s+(?P<stmt>.+)$", "if {cond}:\n    {stmt}"),
    ("if", r"^If\s+(?P<cond>.+?)\s+Then$", "if {cond}:"),
    ("elseif", r"^ElseIf\s+(?P<cond>.+?)\s+Then$", "elif {cond}:"),
    ("else", r"^Else$", "else:"),
    ("endif", r"^EndIf$", ""),
    ("continue", r"^ContinueLoop$", "continue"),
    ("exitloop", r"^ExitLoop$", "break"),
    # `For $i = <start> To <end>` -- see :data:`AGENT_CACHE_COUNT` for the one bound that is a
    # substitution rather than a number.
    (
        "for",
        r"^For\s+\$(?P<name>\w+)\s*=\s*(?P<start>\S.*?)\s+To\s+(?P<end>\S.*?)(?:\s+Step\s+(?P<step>.+))?$",
        "for {name} in range({start}, {end} + 1):",
    ),
    ("next", r"^Next$", ""),
    # A call whose answer is discarded. It must come **last** among the statement rules, after every
    # shape that starts with a keyword or an assignment. The `pyright: ignore` is not decoration: the
    # source throws this answer away on purpose (`Skill_UseSkill($l_b_SkillSlot)`), and the checker's
    # `reportUnusedExpression` would otherwise be the one thing keeping this package off "pyright clean".
    ("call", r"^(?P<expr>[A-Za-z_]\w*\s*\(.*\))$", "{expr}  # pyright: ignore[reportUnusedExpression]"),
)

#: The one `For` bound that is **not** a number: ``$g_i_AgentCacheCount`` is how many rows GwAu3's
#: per-frame agent cache holds, and the row index it drives is only ever used as
#: ``UAI_GetAgentInfo($i, <column>)`` -- checked, all thirty-four bodies that write the loop use it for
#: nothing else (`tests/scratch/_loop_variable_uses.py`). This layer keeps no cache and has no rows, so
#: the loop walks the **live agent ids** (`_cached_ids`) and the same reads become reads *by id*, which
#: is the substitution `py4gw/gwa3/uai_get_agent.py` documents for every other row-index walk.
AGENT_CACHE_COUNT = "$g_i_AgentCacheCount"
AGENT_CACHE_LOOP = "for {name} in _cached_ids():"

#: ``UAI_GetAgentInfo(<agent>, $GC_UAI_AGENT_Distance)`` and its siblings, which are **rewritten** rather
#: than refused: the column is one GwAu3 *computes* when it fills its cache, and this layer answers the
#: same number through `_cached_distance` -- the same distance to the player, from the same two live
#: coordinates the cache used (``UtilityAI_AgentCache.au3:163-165``).
DISTANCE_CALLS: tuple[str, ...] = ("UAI_GetAgentInfo", "UAI_GetAgentInfoByID", "UAI_GetPlayerInfo")


class TranscribeError(Exception):
    """A body this translator will not guess at."""

    def __init__(self, line: str, reason: str) -> None:
        super().__init__(f"{reason}: {line}")
        self.line = line
        self.reason = reason


def _split_top_level(arguments: str) -> list[str]:
    """An AutoIt argument list split on its **top-level** commas."""

    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for character in arguments:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(character)
    parts.append("".join(current))
    return parts


def rewrite_distance_calls(expr: str) -> str:
    """``UAI_GetAgentInfo(<agent>, $GC_UAI_AGENT_Distance)`` -> ``_cached_distance(<agent>)``.

    **A rewrite rather than a refusal, because the layer answers this column.** ``Distance`` is one of
    the six the port's `UAI_GetAgentInfo` refuses as cache-only: GwAu3 fills it when it fills its cache,
    as the distance from the agent to the *player*, and `py4gw/gwa3/uai_get_agent.py` computes the same
    number from the same two live coordinates (`_cached_distance`). So a body that reads it is a body
    this layer can run -- and **it could not before**: three transcribed strategies called
    ``UAI_GetAgentInfoByID(<id>, $GC_UAI_AGENT_Distance)`` and would have raised the refusal in a fight.

    The scan is a balanced-parenthesis walk, because the agent argument is sometimes a call
    (``UAI_GetAgentInfoByID($g_i_BestTarget, ...)``) and a regular expression would cut it short. The
    **player form** has no argument at all -- ``UAI_GetPlayerInfo($GC_UAI_AGENT_Distance)`` is the
    player's distance to itself, which is ``0`` -- and it is left to refuse rather than guessed at; no
    body in ``Skills/`` writes it (`tests/scratch/_loop_variable_uses.py` measured the three shapes).
    """

    out: list[str] = []
    index = 0
    while index < len(expr):
        for name in DISTANCE_CALLS:
            if not expr.startswith(name + "(", index):
                continue
            start = index + len(name) + 1
            depth = 1
            cursor = start
            while cursor < len(expr) and depth:
                if expr[cursor] == "(":
                    depth += 1
                elif expr[cursor] == ")":
                    depth -= 1
                cursor += 1
            if depth:
                break
            arguments = expr[start : cursor - 1]
            parts = _split_top_level(arguments)
            if len(parts) == 2 and parts[1].strip() == "$GC_UAI_AGENT_Distance":
                out.append(f"_cached_distance({parts[0].strip()})")
                index = cursor
                break
            out.append(expr[index:cursor])
            index = cursor
            break
        else:
            out.append(expr[index])
            index += 1
    return "".join(out)


#: The statement keywords that can appear **inline** after `If <cond> Then`. AutoIt writes
#: `If <cond> Then ContinueLoop` inside its loops, and `ContinueLoop` is not an expression: emitting it
#: through `translate_expression` left the literal word in the generated body, where it would be an
#: undefined name at run time. The four loop bodies this round un-refused had 78 of them, and pyright
#: found every one (`reportUndefinedVariable`).
_INLINE_STATEMENTS: dict[str, str] = {
    "ContinueLoop": "continue",
    "ExitLoop": "break",
}


def _translate_inline_statement(stmt: str) -> str:
    """The statement GwAu3 writes after an inline `Then`, translated **as a statement**.

    Five forms appear in the plugin, and the order matters:

    * ``ContinueLoop``/``ExitLoop`` -- the loop keywords, which are not expressions at all (78 of them
      in the four bodies this round un-refused, and pyright's ``reportUndefinedVariable`` found every
      one);
    * ``Return <expr>`` / a bare ``Return``;
    * ``$x = <expr>`` -- **an assignment**, and it must be translated as one: ``translate_expression``
      rewrites a lone ``=` between values into ``==`` (that is AutoIt's *equality* in a condition), so
      sending this form through it emitted ``l_i_FallbackAlly == l_i_AgentID`` where the source assigns
      (``UtilityAI_EchoRefrain.au3:393``);
    * ``$x += <expr>`` -- the compound form;
    * anything else, which is a call whose answer is discarded.
    """

    stripped = stmt.strip()
    if stripped in _INLINE_STATEMENTS:
        return _INLINE_STATEMENTS[stripped]
    if stripped.startswith("Return"):
        rest = stripped[len("Return") :].strip()
        return f"return {translate_expression(rest)}" if rest else "return"

    assignment = re.match(r"^\$(?P<name>\w+)\s*=\s*(?P<expr>.+)$", stripped)
    if assignment:
        return f"{assignment.group('name')} = {translate_expression(assignment.group('expr'))}"

    compound = re.match(
        r"^\$(?P<name>\w+)\s*(?P<op>\+=|-=|\*=|/=)\s*(?P<expr>.+)$", stripped
    )
    if compound:
        return (
            f"{compound.group('name')} {compound.group('op')} "
            f"{translate_expression(compound.group('expr'))}"
        )

    return translate_expression(stmt)


def translate_expression(expr: str) -> str:
    """AutoIt expression to Python, or :class:`TranscribeError` for anything not understood."""

    if "@error" in expr or expr.startswith("SetError"):
        raise TranscribeError(expr, "AutoIt's error channel has no twin here")

    text = rewrite_distance_calls(expr)
    for pattern, replacement in _OPERATORS:
        text = re.sub(pattern, replacement, text)

    # A lone `=` between values is AutoIt's equality (assignment is a statement shape, handled above).
    text = re.sub(r"(?<=[\w\)\]\"'])\s*=\s*(?=[\w\$\(\"'-])", " == ", text)

    text = re.sub(r"\$GC_(\w+)", r"_constants.GC_\1", text)
    text = re.sub(r"\$g_(\w+)", r"uai_const.g_\1", text)
    # Every other `$name` becomes `name`, prefix and all (`$l_i_Target` -> `l_i_Target`). **Keeping the
    # prefix is what makes local names unique**: stripping `l_`/`a_` collapses `$l_i_Target` and
    # `$a_i_Target` into one name.
    text = re.sub(r"\$(\w+)", r"\1", text)

    # AutoIt's ternary (`cond ? a : b`) is Python's `a if cond else b`; anything left with a `?` refuses.
    text = re.sub(r"\(([^()?]+?)\s*\?\s*([^:()]+?)\s*:\s*([^()]+?)\)", r"(\2 if \1 else \3)", text)
    if "?" in text:
        raise TranscribeError(expr, "an AutoIt ternary this translator cannot rewrite")

    return text.strip()


def translate_body(body: str) -> str:
    """The body's statements as Python, or :class:`TranscribeError` for the first unreadable line."""

    out: list[str] = []
    indent = 0
    # AutoIt's `_` at the end of a line continues it, so the logical lines are joined **before** any
    # statement rule sees them: `If A And _` / `<next line> Then` is one `If`. GwAu3 writes two of the
    # `Anti_*` predicates that way, and before this join they refused on the first half of an `If`.
    logical: list[str] = []
    for raw in body.splitlines():
        stripped = raw.split(";", 1)[0].rstrip() if not raw.lstrip().startswith(";~") else ""
        if logical and logical[-1].endswith("_"):
            logical[-1] = logical[-1][:-1].rstrip() + " " + stripped.strip()
            continue
        logical.append(stripped)

    for line in logical:
        line = line.strip()
        if not line or line.startswith(";~") or line.startswith("#"):
            continue

        for kind, pattern, template in RULES:
            match = re.match(pattern, line)
            if not match:
                continue
            groups = match.groupdict()
            expr = translate_expression(groups["expr"]) if groups.get("expr") else ""
            cond = translate_expression(groups["cond"]) if groups.get("cond") else ""
            stmt = groups.get("stmt", "")
            if stmt:
                # The inline statement's own shape is translated but not re-read: the three forms GwAu3
                # writes inline are an assignment, a `ContinueLoop`/`ExitLoop`, and a call.
                stmt = _translate_inline_statement(stmt)
            if kind == "for":
                # The cache-count bound is the one substitution: the loop walks the live agent ids.
                source_end = match.groupdict().get("end", "")
                if match.groupdict().get("step"):
                    # No `For` in `Skills/` writes a `Step` (checked: 39 loops, none stepped), and a
                    # stepped loop emitted as a plain `range` would silently change the iteration -- so
                    # it refuses rather than being approximated.
                    raise TranscribeError(line, "a `For` with a `Step`, which this translator does not read")
                if source_end and source_end.strip() == AGENT_CACHE_COUNT:
                    template = AGENT_CACHE_LOOP
                    start = 0
                    expr = ""
                else:
                    start = translate_expression(groups["start"])
                text = template.format(name=groups["name"], start=start, expr=expr, end=expr)
            else:
                text = template.format(
                    name=groups.get("name", ""),
                    expr=expr,
                    cond=cond,
                    stmt=stmt,
                    op=groups.get("op", ""),
                )
            if kind in ("else", "elseif", "next"):
                indent = max(0, indent - 1)
            prefix = "    " * indent
            for piece in text.split("\n"):
                out.append(f"{prefix}{piece}" if piece else "")
            # **Only a block opener indents.** `If ... Then Return ...` is one self-contained line with no
            # `EndIf` of its own; indenting after it walked the body a level deeper per guard, which the
            # import check caught as an `IndentationError`.
            if kind in ("if", "elseif", "else", "for"):
                indent += 1
            break
        else:
            raise TranscribeError(line, "no statement rule")

    return "\n".join(out)


def refused_agent_columns() -> frozenset[str]:
    """Every ``$GC_UAI_AGENT_*`` column the layer's own accessor **refuses**, read from its source text.

    **This is the check that keeps a transcribed body from raising.** `py4gw/gwa3/uai_agent.py` refuses
    six columns GwAu3 fills in its cache and three the two GwAu3 files disagree about
    (``IsMoving``/``IsAttacking``/``IsIdle``: one file treats model state ``0x40`` as *attacking*, another
    as *idle*). A strategy body that reads one of them would have raised that refusal **in a fight** --
    and nine transcribed bodies did exactly that until this check existed, including
    `CanUse_Dash` (``IsMoving``) and `CanUse_CriticalEye` (``IsAttacking``). A body reading one now
    refuses with that reason instead, which is also a better work item than "no statement rule".

    ``Distance`` is **not** in that set any more, and it was never refused here: `rewrite_distance_calls`
    turns its three call shapes into ``_cached_distance``, and the layer's own accessor answers the column
    the same way (`py4gw/gwa3/uai_agent.py`), so a rewritten body and a script get the same quantity.
    """

    text = (OUTPUT_DIR / "uai_agent.py").read_text(encoding="utf-8", errors="replace")
    columns: set[str] = set()
    for table in ("_DISAGREEING_COLUMNS", "_CACHE_ONLY_COLUMNS"):
        match = re.search(rf"(?ms)^{table}\s*:\s*dict\[str, str\]\s*=\s*\{{(.*?)^\}}", text)
        if match is None:
            continue
        columns.update(re.findall(r'^\s*"(\w+)":', match.group(1), re.M))
    return frozenset(columns - {"Distance"})


def refused_column_reads(translated: str) -> list[str]:
    """The refused columns a translated body reads, in the source's own spelling."""

    return sorted(
        {
            name
            for name in re.findall(r"_constants\.GC_UAI_AGENT_(\w+)", translated)
            if name in refused_agent_columns()
        }
    )


def called_names(python_body: str) -> set[str]:
    """Every name the transcribed body calls, so an unported one can refuse instead of raising."""

    return {
        name
        for name in re.findall(r"(?<![\w.])(\w+)\s*\(", python_body)
        if name not in _LANGUAGE_NAMES
    }


def parse_functions(path: Path, prefixes: tuple[str, ...]) -> list[tuple[str, str, str, int]]:
    """``[(name, params, body, line)]`` for one file and the families wanted from it."""

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    found: list[tuple[str, str, str, int]] = []
    for match in FUNC.finditer(text):
        if not match.group("name").startswith(prefixes):
            continue
        end = text.find("EndFunc", match.end())
        if end == -1:
            continue
        line = text[: match.start()].count("\n") + 1
        found.append((match.group("name"), match.group("params"), text[match.end() : end], line))
    return found


def surface_names() -> frozenset[str]:
    """Every routine this layer implements, by GwAu3's name -- the check a body has to pass.

    **Built module by module, and a module that will not import is skipped rather than fatal.** The
    generator has to be able to run on a tree whose generated code is broken -- that is exactly when it
    is needed -- and a hard failure here is a deadlock: the package cannot import until the generator
    rewrites the file, and the generator cannot run until the package imports. It happened once (a
    self-import the generator itself had emitted), and this is the fix.
    """

    return frozenset(import_map())


def import_map() -> dict[str, str]:
    """``{routine name: the ``py4gw.gwa3`` module that declares it}``, read **statically**.

    The names come from each module's own ``__all__`` in its source text, not from importing it. That is
    the point: the generator has to run on a tree whose generated code is broken -- that is exactly when
    it is needed -- and importing the package to ask would fail on the very file this run is rewriting.
    It happened once, and it is a deadlock: the package cannot import until the generator rewrites the
    file, and the generator cannot run until the package imports.

    **Two private names are added by hand**, because a body needs them and neither is in an ``__all__``:
    ``_cached_ids`` (the live agent ids a ``$g_i_AgentCacheCount`` loop walks) and ``_cached_distance``
    (the column the ``Distance`` rewrite reads). Both live in `py4gw/gwa3/uai_get_agent.py`.
    """

    mapping: dict[str, str] = {
        "_cached_ids": "uai_get_agent",
        "_cached_distance": "uai_get_agent",
    }
    for path in sorted(OUTPUT_DIR.glob("*.py")):
        if path.stem == "__init__":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"(?ms)^__all__\s*=\s*\[(.*?)\]", text)
        if match is None:
            continue
        for name in re.findall(r"[\"'](\w+)[\"']", match.group(1)):
            mapping.setdefault(name, path.stem)
    return mapping


def import_block(needed: set[str], owners: dict[str, str], skip: frozenset[str] = frozenset()) -> str:
    """The ``from .<module> import (...)`` lines for the names a generated module's bodies call."""

    by_module: dict[str, list[str]] = {}
    for name in sorted(needed):
        module = owners.get(name)
        if module is None or module in skip:
            continue
        by_module.setdefault(module, []).append(name)

    lines: list[str] = []
    for module in sorted(by_module):
        names = by_module[module]
        if len(names) == 1:
            lines.append(f"from .{module} import {names[0]}")
        else:
            lines.append(f"from .{module} import (\n" + "".join(f"    {n},\n" for n in names) + ")")
    return "\n".join(lines) + ("\n" if lines else "")


def constant_names() -> frozenset[str]:
    """Every ``GC_*`` name the generated constants module carries.

    Read statically, like the import map: the check has to work on a tree whose code may not import. A
    body naming a constant this layer does not carry would raise ``AttributeError`` where the source
    reads a value -- the same landmine class as an unimported call, and the reason both are checked here.
    """

    text = (OUTPUT_DIR / "constants.py").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?ms)^__all__\s*=\s*\[(.*?)\n\]", text)
    if match is None:
        return frozenset()
    return frozenset(re.findall(r"[\"'](\w+)[\"']", match.group(1)))


def declared_constant_spelling(translated: str) -> str:
    """Rewrite every ``_constants.X`` to the spelling the constants module **declares**.

    **AutoIt variable names are case-insensitive**, so GwAu3's plugin bodies write
    ``$GC_I_SKILL_ID_Spirit_Shackles`` where its own constants file declares
    ``$GC_I_SKILL_ID_SPIRIT_SHACKLES`` -- and so do thirty names the hand-written port had to fix one by
    one when it was first written (`py4gw/gwa3/uai_can_cast.py` records that). Python is case-sensitive,
    so the transcription must use the declared spelling; a name with no declared twin is left alone and
    the constant check refuses the body, which is what happens to the three bodies naming a ``*_PvP``
    skill id GwAu3 never declares.
    """

    declared = constant_names()
    by_lower = {name.lower(): name for name in declared}

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in declared:
            return match.group(0)
        return f"_constants.{by_lower[name.lower()]}" if name.lower() in by_lower else match.group(0)

    return re.sub(r"_constants\.(\w+)", replace, translated)


def render_function(
    name: str,
    params: str,
    body: str,
    source_file: str,
    line: int,
    available: frozenset[str],
    prologue: str = "",
) -> tuple[str, bool]:
    """One function's text, and whether it is routed (``False`` means it refuses).

    ``prologue`` is the deferred imports a body needs for *other strategies it calls*: a strategy that
    calls a strategy in another generated module imports it **inside the function**, because a
    module-level import between two strategy modules is a cycle (the first run of this generator emitted
    those and every module failed to import -- `ImportError: cannot import name 'BestTarget_AgnarsRage'
    from partially initialized module`).
    """

    signature = ", ".join(part.strip().lstrip("$") for part in params.split(",") if part.strip())
    reason: str | None = None
    quoted = ""
    try:
        translated = translate_body(body)
        # AutoIt is case-insensitive about variable names; the constants module is not. Normalise first,
        # so the checks below and the emitted code all use the declared spelling.
        translated = declared_constant_spelling(translated)
        missing = sorted(called_names(translated) - available)
        if missing:
            raise TranscribeError(missing[0], "calls a name this layer does not implement")
        refused = refused_column_reads(translated)
        if refused:
            raise TranscribeError(
                f"$GC_UAI_AGENT_{refused[0]}",
                "reads a column this layer refuses, so the body cannot answer correctly",
            )
        unknown_constants = sorted(
            name
            for name in set(re.findall(r"_constants\.(\w+)", translated))
            if name not in constant_names()
        )
        if unknown_constants:
            raise TranscribeError(
                unknown_constants[0], "names a constant this layer does not carry"
            )
    except TranscribeError as error:
        reason = error.reason
        quoted = error.line.replace('"', "'")
        translated = ""

    if reason is not None:
        return (
            f'def {name}({signature}) -> Any:\n'
            f'    """**REFUSED: this body is not transcribed.**\n\n'
            f'    ``{source_file}:{line}`` -- {reason}. The body is\n\n'
            f'    .. code-block:: text\n\n'
            f'        {quoted}\n\n'
            f'    A strategy is the source\'s content -- which agent a skill wants, under which guard -- so\n'
            f'    it is transcribed or refused, never re-derived. The line above is what stopped this one,\n'
            f'    and it is this function\'s work item.\n'
            f'    """\n\n'
            f'    raise NotImplementedError(\n'
            f'        "`{name}` (`{source_file}:{line}`) has a body this layer does not port: "\n'
            f'        "{reason}: {quoted}"\n'
            f'    )\n',
            False,
        )

    if not translated.strip():
        translated = "return 0"
    if prologue:
        translated = prologue + "\n" + translated
    indented = "\n".join(f"    {piece}" if piece else "" for piece in translated.split("\n"))
    return (
        f'def {name}({signature}) -> Any:\n'
        f'    """``{source_file}:{line}`` -- transcribed from GwAu3\'s own body."""\n\n'
        f"{indented}\n",
        True,
    )


STRATEGY_HEADER = '''"""GwAu3's ``{source_file}`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **{routed} of this file's {total} are transcribed and {refused}
refuse** -- a body the translator cannot read, or one calling a name this layer does not implement,
refuses by name rather than answering a plausible target.

Their callees are this layer's own: ``UAI_GetNearestAgent``, ``UAI_GetAgentLowest``,
``UAI_GetPlayerInfo``, ``UAI_GetBestSingleTarget``, ``UAI_PlayerHasEffect``,
``UAI_GetPlayerEffectInfo``, ``Party_GetPetInfo`` and the ``Anti_*`` predicates in
`py4gw/gwa3/uai_anti.py`.
"""

from __future__ import annotations

import math
from typing import Any

from . import constants as _constants
from . import uai_const
from .uai_agent import UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_effects import UAI_AgentHasEffect, UAI_GetPlayerEffectInfo, UAI_PlayerHasEffect
from .uai_filter import (
    UAI_Filter_IsLivingAlly,
    UAI_Filter_IsLivingEnemy,
    UAI_Filter_IsMoving,
    UAI_Filter_IsSpirit,
)
from .uai_get_agent import (
    UAI_GetAgentHighest,
    UAI_GetAgentLowest,
    UAI_GetBestSingleTarget,
    UAI_GetFarthestAgent,
    UAI_GetNearestAgent,
)
from .uai_anti import (
{anti_imports})
{imports}

'''

ANTI_HEADER = '''"""GwAu3's ``Anti_*`` predicates: whether a skill of a kind is worth using right now.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``).

**What these are, and why they have a module of their own.** ``Anti_Spell`` answers "is a spell worth
casting at this moment"; its siblings ask the same about enchantments, attacks, hexes, stances, shouts,
signets, chants, weapon spells, item spells, preparations, traps, pet attacks, wards, echo/refrains,
glyphs and wells. **1,784 of the 4,572 strategy functions are a single one of these guards** -- the
largest single block in the ranking -- so they are one module, imported by every strategy module, which
also keeps the import graph acyclic.

{routed} of {total} are transcribed; {refused} refuse, with the source line that stopped the translator.
"""

from __future__ import annotations

import math
from typing import Any

from . import constants as _constants
from . import uai_const
from .uai_agent import UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_effects import (
    UAI_AgentHasEffect,
    UAI_GetPlayerEffectInfo,
    UAI_PlayerHasEffect,
)
from .uai_filter import UAI_Filter_IsLivingAlly, UAI_Filter_IsLivingEnemy, UAI_Filter_IsSpirit
from .uai_get_agent import (
    UAI_GetAgentLowest,
    UAI_GetBestSingleTarget,
    UAI_GetNearestAgent,
)
{imports}

'''

TRAILER = '''

__all__ = [
{exports}]
'''

#: Every file that declares a strategy function, so every name the two tables answer resolves.
SOURCE_FILES: tuple[str, ...] = (
    "UtilityAI_Attack.au3",
    "UtilityAI_Chant.au3",
    "UtilityAI_EchoRefrain.au3",
    "UtilityAI_Enchantment.au3",
    "UtilityAI_Form.au3",
    "UtilityAI_Glyph.au3",
    "UtilityAI_Hex.au3",
    "UtilityAI_ItemSpell.au3",
    "UtilityAI_PetAttack.au3",
    "UtilityAI_Preparation.au3",
    "UtilityAI_Ritual.au3",
    "UtilityAI_Shout.au3",
    "UtilityAI_Signet.au3",
    "UtilityAI_Skill10.au3",
    "UtilityAI_Skill16.au3",
    "UtilityAI_Spell.au3",
    "UtilityAI_Stance.au3",
    "UtilityAI_Trap.au3",
    "UtilityAI_Ward.au3",
    "UtilityAI_WeaponSpell.au3",
    "UtilityAI_Well.au3",
)


@dataclass
class Result:
    """What one generated module emitted."""

    routed: int = 0
    refused: int = 0
    total: int = 0


def module_name(source_file: str) -> str:
    return "uai_strategy_" + source_file[len("UtilityAI_") : -len(".au3")].lower()


def generate_anti(available: frozenset[str], owners: dict[str, str]) -> tuple[str, Result, list[str], list[str]]:
    """``uai_anti.py``: the 21 predicates, gathered from every file that declares one.

    **It returns the names that *refused* as well as the ones it wrote**, because a predicate that
    refuses is not usable by a strategy body: 1,099 bodies guard on ``Anti_Attack``/``Anti_Hex``/
    ``Anti_ItemSpell``/``Anti_Spell``, and while those four refused the caller check could not see it --
    the names were in ``__all__``, so the bodies transcribed and would have raised the predicate's own
    refusal **inside a fight**. The strategy pass now treats a refused predicate as unavailable, which is
    the same landmine rule as an unimported call.
    """

    pieces: list[str] = []
    names: list[str] = []
    refused_names: list[str] = []
    needed: set[str] = set()
    result = Result()
    for source_file in SOURCE_FILES:
        for name, params, body, line in parse_functions(SKILLS_DIR / source_file, ("Anti_",)):
            text, routed = render_function(name, params, body, source_file, line, available)
            pieces.append(text)
            names.append(name)
            if routed:
                needed |= called_names(text)
            else:
                refused_names.append(name)
            result.total += 1
            result.routed += 1 if routed else 0
            result.refused += 0 if routed else 1
    exports = "".join(f'    "{name}",\n' for name in sorted(names))
    text = (
        ANTI_HEADER.format(
            routed=result.routed,
            total=result.total,
            refused=result.refused,
            # **A predicate never imports itself**: `Anti_X` bodies call their siblings, and those are
            # defined in this very module. The first run mapped them to `.uai_anti` and the module
            # imported itself -- caught by the import check, which is why every generated module is
            # imported before anything is claimed about it.
            imports=import_block(needed, owners, skip=frozenset({"uai_anti"})),
        )
        + "\n\n".join(pieces)
        + TRAILER.format(exports=exports)
    )
    return text, result, names, refused_names


def generate_strategy(
    source_file: str,
    anti_names: list[str],
    available: frozenset[str],
    owners: dict[str, str],
    unusable: frozenset[str] = frozenset(),
) -> tuple[str, Result]:
    """One file's ``BestTarget_*``/``CanUse_*`` functions.

    ``unusable`` is the set of names the layer declares but whose **own body refused** in this run -- the
    ``Anti_*`` predicates that could not be transcribed. A body calling one of those refuses instead of
    being transcribed into a call that raises.
    """

    functions = parse_functions(SKILLS_DIR / source_file, ("BestTarget_", "CanUse_"))
    usable = (available | frozenset(anti_names)) - unusable
    # **A strategy module never imports another strategy module at module scope.** Bodies that call a
    # strategy defined elsewhere get that import *inside the function*, which is the only shape that
    # cannot cycle: the two modules would otherwise import each other and neither would finish.
    strategy_owners = {
        name: module for name, module in owners.items() if module.startswith("uai_strategy_")
    }
    pieces: list[str] = []
    needed: set[str] = set()
    result = Result(total=len(functions))
    for name, params, body, line in functions:
        text, routed = render_function(name, params, body, source_file, line, usable)
        if routed:
            cross = sorted(
                called
                for called in called_names(text)
                if strategy_owners.get(called, "") not in ("", module_name(source_file))
            )
            if cross:
                prologue = "\n".join(
                    f"from .{strategy_owners[called]} import {called}" for called in cross
                )
                text, routed = render_function(
                    name, params, body, source_file, line, usable, prologue=prologue
                )
            else:
                needed |= called_names(text)
        pieces.append(text)
        result.routed += 1 if routed else 0
        result.refused += 0 if routed else 1
    anti_imports = "".join(f"    {name},\n" for name in sorted(anti_names))
    exports = "".join(f'    "{name}",\n' for name, _, _, _ in sorted(functions))
    text = (
        STRATEGY_HEADER.format(
            source_file=source_file,
            routed=result.routed,
            refused=result.refused,
            total=result.total,
            anti_imports=anti_imports,
            imports=import_block(needed, owners, skip=frozenset({"uai_anti"}) | {
                module for module in strategy_owners.values()
            }),
        )
        + "\n\n".join(pieces)
        + TRAILER.format(exports=exports)
    )
    return text, result


def main() -> int:
    available = surface_names()
    owners = import_map()

    anti_text, anti_result, anti_names, anti_refused = generate_anti(available, owners)
    (OUTPUT_DIR / "uai_anti.py").write_text(anti_text, encoding="utf-8")
    # **The anti predicates are mapped explicitly, not read back from the package.** `import_map()` runs
    # before this file is written, so a run that has just changed the predicates would otherwise generate
    # its strategy modules against the *previous* content -- output that depends on its own last run.
    # The ones whose own body refused are mapped too, and then **removed from availability** below: a
    # body calling one must refuse rather than raise the predicate's refusal at run time.
    owners = {**owners, **{name: "uai_anti" for name in anti_names}}
    print(f"Wrote py4gw/gwa3/uai_anti.py -- {anti_result.routed} transcribed, {anti_result.refused} refused")

    routed = anti_result.routed
    refused = anti_result.refused
    unusable = frozenset(anti_refused)
    for source_file in SOURCE_FILES:
        text, result = generate_strategy(source_file, anti_names, available, owners, unusable)
        # **`.py` is not decoration here.** The first version wrote `OUTPUT_DIR / module_name(...)`, and
        # `module_name` answers a *module* name (`uai_strategy_attack`) -- so every run wrote
        # extension-less files beside the real ones and the generated modules never changed, while the
        # run reported success. What caught it was the currency test, which compares the files on disk
        # with what the generator produces: exactly the check that exists for this.
        (OUTPUT_DIR / f"{module_name(source_file)}.py").write_text(text, encoding="utf-8")
        routed += result.routed
        refused += result.refused
        if result.total:
            print(
                f"  {module_name(source_file)}: {result.routed} transcribed, "
                f"{result.refused} refused of {result.total}"
            )
    print(f"total: {routed} transcribed, {refused} refused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
