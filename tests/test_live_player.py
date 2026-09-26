"""Live Guild Wars test for the `Player` action members.

Nine members of `py4gw/player.py` act: they change the game by calling the client's
own function on the client's own thread through `py4gw/game_thread`. Offline tests
prove the emitted dispatcher pushes the right arguments; only a running client can
prove the client accepts them.

**The rule this suite follows: a member is tested through the member.** It calls
`Player.Move`, not `agent.move_to_func`; where a report exists, the effect is read
out of the client's own message stream rather than asserted from a call completing.

**Two messages are watched, and only these two.** The client reports its own target
changes (`UIMessage::kChangeTarget`) and its own dialog bodies (`kDialogBody`). Both
carry a packet pointer, which is what makes them safe: the observer dereferences
`wparam`, so watching a message whose `wparam` is a raw value would read a wild
address on the game thread. `kSendAgentDialog` is exactly that case
(`agent.cpp:138-141` passes the dialog id itself), and no `kSend*` message is watched
here for that reason.

**Everything restores what it changes**, and every wait is bounded:

- targeting targets another agent and then clears;
- movement walks a short step and then walks back to the exact starting point;
- a title is removed, switched, and put back;
- the friend-list status is set to the value it already has.

**One test is fenced off, because it starts a fight.** Targeting, calling and
interacting with an *enemy* is the branch the rest of the suite refuses to take: a
call-target on an enemy is a party broadcast, and interacting with one attacks it.
That test runs only when ``PY4GW_LIVE_ENEMY=1`` is set, it prints what it is about to
do, it gives up and walks the character away after ``ENEMY_OBSERVE_S`` seconds, and it
abandons the attempt early if the character's own health falls below
``ENEMY_ABORT_HP``. It is the operator's decision to start a fight; it is not a
suite's.

The one effect this suite cannot take back by itself is a **dialog**, which the
client opens in response to an interaction. Closing it needs the Escape key, and
this project does not synthesise keyboard input — so the interaction test runs last
and hands the client back to the operator with that stated plainly.

Run it from an **elevated** shell, in a map, with Guild Wars running::

    python -m unittest tests.test_live_player -v

What it proves: the six call forms reach the client's own functions and complete on
the game thread; the client's own reports agree with what was asked; the guards the
source declares refuse what they say they refuse; and both hooked functions are back
to their own bytes with the code section unchanged afterwards.

What it does not prove: that these are safe to run unattended — they change game
state on purpose. `DepositFaction` is not tested at all: it needs 5000 faction and an
ambassador to talk to, which is the operator's business rather than the test's.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
import unittest
from typing import Callable

import py4gw
from py4gw import dialog
from py4gw.context.agent_array import AgentAllegiance
from py4gw.game_thread.shared_block import (
    CallForm,
    CommandState,
    EventKind,
    EventRecord,
)
from py4gw.memory import ProcessMemoryReader
from py4gw.player import Player
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

#: The two functions the connection hooks. Their entry bytes are read before and
#: after the run, so "the hooks were taken back out" is checked, not assumed.
HOOK_RESOLVER = "game_thread.leave_game_thread_func"
OBSERVE_RESOLVER = "ui.send_ui_message_func"
HOOK_ENTRY = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
OBSERVE_ENTRY = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")

#: ``UIMessage::kChangeTarget`` (``constants/ui.h:39``): the client's own notice that
#: its target changed. Its packet is ``ChangeTargetUIMsg``, whose first word is the
#: manual target id (``context/ui.h:78-85``).
#:
#: Measured behaviour recorded in ``docs/RESEARCH.md``: the client reports a
#: *change*. Given the target it already has it says nothing at all, which is why
#: every targeting test clears first.
CHANGE_TARGET_MESSAGE = 0x10000020

#: ``UIMessage::kDialogBody`` (``constants/ui.h:75``): the client's own notice that a
#: dialog is open. Its packet is ``DialogBodyInfo`` — ``{type, agent_id, message}``
#: (``context/ui.h:54-58``) — so the agent the dialog belongs to is the second word.
#: Reforged's own runtime reads that field for the same purpose
#: (``agent.cpp:133-137``).
DIALOG_BODY_MESSAGE = 0x100000A6

#: The function every target-changing member ends at, and the one the suite uses to
#: clear the target. ``Player.ChangeTarget(0)`` refuses a zero id because the source's
#: binding does (``player_bindings.cpp:238``), so the clear cannot go through the
#: member; a separate test asserts that refusal.
CHANGE_TARGET_RESOLVER = "agent.change_target_func"

#: ``UIMessage::kSendCallTarget`` (``constants/ui.h:193``). Its ``wparam`` is a
#: ``Context::SendCallTargetPacket*`` — ``{call_type, agent_id}`` — which is what
#: Reforged's own handler dereferences (``agent.cpp:166-174``), so it is a packet
#: pointer and safe to watch. Only the enemy-branch test looks for it, and only to
#: report: a call that reaches the client's own ``call_target_func`` may broadcast
#: without re-sending the message it was named after.
SEND_CALL_TARGET_MESSAGE = 0x30000013

#: Set this to ``1`` to run the enemy-branch test. Off by default because it starts a
#: fight on purpose: the character will approach and attack the agent it picks.
ENEMY_BRANCH_ENV = "PY4GW_LIVE_ENEMY"

#: How far away an enemy may be for the fenced test to pick it, and how long that test
#: watches before giving up and walking the character away. An explorable area does not
#: put an enemy next to the character — the client walking into range is part of what
#: the test is watching for, so the range is generous and the window covers the walk.
ENEMY_RANGE = 4000.0
ENEMY_OBSERVE_S = 20.0
ENEMY_POLL_S = 0.2

#: The test abandons the fight and walks away once the character's own health falls
#: below this fraction of its maximum. The operator asked for an interaction; they did
#: not ask for a death.
ENEMY_ABORT_HP = 0.4

#: How far the movement test walks, in game units, and how long it waits.
MOVE_STEP = 25.0
MOVE_WAIT_S = 3.0
MOVE_MINIMUM = 1.0
RETURN_TOLERANCE = 15.0
NOTICE_WAIT_S = 2.0
ACTION_WAIT_S = 2.0
POLL_S = 0.02

#: How close a candidate has to be before this suite will interact with it: the
#: client walks to a distant target by itself, and this ranges over "close enough
#: that the walk is short". The interaction test runs last, so a short walk cannot
#: disturb a test that follows it.
INTERACT_RANGE = 200.0

#: Reading every agent record to find the nearest would be thousands of remote reads
#: in a busy outpost. The search is capped per kind and reports what it settled for.
CANDIDATE_READ_LIMIT = 60

TEXT_CHUNK = 0x10000


class LivePlayerActionTests(unittest.TestCase):
    """What each action member does, read back from the client's own reports."""

    pid: int
    client: py4gw.ConnectedClient
    events: list[EventRecord]
    completions: list[EventRecord]
    target_agent: int
    interact_agent: int
    interact_distance: float
    enemy_agent: int
    enemy_distance: float
    enemy_count: int
    enemy_nearest: float

    # -- setup -------------------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        if not win32.is_elevated():
            raise unittest.SkipTest(
                "The controller must be elevated: connecting asserts it, and the "
                "write rights are denied without it. Run this suite from an "
                "elevated shell."
            )

        module = win32.get_main_module(cls.pid)
        cls.module_base = int(module["base_address"])
        cls.module_size = int(module["size"])

        # Read-only preflight, before anything is written: both entry byte sequences
        # and a digest of the whole code section to compare against at the end.
        cls.hook_address = cls._resolve(win32, cls.pid, HOOK_RESOLVER)
        cls.observe_address = cls._resolve(win32, cls.pid, OBSERVE_RESOLVER)
        for name, address, expected in (
            (HOOK_RESOLVER, cls.hook_address, HOOK_ENTRY),
            (OBSERVE_RESOLVER, cls.observe_address, OBSERVE_ENTRY),
        ):
            observed = cls._read_entry(win32, cls.pid, address, len(expected))
            if observed != expected:
                raise AssertionError(
                    f"pid {cls.pid}: {name} at 0x{address:08X} holds "
                    f"{observed.hex(' ')}, not {expected.hex(' ')}. Nothing was "
                    "written."
                )
        cls.text_before = cls._text_digest(win32, cls.pid)

        # Connecting installs the capability layer. That is the mode a caller uses,
        # so it is the mode under test.
        cls.client = py4gw.connect(clients[0])
        cls.events = []
        cls.completions = []
        cls.client.callbacks.register(EventKind.UI_MESSAGE, cls.events.append)
        cls.client.callbacks.register(
            EventKind.COMMAND_COMPLETE, cls.completions.append
        )
        cls.client.watch(CHANGE_TARGET_MESSAGE)
        cls.client.watch(DIALOG_BODY_MESSAGE)
        cls.client.watch(SEND_CALL_TARGET_MESSAGE)

        try:
            cls.agent_id = int(Player.GetAgentID())
            cls.xy = Player.GetXY()
            cls.active_title = int(Player.GetActiveTitleID())
            cls.status = int(Player.GetPlayerStatus())
            if not cls.agent_id or cls.xy == (0.0, 0.0):
                raise unittest.SkipTest(
                    "Log a character into a map before running this test: no "
                    "player agent or position was readable, so every action here "
                    "would be aimed at nothing."
                )
            cls.target_agent = cls._first_safe_living(cls.client, cls.agent_id)
            cls.interact_agent, cls.interact_distance = cls._nearest_safe_agent(
                cls.client, cls.xy, cls.agent_id
            )
            cls.enemy_agent, cls.enemy_distance = cls._nearest_enemy(
                cls.client, cls.xy, cls.agent_id
            )
            cls.enemy_count, cls.enemy_nearest = cls.enemy_census(
                cls.client, cls.xy, cls.agent_id
            )
        except BaseException:
            # The layer is installed: take it back out before anything leaves this
            # method, including a skip.
            py4gw.disconnect()
            raise

        print(
            f"\n--- Player action live test, pid {cls.pid} ---\n"
            f"module                     = 0x{cls.module_base:08X} + "
            f"0x{cls.module_size:X}\n"
            f"leave_game_thread_func     = 0x{cls.hook_address:08X}\n"
            f"ui.send_ui_message_func    = 0x{cls.observe_address:08X}\n"
            f"player agent               = {cls.agent_id} at "
            f"({cls.xy[0]:.1f}, {cls.xy[1]:.1f})\n"
            f"active title               = {cls.active_title}\n"
            f"friend-list status         = {cls.status}\n"
            f"targeting candidate        = "
            + (
                f"agent {cls.target_agent}" if cls.target_agent else "none found"
            )
            + "\n"
            f"interaction candidate      = "
            + (
                f"agent {cls.interact_agent} at {cls.interact_distance:.1f} units"
                if cls.interact_agent
                else f"none within {INTERACT_RANGE:.0f} units"
            )
            + "\n"
            f"enemy candidate            = "
            + (
                f"agent {cls.enemy_agent} at {cls.enemy_distance:.1f} units "
                f"({'fenced test enabled' if os.environ.get(ENEMY_BRANCH_ENV) == '1' else 'fenced: set ' + ENEMY_BRANCH_ENV + '=1 to use it'})"
                if cls.enemy_agent
                else f"none within {ENEMY_RANGE:.0f} units "
                f"({cls.enemy_count} living enemies in the array, nearest "
                + (
                    f"{cls.enemy_nearest:.0f} units away)"
                    if cls.enemy_count
                    else "nowhere)"
                )
            )
            + "\n"
            f"watched messages           = kChangeTarget "
            f"0x{CHANGE_TARGET_MESSAGE:08X}, kDialogBody "
            f"0x{DIALOG_BODY_MESSAGE:08X}\n"
            "plan: target then clear, walk "
            f"{MOVE_STEP:.0f} units and back, interact if in range, title "
            "remove/restore,\n      status set to the value it already has. "
            "DepositFaction is not tested (it needs\n      5000 faction and an "
            "ambassador). No enemy is targeted, interacted with, or called.\n"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        py4gw.disconnect()

        win32 = Win32()
        hook_after = cls._read_entry(win32, cls.pid, cls.hook_address, len(HOOK_ENTRY))
        observe_after = cls._read_entry(
            win32, cls.pid, cls.observe_address, len(OBSERVE_ENTRY)
        )
        text_after = cls._text_digest(win32, cls.pid)

        print(
            "\n--- the client was put back as follows ---\n"
            f"game-thread entry after    = {hook_after.hex(' ')}\n"
            f"message entry after        = {observe_after.hex(' ')}\n"
            f"code section before        = {cls.text_before[0][:32]}... "
            f"({cls.text_before[1]} bytes)\n"
            f"code section after         = {text_after[0][:32]}... "
            f"({text_after[1]} bytes)\n"
            "--- end of live Player action test ---"
        )

        if hook_after != HOOK_ENTRY or observe_after != OBSERVE_ENTRY:
            raise AssertionError(
                f"pid {cls.pid}: a hooked function was left patched: "
                f"{hook_after.hex(' ')} and {observe_after.hex(' ')}."
            )
        if text_after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the code section changed during the run: "
                f"{cls.text_before[0]} before, {text_after[0]} after."
            )

    # -- helpers -----------------------------------------------------------

    def action(self, what: str, call: Callable[[], object]) -> None:
        """Run one member and require that its call completed on the game thread.

        The members return ``None``, as the source's do, so the completion event the
        payload publishes is the only evidence available that the call ran at all —
        and it is better evidence than a return value would be, because it is
        written by the code running inside the client.

        Completions are matched by **sequence number**, not by arrival: the listener
        delivers asynchronously, so an earlier call's event can land after the list
        is cleared. A sequence has to be greater than every one seen before the
        member was called to belong to it.
        """

        previous = self.drain_completions()
        published_before = self.client.bridge.header().command_written
        call()
        published_after = self.client.bridge.header().command_written

        self.assertGreater(
            published_after,
            published_before,
            f"{what}: the member published no command at all, so its own guard "
            "returned before it reached the client function. That is the source's "
            "behaviour for an agent it cannot resolve, and it means this test chose "
            "a target the member would not act on.",
        )

        completed = self.wait_for(
            lambda: any(
                event.sequence > previous for event in self.completions
            ),
            ACTION_WAIT_S,
        )
        self.assertTrue(
            completed,
            f"{what}: a command was published (command_written "
            f"{published_before} -> {published_after}) but no completion event "
            f"arrived within {ACTION_WAIT_S}s. Completions seen: "
            f"{[event.sequence for event in self.completions]}",
        )
        event = next(
            event for event in self.completions if event.sequence > previous
        )
        state = int(event.arg1)
        self.assertEqual(
            state,
            CommandState.DONE,
            f"{what}: the call failed inside the client with state {state} and "
            f"result {event.arg2}. A negative result is the payload refusing; see "
            "shared_block.py's RESULT_ constants.",
        )

    def drain_completions(self, settle_s: float = 0.15) -> int:
        """Forget seen completions and return the highest sequence among them.

        The settle delay is the point: an event published by a call this test has
        already waited for may still be in flight to the listener, and counting it
        against the *next* member would be a false failure.

        **Command sequences start at zero.** A command's sequence number is the
        ``command_written`` counter's value before it advances, so the very first
        command published through a block is sequence ``0`` — measured live, after a
        first version of this helper used ``0`` as "nothing seen yet" and waited two
        seconds for an event it had already been handed.
        """

        time.sleep(settle_s)
        highest = max((event.sequence for event in self.completions), default=-1)
        self.completions.clear()
        return highest

    def assert_no_call(self, what: str, settle_s: float = 0.4) -> None:
        """Require that a member published no call at all.

        This is how a guard is checked live: the source refuses the value *before*
        the client function is reached, so nothing should cross the queue.
        """

        previous = self.drain_completions()
        time.sleep(settle_s)
        published = [
            event for event in self.completions if event.sequence > previous
        ]
        self.assertFalse(
            published,
            f"{what} published a call ({published}), but the source refuses that "
            "value before calling anything",
        )

    def saw_message(self, message: int) -> bool:
        """Return whether the client sent ``message`` at all in this window."""

        return any(
            event.kind == EventKind.UI_MESSAGE and event.sequence == message
            for event in self.events
        )

    def notice(self, message: int, word_index: int, value: int) -> bool:
        """Return whether the client reported ``message`` with that word set.

        The observer copies four words of the message's packet, in order, so packet
        word *n* arrives as ``arg{n}``.
        """

        for event in self.events:
            if event.kind != EventKind.UI_MESSAGE or event.sequence != message:
                continue
            words = (event.arg0, event.arg1, event.arg2, event.arg3)
            if words[word_index] == value:
                return True
        return False

    def wait_for(self, predicate: Callable[[], bool], timeout_s: float) -> bool:
        """Poll a predicate over the events the listener thread delivers."""

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(POLL_S)
        return predicate()

    def require_living_agent(self, agent_id: int) -> None:
        """Skip when a chosen agent is no longer one the member would act on.

        Candidates are chosen once, and an agent can disappear or have its movement
        record go stale before the test that uses it runs. Every action member
        applies Reforged's ``GetAgentByID`` guard first, so acting on a vanished
        agent makes the member return without calling anything — which is correct
        behaviour that would otherwise read as a failed call.
        """

        record = self.client.read_agent_by_id(agent_id)
        if record is None or record.GetAsAgentLiving() is None:
            self.skipTest(
                f"agent {agent_id} is no longer a living agent the client can find, "
                "so the member's own guard would return without calling anything. "
                "Nothing was called."
            )

    def clear_target(self) -> None:
        """Put the target back to none, through the call path.

        Not through the member: ``Player.ChangeTarget`` refuses a zero id, which a
        separate test asserts. Clearing is still something this client does on
        request, so the suite does it directly and leaves no target selected.
        """

        record = self.client.call_function(
            CHANGE_TARGET_RESOLVER, CallForm.U32_U32, 0, 0
        )
        self.assertEqual(
            record.state,
            CommandState.DONE,
            f"clearing the target did not complete: state {record.state!r}, "
            f"result {record.result}",
        )

    @staticmethod
    def enemy_census(
        client: py4gw.ConnectedClient, xy: tuple[float, float], own_agent: int
    ) -> tuple[int, float]:
        """Return ``(living enemies in the array, distance to the nearest)``.

        Reported whether or not the fenced test runs: "none found" and "all of them are
        out of range" are different problems, and a skip message that does not tell
        them apart sends the operator looking for the wrong one.
        """

        snapshot = client.read_agent_array()
        if snapshot is None:
            return 0, float("inf")

        count = 0
        nearest = float("inf")
        for reference in snapshot.all:
            if reference.allegiance is not AgentAllegiance.ENEMY:
                continue
            if reference.agent_id in (0, own_agent) or not reference.is_living:
                continue
            count += 1
            record = client.read_agent_by_id(int(reference.agent_id))
            if record is None:
                continue
            distance = math.dist((float(record.pos.x), float(record.pos.y)), xy)
            nearest = min(nearest, distance)
        return count, nearest

    @staticmethod
    def _nearest_enemy(
        client: py4gw.ConnectedClient, xy: tuple[float, float], own_agent: int
    ) -> tuple[int, float]:
        """Return the nearest living enemy, and its distance.

        Only the fenced enemy-branch test asks for this, and it takes the nearest one
        at any distance: an explorable area does not put an enemy next to the
        character, and the client walking into range is part of what that test is
        watching for. The walk is what ``ENEMY_OBSERVE_S`` is sized for.
        """

        snapshot = client.read_agent_array()
        if snapshot is None:
            return 0, 0.0

        best_id, best_distance = 0, 0.0
        for reference in snapshot.all:
            if reference.allegiance is not AgentAllegiance.ENEMY:
                continue
            if reference.agent_id in (0, own_agent) or not reference.is_living:
                continue
            record = client.read_agent_by_id(int(reference.agent_id))
            if record is None or record.GetAsAgentLiving() is None:
                continue
            if float(record.hp) <= 0.0:
                continue
            distance = math.dist((float(record.pos.x), float(record.pos.y)), xy)
            if distance > ENEMY_RANGE:
                continue
            if not best_id or distance < best_distance:
                best_id, best_distance = int(reference.agent_id), distance
        return best_id, best_distance

    def own_health(self) -> tuple[float, int]:
        """Return the controlled character's ``(health fraction, max health)``.

        **The two are different kinds of number, and the source says so.**
        ``AgentLiving.hp`` is a fraction — *"Health in % where 1=100% and 0=0%"*
        (``agent.h:215``) — and ``max_hp`` is an integer that *"only works for
        yourself"* (``agent.h:216``), so for any other agent it reads ``0``.

        This test compared one against the other on its first live run: a character at
        ``1.0`` — full health — was reported as *"down to 1/455, below 40%"*, and the
        run aborted before it observed anything. Both numbers were read correctly; the
        meaning was assumed from the field names instead of taken from the header.
        """

        record = self.client.read_agent_by_id(self.agent_id)
        if record is None:
            return 0.0, 0
        return float(record.hp), int(record.max_hp)

    def distance_to_agent(self, agent_id: int) -> float:
        """Return how far an agent is from the character, or a large number."""

        record = self.client.read_agent_by_id(agent_id)
        if record is None:
            return float("inf")
        return math.dist(
            (float(record.pos.x), float(record.pos.y)), Player.GetXY()
        )

    def restore_position(
        self, before: tuple[float, float], attempts: int = 2
    ) -> None:
        """Walk the character back if an action made the client move it.

        Interacting and calling a target can both make the client walk to the agent.
        That is the client's doing rather than the test's, but the character is left
        wherever it stopped, so the suite puts it back — and says so when it had to.

        Two attempts, because one is not always enough: while the client is still
        walking somewhere of its own accord, a destination issued on top of that can
        be overtaken by the walk it is already running. A live run left the character
        57 units away on the first attempt and would have reported a failure for a
        move that simply needed the second one.
        """

        moved = math.dist(Player.GetXY(), before)
        for attempt in range(1, attempts + 1):
            now = Player.GetXY()
            moved = math.dist(now, before)
            if moved <= RETURN_TOLERANCE:
                return
            self.action(
                f"walking back to ({before[0]:.1f}, {before[1]:.1f})"
                + (f", attempt {attempt}" if attempt > 1 else ""),
                lambda: Player.Move(before[0], before[1]),
            )
            if self.wait_for(
                lambda: math.dist(Player.GetXY(), before) <= RETURN_TOLERANCE,
                MOVE_WAIT_S * 2,
            ):
                print(
                    f"\n  the client walked {moved:.1f} units during the action; "
                    f"walked back{' on the second attempt' if attempt > 1 else ''}"
                )
                return

        self.fail(
            f"the action left the character {moved:.1f} units from where it started "
            f"and it did not walk back in {attempts} attempts; it is at "
            f"{Player.GetXY()}. If a dialog is open, press Escape first — the client "
            "will not walk with one up — then walk back by hand."
        )

    @staticmethod
    def _first_safe_living(client: py4gw.ConnectedClient, own_agent: int) -> int:
        """Return the first living agent that is not the player's own.

        Used for targeting, which needs no distance: the client has no range limit on
        selecting a target.

        The reference is verified with a **full record read**, not with the
        reference's own classification. Reforged's ``GetAgentByID`` requires the
        agent's movement record as well as the array slot (``agent_methods.cpp:80-85``),
        and every member this suite drives applies that guard, so a candidate chosen
        from the lighter classification can turn out to be one the member refuses —
        which looks like a failed call unless the selection is the same test.
        """

        snapshot = client.read_agent_array()
        if snapshot is None:
            return 0
        for reference in snapshot.all:
            if not reference.is_living:
                continue
            if reference.agent_id in (0, own_agent):
                continue
            if reference.allegiance in (None, AgentAllegiance.ENEMY):
                continue
            record = client.read_agent_by_id(int(reference.agent_id))
            if record is None or record.GetAsAgentLiving() is None:
                continue
            return int(reference.agent_id)
        return 0

    @staticmethod
    def _nearest_safe_agent(
        client: py4gw.ConnectedClient, xy: tuple[float, float], own_agent: int
    ) -> tuple[int, float]:
        """Return the nearest agent this suite may interact with, and its distance.

        Three exclusions, all deliberate:

        - **the player's own agent**, because the action would be aimed at the
          character running it. A live run picked the player for both the interact
          and the call-target test before this was added, and both "passed" while
          proving nothing;
        - **enemies**, and anything whose allegiance is unknown, because interacting
          with an enemy starts a fight and calling one broadcasts to the party;
        - anything beyond ``INTERACT_RANGE``, because the client walks to a distant
          target and a test that walks the character across a map is not bounded.

        Candidates are considered in the order most likely to answer with something
        observable: an NPC (a living agent with no login number, so not a player) can
        open a dialog, a gadget may, and another player will not. The search is
        capped per kind, because reading every record in a busy outpost to find the
        true nearest would be thousands of remote reads.
        """

        snapshot = client.read_agent_array()
        if snapshot is None:
            return 0, 0.0

        for wanted in (
            lambda record: record.is_living_type and not int(record.login_number),
            lambda record: record.is_gadget_type,
            lambda record: record.is_living_type,
        ):
            best_id, best_distance = 0, 0.0
            read = 0
            for reference in snapshot.all:
                if reference.agent_id in (0, own_agent):
                    continue
                if reference.allegiance in (None, AgentAllegiance.ENEMY):
                    continue
                if not (reference.is_living or reference.is_gadget):
                    continue
                if read >= CANDIDATE_READ_LIMIT:
                    break
                read += 1
                try:
                    record = client.read_agent(reference)
                except (OSError, RuntimeError):
                    continue
                if record is None or not wanted(record):
                    continue
                distance = math.dist(
                    (float(record.pos.x), float(record.pos.y)), xy
                )
                if distance > INTERACT_RANGE:
                    continue
                if not best_id or distance < best_distance:
                    best_id, best_distance = int(reference.agent_id), distance
            if best_id:
                return best_id, best_distance
        return 0, 0.0

    # -- targeting ---------------------------------------------------------

    def test_targeting_is_reported_by_the_client(self) -> None:
        """``Player.ChangeTarget`` reaches the client's target setter.

        The id is read back out of the client's own ``kChangeTarget`` notice, which
        makes this an asserted effect rather than a claim that a call completed. The
        measure of whether the guard is right is the id the *client* reports.
        """

        if not self.target_agent:
            self.skipTest(
                "no other non-enemy living agent was found to target; the client "
                "reports no change when it is given the target it already has, so "
                "targeting the player's own agent would prove nothing"
            )
        if not Player.IsAgentIDValid(self.target_agent):
            self.skipTest(
                f"agent {self.target_agent} is no longer an id the client resolves, "
                "so Player.ChangeTarget's guard would return without calling. "
                "Nothing was called."
            )

        self.clear_target()
        self.wait_for(lambda: self.notice(CHANGE_TARGET_MESSAGE, 0, 0), NOTICE_WAIT_S)
        self.events.clear()

        self.action(
            f"targeting agent {self.target_agent}",
            lambda: Player.ChangeTarget(self.target_agent),
        )

        self.assertTrue(
            self.wait_for(
                lambda: self.notice(CHANGE_TARGET_MESSAGE, 0, self.target_agent),
                NOTICE_WAIT_S,
            ),
            f"the client did not report a target change to {self.target_agent} "
            f"within {NOTICE_WAIT_S}s. Notices seen: "
            f"{[(hex(event.sequence), event.arg0) for event in self.events]}",
        )
        self.assertEqual(
            Player.GetTargetID(),
            self.target_agent,
            "the client announced this target, and Player.GetTargetID reads the "
            "connection's capture of that same notice, so the two must agree",
        )
        print(
            f"\n  targeted agent {self.target_agent}: the client's own notice says so, "
            f"and Player.GetTargetID() reads {Player.GetTargetID()}"
        )

        self.clear_target()
        self.wait_for(lambda: self.notice(CHANGE_TARGET_MESSAGE, 0, 0), NOTICE_WAIT_S)
        self.assertEqual(
            Player.GetTargetID(),
            0,
            "the client announced that the target was cleared, so GetTargetID must "
            "report none",
        )

    def test_targeting_refuses_a_zero_id_without_calling_anything(self) -> None:
        """``Player.ChangeTarget(0)`` does nothing, because the source refuses it.

        The binding's guard is the first thing it does (``player_bindings.cpp:237``),
        so no call should be published at all. The client function *does* accept a
        zero id — that is how this suite clears the target — which is exactly why the
        guard matters: the member is not the function.
        """

        self.clear_target()
        self.wait_for(lambda: self.notice(CHANGE_TARGET_MESSAGE, 0, 0), NOTICE_WAIT_S)

        self.assert_no_call("Player.ChangeTarget(0)", settle_s=0.6)
        Player.ChangeTarget(0)
        self.assert_no_call("Player.ChangeTarget(0)", settle_s=0.6)

    # -- movement ----------------------------------------------------------

    def test_movement_walks_there_and_back(self) -> None:
        """``Player.Move`` moves the character, and the suite walks it back.

        The effect is read from the client's own world context — ``Player.GetXY()``
        before, after, and after the return — so the position is the client's report
        and not this test's assumption. The step is deliberately small: the client
        paths there itself, and a long walk is not a bounded test.

        Two directions are tried, and that is the test being robust rather than the
        member being lenient: the client refuses a point it cannot path to, so
        standing against a wall to the east makes a +X step do nothing at all. Two
        bounded attempts beat a test that fails because of where the character
        happened to be standing.
        """

        start = Player.GetXY()
        start_x, start_y = start
        if (start_x, start_y) == (0.0, 0.0):
            self.skipTest("the client reports no position; the map may be loading")

        reached = start
        for label, point in (
            ("+X", (start_x + MOVE_STEP, start_y)),
            ("-X", (start_x - MOVE_STEP, start_y)),
        ):
            self.action(
                f"moving {label} to ({point[0]:.1f}, {point[1]:.1f})",
                lambda point=point: Player.Move(point[0], point[1]),
            )
            if self.wait_for(
                lambda: math.dist(Player.GetXY(), start) >= MOVE_MINIMUM,
                MOVE_WAIT_S,
            ):
                reached = Player.GetXY()
                print(
                    f"\n  walked {math.dist(reached, start):.2f} units {label} "
                    f"toward ({point[0]:.1f}, {point[1]:.1f}); returning to the start"
                )
                break
        else:
            self.fail(
                f"the character did not move from ({start_x:.1f}, {start_y:.1f}) "
                f"within {MOVE_WAIT_S}s of either call completing. The client refuses "
                "a path it cannot walk, which is what a wall or a closed door does, so "
                "move the character somewhere open and rerun. If a dialog is open on "
                "the client, press Escape first — the client does not walk with one up."
            )

        self.action(
            f"moving back to ({start_x:.1f}, {start_y:.1f})",
            lambda: Player.Move(start_x, start_y),
        )
        returned = self.wait_for(
            lambda: math.dist(Player.GetXY(), start) <= RETURN_TOLERANCE,
            MOVE_WAIT_S,
        )
        resting = Player.GetXY()

        self.assertTrue(
            returned,
            f"the character did not return to ({start_x:.1f}, {start_y:.1f}) within "
            f"{MOVE_WAIT_S}s; it is at ({resting[0]:.1f}, {resting[1]:.1f}), "
            f"{math.dist(resting, start):.1f} units away. Walk it back "
            "by hand.",
        )

    # -- interaction -------------------------------------------------------

    # -- the enemy branch, fenced ------------------------------------------

    def test_y_enemy_target_call_and_interact(self) -> None:
        """Target an enemy, call it, and interact with it.

        **This starts a fight on purpose**, so it runs only when
        ``PY4GW_LIVE_ENEMY=1`` is set. The other tests refuse the enemy branches for
        exactly this reason; here the operator asked for them, which is what the
        environment variable records.

        Three members, in the order a player would use them:

        1. ``ChangeTarget`` — verified by the client's own ``kChangeTarget`` notice,
           which is the same evidence the friendly targeting test uses;
        2. ``CallTarget`` — an enemy takes the ``call_target_func`` branch
           (``agent_methods.cpp:207-217``), so this is the *other* half of that
           member, and the half a party sees;
        3. ``Interact`` — an enemy takes ``INTERACT_ENEMY``, which is what attacking
           is.

        The effect is read from the client: the enemy's health dropping, or the
        character walking into range. Both are the client's own record. The test gives
        up after ``ENEMY_OBSERVE_S`` seconds, abandons early if the character's health
        falls below ``ENEMY_ABORT_HP``, then clears the target and walks back to where
        the character started.
        """

        if os.environ.get(ENEMY_BRANCH_ENV) != "1":
            self.skipTest(
                f"set {ENEMY_BRANCH_ENV}=1 to run this test: it targets, calls and "
                "interacts with an enemy, which starts a fight. It is fenced because "
                "that is the operator's decision and not a suite's."
            )
        if not self.enemy_agent:
            enemies, nearest = self.enemy_census(
                self.client, Player.GetXY(), self.agent_id
            )
            self.skipTest(
                f"no living enemy within {ENEMY_RANGE:.0f} units. The array holds "
                f"{enemies} living enemies and the nearest is "
                + (f"{nearest:.0f} units away" if enemies else "nowhere — none exist")
                + ". Nothing was targeted, called, or attacked."
            )
        self.require_living_agent(self.enemy_agent)

        enemy = self.client.read_agent_by_id(self.enemy_agent)
        assert enemy is not None
        start_xy = Player.GetXY()
        enemy_health = float(enemy.hp)
        own_health, own_max_health = self.own_health()

        print(
            f"\n--- enemy branch (fenced) ---\n"
            f"  enemy agent {self.enemy_agent}, level {int(enemy.level)}, "
            f"health {enemy_health:.0%} of its own maximum, "
            f"{self.enemy_distance:.1f} units away\n"
            f"  character health {own_health:.0%} of {own_max_health} at "
            f"({start_xy[0]:.1f}, {start_xy[1]:.1f})\n"
            f"  this will approach and attack that agent, for at most "
            f"{ENEMY_OBSERVE_S:.0f}s, and stop early below "
            f"{ENEMY_ABORT_HP:.0%} health"
        )

        # 1. Target it.
        self.clear_target()
        self.wait_for(lambda: self.notice(CHANGE_TARGET_MESSAGE, 0, 0), NOTICE_WAIT_S)
        self.events.clear()
        self.action(
            f"targeting enemy {self.enemy_agent}",
            lambda: Player.ChangeTarget(self.enemy_agent),
        )
        self.assertTrue(
            self.wait_for(
                lambda: self.notice(CHANGE_TARGET_MESSAGE, 0, self.enemy_agent),
                NOTICE_WAIT_S,
            ),
            f"the client did not report a target change to enemy "
            f"{self.enemy_agent}; notices seen: "
            f"{[(hex(event.sequence), event.arg0) for event in self.events]}",
        )
        print(f"  targeted: the client's own notice confirms enemy {self.enemy_agent}")

        # 2. Call it. This is the branch the friendly test never takes.
        self.events.clear()
        self.action(
            f"calling enemy {self.enemy_agent}",
            lambda: Player.CallTarget(self.enemy_agent),
        )
        echoed = self.wait_for(
            lambda: self.notice(SEND_CALL_TARGET_MESSAGE, 1, self.enemy_agent), 1.0
        )
        print(
            "  called: Player.CallTarget took the enemy branch and completed; the "
            "client "
            + (
                "echoed its own kSendCallTarget for it"
                if echoed
                else "sent no notice of its own, which is expected: call_target_func "
                "is the handler, so it acts rather than re-broadcasting"
            )
        )

        # 3. Interact with it, which for an enemy is attacking it.
        self.action(
            f"interacting with enemy {self.enemy_agent}",
            lambda: Player.Interact(self.enemy_agent),
        )

        outcome = ""
        deadline = time.monotonic() + ENEMY_OBSERVE_S
        while time.monotonic() < deadline:
            now = self.client.read_agent_by_id(self.enemy_agent)
            if now is None or float(now.hp) <= 0.0:
                outcome = "the enemy is at 0 health or gone from the array — it died"
                break
            if float(now.hp) < enemy_health:
                outcome = (
                    f"the enemy's health fell from {enemy_health:.0%} to "
                    f"{float(now.hp):.0%}: the attack landed"
                )
                break
            if math.dist(Player.GetXY(), start_xy) >= MOVE_MINIMUM:
                outcome = (
                    "the character walked toward it ("
                    f"{math.dist(Player.GetXY(), start_xy):.1f} units moved)"
                )
                break
            health, _ = self.own_health()
            if health < ENEMY_ABORT_HP:
                outcome = (
                    f"abandoned: the character is at {health:.0%} health, below "
                    f"{ENEMY_ABORT_HP:.0%}"
                )
                break
            time.sleep(ENEMY_POLL_S)

        self.assertTrue(
            outcome,
            f"nothing came of interacting with enemy {self.enemy_agent} within "
            f"{ENEMY_OBSERVE_S:.0f}s: its health is unchanged and the character did "
            "not move. The client may not have had a path to it, or the character may "
            "not be able to attack at all.",
        )
        print(f"  interacted: {outcome}")

        # 4. Put the game back: no target, and the character where it started.
        self.clear_target()
        self.restore_position(start_xy)
        health, maximum = self.own_health()
        print(
            f"  restored: target cleared, character at {Player.GetXY()}, health "
            f"{health:.0%} of {maximum}"
        )

    def test_z_interacting_reaches_the_client(self) -> None:
        """``Player.Interact`` runs the client's own world action for an agent.

        When the client opens a dialog it says so, naming the agent, and that notice
        is the assertion. A gadget with no dialog reports nothing: the call still
        completed on the game thread and the client is still answering, and the test
        says which of the two it saw instead of assuming the stronger one.

        **This test runs last on purpose**, which is why its name starts with ``z``:
        unittest runs methods in alphabetical order. Interacting can leave a dialog
        open, and this project does not synthesise keyboard input, so the dialog is
        the one effect here that the suite cannot take back by itself — the operator
        presses Escape. Running it last keeps that from breaking the movement test,
        which is exactly what happened when it ran third: the character could not
        walk while the dialog from this call was up.

        The candidate has to be close, for the same reason: interacting with
        something far away makes the *client* walk, and that walk is neither the
        action under test nor bounded.
        """

        if not self.interact_agent:
            self.skipTest(
                f"no non-enemy agent within {INTERACT_RANGE:.0f} units. Stand near "
                "something interactable — an NPC or a chest — and rerun. Nothing was "
                "interacted with."
            )

        self.events.clear()
        before = Player.GetXY()
        self.require_living_agent(self.interact_agent)
        reached = self.distance_to_agent(self.interact_agent)
        if reached > INTERACT_RANGE:
            self.skipTest(
                f"agent {self.interact_agent} is {reached:.0f} units away now, beyond "
                f"the {INTERACT_RANGE:.0f}-unit range this suite will interact at: the "
                "client walks to a distant target, and that walk is not bounded. "
                "Nothing was interacted with."
            )
        self.action(
            f"interacting with agent {self.interact_agent}",
            lambda: Player.Interact(self.interact_agent),
        )

        # A dialog is "open" if the client reported one *at all* during this window,
        # whatever agent it named: the interaction can make the client walk to the
        # agent first, and the dialog then belongs to whoever answered.
        dialog_seen = self.wait_for(
            lambda: self.saw_message(DIALOG_BODY_MESSAGE), NOTICE_WAIT_S
        )
        self.assertEqual(
            int(Player.GetAgentID()),
            self.agent_id,
            "the client stopped answering after the interaction",
        )
        if dialog_seen:
            active = dialog.get_active_dialog()
            captured = 0 if active is None else active.agent_id
            buttons = dialog.get_active_dialog_buttons()
            self.assertEqual(
                captured,
                self.interact_agent,
                "the client reported a dialog for this agent, and the dialog module "
                "captures that same message, so the agent must match",
            )
            if buttons:
                self.assertTrue(
                    all(button.dialog_id != 0 for button in buttons),
                    f"the client announced buttons with no dialog id: "
                    f"{[button.dialog_id for button in buttons]}",
                )
            print(
                f"  the dialog module captured agent {captured} and "
                f"{len(buttons)} button(s): "
                f"{[button.dialog_id for button in buttons]}"
            )
        print(
            f"\n  interact agent {self.interact_agent}: the call completed and the "
            "client is answering; "
            + (
                "the client reported a dialog"
                if dialog_seen
                else "the client reported no dialog, which a gadget without one does"
            )
        )
        if dialog_seen:
            displaced = math.dist(Player.GetXY(), before)
            print(
                "  a dialog is open on the client, and this project does not "
                "synthesise keyboard input,\n  so the suite cannot close it: press "
                "Escape. The walk back is not attempted, because a\n  client with a "
                "dialog up does not walk — that is measured, not assumed."
            )
            if displaced > RETURN_TOLERANCE:
                print(
                    f"  the client walked {displaced:.1f} units to reach the agent; "
                    "walk back by hand after\n  closing the dialog."
                )
            return
        self.restore_position(before)

    # -- titles ------------------------------------------------------------

    def active_title_tier(self) -> int:
        """Return the title tier index the client's own player record holds.

        Read straight out of the record rather than through ``GetActiveTitleID``:
        the member maps a tier back to a title index, and the mapping loses
        information when two titles share a tier index. The tier is the value the
        setter actually changes, so it is the one the assertions use.
        """

        world = self.client.read_world_context()
        number = Player.GetPlayerNumber()
        if world is None or number is None:
            return 0
        record = world.GetPlayerById(int(number))
        if record is None:
            return 0
        return int(record.active_title_tier)

    @staticmethod
    def titles_with_progress() -> list[tuple[int, int]]:
        """Return ``(title index, tier index)`` for every title with progress.

        A tier index of ``0`` is a title the character has earned nothing in. Setting
        one displays nothing, which is indistinguishable from having removed the
        title, so those cannot be used to prove the setter does something.
        """

        return [
            (index, tier)
            for index, tier in enumerate(
                int(title.current_title_tier_index)
                for title in Player.GetTitleArrayRaw()
            )
            if tier
        ]

    def other_title(
        self, original: int, original_tier: int
    ) -> tuple[int, int, bool] | None:
        """Return ``(title index, tier index, tier is unique)`` for another title.

        The **tier** is what the setter changes, so any other title with progress
        proves it. The **title index** is only readable back unambiguously when one
        title holds that tier: ``GetActiveTitleID`` returns the first title matching
        a tier, so two titles sharing one cannot be told apart from outside. The
        third value says whether that read-back can be asserted or only reported.

        ``None`` means no such title, and it is ``None`` rather than ``0`` because
        **title 0 is a real title** — ``TitleID`` starts at ``Hero`` and puts
        ``None`` at ``0xff`` (``constants/constants.h:250-267``). An earlier version
        of this helper returned ``0`` for "not found" and so reported that a
        character with progress in forty titles had no second title to switch to.
        """

        tiers = [
            int(title.current_title_tier_index)
            for title in Player.GetTitleArrayRaw()
        ]
        for index, tier in enumerate(tiers):
            if index == original or not tier or tier == original_tier:
                continue
            return index, tier, tiers.count(tier) == 1
        return None

    def test_titles_round_trip(self) -> None:
        """``RemoveActiveTitle`` and ``SetActiveTitle``, with the title put back.

        The client's own player record is what says which title is displayed: a tier
        index of ``0`` means none, and anything else is the tier of the title being
        shown. Both members are checked against it, and the character is left with
        the title it started with.

        The **change** step is the one that proves the setter does something. A round
        trip that removes a title and puts the same one back could pass on a function
        that does nothing at all; switching to a different title and reading *that*
        title's tier out of the client cannot.
        """

        original = int(Player.GetActiveTitleID())
        original_tier = self.active_title_tier()

        if not original:
            self.skipTest(
                "no title is displayed on this character, so there is nothing to "
                "remove or restore. Select a title in-game and rerun: without one, "
                "the only thing this test could check is that removing nothing "
                "leaves nothing."
            )

        self.action("removing the active title", Player.RemoveActiveTitle)
        self.assertTrue(
            self.wait_for(lambda: self.active_title_tier() == 0, NOTICE_WAIT_S),
            f"the client still reports title tier {self.active_title_tier()} after "
            f"Player.RemoveActiveTitle() completed; the character had title "
            f"{original} displayed at tier {original_tier}",
        )
        self.assertEqual(
            int(Player.GetActiveTitleID()),
            0,
            "the tier is 0 but the member still reports a title, which is the "
            "reader bug this test found: a tier of 0 is what 'none displayed' is",
        )
        print(f"\n  title {original} (tier {original_tier}) removed: the client reports tier 0")

        self.action(
            f"restoring title {original}",
            lambda: Player.SetActiveTitle(original),
        )
        self.assertTrue(
            self.wait_for(
                lambda: self.active_title_tier() == original_tier, NOTICE_WAIT_S
            ),
            f"the client reports tier {self.active_title_tier()} after restoring "
            f"title {original}, which had tier {original_tier}",
        )
        self.assertEqual(int(Player.GetActiveTitleID()), original)
        print(f"  restored: the client reports tier {original_tier} again")

        choice = self.other_title(original, original_tier)
        if choice is None:
            earned = self.titles_with_progress()
            print(
                "  the change step needs a second title the character has progress "
                "in:\n    this character has progress in "
                + (", ".join(f"title {i} (tier {t})" for i, t in earned) or "none")
                + ".\n    The remove/restore above already shows the setter writing "
                "a value that was not\n    there — it put tier "
                f"{original_tier} back on title {original} — but switching to a "
                "different\n    title needs a different one to switch to."
            )
            return
        other, other_tier, unique = choice

        self.action(
            f"switching to title {other}",
            lambda: Player.SetActiveTitle(other),
        )
        self.assertTrue(
            self.wait_for(
                lambda: self.active_title_tier() == other_tier, NOTICE_WAIT_S
            ),
            f"the client reports tier {self.active_title_tier()} after "
            f"Player.SetActiveTitle({other}), whose tier is {other_tier}: the "
            "function did not change the displayed title",
        )
        if unique:
            self.assertEqual(
                int(Player.GetActiveTitleID()),
                other,
                "the tier changed to the one title "
                f"{other} has, but the member does not report title {other}",
            )
            print(
                f"  switched to title {other} (tier {other_tier}); the member reads "
                "the same title back"
            )
        else:
            print(
                f"  switched to title {other} (tier {other_tier}); a second title "
                f"shares tier {other_tier}, so\n    Player.GetActiveTitleID reports "
                "the first of them, as the source's own search does"
            )

        self.action(
            f"putting title {original} back",
            lambda: Player.SetActiveTitle(original),
        )
        self.assertTrue(
            self.wait_for(
                lambda: self.active_title_tier() == original_tier, NOTICE_WAIT_S
            ),
            f"the title was not put back: the client reports tier "
            f"{self.active_title_tier()}, expected {original_tier}. Restore title "
            f"{original} by hand.",
        )
        print(f"  title {original} is displayed again; nothing left changed")

    # -- status ------------------------------------------------------------

    def test_status_is_set_to_the_value_it_already_has(self) -> None:
        """``Player.SetPlayerStatus`` reaches the client's online-status setter.

        Set to the value it already holds, so nothing visible changes — the status is
        shown to friends — and the read-back is still a real check: the call has to
        complete on the game thread and the client's own field has to still agree.
        """

        before = int(Player.GetPlayerStatus())
        result = Player.SetPlayerStatus(before)

        self.assertTrue(result, "Player.SetPlayerStatus refused a valid status")
        self.assertEqual(
            int(Player.GetPlayerStatus()),
            before,
            "the friend-list status changed when it was set to the value it had",
        )

    def test_status_refuses_a_value_the_source_refuses(self) -> None:
        """``Player.SetPlayerStatus(9)`` reports ``False`` without calling anything.

        Reforged validates with ``PlayerStatus.from_value`` and returns ``False`` for
        anything that is not a status (``Py4GWCoreLib/Player.py:691-694``); native
        refuses above ``Away`` (``player_bindings.cpp:339-340``).
        """

        self.assert_no_call("Player.SetPlayerStatus(9)", settle_s=0.6)
        self.assertFalse(Player.SetPlayerStatus(9))
        self.assertFalse(Player.SetPlayerStatus("not-a-status"))
        self.assert_no_call("an invalid status", settle_s=0.6)

    # -- call target -------------------------------------------------------

    def test_call_target_runs_on_a_non_enemy(self) -> None:
        """``Player.CallTarget`` on a non-enemy takes the world-action branch.

        The source branches on allegiance (``agent_methods.cpp:207-224``): an enemy
        is called through ``call_target_func``, anything else through
        ``do_world_action_func`` with the call suppressed. Only safe agents are
        available to this suite, so this exercises the second branch and **the enemy
        branch is skipped on purpose** — a real call-target is a party broadcast, and
        this test was not asked to choose a target for the party.
        """

        agent_id = self.interact_agent or self.target_agent
        if not agent_id:
            self.skipTest("no non-enemy agent was found to call")

        before = Player.GetXY()
        self.require_living_agent(agent_id)
        self.action(
            f"calling agent {agent_id}",
            lambda: Player.CallTarget(agent_id),
        )
        self.assertEqual(
            int(Player.GetAgentID()),
            self.agent_id,
            "the client stopped answering after the call",
        )
        print(
            f"\n  call-target branch ran on agent {agent_id} (non-enemy, so the "
            "world-action branch; the enemy branch would be a party broadcast)"
        )
        self.restore_position(before)

    # -- the client itself -------------------------------------------------

    def test_the_client_is_still_there_and_answering(self) -> None:
        """Every action above ran in this process; it has to still be the same one."""

        win32 = Win32()
        still_running = [int(row["pid"]) for row in win32.find_guild_wars()]
        self.assertIn(self.pid, still_running, "the client process is gone")
        self.assertEqual(
            int(Player.GetAgentID()), self.agent_id, "the player agent changed"
        )
        self.assertGreater(Player.GetLevel(), 0)

    # -- read-only helpers -------------------------------------------------

    @staticmethod
    def _resolve(win32: Win32, pid: int, resolver: str) -> int:
        """Resolve one catalog name through a fresh read-only handle."""

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            scanner.initialize()
            catalog = PatternCatalog.from_directory("offsets")
            result = catalog.resolve(resolver, scanner)
        if not result.ok:
            raise AssertionError(
                f"pid {pid}: {resolver} did not resolve: {result.message}"
            )
        return int(result.value)

    @staticmethod
    def _read_entry(win32: Win32, pid: int, address: int, size: int) -> bytes:
        """Read entry bytes through a fresh read-only handle."""

        with ProcessMemoryReader(win32, pid) as reader:
            return reader.read(address, size)

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        """Return a hash of the client's whole code section.

        The two entry patches change seventeen bytes of it for as long as the
        connection is open. Hashing it before and after is what turns "the hooks were
        taken back out" into something checked.
        """

        module = win32.get_main_module(pid)
        digest = hashlib.sha256()
        size = 0
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
