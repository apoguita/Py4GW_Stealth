"""Simple external connection objects for selected Guild Wars clients."""

from __future__ import annotations

from typing import Any

from .context import (
    CharContext,
    CharContextStruct,
    Cinematic,
    CinematicStruct,
    GameContext,
    GameContextStruct,
    GameplayContext,
    GameplayContextStruct,
    PreGameContext,
    PreGameContextStruct,
    ServerRegion,
    ServerRegionStruct,
    InstanceInfo,
    InstanceInfoStruct,
    TextParser,
    TextParserStruct,
    AvailableCharacterArray,
    AvailableCharacterArrayStruct,
    PartyContext,
    PartyContextStruct,
    GuildContext,
    GuildContextStruct,
    AccAgentContext,
    AccAgentContextStruct,
)
from .memory import ProcessMemoryReader
from .scanner import PatternCatalog, RemoteScanner
from .win32 import Win32


class ConnectedClient:
    """Own the read-only resources for one selected ``Gw.exe`` process."""

    def __init__(
        self,
        process: dict[str, Any] | int,
        win32: Win32 | None = None,
    ) -> None:
        """Connect to a PID or to a process record returned by discovery."""

        self._win32 = win32 or Win32()
        self._process = self._resolve_process(process)
        self._pid = int(self._process["pid"])
        module = self._win32.get_main_module(self._pid)
        self._reader = ProcessMemoryReader(self._win32, self._pid)
        try:
            self._scanner = RemoteScanner(
                self._reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            self._scanner.initialize()
            patterns = PatternCatalog.from_directory("offsets")
            self._game_context = GameContext(
                self._reader,
                self._scanner,
                patterns,
            )
            self._game_context.initialize()
            self._gameplay_context = GameplayContext(
                self._reader,
                self._scanner,
                patterns,
            )
            self._gameplay_context.initialize()
            self._cinematic = Cinematic(self._reader, self._game_context)
            self._pre_game_context = PreGameContext(
                self._reader,
                self._scanner,
                patterns,
            )
            self._pre_game_context.initialize()
            self._server_region = ServerRegion(
                self._reader,
                self._scanner,
                patterns,
            )
            self._server_region.initialize()
            self._instance_info = InstanceInfo(
                self._reader,
                self._scanner,
                patterns,
            )
            self._instance_info.initialize()
            self._text_parser = TextParser(self._reader, self._game_context)
            self._available_characters = AvailableCharacterArray(
                self._reader,
                self._scanner,
                patterns,
            )
            self._available_characters.initialize()
            self._party_context = PartyContext(self._reader, self._game_context)
            self._guild_context = GuildContext(self._reader, self._game_context)
            self._acc_agent_context = AccAgentContext(
                self._reader, self._game_context
            )
            self._context = CharContext(
                self._reader,
                self._scanner,
                patterns,
                game_context=self._game_context,
            )
            self._context.initialize()
        except Exception:
            self._reader.close()
            raise

    @property
    def pid(self) -> int:
        """Return the selected process ID."""

        return self._pid

    @property
    def process(self) -> dict[str, Any]:
        """Return the process record used to create this connection."""

        return dict(self._process)

    @property
    def context(self) -> CharContext:
        """Return the external CharContext reader for this client."""

        return self._context

    @property
    def game_context(self) -> GameContext:
        """Return the external GameContext reader for this client."""

        return self._game_context

    def read_game_context(self) -> GameContextStruct:
        """Read and return the current complete GameContext snapshot."""

        return self._game_context.read()

    @property
    def gameplay_context(self) -> GameplayContext:
        """Return the external GameplayContext reader for this client."""

        return self._gameplay_context

    def read_gameplay_context(self) -> GameplayContextStruct | None:
        """Read and return the current GameplayContext snapshot, if present."""

        return self._gameplay_context.read()

    @property
    def pre_game_context(self) -> PreGameContext:
        """Return the external PreGameContext reader for this client."""

        return self._pre_game_context

    def read_pre_game_context(self) -> PreGameContextStruct | None:
        """Read and return the current complete PreGameContext snapshot."""

        return self._pre_game_context.read()

    @property
    def server_region(self) -> ServerRegion:
        """Return the external ServerRegion reader for this client."""

        return self._server_region

    def read_server_region(self) -> ServerRegionStruct | None:
        """Read and return the current server-region value, if available."""

        return self._server_region.read()

    @property
    def instance_info(self) -> InstanceInfo:
        """Return the external InstanceInfo reader for this client."""

        return self._instance_info

    def read_instance_info(self) -> InstanceInfoStruct | None:
        """Read and return the current InstanceInfo snapshot, if available."""

        return self._instance_info.read()

    @property
    def text_parser(self) -> TextParser:
        """Return the external TextParser reader for this client."""

        return self._text_parser

    def read_text_parser(self) -> TextParserStruct | None:
        """Read the current TextParser snapshot, if its pointer is available."""

        return self._text_parser.read()

    @property
    def available_characters(self) -> AvailableCharacterArray:
        """Return the external account-roster reader for this client."""

        return self._available_characters

    def read_available_characters(self) -> AvailableCharacterArrayStruct | None:
        """Read the current account-wide available-character roster."""

        return self._available_characters.read()

    @property
    def party_context(self) -> PartyContext:
        """Return the external PartyContext reader for this client."""

        return self._party_context

    def read_party_context(self) -> PartyContextStruct | None:
        """Read the current PartyContext snapshot, if available."""

        return self._party_context.read()

    @property
    def guild_context(self) -> GuildContext:
        """Return the external GuildContext reader for this client."""

        return self._guild_context

    def read_guild_context(self) -> GuildContextStruct | None:
        """Read the current GuildContext snapshot, if available."""

        return self._guild_context.read()

    @property
    def acc_agent_context(self) -> AccAgentContext:
        """Return the external agent-context reader for this client."""

        return self._acc_agent_context

    def read_acc_agent_context(self) -> AccAgentContextStruct | None:
        """Read the current maintained agent context, if available."""

        return self._acc_agent_context.read()

    @property
    def cinematic(self) -> Cinematic:
        """Return the external cinematic reader for this client."""

        return self._cinematic

    def read_cinematic_context(self) -> CinematicStruct | None:
        """Read and return the current cinematic snapshot, if present."""

        return self._cinematic.read()

    def read_char_context(self) -> CharContextStruct:
        """Read and return the current complete CharContext snapshot."""

        return self._context.read()

    def character_name(self) -> str | None:
        """Return the live character name, or ``None`` at the selection menu."""

        try:
            name = self._context.read_player_name().strip()
        except (OSError, RuntimeError):
            return None
        return name or None

    @property
    def is_connected(self) -> bool:
        """Return whether this client has an open read-only connection."""

        return not self._reader.is_closed

    @property
    def is_logged_in(self) -> bool:
        """Return whether this connected client has a logged-in character."""

        return self._context.is_logged_in

    def close(self) -> None:
        """Close the read-only process handle owned by this connection."""

        self._reader.close()

    def __enter__(self) -> ConnectedClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _resolve_process(self, process: dict[str, Any] | int) -> dict[str, Any]:
        if isinstance(process, int):
            pid = process
            for candidate in self._win32.find_guild_wars():
                if int(candidate["pid"]) == pid:
                    return candidate
            raise ValueError(f"PID {pid} is not a running Guild Wars client.")
        pid = int(process["pid"])
        if pid <= 0:
            raise ValueError("The selected process PID must be positive.")
        return dict(process)


_current_client: ConnectedClient | None = None


def connect(process: dict[str, Any] | int) -> ConnectedClient:
    """Select one Guild Wars client and make it the current connection."""

    global _current_client
    disconnect()
    _current_client = ConnectedClient(process)
    return _current_client


def disconnect() -> None:
    """Close and clear the current selected client, if one exists."""

    global _current_client
    if _current_client is not None:
        _current_client.close()
        _current_client = None


def current_client() -> ConnectedClient | None:
    """Return the current selected client, if one has been connected."""

    return _current_client
