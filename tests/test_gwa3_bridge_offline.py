"""Offline tests for the GwAu3 bridge protocol and worker.

No client, no elevation, no pipe. The protocol is pure JSON in and JSON out, and the worker's
dispatch is pure logic over a surface a test can supply -- which is why this is testable at all before
a pipe exists.

What is being established, and they are different questions:

1. **The wire format round-trips**, and refuses a message that is not its shape rather than guessing.
2. **The worker tells the four failure kinds apart** -- ``not_implemented`` / ``refused`` /
   ``unknown`` / ``error`` -- because that distinction is the entire reason the protocol carries an
   error kind. A migrating script must be able to tell "not built yet" from "this project will not do
   that".
3. **The reply never lies.** A response is ``ok`` only when the routine returned; a routine that
   raised is never reported as a value.
"""

from __future__ import annotations

import json
import unittest

from py4gw.gwa3 import bridge, data_party


class ProtocolRoundTripTests(unittest.TestCase):
    """The wire format."""

    def test_a_request_round_trips(self) -> None:
        request = bridge.Request(call="Skill_GetSkillInfo", args=[1062, "Recharge"], request_id=7)
        self.assertEqual(bridge.decode_request(bridge.encode_request(request)), request)

    def test_a_request_without_an_id_round_trips(self) -> None:
        request = bridge.Request(call="Agent_GetMyID")
        decoded = bridge.decode_request(bridge.encode_request(request))
        self.assertEqual(decoded.call, "Agent_GetMyID")
        self.assertEqual(decoded.args, [])
        self.assertIsNone(decoded.request_id)

    def test_a_response_round_trips(self) -> None:
        response = bridge.Response(ok=True, result=42, request_id=1)
        self.assertEqual(bridge.decode_response(bridge.encode_response(response)), response)

    def test_a_failure_response_round_trips_with_its_kind(self) -> None:
        response = bridge.Response(ok=False, kind=bridge.KIND_REFUSED, detail="needs the connection")
        decoded = bridge.decode_response(bridge.encode_response(response))
        self.assertFalse(decoded.ok)
        self.assertEqual(decoded.kind, bridge.KIND_REFUSED)
        self.assertEqual(decoded.detail, "needs the connection")

    def test_a_request_is_one_line(self) -> None:
        """Line-delimited framing only works if the payload never contains a newline."""

        encoded = bridge.encode_request(
            bridge.Request(call="Chat_SendChat", args=["!", "line one\nline two"])
        )
        self.assertNotIn("\n", encoded)
        self.assertEqual(bridge.decode_request(encoded).args, ["!", "line one\nline two"])

    def test_a_result_that_json_cannot_carry_does_not_break_the_frame(self) -> None:
        """A routine returning a ctypes value must not turn into a bare exception on the wire."""

        class Opaque:
            def __repr__(self) -> str:
                return "<opaque>"

        encoded = bridge.encode_response(bridge.Response(ok=True, result=Opaque()))
        self.assertNotIn("\n", encoded)
        self.assertEqual(bridge.decode_response(encoded).result, "<opaque>")


class ProtocolRefusalTests(unittest.TestCase):
    """A message that is not this protocol's shape is refused, not guessed at."""

    def test_empty_input_is_refused(self) -> None:
        with self.assertRaises(bridge.ProtocolError):
            bridge.decode_request("   ")

    def test_malformed_json_is_refused(self) -> None:
        with self.assertRaises(bridge.ProtocolError):
            bridge.decode_request("{not json")

    def test_a_request_without_a_call_is_refused(self) -> None:
        with self.assertRaises(bridge.ProtocolError):
            bridge.decode_request('{"args": []}')

    def test_a_request_with_a_non_list_args_is_refused(self) -> None:
        with self.assertRaises(bridge.ProtocolError):
            bridge.decode_request('{"call": "X", "args": "nope"}')

    def test_a_response_without_ok_is_refused(self) -> None:
        with self.assertRaises(bridge.ProtocolError):
            bridge.decode_response('{"result": 1}')

    def test_a_failed_response_without_an_error_object_is_refused(self) -> None:
        with self.assertRaises(bridge.ProtocolError):
            bridge.decode_response('{"ok": false}')


class WorkerDispatchTests(unittest.TestCase):
    """The worker against a surface the test supplies, so every kind is reachable."""

    def setUp(self) -> None:
        def refuses(_: object) -> object:
            raise NotImplementedError("GwAu3_Data_Party.au3:44-46 needs the second record")

        def explodes(_: object) -> object:
            raise ValueError("the client said no")

        self.worker = bridge.Worker(
            surface={
                "Skill_GetSkillInfo": lambda skill_id, info: {"Recharge": 30}.get(info, 0),
                "Agent_GetMyID": lambda: 4242,
                "Agent_GetAgentInfo": lambda agent_id, info: f"{agent_id}:{info}",
                "Party_GetPartyContextInfo": refuses,
                "Explodes": explodes,
            }
        )
        # A name GwAu3 declares and this layer has not built, and a name nothing declares.
        self.worker._declared = frozenset({"Agent_GoNPC"})

    def _ask(self, call: str, *args: object) -> bridge.Response:
        return self.worker.dispatch(bridge.Request(call=call, args=list(args)))

    def test_a_routine_that_returns_is_ok_with_its_value(self) -> None:
        response = self._ask("Skill_GetSkillInfo", 1062, "Recharge")
        self.assertTrue(response.ok)
        self.assertEqual(response.result, 30)

    def test_a_routine_with_no_arguments_is_called_with_none(self) -> None:
        self.assertEqual(self._ask("Agent_GetMyID").result, 4242)

    def test_arguments_arrive_in_order(self) -> None:
        self.assertEqual(self._ask("Agent_GetAgentInfo", -2, "X").result, "-2:X")

    def test_a_declared_but_unbuilt_name_is_not_implemented(self) -> None:
        response = self._ask("Agent_GoNPC", 42)
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_NOT_IMPLEMENTED)
        # The detail must point at where the work is recorded, not merely refuse.
        self.assertIn("GWA3_ROUTE_MAP.md", response.detail)

    def test_a_name_nothing_declares_is_unknown(self) -> None:
        response = self._ask("NoSuchThing")
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_UNKNOWN)

    def test_a_refusal_is_refused_and_keeps_its_reason(self) -> None:
        """Against the **real** shipped module, because that is where the raising reader lives.

        The stub in `setUp` cannot serve this: it takes one argument and the worker passes the request's
        own two, so the call raised `TypeError` and was correctly reported as `error`. That was the
        test's bug, and it is recorded here because "an unexpected exception is an error" is exactly
        the behaviour that made the bug visible rather than silent.

        **The one argument is GwAu3's own arity.** ``Func Party_GetPartyContextInfo($a_s_Info = "")``
        (`GwAu3_Data_Party.au3:4`) takes the field name and nothing else -- unlike every other family,
        whose accessor takes a record id first. The layer carried a record-id parameter until the first
        live run; a migrating script's ``Party_GetPartyContextInfo("PlayerCount")`` would have had the
        key read as the id and answered `0` with no error at all.
        """

        worker = bridge.Worker(surface={"Party_GetPartyContextInfo": data_party.Party_GetPartyContextInfo})
        response = worker.dispatch(
            bridge.Request(call="Party_GetPartyContextInfo", args=["MyPartyPtr"])
        )
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_REFUSED)
        self.assertIn("GwAu3_Data_Party.au3:35-36", response.detail)

    def test_a_routine_called_with_the_wrong_arity_is_an_error(self) -> None:
        """A caller's mistake must come back as a described failure, not as a dropped channel."""

        response = self._ask("Agent_GetMyID", "an argument it does not take")
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_ERROR)
        self.assertIn("TypeError", response.detail)

    def test_any_other_exception_is_an_error_and_is_never_a_result(self) -> None:
        response = self._ask("Explodes", 1)
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_ERROR)
        self.assertIn("ValueError", response.detail)
        self.assertIn("the client said no", response.detail)
        self.assertIsNone(response.result)

    def test_handle_answers_a_bad_request_instead_of_raising(self) -> None:
        """A worker that raised on a malformed line would drop the channel for a caller's typo."""

        answered = self.worker.handle("not json at all")
        response = bridge.decode_response(answered)
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_BAD_REQUEST)

    def test_handle_round_trips_a_real_request(self) -> None:
        answered = self.worker.handle('{"call": "Skill_GetSkillInfo", "args": [1062, "Recharge"], "id": 3}')
        response = bridge.decode_response(answered)
        self.assertTrue(response.ok)
        self.assertEqual(response.result, 30)
        self.assertEqual(response.request_id, 3)


class ServeLoopTests(unittest.TestCase):
    """The loop, over an in-process pair -- the same code path a pipe will drive."""

    def test_the_loop_answers_every_line_and_stops_at_the_end(self) -> None:
        lines = iter(
            [
                '{"call": "Agent_GetMyID", "id": 1}',
                "",
                '{"call": "NoSuchThing", "id": 2}',
            ]
        )
        written: list[str] = []
        worker = bridge.Worker(surface={"Agent_GetMyID": lambda: 4242})

        handled = bridge.serve(lambda: next(lines, None), written.append, worker)

        self.assertEqual(handled, 2, "a blank line is skipped and must not count as handled")
        self.assertEqual(len(written), 2)
        self.assertEqual(bridge.decode_response(written[0]).result, 4242)
        self.assertEqual(bridge.decode_response(written[1]).kind, bridge.KIND_UNKNOWN)

    def test_a_blank_line_produces_no_reply(self) -> None:
        lines = iter(["", '{"call": "Agent_GetMyID"}'])
        written: list[str] = []
        bridge.serve(
            lambda: next(lines, None), written.append, bridge.Worker(surface={"Agent_GetMyID": lambda: 1})
        )
        self.assertEqual(len(written), 1)


class RealSurfaceTests(unittest.TestCase):
    """The surface the worker resolves from the package that actually ships."""

    def test_the_shipped_routines_are_all_reachable_by_name(self) -> None:
        surface = bridge.layer_surface()
        for name in (
            "Agent_GetAgentInfo",
            "Agent_GetMyID",
            "Agent_GetDistance",
            "Skill_GetSkillInfo",
            "Party_GetPartyContextInfo",
        ):
            with self.subTest(name=name):
                self.assertIn(name, surface)

    def test_constants_are_not_routines(self) -> None:
        """`constants` is a name table, not a callable surface: it must not be offered as calls."""

        surface = bridge.layer_surface()
        self.assertNotIn("GC_I_ALLEGIANCE_ENEMY", surface)

    def test_a_shipped_routine_called_without_a_client_reports_an_error_not_a_crash(self) -> None:
        """The worker must survive a routine that needs the client when none is connected.

        The reply is `error` with the connection message, not `ok` with a stand-in value.
        """

        worker = bridge.Worker()
        response = worker.dispatch(bridge.Request(call="Agent_GetMyID"))
        self.assertFalse(response.ok)
        self.assertEqual(response.kind, bridge.KIND_ERROR)
        self.assertIn("connect", response.detail.lower())

    def test_gwau3_declared_names_come_from_the_mechanism_map(self) -> None:
        declared = bridge.gwau3_declared_names()
        self.assertEqual(len(declared), 648)
        self.assertIn("Agent_GoNPC", declared)


if __name__ == "__main__":
    unittest.main()
