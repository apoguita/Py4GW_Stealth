"""External port of Reforged's ``Py4GWCoreLib/Agent.py``.

Every member of the Reforged ``Agent`` class is present here with the same name, the same
signature and the same return values, so a script that reads ``Agent.GetLevel(agent_id)`` keeps
working after switching libraries. What differs is *which* members can produce a value.

The Reforged class is a namespace of **148** ``@staticmethod``s over an agent record — the source's
own count, which an earlier pass measured as 147 because ``GetAnimationCode`` is declared
``def GetAnimationCode (agent_id : int)`` (``Agent.py:567-568``), with a space before its
parenthesis. This port keeps that shape and reaches the record through the ported contexts —
``py4gw/context/agent_array.py`` for the agents, ``py4gw/context/world_context.py`` for attributes
and NPC models — resolved the same way every other accessor class resolves the selected client,
through :func:`py4gw.client.require_client`.

Three groups exist, and each member says which one it is in its docstring:

``implemented``
    The value comes from an agent record this project can read. These members return exactly
    what Reforged returns, including its defaults when the record is missing. A member whose body
    calls another member of this class that raises is in this group too: the raise comes from the
    member that owns the missing piece, which is the source's own call graph.

``blocked``
    The member's own body needs something this port does not have: a native binding call
    (``PyAgent.get_agent_enc_name``), a companion class (``Utils``, ``Skill``, ``Effect``,
    ``UIManager``) or a native console (``PySystem.Console``). These raise ``NotImplementedError``
    through :func:`_unported`, naming the file and the lines of what is missing, so the call site
    fails loudly instead of receiving a plausible wrong value. The game-data enums the class reads
    are **not** in this group any more: ``enums_src/GameData_enums.py`` is ported at
    ``py4gw/enums_src/game_data_enums.py``, and the eight members that waited on it take their
    professions, allegiances and weapon types from it.

**The one adaptation that changes behaviour, and it is the source's own cache.** ``Agent.py:40-50``
declares four per-frame caches of agent records (``_agent_cache``, ``_living_cache``,
``_item_cache``, ``_gadget_cache``) and ``enable()`` registers the callback that clears them once
per frame (``Agent.py:52-60``). This port has no frame loop, so there is no frame boundary to key
those caches to and no tick to invalidate them; a verbatim copy would pin a map-scoped
dereferenced record for the life of the process, which is the stale data the port's rules forbid
(``AGENTS.md``, ``PORTING_RULES.md``). So ``GetLivingAgentByID``, ``GetItemAgentByID`` and
``GetGadgetAgentByID`` keep the source's calls, order, short-circuits and returns **without** the
cache lookup and store: the members read when they are called.

Two consequences are visible on the surface, and both are reported rather than papered over:
``_invalidate_property_cache`` and ``enable`` raise, because clearing and registering are exactly
the two halves of the mechanism this port does not have; and the source's module-level
``Agent.enable()`` (``Agent.py:1649``) is not called at import.
"""

from __future__ import annotations

from .client import require_client
from .context.agent_array import (
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    AgentStruct,
)
from .context.world_context import AttributeStruct, NPC_ModelStruct, WorldContextStruct


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise
    is what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"Agent.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


class Agent:
    """The Reforged ``Agent`` namespace class (``Agent.py:13-1646``): 148 static members.

    Every member takes an ``agent_id`` and reads. The class holds the two constants the source
    declares (``Agent.py:14-18``) and nothing else: the four per-frame caches the source declares
    at ``Agent.py:40-43`` are not kept here, for the reason the module docstring gives.
    """

    #: ``Agent.py:14``. Filled in by ``IsMartial``/``IsMelee`` on first use in the source; both
    #: members are blocked here (they need ``Skill.GetID``), so the constant stays at its
    #: declared value.
    ILLUSIONARY_WEAPONRY_ID = 0

    #: ``Agent.py:18``. Agent HP is normalized 0.0-1.0 for most non-party entities; the smallest
    #: expected enemy health pool is used so ~1 HP residual noise still counts as dead across the
    #: common 400-1000 HP range.
    DEAD_HEALTH_EPSILON = 1.0 / 400.0

    @staticmethod
    def _enc_name_bytes_to_wstr(enc_bytes: list[int]) -> str:
        """Convert raw ``GetAgentEncName()`` byte values into a UTF-16LE string (``Agent.py:21-29``).

        Pure arithmetic over the bytes it is handed, so it needs nothing the port does not have.
        """

        if not enc_bytes:
            return ""

        raw = bytes(enc_bytes)
        text = raw[: len(raw) & ~1].decode("utf-16-le", "ignore")
        null_index = text.find("\x00")
        return text[:null_index] if null_index >= 0 else text

    @staticmethod
    def IsValid(agent_id: int) -> bool:
        """Check if the agent is valid (``Agent.py:31-38``)."""

        return Agent.GetAgentByID(agent_id) is not None

    @staticmethod
    def _invalidate_property_cache() -> None:
        """Clear the four per-frame agent caches (``Agent.py:45-50``).

        Blocked: it clears ``_agent_cache``/``_living_cache``/``_item_cache``/``_gadget_cache``,
        which this port does not keep, and the only thing that ever called it is the frame tick
        ``enable()`` registers.
        """

        raise _unported(
            "_invalidate_property_cache",
            "the four per-frame agent caches it clears (Agent.py:40-50), which this port does not "
            "keep: their only invalidation is the once-per-frame callback enable() registers, and "
            "there is no frame loop here (AGENTS.md, PORTING_RULES.md)",
        )

    @staticmethod
    def enable() -> None:
        """Register the per-frame cache invalidation (``Agent.py:52-60``).

        Blocked: it calls ``PyCallback.PyCallback.Register("Agent.InvalidatePropertyCache",
        Phase.PreUpdate, ...)``, a per-frame callback registration, and this project has no frame
        loop to drive it. The source also calls this at module level (``Agent.py:1649``), which
        this port does not reproduce.
        """

        raise _unported(
            "enable",
            "the per-frame callback registration PyCallback.PyCallback.Register(..., "
            "Phase.PreUpdate, ...) (Agent.py:52-60; stubs/PyCallback.pyi:40), which this project "
            "has no frame loop for",
        )

    @staticmethod
    def GetAgentByID(agent_id: int) -> AgentStruct | None:
        """Retrieve an agent by its ID, or ``None`` (``Agent.py:62-81``).

        Adapted at the reader. Reforged returns ``AgentArray.GetAgentByID(agent_id)``
        (``AgentArray.py:221-224``), which asks the native agent-array context
        (``AgentContext.py:1477-1497``) and answers ``None`` for any id no snapshot holds — including
        ``0``. This port reads the same context through ``ConnectedClient.read_agent_by_id``; the
        exceptions it can raise are the port's transport answering where the in-process binding
        answers null (a non-positive id raises ``ValueError`` there, an unreadable or stale record
        raises ``OSError``/``StaleAgentReferenceError``), so they are mapped to the source's ``None``.

        The four lines the source leaves *after* its own ``return`` (``Agent.py:74-81``) are
        unreachable there and are not reproduced; the cache they maintain is the adaptation the
        module docstring describes.
        """

        client = require_client()
        try:
            return client.read_agent_by_id(int(agent_id))
        except (OSError, RuntimeError, ValueError):
            return None

    @staticmethod
    def GetLivingAgentByID(agent_id: int) -> AgentLivingStruct | None:
        """Retrieve a living agent by its ID, or ``None`` (``Agent.py:84-101``).

        The source's calls, order, short-circuits and returns, without the per-frame cache lookup
        and store (``Agent.py:92-93``, ``99-100``) — see the module docstring.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return None
        return agent.GetAsAgentLiving()

    @staticmethod
    def GetItemAgentByID(agent_id: int) -> AgentItemStruct | None:
        """Retrieve an item agent by its ID, or ``None`` (``Agent.py:103-120``).

        Without the per-frame cache (``Agent.py:111-112``, ``118-119``), as above.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return None
        return agent.GetAsAgentItem()

    @staticmethod
    def GetGadgetAgentByID(agent_id: int) -> AgentGadgetStruct | None:
        """Retrieve a gadget agent by its ID, or ``None`` (``Agent.py:122-139``).

        Without the per-frame cache (``Agent.py:130-131``, ``137-138``), as above.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return None
        return agent.GetAsAgentGadget()

    @staticmethod
    def GetNameByID(agent_id: int) -> str:
        """Get the decoded display name of an agent by its ID (``Agent.py:141-147``).

        Blocked on the binding, not on the decode: the source reads the encoded name through
        ``PyAgent.get_agent_enc_name`` (``agent_bindings.cpp:216``, ``stubs/PyAgent.pyi:98``) and
        hands it to ``native_src.internals.string_table.decode``, which this port *has*
        (``py4gw/internals/string_table.py``). No resolver returns that binding
        (``offsets/agent.json`` carries the eight agent names the port does have).
        """

        raise _unported(
            "GetNameByID",
            "PyAgent.get_agent_enc_name (agent_bindings.cpp:216; stubs/PyAgent.pyi:98), the "
            "binding call that returns an agent's encoded name; the string-table decode it feeds "
            "is ported (py4gw/internals/string_table.py)",
        )

    #: ``Agent.py:149``: the source's alias for :meth:`GetNameByID`, declared in the class body
    #: right after it, so both names are the same ``staticmethod``.
    RequestName = GetNameByID

    @staticmethod
    def IsNameReady(agent_id: int) -> bool:
        """Whether the agent's name has decoded yet (``Agent.py:151-153``).

        The body is the source's; the raise comes from :meth:`GetNameByID`, which owns the missing
        binding call.
        """

        return Agent.GetNameByID(agent_id) != ""

    @staticmethod
    def GetEncNameByID(agent_id: int) -> list[int]:
        """Get the encoded name of an agent by its ID (``Agent.py:155-159``).

        Blocked on ``PyAgent.get_agent_enc_name`` (``agent_bindings.cpp:216``), the same binding
        :meth:`GetNameByID` needs.
        """

        raise _unported(
            "GetEncNameByID",
            "PyAgent.get_agent_enc_name (agent_bindings.cpp:216; stubs/PyAgent.pyi:98), the "
            "binding call that returns an agent's encoded name",
        )

    @staticmethod
    def GetEncNameStrByID(agent_id: int, literal: bool = False) -> str:
        """Get an agent's encoded name as a readable debug string (``Agent.py:161-179``).

        Blocked on ``PyAgent.get_agent_enc_name`` (``agent_bindings.cpp:216``). Both helpers the
        body uses are ported — ``Agent._enc_name_bytes_to_wstr`` here and
        ``encoded_wstr_to_str`` in ``py4gw/internals/helpers.py`` — so the binding call is the only
        thing outstanding.
        """

        raise _unported(
            "GetEncNameStrByID",
            "PyAgent.get_agent_enc_name (agent_bindings.cpp:216; stubs/PyAgent.pyi:98), the "
            "binding call that returns an agent's encoded name; the two helpers the body uses are "
            "ported (Agent._enc_name_bytes_to_wstr, py4gw/internals/helpers.py)",
        )

    @staticmethod
    def GetAgentIDByName(name: str) -> int:
        """Retrieve the first agent whose name matches, or ``0`` (``Agent.py:181-198``).

        Adapted twice, and blocked once. The walk is ``AgentArray.GetAgentArray()``
        (``AgentArray.py:15-29``) in the source and the ported context's own snapshot here
        (``ConnectedClient.read_agent_array``); the comparison is ``Agent.GetNameByID``'s, so the
        raise is that member's missing binding call.
        """

        client = require_client()
        try:
            snapshot = client.read_agent_array()
        except (OSError, RuntimeError, ValueError):
            return 0
        if snapshot is None:
            return 0

        for agent_id in [reference.agent_id for reference in snapshot.references]:
            agent_name = Agent.GetNameByID(agent_id)
            if name.lower() in agent_name.lower():
                if Agent.IsValid(agent_id):
                    return agent_id
        return 0

    @staticmethod
    def GetAgentIDByEncString(enc_string: str) -> int:
        """Retrieve the first agent whose encoded name matches, or ``0`` (``Agent.py:200-220``).

        The same two adaptations as :meth:`GetAgentIDByName`; the raise comes from
        ``Agent.GetEncNameStrByID``.
        """

        if not enc_string:
            return 0

        client = require_client()
        try:
            snapshot = client.read_agent_array()
        except (OSError, RuntimeError, ValueError):
            return 0
        if snapshot is None:
            return 0

        for agent_id in [reference.agent_id for reference in snapshot.references]:
            if not Agent.IsValid(agent_id):
                continue
            if Agent.GetEncNameStrByID(agent_id, literal=True) == enc_string:
                return agent_id
        return 0

    @staticmethod
    def GetModelIDByEncString(enc_string: str, log: bool = False) -> int:
        """Retrieve a model id by encoded name, or ``0`` (``Agent.py:222-240``).

        The body is the source's, ``log`` prints included; the raise comes from
        ``Agent.GetAgentIDByEncString``.
        """

        agent_id = Agent.GetAgentIDByEncString(enc_string)
        if log:
            print(f"Debug: GetModelIDByEncString('{enc_string}') found agent_id={agent_id}")
        if agent_id == 0:
            return 0
        model_id = Agent.GetModelID(agent_id)
        if log:
            print(f"Debug: GetModelIDByEncString('{enc_string}') found model_id={model_id}")
        return model_id

    @staticmethod
    def GetAttributes(agent_id: int) -> list[AttributeStruct]:
        """Retrieve an agent's attributes, or ``[]`` (``Agent.py:242-250``).

        Adapted at the context: the source asks ``GWContext.World.GetContext()`` (``Context.py``);
        this port reads the same world context through ``ConnectedClient.read_world_context``,
        whose ``get_attributes_by_agent_id`` is the identical read over the ported
        ``attributes`` array.
        """

        client = require_client()
        try:
            world_ctx: WorldContextStruct | None = client.read_world_context()
        except (OSError, RuntimeError):
            return []
        if world_ctx is None:
            return []

        attributes = world_ctx.get_attributes_by_agent_id(agent_id)
        return attributes

    @staticmethod
    def GetAttributesDict(agent_id: int) -> dict[int, int]:
        """Retrieve an agent's attributes as ``{attribute_id: level}`` (``Agent.py:252-265``)."""

        attributes_raw: list[AttributeStruct] = Agent.GetAttributes(agent_id)
        attributes = {}

        for attr in attributes_raw:
            attr_id = int(attr.attribute_id)
            attr_level = attr.level_base
            if attr_level > 0:
                attributes[attr_id] = attr_level

        return attributes

    @staticmethod
    def GetInstanceFrames(agent_id: int) -> int:
        """Retrieve the instance timer of an agent in frames (``Agent.py:267-278``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0
        return agent.timer

    @staticmethod
    def GetInstanceUptime(agent_id: int) -> int:
        """Retrieve the instance timer of an agent in milliseconds (``Agent.py:280-294``).

        The source's body is four lines — the record, ``UIManager.GetFPSLimit()``, the ``max``
        against 30 that keeps the division safe, and the millisecond conversion. Reforged reaches
        the frame limit through ``UIManager.GetFPSLimit`` (``UIManager.py:283``), which is
        ``PyUIManager.UIManager.get_frame_limit()``, which is native's ``GW::ui::GetFrameLimit``
        (``ui_methods.cpp:1833-1858``) — and that function **is** ported
        (:func:`py4gw.ui.preferences.get_frame_limit`). ``UIManager`` has no ported home yet, so
        this calls the native function the wrapper ends at; the value is the same one the source
        divides by, reached one layer lower.
        """

        from .ui.preferences import get_frame_limit

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0
        fps_limit = get_frame_limit()
        fps_limit = max(fps_limit, 30)  # Prevent division by zero
        return int(agent.timer / fps_limit * 1000)

    @staticmethod
    def GetAgentEffects(agent_id: int) -> int:
        """Retrieve the effects of an agent (``Agent.py:296-308``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0

        return living.effects

    @staticmethod
    def GetTypeMap(agent_id: int) -> int:
        """Retrieve the type map of an agent (``Agent.py:310-321``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.type_map

    @staticmethod
    def GetModelState(agent_id: int) -> int:
        """Retrieve the model state of an agent (``Agent.py:323-334``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.model_state

    @staticmethod
    def GetModelID(agent_id: int) -> int:
        """Retrieve the model of an agent (``Agent.py:336-343``).

        The source also carries ``@frame_cache(category="Agent", source_lib="GetModelID")``
        (``Agent.py:337``); the decorator is dropped, because its only invalidation is Reforged's
        per-frame tick and this port has no frame loop (``PORTING_RULES.md``). The member reads
        when it is called.
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.player_number

    @staticmethod
    def IsLiving(agent_id: int) -> bool:
        """Check if the agent is living (``Agent.py:345-351``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return False
        return agent.is_living_type

    @staticmethod
    def IsItem(agent_id: int) -> bool:
        """Check if the agent is an item (``Agent.py:353-359``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return False
        return agent.is_item_type

    @staticmethod
    def IsGadget(agent_id: int) -> bool:
        """Check if the agent is a gadget (``Agent.py:361-367``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return False
        return agent.is_gadget_type

    @staticmethod
    def GetPlayerNumber(agent_id: int) -> int:
        """Retrieve the player number of an agent (``Agent.py:369-375``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.player_number

    @staticmethod
    def GetLoginNumber(agent_id: int) -> int:
        """Retrieve the login number of an agent (``Agent.py:377-383``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.login_number

    @staticmethod
    def IsSpirit(agent_id: int) -> bool:
        """Check if the agent is a spirit (``Agent.py:385-393``)."""

        from .enums_src.game_data_enums import Allegiance

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        allegiance = Allegiance(living.allegiance)
        return allegiance == Allegiance.SpiritPet and Agent.IsSpawned(agent_id)

    @staticmethod
    def IsPet(agent_id: int) -> bool:
        """Check if the agent is a pet (``Agent.py:395-403``)."""

        from .enums_src.game_data_enums import Allegiance

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        allegiance = Allegiance(living.allegiance)
        return allegiance == Allegiance.SpiritPet and not Agent.IsSpawned(agent_id)

    @staticmethod
    def IsMinion(agent_id: int) -> bool:
        """Check if the agent is a minion (``Agent.py:405-413``)."""

        from .enums_src.game_data_enums import Allegiance

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        allegiance = Allegiance(living.allegiance)
        return allegiance == Allegiance.Minion

    @staticmethod
    def GetOwnerID(agent_id: int) -> int:
        """Retrieve the owner ID of an agent (``Agent.py:415-421``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.owner

    @staticmethod
    def GetXY(agent_id: int) -> tuple[float, float]:
        """Retrieve the X and Y coordinates of an agent (``Agent.py:423-435``).

        The source also carries ``@frame_cache(category="Agent", source_lib="GetXY")``
        (``Agent.py:424``); the decorator is dropped (no frame loop here), so the member reads
        when it is called.
        """

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0
        pos = agent.pos
        return pos.x, pos.y

    @staticmethod
    def GetXYZ(agent_id: int) -> tuple[float, float, float]:
        """Retrieve the X, Y and Z coordinates of an agent (``Agent.py:437-449``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0, 0.0
        pos = agent.pos
        z = agent.z
        return pos.x, pos.y, z

    @staticmethod
    def GetZPlane(agent_id: int) -> int:
        """Retrieve the Z plane of an agent (``Agent.py:451-462``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0
        pos = agent.pos
        return pos.zplane

    @staticmethod
    def GetNameTagXYZ(agent_id: int) -> tuple[float, float, float]:
        """Retrieve the name tag X, Y and Z of an agent (``Agent.py:464-474``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0, 0.0
        return agent.name_tag_x, agent.name_tag_y, agent.name_tag_z

    @staticmethod
    def GetModelScale1(agent_id: int) -> tuple[float, float]:
        """Retrieve the model scale of an agent (``Agent.py:476-487``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0

        return agent.width1, agent.height1

    @staticmethod
    def GetModelScale2(agent_id: int) -> tuple[float, float]:
        """Retrieve the model scale of an agent (``Agent.py:489-500``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0

        return agent.width2, agent.height2

    @staticmethod
    def GetModelScale3(agent_id: int) -> tuple[float, float]:
        """Retrieve the model scale of an agent (``Agent.py:502-513``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0

        return agent.width3, agent.height3

    @staticmethod
    def GetNameProperties(agent_id: int) -> int:
        """Retrieve the name properties of an agent (``Agent.py:515-526``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0

        return agent.name_properties

    @staticmethod
    def GetVisualEffects(agent_id: int) -> int:
        """Retrieve the visual effects of an agent (``Agent.py:528-539``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0

        return agent.visual_effects

    @staticmethod
    def GetTerrainNormalXYZ(agent_id: int) -> tuple[float, float, float]:
        """Retrieve the terrain normal X, Y and Z of an agent (``Agent.py:541-552``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0, 0.0

        return agent.terrain_normal.x, agent.terrain_normal.y, agent.terrain_normal.z

    @staticmethod
    def GetGround(agent_id: int) -> float:
        """Retrieve the ground of an agent (``Agent.py:554-565``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0

        return agent.ground

    @staticmethod
    def GetAnimationCode(agent_id: int) -> int:
        """Retrieve the animation code of an agent (``Agent.py:567-578``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.animation_code

    @staticmethod
    def GetWeaponItemType(agent_id: int) -> int:
        """Retrieve the weapon item type of an agent (``Agent.py:580-591``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.weapon_item_type

    @staticmethod
    def GetOffhandItemType(agent_id: int) -> int:
        """Retrieve the offhand item type of an agent (``Agent.py:593-604``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.offhand_item_type

    @staticmethod
    def GetAnimationType(agent_id: int) -> float:
        """Retrieve the animation type of an agent (``Agent.py:606-617``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.animation_type

    @staticmethod
    def GetWeaponAttackSpeed(agent_id: int) -> float:
        """Retrieve the weapon attack speed of an agent (``Agent.py:619-630``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0.0

        return living_agent.weapon_attack_speed

    @staticmethod
    def GetAttackSpeedModifier(agent_id: int) -> float:
        """Retrieve the attack speed modifier of an agent (``Agent.py:632-643``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0.0

        return living_agent.attack_speed_modifier

    @staticmethod
    def GetAgentModelType(agent_id: int) -> int:
        """Retrieve the agent model type of an agent (``Agent.py:645-656``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.agent_model_type

    @staticmethod
    def GetTransmogNPCID(agent_id: int) -> int:
        """Retrieve the transmog NPC ID of an agent (``Agent.py:658-669``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.transmog_npc_id

    @staticmethod
    def GetGuildID(agent_id: int) -> int:
        """Retrieve the guild ID of an agent (``Agent.py:671-685``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        tags = living_agent.tags
        if tags is None:
            return 0
        return tags.guild_id

    @staticmethod
    def GetTeamID(agent_id: int) -> int:
        """Retrieve the team ID of an agent (``Agent.py:687-698``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.team_id

    @staticmethod
    def GetAnimationSpeed(agent_id: int) -> float:
        """Retrieve the animation speed of an agent (``Agent.py:700-711``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0.0

        return living_agent.animation_speed

    @staticmethod
    def GetAnimationID(agent_id: int) -> int:
        """Retrieve the animation ID of an agent (``Agent.py:713-724``)."""

        living_agent = Agent.GetLivingAgentByID(agent_id)
        if living_agent is None:
            return 0

        return living_agent.animation_id

    @staticmethod
    def GetRotationAngle(agent_id: int) -> float:
        """Retrieve the rotation angle of an agent (``Agent.py:726-736``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0
        return agent.rotation_angle

    @staticmethod
    def GetRotationCos(agent_id: int) -> float:
        """Retrieve the cosine of the rotation angle of an agent (``Agent.py:738-748``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0
        return agent.rotation_cos

    @staticmethod
    def GetRotationSin(agent_id: int) -> float:
        """Retrieve the sine of the rotation angle of an agent (``Agent.py:750-761``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0
        return agent.rotation_sin

    @staticmethod
    def GetVelocityXY(agent_id: int) -> tuple[float, float]:
        """Retrieve the X and Y velocity of an agent (``Agent.py:763-775``)."""

        agent = Agent.GetAgentByID(agent_id)
        if agent is None:
            return 0.0, 0.0
        velocity = agent.velocity

        return velocity.x, velocity.y

    @staticmethod
    def GetProfessions(agent_id: int) -> tuple[int, int]:
        """Retrieve the primary and secondary professions (``Agent.py:777-788``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, 0

        return living.primary, living.secondary

    @staticmethod
    def GetProfessionNames(agent_id: int) -> tuple[str, str]:
        """Retrieve the names of the primary and secondary professions (``Agent.py:790-807``)."""

        from .enums_src.game_data_enums import Profession, Profession_Names

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return "", ""

        profession = Profession(living.primary)
        prof_name = Profession_Names[profession]
        secondary_profession = Profession(living.secondary)
        secondary_prof_name = Profession_Names[secondary_profession]

        return prof_name if prof_name is not None else "", secondary_prof_name if secondary_prof_name is not None else ""

    @staticmethod
    def GetProfessionShortNames(agent_id: int) -> tuple[str, str]:
        """Retrieve the short names of the primary and secondary professions (``Agent.py:809-826``)."""

        from .enums_src.game_data_enums import ProfessionShort, ProfessionShort_Names

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return "", ""

        profession = ProfessionShort(living.primary)
        prof_name = ProfessionShort_Names[profession]
        secondary_profession = ProfessionShort(living.secondary)
        secondary_prof_name = ProfessionShort_Names[secondary_profession]

        return prof_name, secondary_prof_name

    @staticmethod
    def GetProfessionIDs(agent_id: int) -> tuple[int, int]:
        """Retrieve the ids of the primary and secondary professions (``Agent.py:828-838``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, 0
        return living.primary, living.secondary

    @staticmethod
    def GetLevel(agent_id: int) -> int:
        """Retrieve the level of an agent (``Agent.py:840-850``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.level

    @staticmethod
    def GetEnergy(agent_id: int) -> float:
        """Retrieve the energy of the agent (``Agent.py:852-862``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.energy

    @staticmethod
    def GetMaxEnergy(agent_id: int) -> int:
        """Retrieve the maximum energy of the agent (``Agent.py:864-874``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.max_energy

    @staticmethod
    def GetEnergyRegen(agent_id: int) -> float:
        """Retrieve the energy regeneration of the agent (``Agent.py:876-886``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.energy_regen

    @staticmethod
    def GetEnergyPips(agent_id: int) -> int:
        """Retrieve the energy pips of the agent (``Agent.py:888-899``).

        The conversion is ``Utils.calculate_energy_pips``
        (``py4gwcorelib_src/Utils.py:749-753``), ported as ``Utils``'s own arithmetic
        (``py4gw/py4gwcorelib_src/utils.py``).
        """

        from .py4gwcorelib_src.utils import Utils

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return Utils.calculate_energy_pips(living.max_energy, living.energy_regen)

    @staticmethod
    def GetHealth(agent_id: int) -> float:
        """Retrieve the health of the agent (``Agent.py:901-911``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.hp

    @staticmethod
    def GetMaxHealth(agent_id: int) -> int:
        """Retrieve the maximum health of the agent (``Agent.py:913-923``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.max_hp

    @staticmethod
    def GetHealthRegen(agent_id: int) -> float:
        """Retrieve the health regeneration of the agent (``Agent.py:925-935``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.hp_pips

    @staticmethod
    def GetHealthPips(agent_id: int) -> int:
        """Retrieve the health pips of the agent (``Agent.py:937-950``).

        The conversion is ``Utils.calculate_health_pips``
        (``py4gwcorelib_src/Utils.py:755-759``), ported as ``Utils``'s own arithmetic
        (``py4gw/py4gwcorelib_src/utils.py``).
        """

        from .py4gwcorelib_src.utils import Utils

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0

        return Utils.calculate_health_pips(living.max_hp, living.hp_pips)

    @staticmethod
    def CanAct(agent_id: int) -> bool:
        """Always ``True`` (``Agent.py:952-955``).

        The source returns the literal: the combat-event queue behind it is commented out
        (``Agent.py:955``), so there is nothing to port but the constant.
        """

        return True

    @staticmethod
    def IsMoving(agent_id: int) -> bool:
        """Check if the agent is moving (``Agent.py:957-962``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_moving

    @staticmethod
    def IsKnockedDown(agent_id: int) -> bool:
        """Check if the agent is knocked down (``Agent.py:964-970``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_knocked_down

    @staticmethod
    def GetKnockDownTimeRemaining(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:972-975``).

        The source returns the literal; the combat-event helper behind it is commented out.
        """

        return 0

    @staticmethod
    def IsBleeding(agent_id: int) -> bool:
        """Check if the agent is bleeding (``Agent.py:978-983``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_bleeding

    @staticmethod
    def IsCrippled(agent_id: int) -> bool:
        """Check if the agent is crippled (``Agent.py:985-990``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_crippled

    @staticmethod
    def IsDeepWounded(agent_id: int) -> bool:
        """Check if the agent is deep-wounded (``Agent.py:992-997``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_deep_wounded

    @staticmethod
    def IsPoisoned(agent_id: int) -> bool:
        """Check if the agent is poisoned (``Agent.py:999-1004``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_poisoned

    @staticmethod
    def IsConditioned(agent_id: int) -> bool:
        """Check if the agent is conditioned (``Agent.py:1006-1011``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_conditioned

    @staticmethod
    def IsEnchanted(agent_id: int) -> bool:
        """Check if the agent is enchanted (``Agent.py:1013-1018``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_enchanted

    @staticmethod
    def IsHexed(agent_id: int) -> bool:
        """Check if the agent is hexed (``Agent.py:1020-1025``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_hexed

    @staticmethod
    def IsDegenHexed(agent_id: int) -> bool:
        """Check if the agent is degeneration-hexed (``Agent.py:1027-1032``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_degen_hexed

    @staticmethod
    def IsDead(agent_id: int) -> bool:
        """Check if the agent is dead (``Agent.py:1034-1051``).

        The five terms are the source's, in its order, including the residual-health epsilon
        (``Agent.DEAD_HEALTH_EPSILON``).
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        health = float(living.hp)
        is_dead = bool(living.is_dead)
        dead_by_type_map = bool(living.is_dead_by_type_map)
        is_exploitable_corpse = bool(living.is_exploitable)
        is_used_corpse = bool(living.is_used_corpse)
        return (
            is_dead
            or dead_by_type_map
            or is_exploitable_corpse
            or is_used_corpse
            or health <= Agent.DEAD_HEALTH_EPSILON
        )

    @staticmethod
    def IsExploitable(agent_id: int) -> bool:
        """Check if the agent is exploitable (``Agent.py:1053-1058``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_exploitable

    @staticmethod
    def IsExploitableCorpse(agent_id: int) -> bool:
        """Whether the agent is a dead, unexploited, fleshy corpse (``Agent.py:1060-1063``)."""

        return Agent.IsExploitable(agent_id) and Agent.IsFleshy(agent_id)

    @staticmethod
    def IsUsedCorpse(agent_id: int) -> bool:
        """Check if the agent's corpse has been used (``Agent.py:1065-1070``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_used_corpse

    @staticmethod
    def IsExploitedCorpse(agent_id: int) -> bool:
        """Whether the agent's corpse has already been exploited (``Agent.py:1072-1075``)."""

        return Agent.IsUsedCorpse(agent_id)

    @staticmethod
    def IsAlive(agent_id: int) -> bool:
        """Check if the agent is alive (``Agent.py:1077-1093``).

        The source's negation of :meth:`IsDead`'s terms, including the epsilon.
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        health = float(living.hp)
        is_dead = bool(living.is_dead)
        dead_by_type_map = bool(living.is_dead_by_type_map)
        is_exploitable_corpse = bool(living.is_exploitable)
        is_used_corpse = bool(living.is_used_corpse)
        return (
            health > Agent.DEAD_HEALTH_EPSILON
            and not is_dead
            and not dead_by_type_map
            and not is_exploitable_corpse
            and not is_used_corpse
        )

    @staticmethod
    def IsWeaponSpelled(agent_id: int) -> bool:
        """Check if the agent's weapon is spelled (``Agent.py:1095-1100``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_weapon_spelled

    @staticmethod
    def IsInCombatStance(agent_id: int) -> bool:
        """Check if the agent is in a combat stance (``Agent.py:1102-1107``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_in_combat_stance

    @staticmethod
    def HasStance(agent_id: int) -> bool:
        """Always ``False`` (``Agent.py:1109-1112``).

        The source returns the literal; the combat-event helper behind it is commented out.
        """

        return False

    @staticmethod
    def GetStanceID(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1114-1117``)."""

        return 0

    @staticmethod
    def GetStanceCooldown(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1119-1122``)."""

        return 0

    @staticmethod
    def IsAggressive(agent_id: int) -> bool:
        """Check if the agent is attacking or casting (``Agent.py:1124-1132``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        is_attacking = living.is_attacking
        is_casting = living.is_casting
        return is_attacking or is_casting

    @staticmethod
    def IsAttacking(agent_id: int) -> bool:
        """Check if the agent is attacking (``Agent.py:1134-1140``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_attacking

    @staticmethod
    def IsCasting(agent_id: int) -> bool:
        """Check if the agent is casting (``Agent.py:1142-1148``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_casting

    @staticmethod
    def GetCastingSkillID(agent_id: int) -> int:
        """Retrieve the skill the agent is casting (``Agent.py:1150-1161``)."""

        if not Agent.IsCasting(agent_id):
            return 0

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0

        return living.skill

    @staticmethod
    def GetTarget(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1163-1203``).

        The source returns the literal: its real body — player, hero, pet and combat-event lookups
        — is one long comment (``Agent.py:1167-1203``), so there is nothing to port but the
        constant.
        """

        return 0

    @staticmethod
    def GetCastingTarget(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1205-1208``)."""

        return 0

    @staticmethod
    def GetRemainingCastTime(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1210-1213``)."""

        return 0

    @staticmethod
    def GetRemainingRechargeTime(agent_id: int, skill_id: int) -> int:
        """Always ``0`` (``Agent.py:1215-1218``)."""

        return 0

    @staticmethod
    def IsTargeted(agent_id: int) -> bool:
        """Always ``False`` (``Agent.py:1220-1223``)."""

        return False

    @staticmethod
    def GetAgetsTargeting(agent_id: int) -> list[int]:
        """Always ``[]`` (``Agent.py:1225-1228``)."""

        return []

    @staticmethod
    def IsSkillOnCooldown(agent_id: int, skill_id: int) -> bool:
        """Always ``False`` (``Agent.py:1230-1233``)."""

        return False

    @staticmethod
    def IsCooldownEstimated(agent_id: int, skill_id: int) -> bool:
        """Always ``False`` (``Agent.py:1235-1238``)."""

        return False

    @staticmethod
    def GetSkillsOnCooldown(agent_id: int) -> list[tuple[int, int, bool]]:
        """Always ``[]`` (``Agent.py:1240-1246``)."""

        return []

    @staticmethod
    def GetRecentHealingReceived(agent_id: int, count: int = 20) -> list[tuple[int, int, float, int]]:
        """Always ``[]`` (``Agent.py:1248-1252``)."""

        return []

    @staticmethod
    def GetRecentHealingDealt(agent_id: int, count: int = 20) -> list[tuple[int, int, float, int]]:
        """Always ``[]`` (``Agent.py:1254-1258``)."""

        return []

    @staticmethod
    def HasEffectRenewed(agent_id: int, effect_id: int, window_ms: int = 10000) -> bool:
        """Always ``False`` (``Agent.py:1260-1263``)."""

        return False

    @staticmethod
    def GetObservedSkillbar(agent_id: int) -> list[int]:
        """Always ``[]`` (``Agent.py:1265-1269``)."""

        return []

    @staticmethod
    def GetAttackTarget(agent_id: int) -> int:
        """Always ``0`` (``Agent.py:1271-1274``)."""

        return 0

    @staticmethod
    def IsIdle(agent_id: int) -> bool:
        """Check if the agent is idle (``Agent.py:1276-1281``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_idle

    @staticmethod
    def HasBossGlow(agent_id: int) -> bool:
        """Check if the agent has a boss glow (``Agent.py:1283-1288``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.has_boss_glow

    @staticmethod
    def GetWeaponType(agent_id: int) -> tuple[int, str]:
        """Retrieve the weapon type of the agent (``Agent.py:1290-1305``)."""

        from .enums_src.game_data_enums import Weapon, Weapon_Names

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, "Unknown"

        try:
            weapon_type_enum = Weapon(living.weapon_type)
        except ValueError:
            return living.weapon_type, "Unknown"

        name = Weapon_Names.get(weapon_type_enum, "Unknown")
        return living.weapon_type, name

    @staticmethod
    def IsHoldingItem(agent_id: int) -> bool:
        """Check if the agent is carrying a bundle (``Agent.py:1307-1318``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False

        return living.weapon_type == 0

    @staticmethod
    def GetWeaponExtraData(agent_id: int) -> tuple[int, int, int, int]:
        """Retrieve the weapon extra data of the agent (``Agent.py:1320-1331``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, 0, 0, 0

        return (
            living.weapon_item_id,
            living.weapon_item_type,
            living.offhand_item_id,
            living.offhand_item_type,
        )

    @staticmethod
    def IsMartial(agent_id: int) -> bool:
        """Check if the agent is martial (``Agent.py:1333-1355``).

        Blocked on one companion class: the body resolves ``Skill.GetID("Illusionary_Weaponry")``
        — which is ported (``py4gw/skill.py`` over native's own name table) — and then asks
        ``Effects.HasEffect`` (``Effect.py:102``) before comparing the weapon name, and the
        ``Effect`` class is not ported. The member also writes ``Agent.ILLUSIONARY_WEAPONRY_ID`` on
        first use, which is the source's own memo.
        """

        raise _unported(
            "IsMartial",
            "Effects.HasEffect (Effect.py:102), the companion class the body asks about "
            "Illusionary Weaponry before comparing the weapon name; Skill.GetID is ported",
        )

    @staticmethod
    def IsCaster(agent_id: int) -> bool:
        """Check if the agent is a caster (``Agent.py:1357-1372``).

        The body is the source's; the raise comes from ``Agent.IsPet`` (allegiance enum) and
        ``Agent.GetWeaponType`` (weapon enum), which own the missing pieces.
        """

        if Agent.IsPet(agent_id):
            return False

        caster_weapon_types = {"Wand", "Staff", "Staff1", "Staff2", "Staff3", "Scepter", "Scepter2"}
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if weapon_type == 0 or weapon_name == "Unknown":
            return False

        return weapon_name in caster_weapon_types

    @staticmethod
    def IsMelee(agent_id: int) -> bool:
        """Check if the agent is melee (``Agent.py:1374-1394``).

        Blocked like :meth:`IsMartial`: the remaining piece is ``Effects.HasEffect``
        (``Effect.py:102``); ``Skill.GetID`` is ported.
        """

        raise _unported(
            "IsMelee",
            "Effects.HasEffect (Effect.py:102), the companion class the body asks about "
            "Illusionary Weaponry before comparing the weapon name; Skill.GetID is ported",
        )

    @staticmethod
    def IsRanged(agent_id: int) -> bool:
        """Check if the agent is ranged (``Agent.py:1396-1409``).

        The body is the source's; the raise comes from ``Agent.IsPet`` and ``Agent.GetWeaponType``.
        """

        if Agent.IsPet(agent_id):
            return False
        weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
        if weapon_type == 0:
            return False
        ranged_weapon_types = ["Bow", "Spear"]
        return weapon_name in ranged_weapon_types

    @staticmethod
    def GetDaggerStatus(agent_id: int) -> int:
        """Retrieve the dagger status of the agent (``Agent.py:1411-1417``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0
        return living.dagger_status

    @staticmethod
    def GetAllegiance(agent_id: int) -> tuple[int, str]:
        """Retrieve the allegiance of the agent (``Agent.py:1419-1433``)."""

        from .enums_src.game_data_enums import Allegiance, AllegianceNames

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0, "Unknown"

        try:
            allegiance_enum = Allegiance(living.allegiance)
        except ValueError:
            return living.allegiance, "Unknown"

        name = AllegianceNames.get(allegiance_enum, "Unknown")
        return living.allegiance, name

    @staticmethod
    def IsPlayer(agent_id: int) -> bool:
        """Check if the agent is a player (``Agent.py:1435-1438``)."""

        login_number = Agent.GetLoginNumber(agent_id)
        return login_number != 0

    @staticmethod
    def IsNPC(agent_id: int) -> bool:
        """Check if the agent is an NPC (``Agent.py:1440-1443``)."""

        login_number = Agent.GetLoginNumber(agent_id)
        return login_number == 0

    @staticmethod
    def GetNPCModelByID(model_id: int) -> NPC_ModelStruct | None:
        """Retrieve an NPC model record by its id, or ``None`` (``Agent.py:1445-1463``).

        Adapted at the context, like :meth:`GetAttributes`: the source asks
        ``GWContext.World.GetContext()``; this port reads the same world context through
        ``ConnectedClient.read_world_context``, whose ``npc_models`` is the ported
        ``npc_models_array``. The member's own order is kept — the indexed record first, then the
        scan by ``model_file_id``.
        """

        if model_id <= 0:
            return None
        client = require_client()
        try:
            world_ctx: WorldContextStruct | None = client.read_world_context()
        except (OSError, RuntimeError):
            return None
        if world_ctx is None:
            return None
        npc_models = world_ctx.npc_models
        if not npc_models:
            return None
        if model_id < len(npc_models):
            npc = npc_models[model_id]
            if npc and npc.is_valid:
                return npc
        for npc in npc_models:
            if int(npc.model_file_id) == int(model_id):
                return npc
        return None

    @staticmethod
    def GetNPCFlags(agent_id: int) -> int:
        """Retrieve the NPC flags of the agent (``Agent.py:1465-1471``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None or living.is_player:
            return 0
        npc = Agent.GetNPCModelByID(int(living.player_number))
        return int(npc.npc_flags) if npc else 0

    @staticmethod
    def IsFleshy(agent_id: int) -> bool:
        """Check if the agent's model is fleshy (``Agent.py:1473-1481``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        if living.is_player:
            return True
        npc = Agent.GetNPCModelByID(int(living.player_number))
        return bool(npc and npc.is_fleshy)

    @staticmethod
    def HasQuest(agent_id: int) -> bool:
        """Check if the agent has a quest (``Agent.py:1483-1488``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.has_quest

    @staticmethod
    def IsDeadByTypeMap(agent_id: int) -> bool:
        """Check if the type map marks the agent dead (``Agent.py:1490-1495``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_dead_by_type_map

    @staticmethod
    def IsFemale(agent_id: int) -> bool:
        """Check if the agent is female (``Agent.py:1497-1502``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_female

    @staticmethod
    def IsHidingCape(agent_id: int) -> bool:
        """Check if the agent is hiding its cape (``Agent.py:1504-1509``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_hiding_cape

    @staticmethod
    def CanBeViewedInPartyWindow(agent_id: int) -> bool:
        """Check if the agent can be viewed in the party window (``Agent.py:1511-1516``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.can_be_viewed_in_party_window

    @staticmethod
    def IsSpawned(agent_id: int) -> bool:
        """Check if the agent is spawned (``Agent.py:1518-1523``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_spawned

    @staticmethod
    def IsBeingObserved(agent_id: int) -> bool:
        """Check if the agent is being observed (``Agent.py:1525-1530``)."""

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return False
        return living.is_being_observed

    @staticmethod
    def GetOvercast(agent_id: int) -> float:
        """Retrieve the overcast of the agent (``Agent.py:1532-1538``).

        The field is the source's ``h0128`` — an unnamed word of the living record that this port's
        context carries under the same name (``agent_array.py:287``).
        """

        living = Agent.GetLivingAgentByID(agent_id)
        if living is None:
            return 0.0
        return living.h0128

    @staticmethod
    def GetProfessionsTexturePaths(agent_id: int) -> tuple[str, str]:
        """Retrieve the profession icon texture paths (``Agent.py:1540-1561``).

        Its two enum dependencies are ported — ``GetProfessions`` reads the record and
        ``GetProfessionNames`` maps it through ``enums_src.GameData_enums.Profession`` — so what is
        left is the root the source prefixes both paths with: ``PySystem.Console.get_projects_path()``
        (``stubs/PySystem.pyi:105``), a native console call inside the injected runtime. Without it a
        path would be built from this project's own directory, which is a different string.
        """

        raise _unported(
            "GetProfessionsTexturePaths",
            "PySystem.Console.get_projects_path() (stubs/PySystem.pyi:105), the native console "
            "path the source prefixes its texture paths with",
        )

    # ── item agents (Agent.py:1563-1597) ──────────────────────────────────

    @staticmethod
    def GetItemAgentOwnerID(agent_id: int) -> int:
        """Retrieve the owner ID of the item agent, or ``999`` (``Agent.py:1564-1573``)."""

        item = Agent.GetItemAgentByID(agent_id)
        if item is None:
            return 999
        current_owner_id = item.owner

        return current_owner_id

    @staticmethod
    def GetItemAgentItemID(agent_id: int) -> int:
        """Retrieve the item ID of the item agent (``Agent.py:1575-1581``)."""

        item_data = Agent.GetItemAgentByID(agent_id)
        if item_data is None:
            return 0
        return item_data.item_id

    @staticmethod
    def GetItemAgentExtraType(agent_id: int) -> int:
        """Retrieve the extra type of the item agent (``Agent.py:1583-1589``)."""

        item_data = Agent.GetItemAgentByID(agent_id)
        if item_data is None:
            return 0
        return item_data.extra_type

    @staticmethod
    def GetItemAgenth00CC(agent_id: int) -> int:
        """Retrieve the ``h00CC`` of the item agent (``Agent.py:1591-1597``)."""

        item_data = Agent.GetItemAgentByID(agent_id)
        if item_data is None:
            return 0
        return item_data.h00CC

    # ── gadget agents (Agent.py:1599-1646) ────────────────────────────────

    @staticmethod
    def GetGadgetID(agent_id: int) -> int:
        """Retrieve the gadget ID of the agent (``Agent.py:1600-1606``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.gadget_id

    @staticmethod
    def GetGadgetAgentID(agent_id: int) -> int:
        """Retrieve the agent ID of the gadget agent (``Agent.py:1608-1614``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.agent_id

    @staticmethod
    def GetGadgetAgentExtraType(agent_id: int) -> int:
        """Retrieve the extra type of the gadget agent (``Agent.py:1616-1622``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.extra_type

    @staticmethod
    def GetGadgetAgenth00C4(agent_id: int) -> int:
        """Retrieve the ``h00C4`` of the gadget agent (``Agent.py:1624-1630``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.h00C4

    @staticmethod
    def GetGadgetAgenth00C8(agent_id: int) -> int:
        """Retrieve the ``h00C8`` of the gadget agent (``Agent.py:1632-1638``)."""

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return 0
        return gadget.h00C8

    @staticmethod
    def GetGadgetAgenth00D4(agent_id: int) -> list:
        """Retrieve the ``h00D4`` of the gadget agent (``Agent.py:1640-1646``).

        One detail of the value: the source returns the record's fixed-size array object as it
        stands, and this port answers with the dict-free ``list`` of its four words — the type the
        member's own ``-> list`` annotation declares, and the one a caller can iterate the same way.
        """

        gadget = Agent.GetGadgetAgentByID(agent_id)
        if gadget is None:
            return []
        return list(gadget.h00D4)
