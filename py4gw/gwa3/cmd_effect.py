"""GwAu3's ``Effect_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

One function, and it **refuses**. GwAu3's own body is a lookup followed by a packet: it asks
``Agent_GetAgentBondInfo($a_i_AgentID, $a_i_SkillID, $a_i_TargetID, "BondID")`` for a bond's id and
returns without doing anything when that answers ``0``, then forges ``HEADER_BOND_DROP`` with the id.
The lookup is the part this project cannot make, and the reason is on the function -- it is worth
reading, because the obvious-looking substitute is a wrong effect.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Effect_DropBond"]

#: GwAu3's own "no bond matched" answer, from `Agent_GetAgentBondInfo`'s ``BondID`` case: the function
#: returns **without enqueuing anything** when it is zero (``GwAu3_Cmd_Effect.au3``).
_NO_BOND = 0


def Effect_DropBond(skill_id: Any, agent_id: Any = -2, target_id: Any = 0) -> bool:
    """**REFUSED: GwAu3's first step is a lookup this project cannot make.**

    ``GwAu3_Cmd_Effect.au3`` does two things, in this order:

    1. ``Agent_GetAgentBondInfo($a_i_AgentID, $a_i_SkillID, $a_i_TargetID, "BondID")`` -- walk the
       global agent-effects array for the bond whose skill and target match, and take its **bond id**;
    2. return without doing anything when that id is ``0``, otherwise forge ``HEADER_BOND_DROP`` with it.

    **Step one has no route here**, and it is the same gap this layer already records for
    ``Agent_GetAgentInfo``'s ``EffectCount`` and ``BondCount``: the walk needs the connection's
    agent-effects array address, and a materialized record carries no target address
    (``py4gw/gwa3/data_agent.py``).

    **The tempting shortcut is the one this refuses.** ``py4gw.effect.drop_buff(buff_id)`` is the
    client's own drop and takes **one** word -- so ``drop_buff(skill_id)`` would look like a route. It
    is not: GwAu3's argument is a *skill* id and the lookup exists precisely because the **bond id is a
    different number**. Passing the skill id would drop whichever buff the client resolves that word
    to, which is a wrong effect reached by a plausible-looking call, and nothing in the answer would
    say so.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Effect.au3: `Effect_DropBond($a_i_SkillID, $a_i_AgentID = -2, $a_i_TargetID = 0)` "
        "first calls `Agent_GetAgentBondInfo($a_i_AgentID, $a_i_SkillID, $a_i_TargetID, \"BondID\")` and "
        "forges `HEADER_BOND_DROP` with the **bond id** it finds. That lookup walks the global "
        "agent-effects array, which needs the connection's array address -- the same gap recorded for "
        "`Agent_GetAgentInfo`'s `EffectCount` and `BondCount` (`py4gw/gwa3/data_agent.py`). "
        "`py4gw.effect.drop_buff` (`py4gw/effect.py:220-233`) takes a **buff id**, not a skill id, so "
        "passing this function's argument to it would drop a different effect and report success."
    )

