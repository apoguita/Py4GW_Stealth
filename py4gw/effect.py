"""Port of Reforged's ``Py4GWCoreLib/Effect.py`` over Native's ``PyEffects`` binding.

**Sources.** ``Py4GWCoreLib/Effect.py`` (176 lines, ``class Effects`` at line 5, **15 members**) and
the binding its every member calls: ``effects_bindings.cpp:34-184``, over
``GW::effects`` (``effects_methods.cpp:29-72``) and ``Context::Effect``/``Buff``/``AgentEffects``
(``skill.h:124-152``). ``stubs/PyEffects.pyi`` is the same surface in stub form.

**What the walk is, and where this port reads it.** Every effect and buff the binding answers with
comes out of one array: ``Context::GetPartyEffectsArray()`` (``effects_methods.cpp:29-41``) — the
world's ``party_effects``, a ``GWArray<AgentEffects>`` — scanned for the block whose ``agent_id``
matches, and then its ``effects`` or ``buffs`` sub-array. This port already reads that array:
``WorldContextStruct.party_effects`` → :class:`~py4gw.context.world_context.AgentEffectsStruct`,
whose ``effects``/``buffs`` properties are the two sub-arrays (``AgentEffectsStruct`` 0x24,
``Effect`` 0x18, ``Buff`` 0x10 — native's own ``static_assert``s). So the whole binding surface is a
read: no call, no hook, no target-side work.

**The three members that are not reads**, ported as the source writes them:

- ``DropBuff`` calls the client's own drop-buff function — the resolver
  ``effects.drop_buff_func`` (``offsets/effects.json``, from ``effects_patterns.cpp``) — on the
  client's thread, through the same call machinery ``Player``'s actions use.
- ``ApplyDrunkEffect`` calls the post-process function at ``effects.post_process_effect_func`` with
  the two words. Native calls the *original* pointer its own hook saved (``effects.cpp:23-27``);
  this port has no hook on that function, so the client's own code at that address is the same
  target.
- ``GetAlcoholLevel`` cannot be answered at all: native's number is the ``intensity`` argument of
  the client's post-process call, captured by an entry hook that stores it (``effects.cpp:24-41``,
  ``g_alcohol_level``). That is target-side work — the entry is in
  [`docs/TARGET_SIDE_WORK.md`](../../docs/TARGET_SIDE_WORK.md) — so the member raises naming it
  rather than answering a number from nowhere.

**Two findings recorded here rather than smoothed over.**

1. ``Effects.GetAlcoholTimeRemaining`` (``Effect.py:161-164``) calls
   ``PyEffects.PyEffects.GetAlcoholTimeRemaining()`` — and **the binding implements no such
   member** (``effects_bindings.cpp:181-183`` declares ``GetAlcoholLevel`` and ``ApplyDrunkEffect``,
   nothing else), and native tracks no alcohol *time* anywhere (``g_alcohol_level`` is a bare word).
   The stub declares it (``PyEffects.pyi:41``), which is why Reforged's Python calls it. The port
   reports the disagreement on the member instead of inventing a clock for it.
2. ``Effects.GetBuffID``'s docstring says it returns ``-1`` when the buff is not found; its body
   returns ``0``. The body is what is ported (``Effect.py:139-149``).
"""

from __future__ import annotations

from dataclasses import dataclass

from .client import require_client
from .context.world_context import AgentEffectsStruct, BuffStruct, EffectStruct

#: ``DWORD`` arithmetic wraps at 32 bits, and both the skill timer and an effect's elapsed time are
#: ``DWORD`` in the source (``skill.cpp:39-45``).
_DWORD_MASK = 0xFFFFFFFF

#: The two catalog names the calls below use (``offsets/effects.json``, from
#: ``effects_patterns.cpp``).
_DROP_BUFF_FUNC = "effects.drop_buff_func"
_POST_PROCESS_EFFECT_FUNC = "effects.post_process_effect_func"


@dataclass(slots=True)
class EffectType:
    """Native's ``PyEffectType`` (``effects_bindings.cpp:15-24``), bound as ``PyEffects.EffectType``.

    A value snapshot: the client's ``Context::Effect`` copied out, with the two derived times the
    binding computes — ``time_elapsed`` and ``time_remaining``.
    """

    skill_id: int = 0
    attribute_level: int = 0
    effect_id: int = 0
    agent_id: int = 0
    duration: float = 0.0
    timestamp: int = 0
    time_elapsed: int = 0
    time_remaining: int = 0


@dataclass(slots=True)
class BuffType:
    """Native's ``PyBuffType`` (``effects_bindings.cpp:26-30``), bound as ``PyEffects.BuffType``."""

    skill_id: int = 0
    buff_id: int = 0
    target_agent_id: int = 0


def _agent_effects(agent_id: int) -> AgentEffectsStruct | None:
    """``GW::effects::GetAgentEffectsArray`` (``effects_methods.cpp:29-41``).

    ``Context::GetPartyEffectsArray()`` is the world's ``party_effects`` when its header is valid;
    the source then walks it for the block whose ``agent_id`` matches, and answers null when there
    is none. The port reads the same array and makes the same scan.
    """

    client = require_client()
    world = client.read_world_context()
    if world is None:
        return None
    for block in world.party_effects or []:
        if int(block.agent_id) == int(agent_id):
            return block
    return None


def _get_agent_effects(agent_id: int) -> list[EffectStruct]:
    """``GW::effects::GetAgentEffects`` (``effects_methods.cpp:47-50``): the ``effects`` sub-array.

    The source answers the array only when ``effects.valid()``; this port's ``effects`` property
    reads an invalid header as no records at all, which is the same answer.
    """

    block = _agent_effects(agent_id)
    if block is None:
        return []
    return list(block.effects)


def _get_agent_buffs(agent_id: int) -> list[BuffStruct]:
    """``GW::effects::GetAgentBuffs`` (``effects_methods.cpp:52-55``): the ``buffs`` sub-array."""

    block = _agent_effects(agent_id)
    if block is None:
        return []
    return list(block.buffs)


def _effect_snapshot(effect: EffectStruct) -> EffectType:
    """One ``PyEffectType`` out of a ``Context::Effect`` (``effects_bindings.cpp:100-109``).

    The binding copies six fields and computes two:
    ``time_elapsed = PY4GW::MemoryManager::GetSkillTimer() - timestamp`` and
    ``time_remaining = (DWORD)(duration * 1000.0f) - time_elapsed`` (``skill.cpp:39-45``). Both are
    ``DWORD`` subtractions, so both wrap — masked here the way the registers do.
    """

    duration = float(effect.duration)
    timestamp = int(effect.timestamp)

    skill_timer = require_client().memory_manager.GetSkillTimer()
    time_elapsed = (skill_timer - timestamp) & _DWORD_MASK
    time_remaining = ((int(duration * 1000.0) & _DWORD_MASK) - time_elapsed) & _DWORD_MASK

    return EffectType(
        skill_id=int(effect.skill_id),
        attribute_level=int(effect.attribute_level),
        effect_id=int(effect.effect_id),
        agent_id=int(effect.agent_id),
        duration=duration,
        timestamp=timestamp,
        time_elapsed=time_elapsed,
        time_remaining=time_remaining,
    )


def _buff_snapshot(buff: BuffStruct) -> BuffType:
    """One ``PyBuffType`` out of a ``Context::Buff`` (``effects_bindings.cpp:118-124``)."""

    return BuffType(
        skill_id=int(buff.skill_id),
        buff_id=int(buff.buff_id),
        target_agent_id=int(buff.target_agent_id),
    )


def effect_count(agent_id: int) -> int:
    """``PyEffects.effect_count`` (``effects_bindings.cpp:49-52``)."""

    return len(_get_agent_effects(agent_id))


def buff_count(agent_id: int) -> int:
    """``PyEffects.buff_count`` (``effects_bindings.cpp:54-57``)."""

    return len(_get_agent_buffs(agent_id))


def effect_exists(agent_id: int, skill_id: int) -> bool:
    """``PyEffects.effect_exists`` (``effects_bindings.cpp:59-67``): an exact skill-id match."""

    for effect in _get_agent_effects(agent_id):
        if int(effect.skill_id) == int(skill_id):
            return True
    return False


def buff_exists(agent_id: int, skill_id: int) -> bool:
    """``PyEffects.buff_exists`` (``effects_bindings.cpp:69-77``): an exact skill-id match."""

    for buff in _get_agent_buffs(agent_id):
        if int(buff.skill_id) == int(skill_id):
            return True
    return False


def get_effects(agent_id: int) -> list[EffectType]:
    """``PyEffects.get_effects`` (``effects_bindings.cpp:94-112``)."""

    return [_effect_snapshot(effect) for effect in _get_agent_effects(agent_id)]


def get_buffs(agent_id: int) -> list[BuffType]:
    """``PyEffects.get_buffs`` (``effects_bindings.cpp:114-127``)."""

    return [_buff_snapshot(buff) for buff in _get_agent_buffs(agent_id)]


def drop_buff(buff_id: int) -> bool:
    """``PyEffects.drop_buff`` (``effects_bindings.cpp:45-47``) over ``GW::effects::DropBuff``.

    ``g_drop_buff_func ? g_drop_buff_func(buff_id), true : false`` (``effects_methods.cpp:65-72``):
    a one-word call on the client's own thread, and ``false`` when the catalog has no such function.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    if not client.resolves(_DROP_BUFF_FUNC):
        return False
    client.call_function(_DROP_BUFF_FUNC, CallForm.U32, int(buff_id))
    return True


def get_drunk_af(intensity: int, tint: int) -> None:
    """``PyEffects.get_drunk_af`` (``effects_bindings.cpp:41-43``) over ``GW::effects::GetDrunkAf``.

    ``g_post_process_effect_original ? g_post_process_effect_original(intensity, tint)``
    (``effects_methods.cpp:23-27``). Native's pointer is the trampoline its own hook saved; this
    port holds no hook on that function, so the client's code at the resolved address is the call.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    if not client.resolves(_POST_PROCESS_EFFECT_FUNC):
        return
    client.call_function(
        _POST_PROCESS_EFFECT_FUNC, CallForm.U32_U32, int(intensity), int(tint)
    )


def get_alcohol_level() -> int:
    """``PyEffects.get_alcohol_level`` (``effects_bindings.cpp:37-39``).

    Blocked on target-side work: native's answer is the ``intensity`` argument of the client's
    post-process call, captured by the entry hook at ``effects.cpp:24-41`` into ``g_alcohol_level``.
    This port has no hook on that function, so the member raises and names the work instead of
    answering a number it does not have (``docs/TARGET_SIDE_WORK.md``).
    """

    raise NotImplementedError(
        "PyEffects.get_alcohol_level is declared but not built here yet: it needs the entry hook "
        "on the client's post-process function that native installs to capture its intensity "
        "argument into g_alcohol_level (effects.cpp:24-41; the function is the catalog's "
        "effects.post_process_effect_func). The source's member works; this port raises at the "
        "call site and names the work item instead of returning a wrong value."
    )


class PyEffects:
    """Native's ``PyEffects.PyEffects`` (``effects_bindings.cpp:130-183``).

    The instance holds one ``agent_id`` and every method is the module-level function above applied
    to it — exactly as the binding wraps ``GW::effects``. The three statics are the class's own in
    the source (``def_static``), so they are static here too.
    """

    def __init__(self, agent_id: int) -> None:
        self.agent_id = int(agent_id)

    def GetEffects(self) -> list[EffectType]:
        """``PyEffects.PyEffects.GetEffects`` (``effects_bindings.cpp:133-146``)."""

        return get_effects(self.agent_id)

    def GetBuffs(self) -> list[BuffType]:
        """``PyEffects.PyEffects.GetBuffs`` (``effects_bindings.cpp:147-157``)."""

        return get_buffs(self.agent_id)

    def GetEffectCount(self) -> int:
        """``PyEffects.PyEffects.GetEffectCount`` (``effects_bindings.cpp:158-161``)."""

        return effect_count(self.agent_id)

    def GetBuffCount(self) -> int:
        """``PyEffects.PyEffects.GetBuffCount`` (``effects_bindings.cpp:162-165``)."""

        return buff_count(self.agent_id)

    def EffectExists(self, skill_id: int) -> bool:
        """``PyEffects.PyEffects.EffectExists`` (``effects_bindings.cpp:166-172``)."""

        return effect_exists(self.agent_id, skill_id)

    def BuffExists(self, skill_id: int) -> bool:
        """``PyEffects.PyEffects.BuffExists`` (``effects_bindings.cpp:173-179``)."""

        return buff_exists(self.agent_id, skill_id)

    def DropBuff(self, skill_id: int) -> None:
        """``PyEffects.PyEffects.DropBuff`` (``effects_bindings.cpp:180``).

        The argument is named ``skill_id`` in the binding and forwarded as the buff id — the stub
        says so at ``PyEffects.pyi:35-37``, and the source's own wrapper calls it ``buff_id``.
        """

        drop_buff(skill_id)

    @staticmethod
    def GetAlcoholLevel() -> int:
        """``PyEffects.PyEffects.GetAlcoholLevel`` (``effects_bindings.cpp:181``)."""

        return get_alcohol_level()

    @staticmethod
    def ApplyDrunkEffect(intensity: int = 0, tint: int = 0) -> None:
        """``PyEffects.PyEffects.ApplyDrunkEffect`` (``effects_bindings.cpp:182-183``)."""

        get_drunk_af(intensity, tint)


class Effects:
    """The Reforged ``Effects`` namespace class (``Effect.py:5-176``): 15 static members.

    Every member is the source's two lines: build ``PyEffects.PyEffects(agent_id)`` (or call one of
    its statics) and return what it answers. The port keeps that shape, so a script that calls
    ``Effects.HasEffect(agent_id, skill_id)`` reads the same client array through the same walk.
    """

    @staticmethod
    def get_instance(agent_id: int) -> PyEffects:
        """Get the ``PyEffects`` instance for one agent (``Effect.py:6-14``)."""

        return PyEffects(agent_id)

    @staticmethod
    def DropBuff(buff_id: int) -> None:
        """Drop a buff on the player by its buff id (``Effect.py:16-25``)."""

        from .player import Player

        PyEffects(Player.GetAgentID()).DropBuff(buff_id)

    @staticmethod
    def GetBuffs(agent_id: int) -> list[BuffType]:
        """Get the active buffs on one agent (``Effect.py:27-36``)."""

        return PyEffects(agent_id).GetBuffs()

    @staticmethod
    def GetEffects(agent_id: int) -> list[EffectType]:
        """Get the active effects on one agent (``Effect.py:38-48``)."""

        return PyEffects(agent_id).GetEffects()

    @staticmethod
    def GetBuffCount(agent_id: int) -> int:
        """Count the active buffs on one agent (``Effect.py:50-60``)."""

        return PyEffects(agent_id).GetBuffCount()

    @staticmethod
    def GetEffectCount(agent_id: int) -> int:
        """Count the active effects on one agent (``Effect.py:62-72``)."""

        return PyEffects(agent_id).GetEffectCount()

    @staticmethod
    def BuffExists(agent_id: int, skill_id: int) -> bool:
        """Whether a skill's buff is on one agent (``Effect.py:74-86``)."""

        return PyEffects(agent_id).BuffExists(skill_id)

    @staticmethod
    def EffectExists(agent_id: int, skill_id: int) -> bool:
        """Whether a skill's effect is on one agent (``Effect.py:88-99``)."""

        return PyEffects(agent_id).EffectExists(skill_id)

    @staticmethod
    def HasEffect(agent_id: int, skill_id: int) -> bool:
        """Whether a skill is on one agent as either an effect or a buff (``Effect.py:101-103``).

        The source's one line, short-circuit for short-circuit: the effect array answers first.
        """

        return Effects.EffectExists(agent_id, skill_id) or Effects.BuffExists(
            agent_id, skill_id
        )

    @staticmethod
    def EffectAttributeLevel(agent_id: int, skill_id: int) -> int:
        """The attribute level of one effect, or ``0`` (``Effect.py:105-119``)."""

        for effect in PyEffects(agent_id).GetEffects():
            if effect.skill_id == skill_id:
                return effect.attribute_level
        return 0

    @staticmethod
    def GetEffectTimeRemaining(agent_id: int, skill_id: int) -> int:
        """The remaining duration of one effect, or ``0`` (``Effect.py:121-136``)."""

        for effect in PyEffects(agent_id).GetEffects():
            if effect.skill_id == skill_id:
                return effect.time_remaining
        return 0

    @staticmethod
    def GetBuffID(skill_id: int) -> int:
        """The player's buff id for one skill, or ``0`` (``Effect.py:138-149``).

        The source's docstring says ``-1`` when the buff is not found; the body returns ``0``, and
        the body is what is ported.
        """

        from .player import Player

        for buff in Effects.GetBuffs(Player.GetAgentID()):
            if buff.skill_id == skill_id:
                return buff.buff_id
        return 0

    @staticmethod
    def GetAlcoholLevel() -> int:
        """The player's alcohol level (``Effect.py:151-159``).

        Blocked: the number is native's hooked capture, which this port does not have — see
        :func:`get_alcohol_level` and ``docs/TARGET_SIDE_WORK.md``.
        """

        return PyEffects.GetAlcoholLevel()

    @staticmethod
    def GetAlcoholTimeRemaining() -> int:
        """The tracked alcohol duration remaining (``Effect.py:161-164``).

        Blocked on a finding, not on work this port can do: the member calls
        ``PyEffects.PyEffects.GetAlcoholTimeRemaining()``, and **the binding implements no such
        member** (``effects_bindings.cpp:181-183`` declares only ``GetAlcoholLevel`` and
        ``ApplyDrunkEffect``). The stub declares it (``PyEffects.pyi:41``), and native tracks no
        alcohol time at all — ``g_alcohol_level`` is a bare word with no companion timestamp
        (``effects.cpp:29-41``). A port cannot call what is not there, so the member raises and names
        the disagreement instead of inventing a clock.
        """

        raise NotImplementedError(
            "Effects.GetAlcoholTimeRemaining is declared but not built here yet: its body calls "
            "PyEffects.PyEffects.GetAlcoholTimeRemaining(), and the binding implements no such "
            "member (effects_bindings.cpp:181-183 has GetAlcoholLevel and ApplyDrunkEffect only; "
            "the stub PyEffects.pyi:41 declares it, and native tracks no alcohol time — "
            "g_alcohol_level is a bare word at effects.cpp:29). The source's member is a call on a "
            "binding member that does not exist; this port raises at the call site and names that "
            "disagreement instead of returning a wrong value."
        )

    @staticmethod
    def ApplyDrunkEffect(intensity: int, tint: int) -> None:
        """Apply the drunk post-process effect (``Effect.py:166-176``)."""

        PyEffects.ApplyDrunkEffect(intensity, tint)
