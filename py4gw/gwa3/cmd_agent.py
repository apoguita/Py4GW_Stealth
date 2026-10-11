"""GwAu3's ``Agent_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Why this module is hand-written while the readers are generated.** A reader is one ``Switch`` over
field names, which is transcription and belongs in a generator. An action is control flow -- a guard, a
loop, a choice between two mechanisms -- and its effects are real, so each function here is written out
against GwAu3's own body with its GwAu3 lines cited.

**The mechanism, and why it differs.** GwAu3 reaches these effects by **forging packets**:
``Core_SendPacket(0xC, $GC_I_HEADER_ACTION_ATTACK, $id, $call)`` and its neighbours build a message and
hand it to the client's sender. This project does not forge packets. Where GwAu3 sends a packet, this
module **calls the client's own function on the game thread** -- the same effect reached the way the
client reaches it, which is the route ``docs/GWA3_ROUTE_MAP.md`` records for each of these rows. Where
the effect *is* a control action rather than a function call -- ``Agent_CancelAction``, whose packet
carries ``HEADER_ACTION_CANCEL`` -- the route is the client's own control action, pressed the way
Reforged's own ``Keybinds`` press it (``py4gw/gwa3/core.py``'s ``Core_ControlAction`` states it).

Two consequences a caller should know:

* **A packet function in GwAu3 returns ``0`` always**, because ``Core_SendPacket`` has no ``Return``
  and AutoIt answers a valueless return as ``0``. These functions return ``True`` when the call was
  made, because that is what the project's own members answer and a caller cannot act on a constant. The
  divergence is recorded on each function rather than hidden.
* **``Agent_MakeAgentArray`` is refused.** GwAu3's version enqueues a request that makes the *client*
  build a snapshot array; this project reads the client's array directly and has no such request, so
  there is nothing to route it to.

**Allegiance, and one value that does not line up.** GwAu3's ``$GC_I_ALLEGIANCE_ANIMAL`` is ``2``, which
is this project's ``Allegiance.Neutral``; this project's ``Allegiance.SpiritPet`` is ``4`` where GwAu3's
``$GC_I_ALLEGIANCE_SPIRIT`` is also ``4``. So ``Agent_TargetNearestAnimal`` filters on ``Neutral``, and
that is the same byte GwAu3 tests.
"""

from __future__ import annotations

from typing import Any

from ..agent_array import AgentArray
from ..enums_src.game_data_enums import Allegiance
from ..player import Player
from . import constants as _constants
from .core import Core_ControlAction
from .data_agent import (
    Agent_ConvertID,
    Agent_GetAgentInfo,
    Agent_GetDistance,
    Agent_GetMyID,
)

__all__ = [
    "Agent_Attack",
    "Agent_CallTarget",
    "Agent_CancelAction",
    "Agent_ChangeTarget",
    "Agent_ClearTarget",
    "Agent_GoNPC",
    "Agent_GoPlayer",
    "Agent_GoSignpost",
    "Agent_MakeAgentArray",
    "Agent_TargetNearestAlly",
    "Agent_TargetNearestAnimal",
    "Agent_TargetNearestEnemy",
    "Agent_TargetSelf",
]

# GwAu3's own default for the nearest-target searches (`GwAu3_Cmd_Agent.au3:35`).
_DEFAULT_MAX_DISTANCE = 1300


def Agent_ChangeTarget(agent_id: Any) -> bool:
    """Change the target (``GwAu3_Cmd_Agent.au3:3-20``).

    GwAu3's guard is kept: **a zero id is allowed on purpose** -- its own comment records that zero is
    how the native clears the selection, and that is what ``Agent_ClearTarget`` sends -- and only a
    negative id is refused. The id goes through ``Agent_ConvertID`` first, so ``-2`` is the controlled
    character and ``-1`` the current target.

    **The mechanism differs and the route is recorded.** GwAu3 enqueues a command record its injected
    stub turns into a call on the game thread. This calls ``Player.ChangeTarget``
    (``py4gw/player.py:1074``), which drives ``agent.change_target_func`` on the game thread --
    the same function GwAu3's stub calls (``GwAu3_Core_Assembler.au3:2464``), reached directly.

    **The return differs.** GwAu3 answers ``True`` whenever the id passed its guard, because its
    ``Core_Enqueue`` reports nothing about what the client did. This answers ``True`` on the same
    condition, which is the same information.
    """

    resolved = Agent_ConvertID(agent_id)
    if resolved < 0:
        return False
    Player.ChangeTarget(resolved)
    return True


def Agent_ClearTarget() -> bool:
    """Clear the target (``GwAu3_Cmd_Agent.au3:155-157``).

    GwAu3's own implementation is ``Agent_ChangeTarget(0)`` -- and its comment on that function records
    that zero is how the native clears the selection. So this is the same call with the same zero.
    """

    return Agent_ChangeTarget(0)


def Agent_TargetSelf() -> bool:
    """Target the controlled character (``GwAu3_Cmd_Agent.au3:159-162``)."""

    return Agent_ChangeTarget(Agent_GetMyID())


def Agent_CallTarget(target: Any) -> bool:
    """Call a target to the party (``GwAu3_Cmd_Agent.au3:185-187``).

    **The mechanism differs, and the two calls are the same call.** GwAu3 forges
    ``Core_SendPacket(0xC, $GC_I_HEADER_CALL_TARGET, 0xA, $id)`` -- header ``0x23``, then ``0xA``, then
    the id. ``Player.CallTarget`` (``py4gw/player.py:1096``) branches on the agent's allegiance: an
    enemy goes through ``agent.call_target_func`` with ``CallTargetType.ATTACKING_OR_TARGETTING``, which
    is ``0xA`` -- **the same constant GwAu3 hardcodes, for the same case** -- and anything else through
    ``agent.do_world_action_func`` with the call flag set.

    So this is not a substitute for GwAu3's packet; it is the native path that packet stands for, and
    the project's own port records that its runtime's handler for `kSendCallTarget` is what reaches
    `call_target_func` (``player.py:1105-1112``).

    **The return differs.** GwAu3 answers ``0`` on every path, because ``Core_SendPacket`` has no
    ``Return``. This answers ``True`` when the call was made.
    """

    Player.CallTarget(Agent_ConvertID(target))
    return True


def Agent_Attack(target: Any, call_target: bool = False) -> bool:
    """Attack an agent (``GwAu3_Cmd_Agent.au3:180-182``).

    GwAu3 forges ``Core_SendPacket(0xC, $GC_I_HEADER_ACTION_ATTACK, $id, $call)``. This calls
    ``Player.Interact(agent_id, call_target)`` (``py4gw/player.py:1140``), which drives
    ``agent.do_world_action_func`` -- the same world action the client issues -- and which, when
    ``call_target`` is set, first calls ``Player.CallTarget`` exactly as GwAu3's ``$a_b_CallTarget``
    argument is meant to.

    **The return differs.** GwAu3 answers ``0`` on every path. This answers ``True`` when the call was
    made.
    """

    Player.Interact(Agent_ConvertID(target), call_target)
    return True


def Agent_GoNPC(agent: Any) -> bool:
    """Talk to an NPC (``GwAu3_Cmd_Agent.au3:169-172``).

    GwAu3 forges ``Core_SendPacket(0xC, $GC_I_HEADER_INTERACT_LIVING, $id)``. This calls
    ``Player.Interact`` -- the client's own ``agent.do_world_action_func`` with
    ``WorldActionId.INTERACT_LIVING``, which is the action the packet names. The route is the same one
    ``Agent_Attack`` uses because the client routes both through the same world action.
    """

    Player.Interact(Agent_ConvertID(agent))
    return True


def Agent_GoPlayer(agent: Any) -> bool:
    """Run to or follow a player (``GwAu3_Cmd_Agent.au3:165-167``).

    GwAu3 forges ``Core_SendPacket(0x8, $GC_I_HEADER_INTERACT_PLAYER, $id)`` -- header ``0x33``. This
    calls ``Player.Interact``: the client's ``agent.do_world_action_func`` is the world action that
    header stands for, and it is what the project's own port uses for interaction.

    **Recorded as a route and not asserted as identical.** The header GwAu3 sends and the action id the
    client uses are not the same number, so this row is a correspondence: both make the character
    approach and interact with the agent. It has not been compared live.
    """

    Player.Interact(Agent_ConvertID(agent))
    return True


def Agent_GoSignpost(agent: Any) -> bool:
    """Run to a signpost (``GwAu3_Cmd_Agent.au3:174-177``).

    GwAu3 forges ``Core_SendPacket(0xC, $GC_I_HEADER_GADGET_INTERACT, $id, 0)``. This calls
    ``Player.Interact``, the client's own interaction action. Same correspondence as ``Agent_GoPlayer``:
    recorded, not compared live.
    """

    Player.Interact(Agent_ConvertID(agent))
    return True


def Agent_CancelAction() -> bool:
    """Cancel the current action (``GwAu3_Cmd_Agent.au3:189-192``).

    GwAu3 forges ``Core_SendPacket(0x4, $GC_I_HEADER_ACTION_CANCEL)`` -- header ``0x28``, no parameters.

    **The route is the control action Reforged presses for this effect.** ``Keybinds.CancelAction()`` →
    ``Keybinds.PressKeybind(ControlAction_CancelAction, 75)``
    (``routines_src/yield_src/keybinds.py:160-161``), held down and released through
    ``UIManager.Keydown``/``Keyup`` (``routines_src/behaviourtrees_src/keybinds.py:101,119``) -- the client's
    own cancel-action control code, ``$GC_I_CONTROL_ACTION_CANCEL_ACTION`` (``0xAF``), which this port's
    enum carries too (``py4gw/enums_src/ui_enums.py``, ``ControlAction_CancelAction``). So this member
    presses that code through the layer's own control-action member, `py4gw/gwa3/core.py`'s
    ``Core_ControlAction`` -- **the source's own statement for its two mid-cast cancels**
    (``UtilityAI_Core.au3:106``, ``:233``), which this layer now performs rather than refusing.

    GwAu3's return shape is kept as this module keeps it: ``True`` once the press is made, where GwAu3
    answers ``0`` because ``Core_SendPacket`` has no ``Return`` (the divergence this module's header
    records).
    """

    Core_ControlAction(_constants.GC_I_CONTROL_ACTION_CANCEL_ACTION)
    return True


def Agent_MakeAgentArray(agent_type: int = 0) -> bool:
    """**Refused.** GwAu3's call asks the client to build an array; this project reads one.

    ``GwAu3_Cmd_Agent.au3:22-33`` enqueues ``$g_p_MakeAgentArray``, whose stub is a request that makes
    the **client** build a snapshot of its agent array, optionally filtered by type. This project's
    ``AgentArray`` reads the client's own array on demand and traverses it, so there is no request to
    route: the effect GwAu3 asks for is not an effect this project has a mechanism for. A caller who
    wants the array asks ``Agent_GetAgentArray``, which is the reader.

    Refused rather than returning ``True`` for having done nothing, because a caller that believed the
    snapshot had been made would then read a stale one.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Agent.au3:22-33 enqueues $g_p_MakeAgentArray, a request that makes the client build "
        "an agent-array snapshot. This project reads the client's array on demand "
        "(py4gw/agent_array.py:43) and has no such request to route to, so there is no mechanism to "
        "reproduce -- call Agent_GetAgentArray for the array itself."
    )


def _target_nearest(allegiance: int, max_distance: float, exclude_self: bool) -> int:
    """GwAu3's nearest-target search, shared by the three variants that differ only in allegiance.

    GwAu3 writes the loop out three times, once per variant (``GwAu3_Cmd_Agent.au3:35-153``), and each
    copy is the same walk with a different ``$GC_I_ALLEGIANCE_*`` comparison. The three public
    functions below keep GwAu3's own bodies and defaults; this helper is the shared walk they call,
    written out here rather than generated because it is control flow rather than a field lookup.

    GwAu3's own steps, in order:

    1. iterate ``1`` to ``Agent_GetMaxAgents() - 1`` -- its comment records that the bound is
       **exclusive**, because the manager refuses an id at or above it (``GwAu3_Cmd_Agent.au3:41-42``);
    2. skip a slot whose pointer is null;
    3. skip a dead agent;
    4. skip an allegiance that is not the one asked for;
    5. skip the controlled character when ``exclude_self``;
    6. take the shortest distance and remember the id.

    **This walks the project's id list rather than GwAu3's slot range.** GwAu3's bound is the array's
    *capacity*, which this project does not expose (``Agent_GetMaxAgents`` returns the number of ids the
    array holds, and its own docstring says so). The destinations are the same agents, and the result is
    the nearest live agent of that allegiance -- but a caller relying on the search visiting empty slots
    would see a difference. Recorded rather than hidden.
    """

    my_id = Agent_GetMyID()
    best_id = 0
    best_distance = max_distance

    for candidate in AgentArray.GetAgentArray():
        if exclude_self and candidate == my_id:
            continue
        if Agent_GetAgentInfo(candidate, "IsDead"):
            continue
        if Agent_GetAgentInfo(candidate, "Allegiance") != allegiance:
            continue

        distance = Agent_GetDistance(candidate, my_id)
        if distance < best_distance:
            best_distance = distance
            best_id = candidate

    if best_id > 0:
        Agent_ChangeTarget(best_id)
    return best_id


def Agent_TargetNearestEnemy(max_distance: float = _DEFAULT_MAX_DISTANCE) -> int:
    """Target the nearest enemy (``GwAu3_Cmd_Agent.au3:35-71``).

    GwAu3's default range is ``1300`` and it has **no** ``exclude_self`` parameter -- an enemy is never
    the controlled character, so its loop does not test for it.
    """

    return _target_nearest(int(Allegiance.Enemy), max_distance, exclude_self=False)


def Agent_TargetNearestAlly(max_distance: float = _DEFAULT_MAX_DISTANCE, exclude_self: bool = True) -> int:
    """Target the nearest ally (``GwAu3_Cmd_Agent.au3:73-112``).

    GwAu3's default is ``exclude_self = True``, and its loop honours it.
    """

    return _target_nearest(int(Allegiance.Ally), max_distance, exclude_self)


def Agent_TargetNearestAnimal(max_distance: float = _DEFAULT_MAX_DISTANCE, exclude_self: bool = True) -> int:
    """Target the nearest animal (``GwAu3_Cmd_Agent.au3:114-153``).

    GwAu3 compares against ``$GC_I_ALLEGIANCE_ANIMAL``, which is ``0x2``. This project's value for that
    byte is ``Allegiance.Neutral`` -- the same byte, a different name -- so ``Neutral`` is what is
    tested here. ``Allegiance.SpiritPet`` is ``4``, which is GwAu3's *``SPIRIT``*, not its ``ANIMAL``.
    """

    return _target_nearest(int(Allegiance.Neutral), max_distance, exclude_self)
