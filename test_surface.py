"""The library's whole surface: described, organised, runnable, and reported.

This is the engine behind ``main.py``'s test surface. It answers three questions about every name
`py4gw` exports and every member those names carry:

1. **What is it?** -- kind (record, enum, class, function, constant), its signature, its fields and
   their offsets, its enum values, and the one-line summary of its own docstring.
2. **May it be run?** -- a record's fields and a record's properties read; a ``@staticmethod`` that
   takes no arguments can be called; an instance method cannot be run without an instance, and a
   member whose own source reaches for the current client is marked as needing one.
3. **What did it answer?** -- the value, the exception it raised, or the reason it was skipped, with
   the time it took. Nothing here raises: a member that fails is a result, because the point of the
   surface is to *show* what the library does, including where it says no.

**Writes are classified, never guessed at run time.** A member whose name (or whose own docstring)
says it acts -- ``Set*``, ``Move*``, ``Send*``, ``Use*``, ``Travel``, ``Interact``, ``Buy`` ... --
is marked ``write`` and is not run unless a caller explicitly asks for writes. Everything else is
``read``, and anything the rules do not recognise is ``unknown`` and is *also* not run: this module
never calls something it cannot classify, because the client is on the other end of those calls.

Nothing here needs a client, elevation, or a UAC prompt: with no connection every
client-dependent member is expected to refuse, and refusing cleanly is itself the finding.
"""

from __future__ import annotations

import contextlib
import ctypes
import enum
import importlib
import inspect
import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import py4gw

#: The group whose members act on **this process's own window** rather than on the client. They are
#: the AutoIt-compatible toolkit, so calling one cannot write to Guild Wars; the classification below
#: is about the client, which is what must never be written without being asked for.
GUI_GROUP = "py4gw.gui"

#: Modules whose public names are part of the surface as well as the exported ones. This is a
#: fallback for a caller that wants a fixed list; the window maps **every** module of the package,
#: discovered from the package itself (:func:`discover_modules`), because "the library" is what is on
#: disk and a hand-written list goes stale the first time a module is added.
EXTRA_MODULES: tuple[str, ...] = (
    "py4gw.context",
    "py4gw.ui",
    "py4gw.win32",
    "py4gw.frame_tree",
    "py4gw.game_thread",
    "py4gw.gui",
    "py4gw.helpers",
    "py4gw.internals",
    "py4gw.memory",
    "py4gw.scanner",
    "py4gw.py4gwcorelib_src",
)


def discover_modules(package: str = "py4gw") -> tuple[str, ...]:
    """Every module of the library, read from the package on disk.

    The declared export list is the library's contract; the modules are the library. Mapping only
    the exports left whole wrapper classes out -- ``Agent``, for one, is not exported by name -- so
    the map is built from the package directory: every ``*.py`` under it becomes a group, and the
    package's own ``__init__`` stays the first group.
    """

    package_module = importlib.import_module(package)
    location = getattr(package_module, "__file__", None)
    if not location:
        return (package,)
    root = Path(location).resolve().parent
    modules: list[str] = [package]
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        parts = list(path.relative_to(root).with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        modules.append(".".join([package, *parts]))
    return tuple(dict.fromkeys(modules))

#: Names whose *own source* says they act on the client. The classification is deliberately
#: conservative: a name that is not here and does not match the read patterns below is ``unknown``
#: and is reported as such rather than run.
WRITE_NAMES: frozenset[str] = frozenset(
    {
        "connect",
        "disconnect",
        "enable",
        "disable",
        "initialize",
        "terminate",
        "shutdown",
        "load_string_table",
        "reset",
    }
)

#: Prefixes of members that act. A read-only member of the sources is spelled with one of the read
#: prefixes below; anything else is unknown.
WRITE_PREFIXES: tuple[str, ...] = (
    "Set",
    "Add",
    "Insert",
    "Remove",
    "Delete",
    "Clear",
    "Create",
    "Move",
    "Send",
    "Use",
    "Cast",
    "Click",
    "Press",
    "Travel",
    "Interact",
    "Buy",
    "Sell",
    "Trade",
    "Flag",
    "Kick",
    "Invite",
    "Accept",
    "Deny",
    "Abandon",
    "Request",
    "Perform",
    "Do",
    "Drop",
    "Pick",
    "Equip",
    "Enter",
    "Leave",
    "Open",
    "Close",
    "Toggle",
    "Change",
    "Write",
    "Patch",
    "Install",
    "Register",
    "Unregister",
    "Hook",
    "Start",
    "Stop",
    "Play",
    "Pause",
    "Resume",
    "Log",
    "Say",
    "Chat",
)

READ_PREFIXES: tuple[str, ...] = (
    "Get",
    "Is",
    "Has",
    "Can",
    "Find",
    "Read",
    "Resolve",
    "Lookup",
    "Query",
    "Scan",
    "Search",
    "Count",
    "List",
    "To",
    "As",
    "Format",
    "Describe",
    "Snapshot",
    "Compute",
    "Calculate",
    "Calc",
    "Check",
    "Try",
    "Build",
    "Enumerate",
    "Collect",
    "Dump",
    "Print",
    "Show",
    "Repr",
)

#: Members whose *own source* reaches for the selected client. That is the library's accessor
#: pattern (``require_client()`` / ``current_client()``), so it is read from the source rather than
#: guessed from the name.
CLIENT_ACCESSORS: tuple[str, ...] = ("require_client(", "current_client(")

#: What a member's own source *calls* when it acts on the client. These are the port's write
#: vocabulary, read out of the code that does the writing: the game-thread call layer
#: (``client.call_function``), the shared block (``client.bridge.write_data`` / ``.submit``), the
#: invasive-rights transport (``WriteAccess``), a raw write, and the UI message sender. A member
#: whose source contains one of these is a write, whatever its name says.
WRITE_MARKERS: tuple[str, ...] = (
    "call_function(",
    ".bridge.",
    "write_data(",
    ".submit(",
    "WriteAccess",
    "write_process_memory(",
    "send_ui_message",
    "SendUIMessage",
    "PatchFunction",
    ".patch(",
    "install(",
)

#: What a member's own source calls when it only reads: the reader accessor, a context read, or the
#: globals the readers resolve through.
READ_MARKERS: tuple[str, ...] = (
    "require_client(",
    "current_client(",
    ".get_context(",
    ".read(",
    "ProcessMemoryReader",
    "GWContext",
    "read_player_name",
)


@dataclass(frozen=True)
class Entry:
    """One runnable or readable thing on the library's surface."""

    group: str
    owner: str
    name: str
    kind: str
    signature: str = ""
    detail: str = ""
    doc: str = ""
    access: str = "read"
    access_reason: str = ""
    run: str = "none"
    needs_client: bool = False
    parameters: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        """The entry's path on the surface -- group, owner and name -- which is its identity."""

        where = f"{self.owner}.{self.name}" if self.owner else self.name
        return f"{self.group}.{where}" if self.group else where

    @property
    def display(self) -> str:
        """The entry as a table row shows it: its path, then its signature."""

        return f"{self.label}{self.signature}" if self.signature else self.label

    @property
    def runnable(self) -> bool:
        """Whether this engine can run the entry at all, on its own."""

        return self.run != "none"


@dataclass
class Outcome:
    """What running one entry produced."""

    entry: Entry
    status: str
    value: str = ""
    error: str = ""
    output: str = ""
    milliseconds: float = 0.0

    @property
    def answered(self) -> bool:
        """Whether the entry answered something."""

        return self.status == "answered"


@dataclass
class Summary:
    """Counts over a set of entries, which is what the window's header shows."""

    total: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    by_group: dict[str, int] = field(default_factory=dict)
    runnable: int = 0
    needs_client: int = 0
    writes: int = 0
    unknown: int = 0

    def lines(self) -> list[str]:
        """The summary as human-readable lines."""

        lines = [f"entries: {self.total}", f"runnable without a client: {self.runnable}"]
        if self.needs_client:
            lines.append(f"reach for the selected client: {self.needs_client}")
        if self.writes:
            lines.append(f"classified as writes (not run unless asked): {self.writes}")
        if self.unknown:
            lines.append(f"unclassified (reported, never run): {self.unknown}")
        lines.append("by kind: " + ", ".join(f"{k}={v}" for k, v in sorted(self.by_kind.items())))
        return lines


def _short_doc(value: Any) -> str:
    """The first line of an object's docstring."""

    text = inspect.getdoc(value) or ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _signature(value: Any) -> str:
    """A callable's signature, or an empty string when it has none to show."""

    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError):
        return ""


def _source(value: Any) -> str:
    """An object's own source, or an empty string when it cannot be read."""

    try:
        return inspect.getsource(value)
    except (OSError, TypeError):
        return ""


def _classify(owner: str, name: str, doc: str, source: str = "", group: str = "") -> str:
    """Whether a member reads, writes, or cannot be classified: the verdict alone."""

    return _classify_with_reason(owner, name, doc, source, group)[0]


def _classify_with_reason(
    owner: str, name: str, doc: str, source: str = "", group: str = ""
) -> tuple[str, str]:
    """The verdict and the evidence for it.

    Name and docstring first -- the library's own spelling is a strong signal -- and then the
    member's own source, which is the evidence that settles it: a member that calls the game-thread
    layer, the shared block or the write transport *acts*, however it is named, and one that calls
    the reader accessor or a context read only reads. A member with neither is ``unknown`` and is
    reported rather than run.

    The AutoIt toolkit is a group of its own: ``GUICreate`` and ``GUICtrlCreate...`` act on **this**
    process's window and never on the client, so they are classified as reads here.
    """

    if group == GUI_GROUP:
        return ("read", "the AutoIt toolkit acts on this process's window, never on the client")
    if name in WRITE_NAMES:
        return ("write", f"{name!r} is one of the library's own acting names")
    lowered = doc.lower()
    if "this is a write" in lowered or "writes to the client" in lowered:
        return ("write", "its own docstring says it writes")
    for marker in WRITE_MARKERS:
        if marker in source:
            return ("write", f"its own source calls {marker}")
    if name.startswith(WRITE_PREFIXES):
        return ("write", f"its name starts with a write prefix ({name[:4]})")
    for marker in READ_MARKERS:
        if marker in source:
            return ("read", f"its own source calls {marker} and no write marker")
    if name.startswith(READ_PREFIXES):
        return ("read", f"its name starts with a read prefix ({name[:4]})")
    return ("unknown", "nothing in its name, docstring or source settles whether it acts")


def _needs_client(value: Any) -> bool:
    """Whether a member's own source reaches for the selected client."""

    source = _source(value)
    return any(accessor in source for accessor in CLIENT_ACCESSORS)


def _kind_of(value: Any) -> str:
    """The surface's own word for what a value is."""

    if isinstance(value, enum.EnumMeta):
        return "enum"
    if isinstance(value, type):
        if getattr(value, "_fields_", None):
            return "record"
        if getattr(value, "_member_map_", None):
            return "enum"
        return "class"
    if inspect.isfunction(value) or inspect.isbuiltin(value):
        return "function"
    if inspect.ismodule(value):
        return "module"
    if isinstance(value, dict):
        return "mapping"
    return "constant"


def _run_mode(value: Any) -> str:
    """How the engine can run a member: its fields, its value, or a call."""

    if isinstance(value, property):
        return "property"
    if isinstance(value, (staticmethod, classmethod)):
        return "call"
    if callable(value):
        return "call"
    return "value"


def _member_entries(group: str, owner: str, cls: type) -> list[Entry]:
    """Every public member of a class, as entries."""

    entries: list[Entry] = []
    for name, attribute in sorted(vars(cls).items()):
        if name.startswith("_"):
            continue
        run = _run_mode(attribute)
        function = (
            attribute.__func__
            if isinstance(attribute, (staticmethod, classmethod))
            else attribute
        )
        source = _source(function)
        doc = _short_doc(function)
        access, reason = _classify_with_reason(owner, name, doc, source, group)
        if run == "call":
            signature = _signature(function)
            required = _required_parameters(function)
            if required:
                run = "call-with-arguments"
            entries.append(
                Entry(
                    group=group,
                    owner=owner,
                    name=name,
                    kind="method",
                    signature=signature,
                    doc=doc,
                    access=access, access_reason=reason,
                    run=run,
                    needs_client=_needs_client(function),
                    parameters=tuple(required),
                )
            )
            continue
        if run == "property":
            entries.append(
                Entry(
                    group=group,
                    owner=owner,
                    name=name,
                    kind="property",
                    doc=doc,
                    access=access, access_reason=reason,
                    run="property",
                    needs_client=_needs_client(function),
                )
            )
            continue
        entries.append(
            Entry(
                group=group,
                owner=owner,
                name=name,
                kind="attribute",
                detail=type(attribute).__name__,
                access=access, access_reason=reason,
                run="value",
            )
        )
    return entries


def _required_parameters(value: Any) -> list[str]:
    """The names of a callable's required parameters."""

    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        return []
    return [
        parameter.name
        for parameter in signature.parameters.values()
        if parameter.default is inspect.Parameter.empty
        and parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]


def _record_entries(group: str, name: str, value: type) -> list[Entry]:
    """A ctypes record: its fields with offsets and types, and its own properties."""

    entries: list[Entry] = []
    for field_definition in getattr(value, "_fields_", ()):  # type: ignore[union-attr]
        # A field is ``(name, type)``; a bitfield is ``(name, type, width)``.
        field_name = field_definition[0]
        field_type = field_definition[1]
        offset = getattr(value, field_name).offset
        type_name = getattr(field_type, "__name__", str(field_type))
        bit_width = f" bitfield {field_definition[2]}" if len(field_definition) > 2 else ""
        entries.append(
            Entry(
                group=group,
                owner=name,
                name=field_name,
                kind="field",
                detail=f"+0x{offset:04X} {type_name}{bit_width}",
                access="read",
                access_reason="a record field: read from the record's own bytes",
                run="field",
            )
        )
    for entry in _member_entries(group, name, value):
        entries.append(entry)
    return entries


def _enum_entries(group: str, name: str, value: enum.EnumMeta) -> list[Entry]:
    """An enum: every member with its value, and its own methods and properties as well.

    An enum in this library is not only its members -- ``PlayerStatus.from_value`` and
    ``display_name`` are part of its surface -- so the class's own members are mapped beside the
    members it enumerates.
    """

    members: dict[str, Any] = dict(value.__members__)
    entries = [
        Entry(
            group=group,
            owner=name,
            name=member_name,
            kind="enum member",
            detail=repr(getattr(member, "value", None)),
            access="read",
            access_reason="an enum member: a declared constant",
            run="value",
        )
        for member_name, member in members.items()
    ]
    entries.extend(_member_entries(group, name, value))
    return entries


def entries_for(module_name: str, expanded: set[int] | None = None) -> list[Entry]:
    """Every entry a module contributes to the surface.

    ``expanded`` is the set of records, enums and classes already mapped by an earlier module: one
    that is already there is named once, pointing at where it is declared, and its members are not
    listed a second time. A record reached through four namespaces is still one record.
    """

    module = importlib.import_module(module_name)
    exported = getattr(module, "__all__", None)
    if exported:
        # An exported list is taken as written: ``py4gw.context`` and ``py4gw.win32`` are modules,
        # and they are exported names of the library like any other.
        names = list(exported)
    else:
        # A module with no export list declares its surface in its own body -- the generated
        # constant modules are exactly that (3,111 AutoIt names in ``py4gw.gui.constants``) -- so
        # every public name it holds is part of the surface. Modules are left out: each has a group
        # of its own.
        names = [
            name
            for name, value in vars(module).items()
            if not name.startswith("_") and not inspect.ismodule(value)
        ]
    # A module's ``__all__`` is its export list, not everything it declares: a record that is
    # declared here and exported only through a package would otherwise be named but never mapped --
    # its fields and members missing from the surface entirely -- so every public name this module
    # *declares* is mapped here as well.
    for name, value in vars(module).items():
        if name.startswith("_") or name in names or inspect.ismodule(value):
            continue
        if getattr(value, "__module__", None) == module_name:
            names.append(name)
    names = sorted(set(names))
    entries: list[Entry] = []
    for name in sorted(names):
        value = getattr(module, name, None)
        if value is None:
            # A name the module declares but does not bind is still part of the surface, and saying
            # so is the honest row for it.
            entries.append(
                Entry(
                    group=module_name,
                    owner="",
                    name=name,
                    kind="unbound",
                    detail="declared, not bound (None)",
                    access="read",
                    run="none",
                )
            )
            continue
        kind = _kind_of(value)
        entry = Entry(
            group=module_name,
            owner="",
            name=name,
            kind=kind,
            doc=_short_doc(value),
            access="read",
            access_reason="a name the module declares: reading it touches nothing",
            run="value",
        )
        if kind in ("record", "enum", "class"):
            defining = getattr(value, "__module__", "")
            already = expanded is not None and id(value) in expanded
            if already or (defining and defining != module_name):
                entry = Entry(
                    group=module_name,
                    owner="",
                    name=name,
                    kind=kind,
                    detail=f"declared in {defining or 'an earlier module'}",
                    doc=entry.doc,
                    access="read",
                    access_reason="the same object an earlier module declared",
                    run="none",
                )
                entries.append(entry)
                continue
            if expanded is not None:
                expanded.add(id(value))
        entries.append(entry)
        if kind == "record":
            entries.extend(_record_entries(module_name, name, value))
        elif kind == "enum":
            entries.extend(_enum_entries(module_name, name, value))
        elif kind == "class":
            entries.extend(_member_entries(module_name, name, value))
    return entries


def build_entries(
    modules: Sequence[str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[Entry, ...]:
    """The whole surface, in a stable order.

    ``py4gw``'s declared exports come first, then the namespaces in :data:`EXTRA_MODULES`. A record,
    enum or class is expanded **once**, in the module that declares it -- a namespace that re-exports
    it gets one line naming where it lives -- so the 347 records a naive walk finds are the 172 the
    library actually declares, each mapped once.
    """

    if modules is None:
        modules = discover_modules()
    seen_labels: set[str] = set()
    expanded: set[int] = set()
    entries: list[Entry] = []
    for module_name in modules:
        if progress is not None:
            progress(module_name)
        try:
            module_entries = entries_for(module_name, expanded)
        except Exception as error:  # noqa: BLE001 - a module that cannot be read is a finding
            entries.append(
                Entry(
                    group=module_name,
                    owner="",
                    name="<module could not be read>",
                    kind="module",
                    detail=f"{type(error).__name__}: {error}",
                    access="read",
                    run="none",
                )
            )
            continue
        for entry in module_entries:
            if entry.label in seen_labels:
                continue
            seen_labels.add(entry.label)
            entries.append(entry)
    return tuple(entries)


def find(entries: Iterable[Entry], query: str) -> list[Entry]:
    """Entries matching a query, for a caller that knows a member's name but not its module.

    A class is expanded in the module that **declares** it -- that is where its members live, and a
    name re-exported by ``py4gw`` names that home -- so a caller looking for ``Agent.Move`` should
    not have to know whether the class is declared in ``py4gw`` or in ``py4gw.agent``. The query is
    matched against the entry's path, case-insensitively, and against its last two parts
    (``Owner.member``) exactly.
    """

    wanted = query.strip().lower()
    if not wanted:
        return []
    matches: list[Entry] = []
    for entry in entries:
        label = entry.label.lower()
        tail = ".".join(entry.label.split(".")[-2:]).lower()
        if label == wanted or label.endswith("." + wanted) or tail == wanted:
            matches.append(entry)
    return matches


def outcomes_with_status(
    outcomes: Iterable[Outcome], status: str | None, needle: str = ""
) -> list[Outcome]:
    """The outcomes a reader asked to see: one status (or all), and a text filter.

    This is what the window's output buttons use, and it keeps the *order* of the run: filtering is
    a view of the same results, not a new run.
    """

    wanted = (status or "").strip().lower()
    text = needle.strip().lower()
    selected: list[Outcome] = []
    for outcome in outcomes:
        if wanted:
            if wanted == "not answered":
                if outcome.status == "answered":
                    continue
            elif outcome.status.lower() != wanted:
                continue
        if text:
            haystack = " ".join(
                (
                    outcome.entry.label,
                    outcome.entry.doc,
                    outcome.status,
                    outcome.value,
                    outcome.error,
                    outcome.output,
                )
            ).lower()
            if text not in haystack:
                continue
        selected.append(outcome)
    return selected


def statuses(outcomes: Iterable[Outcome]) -> dict[str, int]:
    """How many outcomes there are of each status, most frequent first."""

    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.status] = counts.get(outcome.status, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def summarise(entries: Iterable[Entry]) -> Summary:
    """Count a set of entries."""

    summary = Summary()
    for entry in entries:
        summary.total += 1
        summary.by_kind[entry.kind] = summary.by_kind.get(entry.kind, 0) + 1
        summary.by_group[entry.group] = summary.by_group.get(entry.group, 0) + 1
        if entry.run in ("call", "property", "field", "value"):
            summary.runnable += 1
        if entry.needs_client:
            summary.needs_client += 1
        if entry.access == "write":
            summary.writes += 1
        elif entry.access == "unknown":
            summary.unknown += 1
    return summary


def _owner_value(entry: Entry) -> Any:
    """The object an entry belongs to: the module, or the class inside it."""

    module = importlib.import_module(entry.group)
    if not entry.owner:
        return getattr(module, entry.name)
    return getattr(module, entry.owner)


def _instantiable(value: Any) -> bool:
    """Whether a class can be built with no arguments, which is what a zeroed record needs.

    A ``ctypes`` record is plain memory and is always built with no arguments; anything else is
    asked through its signature, because calling a class whose constructor connects or allocates
    would be a side effect this engine must not have.
    """

    if not isinstance(value, type):
        return False
    if issubclass(value, (ctypes.Structure, ctypes.Union)):
        return True
    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        return False
    for parameter in signature.parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if parameter.default is inspect.Parameter.empty:
            return False
    return True


def _format(value: Any, limit: int = 400) -> str:
    """A value as one readable line."""

    try:
        text = repr(value)
    except Exception as error:  # noqa: BLE001 - a value whose repr fails is still a result
        text = f"<repr raised {type(error).__name__}: {error}>"
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def run_entry(
    entry: Entry,
    include_writes: bool = False,
    include_unknown: bool = False,
    client_connected: bool = False,
    args: Sequence[Any] | None = None,
) -> Outcome:
    """Run one entry and report what it did, never raising.

    The order of the checks is the safety order. A write is skipped unless it was asked for. An
    unclassified member is skipped whenever a client is connected -- with something connected, an
    unclassified member cannot be told apart from a write -- and is run only when nothing is
    connected, where the library itself refuses every client-facing call, so the worst an
    unclassified member can do is report that refusal. That is the one run in which the whole
    surface can be exercised with no client and without asking for writes.

    ``args`` are the arguments for a member that needs them, and they are passed only when the
    member's own classification allows the call at all.
    """

    started = time.perf_counter()
    if entry.access == "write" and not include_writes:
        return Outcome(entry, "skipped (classified as a write)")

    # A member of this library reports through ``print`` as well as through its return value (the
    # skillbar's template encoder says why it could not encode, for one), so what a member writes is
    # part of what it produced and is captured with it rather than spilled onto the console.
    printed = io.StringIO()

    def finish(status: str, value: str = "", error: str = "") -> Outcome:
        return Outcome(
            entry,
            status,
            value=value,
            error=error,
            output=" ".join(printed.getvalue().split()),
            milliseconds=(time.perf_counter() - started) * 1000.0,
        )

    with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
        return _run_entry_body(
            entry, include_writes, include_unknown, client_connected, tuple(args or ()), finish
        )


def _run_entry_body(
    entry: Entry,
    include_writes: bool,
    include_unknown: bool,
    client_connected: bool,
    args: tuple[Any, ...],
    finish: Callable[..., Outcome],
) -> Outcome:
    """The body of :func:`run_entry`, with what the entry writes already captured."""

    if entry.run == "none":
        return finish("not runnable")

    # The skips come before anything is resolved: a member this engine will not run should not even
    # look its owner up, so a synthetic entry (a test's, or one from a module that failed to read)
    # is answered rather than raising. An unclassified member is skipped whenever a client is
    # connected -- an anonymous caller asking for "unknowns" cannot change what an unknown *is* --
    # unless writes were asked for too, in which case it is no worse than a write.
    if entry.access == "unknown" and entry.kind == "method":
        if client_connected and not include_writes:
            return finish("skipped (not classified, and a client is connected)")
        if not include_unknown:
            return finish("skipped (not classified: read or write)")

    if entry.kind == "enum member":
        # An enum member is a value, and the owner is the enum: ask it by name.
        try:
            owner = _owner_value(entry)
            return finish("answered", value=_format(owner[entry.name]))
        except Exception as error:  # noqa: BLE001 - a member that cannot be resolved
            return finish("failed", error=f"{type(error).__name__}: {error}")

    try:
        owner = _owner_value(entry)
    except Exception as error:  # noqa: BLE001 - a module or class that cannot be reached
        return finish("failed", error=f"{type(error).__name__}: {error}")

    if entry.kind == "field" or entry.run == "value":
        if entry.kind in ("record", "enum", "class", "function", "module", "mapping", "constant"):
            return finish("answered", value=_format(owner))
        if not _instantiable(owner):
            # A record whose constructor wants arguments (a namedtuple-like record, for instance):
            # its fields cannot be shown without an instance, and inventing one would show values
            # that exist nowhere.
            return finish("skipped (needs an instance)")
        try:
            instance = owner()
        except Exception as error:  # noqa: BLE001 - a record that cannot be built
            return finish("failed", error=f"cannot build the record: {type(error).__name__}: {error}")
        try:
            return finish("answered", value=_format(getattr(instance, entry.name)))
        except Exception as error:  # noqa: BLE001 - reading a field of a zeroed record
            return finish("failed", error=f"{type(error).__name__}: {error}")

    if entry.run == "property":
        cls = owner
        if not _instantiable(cls):
            return finish("needs a snapshot", error="the record needs an instance to read from")
        try:
            instance = cls()
        except Exception as error:  # noqa: BLE001 - a record that cannot be built
            return finish(
                "needs a snapshot",
                error=f"cannot build the record: {type(error).__name__}: {error}",
            )
        try:
            return finish("answered", value=_format(getattr(instance, entry.name)))
        except Exception as error:  # noqa: BLE001 - the port's own refusal is a result
            return finish("refused", error=f"{type(error).__name__}: {error}")

    if entry.run == "call":
        cls = owner
        try:
            attribute = getattr(cls, entry.name)
        except AttributeError as error:
            return finish("failed", error=f"the member is not on its owner: {error}")
        try:
            return finish("answered", value=_format(attribute()))
        except NotImplementedError as error:
            return finish("declared unavailable", error=str(error))
        except Exception as error:  # noqa: BLE001 - the library's own refusal is a result
            return finish("refused", error=f"{type(error).__name__}: {error}")

    if entry.run == "call-with-arguments":
        if not args:
            return finish("skipped (needs arguments)", error=", ".join(entry.parameters))
        cls = owner
        try:
            attribute = getattr(cls, entry.name)
        except AttributeError as error:
            return finish("failed", error=f"the member is not on its owner: {error}")
        try:
            return finish("answered", value=_format(attribute(*args)))
        except NotImplementedError as error:
            return finish("declared unavailable", error=str(error))
        except Exception as error:  # noqa: BLE001 - the library's own refusal is a result
            return finish("refused", error=f"{type(error).__name__}: {error}")

    return finish("not runnable")


def run_all(
    entries: Sequence[Entry],
    include_writes: bool = False,
    include_unknown: bool = False,
    client_connected: bool = False,
    progress: Callable[[int, int, Outcome], None] | None = None,
) -> list[Outcome]:
    """Run every entry, reporting each result as it happens.

    ``client_connected`` tells the engine whether something is connected, which decides whether an
    unclassified member may be run: see :func:`run_entry`. Entries that need arguments are reported
    as such rather than run: the window runs those one at a time, with the caller's own values.
    """

    outcomes: list[Outcome] = []
    for index, entry in enumerate(entries, start=1):
        outcome = run_entry(
            entry,
            include_writes=include_writes,
            include_unknown=include_unknown,
            client_connected=client_connected,
        )
        outcomes.append(outcome)
        if progress is not None:
            progress(index, len(entries), outcome)
    return outcomes


def report(entries: Sequence[Entry], outcomes: Sequence[Outcome]) -> str:
    """The whole surface and what running it produced, as text.

    The report is written for a human reader: a summary first, then every entry with its kind, its
    access classification and its own line of result -- and, at the end, the entries that were
    skipped, grouped by the reason they were skipped.
    """

    summary = summarise(entries)
    answered = sum(1 for outcome in outcomes if outcome.status == "answered")
    lines: list[str] = []
    lines.append("py4gw library surface")
    lines.append("=" * 78)
    lines.extend(summary.lines())
    lines.append(f"entries run: {len(outcomes)}; answered: {answered}")
    counts: dict[str, int] = {}
    for outcome in outcomes:
        key = outcome.status if outcome.status != "answered" else "answered"
        counts[key] = counts.get(key, 0) + 1
    lines.append("outcomes: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    lines.append("")
    lines.append("every entry")
    lines.append("-" * 78)
    outcomes_by_label = {outcome.entry.label: outcome for outcome in outcomes}
    for entry in entries:
        outcome = outcomes_by_label.get(entry.label)
        status = outcome.status if outcome is not None else "not run"
        show = outcome.value if outcome and outcome.value else (outcome.error if outcome else "")
        lines.append(
            f"{entry.kind:<12} {entry.access:<8} {status:<34} {entry.display}"
            + (f"  = {show}" if show else "")
        )
        if entry.access_reason:
            lines.append(f"{'':<12} why {entry.access}: {entry.access_reason}")
        if entry.doc:
            lines.append(f"{'':<12} {entry.doc}")
    skipped: dict[str, list[str]] = {}
    for outcome in outcomes:
        if outcome.status == "answered":
            continue
        skipped.setdefault(outcome.status, []).append(outcome.entry.label)
    if skipped:
        lines.append("")
        lines.append("what was not answered, by reason")
        lines.append("-" * 78)
        for reason, labels in sorted(skipped.items()):
            lines.append(f"{reason}: {len(labels)}")
            for label in sorted(labels):
                lines.append(f"    {label}")
    return "\n".join(lines)


def write_report(text: str, path: str | Path) -> Path:
    """Write a report to ``path``, creating its directory, and return where it went."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def summary_report(entries: Sequence[Entry], outcomes: Sequence[Outcome]) -> str:
    """The run as a short report: what was run, per module, and everything that did not answer.

    The full report (`report`) prints all ~20,000 entries; this one is what a person reads first:
    the counts, a module-by-module table of answered against not answered, and then **every entry
    that did not answer** with the reason it did not -- which is the list worth acting on. Entries
    that answered are counted, not listed; their values are in the full report.
    """

    by_label = {outcome.entry.label: outcome for outcome in outcomes}
    statuses: dict[str, int] = {}
    for outcome in outcomes:
        statuses[outcome.status] = statuses.get(outcome.status, 0) + 1
    per_module: dict[str, list[int]] = {}
    for entry in entries:
        outcome = by_label.get(entry.label)
        answered = 1 if outcome is not None and outcome.status == "answered" else 0
        counters = per_module.setdefault(entry.group, [0, 0])
        counters[0] += 1
        counters[1] += answered

    lines: list[str] = []
    lines.append("py4gw library surface -- summary")
    lines.append("=" * 70)
    lines.append(f"entries: {len(entries)} in {len(per_module)} modules; results: {len(outcomes)}")
    total_answered = statuses.get("answered", 0)
    lines.append(
        f"answered: {total_answered};  not answered: {len(outcomes) - total_answered}"
    )
    for status, count in sorted(statuses.items(), key=lambda item: -item[1]):
        lines.append(f"    {status:<45} {count}")
    lines.append("")
    lines.append("per module (entries / answered)")
    lines.append("-" * 70)
    for group in sorted(per_module, key=lambda name: (name != "py4gw", name)):
        total, answered = per_module[group]
        lines.append(f"    {group:<48} {total:>6} / {answered:>6}")
    lines.append("")
    lines.append("everything that did not answer, by status")
    lines.append("-" * 70)
    notable = [
        outcome
        for outcome in outcomes
        if outcome.status != "answered"
    ]
    grouped: dict[str, list[Outcome]] = {}
    for outcome in notable:
        grouped.setdefault(outcome.status, []).append(outcome)
    for status in sorted(grouped):
        lines.append("")
        lines.append(f"{status}: {len(grouped[status])}")
        for outcome in sorted(grouped[status], key=lambda item: item.entry.label):
            reason = outcome.error or outcome.value or outcome.output
            lines.append(f"    {outcome.entry.display}")
            if reason:
                lines.append(f"        {reason}")
            if outcome.entry.access_reason:
                lines.append(f"        why {outcome.entry.access}: {outcome.entry.access_reason}")
    return "\n".join(lines)


def write_summary_report(
    entries: Sequence[Entry], outcomes: Sequence[Outcome], path: str | Path
) -> Path:
    """Write the short report of a run and return where it went."""

    return write_report(summary_report(entries, outcomes), path)
