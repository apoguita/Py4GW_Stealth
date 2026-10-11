"""The GwAu3-compatible layer's wire protocol, and the worker that answers it.

Part of the GwAu3-compatible layer; see ``docs/GWA3_COMPAT_SPEC.md``.

**What this is.** AutoIt cannot call a Python function: its interop is Win32 and COM, and a Python
library is neither a DLL export table nor a COM server. So there is no *binding* -- there is a
**bridge**: a channel an AutoIt script talks over and a Python side that answers. This module is both
halves of the conversation, and it is deliberately split so the half that can be tested without a
client is the larger one:

* :func:`encode_request` / :func:`decode_request` and :func:`encode_response` / :func:`decode_response`
  are the wire format -- pure JSON, no I/O, no client.
* :class:`Worker` holds the connection and resolves a request's ``call`` name against the layer.
* :func:`serve` runs the request loop over an already-open pipe handle.

**The message is line-delimited JSON.** Framing is separate from payload, so something other than a
pipe can carry it -- a test uses an in-process pair, and a throwaway probe can use stdio. One JSON
object per line, in both directions, UTF-8.

**The name is data, not dispatch.** ``{"call": "Skill_GetSkillInfo", "args": [1062, "Recharge"]}``
carries the function's name as a *string*, which is the one place name-dispatch is correct: the name
arrives from AutoIt and there is nothing else it could be. **Inside** the layer no member reaches a
field through a dynamic name -- the field-name arguments (``"Recharge"``) are GwAu3's own contract and
are resolved by the explicit tables the generators emit, never by ``getattr``.

**A failure says which kind it is.** AutoIt has no exceptions, so the reply has to carry the
distinction a Python caller would get from the class:

===========================  ==========================================================
``ok: true``                 the call ran; ``result`` is its return value
``not_implemented``          the name exists in GwAu3 and this layer has not built it yet
``refused``                  the effect is one this project declines to produce
``unknown``                  no such name -- neither implemented nor declared by GwAu3
``error``                    the call ran and raised; ``error.detail`` is the message
===========================  ==========================================================

That distinction is the whole reason the protocol exists in this shape: a migrating script can tell
"not built yet" from "this project will not do that" from "you asked for something that does not
exist", and none of them is silently a plausible value.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator

PROTOCOL_VERSION = 1

# The error kinds, spelled once so both sides agree.
KIND_NOT_IMPLEMENTED = "not_implemented"
KIND_REFUSED = "refused"
KIND_UNKNOWN = "unknown"
KIND_ERROR = "error"
KIND_BAD_REQUEST = "bad_request"


class ProtocolError(ValueError):
    """A message that is not the shape this protocol defines."""


@dataclass(frozen=True)
class Request:
    """One call: GwAu3's function name, its arguments, and an id the reply echoes."""

    call: str
    args: list[Any] = field(default_factory=list)
    request_id: Any = None


@dataclass(frozen=True)
class Response:
    """One answer. Exactly one of ``result`` and ``error`` is set.

    ``ok`` is the only field a caller must read first; a caller that ignores it and reads ``result``
    anyway gets ``None``, which is why every failure kind carries a human-readable ``detail``.
    """

    ok: bool
    result: Any = None
    kind: str | None = None
    detail: str = ""
    request_id: Any = None


def encode_request(request: Request) -> str:
    """One request as a single line, without the newline."""

    if not isinstance(request.call, str) or not request.call:
        raise ProtocolError("a request needs a non-empty call name")
    if not isinstance(request.args, list):
        raise ProtocolError("a request's args must be a list")
    payload: dict[str, Any] = {"call": request.call, "args": request.args}
    if request.request_id is not None:
        payload["id"] = request.request_id
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def decode_request(line: str) -> Request:
    """Parse one request line, refusing anything that is not this protocol's shape."""

    text = line.strip()
    if not text:
        raise ProtocolError("empty request")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"request is not JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ProtocolError("a request must be a JSON object")
    call = payload.get("call")
    if not isinstance(call, str) or not call:
        raise ProtocolError("a request needs a non-empty 'call'")
    args = payload.get("args", [])
    if not isinstance(args, list):
        raise ProtocolError("'args' must be a list")
    return Request(call=call, args=args, request_id=payload.get("id"))


def encode_response(response: Response) -> str:
    """One response as a single line, without the newline."""

    payload: dict[str, Any] = {"ok": response.ok}
    if response.request_id is not None:
        payload["id"] = response.request_id
    if response.ok:
        payload["result"] = response.result
    else:
        payload["error"] = {"kind": response.kind or KIND_ERROR, "detail": response.detail}
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=repr)


def decode_response(line: str) -> Response:
    """Parse one response line."""

    text = line.strip()
    if not text:
        raise ProtocolError("empty response")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"response is not JSON: {error}") from error
    if not isinstance(payload, dict) or "ok" not in payload:
        raise ProtocolError("a response must be a JSON object with 'ok'")

    ok = bool(payload["ok"])
    if ok:
        return Response(ok=True, result=payload.get("result"), request_id=payload.get("id"))

    error = payload.get("error")
    if not isinstance(error, dict):
        raise ProtocolError("a failed response must carry an 'error' object")
    return Response(
        ok=False,
        kind=str(error.get("kind", KIND_ERROR)),
        detail=str(error.get("detail", "")),
        request_id=payload.get("id"),
    )


# ---------------------------------------------------------------------------------------------
# The layer's callable surface.
#
# Resolved from the modules this package actually ships, so a name that is not there is answered
# `unknown` (or `not_implemented`, when GwAu3 declares it and this layer has not built it) rather
# than silently missing. Nothing is hand-listed: a list would drift from the package the moment a
# module lands.
# ---------------------------------------------------------------------------------------------

def _layer_modules() -> Iterator[Any]:
    """The modules of ``py4gw.gwa3`` that expose GwAu3 routines."""

    package = importlib.import_module("py4gw.gwa3")
    for name in getattr(package, "__all__", ()):
        if name == "constants":
            continue
        module = importlib.import_module(f"py4gw.gwa3.{name}")
        yield module


def layer_surface() -> dict[str, Callable[..., Any]]:
    """``{GwAu3 name: callable}`` for every routine this layer implements."""

    surface: dict[str, Callable[..., Any]] = {}
    for module in _layer_modules():
        for name in getattr(module, "__all__", ()):
            routine = getattr(module, name, None)
            if callable(routine):
                surface[name] = routine
    return surface


def gwau3_declared_names() -> frozenset[str]:
    """Every function name GwAu3 declares, from the mechanism map.

    Used only to tell ``not_implemented`` (GwAu3 has it, this layer does not) from ``unknown`` (no such
    function anywhere). A GwAu3 name that is neither implemented nor declared is a caller's typo, and
    saying which of the two it is costs one lookup.
    """

    from pathlib import Path

    path = Path(__file__).resolve().parent.parent.parent / "external" / "GwAu3_mechanism_map.json"
    if not path.is_file():
        return frozenset()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    return frozenset(
        entry["name"]
        for entry in payload.get("functions", [])
        if isinstance(entry.get("name"), str)
    )


class Worker:
    """Answers protocol requests against the layer.

    Holds no connection of its own: a routine reaches the client through ``py4gw``'s own
    process-global connection, exactly as it does when called from Python. The worker's job is the
    protocol, not the client.
    """

    def __init__(self, surface: dict[str, Callable[..., Any]] | None = None) -> None:
        self._surface = surface if surface is not None else layer_surface()
        self._declared = gwau3_declared_names()

    @property
    def surface(self) -> dict[str, Callable[..., Any]]:
        return dict(self._surface)

    def handle(self, line: str) -> str:
        """Answer one request line with one response line. Never raises."""

        try:
            request = decode_request(line)
        except ProtocolError as error:
            return encode_response(
                Response(ok=False, kind=KIND_BAD_REQUEST, detail=str(error))
            )

        response = self.dispatch(request)
        return encode_response(response)

    def dispatch(self, request: Request) -> Response:
        """Run one request and describe the outcome, distinguishing the four failure kinds."""

        routine = self._surface.get(request.call)
        if routine is None:
            if request.call in self._declared:
                return Response(
                    ok=False,
                    kind=KIND_NOT_IMPLEMENTED,
                    detail=(
                        f"GwAu3 declares {request.call} and this layer has not built it yet. "
                        f"docs/GWA3_ROUTE_MAP.md records what it needs."
                    ),
                    request_id=request.request_id,
                )
            return Response(
                ok=False,
                kind=KIND_UNKNOWN,
                detail=f"no function named {request.call} -- not in this layer and not declared by GwAu3",
                request_id=request.request_id,
            )

        try:
            result = routine(*request.args)
        except NotImplementedError as error:
            # A key or routine this layer refuses. The message already names the capability.
            return Response(
                ok=False, kind=KIND_REFUSED, detail=str(error), request_id=request.request_id
            )
        except Exception as error:  # noqa: BLE001 - the protocol's job is to describe any failure
            return Response(
                ok=False,
                kind=KIND_ERROR,
                detail=f"{type(error).__name__}: {error}",
                request_id=request.request_id,
            )
        return Response(ok=True, result=result, request_id=request.request_id)


def serve(
    read_line: Callable[[], str | None],
    write_line: Callable[[str], None],
    worker: Worker | None = None,
) -> int:
    """Run the request loop until ``read_line`` answers ``None``.

    The I/O is passed in rather than owned, which is what lets the offline tests drive the whole loop
    over an in-process pair and lets a real run use a pipe without changing anything here.
    """

    active = worker if worker is not None else Worker()
    handled = 0
    while True:
        line = read_line()
        if line is None:
            return handled
        if not line.strip():
            continue
        write_line(active.handle(line))
        handled += 1


def main(argv: Iterable[str] | None = None) -> int:
    """Entry point: serve the protocol over stdio.

    Stdio is the transport for a probe or a script that wants one call, not the intended channel --
    the pipe is, because a single byte stream cannot carry a request and its result apart from any
    stray output. Kept here so the worker can be exercised without a pipe before the pipe exists.
    """

    arguments = list(argv if argv is not None else sys.argv[1:])

    def read_line() -> str | None:
        line = sys.stdin.readline()
        return None if line == "" else line

    def write_line(line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    if "--version" in arguments:
        sys.stdout.write(f"{PROTOCOL_VERSION}\n")
        return 0

    routine_count = len(layer_surface())
    sys.stderr.write(
        f"gwa3 worker: protocol {PROTOCOL_VERSION}, {routine_count} routines, one JSON object per line\n"
    )
    sys.stderr.flush()
    return serve(read_line, write_line)


if __name__ == "__main__":
    raise SystemExit(main())
