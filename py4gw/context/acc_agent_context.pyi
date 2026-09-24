from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from typing import Any, Optional

from .game_context import GameContext
from .gw_array import GWArray, RemoteMemoryReader


class Vec3fStruct(TargetStruct):
    x: float
    y: float
    z: float


Vec3f = Vec3fStruct


class AgentSummaryInfoSubStruct(TargetStruct):
    h0000: int
    h0004: int
    gadget_id: int
    h000C: int
    gadget_name_enc: int
    h0014: int
    composite_agent_id: int

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = ...
    ) -> AgentSummaryInfoSubStruct: ...

    @property
    def gadget_name_encoded_str(self) -> str | None: ...

    @property
    def gadget_name_str(self) -> str | None: ...


AgentSummaryInfoSub = AgentSummaryInfoSubStruct


class AgentSummaryInfoStruct(TargetStruct):
    h0000: int
    h0004: int
    extra_info_sub_ptr: int

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = ...
    ) -> AgentSummaryInfoStruct: ...

    @property
    def extra_info_sub(self) -> AgentSummaryInfoSubStruct | None: ...


AgentSummaryInfo = AgentSummaryInfoStruct


class AgentMovementStruct(TargetStruct):
    h0000: Any
    agent_id: int
    h0010: Any
    agent_def: int
    h0020: Any
    moving1: int
    h003C: Any
    moving2: int
    h0048: Any
    h0064: Vec3fStruct
    h0070: int
    h0074: Vec3fStruct

    @property
    def agentDef(self) -> int: ...


AgentMovement = AgentMovementStruct


class AgentInfoStruct(TargetStruct):
    h0000: Any
    name_enc: int


AgentInfo = AgentInfoStruct
AgentInfoArray = GWArray


class AccAgentContextStruct(TargetStruct):
    h0000_array: GWArray
    h0010: Any
    h0024: int
    h0028: Any
    h0030: int
    h0034: Any
    h003C: int
    h0040: Any
    h0048: int
    h004C: Any
    h0054: int
    h0058: Any
    h0084_array: GWArray
    h0094: int
    agent_summary_info_array: GWArray
    h00A8_array: GWArray
    h00B8_array: GWArray
    rand1: int
    rand2: int
    h00D0: Any
    agent_movement_array: GWArray
    h00F8_array: GWArray
    h0108: Any
    h014C_array: GWArray
    h015C_array: GWArray
    h016C: Any
    instance_timer: int

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = ...
    ) -> AccAgentContextStruct: ...

    @property
    def remote_address(self) -> int | None: ...

    @property
    def h0000(self) -> GWArray: ...

    @property
    def h0084(self) -> GWArray: ...

    @property
    def agent_summary_info(self) -> GWArray: ...

    @property
    def h00A8(self) -> GWArray: ...

    @property
    def h00B8(self) -> GWArray: ...

    @property
    def agent_movement(self) -> GWArray: ...

    @property
    def h00F8(self) -> GWArray: ...

    @property
    def agent_array1(self) -> GWArray: ...

    @property
    def agent_async_movement(self) -> GWArray: ...

    @property
    def h0000_ptrs(self) -> list[int]: ...

    @property
    def h0084_ptrs(self) -> list[int]: ...

    @property
    def agent_summary_info_list(self) -> list[AgentSummaryInfoStruct]: ...

    @property
    def h00A8_ptrs(self) -> list[int]: ...

    @property
    def h00B8_ptrs(self) -> list[int]: ...

    @property
    def agent_movement_ptrs(self) -> list[AgentMovementStruct | None] | None: ...

    @property
    def valid_agents_ids(self) -> list[int]: ...

    @property
    def h00F8_ptrs(self) -> list[int]: ...

    @property
    def h014C_ptrs(self) -> list[int]: ...

    @property
    def h015C_ptrs(self) -> list[int]: ...


AgentContextStruct = AccAgentContextStruct


class AccAgentContext:
    _ptr: int
    _cached_ctx: AccAgentContextStruct | None
    _callback_name: str

    def __init__(self, reader: RemoteMemoryReader, game_context: GameContext) -> None: ...

    @staticmethod
    def get_ptr() -> int: ...

    @staticmethod
    def _update_ptr() -> None: ...

    @staticmethod
    def enable() -> None: ...

    @staticmethod
    def disable() -> None: ...

    @staticmethod
    def get_context() -> Optional[AccAgentContextStruct]: ...

    def resolve_address(self) -> int | None: ...

    def read(self) -> AccAgentContextStruct | None: ...


AgentContext = AccAgentContext


def get() -> AccAgentContextStruct | None: ...
