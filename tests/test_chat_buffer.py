"""Live Guild Wars tests for the external ChatBuffer reader."""

from __future__ import annotations

import unittest

from py4gw import (
    ChatBuffer,
    ChatBufferStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveChatBufferTests(unittest.TestCase):
    """Verify ChatBuffer and typing-state reads against a client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first discovered client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")

        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        cls.scanner.initialize()
        cls.chat = ChatBuffer(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_resolves_live_chat_pointers(self) -> None:
        """The JSON resolvers locate the chat and typing pointer slots."""

        address = self.chat.initialize()
        self.assertIsNotNone(address)
        self.assertGreater(address or 0, 0)
        self.assertGreater(self.chat.cached_pointer_address or 0, 0)
        self.assertGreater(self.chat.cached_typing_pointer_address or 0, 0)
        print(
            f"Live ChatBuffer: 0x{address or 0:08X}, "
            f"typing={self.chat.is_typing()}"
        )

    def test_reads_live_chat_buffer(self) -> None:
        """The ring header and bounded message headers are readable."""

        snapshot = self.chat.read()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertIsInstance(snapshot, ChatBufferStruct)
        self.assertLessEqual(int(snapshot.next), 0x200)
        messages = snapshot.message_records
        self.assertLessEqual(len(messages), 0x200)
        print(
            f"Live chat: next={snapshot.next}, messages={len(messages)}, "
            f"typing={self.chat.is_typing()}"
        )
        if messages:
            print(f"Live first message channel={messages[0].channel}")
            self.assertIsInstance(messages[0].message_str, str)
            self.assertEqual(messages[0].message_encoded_str, messages[0].message_str)
            self.assertEqual(
                messages[0].message_codepoints,
                tuple(ord(character) for character in messages[0].message_str),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
