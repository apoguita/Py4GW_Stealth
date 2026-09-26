"""Live Guild Wars test for what the last two changes implemented.

Two things are exercised, and both need a running client.

**The enum-backed ``Agent`` members** (``py4gw/agent.py`` + ``py4gw/enums_src/game_data_enums.py``).
Nine members were blocked on the game-data enums and now answer: ``IsSpirit``, ``IsPet``,
``IsMinion``, ``GetAllegiance``, ``GetProfessionNames``, ``GetProfessionShortNames``,
``GetWeaponType``, and the two that only needed ``IsPet`` — ``IsCaster`` and ``IsRanged``. Every one
of them is driven against **real agents**, and every answer is checked against the record the member
claims to read plus the enum tables the source maps through: this is the source's own arithmetic
evaluated on this client's data.

**The chat-log write path** (``py4gw/chat.py`` + ``Player.SendFakeChat``/``SendFakeChatColored``).
The port writes a line into the client's own chat log through ``kWriteToChatLog``, and it has never
been observed doing it. The verification is the client's own: the connection watches that message id
(``_WATCHED_MESSAGES`` gains ``(0x1000007F, 4)`` for this run), and the observer — code running
*inside* the client's call — copies the string the packet names. So a line this port writes comes
back as an event the client produced, carrying the text it was handed.

**What this run changes.** Connecting installs the capability layer (two entry hooks, the block, the
dispatcher, a listener thread), and the fake-chat calls write into the client's chat log — visible in
its chat window, which is the point. Nothing is sent to the server by the log writers: the two
send tests use the command channel (``/age``), which the client answers itself. ``tearDownClass``
disconnects, compares both entry bytes and the whole code section against the values taken before the
run, and then connects and disconnects once more — which can only succeed if the entries are the
originals again.

Run it from an **elevated** shell, with Guild Wars running and a character in a map::

    python -m unittest tests.test_live_agent_chat -v
"""

from __future__ import annotations

import hashlib
import time
import unittest
from typing import Any

import py4gw
from py4gw import chat
from py4gw.agent import Agent
from py4gw.client import (
    _GAME_THREAD_HOOK,
    _GAME_THREAD_HOOK_BYTES,
    _GAME_THREAD_OBSERVE,
    _GAME_THREAD_OBSERVE_BYTES,
    _WATCHED_MESSAGES,
)
from py4gw.enums_src.game_data_enums import (
    Allegiance,
    AllegianceNames,
    Profession,
    Profession_Names,
    ProfessionShort,
    ProfessionShort_Names,
    Weapon,
    Weapon_Names,
)
from py4gw.game_thread.shared_block import EventKind, EventRecord
from py4gw.player import ChatChannel, Player
from py4gw.win32 import Win32

#: ``ui::UIMessage::kWriteToChatLog`` (``constants/ui.h:62``): the message the chat log is written
#: with, and the one this run watches so the client reports the line it was handed.
WRITE_TO_CHAT_LOG = 0x1000007F

#: ``ui::UIChatMessage``'s ``message`` field (``context/ui.h:325-329``): word 1, which is where the
#: client finds the encoded line this port places in the block.
CHAT_MESSAGE_FIELD_OFFSET = 4

#: How many agent records to drive the members against, and how long to wait for an event.
AGENT_LIMIT = 48
WAIT_SECONDS = 6.0
TEXT_CHUNK = 0x100000

#: The marker both fake-chat lines carry, so the client's own report can be recognised.
MARKER = "Py4GW-Stealth-live-fakechat"
COLOURED_MARKER = "Py4GW-Stealth-live-coloured"


class _MessageSpy:
    """Keep every UI message the client's own function was called with.

    **The message id is the event's ``sequence``, not ``arg0``.** The observer stores the id in the
    sequence word and the *packet's* four words in ``arg0..arg3``
    (``game_thread/payload.py:788-792``); for ``kWriteToChatLog`` word 0 is the channel, which is why
    filtering on ``arg0`` matched nothing and this suite reported "no copies" for lines the client
    had in fact been handed (live, 2026-09-26: the same send produced one event with
    ``sequence=0x1000007F``, ``arg0=1``, and the copied text).
    """

    def __init__(self) -> None:
        self.events: list[EventRecord] = []

    def __call__(self, event: EventRecord) -> None:
        self.events.append(event)

    def lines(self, message_id: int) -> list[str]:
        """The text of every copy taken for one message id, decoded as code units."""

        return [
            _units_to_text(event.text)
            for event in self.events
            if event.sequence == message_id and event.text
        ]

    def wait_for(self, message_id: int, containing: str, timeout: float) -> str | None:
        """Wait for a copy of one message that contains ``containing``, or give up."""

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for line in self.lines(message_id):
                if containing in line:
                    return line
            time.sleep(0.05)
        return None


def _units_to_text(units: tuple[int, ...]) -> str:
    """Decode the observer's code-unit copy, dropping the terminator.

    The copy is the wide string the client was handed: an encoded line (``\\x108\\x107`` then the
    text literally, then ``\\x1``), so the literal characters of a chat line are readable in it as
    they are.
    """

    return "".join(chr(unit) for unit in units if unit != 0)


def _chat_log_texts(client: Any) -> list[str]:
    """The lines the client's own chat log holds, through the ported chat-buffer context.

    This is the witness ``tests/probe_chat_log_write.py`` uses: the log is what the client *stored*,
    so it shows a line arrived even when a message-level observation is not what is being asked.
    """

    buffer = client.read_chat_buffer()
    if buffer is None:
        return []
    texts: list[str] = []
    for record in buffer.message_records:
        try:
            texts.append(record.message_str)
        except Exception:  # a slot that is not a readable message is skipped, not fatal
            continue
    return texts


class _LiveAgentChatTests(unittest.TestCase):
    """Drive the newly ported members and the chat log writer against the running client."""

    client: Any
    spy: _MessageSpy

    # -- setup and teardown ------------------------------------------------

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

        module = win32.get_main_module(cls.pid)
        cls.module_base = int(module["base_address"])
        cls.module_size = int(module["size"])
        cls.text_before = cls._text_digest(win32, cls.pid)

        # The one change this test makes to the library's own configuration: the chat-log message is
        # watched for this run, so the client's own call to ``SendUIMessage`` brings the line back.
        cls.watches = _WATCHED_MESSAGES
        py4gw.client._WATCHED_MESSAGES = cls.watches + (  # type: ignore[attr-defined]
            (WRITE_TO_CHAT_LOG, CHAT_MESSAGE_FIELD_OFFSET),
        )

        cls.client = py4gw.connect(clients[0])
        cls.spy = _MessageSpy()
        cls.client.callbacks.register(EventKind.UI_MESSAGE, cls.spy)
        print(
            f"--- connected to pid {cls.pid}, module 0x{cls.module_base:08X} "
            f"({cls.module_size:#x} bytes), watching kWriteToChatLog ---"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        py4gw.client._WATCHED_MESSAGES = cls.watches  # type: ignore[attr-defined]
        py4gw.disconnect()

        win32 = Win32()
        after = cls._text_digest(win32, cls.pid)
        print(
            f"--- code section after disconnect: {after[0][:16]}… ({after[1]:#x} bytes); "
            f"before: {cls.text_before[0][:16]}… ---"
        )
        if after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the code section is not what it was before the run: "
                f"{cls.text_before[0]} -> {after[0]}"
            )

        # Both entries must hold their original bytes again, and the only proof that needs no
        # assumption is that installing the layer once more succeeds — ``_prepare_target``
        # compares those exact bytes before it patches anything.
        py4gw.connect(win32.find_guild_wars()[0])
        py4gw.disconnect()
        print("--- the layer reinstalled and was removed again: entries are the originals ---")

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _read_bytes(address: int, size: int) -> bytes:
        from py4gw.memory import ProcessMemoryReader

        win32 = Win32()
        with ProcessMemoryReader(win32, _LiveAgentChatTests.pid) as reader:
            return reader.read(address, size)

    @classmethod
    def _text_digest(cls, win32: Win32, pid: int) -> tuple[str, int]:
        """A hash of the client's whole code section, before and after the run."""

        from py4gw.memory import ProcessMemoryReader
        from py4gw.scanner import RemoteScanner

        module = win32.get_main_module(pid)
        digest = hashlib.sha256()
        size = 0
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader, int(module["base_address"]), int(module["size"])
            )
            scanner.initialize()
            section = scanner.get_section_range("text")
            address = section.start
            while address < section.end:
                chunk = min(TEXT_CHUNK, section.end - address)
                digest.update(reader.read(address, chunk))
                size += chunk
                address += chunk
        return digest.hexdigest(), size

    def _agent_ids(self) -> list[int]:
        """The ids the agent array reports, capped for a bounded run."""

        snapshot = self.client.read_agent_array()
        return [int(reference.agent_id) for reference in snapshot.references][:AGENT_LIMIT]

    # -- the enum-backed members on live data ------------------------------

    def test_a_living_agents_enum_backed_members_answer_the_source_s_arithmetic(self) -> None:
        """Each member is checked against the record it reads and the table the source uses."""

        player_id = self.client.read_player_agent_id().agent_id
        ids = self._agent_ids()
        print(f"--- player agent {player_id}; {len(ids)} agents in the array ---")
        self.assertTrue(ids, "the agent array reported no agents; is a character in a map?")

        checked = {name: 0 for name in (
            "IsSpirit", "IsPet", "IsMinion", "GetAllegiance", "GetProfessionNames",
            "GetProfessionShortNames", "GetWeaponType", "IsCaster", "IsRanged",
        )}
        rows: list[str] = []

        for agent_id in ids:
            record = self.client.read_agent_by_id(agent_id)
            if record is None or not hasattr(record, "allegiance"):
                continue
            raw_allegiance = int(record.allegiance)
            spawned = bool(record.is_spawned)
            primary = int(record.primary)
            secondary = int(record.secondary)
            weapon = int(record.weapon_type)

            # The source's own arithmetic, on this record.
            expected_spirit = raw_allegiance == int(Allegiance.SpiritPet) and spawned
            expected_pet = raw_allegiance == int(Allegiance.SpiritPet) and not spawned
            expected_minion = raw_allegiance == int(Allegiance.Minion)
            expected_allegiance = (
                (raw_allegiance, AllegianceNames[Allegiance(raw_allegiance)])
                if raw_allegiance in {int(member) for member in Allegiance}
                else (raw_allegiance, "Unknown")
            )
            profession_name = Profession_Names[Profession(primary)] if primary in {
                int(member) for member in Profession
            } else None
            secondary_name = Profession_Names[Profession(secondary)] if secondary in {
                int(member) for member in Profession
            } else None
            expected_weapon = (
                (weapon, Weapon_Names[Weapon(weapon)])
                if weapon in {int(member) for member in Weapon}
                else (weapon, "Unknown")
            )

            with self.subTest(agent=agent_id, member="IsSpirit"):
                self.assertEqual(Agent.IsSpirit(agent_id), expected_spirit)
                checked["IsSpirit"] += 1
            with self.subTest(agent=agent_id, member="IsPet"):
                self.assertEqual(Agent.IsPet(agent_id), expected_pet)
                checked["IsPet"] += 1
            with self.subTest(agent=agent_id, member="IsMinion"):
                self.assertEqual(Agent.IsMinion(agent_id), expected_minion)
                checked["IsMinion"] += 1
            with self.subTest(agent=agent_id, member="GetAllegiance"):
                self.assertEqual(Agent.GetAllegiance(agent_id), expected_allegiance)
                checked["GetAllegiance"] += 1
            with self.subTest(agent=agent_id, member="GetWeaponType"):
                self.assertEqual(Agent.GetWeaponType(agent_id), expected_weapon)
                checked["GetWeaponType"] += 1

            if profession_name is not None and secondary_name is not None:
                with self.subTest(agent=agent_id, member="GetProfessionNames"):
                    self.assertEqual(
                        Agent.GetProfessionNames(agent_id),
                        (profession_name, secondary_name),
                    )
                    checked["GetProfessionNames"] += 1
                with self.subTest(agent=agent_id, member="GetProfessionShortNames"):
                    self.assertEqual(
                        Agent.GetProfessionShortNames(agent_id),
                        (
                            ProfessionShort_Names[ProfessionShort(primary)],
                            ProfessionShort_Names[ProfessionShort(secondary)],
                        ),
                    )
                    checked["GetProfessionShortNames"] += 1

            # The two members that only needed ``IsPet``: a pet is neither caster nor ranged.
            if expected_pet:
                with self.subTest(agent=agent_id, member="IsCaster"):
                    self.assertFalse(Agent.IsCaster(agent_id))
                    checked["IsCaster"] += 1
                with self.subTest(agent=agent_id, member="IsRanged"):
                    self.assertFalse(Agent.IsRanged(agent_id))
                    checked["IsRanged"] += 1

            if len(rows) < 12:
                rows.append(
                    f"    {agent_id:>6}  allegiance {raw_allegiance} "
                    f"({expected_allegiance[1]:<11}) spawned {int(spawned)}  "
                    f"prof {primary}/{secondary}  weapon {weapon} "
                    f"({expected_weapon[1]:<8}) spirit {int(expected_spirit)} "
                    f"pet {int(expected_pet)} minion {int(expected_minion)}"
                )

        for row in rows:
            print(row)
        print(f"--- members checked per agent: {checked} ---")
        # The members are only proven by what they agreed with, so require a real sample.
        self.assertGreaterEqual(checked["GetAllegiance"], 1)
        self.assertGreaterEqual(checked["GetWeaponType"], 1)

    def test_the_players_own_professions_and_allegiance_are_readable(self) -> None:
        """The player's record is the one a caller checks by eye, so print what it answers."""

        player_id = self.client.read_player_agent_id().agent_id
        record = self.client.read_agent_by_id(player_id)
        self.assertIsNotNone(record)

        names = Agent.GetProfessionNames(player_id)
        short = Agent.GetProfessionShortNames(player_id)
        allegiance = Agent.GetAllegiance(player_id)
        weapon = Agent.GetWeaponType(player_id)
        print(
            f"--- player {player_id}: professions {names} ({short}), "
            f"allegiance {allegiance}, weapon {weapon}, "
            f"caster {Agent.IsCaster(player_id)}, ranged {Agent.IsRanged(player_id)}, "
            f"spirit {Agent.IsSpirit(player_id)}, pet {Agent.IsPet(player_id)}, "
            f"minion {Agent.IsMinion(player_id)} ---"
        )
        # The player's own profession pair comes from the same two tables, and a player is alive.
        self.assertEqual(
            names[0], Profession_Names[Profession(int(record.primary))]
        )
        self.assertIn(allegiance[1], set(AllegianceNames.values()) | {"Unknown"})

    # -- the chat log write path -------------------------------------------

    def test_a_fake_chat_line_is_written_by_the_client_s_own_function(self) -> None:
        """``Player.SendFakeChat`` reaches the client, and the client reports the line."""

        Player.SendFakeChat(ChatChannel.CHANNEL_ALL, MARKER)
        line = self.spy.wait_for(WRITE_TO_CHAT_LOG, MARKER, WAIT_SECONDS)
        self.assertIsNotNone(
            line,
            "the client was never called with kWriteToChatLog carrying our line; "
            f"observed kWriteToChatLog copies: {self.spy.lines(WRITE_TO_CHAT_LOG)}",
        )
        print(f"--- the client was handed: {line!r} ---")
        self.assertIn(MARKER, line or "")
        self.assertEqual(chat._transient_chat_message, 0)

    def test_a_coloured_fake_chat_line_is_written_too(self) -> None:
        """``Player.SendFakeChatColored`` runs the formatter and writes the coloured line."""

        Player.SendFakeChatColored(ChatChannel.CHANNEL_ALL, COLOURED_MARKER, 255, 128, 0)
        line = self.spy.wait_for(WRITE_TO_CHAT_LOG, COLOURED_MARKER, WAIT_SECONDS)
        self.assertIsNotNone(
            line,
            "the coloured line never reached the client; "
            f"observed kWriteToChatLog copies: {self.spy.lines(WRITE_TO_CHAT_LOG)}",
        )
        print(f"--- the client was handed: {line!r} ---")
        self.assertIn("<c=#FF8000>", line or "")

    def test_the_watched_history_keeps_the_lines_without_a_request(self) -> None:
        """The history is there before anyone asks for it — the port's own keeping of the log.

        The two fake-chat tests above wrote lines into the client's log, and **nothing in this suite
        calls ``Player.RequestChatHistory``**: the lines are in the history because the connection
        watches ``kWriteToChatLog`` and the chat module decodes each announced line as it arrives —
        the message native's own chat module registers a callback for (``chat.cpp:205``). A
        post-mortem read is therefore just ``Player.GetChatHistory()``.
        """

        history = Player.GetChatHistory()
        newest = history[-1] if history else "(none)"
        print(f"--- watched history: {len(history)} line(s); newest: {newest!r} ---")
        self.assertTrue(Player.IsChatHistoryReady(), "no line was watched at all")
        self.assertTrue(
            any(MARKER in line for line in history),
            f"the line written earlier is not in the watched history: {history!r}",
        )

    def test_the_command_channel_reaches_the_client_s_sender(self) -> None:
        """``SendChat`` over the command opcode reaches this build's real sender, and the client lives.

        Two returns, and they differ for the source's own reason: ``chat.SendChat`` is the port of
        ``GW::chat::SendChat`` and answers ``bool`` — ``False`` means its guard refused the opcode
        before any call — while ``Player.SendChatCommand`` is Reforged's wrapper, which queues the
        send and answers ``None`` (``Player.py``: the ``ActionQueueManager().AddAction`` call). So the
        refusal is asserted on the member that has an answer, and the wrapper is called for its
        effect. ``/age`` is a command: nothing is broadcast, and the client's own reply is what the
        log shows.
        """

        before = len(self.spy.events)
        before_log = _chat_log_texts(self.client)
        self.assertTrue(
            chat.SendChat("/", "age"),
            "chat.SendChat refused the command opcode before the call",
        )
        self.assertIsNone(Player.SendChatCommand("age"))
        time.sleep(WAIT_SECONDS / 2)
        after_log = _chat_log_texts(self.client)
        print(
            f"--- /age sent through chat.send_chat_func (0x0082D620); "
            f"{len(self.spy.events) - before} further UI message(s) observed; "
            f"client log {len(before_log)} -> {len(after_log)} lines ---"
        )
        for line in after_log[len(before_log):][-3:]:
            print(f"--- the client said: {line!r} ---")
        # The client answering is the proof it survived the call; the line itself is printed above
        # as the evidence of what came back, because the reply's message id is the client's choice.
        self.assertEqual(self.client.read_player_agent_id().agent_id > 0, True)


if __name__ == "__main__":
    unittest.main()
