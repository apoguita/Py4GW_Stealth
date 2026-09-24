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

from enum import IntEnum
from typing import Any

from .client import ConnectedClient, require_client
from .context.party_context import (
    HenchmanPartyMemberStruct,
    HeroPartyMemberStruct,
    PartyContextStruct,
    PartyInfoStruct,
    PlayerPartyMemberStruct,
)
from .context.world_context import PetInfoStruct, WorldContextStruct


def _disabled(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member that needs code inside the client."""

    return NotImplementedError(
        f"Party.{member} is not available from an external reader: {requirement}. "
        "It exists for source parity so a ported script fails at the call site "
        "and names the missing mechanism instead of returning a wrong value."
    )


class HeroType(IntEnum):
    """Native ``GW::Constants::HeroID``, ported from ``Hero_enums.py``."""

    None_ = 0
    Norgu = 1
    Goren = 2
    Tahlkora = 3
    MasterOfWhispers = 4
    AcolyteJin = 5
    Koss = 6
    Dunkoro = 7
    AcolyteSousuke = 8
    Melonni = 9
    ZhedShadowhoof = 10
    GeneralMorgahn = 11
    MagridTheSly = 12
    Zenmai = 13
    Olias = 14
    Razah = 15
    MOX = 16
    KeiranThackeray = 17
    Jora = 18
    PyreFierceshot = 19
    Anton = 20
    Livia = 21
    Hayda = 22
    Kahmu = 23
    Gwen = 24
    Xandra = 25
    Vekk = 26
    Ogden = 27
    MercenaryHero1 = 28
    MercenaryHero2 = 29
    MercenaryHero3 = 30
    MercenaryHero4 = 31
    MercenaryHero5 = 32
    MercenaryHero6 = 33
    MercenaryHero7 = 34
    MercenaryHero8 = 35
    Miku = 36
    ZeiRi = 37
    Devona = 38
    GhostOfAlthea = 39


#: Native ``kHeroNameMap`` (``party_bindings.cpp:173``): display name to id.
#: ``Devona`` and ``GhostOfAlthea`` have no entry in the source table.
HERO_NAME_TO_ID: dict[str, HeroType] = {
    "": HeroType.None_,
    "Norgu": HeroType.Norgu,
    "Goren": HeroType.Goren,
    "Tahlkora": HeroType.Tahlkora,
    "Master Of Whispers": HeroType.MasterOfWhispers,
    "Acolyte Jin": HeroType.AcolyteJin,
    "Koss": HeroType.Koss,
    "Dunkoro": HeroType.Dunkoro,
    "Acolyte Sousuke": HeroType.AcolyteSousuke,
    "Melonni": HeroType.Melonni,
    "Zhed Shadowhoof": HeroType.ZhedShadowhoof,
    "General Morgahn": HeroType.GeneralMorgahn,
    "Magrid The Sly": HeroType.MagridTheSly,
    "Zenmai": HeroType.Zenmai,
    "Olias": HeroType.Olias,
    "Razah": HeroType.Razah,
    "M.O.X.": HeroType.MOX,
    "Keiran Thackeray": HeroType.KeiranThackeray,
    "Jora": HeroType.Jora,
    "Pyre Fierceshot": HeroType.PyreFierceshot,
    "Anton": HeroType.Anton,
    "Livia": HeroType.Livia,
    "Hayda": HeroType.Hayda,
    "Kahmu": HeroType.Kahmu,
    "Gwen": HeroType.Gwen,
    "Xandra": HeroType.Xandra,
    "Vekk": HeroType.Vekk,
    "Ogden Stonehealer": HeroType.Ogden,
    "Mercenary Hero 1": HeroType.MercenaryHero1,
    "Mercenary Hero 2": HeroType.MercenaryHero2,
    "Mercenary Hero 3": HeroType.MercenaryHero3,
    "Mercenary Hero 4": HeroType.MercenaryHero4,
    "Mercenary Hero 5": HeroType.MercenaryHero5,
    "Mercenary Hero 6": HeroType.MercenaryHero6,
    "Mercenary Hero 7": HeroType.MercenaryHero7,
    "Mercenary Hero 8": HeroType.MercenaryHero8,
    "Miku": HeroType.Miku,
    "Zei Ri": HeroType.ZeiRi,
}


class Hero:
    """Native ``PyParty.Hero``, ported from ``party_bindings.cpp:214``.

    The source keeps a hero id and two fields (``hero_name``,
    ``hero_profession``) that neither constructor assigns, so ``GetName`` always
    returns an empty string and ``GetProfession`` always returns ``0``.
    """

    _MAX_ID = int(HeroType.ZeiRi)

    def __init__(self, value: int | str = 0) -> None:
        """Resolve a hero from an id or a display name."""

        if isinstance(value, str):
            self._hero_id = HERO_NAME_TO_ID.get(value, HeroType.None_)
        elif 0 <= int(value) <= Hero._MAX_ID:
            self._hero_id = HeroType(int(value))
        else:
            self._hero_id = HeroType.None_

    def GetID(self) -> int:
        """Return the hero id."""

        return int(self._hero_id)

    def GetName(self) -> str:
        """Return the hero name, which the source never populates."""

        return ""

    def GetProfession(self) -> int:
        """Return the hero profession, which the source never populates."""

        return 0


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
    def _party() -> PartyInfoStruct | None:
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

    @staticmethod
    def party_instance() -> Any:
        """Disabled: Reforged returns a ``PyParty`` native binding object.

        The binding is constructed inside the client; there is nothing to
        construct externally, and every member that used it here reads the party
        context instead.
        """

        raise _disabled(
            "party_instance",
            "it returns a PyParty native binding object, which only exists "
            "inside the client",
        )

    # ── party identity ────────────────────────────────────────────────────

    @staticmethod
    def GetPartyID() -> int:
        """Return the party's id, or ``0``."""

        party = Party._party()
        return int(party.party_id) if party is not None else 0

    @staticmethod
    def GetPlayers() -> list[PlayerPartyMemberStruct]:
        """Return the current player-party members, or an empty list.

        Reforged returns the native binding's ``players`` list; this returns the
        same records decoded from the party context.
        """

        party = Party._party()
        if party is None:
            return []
        return list(party.players or [])

    @staticmethod
    def GetHeroes() -> list[HeroPartyMemberStruct]:
        """Return the current hero-party members, or an empty list."""

        party = Party._party()
        if party is None:
            return []
        return list(party.heroes or [])

    @staticmethod
    def GetHenchmen() -> list[HenchmanPartyMemberStruct]:
        """Return the current henchman-party members, or an empty list."""

        party = Party._party()
        if party is None:
            return []
        return list(party.henchmen or [])

    @staticmethod
    def GetPlayerCount() -> int:
        """Return how many players are in the party."""

        return len(Party.GetPlayers())

    @staticmethod
    def GetPartySize() -> int:
        """Return the party size: players, heroes and henchmen together.

        Native ``get_party_size`` is
        ``players.size() + heroes.size() + henchmen.size()``, not the player
        count.
        """

        return (
            len(Party.GetPlayers())
            + len(Party.GetHeroes())
            + len(Party.GetHenchmen())
        )

    @staticmethod
    def GetHeroCount() -> int:
        """Return how many heroes are in the party.

        Native ``get_party_hero_count`` is ``heroes.size()`` on the party info,
        not the party context's ``hero_count`` field.
        """

        return len(Party.GetHeroes())

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
        """Return whether this client is the party leader.

        Native ``get_is_leader`` takes the first *connected* player in the party
        and returns whether its login number is this player's. That is a
        different computation from ``PartyContext::IsPartyLeader()``, which
        reads bit 7 of the context flag, and the binding uses the former.
        """

        from .player import Player

        players = Party.GetPlayers()
        if not players:
            return False
        player_number = Player.GetPlayerNumber()
        for member in players:
            if bool(member.is_connected):
                return int(member.login_number) == player_number
        return False

    @staticmethod
    def IsPartyLoaded() -> bool:
        """Return whether the party is loaded.

        Reforged checks the map gate, then ``Player.IsPlayerLoaded``, then the
        native ``is_party_loaded``, which is every player-party member reporting
        ``connected()``. All three are now ported.
        """

        from .map import Map
        from .player import Player

        if not Map.IsMapReady():
            return False
        if not Player.IsPlayerLoaded():
            return False
        return Party._is_party_connected()

    @staticmethod
    def _is_party_connected() -> bool:
        """Return whether every player-party member reports ``connected()``.

        Native ``get_is_party_loaded``, which the binding exposes as the
        ``is_party_loaded`` property that ``Party.IsPartyLoaded`` reads last. It
        requires a readable player array; an unreadable or empty one is ``False``
        rather than a vacuous ``True``.

        Private because Reforged's Python surface has no member for it; the
        public member is the composite :meth:`IsPartyLoaded`.
        """

        players = Party.GetPlayers()
        if not players:
            return False
        return all(bool(member.is_connected) for member in players)

    @staticmethod
    def IsHardMode() -> bool:
        """Return whether the party is in hard mode.

        Native ``get_is_party_in_hard_mode`` is
        ``PartyContext::InHardMode()``: bit 4 of the context flag.
        """

        context = Party._context()
        return bool(context is not None and context.in_hard_mode)

    @staticmethod
    def IsNormalMode() -> bool:
        """Return whether the party is in normal mode."""

        return not Party.IsHardMode()

    @staticmethod
    def IsAllTicked() -> bool:
        """Return whether every player-party member is ticked.

        Native ``get_is_party_ticked``: all players ticked, with an unreadable or
        empty player array reporting ``False``.
        """

        players = Party.GetPlayers()
        if not players:
            return False
        return all(bool(member.is_ticked) for member in players)

    @staticmethod
    def IsPlayerTicked(login_number: int) -> bool:
        """Return whether one player-party member is ticked.

        Native ``get_is_player_ticked`` treats its argument as an **index** into
        the player array, with ``0xFFFFFFFF`` meaning "this player", found by
        login number. Reforged's Python names the parameter ``login_number`` and
        passes it straight through, so the name and the meaning disagree in the
        source; the native meaning is kept here.
        """

        from .player import Player

        players = Party.GetPlayers()
        if not players:
            return False
        if login_number == 0xFFFFFFFF:
            player_number = Player.GetPlayerNumber()
            for member in players:
                if int(member.login_number) == player_number:
                    return bool(member.is_ticked)
            return False
        if login_number >= len(players):
            return False
        return bool(players[login_number].is_ticked)

    @staticmethod
    def GetOthers() -> list[int]:
        """Return the agent ids of allies, minions and pets in the party.

        Two different things are called ``others`` in the source. The binding
        owns a ``std::vector<uint32_t> others`` that ``PyParty::GetContext``
        clears and never fills, so the binding's copy is always empty.
        ``GW::Context::PartyInfo::others`` is the game's own array, described
        there as "agent id of allies, minions, pets", and Reforged reads that
        one in ``native_src/context/PartyContext.py:78``. The array is the one
        that carries data, so this reads it.
        """

        party = Party._party()
        if party is None:
            return []
        return [int(value) for value in (party.others or [])]

    @staticmethod
    def GetHeroIndex(hero_id: HeroType | int) -> int:
        """Return a hero's one-based position in the party, or ``0``.

        Native matches on both the hero id and the owning player, and returns
        ``index + 1`` so that ``0`` stays free to mean "not found".
        """

        from .player import Player

        heroes = Party.GetHeroes()
        login_number = Player.GetLoginNumber()
        for index, hero in enumerate(heroes):
            if (
                int(hero.hero_id) == int(hero_id)
                and int(hero.owner_player_id) == login_number
            ):
                return index + 1
        return 0

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
        def GetPlayerNameByLoginNumber(login_number: int) -> str:
            """Disabled: it needs the client's agent name decoder.

            Native ``GetPlayerNameByLoginNumber`` is
            ``agent::GetPlayerNameByLoginNumber``, which returns an encoded
            name buffer. Decoding that buffer is a native call, so the external
            reader cannot produce the name.
            """

            raise _disabled(
                "Players.GetPlayerNameByLoginNumber",
                "it needs the client's encoded-name decoder for arbitrary agents",
            )

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
        """Reforged's ``Party.Heroes`` namespace."""

        @staticmethod
        def GetHeroAgentIDByPartyPosition(hero_position: int) -> int:
            """Return a hero's agent id by party position.

            Native ``get_hero_agent_id``: position ``0`` is the controlled
            character, and ``1..n`` are one-based into the hero array.
            """

            if hero_position == 0:
                from .player import Player

                return Player.GetAgentID()
            heroes = Party.GetHeroes()
            index = hero_position - 1
            if index < 0 or index >= len(heroes):
                return 0
            return int(heroes[index].agent_id)

        @staticmethod
        def GetHeroIDByAgentID(agent_id: int) -> int | None:
            """Return a hero's id by agent id.

            The source returns nothing when no hero matches, which is ``None``
            here rather than a fabricated ``0``.
            """

            for hero in Party.GetHeroes():
                if int(hero.agent_id) == agent_id:
                    return int(hero.hero_id)
            return None

        @staticmethod
        def GetHeroIDByPartyPosition(hero_position: int) -> int | None:
            """Return a hero's id by party position, or ``None``."""

            for index, hero in enumerate(Party.GetHeroes()):
                if index == hero_position:
                    return int(hero.hero_id)
            return None

        @staticmethod
        def GetHeroIdByName(hero_name: str) -> int:
            """Return a hero's id by display name.

            ``Hero(name).GetID()`` resolves against the source's name table
            (``party_bindings.cpp:173``). An unknown name is ``HeroType.None_``.
            """

            hero = Hero(hero_name)
            return hero.GetID()

        @staticmethod
        def GetHeroNameById(hero_id: int) -> str:
            """Return a hero's display name by id.

            **Always empty.** ``Hero::GetName`` returns the ``hero_name`` member
            (``party_bindings.cpp:232``), and neither ``Hero`` constructor ever
            assigns it, so the source cannot produce a name here.
            """

            return Hero(hero_id).GetName()

        @staticmethod
        def GetNameByAgentID(agent_id: int) -> str:
            """Return a hero's display name by agent id.

            **Always empty**, for the same reason as
            :meth:`GetHeroNameById`: the name walk succeeds but the name it asks
            for is never populated.
            """

            for hero in Party.GetHeroes():
                if int(hero.agent_id) == agent_id:
                    return Hero(int(hero.hero_id)).GetName()
            return ""

        @staticmethod
        def GetHeroPartyPositionByAgentID(agent_id: int) -> int:
            """Return a hero's zero-based party position, or ``-1``."""

            for index, hero in enumerate(Party.GetHeroes()):
                if int(hero.agent_id) == agent_id:
                    return index
            return -1

        @staticmethod
        def GetTargetIDByAgentID(agent_id: int) -> int:
            """Return a hero's locked target id, or ``0``.

            The source first requires the agent to be a hero in the party, then
            walks ``world->hero_flags`` for its ``locked_target_id``.
            """

            if Party.Heroes.GetHeroPartyPositionByAgentID(agent_id) < 0:
                return 0
            world = Party._world()
            if world is None:
                return 0
            for hero_flag in world.hero_flags or []:
                if int(hero_flag.agent_id) == agent_id:
                    return int(hero_flag.locked_target_id)
            return 0

        @staticmethod
        def IsHeroFlagged(hero_party_number: int) -> bool:
            """Return whether a hero is flagged.

            Native ``PyParty::IsHeroFlagged`` handles **only** position ``0``,
            where it reports whether the all-flag is set; every other position
            returns ``False``, because the source notes that per-hero flags are
            not reachable through the context it has. That limitation is the
            source's, not this port's.
            """

            if hero_party_number != 0:
                return False
            return Party.Heroes.IsAllFlagged()

        @staticmethod
        def IsAllFlagged() -> bool:
            """Return whether the all-flag is set.

            Native reads ``world->all_flag`` raw and treats a non-zero x or y as
            flagged, so this reads the same three floats directly rather than
            going through ``WorldContextStruct.all_flag``, which withholds
            non-finite values.

            **Finding:** Guild Wars stores an *unset* all-flag as
            ``(+inf, +inf, 0.0)``, and ``inf != 0.0``, so Native's own
            comparison reports ``True`` when nothing is flagged. This port
            reproduces that; it is the source's behaviour, not a read error. The
            flag position is the trustworthy signal - see :meth:`GetAllFlag`.
            """

            world = Party._world()
            if world is None:
                return False
            x = float(world.all_flag_array[0])
            y = float(world.all_flag_array[1])
            return x != 0.0 or y != 0.0

        @staticmethod
        def GetAllFlag() -> tuple[float, float]:
            """Return the all-flag position as ``(x, y)``.

            An unset flag reads back as ``(+inf, +inf)``, the value the game
            stores; ``(0.0, 0.0)`` is only returned when there is no world
            context to read.
            """

            world = Party._world()
            if world is None:
                return (0.0, 0.0)
            return (float(world.all_flag_array[0]), float(world.all_flag_array[1]))

        # ── actions (disabled) ────────────────────────────────────────────

        @staticmethod
        def AddHero(hero_id: int) -> None:
            """Disabled: adding a hero runs a client action."""

            raise _disabled("Heroes.AddHero", "it asks the client to add a hero")

        @staticmethod
        def AddHeroByName(hero_name: str) -> None:
            """Disabled: adding a hero runs a client action."""

            raise _disabled("Heroes.AddHeroByName", "it asks the client to add a hero")

        @staticmethod
        def KickHero(hero_id: int) -> None:
            """Disabled: kicking a hero runs a client action."""

            raise _disabled("Heroes.KickHero", "it asks the client to kick a hero")

        @staticmethod
        def KickHeroByName(hero_name: str) -> None:
            """Disabled: kicking a hero runs a client action."""

            raise _disabled("Heroes.KickHeroByName", "it asks the client to kick a hero")

        @staticmethod
        def KickAllHeroes() -> None:
            """Disabled: kicking heroes runs a client action."""

            raise _disabled("Heroes.KickAllHeroes", "it asks the client to kick its heroes")

        @staticmethod
        def UseSkill(hero_agent_id: int, slot: int, target_id: int) -> None:
            """Disabled: it drives a hero skill through the client's keybinds."""

            raise _disabled(
                "Heroes.UseSkill",
                "it enqueues a client control action for a hero skill",
            )

        @staticmethod
        def SetSkillAIEnabled(hero_agent_id: int, slot: int, enabled: bool) -> None:
            """Disabled: it changes hero skill AI inside the client."""

            raise _disabled(
                "Heroes.SetSkillAIEnabled", "it changes hero skill AI in the client"
            )

        @staticmethod
        def FlagHero(hero_id: int, x: float, y: float) -> None:
            """Disabled: flagging runs a client action."""

            raise _disabled("Heroes.FlagHero", "it asks the client to flag a hero")

        @staticmethod
        def FlagAllHeroes(x: float, y: float) -> None:
            """Disabled: flagging runs a client action."""

            raise _disabled("Heroes.FlagAllHeroes", "it asks the client to flag its heroes")

        @staticmethod
        def UnflagHero(hero_id: int) -> None:
            """Disabled: unflagging runs a client action."""

            raise _disabled("Heroes.UnflagHero", "it asks the client to unflag a hero")

        @staticmethod
        def UnflagAllHeroes() -> None:
            """Disabled: unflagging runs a client action."""

            raise _disabled("Heroes.UnflagAllHeroes", "it asks the client to unflag its heroes")

        @staticmethod
        def SetHeroBehavior(hero_agent_id: int, behavior: int) -> None:
            """Disabled: it changes hero behavior inside the client."""

            raise _disabled(
                "Heroes.SetHeroBehavior", "it changes hero behavior in the client"
            )

    class Henchmen:
        """Reforged's ``Party.Henchmen`` namespace."""

        @staticmethod
        def AddHenchman(henchman_id: int) -> None:
            """Disabled: adding a henchman runs a client action."""

            raise _disabled(
                "Henchmen.AddHenchman", "it asks the client to add a henchman"
            )

        @staticmethod
        def KickHenchman(henchman_id: int) -> None:
            """Disabled: kicking a henchman runs a client action."""

            raise _disabled(
                "Henchmen.KickHenchman", "it asks the client to kick a henchman"
            )

    class Pets:
        """Reforged's ``Party.Pets`` namespace."""

        @staticmethod
        def _pet_info(owner_id: int) -> PetInfoStruct | None:
            """Return the world pet record for an owner, or ``None``.

            Native ``get_pet_info`` walks ``world->pets`` for a matching
            ``owner_agent_id``, and treats owner ``0`` as the controlled
            character.
            """

            world = Party._world()
            if world is None:
                return None
            if owner_id == 0:
                from .player import Player

                owner_id = Player.GetAgentID()
            for pet in world.pets or []:
                if int(pet.owner_agent_id) == owner_id:
                    return pet
            return None

        @staticmethod
        def GetPetInfo(owner_id: int) -> PetInfoStruct:
            """Return the pet record for an owner.

            Native returns the record by value with every field zeroed when the
            owner has no pet, so an absent pet is a zeroed record rather than a
            missing one.
            """

            return Party.Pets._pet_info(owner_id) or PetInfoStruct()

        @staticmethod
        def GetPetBehavior(owner_id: int) -> int:
            """Return a pet's behavior, or ``0`` when it has none."""

            return int(Party.Pets.GetPetInfo(owner_id).behavior)

        @staticmethod
        def GetPetID(owner_id: int) -> int:
            """Return a pet's agent id, or ``0`` when it has none."""

            return int(Party.Pets.GetPetInfo(owner_id).agent_id)

        @staticmethod
        def SetPetBehavior(behavior: int, lock_target_id: int) -> None:
            """Disabled: it changes pet behavior inside the client."""

            raise _disabled(
                "Pets.SetPetBehavior", "it changes pet behavior in the client"
            )


# ── pending Reforged members, recorded rather than faked ──────────────────
#
# None. Every member of Reforged's ``Party``, ``Party.Players``,
# ``Party.Heroes``, ``Party.Henchmen`` and ``Party.Pets`` is present: the ones
# that read a context are implemented, and the actions raise
# ``NotImplementedError`` naming the mechanism they would need.
#
# Two members return a documented constant because the source's own
# implementation can only produce that constant:
#   Party.GetOthers            -- native PyParty::others is never populated
#   Heroes.GetHeroNameById,
#   Heroes.GetNameByAgentID    -- Hero::GetName reads a field no constructor sets
#
# Two members are limited by the source rather than by this port:
#   Heroes.IsHeroFlagged       -- native handles position 0 only, False otherwise
#   Players.IsPlayerTicked     -- native treats its argument as an array index
#
# ``Frame``-based helpers are deferred with the frame-tree work in ``py4gw/ui``.
