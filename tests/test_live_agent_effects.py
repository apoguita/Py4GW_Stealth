"""Live checks for the agent-name binding, the effects walk and the skill timer.

**What this suite is for.** Three read paths landed on 2026-09-26 with only offline evidence:
`PyAgent.get_agent_enc_name` (and the seven `Agent` members over it), the whole `Effects` class over
`WorldContext.party_effects`, and `PY4GW::MemoryManager.GetSkillTimer`. This suite runs them against
a **real connection** — `py4gw.connect()`, so the connection's own wiring, the GW.dat string-table
decode and the capability layer are all in play — which is what
`tests/probe_agent_effects_live.py` deliberately does not do (that probe reads directly, without
elevation and without connecting).

**It performs no game action.** Every member called here reads. The two action members of `Effects`
are **not** called — `DropBuff` drops a real buff and `ApplyDrunkEffect` changes the character's
post-process — so the suite only checks that their resolvers are in the catalog and says so. Neither
is a write this suite is authorised to make.

**Two members are deliberately two-call.** `Agent.GetNameByID` decodes through
`internals.string_table.decode`, which answers `""` on the first call for a string it has not cached
while the decode runs, and the text on the next — Reforged's own shape, not a limitation of the read.
The name tests here allow that: they ask, and if the answer is empty they ask again, bounded.

Run it from an elevated shell, one suite at a time::

    pwsh -NoProfile -File tools\\run_live_suites.ps1 tests.test_live_agent_effects

or directly::

    python -m unittest tests.test_live_agent_effects -v
"""

from __future__ import annotations

import time
import unittest

import py4gw

from py4gw import Win32
from py4gw.agent import Agent
from py4gw.context.text_parser_context import TextParser
from py4gw.effect import Effects, PyEffects
from py4gw.player import Player

#: How many agents to sample when an id is needed. The walks are one remote read per agent.
SAMPLE = 8

#: The weapon names the source's own lists carry (``Agent.py:1351`` and ``1390``), which is what
#: ``IsMartial``/``IsMelee`` compare against.
MARTIAL_WEAPONS = ("Bow", "Axe", "Hammer", "Daggers", "Scythe", "Spear", "Sword")
MELEE_WEAPONS = ("Axe", "Hammer", "Daggers", "Scythe", "Sword")


#: How long the GW.dat string table may take to fill before a table-backed name test gives up.
#: The first decode starts the load; one warm-up covers every later name, so this is spent once.
TABLE_WAIT_SECONDS = 20.0

#: How many agents a name test looks at. Every step is a remote read, and the sample only has to
#: contain one of each form.
NAME_SAMPLE = 40


class LiveAgentEffectsTests(unittest.TestCase):
    """The name binding, the effects walk and the skill timer, against the running client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Connect to the first discovered client, with the capability layer.

        The full connection is required rather than the read-only one: the decode behind
        ``Agent.GetNameByID`` loads the string table out of GW.dat, and that read is a call into the
        client on its own thread.
        """

        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        if not win32.is_elevated():
            raise unittest.SkipTest(
                "This suite connects to the client, reading GW.dat through it, and connecting "
                "requires an elevated controller. Run it from an elevated shell. "
                "(tests/probe_agent_effects_live.py reads the same members without elevation, "
                "except the decode.)"
            )
        cls.client = py4gw.connect(clients[0])

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the connection opened for the live checks."""

        py4gw.disconnect()

    # ── helpers ───────────────────────────────────────────────────────────

    def _view(self):
        """Return the source-shaped agent-array view, or skip when the client has none."""

        context = self.client.agent_array.get_context()
        if context is None:
            self.skipTest("The connected client has no active AgentContext.")
        return context

    def _agent_ids(self) -> list[int]:
        agents = self._view().GetAgentArray()
        if not agents:
            self.skipTest("The connected client has no current agents.")
        return [int(agent_id) for agent_id in agents]

    def _decoded_name(self, agent_id: int) -> str:
        """Ask for a name once.

        The decode answers `""` while the string table loads, and that wait is the same for every
        name — so it is spent once in :meth:`_warm_string_table`, not retried per agent.
        """

        return Agent.GetNameByID(agent_id)

    def _sample_ids(self) -> list[int]:
        """The first ``NAME_SAMPLE`` living agents, which is where names live."""

        return self._agent_ids()[:NAME_SAMPLE]

    def _warm_string_table(self) -> tuple[int, str]:
        """Wait, bounded, for the GW.dat table to answer one non-player name.

        A player's encoded name carries its text inline and needs no table; every other name is
        string-table indices, and the table is filled by a call into the client the first time a
        decode is asked for one. This asks for the same few candidates until one answers, which
        covers the whole suite's table-backed half in one wait.
        """

        from py4gw.internals import string_table
        from py4gw.internals.string_table import decode as decode_raw

        candidates: list[tuple[int, bytes]] = []
        for agent_id in self._sample_ids():
            encoded = Agent.GetEncNameByID(agent_id)
            if encoded and encoded[:2] != [0xA9, 0x0B]:
                candidates.append((agent_id, bytes(encoded)))
            if len(candidates) == 6:
                break
        if not candidates:
            return 0, ""

        deadline = time.time() + TABLE_WAIT_SECONDS
        while time.time() < deadline:
            for agent_id, raw in candidates:
                text = decode_raw(raw)
                if text:
                    return agent_id, text
            time.sleep(0.25)
        self.table_status = string_table._last_load_status
        return 0, ""

    # ── the array view, through the real connection ───────────────────────

    def test_the_view_is_the_clients_own_agent_array(self) -> None:
        """The ported view reads the array the client keeps (``AgentContext.py:1405-1415``)."""

        view = self._view()
        header = view.agent_array
        size = int(header.m_size)
        capacity = int(header.m_capacity)

        self.assertGreater(capacity, 0)
        self.assertGreater(size, 0)
        self.assertLessEqual(size, capacity)
        self.assertGreater(int(header.m_buffer), 0x10000)

        records = view.raw_agents
        self.assertEqual(len(records), size)
        present = [record for record in records if record is not None]
        self.assertTrue(all(int(record.agent_id) > 0 for record in present))

        from py4gw.agent_array import AgentArray as AgentArrayClass

        self.assertEqual(view.GetAgentArray(), AgentArrayClass.GetAgentArray())
        print(
            "Live AgentArray view: "
            f"buffer=0x{int(header.m_buffer):08X}, size={size}, capacity={capacity}, "
            f"non_null={len(present)}"
        )

    def test_the_category_lists_come_from_the_view(self) -> None:
        """Every category the source fills answers, and its ids come from the array.

        This is the gate the point-of-use ``AccAgentContext`` refresh exists for: without it the
        class-level cache is ``None`` on a fresh connection and every list is empty.
        """

        view = self._view()
        agents = view.GetAgentArray()
        self.assertTrue(agents, "the source's all-agents list is empty")

        for name, category in (
            ("ally", view.GetAllyArray()),
            ("neutral", view.GetNeutralArray()),
            ("enemy", view.GetEnemyArray()),
            ("spirit_pet", view.GetSpiritPetArray()),
            ("minion", view.GetMinionArray()),
            ("npc_minipet", view.GetNPCMinipetArray()),
            ("item", view.GetItemAgentArray()),
            ("owned_item", view.GetOwnedItemAgentArray()),
            ("gadget", view.GetGadgetAgentArray()),
            ("dead_ally", view.GetDeadAllyArray()),
            ("dead_enemy", view.GetDeadEnemyArray()),
        ):
            with self.subTest(category=name):
                self.assertTrue(set(category) <= set(agents))

        count = (
            len(view.GetAllyArray())
            + len(view.GetNeutralArray())
            + len(view.GetEnemyArray())
        )
        print(
            "Live AgentArray categories: "
            f"all={len(agents)}, living-by-allegiance={count}, "
            f"items={len(view.GetItemAgentArray())}, gadgets={len(view.GetGadgetAgentArray())}"
        )

    def test_one_record_answers_through_the_sources_chain(self) -> None:
        """``Agent.GetAgentByID`` -> ``AgentArray.GetAgentByID`` -> the view."""

        agent_id = self._agent_ids()[0]
        through_agent = Agent.GetAgentByID(agent_id)
        self.assertIsNotNone(through_agent)
        assert through_agent is not None
        self.assertEqual(int(through_agent.agent_id), agent_id)
        self.assertIs(self._view().GetAgentByID(agent_id), through_agent)
        print(
            "Live agent record: "
            f"id={agent_id}, type=0x{int(through_agent.type):X}, "
            f"position={through_agent.position}"
        )

    # ── the name binding ──────────────────────────────────────────────────

    def test_encoded_names_are_the_clients_own_bytes(self) -> None:
        """``Agent.GetEncNameByID`` returns the binding's bytes, terminator included.

        The binding copies ``(n + 1) * sizeof(wchar_t)`` bytes (``agent_bindings.cpp:217-223``), so
        the last two entries of a non-empty answer are the terminator.
        """

        checked = 0
        for agent_id in self._agent_ids()[:SAMPLE]:
            encoded = Agent.GetEncNameByID(agent_id)
            if not encoded:
                continue
            with self.subTest(agent_id=agent_id):
                self.assertTrue(all(isinstance(value, int) for value in encoded))
                self.assertTrue(all(0 <= value <= 0xFF for value in encoded))
                self.assertEqual(len(encoded) % 2, 0, "UTF-16 code units come in pairs")
                self.assertEqual(encoded[-2:], [0, 0], "the copy includes the terminator")
                self.assertEqual(Agent.RequestName, Agent.GetNameByID)
            checked += 1
            if checked == 3:
                break

        if not checked:
            self.skipTest("No agent in this zone answered with an encoded name.")
        print(f"Live encoded names: {checked} agent(s) carried a name")

    def test_the_connection_prepares_the_table_without_reading_it_all(self) -> None:
        """The table is read a file at a time, on demand — not the client's whole table.

        Reforged's first frame refreshes the ``TextParser`` context and that refresh ends by loading
        **every** string file of the language (``TextContext.py:152-155``) — 99 of them in this
        client, which in-process is one pass over its own memory. Externally each file is a GW.dat
        chain through the command ring, measured at ~2 s for the first one, and a name needs exactly
        one of them: files are indexed by entry (``entries_per_file`` each), and an encoded name
        carries its entry index. So this port's trigger records the language and the file an entry
        lives in is read when a decode asks for it.

        The assertions are deliberately order-independent, because the tests before this one have
        already asked for names: the whole-table flag is never set, the trigger has run, and the
        files read stay far below the language's own file count — which is read from the client
        rather than assumed.
        """

        from py4gw.internals import string_table

        self.assertFalse(
            string_table._string_table_loaded,
            "the whole table should never be read here",
        )
        self.assertTrue(
            TextParser._string_table_triggered,
            "the table trigger has not run: the context refresh never happened",
        )

        context = self.client.read_text_parser()
        self.assertIsNotNone(context, "the connected client has no TextParser context")
        assert context is not None
        file_count = int(context.language_slots[int(context.language_id)].slot_count)
        self.assertGreater(file_count, 1)

        agent_id, name = self._warm_string_table()
        if not name:
            self.skipTest(
                "no table-backed name decoded; "
                f"table status: {string_table._last_load_status!r}"
            )

        self.assertGreater(len(string_table._string_table), 0)
        self.assertLess(
            len(string_table._loaded_slots),
            file_count,
            "names should read the file an entry lives in, not every file: "
            f"{string_table._last_load_status}",
        )
        print(
            "Live string table: read on demand — "
            f"{len(string_table._loaded_slots)} of the client's {file_count} files read for the "
            f"names this suite asked for; {len(string_table._string_table)} entries held; "
            f"status={string_table._last_load_status!r}"
        )

    def test_names_decode_to_text(self) -> None:
        """``Agent.GetNameByID`` decodes real names, and ``IsNameReady`` agrees.

        Two forms exist and each is checked where it can be: a **player** name carries its text
        inline behind the ``0xBA9`` prefix and decodes with no string table at all, while a name for
        anything else is string-table indices and needs the table GW.dat fills — that one is the
        reason this suite needs the full connection, and it is where NPC, gadget and item names
        become text.
        """

        players = self._collect_decoded(player_only=True, limit=3)
        if players:
            for agent_id, name in players:
                with self.subTest(agent_id=agent_id, form="player"):
                    self.assertTrue(Agent.IsNameReady(agent_id))
                    self.assertEqual(Agent.GetNameByID(agent_id), name)
        else:
            print(
                "Live names: no other player in this district to read an inline name from "
                "(the own character's name is checked by test_player_get_name_is_the_sources_call)"
            )

        agent_id, name = self._warm_string_table()
        if not name:
            from py4gw.internals import string_table

            self.skipTest(
                f"No table-backed name decoded within {TABLE_WAIT_SECONDS:.0f} s: that half needs "
                "the string table GW.dat fills, which is a call into the client — run this again "
                "after a moment in game. "
                f"(table status: {string_table._last_load_status!r})"
            )
        with self.subTest(agent_id=agent_id, form="table"):
            self.assertTrue(Agent.IsNameReady(agent_id))
            self.assertEqual(Agent.GetNameByID(agent_id), name)

        table_backed = [
            self._decoded_name(sample) for sample in self._sample_ids()[:8]
        ]
        decoded = [value for value in table_backed if value]
        print(
            f"Live decoded names: players={players}, table-backed first={agent_id}:{name!r}, "
            f"decoded {len(decoded)} of {len(table_backed)} sampled agents"
        )

    def _collect_decoded(self, player_only: bool, limit: int) -> list[tuple[int, str]]:
        """Return up to ``limit`` agents whose name decodes, with the names.

        ``player_only`` selects the inline ``0xBA9`` form (which needs no string table); otherwise it
        selects a name that is string-table indices. No retry: the inline form decodes on the first
        ask, and the table-backed form is warmed once by :meth:`_warm_string_table`.
        """

        found: list[tuple[int, str]] = []
        own_agent = int(Player.GetAgentID())
        for agent_id in self._sample_ids():
            if len(found) == limit:
                break
            if agent_id == own_agent and not player_only:
                continue
            encoded = Agent.GetEncNameByID(agent_id)
            if not encoded:
                continue
            if (encoded[:2] == [0xA9, 0x0B]) != player_only:
                continue
            name = self._decoded_name(agent_id)
            if name:
                found.append((agent_id, name))
        return found

    def test_the_readable_encoded_string_is_the_escape_form(self) -> None:
        """``GetEncNameStrByID`` escapes non-printable code points (``Agent.py:161-179``)."""

        for agent_id in self._agent_ids()[:SAMPLE]:
            encoded = Agent.GetEncNameByID(agent_id)
            if not encoded:
                continue
            literal = Agent.GetEncNameStrByID(agent_id, literal=True)
            escaped = Agent.GetEncNameStrByID(agent_id)
            with self.subTest(agent_id=agent_id):
                self.assertTrue(literal or escaped)
                self.assertEqual(escaped, literal.replace("\\", "\\\\"))
            print(f"Live encoded string: id={agent_id}, literal={literal[:40]!r}")
            return
        self.skipTest("No agent in this zone answered with an encoded name.")

    def test_the_names_can_be_looked_up_again_by_text(self) -> None:
        """``GetAgentIDByName``/``GetAgentIDByEncString`` find the agent they came from."""

        for agent_id in self._agent_ids()[:SAMPLE]:
            literal = Agent.GetEncNameStrByID(agent_id, literal=True)
            if not literal:
                continue
            with self.subTest(agent_id=agent_id):
                self.assertEqual(Agent.GetAgentIDByEncString(literal), agent_id)
                model_id = Agent.GetModelIDByEncString(literal)
                self.assertEqual(model_id, Agent.GetModelID(agent_id))
            name = self._decoded_name(agent_id)
            if name:
                with self.subTest(agent_id=agent_id, member="GetAgentIDByName"):
                    self.assertEqual(Agent.GetAgentIDByName(name.lower()), agent_id)
            print(f"Live name lookups: id={agent_id}, model={Agent.GetModelID(agent_id)}")
            return
        self.skipTest("No agent in this zone answered with an encoded name.")

    def test_player_get_name_is_the_sources_call(self) -> None:
        """``Player.GetName`` is ``Agent.GetNameByID(Player.GetAgentID())`` again.

        The character's own name is the inline ``0xBA9`` form, so it decodes with no string table
        and needs no wait.
        """

        agent_id = int(Player.GetAgentID())
        self.assertGreater(agent_id, 0, "the player has no agent id in this state")

        name = Player.GetName()
        self.assertTrue(name, "the player's own name did not decode")
        self.assertEqual(name, Agent.GetNameByID(agent_id))
        print(f"Live player name: {name!r} (agent {agent_id})")

    # ── the skill timer ───────────────────────────────────────────────────

    def test_the_skill_timer_is_the_clients_clock(self) -> None:
        """``MemoryManager.GetSkillTimer`` advances, and the window handle is not null."""

        manager = self.client.memory_manager
        first = manager.GetSkillTimer()
        time.sleep(0.25)
        second = manager.GetSkillTimer()

        self.assertGreater(first, 0)
        advanced = (second - first) & 0xFFFFFFFF
        self.assertGreaterEqual(advanced, 200)
        self.assertLess(advanced, 4000)
        self.assertNotEqual(manager.GetGWWindowHandle(), 0)
        self.assertGreater(manager.GetGWWindowHandle(), 0x10000)

        print(
            "Live skill timer: "
            f"{first} -> {second} (+{advanced} ms), window=0x{manager.GetGWWindowHandle():X}"
        )

    def test_the_slot_recharge_is_the_timer_subtraction(self) -> None:
        """A skillbar slot's ``get_recharge`` is ``recharge - GetSkillTimer()`` (``skill.cpp:20-25``)."""

        from py4gw.skillbar import SkillBar

        manager = self.client.memory_manager
        reported = 0
        for slot_index in range(1, 9):
            slot = SkillBar.GetSkillData(slot_index)
            raw = int(slot.recharge)
            recharge = slot.get_recharge
            with self.subTest(slot=slot_index):
                self.assertEqual(recharge, 0 if raw == 0 else (raw - manager.GetSkillTimer()) & 0xFFFFFFFF)
            if raw:
                reported += 1
        print(f"Live slot recharges: {reported} of 8 slots carried a recharge timestamp")

    # ── the effects walk ──────────────────────────────────────────────────

    def test_the_effects_array_is_the_party_effects_array(self) -> None:
        """The walk's source array is readable, and the walk agrees with it block for block.

        An empty array is a real answer here — the client builds a block per agent that has an
        effect or a buff — so this reports what it found rather than failing when the character has
        nothing running.
        """

        world = self.client.read_world_context()
        self.assertIsNotNone(world, "the connected client has no world context")
        assert world is not None

        header = world.party_effects_array
        blocks = world.party_effects or []
        print(
            "Live party effects array: "
            f"buffer=0x{int(header.m_buffer):08X}, size={int(header.m_size)}, "
            f"capacity={int(header.m_capacity)}, blocks_read={len(blocks)}"
        )

        for block in blocks:
            agent_id = int(block.agent_id)
            with self.subTest(agent_id=agent_id):
                self.assertEqual(Effects.GetEffectCount(agent_id), len(block.effects))
                self.assertEqual(Effects.GetBuffCount(agent_id), len(block.buffs))
                self.assertEqual(len(Effects.GetEffects(agent_id)), len(block.effects))
                self.assertEqual(len(Effects.GetBuffs(agent_id)), len(block.buffs))

    def test_the_effect_snapshot_fields_are_the_records(self) -> None:
        """Every effect answers the record's fields plus the two computed times."""

        world = self.client.read_world_context()
        assert world is not None
        blocks = [block for block in (world.party_effects or []) if block.effects]
        if not blocks:
            self.skipTest(
                "No party member has an effect running, so there is nothing to compare — "
                "put a maintained enchantment or any buff up and run this again."
            )

        block = blocks[0]
        agent_id = int(block.agent_id)
        record = block.effects[0]
        effect = Effects.GetEffects(agent_id)[0]

        self.assertEqual(effect.skill_id, int(record.skill_id))
        self.assertEqual(effect.attribute_level, int(record.attribute_level))
        self.assertEqual(effect.effect_id, int(record.effect_id))
        self.assertEqual(effect.agent_id, int(record.agent_id))
        self.assertEqual(effect.duration, float(record.duration))
        self.assertEqual(effect.timestamp, int(record.timestamp))

        timer = self.client.memory_manager.GetSkillTimer()
        self.assertEqual(effect.time_elapsed, (timer - int(record.timestamp)) & 0xFFFFFFFF)
        expected_remaining = (
            (int(float(record.duration) * 1000.0) & 0xFFFFFFFF) - effect.time_elapsed
        ) & 0xFFFFFFFF
        self.assertEqual(effect.time_remaining, expected_remaining)

        self.assertTrue(Effects.EffectExists(agent_id, int(record.skill_id)))
        self.assertTrue(Effects.HasEffect(agent_id, int(record.skill_id)))
        self.assertEqual(
            Effects.EffectAttributeLevel(agent_id, int(record.skill_id)),
            int(record.attribute_level),
        )
        self.assertEqual(
            Effects.GetEffectTimeRemaining(agent_id, int(record.skill_id)),
            effect.time_remaining,
        )
        print(
            "Live effect: "
            f"agent={agent_id}, skill={effect.skill_id}, attribute={effect.attribute_level}, "
            f"elapsed={effect.time_elapsed} ms, remaining={effect.time_remaining} ms"
        )

    def test_the_buff_members_answer_from_the_buff_array(self) -> None:
        """``GetBuffs``/``BuffExists``/``GetBuffID`` over the same walk's buff half."""

        world = self.client.read_world_context()
        assert world is not None
        blocks = [block for block in (world.party_effects or []) if block.buffs]
        if not blocks:
            self.skipTest(
                "No party member has a buff running, so there is nothing to compare — "
                "apply any buff and run this again."
            )

        block = blocks[0]
        agent_id = int(block.agent_id)
        record = block.buffs[0]
        buff = Effects.GetBuffs(agent_id)[0]

        self.assertEqual(buff.skill_id, int(record.skill_id))
        self.assertEqual(buff.buff_id, int(record.buff_id))
        self.assertEqual(buff.target_agent_id, int(record.target_agent_id))
        self.assertTrue(Effects.BuffExists(agent_id, int(record.skill_id)))
        self.assertTrue(Effects.HasEffect(agent_id, int(record.skill_id)))

        player_id = int(Player.GetAgentID())
        player_buffs = Effects.GetBuffs(player_id)
        for player_buff in player_buffs:
            with self.subTest(skill=player_buff.skill_id):
                self.assertEqual(Effects.GetBuffID(player_buff.skill_id), player_buff.buff_id)
        print(
            "Live buff: "
            f"agent={agent_id}, skill={buff.skill_id}, buff_id={buff.buff_id}, "
            f"player_buffs={len(player_buffs)}"
        )

    def test_get_instance_holds_the_agent_id(self) -> None:
        """``Effects.get_instance`` is the binding object (``Effect.py:6-14``)."""

        instance = Effects.get_instance(999)
        self.assertIsInstance(instance, PyEffects)
        self.assertEqual(instance.agent_id, 999)
        self.assertEqual(instance.GetEffectCount(), 0)
        self.assertEqual(instance.GetBuffs(), [])

    def test_the_alcohol_members_report_what_they_need(self) -> None:
        """The two members that cannot answer say so, and neither is a call this suite makes."""

        with self.assertRaises(NotImplementedError) as alcohol:
            Effects.GetAlcoholLevel()
        self.assertIn("post-process function", str(alcohol.exception))

        with self.assertRaises(NotImplementedError) as alcohol_time:
            Effects.GetAlcoholTimeRemaining()
        self.assertIn("effects_bindings.cpp:181-183", str(alcohol_time.exception))

    def test_the_effects_resolvers_resolve_and_the_actions_are_not_run(self) -> None:
        """Both of ``Effects``' calls have their catalog entry; neither is issued here.

        ``DropBuff`` drops a real buff on the character and ``ApplyDrunkEffect`` drives the client's
        drunk post-process. Both are game actions, so this suite checks only that the resolvers the
        members gate on are present — the call forms themselves are exercised by the port's
        ``Player`` action suite, which is written to be run deliberately.
        """

        self.assertTrue(
            self.client.resolves("effects.drop_buff_func"),
            "effects.drop_buff_func does not resolve on this build",
        )
        self.assertTrue(
            self.client.resolves("effects.post_process_effect_func"),
            "effects.post_process_effect_func does not resolve on this build",
        )
        print(
            "Live effects resolvers: drop_buff_func and post_process_effect_func both resolve; "
            "DropBuff/ApplyDrunkEffect not called (game actions)"
        )

    # ── the two members the effects port unblocked ────────────────────────

    def test_martial_and_melee_follow_the_weapon_table(self) -> None:
        """``IsMartial``/``IsMelee`` are the source's body: the effect first, then the pet, then the
        weapon name (``Agent.py:1340-1355`` and ``1381-1394``).

        The expectation is built in that order, because a live agent with Illusionary Weaponry up
        answers ``False`` whatever it is holding — which is what the first run of this suite caught
        when the expectation skipped that branch.
        """

        from py4gw.skill import Skill

        # The source's constant is ``0`` and *filled in on first use* — ``IsMartial`` and ``IsMelee``
        # write ``Skill.GetID("Illusionary_Weaponry")`` into it (``Agent.py:1340-1342``). Asking for
        # the id before either has run compares the declared zero against the table's 33, so the walk
        # below runs first and the memo is checked after it.
        checked = 0
        for agent_id in self._agent_ids()[: SAMPLE * 2]:
            weapon_type, weapon_name = Agent.GetWeaponType(agent_id)
            if int(weapon_type) == 0:
                continue
            illusionary_weaponry = Effects.HasEffect(
                agent_id, Skill.GetID("Illusionary_Weaponry")
            )
            is_pet = Agent.IsPet(agent_id)
            with self.subTest(agent_id=agent_id, weapon=weapon_name):
                expected_martial = (
                    False
                    if illusionary_weaponry
                    else (is_pet or weapon_name in MARTIAL_WEAPONS)
                )
                expected_melee = (
                    False
                    if illusionary_weaponry
                    else (is_pet or weapon_name in MELEE_WEAPONS)
                )
                self.assertEqual(Agent.IsMartial(agent_id), expected_martial)
                self.assertEqual(Agent.IsMelee(agent_id), expected_melee)
            checked += 1
            if checked == 4:
                break

        self.assertEqual(
            Agent.ILLUSIONARY_WEAPONRY_ID, Skill.GetID("Illusionary_Weaponry")
        )
        if not checked:
            self.skipTest(
                "No sampled agent had a weapon in hand, so nothing could be compared — "
                "equip a weapon and run this again."
            )
        print(f"Live martial/melee: {checked} armed agent(s) matched the weapon table")


if __name__ == "__main__":
    unittest.main(verbosity=2)
