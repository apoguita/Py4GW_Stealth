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
from unittest import mock

from py4gw import dialog
from py4gw import player as player_module
from py4gw.game_thread.shared_block import EventKind, EventRecord
from py4gw.player import ChatChannel, Player, PlayerStatus, _pick_highest


def _message(
    kind: int, arg0: int = 0, arg1: int = 0, arg2: int = 0, arg3: int = 0
) -> EventRecord:
    """Build one UI-message event record for the dialog module's capture."""

    return EventRecord(
        kind=EventKind.UI_MESSAGE,
        sequence=kind,
        arg0=arg0,
        arg1=arg1,
        arg2=arg2,
        arg3=arg3,
        tick=0,
    )

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

#: Members this port refuses to run *yet*, either because the value lives in the injected
#: runtime's own in-process state or because the mechanism that would carry the action is not built
#: here. The source runs all of them; the list is this port's work queue.
NOT_PORTED_MEMBERS = (
    "player_instance",
)
#: Members that act on the game by calling the client's own function on the
#: client's own thread. They are ported, so they raise the *connection's* error
#: when nothing is connected, and never ``NotImplementedError``.
#:
#: Each entry is ``(name, call)``; the arguments are nonzero because the source's
#: own guards refuse a zero id before anything is called.
ACTION_MEMBERS = (
    ("SetPlayerStatus", lambda: Player.SetPlayerStatus(1)),
    ("ChangeTarget", lambda: Player.ChangeTarget(1)),
    ("CallTarget", lambda: Player.CallTarget(1)),
    ("Interact", lambda: Player.Interact(1)),
    ("Move", lambda: Player.Move(1.0, 2.0)),
    ("DepositFaction", lambda: Player.DepositFaction(0)),
    ("RemoveActiveTitle", Player.RemoveActiveTitle),
    ("SetActiveTitle", lambda: Player.SetActiveTitle(1)),
    ("SendRawDialog", lambda: Player.SendRawDialog(1)),
    ("SendDialog", lambda: Player.SendDialog(1)),
    ("SendAutomaticDialog", lambda: Player.SendAutomaticDialog(0)),
    # The chat senders reach the client's own sender through :mod:`py4gw.chat`; the opcode is
    # ``/`` for the command form, and the source's own guard refuses anything else.
    ("SendChatCommand", lambda: Player.SendChatCommand("help")),
    ("SendChat", lambda: Player.SendChat("/", "hi")),
    ("SendWhisper", lambda: Player.SendWhisper("name", "hi")),
    # The two log writers reach the client's own chat log through ``chat.WriteChat``, which
    # publishes the UI-message form (``kWriteToChatLog``); nothing is sent to the server.
    ("SendFakeChat", lambda: Player.SendFakeChat(0, "hi")),
    ("SendFakeChatColored", lambda: Player.SendFakeChatColored(0, "hi", 255, 0, 0)),
    # The two skill-trainer sends reach the same ported ``SendRawDialog`` through
    # ``Utils.SkillIdToDialogId`` / ``Utils.BalthazarSkillIdToDialogId``
    # (``native_src/methods/PlayerMethods.py:426-450``). The Balthazar member is called with its
    # default ``use_pvp_remap=True``: its remap reads the skill constant record through the ported
    # ``Skill`` class (``py4gw/skill.py``), and with no connection that read is what the source's own
    # ``except Exception`` catches before the send is attempted.
    ("BuySkill", lambda: Player.BuySkill(1)),
    ("UnlockBalthazarSkill", lambda: Player.UnlockBalthazarSkill(1)),
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
        """Refuse every member that still refuses, without touching the client.

        ``BuySkill``/``UnlockBalthazarSkill`` left this list when ``Utils`` landed, and
        ``RequestChatHistory`` left it when the chat-history trio was ported — that member now reads
        the client's log (a usage error without a connection, exercised in
        :class:`ChatHistoryTests`). What is left is the one member that returns a runtime-owned
        object, which is the documented divergence.
        """

        calls = {
            "player_instance": Player.player_instance,
        }
        for name, call in calls.items():
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(f"Player.{name}", str(caught.exception))

    def test_the_obsolete_instance_member_reports_itself(self) -> None:
        """``player_instance`` is a port artifact, not a work item.

        It returned Reforged's in-process ``PyPlayer`` object. This project has no player object and
        needs none — every value that object provided is answered by this class's own members — so
        the member raises and says exactly that, rather than returning a stand-in, and nothing else
        in the port calls it.
        """

        with self.assertRaises(NotImplementedError) as caught:
            Player.player_instance()
        message = str(caught.exception)
        self.assertIn("Player.player_instance", message)
        self.assertIn("port artifact", message)
        self.assertIn("no player object", message)

    def test_get_instance_uptime_delegates_to_the_agent_class(self) -> None:
        """``Player.py:322-329`` is one line: ``Agent.GetInstanceUptime(Player.GetAgentID())``."""

        with mock.patch("py4gw.player.Player.GetAgentID", staticmethod(lambda: 1153)), mock.patch(
            "py4gw.agent.Agent.GetInstanceUptime", staticmethod(lambda agent_id: 123_456)
        ):
            self.assertEqual(Player.GetInstanceUptime(), 123_456)

    def test_not_ported_and_implemented_sets_are_disjoint(self) -> None:
        """Keep a member from being both ported and refused."""

        overlap = set(NOT_PORTED_MEMBERS) & set(STEALTH_ONLY_MEMBERS)
        self.assertEqual(overlap, set())
        for name in NOT_PORTED_MEMBERS:
            with self.subTest(member=name):
                self.assertIn(name, REFORGED_MEMBERS)


class ChatHistoryTests(unittest.TestCase):
    """``RequestChatHistory``/``IsChatHistoryReady``/``GetChatHistory`` over a fake client.

    The members are native's own statics (``player_bindings.cpp:273-325``), so what an offline test
    can drive is the state machine around them: the flag starts false and is cleared on every
    request, a log the client cannot be asked for answers ready-with-nothing, and the narrow
    conversion replaces every non-ASCII code unit with ``?`` — the source's own loop.
    """

    def setUp(self) -> None:
        player_module._chat_history = []
        player_module._chat_ready = False
        self.addCleanup(setattr, player_module, "_chat_history", [])
        self.addCleanup(setattr, player_module, "_chat_ready", False)

    def test_the_flag_starts_false_and_the_history_starts_empty(self) -> None:
        """``g_chat_ready = false`` and an empty vector are what the source declares."""

        self.assertFalse(Player.IsChatHistoryReady())
        self.assertEqual(Player.GetChatHistory(), [])

    def test_a_missing_log_answers_ready_with_nothing(self) -> None:
        """``player_bindings.cpp:281-282``: no log, ready, and nothing collected."""

        client = mock.Mock()
        client.read_chat_buffer = mock.Mock(return_value=None)
        with mock.patch("py4gw.client._current_client", client):
            Player.RequestChatHistory()

        self.assertTrue(Player.IsChatHistoryReady())
        self.assertEqual(Player.GetChatHistory(), [])

    def test_the_history_is_the_converted_lines(self) -> None:
        """A filled buffer is converted the way native converts it, non-ASCII to ``?``."""

        player_module._chat_history = ["hello", "caf?"]
        player_module._chat_ready = True
        self.assertTrue(Player.IsChatHistoryReady())
        self.assertEqual(Player.GetChatHistory(), ["hello", "caf?"])

    def test_a_request_clears_the_previous_answer(self) -> None:
        """``player_bindings.cpp:277-278``: ready false and the vector cleared before the walk."""

        player_module._chat_history = ["old"]
        player_module._chat_ready = True

        client = mock.Mock()
        client.read_chat_buffer = mock.Mock(return_value=None)
        with mock.patch("py4gw.client._current_client", client):
            Player.RequestChatHistory()

        self.assertEqual(Player.GetChatHistory(), [])
        self.assertTrue(Player.IsChatHistoryReady())

    def test_the_narrow_conversion_replaces_non_ascii_with_a_question_mark(self) -> None:
        """``player_bindings.cpp:313-318``: ``*p < 128 ? *p : '?'``, code unit for code unit."""

        decoded = "a\u0108\u0107b\x01"
        converted = "".join(
            chr(ord(character)) if ord(character) < 128 else "?" for character in decoded
        )
        self.assertEqual(converted, "a??b\x01")

    def test_the_timeout_text_is_the_sources(self) -> None:
        """``player_bindings.cpp:306``: ``L"[ERROR: Timeout]"``, character for character."""

        self.assertEqual(player_module._CHAT_HISTORY_TIMEOUT, "[ERROR: Timeout]")
        self.assertEqual(player_module._CHAT_HISTORY_TIMEOUT_S, 0.5)
        self.assertEqual(player_module._CHAT_HISTORY_POLL_S, 0.005)


class ActionMemberTests(unittest.TestCase):
    """The members that act, and what blocks them when nothing is connected.

    They are ported, so they must not report themselves as unavailable — the
    mechanism they need now exists. What they do need is a connection carrying the
    capability layer, and without one the failure has to name that, not the game.
    """

    def test_action_members_are_declared_in_the_source(self) -> None:
        for name, _ in ACTION_MEMBERS:
            with self.subTest(member=name):
                self.assertIn(name, REFORGED_MEMBERS)

    def test_action_members_are_static_methods(self) -> None:
        for name, _ in ACTION_MEMBERS:
            with self.subTest(member=name):
                self.assertIsInstance(
                    inspect.getattr_static(Player, name), staticmethod
                )

    def test_action_members_ask_for_a_connection(self) -> None:
        """Without a client they raise the usage error, not NotImplementedError.

        One member is left out and has its own test below: ``SendAutomaticDialog``
        returns *before* it needs a client when the client has no dialog with buttons
        open, because there is then nothing to click and nothing to call. That is the
        source's own short-circuit (``Py4GWCoreLib/Player.py:883-889``), not a gap.
        """

        for name, call in ACTION_MEMBERS:
            if name == "SendAutomaticDialog":
                continue
            with self.subTest(member=name):
                with self.assertRaises(RuntimeError) as caught:
                    call()
                self.assertIn("connect()", str(caught.exception))

    def test_send_automatic_dialog_waits_for_a_button_before_it_needs_a_client(self) -> None:
        """The one action whose first step needs nothing: no dialog, no call.

        With the dialog module empty the member returns silently. With a button
        announced it goes on to ``Player.SendDialog``, which is where the missing
        connection is reported — so the member asks for one exactly when it has
        something to do.
        """

        dialog._reset()
        self.assertIsNone(Player.SendAutomaticDialog(0), "no dialog: it returns")

        # The state machine directly: the capture's own guards need a connected client with
        # a ready map, and this suite has no connection — so the gate is opened by hand, which
        # is the state a message is in when it reaches the module.
        dialog._callbacks_suspended = False
        dialog._dispatch_message(
            _message(dialog.DIALOG_BODY_MESSAGE, arg1=241)
        )
        dialog._dispatch_message(
            _message(dialog.DIALOG_BUTTON_MESSAGE, arg2=0x0A00002A)
        )
        with self.assertRaises(RuntimeError) as caught:
            Player.SendAutomaticDialog(0)
        self.assertIn("connect()", str(caught.exception))
        dialog._reset()

    def test_action_and_not_ported_sets_do_not_overlap(self) -> None:
        """A member is either ported onto the call path or refused, never both."""

        names = {name for name, _ in ACTION_MEMBERS}
        self.assertEqual(names & set(NOT_PORTED_MEMBERS), set())

    def test_the_two_groups_account_for_every_member_that_once_refused(self) -> None:
        """The members that used to refuse are now 18 that act and 2 that refuse.

        The count moved four times. The three chat senders were ported onto ``GW::chat``
        (``py4gw/chat.py``): ``SendChatCommand``, ``SendChat`` and ``SendWhisper`` act now, which is
        what the source's own chain does — the binding calls ``GW::chat::SendChat``. Then the two
        log writers joined them: ``SendFakeChat`` and ``SendFakeChatColored`` publish the
        UI-message form through ``chat.WriteChat``, which is ``GW::chat::WriteChat``. Then
        ``Utils`` landed (``py4gw/py4gwcorelib_src/utils.py``) and with it ``BuySkill`` and
        ``UnlockBalthazarSkill``, which are the source's ``Utils`` conversion followed by the same
        ported ``SendRawDialog``. Last, the chat-history trio left: ``RequestChatHistory`` fills
        this module's buffer from the client's log and ``IsChatHistoryReady``/``GetChatHistory``
        read it, which is what native's statics do (``player_bindings.cpp:273-325``).
        """

        self.assertEqual(len(ACTION_MEMBERS), 18)
        self.assertEqual(len(NOT_PORTED_MEMBERS), 1)
        for name, _ in ACTION_MEMBERS:
            with self.subTest(member=name):
                self.assertNotIn(name, NOT_PORTED_MEMBERS)

    def test_the_default_balthazar_path_reaches_the_ported_send(self) -> None:
        """``UnlockBalthazarSkill(id)`` converts through ``Utils`` and then asks for a connection.

        Both halves are ported now: the PvP remap reads the skill constant record through the ported
        ``Skill`` class, and the send is the same ported ``SendRawDialog`` the other actions use.
        With nothing connected the conversion's own record read is unavailable — the source's
        ``except Exception`` branch (``Utils.py:801-807``) — and the failure a caller sees is the
        connection's, exactly as for every other action member.
        """

        with self.assertRaises(RuntimeError) as caught:
            Player.UnlockBalthazarSkill(1)
        self.assertIn("connect()", str(caught.exception))

    def test_send_dialog_parses_the_hex_string_the_source_accepts(self) -> None:
        """``Player.SendDialog("0x0A00002A")`` parses before it needs a client.

        The parse is Reforged's own (``Py4GWCoreLib/Player.py:843-848``): a ``str``
        argument is stripped, lower-cased, has ``0x`` removed and is read as base 16.
        With no connection the member then raises the usage error, which is what this
        checks — a bad parse would raise ``ValueError`` instead.
        """

        with self.assertRaises(RuntimeError) as caught:
            Player.SendDialog("0x0A00002A")
        self.assertIn("connect()", str(caught.exception))

        with self.assertRaises(ValueError):
            Player.SendDialog("not-a-dialog-id")


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
            ("GetTargetID", Player.GetTargetID),
        ):
            with self.subTest(member=name):
                with self.assertRaises(RuntimeError) as caught:
                    call()
                self.assertIn("connect()", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
