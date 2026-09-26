"""Load and execute the Reforged pattern resolver definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .remote import RemoteScanner
from .scanner import Pattern


class _scanner_api(Protocol):
    """Scanner operations needed by the resolver."""

    def find(self, pattern: Pattern, section: str = "text") -> int | None: ...

    def find_in_range(
        self,
        pattern: Pattern,
        start: int,
        end: int,
        limit: int | None = None,
    ) -> list[int]: ...

    def find_assertion(
        self,
        assertion_file: str,
        assertion_message: str,
        line_number: int = 0,
        offset: int = 0,
    ) -> int | None: ...

    def find_nth_use_of_string(
        self,
        value: str,
        occurrence: int,
        offset: int = 0,
        section: str = "text",
        wide: bool = False,
    ) -> int | None: ...

    def function_from_near_call(
        self,
        call_address: int,
        check_valid_ptr: bool = True,
    ) -> int | None: ...

    def to_function_start(self, address: int, scan_range: int = 0xFF) -> int | None: ...

    def is_valid_ptr(self, address: int, section: str = "data") -> bool: ...

    def read_uint32(self, address: int) -> int: ...

    def to_module_address(self, va: int) -> int: ...


@dataclass(frozen=True)
class PatternDefinition:
    """One pattern entry loaded from an offsets JSON file."""

    name: str
    pattern: Pattern | None
    literal: str | None
    assertion_file: str | None
    assertion_message: str | None
    line_number: int
    offset: int
    section: str


@dataclass(frozen=True)
class ResolverStep:
    """One operation in a pointer resolver chain."""

    name: str
    operation: str
    input_name: str
    output_name: str
    pattern_name: str
    literal: str
    start_name: str
    end_name: str
    start_add: int
    end_add: int
    value: int
    occurrence: int
    scan_range: int
    check_valid_ptr: bool
    wide: bool
    section: str


@dataclass(frozen=True)
class ResolverAttempt:
    """One fallback attempt for a resolver."""

    name: str
    steps: tuple[ResolverStep, ...]


@dataclass(frozen=True)
class ResolverDefinition:
    """One named resolver and its failure policy."""

    name: str
    module: str
    severity: str
    action: str
    attempts: tuple[ResolverAttempt, ...]


@dataclass(frozen=True)
class ResolutionTraceStep:
    """The observable result of one resolver step."""

    name: str
    operation: str
    input_value: int
    output_value: int
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class ResolutionResult:
    """A resolver result with failure context and step trace."""

    name: str
    module: str
    ok: bool
    value: int = 0
    selected_attempt: str = ""
    failed_attempt: str = ""
    failed_step: str = ""
    message: str = ""
    severity: str = "error"
    action: str = "halt"
    trace: tuple[ResolutionTraceStep, ...] = ()

    @property
    def should_continue(self) -> bool:
        """Return whether a failed result follows a continue policy."""

        return self.ok or self.action == "continue"


class PatternCatalog:
    """Load copied offsets files and resolve named pointer chains."""

    def __init__(
        self,
        patterns: dict[str, PatternDefinition],
        resolvers: dict[str, ResolverDefinition],
    ) -> None:
        """Create a catalog from already parsed definitions."""

        self._patterns = patterns
        self._resolvers = resolvers

    @classmethod
    def from_directory(cls, directory: str | Path) -> PatternCatalog:
        """Load all JSON definitions from one offsets directory."""

        path = Path(directory)
        if not path.is_absolute() and not path.is_dir():
            project_path = Path(__file__).resolve().parents[2] / path
            if project_path.is_dir():
                path = project_path
        if not path.is_dir():
            raise FileNotFoundError(f"Offsets directory does not exist: {path}")
        patterns: dict[str, PatternDefinition] = {}
        resolvers: dict[str, ResolverDefinition] = {}
        for file_path in sorted(path.glob("*.json")):
            root = json.loads(file_path.read_text(encoding="utf-8"))
            namespace = str(root.get("namespace", ""))
            cls._load_patterns(root.get("patterns", {}), namespace, patterns)
            cls._load_resolvers(root.get("resolvers", {}), namespace, resolvers)
        if not patterns and not resolvers:
            raise ValueError(f"Offsets directory contains no definitions: {path}")
        return cls(patterns, resolvers)

    def get_pattern(self, name: str) -> PatternDefinition:
        """Return one named pattern definition."""

        try:
            return self._patterns[name]
        except KeyError as error:
            raise KeyError(f"Pattern definition not found: {name}") from error

    def get_resolver(self, name: str) -> ResolverDefinition:
        """Return one named resolver definition."""

        try:
            return self._resolvers[name]
        except KeyError as error:
            raise KeyError(f"Resolver definition not found: {name}") from error

    def resolve(self, name: str, scanner: _scanner_api) -> ResolutionResult:
        """Execute one resolver and return its value or detailed failure."""

        resolver = self.get_resolver(name)
        last_result: ResolutionResult | None = None
        for attempt in resolver.attempts:
            result = self._run_attempt(resolver, attempt, scanner)
            if result.ok:
                return result
            last_result = result
        if last_result is None:
            return ResolutionResult(
                name=name,
                module=resolver.module,
                ok=False,
                message="Resolver has no attempts.",
                severity=resolver.severity,
                action=resolver.action,
            )
        return last_result

    @classmethod
    def _load_patterns(
        cls,
        values: Any,
        namespace: str,
        output: dict[str, PatternDefinition],
    ) -> None:
        """Parse pattern entries from one JSON object."""

        if not isinstance(values, dict):
            return
        for raw_name, value in values.items():
            if not isinstance(value, dict):
                raise ValueError(f"Pattern {raw_name} must be an object.")
            name = cls._qualify(namespace, str(raw_name))
            if name in output:
                raise ValueError(f"Duplicate pattern definition: {name}")
            literal = value.get("pattern")
            mask = value.get("mask")
            offset = cls._parse_int(value.get("offset", 0))
            pattern = None
            if literal is not None and str(literal) != "":
                pattern = Pattern.from_literal(
                    str(literal),
                    str(mask) if mask else None,
                    offset,
                )
            output[name] = PatternDefinition(
                name=name,
                pattern=pattern,
                literal=str(literal) if literal is not None else None,
                assertion_file=cls._optional_string(value.get("assertion_file")),
                assertion_message=cls._optional_string(value.get("assertion_message")),
                line_number=cls._parse_int(value.get("line_number", 0)),
                offset=offset,
                section=str(value.get("section", "text")),
            )

    @classmethod
    def _load_resolvers(
        cls,
        values: Any,
        namespace: str,
        output: dict[str, ResolverDefinition],
    ) -> None:
        """Parse resolver chains and fallback attempts from one JSON object."""

        if not isinstance(values, dict):
            return
        for raw_name, value in values.items():
            if not isinstance(value, dict):
                raise ValueError(f"Resolver {raw_name} must be an object.")
            name = cls._qualify(namespace, str(raw_name))
            if name in output:
                raise ValueError(f"Duplicate resolver definition: {name}")
            raw_attempts = value.get("attempts")
            if raw_attempts is None:
                raw_attempts = [{"name": "default", "steps": value.get("steps", [])}]
            attempts = tuple(
                cls._parse_attempt(attempt, namespace)
                for attempt in raw_attempts
            )
            if not attempts or any(not attempt.steps for attempt in attempts):
                raise ValueError(f"Resolver {name} has no steps.")
            output[name] = ResolverDefinition(
                name=name,
                module=str(value.get("module", namespace or name.split(".", 1)[0])),
                severity=str(value.get("log_level", "error")).lower(),
                action=str(value.get("on_fail", "halt")).lower(),
                attempts=attempts,
            )

    @classmethod
    def _parse_attempt(cls, value: Any, namespace: str) -> ResolverAttempt:
        """Parse one resolver attempt."""

        if not isinstance(value, dict):
            raise ValueError("Resolver attempt must be an object.")
        steps = tuple(
            cls._parse_step(step, namespace) for step in value.get("steps", [])
        )
        return ResolverAttempt(str(value.get("name", "default")), steps)

    @classmethod
    def _parse_step(cls, value: Any, namespace: str) -> ResolverStep:
        """Parse one resolver operation."""

        if not isinstance(value, dict):
            raise ValueError("Resolver step must be an object.")
        pattern_name = str(value.get("pattern", ""))
        if pattern_name:
            pattern_name = cls._qualify(namespace, pattern_name)
        return ResolverStep(
            name=str(value.get("name", value.get("op", ""))),
            operation=str(value.get("op", "")).lower(),
            input_name=str(value.get("in", "")),
            output_name=str(value.get("out", "value")),
            pattern_name=pattern_name,
            literal=str(value.get("literal", "")),
            start_name=str(value.get("start", "")),
            end_name=str(value.get("end", "")),
            start_add=cls._parse_int(value.get("start_add", 0)),
            end_add=cls._parse_int(value.get("end_add", 0)),
            value=cls._parse_int(value.get("value", 0)),
            occurrence=cls._parse_int(value.get("nth", 0)),
            scan_range=cls._parse_int(value.get("scan_range", 0xFF)),
            check_valid_ptr=cls._parse_bool(value.get("check_valid_ptr", True)),
            wide=cls._parse_bool(value.get("wide", False)),
            section=str(value.get("section", "text")),
        )

    def _run_attempt(
        self,
        resolver: ResolverDefinition,
        attempt: ResolverAttempt,
        scanner: _scanner_api,
    ) -> ResolutionResult:
        """Execute one attempt and retain a trace for every step."""

        values: dict[str, int] = {}
        trace: list[ResolutionTraceStep] = []
        for step in attempt.steps:
            input_value = values.get(step.input_name, 0) if step.input_name else 0
            output_value = 0
            detail = ""
            try:
                output_value = self._run_step(step, values, scanner)
                ok = output_value != 0
                if not ok:
                    detail = "operation returned no address"
            except (KeyError, OSError, ValueError) as error:
                ok = False
                detail = str(error)
            trace.append(
                ResolutionTraceStep(
                    name=step.name,
                    operation=step.operation,
                    input_value=input_value,
                    output_value=output_value,
                    ok=ok,
                    detail=detail,
                )
            )
            if not ok:
                return ResolutionResult(
                    name=resolver.name,
                    module=resolver.module,
                    ok=False,
                    selected_attempt=attempt.name,
                    failed_attempt=attempt.name,
                    failed_step=step.name,
                    message=detail,
                    severity=resolver.severity,
                    action=resolver.action,
                    trace=tuple(trace),
                )
            values[step.output_name] = output_value

        if "final" not in values:
            return ResolutionResult(
                name=resolver.name,
                module=resolver.module,
                ok=False,
                selected_attempt=attempt.name,
                failed_attempt=attempt.name,
                failed_step="final",
                message="Resolver did not populate final output.",
                severity=resolver.severity,
                action=resolver.action,
                trace=tuple(trace),
            )
        return ResolutionResult(
            name=resolver.name,
            module=resolver.module,
            ok=True,
            value=values["final"],
            selected_attempt=attempt.name,
            severity=resolver.severity,
            action=resolver.action,
            trace=tuple(trace),
        )

    def _run_step(
        self,
        step: ResolverStep,
        values: dict[str, int],
        scanner: _scanner_api,
    ) -> int:
        """Execute one parsed resolver operation."""

        if step.operation in {"scan", "pattern_scan", "pattern"}:
            definition = self.get_pattern(step.pattern_name)
            if definition.pattern is not None:
                value = scanner.find(definition.pattern, definition.section)
            elif definition.assertion_file and definition.assertion_message:
                value = scanner.find_assertion(
                    definition.assertion_file,
                    definition.assertion_message,
                    definition.line_number,
                    definition.offset,
                )
            else:
                return 0
            return value or 0

        if step.operation in {"scan_in_range", "pattern_scan_in_range", "find_in_range"}:
            definition = self.get_pattern(step.pattern_name)
            if definition.pattern is None:
                return 0
            start = self._value(values, step.start_name) + step.start_add
            end = self._value(values, step.end_name) + step.end_add
            matches = scanner.find_in_range(definition.pattern, start, end, limit=1)
            return matches[0] if matches else 0

        if step.operation == "to_function_start":
            return scanner.to_function_start(
                self._value(values, step.input_name), step.scan_range
            ) or 0

        if step.operation == "function_from_near_call":
            return scanner.function_from_near_call(
                self._value(values, step.input_name), step.check_valid_ptr
            ) or 0

        if step.operation in {"find_use_of_string", "use_of_string", "scan_use_of_string"}:
            value = step.literal
            offset = 0
            section = "text"
            if step.pattern_name:
                definition = self.get_pattern(step.pattern_name)
                value = definition.literal or ""
                offset = definition.pattern.offset if definition.pattern else 0
                section = definition.section
            return scanner.find_nth_use_of_string(
                value, step.occurrence, offset, section, step.wide
            ) or 0

        if step.operation in {"deref", "dereference", "read_u32", "read_uint32"}:
            return scanner.read_uint32(self._value(values, step.input_name))

        if step.operation in {"module_relative", "rebase", "to_module_address"}:
            # A hardcoded client virtual address from the source, rebased onto the live
            # module. Native keeps these constants in `DialogMemory` and rebases them
            # with `ToRuntimeAddress` (`dialog_patterns.cpp:21-31`); its own note says
            # they could not live in the JSON pattern system because it had no
            # module-base-relative op. This is that op.
            return scanner.to_module_address(step.value)

        if step.operation == "add":
            return self._value(values, step.input_name) + step.value

        if step.operation in {"divide", "div"}:
            if step.value == 0:
                raise ValueError("Cannot divide by zero.")
            return self._value(values, step.input_name) // step.value

        if step.operation == "validate_section":
            value = self._value(values, step.input_name)
            if not scanner.is_valid_ptr(value, step.section):
                return 0
            return value

        raise ValueError(f"Unsupported resolver operation: {step.operation}")

    @staticmethod
    def _value(values: dict[str, int], name: str) -> int:
        """Return one named intermediate value."""

        if name not in values:
            raise KeyError(f"Resolver value not found: {name}")
        return values[name]

    @staticmethod
    def _qualify(namespace: str, name: str) -> str:
        """Apply a JSON namespace to an unqualified name."""

        return name if not namespace or "." in name else f"{namespace}.{name}"

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        """Return a non-empty JSON string or ``None``."""

        return str(value) if value not in (None, "") else None

    @staticmethod
    def _parse_int(value: Any) -> int:
        """Parse decimal or hexadecimal integer fields."""

        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        return int(str(value), 0)

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse the boolean forms accepted by the native loader."""

        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        return str(value).lower() in {"true", "1", "yes"}
