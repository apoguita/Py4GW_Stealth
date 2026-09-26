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

Some implemented members **act** rather than read: they change the game, and they
do it by calling the client's own function on the client's own thread through
``py4gw/game_thread``. That needs a connection with the capability layer —
``py4gw.connect()`` installs it by default — so a read-only connection
(``game_thread=False``) refuses them with the connection's own error rather than
calling anything. Which function each one calls, and why that function is the
action rather than the UI message the source sends, is recorded at each member and
in ``docs/PLAYER_PORT.md``.
"""

from __future__ import annotations

import time

from enum import IntEnum
from functools import wraps
from typing import Any, Callable, TypeVar

from .client import ConnectedClient, require_client
from .context.agent_array import AgentAllegiance, AgentStruct
from .context.char_context import CharContextStruct
from .context.world_context import PlayerStruct, TitleStruct, WorldContextStruct
from .game_thread.shared_block import CallForm, DecodeState, float_bits
from . import dialog
from . import chat
from .py4gwcorelib_src.utils import Utils

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


#: Reforged's Python reaches the channel values as ``Player.ChatChannel``
#: (``enums_src/UI_enums.py:35-55``) while Native declares them in ``GW::chat``
#: (``common/constants/chat.h``), so the class is declared in :mod:`py4gw.chat` and re-exported
#: here: one declaration, both names.
ChatChannel = chat.ChatChannel


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise
    is what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"Player.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


#: ``static std::vector<std::string> g_chat_history;`` (``player_bindings.cpp:273``): the decoded
#: chat history ``GetChatHistory`` answers with. The source keeps it beside the bindings, which is
#: this module for the ported ``Player``.
_chat_history: list[str] = []

#: ``static bool g_chat_ready = false;`` (``player_bindings.cpp:274``): whether a request has
#: finished. It starts false and ``RequestChatHistory`` clears it again on every call.
_chat_ready: bool = False

#: ``decoded_chat[i] = L"[ERROR: Timeout]"`` (``player_bindings.cpp:306``): what an entry the
#: client did not answer in time becomes. The text is the source's, character for character.
_CHAT_HISTORY_TIMEOUT = "[ERROR: Timeout]"

#: ``>= 500`` milliseconds from the request's own start (``player_bindings.cpp:292`, `305``), and
#: the source's 5 ms poll between looks (``player_bindings.cpp:303``).
_CHAT_HISTORY_TIMEOUT_S = 0.5
_CHAT_HISTORY_POLL_S = 0.005


def _decode_chat_message(message: str, start_time: float) -> str:
    """Decode one chat-log line through the client's decoder (``player_bindings.cpp:294-310``).

    ``message`` is the encoded wide line as the log holds it, which is exactly what native hands
    ``AsyncDecodeStr`` (``temp_chat_log[i].c_str()``). The decode is the port's: the string is
    placed for the client (``begin_string_decode``), the client's own decoder is called on its own
    thread (``async_decode_str``), and the emitted stub copies the text into the slot the host
    reads — the same three pieces ``Dialog``'s text uses.

    Two source behaviours are kept exactly. The wait is bounded by **one** deadline taken from the
    request's start, not per entry, so a slow client spends a shared budget the way
    ``player_bindings.cpp:292-309`` spends it. And an **empty** answer is not an answer: native's
    loop condition is ``while (decoded_chat[i].empty())``, so a decoder that answers with nothing
    keeps the entry waiting until the deadline and then gets the timeout text — which is what this
    does too, rather than treating empty as complete.
    """

    from .ui.async_decode import async_decode_str, begin_string_decode, decoded_text

    encoded = message.encode("utf-16-le", errors="surrogatepass") + b"\x00\x00"
    slot = begin_string_decode(encoded)
    started = async_decode_str(encoded, slot)

    text = ""
    if started:
        while True:
            if require_client().bridge.decode_state(slot) is DecodeState.DONE:
                text, _ = decoded_text(slot)
                break
            if time.monotonic() >= start_time + _CHAT_HISTORY_TIMEOUT_S:
                # The client never answered: the slot would otherwise stay in flight for the life
                # of the connection (``DECODE_DEPTH`` of them would exhaust the decoder), so it is
                # given back here. Native has no slot to leak — its callback writes a string.
                require_client().bridge.release_decode(slot)
                break
            time.sleep(_CHAT_HISTORY_POLL_S)

    while not text and time.monotonic() < start_time + _CHAT_HISTORY_TIMEOUT_S:
        time.sleep(_CHAT_HISTORY_POLL_S)
    if not text:
        return _CHAT_HISTORY_TIMEOUT
    return text


class WorldActionId(IntEnum):
    """The world actions the client's own action function takes.

    ``native_src/methods/PlayerMethods.py:12-18`` declares this class in the same
    file as the player methods, and native declares the same enum as
    ``Constants::WorldActionId`` (``include/GW/common/constants/agent.h:7-14``).
    Both agree, including that ``InteractEnemy`` is ``0`` — the value a
    ``kSendWorldAction`` packet carries by default.
    """

    INTERACT_ENEMY = 0
    INTERACT_PLAYER_OR_OTHER = 1
    INTERACT_NPC = 2
    INTERACT_ITEM = 3
    INTERACT_TRADE = 4
    INTERACT_GADGET = 5


class CallTargetType(IntEnum):
    """The kind of call-target alert.

    Native ``Constants::CallTargetType``
    (``include/GW/common/constants/agent.h:16-21``). It has no Reforged Python
    counterpart: Reforged's ``Player.CallTarget`` reaches the native binding,
    which passes ``AttackingOrTargetting`` (``agent_methods.cpp:212-215``).
    """

    FOLLOWING = 0x3
    MORALE = 0x7
    ATTACKING_OR_TARGETTING = 0xA
    NONE = 0xFF


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
        """Obsolete port artifact: it returned Reforged's in-process ``PyPlayer`` object.

        Reforged's Python reaches every value through ``Player.player_instance().X()``; that object
        is a binding the injected runtime owns in-process, and **this project has no player object
        and does not need one** — every member of this class answers the same data directly from the
        contexts and the capture layer, which is why nothing else here calls it.

        It is kept only because the class surface is the source's, and it raises rather than
        returning a stand-in. It is not a work item: there is nothing to port, because the thing it
        returns no longer has a counterpart or a purpose here.
        """

        raise NotImplementedError(
            "Player.player_instance is a port artifact that is no longer valid: it returned "
            "Reforged's in-process PyPlayer binding object, and this project has no player object. "
            "Every value that object provided is answered by this class's own members — read them "
            "directly instead of through an instance."
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
        """Return the player's current target id, or ``0`` for none.

        Native ``GetTargetId()`` returns ``g_current_target_id``
        (``agent_methods.cpp:65-67``), which the runtime's ``kChangeTarget`` handler
        sets from the client's own notice of the change (``agent.cpp:161-165``). The
        client keeps that value nowhere a reader can reach — it is a message payload
        and nothing else holds it — so this project listens to the same message, and
        the connection keeps the id for the member to read.

        The client reports **changes**, so this is the last target it announced: ``0``
        before the first change and after the target is cleared, which is what the
        source's global holds in both cases. Setting the target it already has
        produces no notice, so the value does not change then either.
        """

        return require_client().target_id

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
        """Retrieve the player's instance uptime (``Player.py:322-329``).

        The source's whole body is ``Agent.GetInstanceUptime(Player.GetAgentID())``, and both halves
        are ported now: the agent record is read from the ported context and the frame limit the
        conversion divides by is native's own ``GW::ui::GetFrameLimit``
        (``py4gw/ui/preferences.py``, reached through ``Agent.GetInstanceUptime``).
        """

        from .agent import Agent

        return Agent.GetInstanceUptime(Player.GetAgentID())

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

        A tier index of ``0`` means **no title is active**, and the source returns
        ``None`` for it before it looks at the title array at all
        (``player_methods.cpp:159-161``). That check is not decoration: without it
        the search matches the first title whose tier index is also ``0`` and
        reports a title the player is not displaying. This port had that bug, and a
        live run is what found it — after ``RemoveActiveTitle()`` the tier is ``0``.
        """

        client = require_client()
        player = Player._local_player(client)
        if player is None:
            return 0
        active_tier = player.active_title_tier
        if not active_tier:
            return 0
        titles = Player.GetTitleArrayRaw()
        if not titles:
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
        """Set the player's friend-list status.

        ``0`` offline, ``1`` online, ``2`` do-not-disturb, ``3`` away. Reforged
        validates the value first — ``PlayerStatus.from_value`` returns ``None``
        for anything else and the member reports ``False`` — then queues
        ``PlayerMethods.SetPlayerStatus``, which refuses a value above ``Away``
        and calls ``PyPlayer.SetPlayerStatus``. Native's binding
        (``player_bindings.cpp:338``) ends at
        ``GW::friend_list::SetFriendListStatus``, which is a call to
        ``SetOnlineStatusFn`` — ``void __cdecl(FriendStatus)``
        (``friend_list_methods.cpp:13``, ``121-127``). That function is what this
        calls, so the client emits the packet itself.
        """

        player_status = PlayerStatus.from_value(status)
        if player_status is None:
            return False
        require_client().call_function(
            "friend_list.set_online_status_func", CallForm.U32, int(player_status)
        )
        return True

    @staticmethod
    def ChangeTarget(agent_id: int) -> None:
        """Change the player's target.

        The source path is two steps and the second one acts.
        ``PyPlayer.ChangeTarget`` (``player_bindings.cpp:237``) refuses a zero id
        and an id that resolves to no agent, then sends ``kSendChangeTarget``;
        the runtime's own handler for that message is what calls the client's
        target setter (``agent.cpp:143-155``). With no runtime inside the client,
        this calls what the handler calls: ``agent.change_target_func(target, 0)``,
        which is the same function the source's ``ChangeTarget`` resolves.

        The binding's guard is applied here, first, exactly as it is there: a
        zero or unresolvable id changes nothing.
        """

        if not agent_id or not Player.IsAgentIDValid(agent_id):
            return
        require_client().call_function(
            "agent.change_target_func", CallForm.U32_U32, agent_id, 0
        )

    @staticmethod
    def CallTarget(agent_id: int) -> None:
        """Broadcast a call-target alert to the party.

        Native ``PyPlayer::CallTarget`` (``player_bindings.cpp:256``) requires a
        nonzero id that resolves to an agent with a living record, then calls
        ``GW::agent::CallTarget(uint32_t)`` (``agent_methods.cpp:227``). That
        branches on allegiance: an enemy is called through ``kSendCallTarget``
        with ``AttackingOrTargetting``, and anything else through
        ``kSendWorldAction`` with ``InteractPlayerOrOther`` and the call flag set.

        Both messages are handled by the runtime, whose handler calls
        ``call_target_func`` and ``do_world_action_func`` respectively
        (``agent.cpp:166-183``), so those two are what this calls.

        Reforged defines this method twice with identical bodies; this port keeps
        one definition, which is the behaviour the second one wins with.
        """

        if not agent_id:
            return
        agent = Player._agent_by_id(agent_id)
        if agent is None or agent.GetAsAgentLiving() is None:
            return

        living = agent.GetAsAgentLiving()
        if living is None:
            return
        if living.allegiance == AgentAllegiance.ENEMY:
            require_client().call_function(
                "agent.call_target_func",
                CallForm.U32_U32,
                int(CallTargetType.ATTACKING_OR_TARGETTING),
                agent_id,
            )
            return
        require_client().call_function(
            "agent.do_world_action_func",
            CallForm.U32_U32_U32,
            int(WorldActionId.INTERACT_PLAYER_OR_OTHER),
            agent_id,
            1,
        )

    @staticmethod
    def Interact(agent_id: int, call_target: bool = False) -> None:
        """Interact with an agent, optionally calling it as a target.

        ``PlayerMethods.InteractAgent``
        (``native_src/methods/PlayerMethods.py:114``) refuses a zero id, resolves
        the agent, picks the world-action id from its type and allegiance, and
        sends ``kSendWorldAction`` with the call flag. Native's
        ``agent::InteractAgent`` (``agent_methods.cpp:157``) does the same and
        additionally calls ``CallTarget`` first when the flag is set. The
        runtime's handler for that message calls
        ``do_world_action_func(action_id, agent_id, suppress)``
        (``agent.cpp:176-183``), which is the call made here.
        """

        if not agent_id:
            return
        agent = Player._agent_by_id(agent_id)
        if agent is None:
            return

        action_id = WorldActionId.INTERACT_ENEMY
        if agent.is_item_type:
            action_id = WorldActionId.INTERACT_ITEM
        elif agent.is_gadget_type:
            action_id = WorldActionId.INTERACT_GADGET
        else:
            living = agent.GetAsAgentLiving()
            if living is None:
                return
            if living.allegiance == AgentAllegiance.ENEMY:
                action_id = WorldActionId.INTERACT_ENEMY
            elif living.allegiance == AgentAllegiance.NPC_MINIPET:
                action_id = WorldActionId.INTERACT_NPC
            else:
                action_id = WorldActionId.INTERACT_PLAYER_OR_OTHER

        if call_target:
            Player.CallTarget(agent_id)

        require_client().call_function(
            "agent.do_world_action_func",
            CallForm.U32_U32_U32,
            int(action_id),
            agent_id,
            1 if call_target else 0,
        )

    @staticmethod
    def Move(x: float, y: float, zPlane: int = 0) -> None:
        """Move the player to a position on its current map.

        ``PlayerMethods.Move`` (``native_src/methods/PlayerMethods.py:157``) fills
        the source's four-float array — ``{x, y, (float)zplane, 0.0}`` — and calls
        ``MoveTo_Func``, declared ``Void_FloatPtr`` (``PlayerMethods.py:24-32``).
        Native's ``agent::Move`` builds the same array
        (``agent_methods.cpp:149-153``). ``agent.move_to_func`` is that resolver in
        this project's catalog, so the array is built in the client and passed by
        address, with the fourth float zero because the client reads it.
        """

        require_client().call_function(
            "agent.move_to_func",
            CallForm.FLOAT_PTR,
            float_bits(x),
            float_bits(y),
            float_bits(float(zPlane)),
        )

    @staticmethod
    def DepositFaction(faction_id: int) -> None:
        """Deposit faction with an ambassador.

        ``0`` is Kurzick and ``1`` is Luxon. ``PlayerMethods.DepositFaction``
        (``native_src/methods/PlayerMethods.py:173``) calls
        ``DepositFaction_Func(0, allegiance, 5000)``, and native's
        ``player::DepositFaction`` passes the same three values
        (``player_methods.cpp:203``). The leading ``0`` and the ``5000`` amount
        are the source's, not this port's.
        """

        require_client().call_function(
            "player.deposit_faction_func",
            CallForm.U32_U32_U32,
            0,
            faction_id,
            5000,
        )

    @staticmethod
    def RemoveActiveTitle() -> None:
        """Clear the player's active title.

        ``RemoveActiveTitleFn`` is ``void __cdecl(void)``
        (``player_methods.cpp:39``), so the call carries no arguments at all —
        which is a different thing from a call with a zero argument.
        """

        require_client().call_function(
            "player.remove_active_title_func", CallForm.NO_ARGS
        )

    @staticmethod
    def SetActiveTitle(title_id: int) -> None:
        """Set the player's active title.

        ``SetActiveTitleFn`` is ``void __cdecl(uint32_t identifier)``
        (``player_methods.cpp:40``), and the identifier is the title id.
        """

        require_client().call_function(
            "player.set_active_title_func", CallForm.U32, title_id
        )

    @staticmethod
    def SendRawDialog(dialog_id: int) -> None:
        """Send a dialog response by its raw dialog id.

        ``PlayerMethods.SendRawDialog``
        (``native_src/methods/PlayerMethods.py:413``) sends ``kSendAgentDialog``
        with the dialog id in ``wparam`` and no packet. The client's own handler
        for that message is ``SendDialogFn`` — ``void __cdecl(uint32_t dialog_id)``
        (``agent_methods.cpp:18``) — and the runtime reaches it by handing the
        message's ``wparam`` straight through as the argument
        (``agent.cpp:138-141``). That function is what this calls, and
        ``agent.send_agent_dialog_func`` is its resolver.
        """

        require_client().call_function(
            "agent.send_agent_dialog_func", CallForm.U32, dialog_id
        )

    @staticmethod
    def BuySkill(skill_id: int) -> None:
        """Buy or learn a skill from a Skill Trainer (``Player.py:816-822``).

        The source queues ``PlayerMethods.SendSkillTrainerDialog``, whose whole body is
        ``Utils.SkillIdToDialogId(skill_id)`` followed by ``PlayerMethods.SendRawDialog``
        (``native_src/methods/PlayerMethods.py:426-436``) — and both halves are ported:
        :func:`py4gw.py4gwcorelib_src.utils.Utils.SkillIdToDialogId` is the source's own OR with
        ``0x0A000000``, and :func:`SendRawDialog` calls the function the runtime's ``_action``
        reaches through ``UIManager.SendUIMessageRaw(kSendAgentDialog, dialog_id, 0)``. The
        ``ActionQueueManager`` that queued it has no ported home; this port's call path runs on the
        client's own thread already, which is what the queue was for (``docs/PLAYER_PORT.md``).
        """

        dialog_skill_id = Utils.SkillIdToDialogId(skill_id)
        Player.SendRawDialog(dialog_skill_id)

    @staticmethod
    def UnlockBalthazarSkill(skill_id: int, use_pvp_remap: bool = True) -> None:
        """Unlock a skill from the Priest of Balthazar vendor (``Player.py:824-831``).

        The source queues ``PlayerMethods.SendBalthazarSkillUnlockDialog``
        (``native_src/methods/PlayerMethods.py:438-450``), whose body is
        ``Utils.BalthazarSkillIdToDialogId(skill_id, use_pvp_remap)`` followed by
        ``PlayerMethods.SendRawDialog`` — the same shape as :func:`BuySkill`, through the same
        ported send.

        Both halves are ported: the conversion reads the skill constant record through the ported
        ``Skill`` class (``py4gw/skill.py``, ``Skill.ExtraData.GetIDPvP``) and the send calls the
        function the runtime's handler reaches. The one thing the default path needs is a
        connection: without one the conversion's own record read is unavailable, which is the
        source's ``except Exception`` branch (``Utils.py:801-807``) and not a substitute for it.
        """

        dialog_skill_id = Utils.BalthazarSkillIdToDialogId(skill_id, use_pvp_remap=use_pvp_remap)
        Player.SendRawDialog(dialog_skill_id)

    @staticmethod
    def SendDialog(dialog_id: str | int) -> None:
        """Send a dialog response to the agent the current dialog belongs to.

        Native ``agent::SendDialog`` (``agent_methods.cpp:28-37``) resolves the agent
        it is answering — ``g_dialog_agent_id``, which the runtime keeps from the
        client's ``kDialogBody`` message — and sends the **gadget** dialog if that
        agent is a gadget and the **agent** dialog otherwise, returning without
        sending when the agent no longer resolves. Both sends are
        ``kSendGadgetDialog``/``kSendAgentDialog``, whose handler passes ``wparam``
        straight to ``SendDialogFn`` — ``void __cdecl(uint32_t dialog_id)``
        (``agent.cpp:138-159``) — so those two functions are what this calls.

        Two boundary differences, both recorded in ``docs/PLAYER_PORT.md``: the agent
        comes from the dialog module's state rather than from the agent module's own
        global (same message, same field, one state instead of two), and the send is
        recorded by :func:`py4gw.dialog._note_sent_dialog` because the runtime records
        it inside the message handler that this port bypasses.

        The dialog id may be given as a number or as the hex string Reforged's Python
        accepts (``Py4GWCoreLib/Player.py:836-851``), which strips a ``0x`` prefix and
        parses the rest as base 16.
        """

        if isinstance(dialog_id, int):
            dialog_value = dialog_id
        else:
            cleaned = dialog_id.strip().lower().replace("0x", "")
            dialog_value = int(cleaned, 16)

        client = require_client()
        active = dialog.get_active_dialog()
        if active is None:
            return
        agent = Player._agent_by_id(active.agent_id)
        if agent is None:
            return

        # The message id **is** the variant: the source's handler is reached by
        # ``kSendGadgetDialog`` for a gadget and ``kSendAgentDialog`` for an agent, and it logs
        # the id it handled. So which one this send is has to be known before the recording,
        # not after it.
        is_gadget = bool(agent.is_gadget_type)
        dialog._note_sent_dialog(
            dialog_value,
            dialog.DIALOG_SEND_GADGET_MESSAGE
            if is_gadget
            else dialog.DIALOG_SEND_AGENT_MESSAGE,
        )
        if is_gadget:
            client.call_function(
                "agent.send_gadget_dialog_func", CallForm.U32, dialog_value
            )
            return
        client.call_function("agent.send_agent_dialog_func", CallForm.U32, dialog_value)

    @staticmethod
    def SendAutomaticDialog(button_number: int) -> None:
        """Click one of the open dialog's buttons, by its visible position.

        ``Py4GWCoreLib/Player.py:854-900``: refuse a negative index, read the active
        dialog's buttons, drop the ones with no dialog id, refuse an index past the
        end, and send the selected button's id through :meth:`SendDialog`. Every one
        of those checks is here in the source's order.

        **One difference.** The source reports each refusal through
        ``PySystem.Console.Log``, which is Reforged's console *inside* the client.
        There is no external equivalent of that console, so the diagnostics are not
        ported; the returns they accompany are, which is what a caller observes.

        ``getattr(button, "dialog_id", 0)`` in the source guards against a binding
        object that may not carry the field. Every button this port builds is a
        :class:`py4gw.dialog.DialogButtonInfo`, which always declares it, so the read
        is direct — the same value, without the dynamic name.
        """

        if button_number < 0:
            return

        available_buttons = [
            button for button in dialog.get_active_dialog_buttons()
            if button.dialog_id != 0
        ]
        if not available_buttons:
            return
        if button_number >= len(available_buttons):
            return

        selected_button = available_buttons[button_number]
        Player.SendDialog(selected_button.dialog_id)

    @staticmethod
    def RequestChatHistory() -> None:
        """Fill the chat history from the client's own log (``player_bindings.cpp:276-323``).

        The source's body, in its own order: clear the buffer and the ready flag; take
        ``GW::chat::GetChatLog()`` and answer ready-with-nothing when it is null; collect the
        non-null messages of the ``CHAT_LOG_LENGTH``-entry ring; decode each of them through
        ``AsyncDecodeStr``; wait up to **500 ms from one start time** for the decodes to land,
        substituting ``L"[ERROR: Timeout]"`` for the ones that do not; convert each decoded wide
        string to a narrow one, replacing every code unit above ASCII with ``?``; store the result
        and set the flag.

        Two things differ, and both are the execution model rather than a choice.
        ``std::thread`` and ``game_thread::Enqueue`` are how the source gets the walk off its own
        thread and the decode onto the client's; this port has no frame loop, so the walk runs at
        the point of request and every client call inside it is issued on the client's own thread
        by the capability layer — the same adaptation the GW.dat load uses. And the wait is on the
        decode slot the emitted stub fills (``py4gw/ui/async_decode.py``) instead of on native's
        ``std::wstring``, with the source's own 500 ms deadline and 5 ms poll.
        """

        global _chat_history, _chat_ready

        _chat_ready = False
        _chat_history = []

        log = chat.GetChatLog()
        if log is None:
            _chat_ready = True
            return

        temp_chat_log: list[str] = []
        for record in log.message_records:
            temp_chat_log.append(record.message_str)

        decoded_chat: list[str] = []
        start_time = time.monotonic()

        for message in temp_chat_log:
            decoded_chat.append(_decode_chat_message(message, start_time))

        converted: list[str] = []
        for decoded in decoded_chat:
            text = ""
            for character in decoded:
                code_unit = ord(character)
                text += chr(code_unit) if code_unit < 128 else "?"
            converted.append(text)

        _chat_history = converted
        _chat_ready = True
    @staticmethod
    def IsChatHistoryReady() -> bool:
        """Return whether the history buffer has been filled (``player_bindings.cpp:324``)."""

        return _chat_ready

    @staticmethod
    def GetChatHistory() -> list[str]:
        """Return the history ``RequestChatHistory`` filled (``player_bindings.cpp:325``)."""

        return _chat_history

    @staticmethod
    def SendChatCommand(command: str) -> None:
        """Send a ``/`` chat command, through the client's own chat sender.

        ``PyPlayer::SendChatCommand`` is ``GW::chat::SendChat('/', msg.c_str())``
        (``player_bindings.cpp:327``), and the ``'/'`` is the command **opcode**
        ``GetChannel`` maps to ``CHANNEL_COMMAND`` (``chat_methods.cpp:53-64``). The facade's
        own body hands the call to Reforged's ``ActionQueueManager``; that manager belongs to the
        injected runtime and has no ported home, so this calls the same function the manager's
        action would have called — :func:`py4gw.chat.SendChat` — which is the port of
        ``GW::chat``'s sender (``chat_methods.cpp:88-103``).
        """

        chat.SendChat("/", command)

    @staticmethod
    def SendChat(channel: ChatChannel | int | str, message: str) -> None:
        """Send a chat message to a channel, through the client's own chat sender.

        ``PyPlayer::SendChat`` is ``GW::chat::SendChat(channel, msg.c_str())``
        (``player_bindings.cpp:328``) and the facade queues that call. The channel the source
        takes is an **opcode character**, not a :class:`ChatChannel` value: ``'!'`` for all,
        ``'@'`` for guild, ``'#'`` for group, ``'$'`` for trade, ``'%'`` for alliance, ``'"'``
        for whisper and ``'/'`` for a command (``chat_methods.cpp:53-64``). An opcode the sender
        does not know sends nothing, which is the source's own guard — and that guard is why
        passing ``ChatChannel.CHANNEL_ALL`` sends nothing: its value is ``3``, and ``3`` is not
        an opcode. That is the source's behaviour, not this port's reading of it.
        """

        chat.SendChat(channel, message)

    @staticmethod
    def SendWhisper(target_name: str, message: str) -> None:
        """Whisper a player, through the client's own chat sender.

        ``PyPlayer::SendWhisper`` is ``GW::chat::SendChat(name.c_str(), msg.c_str())``
        (``player_bindings.cpp:329``) — the *string* overload, which formats
        ``L"\\"%s,%s"`` into the client's own whisper syntax and hands that buffer to the same
        ``g_send_chat_func`` (``chat_methods.cpp:115-127``). It is not ``StartWhisperFn``: that
        ``__fastcall`` opens the whisper frame and is what the *UI* uses, and this member's
        binding does not go near it.
        """

        chat.SendChat(target_name, message)

    @staticmethod
    def SendFakeChat(channel: ChatChannel | int, message: str) -> None:
        """Write a line into this client's own chat log, the way ``SendFakeChat`` does.

        ``PyPlayer::SendFakeChat`` is ``GW::chat::SendFakeChat`` (``player_bindings.cpp:330``),
        which is ``WriteChat`` with ``transient = true`` (``chat_methods.cpp:262-267``): the line is
        *encoded* (``L"\\x108\\x107%s\\x1"``, ``chat_methods.cpp:159``) and handed to the client in a
        ``ui::UIChatMessage {channel, message, channel2}`` packet over ``kWriteToChatLog``
        (``173-202``). :func:`py4gw.chat.WriteChat` is that walk, so this member is the delegation
        its binding is — nothing is sent to the server.
        """

        chat.SendFakeChat(channel, message)

    @staticmethod
    def SendFakeChatColored(
        channel: ChatChannel | int, message: str, r: int, g: int, b: int
    ) -> None:
        """Write a coloured line into this client's own chat log.

        ``GW::chat::SendFakeChatColored`` (``chat_methods.cpp:269-275``) formats the line with
        ``FormatChatMessage`` — the clamping and the ``<c=#RRGGBB>`` wrap this class already
        carries — and writes it as a transient line, which is what
        :func:`py4gw.chat.SendFakeChatColored` does.
        """

        chat.SendFakeChatColored(channel, message, r, g, b)

    @staticmethod
    def FormatChatMessage(message: str, r: int, g: int, b: int) -> str:
        """Return ``message`` wrapped in a clamped ``<c=#RRGGBB>`` tag.

        ``GW::chat::FormatChatMessage`` (``chat_methods.cpp:277-290``): each channel is clamped
        to 1..255 and the tag is upper-case hex. Pure string work, so it is ported whether or not
        the injection that uses it is.
        """

        r = max(1, min(255, r))
        g = max(1, min(255, g))
        b = max(1, min(255, b))
        return f"<c=#{r:02X}{g:02X}{b:02X}>{message}</c>"
