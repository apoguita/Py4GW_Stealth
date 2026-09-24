"""Offline tests for the ported ``Player`` class.

Two things are worth testing without a client. First, the parity of the class
surface: every member Reforged's ``Player`` exposes must exist here, so a ported
script cannot fail with ``AttributeError``. Second, the members that are pure
Python or that refuse immediately, neither of which needs a connection.
"""

from __future__ import annotations

import inspect
import re
import unittest

from py4gw.player import ChatChannel, Player, PlayerStatus, _pick_highest

#: Every public member of Reforged's ``Py4GWCoreLib/Player.py``, transcribed from
#: that file. The port must expose all of them.
REFORGED_MEMBERS = (
    "ResolvePlayerStatus",
    "GetPlayerStatusNameFromValue",
    "_sanitize_account_email_or_fallback",
    "_format_uuid_as_email",
    "player_instance",
    "GetPlayerNumber",
    "GetLoginNumber",
    "GetPartyNumber",
    "IsPlayerLoaded",
    "_require_player_loaded",
    "GetAgentID",
    "GetName",
    "GetXY",
    "GetTargetID",
    "GetAgent",
    "GetObservingID",
    "GetAccountName",
    "GetAccountEmail",
    "GetPlayerUUID",
    "GetInstanceUptime",
    "GetRankData",
    "GetTournamentRewardPoints",
    "GetMorale",
    "GetExperience",
    "GetLevel",
    "GetSkillPointData",
    "GetAccountFlags",
    "IsDhuumsCovenant",
    "IsMelandrusAccord",
    "IsReforged",
    "GetMissionsCompleted",
    "GetMissionsBonusCompleted",
    "GetMissionsCompletedHM",
    "GetMissionsBonusCompletedHM",
    "GetControlledMinions",
    "GetLearnableCharacterSkills",
    "GetUnlockedCharacterSkills",
    "GetKurzickData",
    "GetLuxonData",
    "GetImperialData",
    "GetBalthazarData",
    "GetActiveTitleID",
    "GetTitleArrayRaw",
    "GetTitleArray",
    "GetTitle",
    "GetPlayerStatus",
    "GetPlayerStatusName",
    "SetPlayerStatus",
    "ChangeTarget",
    "CallTarget",
    "Interact",
    "Move",
    "DepositFaction",
    "RemoveActiveTitle",
    "SetActiveTitle",
    "SendRawDialog",
    "BuySkill",
    "UnlockBalthazarSkill",
    "SendDialog",
    "SendAutomaticDialog",
    "RequestChatHistory",
    "IsChatHistoryReady",
    "GetChatHistory",
    "IsTyping",
    "SendChatCommand",
    "SendChat",
    "SendWhisper",
    "SendFakeChat",
    "SendFakeChatColored",
    "FormatChatMessage",
)

#: Members Reforged refuses to run, either because the value lives in DLL-owned
#: state or because the member acts on the game.
DISABLED_MEMBERS = (
    "player_instance",
    "GetTargetID",
    "GetInstanceUptime",
    "IsChatHistoryReady",
    "GetChatHistory",
    "SetPlayerStatus",
    "ChangeTarget",
    "CallTarget",
    "Interact",
    "Move",
    "DepositFaction",
    "RemoveActiveTitle",
    "SetActiveTitle",
    "SendRawDialog",
    "BuySkill",
    "UnlockBalthazarSkill",
    "SendDialog",
    "SendAutomaticDialog",
    "RequestChatHistory",
    "SendChatCommand",
    "SendChat",
    "SendWhisper",
    "SendFakeChat",
    "SendFakeChatColored",
)

#: Members this port adds. The public ones are documented in
#: ``docs/PLAYER_PORT.md``; the private ones are internal helpers.
STEALTH_ONLY_PUBLIC_MEMBERS = (
    "GetUnlockedMaps",
    "IsAgentIDValid",
    "GetMouseOverID",
)

#: ``_account_fallback`` is a rename of Reforged's ``_hwnd_account_fallback``;
#: the rest are new helpers with no Reforged counterpart.
STEALTH_ONLY_PRIVATE_MEMBERS = (
    "_account_fallback",
    "_agent_by_id",
    "_local_player",
    "_party_players",
    "_agent_id_for_login",
    "_world",
    "_uuid_of",
    "_faction",
    "_bitmap_words",
)

STEALTH_ONLY_MEMBERS = STEALTH_ONLY_PUBLIC_MEMBERS + STEALTH_ONLY_PRIVATE_MEMBERS


class SurfaceParityTests(unittest.TestCase):
    """Verify the ported class exposes the whole Reforged surface."""

    def test_every_reforged_member_exists(self) -> None:
        """Keep the port from dropping a member Reforged scripts call."""

        missing = [
            name for name in REFORGED_MEMBERS if not hasattr(Player, name)
        ]
        self.assertEqual(missing, [], f"missing Reforged members: {missing}")

    def test_every_member_is_a_staticmethod(self) -> None:
        """Match Reforged, where ``Player`` is a namespace of static methods."""

        for name in REFORGED_MEMBERS:
            with self.subTest(member=name):
                member = inspect_staticmethod(Player, name)
                self.assertTrue(
                    member,
                    f"Player.{name} must be a staticmethod to match Reforged",
                )

    def test_class_exposes_the_status_enum(self) -> None:
        """Keep the Reforged ``Player.PlayerStatus`` attribute available."""

        self.assertIs(Player.PlayerStatus, PlayerStatus)

    def test_stealth_only_members_are_declared(self) -> None:
        """Ensure additions beyond Reforged are deliberate and documented."""

        for name in STEALTH_ONLY_MEMBERS:
            with self.subTest(member=name):
                self.assertTrue(hasattr(Player, name))

    def test_public_additions_are_named_not_shadowing(self) -> None:
        """Keep added members from colliding with Reforged's names."""

        overlap = set(STEALTH_ONLY_PUBLIC_MEMBERS) & set(REFORGED_MEMBERS)
        self.assertEqual(overlap, set())


def inspect_staticmethod(owner: type, name: str) -> bool:
    """Return whether ``owner.name`` is a static method."""

    return isinstance(vars(owner).get(name), staticmethod)


class PlayerStatusTests(unittest.TestCase):
    """Verify the ported status enum and its coercion rules."""

    def test_values_match_native_friend_status(self) -> None:
        """Keep the values aligned with ``GW::Constants::FriendStatus``."""

        self.assertEqual(int(PlayerStatus.Offline), 0)
        self.assertEqual(int(PlayerStatus.Online), 1)
        self.assertEqual(int(PlayerStatus.DoNotDisturb), 2)
        self.assertEqual(int(PlayerStatus.Away), 3)

    def test_dnd_is_an_alias(self) -> None:
        """Keep Reforged's ``DND`` alias pointing at the same member."""

        self.assertIs(PlayerStatus.DND, PlayerStatus.DoNotDisturb)

    def test_from_value_accepts_members_integers_and_names(self) -> None:
        """Coerce each form Reforged accepts."""

        self.assertIs(PlayerStatus.from_value(PlayerStatus.Away), PlayerStatus.Away)
        self.assertIs(PlayerStatus.from_value(1), PlayerStatus.Online)
        self.assertIs(PlayerStatus.from_value("away"), PlayerStatus.Away)
        self.assertIs(
            PlayerStatus.from_value("  Do Not Disturb  "),
            PlayerStatus.DoNotDisturb,
        )
        self.assertIs(PlayerStatus.from_value("do-not-disturb"), PlayerStatus.DoNotDisturb)
        self.assertIs(PlayerStatus.from_value("DND"), PlayerStatus.DoNotDisturb)

    def test_from_value_rejects_unknown_input(self) -> None:
        """Return ``None`` rather than inventing a status."""

        self.assertIsNone(PlayerStatus.from_value(4))
        self.assertIsNone(PlayerStatus.from_value("busy"))
        self.assertIsNone(PlayerStatus.from_value(None))

    def test_display_names(self) -> None:
        """Spell the statuses the way Reforged does."""

        self.assertEqual(PlayerStatus.Offline.display_name, "offline")
        self.assertEqual(PlayerStatus.Online.display_name, "online")
        self.assertEqual(PlayerStatus.Away.display_name, "away")
        self.assertEqual(PlayerStatus.DoNotDisturb.display_name, "do_not_disturb")

    def test_resolve_and_name_helpers(self) -> None:
        """Exercise the two public status helpers."""

        self.assertIs(Player.ResolvePlayerStatus("dnd"), PlayerStatus.DoNotDisturb)
        self.assertEqual(Player.GetPlayerStatusNameFromValue(0), "offline")
        self.assertEqual(Player.GetPlayerStatusNameFromValue("away"), "away")
        # An unknown value falls back to its text form, as Reforged does.
        self.assertEqual(Player.GetPlayerStatusNameFromValue(9), "9")


class ChatChannelTests(unittest.TestCase):
    """Verify the ported chat channel values."""

    def test_standard_channel_values(self) -> None:
        """Keep the channel ids aligned with the client's."""

        self.assertEqual(int(ChatChannel.CHANNEL_ALLIANCE), 0)
        self.assertEqual(int(ChatChannel.CHANNEL_ALL), 3)
        self.assertEqual(int(ChatChannel.CHANNEL_GUILD), 9)
        self.assertEqual(int(ChatChannel.CHANNEL_WHISPER), 14)
        self.assertEqual(int(ChatChannel.CHANNEL_COMMAND), 16)
        self.assertEqual(int(ChatChannel.CHANNEL_UNKNOWN), -1)


class PureHelperTests(unittest.TestCase):
    """Verify the members that need no client at all."""

    def test_format_chat_message_wraps_and_clamps(self) -> None:
        """Emit a clamped colour tag around the message."""

        self.assertEqual(
            Player.FormatChatMessage("hi", 255, 128, 0),
            "<c=#FF8001>hi</c>",
        )
        # Zero becomes 1 and anything above 255 becomes 255.
        self.assertEqual(
            Player.FormatChatMessage("hi", 0, 0, 0),
            "<c=#010101>hi</c>",
        )
        self.assertEqual(
            Player.FormatChatMessage("hi", 999, -5, 300),
            "<c=#FF01FF>hi</c>",
        )

    def test_format_uuid_as_email(self) -> None:
        """Join the four UUID words into the Reforged form."""

        self.assertEqual(
            Player._format_uuid_as_email((1, 2, 3, 4)), "uuid_1_2_3_4"
        )

    def test_format_uuid_handles_missing_values(self) -> None:
        """Return an empty string only for a missing UUID.

        A four-tuple of zeros is a *present* UUID, so it formats to
        ``uuid_0_0_0_0`` exactly as Reforged's truthiness test produces.
        """

        self.assertEqual(Player._format_uuid_as_email(None), "")
        self.assertEqual(Player._format_uuid_as_email(()), "")
        self.assertEqual(
            Player._format_uuid_as_email((0, 0, 0, 0)), "uuid_0_0_0_0"
        )

    def test_sanitize_accepts_a_plain_ascii_email(self) -> None:
        """Pass a usable address through unchanged."""

        self.assertEqual(
            Player._sanitize_account_email_or_fallback("user@example.com"),
            "user@example.com",
        )

    def test_sanitize_truncates_to_the_max_length(self) -> None:
        """Keep the address within the shared-memory bound."""

        address = "a" * 100 + "@example.com"
        result = Player._sanitize_account_email_or_fallback(address)
        self.assertEqual(len(result), Player._ACCOUNT_EMAIL_MAX_LEN)
        self.assertTrue(result.startswith("a"))


class PickHighestTests(unittest.TestCase):
    """Verify the native duplicated-field resolution, which is not ``max``.

    Native ``PickHighest`` (``player_bindings.cpp:56``) discards a field that
    reads ``0`` or ``0xFFFFFFFF`` and returns the higher of the remaining ones.
    A plain ``max`` differs whenever a duplicate reads ``0xFFFFFFFF``, which the
    client does use to mean "not read".
    """

    def test_prefers_the_higher_valid_value(self) -> None:
        """Take the higher of two readable values."""

        self.assertEqual(_pick_highest(10, 20), 20)
        self.assertEqual(_pick_highest(20, 10), 20)

    def test_zero_is_treated_as_unread(self) -> None:
        """Ignore a zero duplicate rather than letting it win."""

        self.assertEqual(_pick_highest(0, 7), 7)
        self.assertEqual(_pick_highest(7, 0), 7)

    def test_invalid_sentinel_is_discarded(self) -> None:
        """Discard ``0xFFFFFFFF``, which ``max`` would wrongly return."""

        self.assertEqual(_pick_highest(0xFFFFFFFF, 7), 7)
        self.assertEqual(_pick_highest(7, 0xFFFFFFFF), 7)
        # The case that distinguishes this from max(): the sentinel is larger.
        self.assertNotEqual(_pick_highest(5, 0xFFFFFFFF), 0xFFFFFFFF)

    def test_both_unread_falls_back_to_zero(self) -> None:
        """Return zero when neither duplicate is readable."""

        self.assertEqual(_pick_highest(0, 0), 0)
        self.assertEqual(_pick_highest(0xFFFFFFFF, 0), 0)
        self.assertEqual(_pick_highest(0, 0xFFFFFFFF), 0)
        self.assertEqual(_pick_highest(0xFFFFFFFF, 0xFFFFFFFF), 0)


class NativeOnlyMemberTests(unittest.TestCase):
    """Verify members taken from the native surface rather than Reforged's."""

    def test_native_only_members_exist(self) -> None:
        """Expose what native ``PyPlayer`` exposes and Reforged's Python does not."""

        for name in (
            "GetUnlockedMaps",
                            "IsAgentIDValid",
            "GetMouseOverID",
        ):
            with self.subTest(member=name):
                self.assertTrue(hasattr(Player, name))

    def test_mouse_over_id_is_zero_without_a_client(self) -> None:
        """Report the documented constant, which never needs a client.

        Native declares ``mouse_over_id`` and exposes it but only ever resets it
        to zero, so there is no live value to fetch.
        """

        self.assertEqual(Player.GetMouseOverID(), 0)

    def test_is_agent_id_valid_rejects_zero(self) -> None:
        """Reject agent id zero without touching the client."""

        self.assertFalse(Player.IsAgentIDValid(0))

    def test_there_is_no_instance_warmup_constant(self) -> None:
        """Keep the arbitrary Reforged-only warm-up threshold removed.

        Reforged's ``Player.IsPlayerLoaded`` requires
        ``Agent.GetInstanceUptime(agent_id) > 750`` in a tail the native runtime
        does not have, and ``750`` appears nowhere in the native tree. Guard
        against it being reintroduced.
        """

        self.assertFalse(hasattr(Player, "_INSTANCE_WARMUP_FRAMES"))
        # Check the body, not the docstring: the docstring deliberately explains
        # the removed threshold and would match these patterns itself.
        source = inspect.getsource(Player.IsPlayerLoaded)
        body = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        self.assertNotIn("750", body)
        self.assertNotIn("GetInstanceUptime", body)


class DisabledMemberTests(unittest.TestCase):
    """Verify disabled members refuse clearly instead of returning a value."""

    def test_actions_raise_not_implemented(self) -> None:
        """Refuse every action member without touching the client."""

        calls = {
            "SetPlayerStatus": lambda: Player.SetPlayerStatus(1),
            "ChangeTarget": lambda: Player.ChangeTarget(1),
            "CallTarget": lambda: Player.CallTarget(1),
            "Interact": lambda: Player.Interact(1),
            "Move": lambda: Player.Move(1.0, 2.0),
            "DepositFaction": lambda: Player.DepositFaction(0),
            "RemoveActiveTitle": Player.RemoveActiveTitle,
            "SetActiveTitle": lambda: Player.SetActiveTitle(1),
            "SendRawDialog": lambda: Player.SendRawDialog(1),
            "BuySkill": lambda: Player.BuySkill(1),
            "UnlockBalthazarSkill": lambda: Player.UnlockBalthazarSkill(1),
            "SendDialog": lambda: Player.SendDialog(1),
            "SendAutomaticDialog": lambda: Player.SendAutomaticDialog(0),
            "RequestChatHistory": Player.RequestChatHistory,
            "SendChatCommand": lambda: Player.SendChatCommand("/help"),
            "SendChat": lambda: Player.SendChat(0, "hi"),
            "SendWhisper": lambda: Player.SendWhisper("name", "hi"),
            "SendFakeChat": lambda: Player.SendFakeChat(0, "hi"),
            "SendFakeChatColored": lambda: Player.SendFakeChatColored(0, "hi", 1, 2, 3),
            "player_instance": Player.player_instance,
        }
        for name, call in calls.items():
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(f"Player.{name}", str(caught.exception))

    def test_capture_backed_members_raise_not_implemented(self) -> None:
        """Refuse members whose value only exists inside the client."""

        for name, call in (
            ("GetTargetID", Player.GetTargetID),
            ("GetInstanceUptime", Player.GetInstanceUptime),
            ("IsChatHistoryReady", Player.IsChatHistoryReady),
            ("GetChatHistory", Player.GetChatHistory),
        ):
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(f"Player.{name}", str(caught.exception))

    def test_error_names_the_missing_mechanism(self) -> None:
        """Explain what would be required, rather than only refusing."""

        with self.assertRaises(NotImplementedError) as caught:
            Player.Move(1.0, 2.0)
        message = str(caught.exception)
        self.assertIn("game thread", message)
        self.assertIn("source parity", message)

    def test_disabled_and_implemented_sets_are_disjoint(self) -> None:
        """Keep a member from being both ported and refused."""

        overlap = set(DISABLED_MEMBERS) & set(STEALTH_ONLY_MEMBERS)
        self.assertEqual(overlap, set())
        for name in DISABLED_MEMBERS:
            with self.subTest(member=name):
                self.assertIn(name, REFORGED_MEMBERS)


class ConnectedMemberGuardTests(unittest.TestCase):
    """Verify implemented members need a connected client, not a silent zero."""

    def test_implemented_members_raise_without_a_client(self) -> None:
        """Fail loudly when nothing is connected, instead of returning 0."""

        # These members must never be reachable without a recorded client, and
        # the test suite never calls connect(), so every one of them must refuse.
        for name, call in (
            ("GetPlayerNumber", Player.GetPlayerNumber),
            ("GetLevel", Player.GetLevel),
            ("GetAgentID", Player.GetAgentID),
            ("IsPlayerLoaded", Player.IsPlayerLoaded),
            ("GetPlayerUUID", Player.GetPlayerUUID),
            ("GetTitleArrayRaw", Player.GetTitleArrayRaw),
            ("GetPlayerStatus", Player.GetPlayerStatus),
            ("IsTyping", Player.IsTyping),
            ("GetKurzickData", Player.GetKurzickData),
        ):
            with self.subTest(member=name):
                with self.assertRaises(RuntimeError) as caught:
                    call()
                self.assertIn("connect()", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
