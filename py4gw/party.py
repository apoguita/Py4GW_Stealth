"""External port of Reforged's ``Py4GWCoreLib/Party.py``, started at the gate.

Reforged's ``Party`` is 810 lines: a main class plus nested ``Players``,
``Heroes``, ``Henchmen`` and ``Pets``. This file exists first because
``Party`` owns the most load-bearing check in the library.

**``Party.IsPlayerLoaded`` is the priority.** In the native runtime it gates the
entire player-context refresh (``PyPlayer::GetContext``,
``player_bindings.cpp:151``), and Reforged's Python calls it from seventeen
sites across eight modules — ``Party``, ``PartyCache``, ``Player``,
``AccountStruct``, ``AgentPartyStruct``, ``agents``, ``interaction`` and
``controller``. Nothing else is worth porting until this works.

Note the two defects this port does **not** reproduce:

* Reforged's ``Party.IsPlayerLoaded`` is a bare ``pass``, so it returns ``None``
  rather than a bool. Implemented here properly.
* Reforged's ``Player.IsPlayerLoaded`` adds a tail — world context, agent
  validity, and ``Agent.GetInstanceUptime(agent_id) > 750`` — that runs only when
  no party member matches, and can return ``True`` where native returns
  ``False``. The native version is used here instead; see
  ``docs/PLAYER_PORT.md``.

Everything not implemented is recorded at the bottom of this module rather than
stubbed into a shape that would lie about working.
"""

from __future__ import annotations

from .client import ConnectedClient, require_client
from .context.party_context import (
    HenchmanPartyMemberStruct,
    HeroPartyMemberStruct,
    PlayerPartyMemberStruct,
    PartyContextStruct,
)
from .context.world_context import WorldContextStruct


def _disabled(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member that needs code inside the client."""

    return NotImplementedError(
        f"Party.{member} is not available from an external reader: {requirement}. "
        "It exists for source parity so a ported script fails at the call site "
        "and names the missing mechanism instead of returning a wrong value."
    )


class Party:
    """Read-only port of the Reforged ``Party`` namespace class."""

    # ── client access ──────────────────────────────────────────────────────


    @staticmethod
    def _context() -> PartyContextStruct | None:
        """Return the party context, or ``None`` while it is unavailable."""

        try:
            return require_client().read_party_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _party() -> object | None:
        """Return the party record, or ``None`` while it is unavailable."""

        context = Party._context()
        return context.player_party if context is not None else None

    @staticmethod
    def _world() -> WorldContextStruct | None:
        """Return the world context, or ``None`` while it is unavailable."""

        try:
            return require_client().read_world_context()
        except (OSError, RuntimeError):
            return None

    # ── the priority check ────────────────────────────────────────────────

    @staticmethod
    def IsPlayerLoaded() -> bool:
        """Return whether this player is connected in a ready map.

        The native implementation (``player_bindings.cpp:30``), which the source
        describes as "parity with legacy ``GW::PartyMgr::GetIsPlayerLoaded(-1)``":

        1. the map is ready — contexts exist and the map is not loading;
        2. the player number is readable;
        3. the party member whose ``login_number`` matches it reports
           ``connected()``;
        4. otherwise ``False``.

        Reforged's Python version is a bare ``pass``; this is the real check.
        """

        client = require_client()
        from .map import Map

        if not Map.IsMapReady():
            return False

        from .player import Player

        player_number = Player.GetPlayerNumber()
        if player_number is None:
            return False
        for member in Party.GetPlayers():
            if int(member.login_number) == player_number:
                return bool(member.is_connected)
        return False

    # ── party identity ────────────────────────────────────────────────────

    @staticmethod
    def GetPartyID() -> int:
        """Return the party's id, or ``0``."""

        party = Party._party()
        return int(getattr(party, "party_id", 0)) if party is not None else 0

    @staticmethod
    def GetPlayers() -> list[PlayerPartyMemberStruct]:
        """Return the current player-party members, or an empty list.

        Reforged returns the native binding's ``players`` list; this returns the
        same records decoded from the party context.
        """

        party = Party._party()
        if party is None:
            return []
        return list(getattr(party, "players", None) or [])

    @staticmethod
    def GetHeroes() -> list[HeroPartyMemberStruct]:
        """Return the current hero-party members, or an empty list."""

        party = Party._party()
        if party is None:
            return []
        return list(getattr(party, "heroes", None) or [])

    @staticmethod
    def GetHenchmen() -> list[HenchmanPartyMemberStruct]:
        """Return the current henchman-party members, or an empty list."""

        party = Party._party()
        if party is None:
            return []
        return list(getattr(party, "henchmen", None) or [])

    @staticmethod
    def GetPlayerCount() -> int:
        """Return how many players are in the party."""

        return len(Party.GetPlayers())

    @staticmethod
    def GetPartySize() -> int:
        """Return how many players are in the party."""

        return len(Party.GetPlayers())

    @staticmethod
    def GetHeroCount() -> int:
        """Return how many heroes are in the party."""

        context = Party._context()
        if context is None:
            return 0
        return int(context.hero_count)

    @staticmethod
    def GetHenchmanCount() -> int:
        """Return how many henchmen are in the party."""

        return len(Party.GetHenchmen())

    @staticmethod
    def GetPartyLeaderID() -> int:
        """Return the party leader's agent id, or ``0``.

        The leader is the first player-party entry, and its agent id comes from
        the world context, exactly as Reforged resolves it.
        """

        players = Party.GetPlayers()
        if not players:
            return 0
        return Party.Players.GetAgentIDByLoginNumber(int(players[0].login_number))

    @staticmethod
    def GetOwnPartyNumber() -> int:
        """Return this player's zero-based index in the party, or ``-1``."""

        from .player import Player

        agent_id = Player.GetAgentID()
        for index, member in enumerate(Party.GetPlayers()):
            if Party.Players.GetAgentIDByLoginNumber(
                int(member.login_number)
            ) == agent_id:
                return index
        return -1

    @staticmethod
    def GetPartyTarget() -> int:
        """Return the party's called target agent id, or ``0``.

        Reforged reads the first player-party entry's ``called_target_id`` and
        accepts it only when the agent is valid.
        """

        if not Party.IsPlayerLoaded():
            return 0
        players = Party.GetPlayers()
        if not players:
            return 0
        target = int(players[0].called_target_id)
        from .player import Player

        return target if Player.IsAgentIDValid(target) else 0

    # ── party state ───────────────────────────────────────────────────────

    @staticmethod
    def IsPartyDefeated() -> bool:
        """Return whether the party has been defeated."""

        context = Party._context()
        return bool(context is not None and context.is_defeated)

    @staticmethod
    def IsPartyLeader() -> bool:
        """Return whether this client is the party leader."""

        context = Party._context()
        return bool(context is not None and context.is_party_leader)

    @staticmethod
    def IsPartyLoaded() -> bool:
        """Return whether the party is loaded.

        Reforged checks the map gate, then ``Player.IsPlayerLoaded``, then the
        native binding's ``is_party_loaded``. That last value is a binding
        property with no readable context field, so this port checks the first
        two and says so rather than reporting a silently weaker answer.
        """

        from .map import Map
        from .player import Player

        if not Map.IsMapReady():
            return False
        return Player.IsPlayerLoaded()

    @staticmethod
    def IsHardModeUnlocked() -> bool:
        """Return whether hard mode is unlocked on this account."""

        world = Party._world()
        return bool(world is not None and int(world.is_hard_mode_unlocked))

    @staticmethod
    def GetPartyMorale() -> list[tuple[int, int]]:
        """Return ``(agent_id, morale)`` per party member, skipping invalid ones.

        Reforged walks ``world->party_morale`` links, follows each link's
        ``party_member_info`` pointer, and skips entries whose agent id does not
        resolve.
        """

        from .player import Player

        world = Party._world()
        if world is None:
            return []
        morale: list[tuple[int, int]] = []
        for link in world.party_morale or []:
            member = link.party_member_info
            if member is None:
                continue
            agent_id = int(member.agent_id)
            if not Player.IsAgentIDValid(agent_id):
                continue
            morale.append((agent_id, int(member.morale)))
        return morale

    # ── actions (disabled) ────────────────────────────────────────────────

    @staticmethod
    def SetHardMode() -> None:
        """Disabled: mode changes are requested through the client."""

        raise _disabled("SetHardMode", "it asks the client to change difficulty")

    @staticmethod
    def SetNormalMode() -> None:
        """Disabled: mode changes are requested through the client."""

        raise _disabled("SetNormalMode", "it asks the client to change difficulty")

    @staticmethod
    def ReturnToOutpost() -> None:
        """Disabled: returning to an outpost runs a client action."""

        raise _disabled(
            "ReturnToOutpost", "it calls the client's own return-to-outpost action"
        )

    @staticmethod
    def LeaveParty() -> None:
        """Disabled: leaving the party runs a client action."""

        raise _disabled("LeaveParty", "it asks the client to leave the party")

    @staticmethod
    def SearchParty(search_type: object, advertisement: object) -> None:
        """Disabled: party search is dispatched inside the client."""

        raise _disabled(
            "SearchParty", "it dispatches a party-search UI message"
        )

    @staticmethod
    def SearchPartyCancel() -> None:
        """Disabled: cancelling a party search is dispatched inside the client."""

        raise _disabled(
            "SearchPartyCancel", "it dispatches a party-search UI message"
        )

    @staticmethod
    def SearchPartyReply(accept: bool = True) -> None:
        """Disabled: replying to a party search is dispatched inside the client."""

        raise _disabled(
            "SearchPartyReply", "it dispatches a party-search UI message"
        )

    @staticmethod
    def RespondToPartyRequest(party_id: int, accept: bool) -> None:
        """Disabled: responding to an invite is dispatched inside the client."""

        raise _disabled(
            "RespondToPartyRequest", "it dispatches a party-invite UI message"
        )

    @staticmethod
    def SetTickasToggle(enable: bool) -> None:
        """Disabled: ticking is dispatched inside the client."""

        raise _disabled("SetTickasToggle", "it dispatches a tick UI message")

    @staticmethod
    def SetTicked(ticked: bool) -> None:
        """Disabled: ticking is dispatched inside the client."""

        raise _disabled("SetTicked", "it dispatches a tick UI message")

    @staticmethod
    def ToggleTicked() -> None:
        """Disabled: ticking is dispatched inside the client."""

        raise _disabled("ToggleTicked", "it dispatches a tick UI message")

    class Players:
        """Reforged's ``Party.Players`` namespace."""

        @staticmethod
        def GetAgentIDByLoginNumber(login_number: int) -> int:
            """Return the agent id registered for a login number, or ``0``.

            Native ``GetAgentIdByLoginNumber`` is
            ``player::GetPlayerByID(login)->agent_id``, which is a world-context
            lookup.
            """

            world = Party._world()
            if world is None:
                return 0
            player = world.GetPlayerById(int(login_number))
            return int(player.agent_id) if player is not None else 0

        @staticmethod
        def GetPartyNumberFromLoginNumber(login_number: int) -> int:
            """Return a login number's index in the party, or ``-1``."""

            for index, member in enumerate(Party.GetPlayers()):
                if int(member.login_number) == int(login_number):
                    return index
            return -1

        @staticmethod
        def GetLoginNumberByAgentID(agent_id: int) -> int:
            """Return the login number whose agent id matches, or ``0``."""

            for member in Party.GetPlayers():
                if (
                    Party.Players.GetAgentIDByLoginNumber(int(member.login_number))
                    == int(agent_id)
                ):
                    return int(member.login_number)
            return 0

        @staticmethod
        def InvitePlayer(agent_id_or_name: object) -> None:
            """Disabled: invites are dispatched inside the client."""

            raise _disabled(
                "Players.InvitePlayer", "it dispatches a party-invite UI message"
            )

        @staticmethod
        def KickPlayer(login_number: int) -> None:
            """Disabled: kicks are dispatched inside the client."""

            raise _disabled(
                "Players.KickPlayer", "it dispatches a party-kick UI message"
            )


class Heroes:
    """Not ported yet: Reforged's ``Party.Heroes`` helpers and actions."""


class Henchmen:
    """Not ported yet: Reforged's ``Party.Henchmen`` actions."""


class Pets:
    """Not ported yet: Reforged's ``Party.Pets`` helpers."""


# ── pending Reforged members, recorded rather than faked ──────────────────
#
# Blocked because the value is a native binding property with no context field:
#   Players.GetPlayerNameByLoginNumber   (needs the agent name decoder)
#   IsPartyLoaded's final check          (native is_party_loaded)
#
# Pending state readers, all reachable in principle from the party context and
# the agent array:
#   IsHardMode, IsNormalMode, IsAllTicked, IsPlayerTicked, GetHeroIndex,
#   IsPartyLeaderByName, GetOthers, IsHeroFlagged, IsAllFlagged, GetAllFlag,
#   GetPetBehavior, GetPetInfo, GetPetID
#
# Pending actions, all of which need in-process code as the disabled members do:
#   Heroes (AddHero, KickHero, FlagHero, SetHeroBehavior, UseSkill, ...),
#   Henchmen (AddHenchman, KickHenchman), Pets (SetPetBehavior)
#
# ``Frame``-based helpers are deferred with the frame-tree work in ``py4gw/ui``.
