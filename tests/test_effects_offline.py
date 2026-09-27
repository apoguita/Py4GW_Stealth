"""Offline tests for the ported ``Effects`` class and the ``PyEffects`` binding behind it.

**What is pinned.** Reforged's ``Effect.py`` (15 members) is a thin wrapper over Native's
``PyEffects`` binding (``effects_bindings.cpp:34-184``), and the binding is a walk over one array:
``Context::GetPartyEffectsArray()`` — the world's ``party_effects`` — scanned for the block whose
``agent_id`` matches (``effects_methods.cpp:29-55``). So this file drives both layers against a
fixture world whose blocks hold real ``EffectStruct``/``BuffStruct`` records, and checks the values
the binding computes rather than restates:

- the counts and the two ``*Exists`` walks, including that they are exact skill-id matches;
- ``get_effects``/``get_buffs`` field for field, with ``time_elapsed``/``time_remaining`` computed
  from the ported skill timer (``skill.cpp:39-45``) — the fixture supplies the timer, so the
  arithmetic and its ``DWORD`` wrap are both exercised;
- ``HasEffect``'s short-circuit (the effect array first, then the buff array);
- ``EffectAttributeLevel`` and ``GetEffectTimeRemaining`` picking their effect out of the list;
- ``GetBuffID`` walking the player's buffs;
- the three members that are calls or findings: ``DropBuff``, ``ApplyDrunkEffect`` (each gated on
  its catalog resolver, which the fake client answers for), and the two alcohol members, which raise
  naming what they need — the hook native installs, and the binding member that does not exist.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from py4gw.context.world_context import BuffStruct, EffectStruct
from py4gw.effect import (
    BuffType,
    EffectType,
    Effects,
    PyEffects,
    buff_count,
    buff_exists,
    drop_buff,
    effect_count,
    effect_exists,
    get_buffs,
    get_effects,
)

#: The agent the fixture's effects block belongs to, and a second id that has no block.
AGENT_ID = 7
OTHER_AGENT_ID = 8

#: The timer the fixture answers with. Both derived fields are subtractions from it, so a fixed
#: value makes them exact.
SKILL_TIMER = 5_000

#: One effect the fixture installs: a 10-second enchantment applied at timestamp 1000.
EFFECT_SKILL_ID = 1234
EFFECT_ATTRIBUTE_LEVEL = 12
EFFECT_DURATION = 10.0
EFFECT_TIMESTAMP = 1000

#: One buff: a maintained enchantment on the same agent.
BUFF_SKILL_ID = 4321
BUFF_ID = 99


def _effect(
    skill_id: int = EFFECT_SKILL_ID,
    attribute_level: int = EFFECT_ATTRIBUTE_LEVEL,
    duration: float = EFFECT_DURATION,
    timestamp: int = EFFECT_TIMESTAMP,
) -> EffectStruct:
    """One native ``Context::Effect`` record (0x18 bytes, ``skill.h:124-134``)."""

    effect = EffectStruct()
    effect.skill_id = skill_id
    effect.attribute_level = attribute_level
    effect.effect_id = 77
    effect.agent_id = AGENT_ID
    effect.duration = duration
    effect.timestamp = timestamp
    return effect


def _buff(skill_id: int = BUFF_SKILL_ID, target_agent_id: int = 0) -> BuffStruct:
    """One native ``Context::Buff`` record (0x10 bytes, ``skill.h:136-141``)."""

    buff = BuffStruct()
    buff.skill_id = skill_id
    buff.h0004 = 0
    buff.buff_id = BUFF_ID
    buff.target_agent_id = target_agent_id
    return buff


class _EffectsBlock:
    """One ``AgentEffects``-shaped block: an agent id and its two record lists."""

    def __init__(
        self,
        agent_id: int,
        effects: list[EffectStruct] | None = None,
        buffs: list[BuffStruct] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.effects = effects or []
        self.buffs = buffs or []


class _FixtureWorld:
    """A world context whose ``party_effects`` is the array the walk scans."""

    def __init__(self, blocks: list[_EffectsBlock]) -> None:
        self._blocks = blocks

    @property
    def party_effects(self) -> list[_EffectsBlock]:
        return self._blocks


class _FixtureMemoryManager:
    """The ported skill timer, answering a fixed value."""

    def __init__(self, timer: int = SKILL_TIMER) -> None:
        self._timer = timer

    def GetSkillTimer(self) -> int:
        return self._timer


class _FixtureClient:
    """A connection offering the world, the timer, the player's agent id and the two resolvers."""

    def __init__(
        self,
        blocks: list[_EffectsBlock],
        timer: int = SKILL_TIMER,
        agent_id: int = AGENT_ID,
        resolvable: tuple[str, ...] = (),
    ) -> None:
        self.world: Any = _FixtureWorld(blocks)
        self.memory_manager = _FixtureMemoryManager(timer)
        self.agent_id = agent_id
        self.resolvable = resolvable
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []

    def read_world_context(self) -> Any:
        return self.world

    def resolves(self, name: str) -> bool:
        return name in self.resolvable

    def call_function(self, name: str, form: Any, *args: int) -> Any:
        self.calls.append((name, int(form), args))
        result = mock.Mock()
        result.value = 0
        return result


class EffectsTests(unittest.TestCase):
    """The binding surface and Reforged's class, over one fixture array."""

    def setUp(self) -> None:
        self.blocks = [
            _EffectsBlock(AGENT_ID, [_effect()], [_buff()]),
            _EffectsBlock(OTHER_AGENT_ID, [], []),
        ]

    def _use(self, **kwargs: Any) -> _FixtureClient:
        client = _FixtureClient(self.blocks, **kwargs)
        patcher = mock.patch("py4gw.client._current_client", client)
        patcher.start()
        self.addCleanup(patcher.stop)
        return client

    # ── the counts and the two existence walks ────────────────────────────

    def test_counts_are_the_block_s_record_counts(self) -> None:
        """``effect_count``/``buff_count`` are the sub-arrays' sizes (``effects_bindings.cpp:49-57``)."""

        self._use()

        self.assertEqual(effect_count(AGENT_ID), 1)
        self.assertEqual(buff_count(AGENT_ID), 1)
        self.assertEqual(PyEffects(AGENT_ID).GetEffectCount(), 1)
        self.assertEqual(PyEffects(AGENT_ID).GetBuffCount(), 1)
        self.assertEqual(Effects.GetEffectCount(AGENT_ID), 1)
        self.assertEqual(Effects.GetBuffCount(AGENT_ID), 1)

    def test_an_agent_with_no_block_answers_zero_not_an_error(self) -> None:
        """The source answers null from the scan, and every member reads that as none."""

        self._use()

        self.assertEqual(effect_count(OTHER_AGENT_ID), 0)
        self.assertEqual(buff_count(OTHER_AGENT_ID), 0)
        self.assertEqual(effect_count(999), 0)
        self.assertEqual(Effects.GetEffects(999), [])
        self.assertEqual(Effects.GetBuffs(999), [])

    def test_the_existence_walks_match_the_skill_id_exactly(self) -> None:
        """Both walks compare ``skill_id`` and nothing else (``effects_bindings.cpp:59-77``)."""

        self._use()

        self.assertTrue(effect_exists(AGENT_ID, EFFECT_SKILL_ID))
        self.assertTrue(buff_exists(AGENT_ID, BUFF_SKILL_ID))
        self.assertFalse(effect_exists(AGENT_ID, EFFECT_SKILL_ID + 1))
        self.assertFalse(buff_exists(AGENT_ID, BUFF_SKILL_ID + 1))
        # The effect's id is not the buff's: each array answers only for itself.
        self.assertFalse(effect_exists(AGENT_ID, BUFF_SKILL_ID))
        self.assertFalse(buff_exists(AGENT_ID, EFFECT_SKILL_ID))
        self.assertTrue(Effects.EffectExists(AGENT_ID, EFFECT_SKILL_ID))
        self.assertTrue(Effects.BuffExists(AGENT_ID, BUFF_SKILL_ID))

    def test_has_effect_is_the_sources_short_circuit(self) -> None:
        """``EffectExists(...) or BuffExists(...)`` (``Effect.py:101-103``)."""

        self._use()

        self.assertTrue(Effects.HasEffect(AGENT_ID, EFFECT_SKILL_ID))
        self.assertTrue(Effects.HasEffect(AGENT_ID, BUFF_SKILL_ID))
        self.assertFalse(Effects.HasEffect(AGENT_ID, 2))
        self.assertFalse(Effects.HasEffect(999, EFFECT_SKILL_ID))

    # ── the value snapshots ───────────────────────────────────────────────

    def test_get_effects_copies_the_record_and_computes_both_times(self) -> None:
        """``PyEffectType`` field for field (``effects_bindings.cpp:100-109``).

        ``time_elapsed`` is ``GetSkillTimer() - timestamp`` and ``time_remaining`` is
        ``(DWORD)(duration * 1000) - time_elapsed`` (``skill.cpp:39-45``) — 4000 and 6000 for the
        fixture's 10-second effect applied at 1000 with the timer at 5000.
        """

        self._use()

        effects = get_effects(AGENT_ID)
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        self.assertIsInstance(effect, EffectType)
        self.assertEqual(effect.skill_id, EFFECT_SKILL_ID)
        self.assertEqual(effect.attribute_level, EFFECT_ATTRIBUTE_LEVEL)
        self.assertEqual(effect.effect_id, 77)
        self.assertEqual(effect.agent_id, AGENT_ID)
        self.assertEqual(effect.duration, EFFECT_DURATION)
        self.assertEqual(effect.timestamp, EFFECT_TIMESTAMP)
        self.assertEqual(effect.time_elapsed, 4000)
        self.assertEqual(effect.time_remaining, 6000)
        self.assertEqual(PyEffects(AGENT_ID).GetEffects(), effects)
        self.assertEqual(Effects.GetEffects(AGENT_ID), effects)

    def test_the_times_wrap_the_way_the_registers_do(self) -> None:
        """Both subtractions are ``DWORD``, so a timestamp in the future wraps rather than going
        negative — the source's own arithmetic, and the reason the port masks it.

        With the timer at 5000 and the effect applied at 5010, ``elapsed`` is ``2**32 - 10`` and
        ``remaining`` is ``10000 - elapsed``, which wraps back to ``10010``.
        """

        self.blocks = [_EffectsBlock(AGENT_ID, [_effect(timestamp=SKILL_TIMER + 10)], [])]
        self._use()

        effect = Effects.GetEffects(AGENT_ID)[0]
        self.assertEqual(effect.time_elapsed, (1 << 32) - 10)
        self.assertEqual(effect.time_remaining, 10010)

    def test_get_buffs_copies_the_record(self) -> None:
        """``PyBuffType`` field for field (``effects_bindings.cpp:118-124``)."""

        self._use()

        buffs = get_buffs(AGENT_ID)
        self.assertEqual(len(buffs), 1)
        buff = buffs[0]
        self.assertIsInstance(buff, BuffType)
        self.assertEqual(buff.skill_id, BUFF_SKILL_ID)
        self.assertEqual(buff.buff_id, BUFF_ID)
        self.assertEqual(buff.target_agent_id, 0)
        self.assertEqual(Effects.GetBuffs(AGENT_ID), buffs)

    def test_the_effect_scanning_members_pick_their_record(self) -> None:
        """``EffectAttributeLevel`` and ``GetEffectTimeRemaining`` (``Effect.py:105-136``)."""

        self.blocks = [
            _EffectsBlock(
                AGENT_ID,
                [
                    _effect(skill_id=1, attribute_level=3),
                    _effect(attribute_level=EFFECT_ATTRIBUTE_LEVEL),
                ],
                [],
            )
        ]
        self._use()

        self.assertEqual(Effects.EffectAttributeLevel(AGENT_ID, EFFECT_SKILL_ID), 12)
        self.assertEqual(Effects.EffectAttributeLevel(AGENT_ID, 1), 3)
        self.assertEqual(Effects.EffectAttributeLevel(AGENT_ID, 2), 0)
        self.assertEqual(Effects.GetEffectTimeRemaining(AGENT_ID, EFFECT_SKILL_ID), 6000)
        self.assertEqual(Effects.GetEffectTimeRemaining(AGENT_ID, 2), 0)

    def test_get_buff_id_walks_the_player_s_buffs(self) -> None:
        """``GetBuffID`` answers the buff id, or ``0`` (``Effect.py:138-149``)."""

        self._use()

        with mock.patch("py4gw.player.Player.GetAgentID", return_value=AGENT_ID):
            self.assertEqual(Effects.GetBuffID(BUFF_SKILL_ID), BUFF_ID)
            self.assertEqual(Effects.GetBuffID(1), 0)

    # ── the wrapper itself ────────────────────────────────────────────────

    def test_get_instance_is_the_binding_object(self) -> None:
        """``get_instance`` returns ``PyEffects(agent_id)`` (``Effect.py:6-14``)."""

        instance = Effects.get_instance(AGENT_ID)
        self.assertIsInstance(instance, PyEffects)
        self.assertEqual(instance.agent_id, AGENT_ID)

    def test_a_missing_world_context_answers_none(self) -> None:
        """No world context is no effects block, which every member reads as none."""

        client = _FixtureClient([])
        client.world = None
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(effect_count(AGENT_ID), 0)
            self.assertEqual(buff_count(AGENT_ID), 0)
            self.assertFalse(effect_exists(AGENT_ID, EFFECT_SKILL_ID))
            self.assertFalse(Effects.HasEffect(AGENT_ID, EFFECT_SKILL_ID))

    # ── the calls and the two findings ────────────────────────────────────

    def test_drop_buff_is_a_one_word_call_and_is_gated_on_its_resolver(self) -> None:
        """``GW::effects::DropBuff`` (``effects_methods.cpp:65-72``)."""

        client = self._use(resolvable=())
        self.assertFalse(drop_buff(BUFF_ID))
        self.assertEqual(client.calls, [])

        client.resolvable = ("effects.drop_buff_func",)
        self.assertTrue(drop_buff(BUFF_ID))
        self.assertEqual(len(client.calls), 1)
        name, form, args = client.calls[0]
        self.assertEqual(name, "effects.drop_buff_func")
        self.assertEqual(args, (BUFF_ID,))

    def test_drop_buff_on_the_class_calls_the_player_s_instance(self) -> None:
        """``Effects.DropBuff`` uses the player's agent id (``Effect.py:16-25``)."""

        client = self._use(resolvable=("effects.drop_buff_func",))

        with mock.patch("py4gw.player.Player.GetAgentID", return_value=AGENT_ID):
            Effects.DropBuff(BUFF_ID)

        self.assertEqual(
            [call[2] for call in client.calls], [(BUFF_ID,)]
        )

    def test_apply_drunk_effect_is_two_words(self) -> None:
        """``GW::effects::GetDrunkAf(intensity, tint)`` (``effects_methods.cpp:23-27``)."""

        client = self._use(resolvable=("effects.post_process_effect_func",))

        Effects.ApplyDrunkEffect(3, 7)

        self.assertEqual(len(client.calls), 1)
        name, _, args = client.calls[0]
        self.assertEqual(name, "effects.post_process_effect_func")
        self.assertEqual(args, (3, 7))

    def test_the_alcohol_level_names_the_hook_it_needs(self) -> None:
        """``get_alcohol_level`` is native's hooked capture (`effects.cpp:24-41`)."""

        self._use()

        for call in (Effects.GetAlcoholLevel, PyEffects.GetAlcoholLevel):
            with self.subTest(member=call.__qualname__):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                message = str(caught.exception)
                self.assertIn("post-process function", message)
                self.assertIn("effects.cpp:24-41", message)

    def test_the_alcohol_time_names_the_binding_member_that_does_not_exist(self) -> None:
        """``GetAlcoholTimeRemaining`` calls a binding member the binding does not implement."""

        self._use()

        with self.assertRaises(NotImplementedError) as caught:
            Effects.GetAlcoholTimeRemaining()
        message = str(caught.exception)
        self.assertIn("effects_bindings.cpp:181-183", message)
        self.assertIn("PyEffects.pyi:41", message)
        self.assertFalse(hasattr(PyEffects, "GetAlcoholTimeRemaining"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
