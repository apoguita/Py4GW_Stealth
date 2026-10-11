"""GwAu3's ``Attribute_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Two of the six are routed and four refuse**, and the split is worth reading before the code, because
the four are not one kind of thing:

* ``Attribute_LoadSkillTemplate`` and ``Attribute_ChangeSecondProfession`` reach the client's own
  functions through the ported `SkillBar`, which is the same effect GwAu3's packets ask for.
* ``Attribute_IncreaseAttribute`` and ``Attribute_DecreaseAttribute`` forge
  ``HEADER_ATTRIBUTE_INCREASE``/``_DECREASE`` *repeatedly* -- one packet per point of ``$a_i_Amount``
  -- and this project has no member that raises an attribute at all. Answering `True` would report
  points that were never spent.
* ``Attribute_CalculateAttributeSpread`` **touches no client state at all**: it is AutoIt arithmetic
  over an array the caller hands it. It takes its array **`ByRef`**, which has no meaning across the
  bridge -- a Python worker receives the values, not the caller's variable -- so its contract cannot be
  reproduced from here and it refuses rather than return a result the caller cannot receive.
* ``Attribute_LoadAttributes`` sends one packet, but only after walking and validating a caller array
  the same way; it is refused for the same `ByRef` reason as the spread.
"""

from __future__ import annotations

from typing import Any

from ..skillbar import SkillBar

__all__ = [
    "Attribute_CalculateAttributeSpread",
    "Attribute_ChangeSecondProfession",
    "Attribute_DecreaseAttribute",
    "Attribute_IncreaseAttribute",
    "Attribute_LoadAttributes",
    "Attribute_LoadSkillTemplate",
]

#: GwAu3's own maximum for an attribute, from the guards it makes in `IncreaseAttribute`/`Decrease`.
_MAX_ATTRIBUTE = 12


def Attribute_LoadSkillTemplate(template: Any, hero_number: Any = 0) -> None:
    """Load a skill template onto a character or hero (``GwAu3_Cmd_Attribute.au3``).

    GwAu3's guard order is kept, and so is the shape of the failure: it answers **False** when the
    template is empty, when it is not a string, when the hero is not in the party, and when the
    client's own loader refuses -- and **True** only after the packet is enqueued. This project's
    loader answers nothing, so the failure shapes cannot be reproduced by returning; they are refused
    through the bridge instead, which is where a caller reads the reason.

    Hero ``0`` is the controlled character (``SkillBar.LoadSkillTemplate``) and ``1..n`` are heroes
    (``SkillBar.LoadHeroSkillTemplate``), which is GwAu3's own numbering.
    """

    if int(hero_number) == 0:
        SkillBar.LoadSkillTemplate(template)
        return
    SkillBar.LoadHeroSkillTemplate(int(hero_number), template)


def Attribute_ChangeSecondProfession(profession: Any, hero_number: Any = 0) -> bool:
    """Change a character's or hero's secondary profession (``GwAu3_Cmd_Attribute.au3``).

    GwAu3 forges ``HEADER_PROFESSION_CHANGE`` with the hero's **id** (``$l_i_HeroID``, resolved from
    the hero number) and the profession. The ported member takes the hero **index** and the
    profession, which is the same request through the client's own function -- and the two hero
    spellings are checked here rather than assumed: `ChangeHeroSecondary`'s argument is an index, and
    GwAu3's is a number, and they are the same number.
    """

    SkillBar.ChangeHeroSecondary(int(hero_number), int(profession))
    return True


def Attribute_IncreaseAttribute(attribute_id: Any, amount: Any = 1, hero_number: Any = 0) -> bool:
    """**REFUSED: no route yet.** GwAu3 forges one ``HEADER_ATTRIBUTE_INCREASE`` per point.

    ``GwAu3_Cmd_Attribute.au3`` walks the amount, sending a packet for each point, with guards on the
    attribute id and on the resulting value not exceeding ``12``. **This project has no member that
    raises an attribute**: nothing in ``py4gw/`` calls ``IncreaseAttribute``'s resolved function
    (``offsets/gwau3_leads.json`` does not carry it), so there is nothing to route to. The work is a
    resolver for the client's own attribute function, and it is recorded in ``docs/GWA3_ROUTE_MAP.md``
    rather than approximated by writing the attribute's value into the client -- which would be a write
    this project has no scope for and the client would not necessarily honour.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Attribute.au3: `Attribute_IncreaseAttribute` sends "
        "`HEADER_ATTRIBUTE_INCREASE` once per point of `$a_i_Amount` (its loop is why the amount is an "
        "argument rather than one packet with a count). This project has no member that raises an "
        "attribute: the client's own increase function is not resolved anywhere in `py4gw/` and no "
        "`offsets/` entry or GwAu3 lead covers it. Answering True would report points that were never "
        f"spent. Attribute ids are GwAu3's own; the value cap it guards is {_MAX_ATTRIBUTE}."
    )


def Attribute_DecreaseAttribute(attribute_id: Any, amount: Any = 1, hero_number: Any = 0) -> bool:
    """**REFUSED: no route yet.** As ``Attribute_IncreaseAttribute``, in the other direction."""

    raise NotImplementedError(
        "GwAu3_Cmd_Attribute.au3: `Attribute_DecreaseAttribute` sends "
        "`HEADER_ATTRIBUTE_DECREASE` once per point. Refused for the same reason as "
        "`Attribute_IncreaseAttribute`: this project has no member that changes an attribute, and the "
        "client's own function is not resolved in `py4gw/` or in `offsets/`."
    )


def Attribute_CalculateAttributeSpread(*args: Any, **kwargs: Any) -> Any:
    """**REFUSED: its contract is a `ByRef` array, which cannot cross the bridge.**

    ``GwAu3_Cmd_Attribute.au3`` declares ``Func Attribute_CalculateAttributeSpread(ByRef
    $a_ai2_AttributeArray, $a_i_AttributePoints)`` and **writes its result back into the caller's
    array**. The bridge marshals values into JSON: the worker receives a copy, so anything it wrote
    would be written to the copy and the caller's array would be untouched -- the function would appear
    to succeed and change nothing. It also computes no client state, so there is nothing to route. A
    faithful version belongs in AutoIt, where `ByRef` means something, and that is the work.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Attribute.au3: `Attribute_CalculateAttributeSpread(ByRef $a_ai2_AttributeArray, "
        "$a_i_AttributePoints)` writes its result into the caller's own array. The bridge marshals "
        "values into JSON, so a worker would receive a copy and its writes would be discarded -- the "
        "call would report success and change nothing, which is the worst shape a wrong answer can "
        "take. It touches no client state, so a faithful version belongs in AutoIt beside `Log_*`, "
        "where `ByRef` exists."
    )


def Attribute_LoadAttributes(*args: Any, **kwargs: Any) -> Any:
    """**REFUSED: same `ByRef` contract as the spread, and the same reason.**

    ``GwAu3_Cmd_Attribute.au3`` declares ``Func Attribute_LoadAttributes($a_ai2_AttributesArray,
    $a_i_HeroNumber = 0)`` and hands the caller's array to ``Attribute_CalculateAttributeSpread``
    **`ByRef`** before sending one ``HEADER_ATTRIBUTE_LOAD`` packet. The array cannot cross the bridge
    in a form whose changes survive, so the load cannot be reproduced faithfully from here.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Attribute.au3: `Attribute_LoadAttributes($a_ai2_AttributesArray, $a_i_HeroNumber = "
        "0)` passes the caller's array to `Attribute_CalculateAttributeSpread` ByRef and then sends "
        "`HEADER_ATTRIBUTE_LOAD`. Its `ByRef` contract cannot survive the bridge (see "
        "`Attribute_CalculateAttributeSpread`), so it refuses rather than load a spread the caller "
        "cannot see."
    )
