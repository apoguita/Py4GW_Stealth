"""Live Guild Wars tests for the ported ``Skill``, ``SkillBar`` and ``Utils`` reads.

**What this suite adds.** The `Skill` and `SkillBar` ports were verified offline against ``Gw.exe``
on disk, which is the same image the client runs but not the same *process*. This suite does the two
things only a running client can do: it resolves the patterns inside the loaded module (where the
addresses are rebased and the sections are the loader's, not the file's), and it cross-checks every
member it can against **an independent route to the same value** — the world context's skillbar
record, the world and account bitsets, the skill constant record the member claims to read.

**It writes nothing.** The connection is the read-only one (``game_thread=False``): no hook, no
patch, no call into the client, and the suite hashes the client's whole code section before and after
to show it. Elevation is still required, because ``ConnectedClient`` asserts it for every connection.

Run it from an **elevated** shell with Guild Wars running in a loaded map::

    python -m unittest tests.test_live_skill -v
"""

from __future__ import annotations

import hashlib
import unittest
from typing import Any

import py4gw
from py4gw import Win32
from py4gw.agent import Agent
from py4gw.player import Player
from py4gw.py4gwcorelib_src.utils import Utils
from py4gw.skill import Skill
from py4gw.skillbar import SKILL_TOOLTIP_PAYLOAD_LENGTH, SkillBar

#: Skills whose data is stable across builds, used as the live spot checks.
HEALING_SIGNET = 1
POWER_BLOCK = 5
METEOR_SHOWER = 192
BLOOD_RENEWAL = 115
ILLUSIONARY_WEAPONRY = 33


class SkillLiveTests(unittest.TestCase):
    """The ported reads, against the running client."""

    client: Any
    pid: int
    text_before: tuple[str, int]

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        if not win32.is_elevated():
            raise unittest.SkipTest(
                "The controller must be elevated: connecting asserts it, and the write "
                "rights are denied without it. Run this suite from an elevated shell."
            )

        cls.text_before = cls._text_digest(win32, cls.pid)
        cls.client = py4gw.connect(clients[0], game_thread=False)
        print(f"--- connected read-only to pid {cls.pid} ---")

    @classmethod
    def tearDownClass(cls) -> None:
        py4gw.disconnect()
        after = cls._text_digest(Win32(), cls.pid)
        print(
            f"--- code section after disconnect: {after[0][:16]}… ({after[1]:#x} bytes); "
            f"before: {cls.text_before[0][:16]}… ---"
        )
        if after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the read-only connection changed the client's code section: "
                f"{cls.text_before[0]} -> {after[0]}"
            )

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        """Hash the client's whole code section, read-only."""

        from py4gw.memory import ProcessMemoryReader
        from py4gw.scanner import RemoteScanner

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            scanner.initialize()
            section = scanner.get_section_range("text")
            digest = hashlib.sha256()
            address = section.start
            while address < section.end:
                size = min(0x10000, section.end - address)
                digest.update(reader.read(address, size))
                address += size
            return digest.hexdigest(), section.end - section.start

    # -- the skill constant table ------------------------------------------

    def test_the_table_resolves_live_and_indexes_like_the_client(self) -> None:
        """The pattern answers inside the loaded module, and record ``i`` is skill ``i``."""

        constants = self.client.skill_constants
        address = constants.resolve_address()
        self.assertIsNotNone(address, "skillbar.skill_array_addr did not resolve")
        print(f"skill table at 0x{int(address or 0):08X}")

        for skill_id in range(12):
            with self.subTest(skill_id=skill_id):
                record = self.client.read_skill(skill_id)
                self.assertIsNotNone(record, "the table answered no record")
                assert record is not None
                self.assertEqual(int(record.skill_id), skill_id)

    def test_known_skills_read_their_known_data(self) -> None:
        """Values checked against the game's own data, live."""

        signet = self.client.read_skill(HEALING_SIGNET)
        assert signet is not None
        self.assertEqual(signet.type, 7)  # Signet
        self.assertEqual(signet.GetEnergyCost(), 0)
        self.assertEqual(float(signet.activation), 2.0)
        self.assertEqual(int(signet.recharge), 4)

        power_block = self.client.read_skill(POWER_BLOCK)
        assert power_block is not None
        self.assertTrue(power_block.IsElite())
        self.assertEqual(power_block.GetEnergyCost(), 15)

        meteor = self.client.read_skill(METEOR_SHOWER)
        assert meteor is not None
        self.assertEqual(meteor.GetEnergyCost(), 25)
        self.assertEqual(int(meteor.recharge), 60)
        self.assertEqual(int(meteor.overcast), 10)

        renewal = self.client.read_skill(BLOOD_RENEWAL)
        assert renewal is not None
        self.assertEqual(renewal.GetEnergyCost(), 1)
        self.assertEqual(int(renewal.health_cost), 15)

    def test_the_members_answer_from_the_record_they_read(self) -> None:
        """Each member is cross-checked against the record it claims to read."""

        self.assertEqual(Skill.GetType(HEALING_SIGNET)[1], "Signet")
        self.assertEqual(Skill.GetType(POWER_BLOCK)[1], "Spell")
        self.assertTrue(Skill.Flags.IsElite(POWER_BLOCK))
        self.assertEqual(Skill.Data.GetEnergyCost(METEOR_SHOWER), 25)
        self.assertEqual(Skill.Data.GetHealthCost(BLOOD_RENEWAL), 15)
        self.assertEqual(Skill.GetName(HEALING_SIGNET), "Healing_Signet")
        self.assertEqual(Skill.GetID("Illusionary_Weaponry"), ILLUSIONARY_WEAPONRY)

        for skill_id in (HEALING_SIGNET, POWER_BLOCK, METEOR_SHOWER, BLOOD_RENEWAL):
            with self.subTest(skill_id=skill_id):
                record = self.client.read_skill(skill_id)
                assert record is not None
                self.assertEqual(
                    Skill.ExtraData.GetIDPvP(skill_id), int(record.skill_id_pvp)
                )
                self.assertEqual(Skill.Data.GetRecharge(skill_id), int(record.recharge))
                self.assertEqual(Skill.Data.GetOvercast(skill_id), (
                    int(record.overcast) if int(record.special) & 0x1 else 0
                ))

    # -- the skillbar ------------------------------------------------------

    def _player_skillbar(self) -> Any:
        """The player's own skillbar record from the world context, or ``None``."""

        agent_id = int(Player.GetAgentID())
        if not agent_id:
            return None
        world = self.client.read_world_context()
        if world is None:
            return None
        for skillbar in world.skillbars or []:
            if int(skillbar.agent_id) == agent_id:
                return skillbar
        return None

    def test_the_skillbar_reads_the_players_own_bar(self) -> None:
        """``SkillBar`` cross-checked against the world context record, slot by slot."""

        record = self._player_skillbar()
        if record is None:
            self.skipTest("the client reports no player skillbar (character-select screen?)")

        self.assertEqual(SkillBar.GetAgentID(), int(record.agent_id))
        self.assertEqual(SkillBar.GetAgentID(), int(Player.GetAgentID()))

        for slot in range(1, 9):
            with self.subTest(slot=slot):
                self.assertEqual(
                    SkillBar.GetSkillIDBySlot(slot), int(record.skills[slot - 1].skill_id)
                )

        print(f"--- live skillbar: {SkillBar.GetSkillbar()} ---")

    def test_the_slot_records_are_the_world_context_records(self) -> None:
        """A slot's words are the record's words, read through the binding's own members."""

        record = self._player_skillbar()
        if record is None:
            self.skipTest("the client reports no player skillbar")

        for slot in range(1, 9):
            with self.subTest(slot=slot):
                skill = SkillBar.GetSkillData(slot)
                source = record.skills[slot - 1]
                self.assertEqual(skill.adrenaline_a, int(source.adrenaline_a))
                self.assertEqual(skill.adrenaline_b, int(source.adrenaline_b))
                self.assertEqual(skill.recharge, int(source.recharge))
                self.assertEqual(skill.event, int(source.event))

    def test_the_learnt_bitset_agrees_with_the_world_context(self) -> None:
        """``IsSkillLearnt`` recomputed here from the same array it reads."""

        world = self.client.read_world_context()
        if world is None:
            self.skipTest("the client reported no world context")
        words = world.unlocked_character_skills
        if not words:
            self.skipTest("the world context carries no unlocked-character-skills array")

        checked = 0
        for skill_id in range(1, min(len(words) * 32, 2600)):
            expected = False
            real_index = skill_id // 32
            if real_index < len(words):
                expected = bool(int(words[real_index]) & (1 << (skill_id % 32)))
            if checked < 40 and expected:
                self.assertTrue(SkillBar.IsSkillLearnt(skill_id), f"skill {skill_id}")
                checked += 1
            elif checked < 40:
                self.assertFalse(SkillBar.IsSkillLearnt(skill_id), f"skill {skill_id}")
                checked += 1
        print(f"--- checked {checked} learned-skill bits against the world context ---")

    def test_the_unlocked_bitset_agrees_with_the_account_context(self) -> None:
        """``IsSkillUnlocked`` against the account context's own reader."""

        account = self.client.read_account_context()
        if account is None:
            self.skipTest("the client reported no account context")
        words = account.unlocked_account_skill_words
        if not words:
            self.skipTest("the account context carries no unlocked-account-skills array")

        checked = 0
        for skill_id in range(1, min(len(words) * 32, 1200)):
            self.assertEqual(
                SkillBar.IsSkillUnlocked(skill_id),
                account.is_account_skill_unlocked(skill_id),
                f"skill {skill_id}",
            )
            checked += 1
        print(f"--- checked {checked} unlocked-skill bits against the account context ---")

    # -- the hovered skill and the composed template -----------------------

    def test_the_hovered_skill_is_a_real_skill_or_zero(self) -> None:
        """``GetHoveredSkillID`` answers ``0`` or an id the client's own table holds."""

        hovered = SkillBar.GetHoveredSkillID()
        self.assertIsInstance(hovered, int)
        self.assertGreaterEqual(hovered, 0)

        tooltip = self.client.read_current_tooltip()
        if tooltip is not None and int(tooltip.payload_len) == SKILL_TOOLTIP_PAYLOAD_LENGTH:
            self.assertNotEqual(hovered, 0, "a skill tooltip is up but the member answered 0")
            self.assertIsNotNone(self.client.read_skill(hovered))
        print(f"--- hovered skill: {hovered} (tooltip: "
              f"{None if tooltip is None else hex(int(tooltip.payload_len))}) ---")

    def test_the_composed_template_round_trips_against_the_live_skillbar(self) -> None:
        """``Utils.GenerateSkillbarTemplate`` over live data, read back by the source's parser."""

        record = self._player_skillbar()
        if record is None:
            self.skipTest("the client reports no player skillbar")

        template = Utils.GenerateSkillbarTemplate()
        self.assertNotEqual(template, "", "the member answered nothing for a loaded skillbar")
        print(f"--- live template: {template} ---")

        prof_primary, prof_secondary, attributes, skills = Utils.ParseSkillbarTemplate(template)
        self.assertEqual(
            skills, [int(record.skills[slot - 1].skill_id) for slot in range(1, 9)]
        )
        self.assertEqual(
            (prof_primary, prof_secondary),
            tuple(int(value) for value in Agent.GetProfessionIDs(Player.GetAgentID())),
        )
        for attribute_id, level in attributes.items():
            with self.subTest(attribute_id=attribute_id):
                self.assertGreater(level, 0)
        print(f"--- template parses to professions ({prof_primary}, {prof_secondary}) and "
              f"{len(attributes)} attributes ---")
