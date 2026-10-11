"""GwAu3's ``Party_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**GwAu3 reaches every one of these by forging a packet** -- ``Core_SendPacket(0x8,
$GC_I_HEADER_HERO_ADD, $a_i_HeroId)`` and its neighbours (``GwAu3_Cmd_Party.au3``) -- and five of them
by writing a struct into the client's own queue through its injected assembler stub
(``Core_Enqueue``). Neither is available here: this module calls the client's own function on the game
thread instead, which is the route ``docs/GWA3_ROUTE_MAP.md`` records for each row.

**A packet function in GwAu3 returns ``0`` always**, because ``Core_SendPacket`` has no ``Return`` and
AutoIt answers a valueless return as ``0``. These functions answer ``True`` when the call was made --
the project's own members answer that way and a caller cannot act on a constant. The divergence is
stated on each function rather than hidden.

**A hero number is not a hero id, and GwAu3's own packet has an agent id in it.** ``Party_CommandHero``
and ``Party_CancelHero`` take a hero's *party position* and GwAu3 resolves it through
``Party_GetMyPartyHeroInfo($a_i_HeroNumber, "AgentID")`` before putting it in the packet
(``GwAu3_Cmd_Party.au3:45-47``, ``:34-37``). The route here resolves the same way, to the same agent
id, because that is what the effect needs -- and ``Party_CancelHero`` deliberately does **not** call
``Heroes.UnflagHero``, whose argument is a *hero id* resolved through a different function
(``py4gw/party.py:1633-1643``). Same numbers, different meanings, and nothing in the type says so.
"""

from __future__ import annotations

from typing import Any

from ..party import Party
from ..skillbar import SkillBar

__all__ = [
    "Party_AcceptInvitation",
    "Party_AddHero",
    "Party_AddNpc",
    "Party_AddPlayer",
    "Party_CancelAll",
    "Party_CancelHero",
    "Party_CommandAll",
    "Party_CommandHero",
    "Party_DisableHeroSkill",
    "Party_EnableHeroSkill",
    "Party_GetIsHeroSkillDisabled",
    "Party_KickAllHeroes",
    "Party_KickHero",
    "Party_KickInvitedPlayer",
    "Party_KickNpc",
    "Party_KickPlayer",
    "Party_LeaveGroup",
    "Party_LockHeroTarget",
    "Party_RejectInvitation",
    "Party_SetHeroAggression",
    "Party_Tick",
    "Party_ToggleHeroSkillState",
]

#: The coordinates GwAu3 puts in a flag packet to mean "no position" -- ``0x7F800000`` is
#: ``HUGE_VALF`` as GwAu3's own literal, and this project spells the same value ``HUGE_VALF``
#: (``py4gw/party.py:1643``, ``:1652``). Kept as the source's own number so the two are visibly the
#: same float.
_HUGE_VALF = 0x7F800000


def _hero_agent_id(hero_number: Any) -> int:
    """GwAu3's ``Party_GetMyPartyHeroInfo($a_i_HeroNumber, "AgentID")``, which is a party position.

    Position ``0`` is the controlled character and ``1..n`` are the heroes, which is what the ported
    member documents (``py4gw/party.py:1426-1441``) and what GwAu3's own party array holds.
    """

    return int(Party.Heroes.GetHeroAgentIDByPartyPosition(int(hero_number)))


def Party_AddHero(hero_id: Any) -> bool:
    """Add a hero to the party (``GwAu3_Cmd_Party.au3:4-6``).

    GwAu3 forges ``HEADER_HERO_ADD``; this calls the client's own add. The argument means the same
    thing in both: a **hero id**, not an agent id.
    """

    Party.Heroes.AddHero(int(hero_id))
    return True


def Party_KickHero(hero_id: Any) -> bool:
    """Kick a hero from the party (``GwAu3_Cmd_Party.au3:9-11``)."""

    Party.Heroes.KickHero(int(hero_id))
    return True


def Party_KickAllHeroes() -> bool:
    """Kick every hero (``GwAu3_Cmd_Party.au3:14-16``).

    GwAu3's packet carries its own ``0x28`` in the id slot -- its shorthand for "all heroes" -- and
    the ported member is that command with no id at all.
    """

    Party.Heroes.KickAllHeroes()
    return True


def Party_AddNpc(npc_id: Any) -> bool:
    """Add a henchman (``GwAu3_Cmd_Party.au3:19-21``).

    The name says NPC and the argument is a **henchman id**; the ported member is
    ``Henchmen.AddHenchman``, which is the same client command GwAu3's ``HEADER_PARTY_INVITE_NPC``
    packet reaches.
    """

    Party.Henchmen.AddHenchman(int(npc_id))
    return True


def Party_KickNpc(npc_id: Any) -> bool:
    """Kick a henchman (``GwAu3_Cmd_Party.au3:24-26``)."""

    Party.Henchmen.KickHenchman(int(npc_id))
    return True


def Party_Tick(ticked: Any = True) -> bool:
    """Set the party's tick state (``GwAu3_Cmd_Party.au3:29-31``).

    GwAu3 sends ``HEADER_PARTY_TICK`` with the boolean; the ported member takes the state itself.
    ``Party.ToggleTicked`` exists as well and is **not** used: GwAu3's argument is the value wanted,
    not a flip.
    """

    Party.SetTicked(bool(ticked))
    return True


def Party_CancelHero(hero_number: Any) -> bool:
    """Clear a hero's position flag (``GwAu3_Cmd_Party.au3:34-37``).

    GwAu3's packet is ``(HEADER_HERO_FLAG_SINGLE, AgentID, 0x7F800000, 0x7F800000, 0)``: the hero's
    **agent id** and two infinities. This calls ``Heroes.FlagHero`` with the agent id and the same two
    infinities, which is the same request through the client's own function.

    ``Heroes.UnflagHero`` is deliberately not the route, even though its name reads like it: its
    argument goes through ``party::unflag_hero(hero_index)`` and is therefore a **hero id**
    (``py4gw/party.py:1633-1643``). An agent id passed there selects a different hero or none.
    """

    Party.Heroes.FlagHero(_hero_agent_id(hero_number), float(_HUGE_VALF), float(_HUGE_VALF))
    return True


def Party_CancelAll() -> bool:
    """Clear every hero's position flag (``GwAu3_Cmd_Party.au3:40-42``)."""

    Party.Heroes.UnflagAllHeroes()
    return True


def Party_CommandHero(hero_number: Any, x: Any, y: Any) -> bool:
    """Place a hero's position flag (``GwAu3_Cmd_Party.au3:45-47``).

    GwAu3 wraps the coordinates in ``Utils_FloatToInt`` because its packet carries the float's bits;
    the ported member takes the floats themselves, so the conversion is the client's own instead of
    this layer's. The hero's party position resolves to an agent id exactly as GwAu3 resolves it.
    """

    Party.Heroes.FlagHero(_hero_agent_id(hero_number), float(x), float(y))
    return True


def Party_CommandAll(x: Any, y: Any) -> bool:
    """Place the whole party's position flag (``GwAu3_Cmd_Party.au3:50-52``)."""

    Party.Heroes.FlagAllHeroes(float(x), float(y))
    return True


def Party_SetHeroAggression(hero_number: Any, aggression: Any) -> bool:
    """Set a hero's aggression (``GwAu3_Cmd_Party.au3:60-62``).

    GwAu3's comment is the contract: ``0=Fight, 1=Guard, 2=Avoid``. Those are the values the ported
    member takes as ``behavior``, so the number passes straight through.
    """

    Party.Heroes.SetHeroBehavior(_hero_agent_id(hero_number), int(aggression))
    return True


def Party_EnableHeroSkill(hero_number: Any, skill_slot: Any) -> None:
    """Enable a skill on a hero's bar (``GwAu3_Cmd_Party.au3:75-77``).

    **GwAu3's own version has no ``Return`` at all**, so it answers AutoIt's valueless default; the
    same is true here. Its body is ``If Party_GetIsHeroSkillDisabled(...) Then
    Party_ToggleHeroSkillState(...)``, and the ported member it routes to already makes that call
    conditional -- ``set_hero_skill_ai_enabled`` only reaches the client when the state differs
    (``py4gw/party.py:417-419``) -- so the guard is the same guard, one level down.
    """

    Party.Heroes.SetSkillAIEnabled(_hero_agent_id(hero_number), int(skill_slot), True)


def Party_DisableHeroSkill(hero_number: Any, skill_slot: Any) -> bool:
    """Disable a skill on a hero's bar (``GwAu3_Cmd_Party.au3:80-83``).

    **GwAu3 returns ``True`` unconditionally here**, and the same is done: the guard decides whether
    the client is called, not what is answered (``GwAu3_Cmd_Party.au3:81-82``). A caller that tests
    the return is testing "the function ran", which is what it means in GwAu3 too.
    """

    Party.Heroes.SetSkillAIEnabled(_hero_agent_id(hero_number), int(skill_slot), False)
    return True


def Party_LeaveGroup(kick_heroes: Any = True) -> bool:
    """Leave the party (``GwAu3_Cmd_Party.au3:86-89``).

    **The order is GwAu3's and it is load-bearing:** its body kicks every hero *first* and then sends
    the leave packet. The ported members are called in that order.
    """

    if kick_heroes:
        Party.Heroes.KickAllHeroes()
    Party.LeaveParty()
    return True


def Party_AcceptInvitation(party_id: Any) -> None:
    """Accept a party invitation (``GwAu3_Cmd_Party.au3:116-119``).

    GwAu3 fills a struct and hands it to its injected stub, which drives the Party Formation window;
    the ported member is the client's own answer to the same request. GwAu3's body has no ``Return``,
    so this answers nothing.
    """

    Party.RespondToPartyRequest(int(party_id), True)


def Party_RejectInvitation(party_id: Any) -> None:
    """Reject a party invitation (``GwAu3_Cmd_Party.au3:110-113``). As ``Party_AcceptInvitation``."""

    Party.RespondToPartyRequest(int(party_id), False)


def Party_LockHeroTarget(hero_number: Any, agent_id: Any = 0) -> bool:
    """**REFUSED: no route yet.** GwAu3 forges ``HEADER_HERO_LOCK_TARGET``.

    ``GwAu3_Cmd_Party.au3:55-57`` sends ``(HEADER_HERO_LOCK_TARGET, AgentID, $a_i_AgentID)`` with its
    own comment recording that a target of ``0`` cancels the lock. **This project has no member that
    locks a hero onto a target**: ``py4gw/party.py`` carries ``LOCK_PET_TARGET_FUNC`` -- the *pet*
    form, ``party.lock_pet_target_func`` (``py4gw/party.py:94``) -- and nothing for a hero. The work is
    a hero-lock route, and it is recorded in ``docs/GWA3_ROUTE_MAP.md``.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Party.au3:55-57 forges `HEADER_HERO_LOCK_TARGET` with the hero's agent id and the "
        "target (0 cancels). This project has no member that locks a hero onto a target: "
        "`py4gw/party.py:94` carries `LOCK_PET_TARGET_FUNC`, which is the pet form, and the party "
        "module has no hero equivalent. Answering `True` here would report an action that never "
        "reached the client, so it refuses instead."
    )


def Party_GetIsHeroSkillDisabled(hero_number: Any, skill_slot: Any) -> bool:
    """**REFUSED: the read has no member yet.** GwAu3 reads the skillbar record's disabled bit.

    ``GwAu3_Cmd_Party.au3:70-72`` answers ``BitAND(2 ^ ($a_i_SkillSlot - 1),
    Skill_GetSkillbarInfo($a_i_SkillSlot, "Disabled", $a_i_HeroNumber)) > 0``. This project holds the
    same word -- ``set_hero_skill_ai_enabled`` reads it as
    ``int(hero_skillbar.disabled) & (1 << zero_based_slot)`` (``py4gw/party.py:417``) -- but only
    inside a private helper, and the public `SkillBar.GetHeroSkillbar` hands back `SkillbarSkill`
    objects that carry no ``disabled`` field (``py4gw/skillbar.py:747-760``). The work is a member
    that exposes a hero slot's disabled bit, and it is recorded rather than worked around: reaching
    into the private helper from this layer would put client knowledge in the wrong place.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Party.au3:70-72 reads `Skill_GetSkillbarInfo($slot, \"Disabled\", $heroNumber)`. "
        "This project has the same word -- `py4gw/party.py:417` reads it as "
        "`int(hero_skillbar.disabled) & (1 << zero_based_slot)` -- but only inside the private "
        "helper behind `Heroes.SetSkillAIEnabled`, and `SkillBar.GetHeroSkillbar` returns slots that "
        "carry no disabled field (`py4gw/skillbar.py:747-760`). The work is a public member for that "
        "read; this refuses rather than answer a bit it cannot name."
    )


def Party_ToggleHeroSkillState(hero_number: Any, skill_slot: Any) -> bool:
    """**REFUSED: a toggle needs the state it toggles, and that read is refused above.**

    ``GwAu3_Cmd_Party.au3:65-67`` forges ``HEADER_HERO_SKILL_TOGGLE``, which the *client* flips. The
    ported member wants the state it should end in, so the toggle has to read the current one first --
    and this module's read of it, ``Party_GetIsHeroSkillDisabled``, has no route. Answering by
    guessing a state would silently enable where a script asked to disable.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Party.au3:65-67 forges `HEADER_HERO_SKILL_TOGGLE`, which the client flips. "
        "`Heroes.SetSkillAIEnabled` (py4gw/party.py:1595-1609) takes the state to end in, not a flip, "
        "so a faithful toggle needs the current bit -- and `Party_GetIsHeroSkillDisabled`, which reads "
        "it, is refused in this module for want of a public member (the read is py4gw/party.py:417). "
        "Guessing a state would turn a disable into an enable. `Party_EnableHeroSkill` and "
        "`Party_DisableHeroSkill` are routed and take the state explicitly."
    )


def Party_AddPlayer(player_number: Any) -> None:
    """**REFUSED: GwAu3 writes into the client's own command queue.**

    ``GwAu3_Cmd_Party.au3:92-95`` sets a field in its own struct and calls ``Core_Enqueue``, whose
    body is a ``WriteProcessMemory`` into the client's queue at
    ``256 * $g_i_QueueCounter + $g_p_QueueBase`` (``GwAu3_Core.au3:559-566``). That queue is the
    channel GwAu3's forged messages travel on and this project does not write into it. The client's
    own Party Formation button is the safe route, and its callback address is already resolved here --
    ``PARTY_WINDOW_BUTTON_CALLBACK`` (``py4gw/party.py:76``) -- which is the lead the work starts
    from.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Party.au3:92-95 fills `$g_d_AddPlayer` and calls `Core_Enqueue`, which writes into "
        "the client's command queue with `WriteProcessMemory` (`GwAu3_Core.au3:559-566`). This project "
        "does not write into that queue. The client's own Party Formation button is the route to "
        "record, and `PARTY_WINDOW_BUTTON_CALLBACK` (`py4gw/party.py:76`) is the callback it would "
        "send."
    )


def Party_KickPlayer(player_number: Any) -> None:
    """**REFUSED: GwAu3 writes into the client's own command queue.** As ``Party_AddPlayer``."""

    raise NotImplementedError(
        "GwAu3_Cmd_Party.au3:98-101 fills `$g_d_KickPlayer` and calls `Core_Enqueue` -- a write into "
        "the client's queue. Refused for the same reason as `Party_AddPlayer`, with the same lead: "
        "`PARTY_WINDOW_BUTTON_CALLBACK` (`py4gw/party.py:76`)."
    )


def Party_KickInvitedPlayer(party_id: Any) -> None:
    """**REFUSED: GwAu3 writes into the client's own command queue.** As ``Party_AddPlayer``."""

    raise NotImplementedError(
        "GwAu3_Cmd_Party.au3:104-107 fills `$g_d_KickInvitedPlayer` and calls `Core_Enqueue` -- a "
        "write into the client's queue. Refused for the same reason as `Party_AddPlayer`, and the "
        "route to record is the same one: the client's own Party Formation button, whose callback is "
        "`PARTY_WINDOW_BUTTON_CALLBACK` (py4gw/party.py:76). Note that its sibling "
        "`Party_RejectInvitation` IS routed: the client's own `RespondToPartyRequest` "
        "(py4gw/party.py:1252) answers the same invitation request without a queue write."
    )
