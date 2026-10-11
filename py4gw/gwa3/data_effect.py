"""GwAu3's ``GwAu3_Data_Effect.au3``: one skill's effect argument, over two ported readers.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Why this file is written by hand while the other ``data_*`` families are generated.** The family
generator (`tools/generate_gwa3_family.py`) builds one module per source file whose accessor is a
``Switch`` over a **record's offsets** -- every ``Case`` a field at a fixed offset of one structure. This
file's single member switches over three **string** arguments and each ``Case`` is a *computation* that
composes two other ported readers, so the generator's model does not express it: there is no record of
its own to resolve and no offset table to check. The cases below are the source's own three, and the
module is otherwise shaped like its generated siblings.

**One divergence worth naming, and it is the source's own inconsistency, not this layer's.** The two
GwAu3 files that compute a skill's scale disagree about the units of the skill table's ``Scale0``/
``Scale15``/``BonusScale0``/``BonusScale15``: this Data module divides each by ``65536`` (fixed point),
while the plugin's own ``UAI_GetAgentEffectInfo`` reads them raw
(``Cache/UtilityAI_EffectsCache.au3:352-360``). Both are ported **as written** -- the plugin's version in
`py4gw/gwa3/uai_effects.py`, this one here -- and which one the client's table actually holds is a live
question recorded in the spec rather than settled by choosing a side.
"""

from __future__ import annotations

import math
from typing import Any

from .data_party import Party_GetMyPartyHeroInfo
from .data_skill import Skill_GetSkillInfo

__all__ = ["Effect_GetEffectArg"]

#: ``UtilityAI_EffectsCache.au3``'s divisor for the skill table's scale ends, which **this** file applies
#: and the plugin's own accessor does not. Kept as a named constant so the divergence above is visible in
#: the code rather than buried in three expressions.
_SCALE_DIVISOR = 65536


def Effect_GetEffectArg(a_i_SkillID: Any, a_s_Argument: Any = "", a_i_HeroNumber: Any = 0) -> Any:
    """One effect argument of a skill, priced by its caster's attribute level
    (``GwAu3_Data_Effect.au3:3-38``).

    The source's three cases, in its order, and its ``Case Else`` of ``0``:

    * ``"Duration"`` -- ``Round(Duration0 + ((Duration15 - Duration0) / 15) * AttributeLevel)``;
    * ``"Scale"`` -- ``Floor(Scale0 + ((Scale15 - Scale0) / 15) * AttributeLevel)``;
    * ``"BonusScale"`` -- the same over ``BonusScale0``/``BonusScale15``.

    **The attribute level comes from the caster's own effect**, and which caster is the point of the
    second argument: ``$a_i_HeroNumber = 0`` asks for the controlled character
    (``Agent_GetAgentEffectInfo(-2, ...)``, which this layer reads as the player's own agent), and any
    other number resolves that hero's agent id first (``Party_GetMyPartyHeroInfo``). The two skill-table
    ends and the attribute level are the three numbers the interpolation uses, and ``Round`` is Python's
    ``round`` where ``Floor`` is `math.floor` -- AutoIt's two different roundings, kept apart.

    ``Scale`` and ``BonusScale`` divide the skill table's ends by ``65536`` (see the module docstring);
    ``Duration`` does not, because the source does not.
    """

    if a_s_Argument == "Duration":
        duration0 = Skill_GetSkillInfo(a_i_SkillID, "Duration0")
        duration15 = Skill_GetSkillInfo(a_i_SkillID, "Duration15")
        attribute_level = _attribute_level(a_i_SkillID, a_i_HeroNumber)
        return round(duration0 + ((duration15 - duration0) / 15) * attribute_level)

    if a_s_Argument == "Scale":
        scale0 = Skill_GetSkillInfo(a_i_SkillID, "Scale0") / _SCALE_DIVISOR
        scale15 = Skill_GetSkillInfo(a_i_SkillID, "Scale15") / _SCALE_DIVISOR
        attribute_level = _attribute_level(a_i_SkillID, a_i_HeroNumber)
        return math.floor(scale0 + ((scale15 - scale0) / 15) * attribute_level)

    if a_s_Argument == "BonusScale":
        bonus0 = Skill_GetSkillInfo(a_i_SkillID, "BonusScale0") / _SCALE_DIVISOR
        bonus15 = Skill_GetSkillInfo(a_i_SkillID, "BonusScale15") / _SCALE_DIVISOR
        attribute_level = _attribute_level(a_i_SkillID, a_i_HeroNumber)
        return math.floor(bonus0 + ((bonus15 - bonus0) / 15) * attribute_level)

    return 0


def _attribute_level(skill_id: Any, hero_number: Any) -> Any:
    """The caster's attribute level for a skill's effect, from the two arms the source writes.

    ``$a_i_HeroNumber = 0`` is the controlled character, which is the ``-2`` sentinel
    ``Agent_GetAgentEffectInfo`` takes (`py4gw/gwa3/data_agent.py`); anything else resolves the hero's
    agent id through the party accessor first (``GwAu3_Data_Effect.au3:8-12``, ``:18-22``, ``:28-32``).
    """

    from .data_agent import Agent_GetAgentEffectInfo

    if hero_number == 0:
        return Agent_GetAgentEffectInfo(-2, skill_id, "AttributeLevel")
    return Agent_GetAgentEffectInfo(
        Party_GetMyPartyHeroInfo(hero_number, "AgentID"), skill_id, "AttributeLevel"
    )
