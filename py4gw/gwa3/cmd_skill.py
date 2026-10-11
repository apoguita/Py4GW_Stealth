"""GwAu3's ``Skill_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Four of the eleven are routed and seven refuse**, and the split runs along one line: GwAu3 sends its
skill actions through ``Core_Enqueue`` -- a write into the client's own command queue with a struct it
built -- while its skillbar and merchant actions go through ``Core_SendPacket``, and some of those have
a ported member that does the same thing.

* Routed: ``Skill_UseSkill`` (`SkillBar.UseSkill`), ``Skill_UseHeroSkill`` (`Party.Heroes.UseSkill`),
  ``Skill_BuySkillByID`` (`Player.BuySkill`), ``Skill_UnlockSkillByID``
  (`Player.UnlockBalthazarSkill`).
* Refused: everything that reaches the client through ``Core_Enqueue`` -- ``Skill_CancelHeroSkill`` --
  and everything whose effect has no ported member at all -- ``Skill_SetSkillbarSkill``,
  ``Skill_LoadSkillBar``, ``Skill_UnlockSkillBossByID``, ``Skill_UnlockTomeSkillByID``,
  ``Skill_SkillForQuest``.

**GwAu3's own guards are kept, and so are its log lines' decisions.** ``Skill_UseSkill`` refuses a
slot outside ``1..8`` and a target that resolves to zero, and ``Skill_UseHeroSkill`` additionally
refuses a hero index outside ``1..7`` and one that is not in the party. Those are the source's
conditions and they are reproduced; what a caller *reads* is this layer's, because GwAu3 writes to its
RichEdit control and this layer answers a value through the bridge.
"""

from __future__ import annotations

from typing import Any

from ..party import Party
from ..player import Player
from ..skillbar import SkillBar
from .data_agent import Agent_ConvertID

__all__ = [
    "Skill_BuySkillByID",
    "Skill_CancelHeroSkill",
    "Skill_LoadSkillBar",
    "Skill_SetSkillbarSkill",
    "Skill_SkillForQuest",
    "Skill_UnlockSkillBossByID",
    "Skill_UnlockSkillByID",
    "Skill_UnlockTomeSkillByID",
    "Skill_UseHeroSkill",
    "Skill_UseSkill",
]

#: GwAu3's own bounds, from the guards at the top of each function (``GwAu3_Cmd_Skill.au3:4``,
#: ``:31``, ``:36``, ``:60``, ``:65``). Kept as the source's numbers so the two agree on what is valid.
_FIRST_SLOT = 1
_LAST_SLOT = 8
_FIRST_HERO = 1
_LAST_HERO = 7


def Skill_UseSkill(skill_slot: Any, target_id: Any = -2, call_target: Any = False) -> bool:
    """Use a skill from the controlled character's bar (``GwAu3_Cmd_Skill.au3:3-28``).

    GwAu3's guards, in its own order: a slot outside ``1..8`` answers **False** without reaching the
    client, and a target that ``Agent_ConvertID`` resolves to zero or less answers **False** as well.
    Both are reproduced, and both answer `False` rather than raising because that is what GwAu3's own
    callers branch on.

    GwAu3 builds a struct and hands it to its injected stub; the ported member is the client's own
    skill use. **The slot is one-based in both**: GwAu3 subtracts one only on the way into its struct
    (``:15``), while ``SkillBar.UseSkill`` takes the one-based slot a script uses, and the default
    target ``-2`` is GwAu3's own "the controlled character" sentinel.
    """

    if int(skill_slot) < _FIRST_SLOT or int(skill_slot) > _LAST_SLOT:
        return False

    agent_id = Agent_ConvertID(target_id)
    if agent_id <= 0:
        return False

    SkillBar.UseSkill(int(skill_slot), int(agent_id))
    return True


def Skill_UseHeroSkill(hero_index: Any, skill_slot: Any, target_id: Any = 0) -> bool:
    """Use one of a hero's skills (``GwAu3_Cmd_Skill.au3:30-57``).

    GwAu3's four guards are kept in its own order: a hero index outside ``1..7``, a slot outside
    ``1..8``, a hero that is not in the party (its ``Party_GetMyPartyHeroInfo`` answers ``0``), and --
    unlike ``Skill_UseSkill`` -- **no test on the target**, which is allowed to be ``0`` here because
    the default is. The hero's party position resolves to an agent id the same way GwAu3 resolves it,
    which is what the ported member takes.
    """

    if int(hero_index) < _FIRST_HERO or int(hero_index) > _LAST_HERO:
        return False
    if int(skill_slot) < _FIRST_SLOT or int(skill_slot) > _LAST_SLOT:
        return False

    hero_agent_id = int(Party.Heroes.GetHeroAgentIDByPartyPosition(int(hero_index)))
    if hero_agent_id == 0:
        return False

    target = Agent_ConvertID(target_id)
    Party.Heroes.UseSkill(hero_agent_id, int(skill_slot), int(target))
    return True


def Skill_BuySkillByID(skill_id: Any) -> None:
    """Buy a skill from a skill merchant (``GwAu3_Cmd_Skill.au3:114-116``).

    GwAu3 forges a dialog send with ``'0x0A' & Hex($a_i_SkillID, 6)``; the ported member is the
    client's own purchase, which is the same effect through the same dialog mechanism GwAu3 is
    reaching by hand. **GwAu3's body has no ``Return``**, so it answers AutoIt's valueless default; the
    ported member answers nothing either.
    """

    Player.BuySkill(int(skill_id))


def Skill_UnlockSkillByID(skill_id: Any) -> None:
    """Unlock a skill at the Priest of Balthazar (``GwAu3_Cmd_Skill.au3:119-121``).

    GwAu3 forges a dialog send with ``'0x10' & Hex($a_i_SkillID, 6)``; the ported member is the
    client's own unlock, with the same default ``use_pvp_remap`` GwAu3 leaves alone. GwAu3's body has
    no ``Return``.
    """

    Player.UnlockBalthazarSkill(int(skill_id))


def Skill_CancelHeroSkill(hero_index: Any, skill_slot: Any) -> bool:
    """**REFUSED: GwAu3 writes the cancel into the client's own command queue.**

    ``GwAu3_Cmd_Skill.au3:59-84`` fills ``$g_d_CancelHeroSkill`` with the hero's agent id and the
    zero-based slot and calls ``Core_Enqueue`` -- a ``WriteProcessMemory`` into the client's queue
    (``GwAu3_Core.au3:559-566``). This project does not write into that queue. Its guards and its
    ``True`` return are GwAu3's, and a route would have to keep both: a hero index outside ``1..7``, a
    slot outside ``1..8`` and a hero that is not in the party each answer ``False`` **without reaching
    the client**.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Skill.au3:59-84 fills `$g_d_CancelHeroSkill` and calls `Core_Enqueue`, a "
        "`WriteProcessMemory` into the client's command queue (`GwAu3_Core.au3:559-566`). This project "
        "does not write into that queue, and no member of py4gw/ cancels a hero's skill -- "
        "`py4gw/party.py`'s `Heroes.SetSkillAIEnabled` toggles a slot's AI, which is a different "
        "request. Its guards are "
        f"GwAu3's own (hero {_FIRST_HERO}..{_LAST_HERO}, slot {_FIRST_SLOT}..{_LAST_SLOT}, and a hero "
        "in the party) and its success answer is `True`."
    )


def Skill_SetSkillbarSkill(slot: Any, skill_id: Any, hero_number: Any = 0) -> bool:
    """**REFUSED: no member sets one skillbar slot's skill.**

    ``GwAu3_Cmd_Skill.au3:87-95`` forges ``HEADER_SKILLBAR_SKILL_SET`` with the target's agent id (the
    hero's when ``$a_i_HeroNumber`` is not zero, the controlled character's otherwise), the zero-based
    slot, the skill id and a trailing ``0``. This project reads skillbars and loads whole templates
    (`SkillBar.LoadSkillTemplate`, `SkillBar.LoadHeroSkillTemplate`) but has no member that **sets one
    slot**, so the packet's effect has no route -- and a template load is not a substitute: it replaces
    all eight slots, which is a different action with a different result for the other seven.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Skill.au3:87-95 forges `HEADER_SKILLBAR_SKILL_SET` with the agent id, the zero-based "
        "slot, the skill id and a trailing zero. This project has no member that sets one skillbar "
        "slot: `py4gw/skillbar.py` loads whole templates (`SkillBar.LoadSkillTemplate`, "
        "`SkillBar.LoadHeroSkillTemplate`) and reads slots, and a template load would replace all "
        "eight -- a different action with a different effect on the other seven slots."
    )


def Skill_LoadSkillBar(*args: Any, **kwargs: Any) -> bool:
    """**REFUSED: no member loads eight skill ids as GwAu3's packet does.**

    ``GwAu3_Cmd_Skill.au3:98-106`` forges ``HEADER_SKILLBAR_LOAD`` with the agent id, a count of eight
    and the eight skill ids. This project's loader takes **a template**, not eight ids
    (`SkillBar.LoadSkillTemplate`), and a template has a different meaning: it carries attributes and
    a profession as well, and an id list cannot be turned into one without inventing the rest. The work
    is a member that loads a slot list, and the route map records it.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Skill.au3:98-106 forges `HEADER_SKILLBAR_LOAD` with the agent id, the count `8` and "
        "eight skill ids. This project's loader takes a **template string** "
        "(py4gw/skillbar.py: `SkillBar.LoadSkillTemplate`), which also carries attributes and a "
        "profession; building one from eight ids would invent the parts GwAu3 never had. The work is a "
        "member that loads a slot list, and it is named rather than approximated."
    )


def Skill_UnlockSkillBossByID(skill_id: Any) -> None:
    """**REFUSED: no member performs the boss-skill unlock.**

    ``GwAu3_Cmd_Skill.au3:109-111`` forges ``0x005B`` -- a **bare header with no constant in GwAu3's
    own table** -- with the skill id, after a capture signet has been used on a boss. This project has
    no member for it, and the header number is not even named in GwAu3's constants, so nothing about
    the effect is established here beyond GwAu3's own line. The work is a ported route for the unlock.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Skill.au3:109-111 forges header `0x005B` with the skill id -- a literal, not a "
        "`$GC_I_*` constant, which is why nothing in this layer's constant surface names it. Neither "
        "py4gw/skillbar.py nor py4gw/skill.py has a member for the boss-skill unlock, so there is "
        "nothing to route to. The work is a ported route, and it is named rather than guessed at from a "
        "bare header."
    )


def Skill_UnlockTomeSkillByID(item_id: Any, skill_id: Any) -> None:
    """**REFUSED: no member unlocks a skill from a tome.**

    ``GwAu3_Cmd_Skill.au3:124-126`` forges ``HEADER_TOME_UNLOCK_SKILL`` with the item id and the skill
    id. This project has no member for it: ``py4gw/item.py`` reads items and ``py4gw/skillbar.py``
    loads templates, and neither unlocks a skill from a tome. The work is the client's own route.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Skill.au3:124-126 forges `HEADER_TOME_UNLOCK_SKILL` with the item id and the skill "
        "id. This project has no member that unlocks a skill from a tome -- `py4gw/item.py` reads items "
        "and `py4gw/skillbar.py` loads templates -- so the effect has no route. The work is the "
        "client's own unlock."
    )


def Skill_SkillForQuest(skill_slot: Any) -> None:
    """**REFUSED: no member equips the skill a quest grants.**

    ``GwAu3_Cmd_Skill.au3:130-132`` forges ``HEADER_SKILL_EQUIP`` with the **zero-based** slot -- its
    own comment gives the example, Disarm Trap for Venta Cemetery. This project has no member that
    equips a quest's skill, and no reading of the quest-granted slot either. The work is a ported
    route; note the argument is one-based in GwAu3's signature and zero-based in the packet, which a
    route must keep straight.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Skill.au3:130-132 forges `HEADER_SKILL_EQUIP` with `$a_i_SkillSlot - 1` -- "
        "one-based in its signature, zero-based in the packet. This project's py4gw/quest.py reads the "
        "quest log and py4gw/skillbar.py writes skillbar slots; neither equips the skill a quest "
        "grants. The work is a ported route, and the off-by-one is the part a route must keep straight."
    )
