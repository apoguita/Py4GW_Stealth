"""External port of Reforged's ``Py4GWCoreLib/Player.py``.

Every member of the Reforged ``Player`` namespace class is present here with the
same name and the same signature, so a script that reads ``Player.GetLevel()``
keeps working after switching libraries. What differs is *which* members can
actually produce a value.

The Reforged class is a namespace of ``@staticmethod``s that read game contexts
and, for anything that changes game state, queue a call into the client. This
port keeps that shape and resolves the selected client the same way the context
readers do, through :func:`py4gw.client.current_client`.

Three groups exist, and each member says which one it is in its docstring:

``implemented``
    The value comes from a game context, which this project can read. These
    members return exactly what Reforged returns, including its defaults when a
    context is unavailable.

``disabled``
    The value lives in DLL-owned state that only exists because code runs inside
    ``Gw.exe``, or the member performs an action. These members exist so a ported
    script fails loudly at the call site, naming the missing mechanism, instead
    of silently returning a wrong value. They raise ``NotImplementedError``.

``adapted``
    The value is reachable but through a different route than Reforged uses, or
    Reforged's route needs something this project does not read. Each case is
    documented at the member and listed in ``docs/PLAYER_PORT.md``.

None of the disabled members are implemented by writing to ``Gw.exe``; the
project's read-only boundary is unchanged by this module.
"""

from __future__ import annotations

from enum import IntEnum
from functools import wraps
from typing import Any, Callable, TypeVar

from .client import ConnectedClient, require_client
from .context.agent_array import AgentStruct
from .context.char_context import CharContextStruct
from .context.world_context import PlayerStruct, TitleStruct, WorldContextStruct

_T = TypeVar("_T")


class PlayerStatus(IntEnum):
    """Native ``GW::Constants::FriendStatus``, as Reforged names it.

    The same numeric values are exposed by
    :class:`py4gw.context.friend_list_context.FriendStatus`; this is the spelling
    Reforged's ``Player`` uses, including its ``DND`` alias and string parsing.
    """

    Offline = 0
    Online = 1
    DoNotDisturb = 2
    DND = 2
    Away = 3

    @classmethod
    def from_value(cls, status: PlayerStatus | int | str | None) -> PlayerStatus | None:
        """Coerce a member, integer, or status name to a member.

        Accepts ``"offline"``, ``"online"``, ``"do_not_disturb"``,
        ``"donotdisturb"``, ``"dnd"``, and ``"away"``, ignoring case and
        treating spaces and dashes as underscores. Returns ``None`` for anything
        unrecognized, matching Reforged.
        """

        if isinstance(status, cls):
            return status
        if isinstance(status, str):
            normalized = status.strip().lower().replace(" ", "_").replace("-", "_")
            names = {
                "offline": cls.Offline,
                "online": cls.Online,
                "do_not_disturb": cls.DoNotDisturb,
                "donotdisturb": cls.DoNotDisturb,
                "dnd": cls.DoNotDisturb,
                "away": cls.Away,
            }
            return names.get(normalized)
        if status is None:
            return None
        try:
            return cls(int(status))
        except (TypeError, ValueError):
            return None

    @property
    def display_name(self) -> str:
        """Return the Reforged display spelling of this status."""

        if self is PlayerStatus.DoNotDisturb:
            return "do_not_disturb"
        return self.name.lower()


class ChatChannel(IntEnum):
    """Native chat channel identifiers.

    Only the disabled chat senders use these; the enum is ported in full so the
    signatures match Reforged.
    """

    CHANNEL_ALLIANCE = 0
    CHANNEL_ALLIES = 1
    CHANNEL_GWCA1 = 2
    CHANNEL_ALL = 3
    CHANNEL_GWCA2 = 4
    CHANNEL_MODERATOR = 5
    CHANNEL_EMOTE = 6
    CHANNEL_WARNING = 7
    CHANNEL_GWCA3 = 8
    CHANNEL_GUILD = 9
    CHANNEL_GLOBAL = 10
    CHANNEL_GROUP = 11
    CHANNEL_TRADE = 12
    CHANNEL_ADVISORY = 13
    CHANNEL_WHISPER = 14
    CHANNEL_COUNT = 15
    CHANNEL_COMMAND = 16
    CHANNEL_UNKNOWN = -1


def _disabled(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member that needs code inside the client."""

    return NotImplementedError(
        f"Player.{member} is not available from an external reader: {requirement}. "
        "It exists for source parity so a ported script fails at the call site "
        "and names the missing mechanism instead of returning a wrong value."
    )


#: The value the native ``PickHighest`` treats as "not read".
_INVALID_U32 = 0xFFFFFFFF


def _pick_highest(first: int, second: int) -> int:
    """Return the higher of two duplicated fields, ignoring unread ones.

    This is the native ``PickHighest`` from ``player_bindings.cpp:56``. The
    client keeps several values twice and only one copy is current, so the
    runtime ignores a field that reads ``0`` or ``0xFFFFFFFF`` and takes the
    higher of the ones that remain, falling back to ``0``.

    A plain ``max`` is not equivalent: when one copy holds ``0xFFFFFFFF`` it
    would win, and the native deliberately discards it. Reforged's Python
    wrappers use ``max``; the native runtime is the authority here.
    """

    first_ok = first != 0 and first != _INVALID_U32
    second_ok = second != 0 and second != _INVALID_U32
    if first_ok and second_ok:
        return first if first > second else second
    if first_ok:
        return first
    if second_ok:
        return second
    return 0


class Player:
    """Read-only port of the Reforged ``Player`` namespace class."""

    _ACCOUNT_EMAIL_MAX_LEN = 64

    PlayerStatus = PlayerStatus

    #: Reforged's class attribute, kept as the source declares it.
    _last_xy: tuple[float, float] = (0.0, 0.0)

    # ── client access ──────────────────────────────────────────────────────


    # ── status helpers (computed) ──────────────────────────────────────────

    @staticmethod
    def ResolvePlayerStatus(status: PlayerStatus | int | str | None) -> PlayerStatus | None:
        """Return the status member for a value, name, or member."""

        return PlayerStatus.from_value(status)

    @staticmethod
    def GetPlayerStatusNameFromValue(
        status: PlayerStatus | int | str | None,
    ) -> str:
        """Return the display name of a status value, or its text form."""

        player_status = PlayerStatus.from_value(status)
        if player_status is not None:
            return player_status.display_name
        return str(status)

    # ── account identity helpers (computed) ────────────────────────────────

    @staticmethod
    def _account_fallback() -> str:
        """Return a deterministic account identifier for undecodable emails.

        Adapted: Reforged builds this from the client's window handle through
        ``PySystem.Console.get_gw_window_handle()``, a host function. This
        project's :class:`~py4gw.win32.Win32` does not enumerate windows, so the
        process id is used instead. Both are equally stable and unique per
        client, and the value only ever stands in for an unreadable email.
        """

        pid = require_client().pid
        return f"{pid}@Py4GW"[: Player._ACCOUNT_EMAIL_MAX_LEN]

    @staticmethod
    def _sanitize_account_email_or_fallback(account_email: str | None) -> str:
        """Normalize an account email, falling back when it is unusable.

        Reforged collapses non-ASCII or over-long addresses to the fallback so
        downstream shared-memory paths cannot receive an unsafe string.
        """

        if not account_email:
            return Player._account_fallback()
        try:
            account_email = str(account_email).strip()
            if not account_email:
                return Player._account_fallback()
            account_email.encode("ascii")
            if len(account_email) > Player._ACCOUNT_EMAIL_MAX_LEN:
                account_email = account_email[: Player._ACCOUNT_EMAIL_MAX_LEN]
            return account_email
        except Exception:
            return Player._account_fallback()

    @staticmethod
    def _format_uuid_as_email(player_uuid: tuple[int, ...] | None) -> str:
        """Return the ``uuid_1_2_3_4`` form of a player UUID.

        Reforged passes this through ``encoded_wstr_to_str``, which escapes
        non-printable characters rather than decoding them. Every character here
        is printable ASCII, so that step is a no-op and the joined text is
        returned directly.
        """

        if not player_uuid:
            return ""
        try:
            joined = "uuid_" + "_".join(str(part) for part in player_uuid)
        except TypeError:
            return str(player_uuid)
        return joined or "INVALID"

    @staticmethod
    def player_instance() -> Any:
        """Disabled: Reforged returns a ``PyPlayer`` native binding object.

        The binding is constructed inside the client; there is nothing to
        construct externally.
        """

        raise _disabled(
            "player_instance",
            "it returns a PyPlayer native binding object, which only exists "
            "inside the client",
        )

    # ── core identity (context) ────────────────────────────────────────────

    @staticmethod
    def GetPlayerNumber() -> int | None:
        """Return the character's player number, or ``None`` when unreadable."""

        client = require_client()
        try:
            char_context = client.read_char_context()
        except (OSError, RuntimeError):
            return None
        if char_context is None:
            return None
        return int(char_context.player_number)

    @staticmethod
    def GetLoginNumber() -> int:
        """Return the login number whose agent id is this player's agent id.

        Reforged maps each party member's ``login_number`` to an agent id through
        ``Party.Players.GetAgentIDByLoginNumber``, which is
        ``player::GetPlayerByID(login)->agent_id``. Both halves are context
        reads, so this is implemented directly.
        """

        client = require_client()
        agent_id = Player.GetAgentID() if Player.IsPlayerLoaded() else 0
        for member in Player._party_players(client):
            if agent_id and agent_id == Player._agent_id_for_login(client, int(member.login_number)):
                return int(member.login_number)
        return 0

    @staticmethod
    def GetPartyNumber() -> int:
        """Return this player's index in the party list, or ``-1``."""

        login_number = Player.GetLoginNumber()
        client = require_client()
        for index, member in enumerate(Player._party_players(client)):
            if int(member.login_number) == login_number:
                return index
        return -1

    @staticmethod
    def IsPlayerLoaded() -> bool:
        """Return whether this client has a connected player in a ready map.

        Delegates to :meth:`py4gw.party.Party.IsPlayerLoaded`, which owns the
        check. That is where it belongs: the native helper is documented in
        source as "parity with legacy ``GW::PartyMgr::GetIsPlayerLoaded(-1)``"
        (``player_bindings.cpp:28``), so the party module is its historical home,
        and one implementation is the entire point of a check that Reforged's
        Python calls from seventeen sites.

        Reforged splits it: ``Player.IsPlayerLoaded`` holds the real logic and
        ``Party.IsPlayerLoaded`` is a bare ``pass``. This port inverts that, and
        deliberately does not reproduce the ``Player`` tail — world context,
        agent validity, and ``Agent.GetInstanceUptime(agent_id) > 750`` — which
        runs only when no party member matches and can return ``True`` where the
        native returns ``False``. The ``750`` has no source in either base
        project. See ``docs/PLAYER_PORT.md``.
        """

        from .party import Party

        return Party.IsPlayerLoaded()

    @staticmethod
    def _require_player_loaded(
        default: _T | None = None,
    ) -> Callable[[Callable[..., _T]], Callable[..., _T | None]]:
        """Return a decorator that skips the call until the player is loaded."""

        def decorator(func: Callable[..., _T]) -> Callable[..., _T | None]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> _T | None:
                if not Player.IsPlayerLoaded():
                    return default
                return func(*args, **kwargs)

            return wrapper

        return decorator

    # ── shared lookups ────────────────────────────────────────────────────

    @staticmethod
    def _world(client: ConnectedClient) -> WorldContextStruct | None:
        """Return the world context, or ``None`` while unavailable."""

        try:
            return client.read_world_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _party_players(client: ConnectedClient) -> list[Any]:
        """Return the current party player members, or an empty list.

        Delegates to :meth:`py4gw.party.Party.GetPlayers`, which owns the party
        read. Imported lazily because ``Party`` imports ``Player`` back.
        """

        from .party import Party

        return Party.GetPlayers()

    @staticmethod
    def _agent_id_for_login(client: ConnectedClient, login_number: int) -> int:
        """Return the agent id registered for a login number, or ``0``.

        Delegates to :meth:`py4gw.party.Party.Players.GetAgentIDByLoginNumber`,
        which is the native ``GetAgentIdByLoginNumber`` lookup.
        """

        from .party import Party

        return Party.Players.GetAgentIDByLoginNumber(login_number)

    @staticmethod
    def _local_player(client: ConnectedClient) -> PlayerStruct | None:
        """Return this client's own world-context player record, if present."""

        player_number = Player.GetPlayerNumber()
        if player_number is None:
            return None
        world_context = Player._world(client)
        if world_context is None:
            return None
        return world_context.GetPlayerById(player_number)

    # ── agent-backed identity (context) ───────────────────────────────────

    @staticmethod
    def GetAgentID() -> int:
        """Return the controlled character's agent id, or ``0``."""

        if not Player.IsPlayerLoaded():
            return 0
        client = require_client()
        world_context = Player._world(client)
        if world_context is None:
            return 0
        controlled = world_context.player_controlled_character
        if controlled is None:
            return 0
        return int(controlled.agent_id)

    @staticmethod
    def _agent_by_id(agent_id: int) -> AgentStruct | None:
        """Return one agent record by id, or ``None``.

        A private helper, not a Reforged ``Player`` member: Reforged reaches the
        same record through ``Agent.GetAgentByID``.
        """

        if not agent_id:
            return None
        client = require_client()
        try:
            return client.read_agent_by_id(agent_id)
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def GetName() -> str:
        """Return the player's character name.

        Adapted: Reforged calls ``Agent.GetNameByID``, which reads the agent's
        encoded name through a native binding. The same name is a plain field of
        the character context, so it is read from there instead.
        """

        client = require_client()
        try:
            char_context = client.read_char_context()
        except (OSError, RuntimeError):
            return ""
        if char_context is None:
            return ""
        return char_context.player_name_str or ""

    @staticmethod
    def GetXY() -> tuple[float, float]:
        """Return the player's X/Y position, keeping the last good reading.

        A failure to resolve the agent for one read yields ``(0.0, 0.0)``, which
        is not a position any player occupies; returning it would snap map
        overlays to the world origin, so the last real position is returned
        instead, exactly as Reforged does.
        """

        agent = Player._agent_by_id(Player.GetAgentID())
        if agent is not None:
            xy = agent.xy
            if xy and (xy[0] or xy[1]):
                Player._last_xy = xy
                return xy
        return Player._last_xy

    @staticmethod
    def GetAgent() -> AgentStruct | None:
        """Return the player's own agent record, or ``None``."""

        if not Player.IsPlayerLoaded():
            return None
        return Player._agent_by_id(Player.GetAgentID())

    @staticmethod
    def GetObservingID() -> int:
        """Return the agent id this client is registered as.

        Native ``Context::GetObservingId()`` returns ``*g_player_agent_id_addr``.
        While spectating a match that global holds the observed player, so this
        covers both cases.
        """

        client = require_client()
        snapshot = client.read_player_agent_id()
        if snapshot is None:
            return 0
        return int(snapshot.agent_id)

    @staticmethod
    def GetTargetID() -> int:
        """Disabled: the target id is DLL-owned state.

        Native ``GetTargetId()`` returns ``g_current_target_id``, a global the
        runtime maintains from a ``kChangeTarget`` UI-message hook
        (``agent.cpp:60,163``). The client does not keep the current target in a
        readable context, so no honest external value exists.
        """

        raise _disabled(
            "GetTargetID",
            "the current target id is a DLL global set by a UI-message hook and "
            "is not stored in any readable context",
        )

    # ── account and progression (context) ─────────────────────────────────

    @staticmethod
    def GetAccountName() -> str:
        """Return the account name, or ``""`` when unavailable."""

        client = require_client()
        world_context = Player._world(client)
        if world_context is None:
            return ""
        account_info = world_context.account_info
        if account_info is None:
            return ""
        return account_info.account_name_str or ""

    @staticmethod
    def GetAccountEmail() -> str:
        """Return the sanitized account email, or a deterministic fallback.

        Reforged refuses to answer while the map is not ready or a cinematic is
        playing, because the character context is not trustworthy then.
        """

        from .map import Map

        client = require_client()
        if not Map.IsMapReady():
            return ""
        if Map.IsInCinematic():
            return ""
        if not Player.IsPlayerLoaded():
            return ""
        try:
            char_context = client.read_char_context()
        except (OSError, RuntimeError):
            return Player._account_fallback()
        if char_context is None:
            return Player._account_fallback()
        email = char_context.player_email_str
        return Player._sanitize_account_email_or_fallback(email)


    @staticmethod
    def GetPlayerUUID() -> tuple[int, int, int, int]:
        """Return the four UUID words, or all zeros."""

        client = require_client()
        try:
            char_context = client.read_char_context()
        except (OSError, RuntimeError):
            return (0, 0, 0, 0)
        if char_context is None:
            return (0, 0, 0, 0)
        return Player._uuid_of(char_context)

    @staticmethod
    def _uuid_of(char_context: CharContextStruct) -> tuple[int, int, int, int]:
        """Return the character context UUID as a four-tuple."""

        values = tuple(int(value) for value in (char_context.player_uuid or ()))
        if len(values) < 4:
            return (0, 0, 0, 0)
        return (values[0], values[1], values[2], values[3])


    @staticmethod
    def GetInstanceUptime() -> int:
        """Disabled: the uptime needs the client's frame limit.

        Reforged computes ``agent.timer / UIManager.GetFPSLimit() * 1000``. The
        timer is a context field, but ``GW::ui::GetFrameLimit`` resolves the
        limit through a client function pointer and the graphics-option state, so
        the divisor cannot be obtained by reading memory.
        """

        raise _disabled(
            "GetInstanceUptime",
            "converting the instance timer to milliseconds needs the client's "
            "frame limit, which is read through a client function pointer "
            "(GW::ui::GetFrameLimit)",
        )

    @staticmethod
    def GetRankData() -> tuple[int, int, int, int, int]:
        """Return ``(rank, rating, qualifier_points, wins, losses)``."""

        client = require_client()
        world_context = Player._world(client)
        account_info = world_context.account_info if world_context else None
        if account_info is None:
            return (0, 0, 0, 0, 0)
        values = (
            account_info.rank,
            account_info.rating,
            account_info.qualifier_points,
            account_info.wins,
            account_info.losses,
        )
        if any(value is None for value in values):
            return (0, 0, 0, 0, 0)
        return (
            int(account_info.rank),
            int(account_info.rating),
            int(account_info.qualifier_points),
            int(account_info.wins),
            int(account_info.losses),
        )

    @staticmethod
    def GetTournamentRewardPoints() -> int:
        """Return the account's tournament reward points, or ``0``."""

        client = require_client()
        world_context = Player._world(client)
        account_info = world_context.account_info if world_context else None
        if account_info is None:
            return 0
        return int(account_info.tournament_reward_points)

    @staticmethod
    def GetMorale() -> int:
        """Return the current morale from its duplicated field pair."""

        world_context = Player._world(require_client())
        if world_context is None:
            return 0
        return _pick_highest(int(world_context.morale), int(world_context.morale_dupe))

    @staticmethod
    def GetExperience() -> int:
        """Return the current experience from its duplicated field pair."""

        world_context = Player._world(require_client())
        if world_context is None:
            return 0
        return _pick_highest(
            int(world_context.experience), int(world_context.experience_dupe)
        )

    @staticmethod
    def GetLevel() -> int:
        """Return the current level from its duplicated field pair."""

        world_context = Player._world(require_client())
        if world_context is None:
            return 0
        return _pick_highest(int(world_context.level), int(world_context.level_dupe))

    @staticmethod
    def GetSkillPointData() -> tuple[int, int]:
        """Return ``(current_skill_points, total_earned_skill_points)``.

        Both values are duplicated in the client, and the native runtime resolves
        each through ``PickHighest``.
        """

        world_context = Player._world(require_client())
        if world_context is None:
            return (0, 0)
        return (
            _pick_highest(
                int(world_context.current_skill_points),
                int(world_context.current_skill_points_dupe),
            ),
            _pick_highest(
                int(world_context.total_earned_skill_points),
                int(world_context.total_earned_skill_points_dupe),
            ),
        )

    @staticmethod
    def GetAccountFlags() -> int:
        """Return the raw ``reforged_or_dhuums_flags`` bitfield, or ``0``.

        Bits: ``0x1`` Dhuum's Covenant, ``0x2`` Melandru's Accord, ``0x4``
        Reforged.
        """

        client = require_client()
        player = Player._local_player(client)
        if player is None:
            return 0
        return int(player.reforged_or_dhuums_flags)

    @staticmethod
    def IsDhuumsCovenant() -> bool:
        """Return whether the character is under Dhuum's Covenant."""

        return (Player.GetAccountFlags() & 0x1) != 0

    @staticmethod
    def IsMelandrusAccord() -> bool:
        """Return whether the character is under Melandru's Accord."""

        return (Player.GetAccountFlags() & 0x2) != 0

    @staticmethod
    def IsReforged() -> bool:
        """Return whether the character is in Reforged mode."""

        return (Player.GetAccountFlags() & 0x4) != 0

    # ── mission and faction progress (context) ────────────────────────────

    @staticmethod
    def GetMissionsCompleted() -> list[int]:
        """Return the raw normal-mode mission **bitmap words**.

        These are not one entry per mission. The client stores mission progress
        as ``Array<uint32_t>`` bitmaps of 25 words, where a **set bit means the
        mission is completed and a clear bit means it is locked** (Reforged
        ``Globals.py:17``: ``MISSION_BITMAP_ENTRIES = 25``, "each entry is a
        bitmap of a mission flags (32 bits each)"). A set bit means the mission
        is completed; the caller does its own bit math, as Reforged consumers do.
        """

        return Player._bitmap_words("missions_completed")

    @staticmethod
    def GetMissionsBonusCompleted() -> list[int]:
        """Return the raw normal-mode mission-bonus bitmap words.

        Same bitmap encoding as :meth:`GetMissionsCompleted`, with 16 words.
        """

        return Player._bitmap_words("missions_bonus")

    @staticmethod
    def GetMissionsCompletedHM() -> list[int]:
        """Return the raw hard-mode mission bitmap words."""

        return Player._bitmap_words("missions_completed_hm")

    @staticmethod
    def GetMissionsBonusCompletedHM() -> list[int]:
        """Return the raw hard-mode mission-bonus bitmap words."""

        return Player._bitmap_words("missions_bonus_hm")

    @staticmethod
    def _bitmap_words(name: str) -> list[int]:
        """Return one raw bitmap-word array from the world context."""

        world_context = Player._world(require_client())
        if world_context is None:
            return []
        return list(getattr(world_context, name) or [])





    @staticmethod
    def GetControlledMinions() -> list[tuple[int, int]]:
        """Return ``(agent_id, minion_count)`` for each controlled minion."""

        world_context = Player._world(require_client())
        if world_context is None:
            return []
        minions = world_context.controlled_minions or []
        return [
            (int(minion.agent_id), int(minion.minion_count)) for minion in minions
        ]

    @staticmethod
    def GetLearnableCharacterSkills() -> list[int]:
        """Return skills learnable here, populated at trainers and signets.

        Unlike :meth:`GetUnlockedCharacterSkills`, this array is empty unless a
        trainer window or a signet of capture is active.
        """

        world_context = Player._world(require_client())
        if world_context is None:
            return []
        return list(world_context.learnable_character_skills or [])

    @staticmethod
    def GetUnlockedCharacterSkills() -> list[int]:
        """Return the raw unlocked-skill **bitmap words**.

        Not one entry per skill: the client stores unlocked skills as
        ``Array<uint32_t>`` bitmaps of 108 words, where a **set bit means the
        skill is unlocked** (Reforged ``Globals.py:19``:
        ``SKILL_BITMAP_ENTRIES = 108``). The live client reports 75 set bits.
        """

        world_context = Player._world(require_client())
        if world_context is None:
            return []
        return list(world_context.unlocked_character_skills or [])


    @staticmethod
    def GetKurzickData() -> tuple[int, int, int]:
        """Return ``(current, total_earned, max)`` Kurzick faction."""

        return Player._faction(
            "current_kurzick", "total_earned_kurzick", "max_kurzick"
        )

    @staticmethod
    def GetLuxonData() -> tuple[int, int, int]:
        """Return ``(current, total_earned, max)`` Luxon faction."""

        return Player._faction("current_luxon", "total_earned_luxon", "max_luxon")

    @staticmethod
    def GetImperialData() -> tuple[int, int, int]:
        """Return ``(current, total_earned, max)`` Imperial faction."""

        return Player._faction(
            "current_imperial", "total_earned_imperial", "max_imperial"
        )

    @staticmethod
    def GetBalthazarData() -> tuple[int, int, int]:
        """Return ``(current, total_earned, max)`` Balthazar faction."""

        return Player._faction("current_balth", "total_earned_balth", "max_balth")

    @staticmethod
    def _faction(current: str, total: str, maximum: str) -> tuple[int, int, int]:
        """Return one faction triple, resolving duplicated fields natively.

        ``current`` and ``total`` each have a duplicate; the native runtime
        resolves each through ``PickHighest``, and ``max`` is read directly.

        Reforged returns a *list* on this failure path and a tuple otherwise;
        this port returns a tuple in both cases so the declared type is honest.
        """

        world_context = Player._world(require_client())
        if world_context is None:
            return (0, 0, 0)
        return (
            _pick_highest(
                int(getattr(world_context, current)),
                int(getattr(world_context, current + "_dupe")),
            ),
            _pick_highest(
                int(getattr(world_context, total)),
                int(getattr(world_context, total + "_dupe")),
            ),
            int(getattr(world_context, maximum)),
        )

    # ── titles (context) ──────────────────────────────────────────────────

    @staticmethod
    def GetActiveTitleID() -> int:
        """Return the array index of the active title, or ``0``.

        The player record stores a *tier index*; Reforged finds the title whose
        ``current_title_tier_index`` matches it and returns that title's index.
        """

        client = require_client()
        player = Player._local_player(client)
        if player is None:
            return 0
        active_tier = player.active_title_tier
        titles = Player.GetTitleArrayRaw()
        if active_tier is None or not titles:
            return 0
        for index, title in enumerate(titles):
            if int(title.current_title_tier_index) == int(active_tier):
                return index
        return 0

    @staticmethod
    def GetUnlockedMaps() -> list[int]:
        """Return the raw unlocked-map **bitmap words**.

        Native ``PyPlayer`` exposes this as ``unlocked_maps`` from
        ``world->unlocked_map``, but Reforged's Python ``Player`` never wraps it,
        so this member comes from the native surface. As with the mission and
        skill arrays it is a bitmap: a set bit means the map is unlocked.
        """

        world_context = Player._world(require_client())
        if world_context is None:
            return []
        return list(world_context.unlocked_maps or [])

    @staticmethod
    def IsAgentIDValid(agent_id: int) -> bool:
        """Return whether an agent id resolves to a readable agent record.

        Native ``PyPlayer::IsAgentIDValid``. This is the public spelling of the
        lookup Reforged reaches through ``Agent.GetAgentByID``.
        """

        return Player._agent_by_id(agent_id) is not None

    @staticmethod
    def GetMouseOverID() -> int:
        """Return the agent id under the mouse cursor.

        **Always ``0``.** The native ``PyPlayer`` declares ``mouse_over_id`` and
        exposes it as a property (``player_bindings.cpp:71,360``), but
        ``GetContext`` only ever resets it to ``0`` (line 124) and nothing
        assigns it, so no live value exists in either base project. The member
        is present for source parity and reports ``0`` rather than pretending.
        """

        return 0
    @staticmethod
    def GetTitleArrayRaw() -> list[TitleStruct]:
        """Return the title records."""

        world_context = Player._world(require_client())
        if world_context is None:
            return []
        return list(world_context.titles or [])

    @staticmethod
    def GetTitleArray() -> list[int]:
        """Return the valid title indices."""

        return list(range(len(Player.GetTitleArrayRaw())))

    @staticmethod
    def GetTitle(title_id: int) -> TitleStruct | None:
        """Return one title record by array index, or ``None``."""

        titles = Player.GetTitleArrayRaw()
        if title_id < 0 or title_id >= len(titles):
            return None
        return titles[title_id]

    # ── friend-list status (context) ──────────────────────────────────────

    @staticmethod
    def GetPlayerStatus() -> int:
        """Return the friend-list status value.

        Native ``PyPlayer::GetPlayerStatus`` reads
        ``friend_list->player_status``, so the client's own status is a plain
        context field and is reported as ``Offline`` when no friend list exists.
        """

        client = require_client()
        try:
            friend_list = client.read_friend_list()
        except (OSError, RuntimeError):
            return int(PlayerStatus.Offline)
        if friend_list is None:
            return int(PlayerStatus.Offline)
        return int(friend_list.player_status)

    @staticmethod
    def GetPlayerStatusName() -> str:
        """Return the display name of the current friend-list status."""

        status = PlayerStatus.from_value(Player.GetPlayerStatus())
        return status.display_name if status is not None else "unknown"

    @staticmethod
    def IsTyping() -> bool:
        """Return whether the chat edit box is currently open.

        Reforged asks the client through a native binding; the value it reads is
        a game global holding the typing frame id, which this project already
        reads for ``ConnectedClient.is_typing``. Both read the same bytes, so the
        answers match even though the runtime additionally clears that global
        from a UI-message hook.
        """

        return require_client().is_typing()

    # ── actions (disabled) ────────────────────────────────────────────────

    @staticmethod
    def SetPlayerStatus(status: PlayerStatus | int | str) -> bool:
        """Disabled: changing the status sends a CtoS packet.

        Reforged queues ``PlayerMethods.SetPlayerStatus``, which calls the
        client's own setter from the game thread. An external controller cannot
        make the client emit that packet without code inside it.
        """

        raise _disabled(
            "SetPlayerStatus",
            "setting the status calls the client's own setter through the "
            "in-process game thread so the client emits the CtoS packet",
        )

    @staticmethod
    def ChangeTarget(agent_id: int) -> None:
        """Disabled: targeting runs through the client's target setter.

        Reforged calls ``PyPlayer.ChangeTarget`` on the game thread.
        """

        raise _disabled(
            "ChangeTarget",
            "it calls the client's own target setter from the game thread",
        )

    @staticmethod
    def CallTarget(agent_id: int) -> None:
        """Disabled: call-target dispatches a UI message from inside the client.

        Reforged routes through ``GW::Agents::CallTarget`` and the
        ``kSendCallTarget`` UI message. Reforged defines this method twice; this
        port keeps one definition with identical behavior.
        """

        raise _disabled(
            "CallTarget",
            "it dispatches the kSendCallTarget UI message from inside the client",
        )

    @staticmethod
    def Interact(agent_id: int, call_target: bool = False) -> None:
        """Disabled: interacting runs the client's own agent-interaction call."""

        raise _disabled(
            "Interact",
            "it calls the client's own agent-interaction function from the game "
            "thread",
        )

    @staticmethod
    def Move(x: float, y: float, zPlane: int = 0) -> None:
        """Disabled: movement calls the client's own movement function."""

        raise _disabled(
            "Move",
            "it calls the client's own movement function from the game thread",
        )

    @staticmethod
    def DepositFaction(faction_id: int) -> None:
        """Disabled: depositing faction runs a client action."""

        raise _disabled(
            "DepositFaction",
            "it calls the client's own faction-deposit action from the game thread",
        )

    @staticmethod
    def RemoveActiveTitle() -> None:
        """Disabled: changing the active title runs a client action."""

        raise _disabled(
            "RemoveActiveTitle",
            "it calls the client's own title action from the game thread",
        )

    @staticmethod
    def SetActiveTitle(title_id: int) -> None:
        """Disabled: changing the active title runs a client action."""

        raise _disabled(
            "SetActiveTitle",
            "it calls the client's own title action from the game thread",
        )

    @staticmethod
    def SendRawDialog(dialog_id: int) -> None:
        """Disabled: dialog responses are UI messages raised inside the client."""

        raise _disabled(
            "SendRawDialog",
            "it dispatches the kSendAgentDialog UI message from inside the client",
        )

    @staticmethod
    def BuySkill(skill_id: int) -> None:
        """Disabled: buying a skill runs a client trainer action."""

        raise _disabled(
            "BuySkill",
            "it dispatches a skill-trainer dialog from inside the client",
        )

    @staticmethod
    def UnlockBalthazarSkill(skill_id: int, use_pvp_remap: bool = True) -> None:
        """Disabled: unlocking a skill runs a client vendor action."""

        raise _disabled(
            "UnlockBalthazarSkill",
            "it dispatches a Balthazar skill-unlock dialog from inside the client",
        )

    @staticmethod
    def SendDialog(dialog_id: str | int) -> None:
        """Disabled: dialog responses are raised inside the client."""

        raise _disabled(
            "SendDialog",
            "it sends a dialog through the client's own dialog sender",
        )

    @staticmethod
    def SendAutomaticDialog(button_number: int) -> None:
        """Disabled: it reads the active dialog and sends the chosen button.

        It needs both a readable active dialog, which this project cannot obtain,
        and a dialog sender.
        """

        raise _disabled(
            "SendAutomaticDialog",
            "the active dialog is DLL-owned state and sending the choice needs "
            "the client's dialog sender",
        )

    @staticmethod
    def RequestChatHistory() -> None:
        """Disabled: it asks the client to fetch chat history."""

        raise _disabled(
            "RequestChatHistory",
            "it calls the client's own chat-history request",
        )

    @staticmethod
    def IsChatHistoryReady() -> bool:
        """Disabled: chat history readiness is DLL-owned state."""

        raise _disabled(
            "IsChatHistoryReady",
            "the chat-history buffer is owned by the runtime, not by a readable "
            "context",
        )

    @staticmethod
    def GetChatHistory() -> list[str]:
        """Disabled: chat history is buffered inside the runtime."""

        raise _disabled(
            "GetChatHistory",
            "the chat-history buffer is owned by the runtime, not by a readable "
            "context",
        )

    @staticmethod
    def SendChatCommand(command: str) -> None:
        """Disabled: chat commands are sent by the client."""

        raise _disabled(
            "SendChatCommand",
            "it hands the command to the client, which emits the CtoS packet",
        )

    @staticmethod
    def SendChat(channel: ChatChannel | int, message: str) -> None:
        """Disabled: chat is sent by the client."""

        raise _disabled(
            "SendChat",
            "it hands the message to the client, which emits the CtoS packet",
        )

    @staticmethod
    def SendWhisper(target_name: str, message: str) -> None:
        """Disabled: whispers are sent by the client."""

        raise _disabled(
            "SendWhisper",
            "it hands the whisper to the client, which emits the CtoS packet",
        )

    @staticmethod
    def SendFakeChat(channel: ChatChannel | int, message: str) -> None:
        """Disabled: local chat injection runs inside the client."""

        raise _disabled(
            "SendFakeChat",
            "it injects a local chat line through the client's own chat hook",
        )

    @staticmethod
    def SendFakeChatColored(
        channel: ChatChannel | int, message: str, r: int, g: int, b: int
    ) -> None:
        """Disabled: local chat injection runs inside the client."""

        raise _disabled(
            "SendFakeChatColored",
            "it injects a colored local chat line through the client's own chat hook",
        )

    @staticmethod
    def FormatChatMessage(message: str, r: int, g: int, b: int) -> str:
        """Return ``message`` wrapped in a clamped ``<c=#RRGGBB>`` tag.

        This is the only chat member that is pure string work, so it is ported in
        full even though the senders are disabled.
        """

        r = max(1, min(255, r))
        g = max(1, min(255, g))
        b = max(1, min(255, b))
        return f"<c=#{r:02X}{g:02X}{b:02X}>{message}</c>"
