"""Generate ``py4gw/gwa3/uai_best_target_cache.py`` and ``uai_can_use_cache.py``.

**What these two GwAu3 files are, measured rather than assumed.** Each is a *dispatch table* and nothing
else: one function whose whole body is a ``Switch`` over the slot's skill id, and 2,300 (``BestTarget``)
or 2,292 (``CanUse``) ``Case`` lines that ``Return`` a **strategy function's name as a string**, which
GwAu3's engine resolves with AutoIt's ``Call``. No arithmetic, no reads, no decisions -- a skill id maps
to a name.

That is why they are generated: a table transcripted by hand would drift from the source the moment a
skill was added, and there is nothing here to *understand*. The generator reads the ``Case``/``Return``
pair out of the source, resolves the constant through ``py4gw/gwa3/constants.py`` (the 7,480 names built
from GwAu3's own declarations), and writes one dictionary plus one lookup per file.

**What is *not* here, and it is the honest half of the measurement.** The names in these tables point at
4,551 strategy functions in ``API/Plugins/UtilityAI/Skills/`` -- ``BestTarget_*`` and ``CanUse_*``, 20,115
lines between them. They are **not** ported by this generator, and the two lookup functions return the
same *names* GwAu3 returns rather than inventing a strategy of their own. A caller that needs the
strategy's *decision* needs those modules; the census says what that costs: of the 4,551, **1,934 are
``Return`` plus one call**, **1,784 are a single ``Anti_*`` guard**, **404 are a literal**, 130 are three
lines or fewer and 299 are longer -- i.e. **283 distinct bodies**, of which eight cover 3,300 functions.
The next work item is a generator for those bodies, with the ones it cannot transcribe refusing by name.

Run: ``python tools/generate_gwa3_ranking.py``
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GWAU3_CACHE = REPO_ROOT / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI" / "Cache"
OUTPUT_DIR = REPO_ROOT / "py4gw" / "gwa3"

CASE = re.compile(r"^\s*Case\s+(?P<constant>\$GC_I_SKILL_ID_\w+)\s*$")
RETURN = re.compile(r'^\s*Return\s+"(?P<name>\w+)"\s*$')


class Table:
    """One of the two files: its GwAu3 source, its function, its module and its strategy prefix."""

    def __init__(self, source_file: str, module: str, function: str, prefix: str, summary: str) -> None:
        self.source_file = source_file
        self.module = module
        self.function = function
        self.prefix = prefix
        self.summary = summary

    @property
    def source_path(self) -> Path:
        return GWAU3_CACHE / self.source_file

    @property
    def output_path(self) -> Path:
        return OUTPUT_DIR / f"{self.module}.py"


TABLES: tuple[Table, ...] = (
    Table(
        source_file="UtilityAI_BestTargetCache.au3",
        module="uai_best_target_cache",
        function="UAI_GetBestTargetFunc",
        prefix="BestTarget",
        summary=(
            "which target a skill wants: a slot's skill id maps to the name of a ``BestTarget_*``\n"
            "strategy, and the engine resolves that name and calls it"
        ),
    ),
    Table(
        source_file="UtilityAI_CanUseCache.au3",
        module="uai_can_use_cache",
        function="UAI_GetCanUseFunc",
        prefix="CanUse",
        summary=(
            "whether a skill may be used at all: a slot's skill id maps to the name of a ``CanUse_*``\n"
            "strategy -- most of them one guard, ``If Anti_X() Then Return False``"
        ),
    ),
)


def parse_cases(table: Table) -> list[tuple[str, str]]:
    """``[(constant name, strategy name)]`` in the source's own order.

    The parser walks the file line by line and pairs each ``Case`` with the ``Return`` that follows it,
    so a file whose shape changed would produce fewer pairs rather than a wrong table -- and the test
    asserts the count against the source's own ``Case`` count, which is what makes that visible.
    """

    pairs: list[tuple[str, str]] = []
    pending: str | None = None
    for raw in table.source_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        case = CASE.match(raw)
        if case:
            # The source spells the constant with GwAu3's leading `$`; `py4gw/gwa3/constants.py` drops it
            # (`$GC_I_ALLEGIANCE_ENEMY` reads `GC_I_ALLEGIANCE_ENEMY`), so the name is stripped here.
            pending = case.group("constant").lstrip("$")
            continue
        returned = RETURN.match(raw)
        if returned and pending is not None:
            pairs.append((pending, returned.group("name")))
            pending = None
    return pairs


def render(table: Table, pairs: list[tuple[str, str]]) -> str:
    entries = "".join(
        f"    _constants.{constant}: {name!r},\n" for constant, name in pairs
    )
    strategies = sorted({name for _, name in pairs})
    return f'''"""{table.summary[0].upper()}{table.summary[1:]}, generated from GwAu3's own table.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_ranking.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

``{table.function}`` is GwAu3's ``{table.source_file}`` in full: a ``Switch`` over the slot's skill id
with **{len(pairs):,}** ``Case`` lines, each answering the **name of a strategy function as a string** --
the same shape this module keeps, and the same strings. There is no ``Case Else`` in the source, so a
skill id that is in no case answers the empty string here, which is what the source's own fall-through
answers.

**What this module is not.** The {len(strategies):,} names it answers point at strategy functions in
``API/Plugins/UtilityAI/Skills/``, and **those are not ported yet** (see the generator's header and
``docs/GWA3_COMPAT_SPEC.md`` for the measured size: 4,551 functions, 283 distinct bodies, 20,115 lines).
A caller that needs the *decision* the name stands for needs those modules; this module answers the name
GwAu3 would answer and nothing more, which is exactly what GwAu3's own engine consumes.
"""

from __future__ import annotations

from typing import Any

from . import constants as _constants
from .uai_static_skill_cache import UAI_GetStaticSkillInfo

__all__ = ["{table.function}"]

#: ``{{skill id: the strategy function's name}}``, GwAu3's ``Case`` lines in its own order.
_STRATEGIES: dict[int, str] = {{
{entries}}}


def {table.function}(skill_slot: Any) -> Any:
    """The strategy function's name for a slot's skill (``{table.source_file}``).

    GwAu3 switches on ``UAI_GetStaticSkillInfo($a_i_SkillSlot, $GC_UAI_STATIC_SKILL_SkillID)`` -- the
    slot's skill id read from the live skillbar, which this layer answers itself -- so the lookup is the
    same two steps the source makes, in the same order. An empty slot (skill id ``0``) and a skill id in
    no case both answer ``""``, which is the source's own fall-through with no ``Case Else``.
    """

    skill_id = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_SkillID)
    return _STRATEGIES.get(int(skill_id), "")
'''


def main() -> int:
    for table in TABLES:
        pairs = parse_cases(table)
        constants = {constant for constant, _ in pairs}
        table.output_path.write_text(render(table, pairs), encoding="utf-8")
        print(f"Wrote {table.output_path.relative_to(REPO_ROOT)}")
        print(
            f"  {table.source_file}: {len(pairs):,} cases, {len(constants):,} distinct skill constants, "
            f"{len({name for _, name in pairs}):,} distinct strategies"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
