from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class PlayerAgentIdStruct(TargetStruct):
    agent_id: int


class PlayerAgentId:
    _ptr: int
    _cached_ctx: PlayerAgentIdStruct | None
    _callback_name: str

    def __init__(
        self,
        reader: RemoteMemoryReader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None: ...

    @staticmethod
    def get_ptr() -> int: ...

    @staticmethod
    def _update_ptr() -> None: ...

    @staticmethod
    def enable() -> None: ...

    @staticmethod
    def disable() -> None: ...

    @staticmethod
    def get_context() -> PlayerAgentIdStruct | None: ...

    def initialize(self) -> int | None: ...

    def resolve_address(self) -> int | None: ...

    @property
    def cached_pointer_address(self) -> int | None: ...

    def read(self) -> PlayerAgentIdStruct | None: ...


def get() -> PlayerAgentIdStruct | None: ...
