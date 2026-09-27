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
- the three members that are calls or findings: ``DropBuff`` and ``ApplyDrunkEffect`` (each gated on
  its catalog resolver, which the fake client answers for), the alcohol level, whose capture is wired
  (``effects.cpp:15,26-41``) and whose handler is checked here while the member still raises naming the
  one event shape it needs, and ``GetAlcoholTimeRemaining``, which raises naming the binding member
  that does not exist.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw import effect
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
from py4gw.game_thread.shared_block import EventKind, EventRecord

#: The agent the fixture's effects block belongs to, and a second id that has no block.
AGENT_ID = 7
OTHER_AGENT_ID = 8


def _event(arg0: int) -> EventRecord:
    """The record the observer publishes when the client calls the post-process function.

    ``sequence`` is the watched id — the intensity — and ``arg0`` is the argument the stub
    forwarded, which is what native's handler stores.
    """

    return EventRecord(
        kind=int(EventKind.EFFECT_INTENSITY),
        sequence=arg0,
        arg0=arg0,
        arg1=0,
        arg2=0,
        arg3=0,
        tick=0,
    )

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

    def test_the_alcohol_level_names_the_event_shape_it_still_needs(self) -> None:
        """``get_alcohol_level`` raises naming the observer shape its capture still needs.

        The hook, the watch list and the handler are wired (`effects.cpp:15,26-41`); what is missing
        is an event that carries the hooked call's own word arguments instead of dereferencing the
        second one — the live probe measured the level staying zero for exactly that reason.
        """

        self._use()

        for call in (Effects.GetAlcoholLevel, PyEffects.GetAlcoholLevel):
            with self.subTest(member=call.__qualname__):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                message = str(caught.exception)
                self.assertIn("payload.py:762-765", message)
                self.assertIn("effects.cpp:24-41", message)

    def test_the_alcohol_handler_stores_what_the_source_stores(self) -> None:
        """The handler is native's (`effects.cpp:26-41`): ``arg0`` is the captured level."""

        effect._reset_alcohol_state()
        try:
            self.assertEqual(effect._alcohol_level, 0)
            effect._on_post_process_effect(_event(arg0=3))
            self.assertEqual(effect._alcohol_level, 3)
            effect._on_post_process_effect(_event(arg0=5))
            self.assertEqual(effect._alcohol_level, 5)
            effect._reset_alcohol_state()
            self.assertEqual(effect._alcohol_level, 0)
        finally:
            effect._reset_alcohol_state()

    def test_the_alcohol_watch_list_is_the_levels_native_stores(self) -> None:
        """The handler's ``intensity <= 5`` test (`effects.cpp:26-41`) is the watch list here."""

        self.assertEqual(
            effect._WATCHED_INTENSITIES,
            ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)),
        )

    def test_the_connection_wires_the_capture_to_its_own_event_kind(self) -> None:
        """The capture is fed by the post-process hook, and only its kind reaches the handler."""

        source = (Path(__file__).resolve().parents[1] / "py4gw" / "client.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('_EFFECTS_HOOK = "effects.post_process_effect_func"', source)
        self.assertIn('bytes.fromhex("55 8B EC 83 EC 08")', source)
        self.assertIn("EventKind.EFFECT_INTENSITY, effect_module._on_post_process_effect", source)
        self.assertIn("effects_watch=effect_module._WATCHED_INTENSITIES", source)
        self.assertEqual(int(EventKind.EFFECT_INTENSITY), 4)
        self.assertNotEqual(
            int(EventKind.EFFECT_INTENSITY), int(EventKind.UI_MESSAGE)
        )

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
