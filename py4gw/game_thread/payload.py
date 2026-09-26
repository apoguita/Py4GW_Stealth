"""The code that runs inside the client when the game thread reaches our stub.

The stub pushes the address of the shared block and calls into this. One call
does one bounded piece of work:

    validate the block header
    take at most one command the host has published
    run it
    publish the result, then publish a completion event if the event region has
    room for one

How the stub calls it is a contract, and this file is the other half of it:

* ``__stdcall``, one argument — the block address — and the callee pops it, so
  the caller has nothing to clean up afterwards;
* every register this code touches is saved and restored, so it is a well-behaved
  function of the platform ABI and the stub's own ``pushad`` is a second belt
  rather than the only one;
* flags are left modified. The stub saves and restores those, which is where that
  belongs.

The dispatcher takes the block as an argument and jumps only to its own labels,
so there is no absolute address anywhere in it. It is position independent by
construction, needs no relocation step, and can be written at any address the
installer finds.

What it deliberately does not do is call into the client. Nothing here needs to,
and a call needs a bounded target and a typed argument form — the vocabulary that
comes with the operations that require it. An operation this code does not know
completes as ``FAILED`` with ``RESULT_UNKNOWN_OPERATION``, which is a different
thing from an operation that quietly did something else.

The bytes below have been executed, not merely assembled: the offline harness
allocates executable memory in the test process, copies the emitted code into it
and calls it against a fake block. See ``tests/test_payload_offline.py``.
"""

from __future__ import annotations

import struct

from .shared_block import (
    COMMAND_DEPTH,
    COMMAND_OFFSET,
    COMMAND_REGION_OFFSET,
    COMMAND_SIZE,
    DECODE_CAPACITY,
    DECODE_SLOT_LENGTH_OFFSET,
    DECODE_SLOT_OUTPUT_OFFSET,
    DECODE_SLOT_STATE_OFFSET,
    DESCRIPTOR_DEPTH,
    DESCRIPTOR_OFFSET,
    DESCRIPTOR_SIZE,
    EVENT_DEPTH,
    EVENT_OFFSET,
    EVENT_REGION_OFFSET,
    EVENT_SIZE,
    HEADER_OFFSET,
    HEADER_SIZE,
    MAGIC,
    PING_RESULT,
    RESULT_BAD_DESCRIPTOR,
    RESULT_BAD_TARGET,
    RESULT_NO_TARGET,
    RESULT_UNKNOWN_FORM,
    RESULT_UNKNOWN_OPERATION,
    VERSION,
    WATCH_DEPTH,
    WATCH_SIZE,
    CallForm,
    CommandState,
    DecodeState,
    EVENT_TEXT_LENGTH_OFFSET,
    EVENT_TEXT_OFFSET,
    EVENT_TEXT_STATE_OFFSET,
    EVENT_TEXT_WORDS,
    EventKind,
    EventTextState,
    Operation,
    WATCH_STRING_OFFSET,
)

_UINT32_MAX = 0xFFFFFFFF

#: 32-bit register codes, as they appear in a ModRM byte.
_EAX, _ECX, _EDX, _EBX, _ESP, _EBP, _ESI, _EDI = range(8)

#: ``mod`` values: one-byte displacement, four-byte displacement, register.
_MOD_DISP8 = 1
_MOD_DISP32 = 2
_MOD_REGISTER = 3

#: ``rm`` value meaning a SIB byte follows the ModRM byte.
_SIB_FOLLOWS = 0b100

#: The low byte of a near conditional jump: ``0F 8x`` plus a rel32.
_JB = 0x82
_JAE = 0x83
_JE = 0x84
_JNE = 0x85

#: Instructions with no operand of their own.
_PUSHAD = bytes((0x60,))
_POPAD = bytes((0x61,))
_PUSH_EAX = bytes((0x50,))
_POP_EAX = bytes((0x58,))
_INC_EAX = bytes((0x40,))
_INC_EDI = bytes((0x47,))
_TEST_EBX_EBX = bytes((0x85, 0xDB))
_TEST_EDX_EDX = bytes((0x85, 0xD2))
_TEST_EAX_EAX = bytes((0x85, 0xC0))
_TEST_ESI_ESI = bytes((0x85, 0xF6))
_TEST_EDI_EDI = bytes((0x85, 0xFF))
#: ``inc ecx`` and ``inc edi``, the two counters the emitted loops keep.
_INC_ECX = bytes((0x41,))
#: ``mov ebx, [esp+36]``: the block argument, read past the 32 bytes ``pushad``
#: pushed and the 4 bytes of return address above it.
_MOV_EBX_ARG = bytes((0x8B, 0x5C, 0x24, 0x24))
#: ``ret 4``: the callee pops the argument the stub pushed for it, so the stub
#: has nothing to clean up after the call.
_EPILOGUE = bytes((0xC2, 0x04, 0x00))


def _imm8(value: int) -> int:
    """Return a value the one-byte immediate forms can carry, or refuse it.

    The one-byte immediate is sign-extended, so a constant of 128 or more would
    silently become negative. Refusing here turns that into a build-time error
    instead of a wrong comparison inside the client.
    """

    if not 0 <= value <= 0x7F:
        raise ValueError(f"{value} does not fit a one-byte immediate.")
    return value


def _modrm(mod: int, reg: int, rm: int) -> int:
    """Return a ModRM byte."""

    return (mod << 6) | (reg << 3) | rm


def _memory(
    reg: int, base: int, disp: int, index: int | None = None, scale: int = 1
) -> bytes:
    """Return the ModRM and SIB bytes that address ``[base + index*scale + disp]``.

    A displacement that fits one signed byte is encoded as one, so the emitted
    code is the same size an assembler would produce. ``esp`` as a base always
    needs the SIB byte, which is why the no-index case still has two forms.

    ``scale`` is the SIB's own two-bit field, so only 1, 2, 4 and 8 exist; the
    decoder stub walks a wide string, which is what asks for 2.
    """

    if index is not None and scale not in (1, 2, 4, 8):
        raise ValueError(f"an index scale must be 1, 2, 4 or 8, not {scale}.")

    if index is None and base != _ESP:
        if -128 <= disp <= 127:
            return bytes((_modrm(_MOD_DISP8, reg, base), disp & 0xFF))
        return bytes((_modrm(_MOD_DISP32, reg, base),)) + struct.pack("<i", disp)

    scale_bits = {1: 0, 2: 1, 4: 2, 8: 3}[scale] if index is not None else 0
    sib = _modrm(scale_bits, _ESP if index is None else index, base)
    if -128 <= disp <= 127:
        return bytes((_modrm(_MOD_DISP8, reg, _SIB_FOLLOWS), sib, disp & 0xFF))
    return bytes((_modrm(_MOD_DISP32, reg, _SIB_FOLLOWS), sib)) + struct.pack(
        "<i", disp
    )


def _mov_r32_mem(dst: int, base: int, disp: int, index: int | None = None) -> bytes:
    """Return ``mov dst, [base + index + disp]`` (``8B /r``)."""

    return bytes((0x8B,)) + _memory(dst, base, disp, index)


def _movzx_r32_word(
    dst: int, base: int, index: int, disp: int = 0, scale: int = 1
) -> bytes:
    """Return ``movzx dst, word [base + index*scale + disp]`` (``0F B7 /r``)."""

    return bytes((0x0F, 0xB7)) + _memory(dst, base, disp, index, scale)


def _mov_word_mem_r16(
    base: int, disp: int, src: int, index: int | None = None, scale: int = 1
) -> bytes:
    """Return ``mov word [base + index*scale + disp], src`` (``66 89 /r``).

    The operand-size prefix is what makes this a sixteen-bit store: the decoder stub writes a
    wide string, one UTF-16 code unit at a time.
    """

    return bytes((0x66, 0x89)) + _memory(src, base, disp, index, scale)


def _mov_mem_r32(base: int, disp: int, src: int, index: int | None = None) -> bytes:
    """Return ``mov [base + index + disp], src`` (``89 /r``)."""

    return bytes((0x89,)) + _memory(src, base, disp, index)


def _mov_mem_imm32(
    base: int, disp: int, value: int, index: int | None = None
) -> bytes:
    """Return ``mov dword [base + index + disp], imm32`` (``C7 /0``)."""

    return (
        bytes((0xC7,))
        + _memory(0, base, disp, index)
        + struct.pack("<I", value & _UINT32_MAX)
    )


def _lea_r32_mem(dst: int, base: int, disp: int, index: int | None = None) -> bytes:
    """Return ``lea dst, [base + index + disp]`` (``8D /r``)."""

    return bytes((0x8D,)) + _memory(dst, base, disp, index)


def _cmp_mem_imm32(
    base: int, disp: int, value: int, index: int | None = None
) -> bytes:
    """Return ``cmp dword [base + index + disp], imm32`` (``81 /7``)."""

    return (
        bytes((0x81,))
        + _memory(7, base, disp, index)
        + struct.pack("<I", value & _UINT32_MAX)
    )


def _cmp_mem_imm8(
    base: int, disp: int, value: int, index: int | None = None
) -> bytes:
    """Return ``cmp dword [base + index + disp], imm8`` (``83 /7``)."""

    return bytes((0x83,)) + _memory(7, base, disp, index) + bytes((_imm8(value),))


def _cmp_mem_r32(base: int, disp: int, src: int, index: int | None = None) -> bytes:
    """Return ``cmp dword [base + index + disp], src`` (``39 /r``)."""

    return bytes((0x39,)) + _memory(src, base, disp, index)


def _add_r32_mem(dst: int, base: int, disp: int, index: int | None = None) -> bytes:
    """Return ``add dst, [base + index + disp]`` (``03 /r``)."""

    return bytes((0x03,)) + _memory(dst, base, disp, index)


def _mov_r32_imm32(reg: int, value: int) -> bytes:
    """Return ``mov reg, imm32`` (``B8+rd``)."""

    return bytes((0xB8 + reg,)) + struct.pack("<I", value & _UINT32_MAX)


def _mov_r32_r32(dst: int, src: int) -> bytes:
    """Return ``mov dst, src`` (``89 /r``)."""

    return bytes((0x89, _modrm(_MOD_REGISTER, src, dst)))


def _cmp_r32_r32(left: int, right: int) -> bytes:
    """Return ``cmp left, right`` (``39 /r``)."""

    return bytes((0x39, _modrm(_MOD_REGISTER, right, left)))


def _cmp_r32_imm8(reg: int, value: int) -> bytes:
    """Return ``cmp reg, imm8`` (``83 /7``)."""

    return bytes((0x83, _modrm(_MOD_REGISTER, 7, reg), _imm8(value)))


def _cmp_r32_imm32(reg: int, value: int) -> bytes:
    """Return ``cmp reg, imm32`` (``81 /7``)."""

    return bytes((0x81, _modrm(_MOD_REGISTER, 7, reg))) + struct.pack(
        "<I", value & _UINT32_MAX
    )


def _sub_r32_r32(dst: int, src: int) -> bytes:
    """Return ``sub dst, src`` (``2B /r``)."""

    return bytes((0x2B, _modrm(_MOD_REGISTER, dst, src)))


def _xor_r32_r32(dst: int, src: int) -> bytes:
    """Return ``xor dst, src`` (``31 /r``)."""

    return bytes((0x31, _modrm(_MOD_REGISTER, src, dst)))


def _and_r32_imm8(reg: int, value: int) -> bytes:
    """Return ``and reg, imm8`` (``83 /4``)."""

    return bytes((0x83, _modrm(_MOD_REGISTER, 4, reg), _imm8(value)))


def _shl_r32_imm8(reg: int, value: int) -> bytes:
    """Return ``shl reg, imm8`` (``C1 /4``)."""

    return bytes((0xC1, _modrm(_MOD_REGISTER, 4, reg), _imm8(value)))


def _add_r32_imm32(reg: int, value: int) -> bytes:
    """Return ``add reg, imm32`` (``81 /0``).

    Not the ``05+rd`` form: that shortcut exists for ``mov`` and ``push``, not for
    ``add``, where opcode 0x05 means ``add eax`` and nothing else. Using it for
    another register emits a valid-looking instruction that adds to the wrong one.
    """

    return bytes((0x81, _modrm(_MOD_REGISTER, 0, reg))) + struct.pack(
        "<I", value & _UINT32_MAX
    )


def _sub_esp_imm8(value: int) -> bytes:
    """Return ``sub esp, imm8`` (``83 /5``), which reserves stack space."""

    return bytes((0x83, _modrm(_MOD_REGISTER, 5, _ESP), _imm8(value)))


def _add_esp_imm8(value: int) -> bytes:
    """Return ``add esp, imm8`` (``83 /0``), which releases stack space."""

    return bytes((0x83, _modrm(_MOD_REGISTER, 0, _ESP), _imm8(value)))


def _push_imm8(value: int) -> bytes:
    """Return ``push imm8`` (``6A ib``)."""

    return bytes((0x6A, _imm8(value)))


def _push_r32(reg: int) -> bytes:
    """Return ``push reg`` (``50+rd``)."""

    return bytes((0x50 + reg,))


def _call_r32(reg: int) -> bytes:
    """Return ``call reg`` (``FF /2``)."""

    return bytes((0xFF, _modrm(_MOD_REGISTER, 2, reg)))


def _mov_r32_esp(dst: int) -> bytes:
    """Return ``mov dst, esp`` (``89 /r`` with esp as the source)."""

    return bytes((0x89, _modrm(_MOD_REGISTER, _ESP, dst)))


def _power_of_two_shift(value: int, name: str) -> int:
    """Return the shift that multiplies by ``value``, refusing anything else."""

    if value <= 0 or value & (value - 1):
        raise ValueError(f"{name} must be a power of two; it is {value}.")
    return value.bit_length() - 1


def _slot_mask(depth: int, name: str) -> int:
    """Return the slot mask of a ring, refusing a depth it cannot address."""

    _power_of_two_shift(depth, name)
    return depth - 1


#: The slot of a record is its counter's low bits, and a record's address is its
#: slot scaled by the record size. Both need the layout constant to be a power of
#: two; both are checked here rather than discovered as a wrong address later.
_COMMAND_SLOT_MASK = _slot_mask(COMMAND_DEPTH, "COMMAND_DEPTH")
_EVENT_SLOT_MASK = _slot_mask(EVENT_DEPTH, "EVENT_DEPTH")
_COMMAND_SLOT_SHIFT = _power_of_two_shift(COMMAND_SIZE, "COMMAND_SIZE")
_EVENT_SLOT_SHIFT = _power_of_two_shift(EVENT_SIZE, "EVENT_SIZE")
_DESCRIPTOR_SLOT_SHIFT = _power_of_two_shift(DESCRIPTOR_SIZE, "DESCRIPTOR_SIZE")

#: The header fields the payload checks before it trusts anything else. These are
#: the ones that decide how it reads the rest of the block, so a mismatch means
#: every later offset would be wrong. The reserved words are the host's own check,
#: and ``session_id`` decides nothing about addressing.
_HEADER_CHECKS = (
    ("magic", MAGIC),
    ("version", VERSION),
    ("header_size", HEADER_SIZE),
    ("command_depth", COMMAND_DEPTH),
    ("event_depth", EVENT_DEPTH),
)

#: The operations this payload runs, and the label its code lives under.
_OPERATIONS = (
    (Operation.NOP, "nop"),
    (Operation.PING, "ping"),
    (Operation.ADD_U32, "add"),
    (Operation.ECHO_U32, "echo"),
    (Operation.CALL, "call"),
)

#: The packed argument payload a UI message carries: sixteen words, all zero,
#: with the command's words packed into the front. ``ui_bindings.cpp:60-74``.
_UI_PAYLOAD_BYTES = 64

#: How many of those words a command can carry. The rest of the payload is zero.
_UI_PAYLOAD_WORDS = 2

#: The four-float array ``MoveToFn`` takes, built in our own frame from the
#: command's three words plus a zero: ``{x, y, (float)zplane, 0.0f}``
#: (``agent_methods.cpp:149-153``). Native builds the same array on its own stack
#: and passes its address, so the pointer is valid for the call and no longer —
#: the same lifetime the source gives it.
_FLOAT_ARRAY_BYTES = 16

#: The command fields an event carries, as ``(event field, command field)``.
_EVENT_SOURCES = (
    ("sequence", "sequence"),
    ("arg0", "operation"),
    ("arg1", "state"),
    ("arg2", "result"),
)

#: The event fields written as zero. ``tick`` is among them because nothing
#: produces a tick yet: the header has no frame counter to read one from.
_EVENT_ZEROES = ("arg3", "tick", "reserved")


class _Code:
    """A byte buffer with named labels, so jumps are written by name."""

    def __init__(self) -> None:
        self._bytes = bytearray()
        self._labels: dict[str, int] = {}
        self._fixups: list[tuple[int, str]] = []

    def emit(self, data: bytes) -> None:
        """Append encoded instructions."""

        self._bytes += data

    def label(self, name: str) -> None:
        """Mark the current position under ``name``."""

        if name in self._labels:
            raise ValueError(f"label {name!r} is already defined.")
        self._labels[name] = len(self._bytes)

    def jump(self, name: str) -> None:
        """Append ``jmp rel32`` to a label, wherever it ends up."""

        self._bytes.append(0xE9)
        self._relative(name)

    def jcc(self, condition: int, name: str) -> None:
        """Append ``jcc rel32`` to a label, wherever it ends up."""

        self._bytes += bytes((0x0F, condition))
        self._relative(name)

    def assemble(self) -> bytes:
        """Return the code with every jump resolved."""

        for position, name in self._fixups:
            target = self._labels.get(name)
            if target is None:
                raise ValueError(f"label {name!r} is never defined.")
            displacement = target - (position + 4)
            self._bytes[position : position + 4] = struct.pack(
                "<I", displacement & _UINT32_MAX
            )
        self._fixups.clear()
        return bytes(self._bytes)

    def _relative(self, name: str) -> None:
        """Record a rel32 fixup here and reserve the bytes it will occupy."""

        self._fixups.append((len(self._bytes), name))
        self._bytes += b"\x00\x00\x00\x00"


def _capture_return(code: _Code) -> None:
    """Store the callee's `eax` in the command's `value` word.

    Emitted immediately after every `call` in the CALL path: `eax` is the return
    register the source's `__cdecl` declarations use, and the next instruction that
    needs a register for anything else would lose it. A form whose target returns
    `void` leaves whatever the callee left there, which is why the host reads this
    word only when the target it called is one whose return value it wants — the same
    distinction the source's own prototype table carries.
    """

    code.emit(_mov_mem_r32(_ESI, COMMAND_OFFSET["value"], _EAX))


def _emit_call(
    code: _Code, call_table_address: int, module_base: int, module_size: int
) -> None:
    """Emit the CALL path: name a slot, bound the target, run the form.

    Registers on entry: ``ebx`` is the block, ``esi`` the command record, and
    ``edi`` the host's counter, which has to survive because the command is
    published with it afterwards. That leaves ``eax``, ``ecx``, ``edx`` and
    ``ebp`` for the work here.

    Nothing is called that is not inside the client's own module. The host
    resolved the address from the pattern catalog, so it is inside the module by
    construction; this refuses it anyway, because that is the rule the call path
    has to hold on its own rather than trust the host to have held it.
    """

    # The slot this command names, bounds-checked before it is used as an index.
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg0"]))
    code.emit(_cmp_r32_imm8(_EAX, DESCRIPTOR_DEPTH))
    code.jcc(_JAE, "bad_descriptor")
    code.emit(_shl_r32_imm8(_EAX, _DESCRIPTOR_SLOT_SHIFT))
    code.emit(_add_r32_imm32(_EAX, call_table_address))
    code.emit(_mov_r32_mem(_EBP, _EAX, DESCRIPTOR_OFFSET["target"]))
    code.emit(_mov_r32_mem(_EDX, _EAX, DESCRIPTOR_OFFSET["form"]))

    # A slot that names no function is not a call with a zero address; it is an
    # empty slot, and it is refused as one.
    code.emit(_cmp_r32_imm8(_EBP, 0))
    code.jcc(_JE, "no_target")

    code.emit(_cmp_r32_imm32(_EBP, module_base))
    code.jcc(_JB, "bad_target")
    code.emit(_mov_r32_imm32(_EAX, module_base))
    code.emit(_add_r32_imm32(_EAX, module_size))
    code.emit(_cmp_r32_r32(_EBP, _EAX))
    code.jcc(_JAE, "bad_target")

    # The form says how the command's words become the call's arguments. An
    # unknown form fails: it is never guessed at.
    code.emit(_cmp_r32_imm8(_EDX, CallForm.UI_MESSAGE))
    code.jcc(_JE, "ui_message")
    code.emit(_cmp_r32_imm8(_EDX, CallForm.U32_U32))
    code.jcc(_JE, "u32_u32")
    code.emit(_cmp_r32_imm8(_EDX, CallForm.NO_ARGS))
    code.jcc(_JE, "no_args")
    code.emit(_cmp_r32_imm8(_EDX, CallForm.U32))
    code.jcc(_JE, "u32")
    code.emit(_cmp_r32_imm8(_EDX, CallForm.U32_U32_U32))
    code.jcc(_JE, "u32_u32_u32")
    code.emit(_cmp_r32_imm8(_EDX, CallForm.FLOAT_PTR))
    code.jcc(_JE, "float_ptr")
    code.emit(_cmp_r32_imm8(_EDX, CallForm.U32_U32_U32_U32_U32))
    code.jcc(_JE, "u32_u32_u32_u32_u32")
    code.jump("unknown_form")

    # ``void __cdecl(void)``: nothing is pushed, so nothing is released.
    code.label("no_args")
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    # ``void __cdecl(uint32_t)``: the command's first word.
    code.label("u32")
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_push_r32(_EAX))
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_add_esp_imm8(4))
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    # ``void __cdecl(uint32_t, uint32_t, uint32_t)``: three words, pushed right
    # to left so the command's first word is the callee's first parameter.
    code.label("u32_u32_u32")
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg3"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg2"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_push_r32(_EAX))
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_add_esp_imm8(12))
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    # ``void __cdecl(float*)``: build the source's four-float array on our own
    # frame, then pass its address as the one argument.
    code.label("float_ptr")
    code.emit(_sub_esp_imm8(_FLOAT_ARRAY_BYTES))
    code.emit(_xor_r32_r32(_EAX, _EAX))
    code.emit(_mov_mem_r32(_ESP, 12, _EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_mov_mem_r32(_ESP, 0, _EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg2"]))
    code.emit(_mov_mem_r32(_ESP, 4, _EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg3"]))
    code.emit(_mov_mem_r32(_ESP, 8, _EAX))
    code.emit(_mov_r32_esp(_EAX))
    code.emit(_push_r32(_EAX))
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_add_esp_imm8(4))
    code.emit(_add_esp_imm8(_FLOAT_ARRAY_BYTES))
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    # ``void __cdecl(uint32_t, uint32_t)``: the command's first two words, pushed
    # right to left, and the caller releases them.
    code.label("u32_u32")
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg2"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_push_r32(_EAX))
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_add_esp_imm8(8))
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    # ``__cdecl(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t*)``: five words, pushed
    # right to left, which is the whole argument list ``OpenFileByFileId`` declares.
    code.label("u32_u32_u32_u32_u32")
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg5"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg4"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg3"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg2"]))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_push_r32(_EAX))
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_add_esp_imm8(20))
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    code.label("ui_message")
    # A zeroed sixteen-word payload in our own frame, with the command's words
    # packed into the front. Zeroing the whole thing is the contract, not a
    # tidy-up: the client reads the fields the command did not set.
    code.emit(_sub_esp_imm8(_UI_PAYLOAD_BYTES))
    code.emit(_xor_r32_r32(_EAX, _EAX))
    for offset in range(_UI_PAYLOAD_WORDS * 4, _UI_PAYLOAD_BYTES, 4):
        code.emit(_mov_mem_r32(_ESP, offset, _EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg2"]))
    code.emit(_mov_mem_r32(_ESP, 0, _EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg3"]))
    code.emit(_mov_mem_r32(_ESP, 4, _EAX))

    # ``void __cdecl(message_id, wparam, lparam)``: arguments right to left, and
    # the caller releases them, which is what this convention requires.
    code.emit(_push_imm8(0))
    code.emit(_mov_r32_esp(_EAX))
    code.emit(_add_r32_imm32(_EAX, 4))
    code.emit(_push_r32(_EAX))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_push_r32(_EAX))
    code.emit(_call_r32(_EBP))
    _capture_return(code)
    code.emit(_add_esp_imm8(12))
    code.emit(_add_esp_imm8(_UI_PAYLOAD_BYTES))

    # The function returns void, so a completed call carries no value of its own.
    # A zero here means "it ran", not "it returned zero".
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    code.label("bad_descriptor")
    code.emit(_mov_r32_imm32(_EDX, RESULT_BAD_DESCRIPTOR))
    code.emit(_mov_r32_imm32(_ECX, CommandState.FAILED))
    code.jump("store")

    code.label("no_target")
    code.emit(_mov_r32_imm32(_EDX, RESULT_NO_TARGET))
    code.emit(_mov_r32_imm32(_ECX, CommandState.FAILED))
    code.jump("store")

    code.label("bad_target")
    code.emit(_mov_r32_imm32(_EDX, RESULT_BAD_TARGET))
    code.emit(_mov_r32_imm32(_ECX, CommandState.FAILED))
    code.jump("store")

    code.label("unknown_form")
    code.emit(_mov_r32_imm32(_EDX, RESULT_UNKNOWN_FORM))
    code.emit(_mov_r32_imm32(_ECX, CommandState.FAILED))
    code.jump("store")


#: How many words of a watched message's ``wparam`` an event carries. Four is
#: ``ChangeTargetUIMsg``'s manual, auto and current target fields and one spare.
_OBSERVED_WORDS = 4

#: Where the hooked function's arguments sit once ``pushad`` has run: the return
#: address and its 32 bytes are on top of them.
_OBSERVER_BLOCK_OFFSET = 36

#: The epilogue of the observer: it is ``__stdcall`` with three arguments, so it
#: pops twelve bytes rather than the dispatcher's four.
_OBSERVER_EPILOGUE = bytes((0xC2, 0x0C, 0x00))


def build_observer(
    watch_address: int = 0, watch_depth: int = WATCH_DEPTH
) -> bytes:
    """Return the observer: what runs when a watched client function is called.

    The dispatcher answers commands this project publishes. The observer is the
    other direction: it is placed on a client function, and when that function is
    called with a message the host asked about, the call is recorded as an event.

    Its three arguments are ``(block, message_id, wparam)``, pushed by the stub
    from the hooked function's own frame. Reading the client's ``wparam`` is
    guarded on it being non-null, which is the check Native's own handler makes
    before dereferencing a packet pointer (``agent.cpp:145-151``).

    ``watch_address`` is a list of watch entries in the client — each a message id and the byte
    offset of the ``wchar_t*`` field that message carries — and ``watch_depth`` how many; both are
    known when this is built, so they are emitted as data. Without a list the observer only
    validates and returns.

    **It copies that string, and it has to.** The observer runs where the source's own callback
    runs — after the client's send returns (``ui_methods.cpp:1390-1404``) — and the string a
    dialog announces is the client's own only inside that call: read from outside it, the
    announced pointer is a buffer the client reuses (``docs/RESEARCH.md``, 2026-09-25). So the
    copy is taken here, word by word, into the event record the host reads
    (``EVENT_TEXT_OFFSET``) — the same shape as the decoder stub copying the text the client
    hands it. It is **bounded** where the source's ``DupWideStringSafe`` is wrapped in a
    ``__try`` (``dialog.cpp:237-252``): emitted code here has no such frame, so a string with no
    terminator inside ``EVENT_TEXT_WORDS`` is reported as unterminated rather than read on.
    """

    code = _Code()

    code.emit(_PUSHAD)
    # The hooked function's first three arguments, past our own frame: pushad
    # covers the return address and its 32 bytes.
    code.emit(_mov_r32_mem(_EBX, _ESP, _OBSERVER_BLOCK_OFFSET))
    code.emit(_TEST_EBX_EBX)
    code.jcc(_JE, "observer_return")

    for field, expected in _HEADER_CHECKS:
        code.emit(_cmp_mem_imm32(_EBX, HEADER_OFFSET[field], expected))
        code.jcc(_JNE, "observer_return")

    if not watch_address:
        code.jump("observer_return")
    else:
        # ebx block, esi message id, edx wparam, ebp watch entry, edi remaining.
        code.emit(_mov_r32_mem(_ESI, _ESP, _OBSERVER_BLOCK_OFFSET + 4))
        code.emit(_mov_r32_mem(_EDX, _ESP, _OBSERVER_BLOCK_OFFSET + 8))
        code.emit(_TEST_EDX_EDX)
        code.jcc(_JE, "observer_return")
        code.emit(_mov_r32_imm32(_EBP, watch_address))
        code.emit(_mov_r32_imm32(_EDI, watch_depth))

        code.label("watch_next")
        code.emit(_cmp_mem_r32(_EBP, 0, _ESI))
        code.jcc(_JE, "watch_found")
        code.emit(_add_r32_imm32(_EBP, WATCH_SIZE))
        code.emit(bytes((0x4F,)))  # dec edi
        code.jcc(_JNE, "watch_next")
        code.jump("observer_return")

        code.label("watch_found")
        # The event region can be full, in which case the event is dropped: the
        # host is told nothing rather than the client being asked to wait.
        code.emit(_mov_r32_mem(_EAX, _EBX, HEADER_OFFSET["event_written"]))
        code.emit(_mov_r32_mem(_ECX, _EBX, HEADER_OFFSET["event_taken"]))
        code.emit(_sub_r32_r32(_EAX, _ECX))
        code.emit(_cmp_r32_imm8(_EAX, EVENT_DEPTH))
        code.jcc(_JAE, "observer_return")

        code.emit(_mov_r32_mem(_EAX, _EBX, HEADER_OFFSET["event_written"]))
        code.emit(_mov_r32_r32(_ECX, _EAX))
        code.emit(_and_r32_imm8(_ECX, _EVENT_SLOT_MASK))
        code.emit(_shl_r32_imm8(_ECX, _EVENT_SLOT_SHIFT))
        code.emit(_lea_r32_mem(_EDI, _EBX, EVENT_REGION_OFFSET, _ECX))

        code.emit(_mov_mem_imm32(_EDI, EVENT_OFFSET["kind"], EventKind.UI_MESSAGE))
        code.emit(_mov_mem_r32(_EDI, EVENT_OFFSET["sequence"], _ESI))
        for word in range(_OBSERVED_WORDS):
            code.emit(_mov_r32_mem(_ECX, _EDX, word * 4))
            code.emit(_mov_mem_r32(_EDI, EVENT_OFFSET["arg0"] + word * 4, _ECX))
        code.emit(_mov_mem_imm32(_EDI, EVENT_OFFSET["tick"], 0))
        code.emit(_mov_mem_imm32(_EDI, EVENT_OFFSET["reserved"], 0))

        # The copy of the string this message named, taken here because here is the only moment
        # it is the client's own (see the docstring). ebp is this watch entry, so its second word
        # is where the packet's string pointer sits; edx is still the packet pointer, and esi
        # (the message id, already stored) becomes the string's own pointer. eax holds the event
        # counter this path increments at the end, so it is put back afterwards.
        code.emit(_mov_mem_imm32(_EDI, EVENT_TEXT_STATE_OFFSET, EventTextState.ABSENT))
        code.emit(_mov_mem_imm32(_EDI, EVENT_TEXT_LENGTH_OFFSET, 0))
        code.emit(_PUSH_EAX)
        code.emit(_mov_r32_mem(_EAX, _EBP, WATCH_STRING_OFFSET))
        code.emit(_TEST_EAX_EAX)
        code.jcc(_JE, "copy_done")
        code.emit(_TEST_EDX_EDX)
        code.jcc(_JE, "copy_done")
        code.emit(_mov_r32_mem(_ESI, _EDX, 0, _EAX))
        code.emit(_TEST_ESI_ESI)
        code.jcc(_JE, "copy_done")

        code.emit(_xor_r32_r32(_ECX, _ECX))
        code.label("copy_next")
        code.emit(_movzx_r32_word(_EAX, _ESI, _ECX, 0, 2))
        code.emit(_mov_word_mem_r16(_EDI, EVENT_TEXT_OFFSET, _EAX, _ECX, 2))
        code.emit(_INC_ECX)
        code.emit(_TEST_EAX_EAX)
        code.jcc(_JE, "copy_terminated")
        code.emit(_cmp_r32_imm32(_ECX, EVENT_TEXT_WORDS))
        code.jcc(_JB, "copy_next")
        # Every unit the record can hold and no terminator: the string is reported rather than
        # truncated, because half of one decodes to the wrong text.
        code.emit(_mov_mem_r32(_EDI, EVENT_TEXT_LENGTH_OFFSET, _ECX))
        code.emit(
            _mov_mem_imm32(_EDI, EVENT_TEXT_STATE_OFFSET, EventTextState.UNTERMINATED)
        )
        code.jump("copy_done")

        code.label("copy_terminated")
        # The terminator is part of the copy, which is what the source's ``wcslen + 1`` gives it.
        code.emit(_mov_mem_r32(_EDI, EVENT_TEXT_LENGTH_OFFSET, _ECX))
        code.emit(_mov_mem_imm32(_EDI, EVENT_TEXT_STATE_OFFSET, EventTextState.COPIED))
        code.label("copy_done")
        code.emit(_POP_EAX)

        code.emit(bytes((0x40,)))  # inc eax
        code.emit(_mov_mem_r32(_EBX, HEADER_OFFSET["event_written"], _EAX))

    code.label("observer_return")
    code.emit(_POPAD)
    code.emit(_OBSERVER_EPILOGUE)

    return code.assemble()


def observer_size() -> int:
    """Return the observer's length, which does not depend on its data."""

    return len(build_observer(0x10000000))


#: How far the decoder stub will scan the client's string looking for its terminator, in wide
#: characters. Native reads the string with ``wcslen`` inside an SEH frame
#: (``DupWideStringSafe``, ``dialog.cpp:237-252``); this side has no such frame, so the scan is
#: bounded instead. The bound is far past any text a dialog holds: a string that has no
#: terminator inside it is reported as a failed decode rather than scanned further.
DECODE_SCAN_LIMIT = 65536

#: The epilogue of the decoder stub. ``DecodeStr_Callback`` is ``void(__cdecl*)(void*, const
#: wchar_t*)`` (``ui.h:299``), and this stub is called by the **client**, so the caller is the
#: one that cleans the two arguments off the stack: a plain ``ret``. It is deliberately not the
#: observer's ``ret 8`` — the observer is ``__stdcall`` because this project's own forwarder
#: calls it — and getting this wrong takes eight bytes off the client's stack on every decode
#: instead of returning, which is a crash and not an error.
_DECODER_EPILOGUE = bytes((0xC3,))


def build_decoder_stub() -> bytes:
    """Return the decoder stub: what the client calls when it has decoded a string.

    This is the port of the callback native passes to ``AsyncDecodeStr`` — its
    ``DecodeStr_Callback`` is ``void(__cdecl*)(void* param, const wchar_t* s)``
    (``ui.h:299``) — with one difference that the boundary forces: native's callback *is* its
    own code, so it can read the string it is handed, and this one cannot. It copies the text
    into the decode slot the host named in ``param`` and publishes the length with it, which is
    what lets a host outside the client answer with the same text.

    Registers are saved whole, and the stub touches nothing but its own slot, so it is safe on
    whatever thread the client decodes on — which is not something this side may assume
    (native's callback runs wherever the client runs it, and its own dialog code takes a mutex
    for exactly that reason, ``dialog.cpp:1017``).

    The state word is written **last**, and the length before it, so the host's read of the
    state is what tells it the copy is complete.
    """

    code = _Code()

    code.emit(_PUSHAD)
    # The two arguments, past our own frame: pushad covers the return address and its 32 bytes.
    code.emit(_mov_r32_mem(_ESI, _ESP, _OBSERVER_BLOCK_OFFSET))
    code.emit(_mov_r32_mem(_EDI, _ESP, _OBSERVER_BLOCK_OFFSET + 4))
    code.emit(_TEST_EDI_EDI)
    code.jcc(_JE, "decoder_empty_string")

    # esi slot, edi the client's string, ecx how far in we are, eax one code unit.
    code.emit(_xor_r32_r32(_ECX, _ECX))

    code.label("decoder_scan")
    code.emit(_cmp_r32_imm32(_ECX, DECODE_SCAN_LIMIT))
    code.jcc(_JAE, "decoder_no_terminator")
    code.emit(_movzx_r32_word(_EAX, _EDI, _ECX, 0, 2))
    code.emit(_TEST_EAX_EAX)
    code.jcc(_JE, "decoder_found")
    code.emit(_cmp_r32_imm32(_ECX, DECODE_CAPACITY))
    code.jcc(_JAE, "decoder_skip_store")
    code.emit(
        _mov_word_mem_r16(
            _ESI, DECODE_SLOT_OUTPUT_OFFSET, _EAX, _ECX, 2
        )
    )
    code.label("decoder_skip_store")
    code.emit(_INC_ECX)
    code.jump("decoder_scan")

    # The string ended inside the slot's room: the text is whole.
    code.label("decoder_found")
    code.emit(_mov_mem_r32(_ESI, DECODE_SLOT_LENGTH_OFFSET, _ECX))
    code.emit(_mov_mem_imm32(_ESI, DECODE_SLOT_STATE_OFFSET, DecodeState.DONE))
    code.jump("decoder_return")

    # A null string is the empty one the source's own decoder calls back with when it cannot
    # make the decode (``ui_methods.cpp:2583-2586``).
    code.label("decoder_empty_string")
    code.emit(_mov_mem_imm32(_ESI, DECODE_SLOT_LENGTH_OFFSET, 0))
    code.emit(_mov_mem_imm32(_ESI, DECODE_SLOT_STATE_OFFSET, DecodeState.DONE))
    code.jump("decoder_return")

    # No terminator inside the bound: reported, not guessed at. See ``DECODE_SCAN_LIMIT``.
    code.label("decoder_no_terminator")
    code.emit(_mov_mem_imm32(_ESI, DECODE_SLOT_LENGTH_OFFSET, 0))
    code.emit(_mov_mem_imm32(_ESI, DECODE_SLOT_STATE_OFFSET, DecodeState.FAILED))

    code.label("decoder_return")
    code.emit(_POPAD)
    code.emit(_DECODER_EPILOGUE)

    return code.assemble()


def decoder_stub_size() -> int:
    """Return the decoder stub's length, which does not depend on anything."""

    return len(build_decoder_stub())

def build_dispatcher(
    call_table_address: int = 0,
    module_base: int = 0,
    module_size: int = 0,
) -> bytes:
    """Return the dispatcher: what the stub calls on the game thread.

    ``call_table_address`` is where the call table lives inside the client, and
    ``module_base``/``module_size`` bound what may be called. Both are known when
    the dispatcher is built, so they are emitted as data rather than looked up.

    Without a table and bounds the dispatcher still runs every operation it can
    compute itself. A ``CALL`` is refused, because there is nothing it is allowed
    to call — that refusal is emitted, not discovered at run time.
    """

    code = _Code()

    # The argument is read first, then every register is saved, so what this code
    # clobbers is its own business and not the client's.
    code.emit(_PUSHAD)
    code.emit(_MOV_EBX_ARG)
    code.emit(_TEST_EBX_EBX)
    code.jcc(_JE, "return")

    # A block that fails any of these is not ours. It is left exactly as found:
    # no counter moves, no record is touched, nothing is reported.
    for field, expected in _HEADER_CHECKS:
        code.emit(_cmp_mem_imm32(_EBX, HEADER_OFFSET[field], expected))
        code.jcc(_JNE, "return")

    # The payload owns ``command_taken`` and only reads the host's
    # ``command_written``. One call takes one command: this runs on somebody
    # else's thread, inside somebody else's function, so the work per call is
    # bounded on purpose.
    code.emit(_mov_r32_mem(_EAX, _EBX, HEADER_OFFSET["command_written"]))
    code.emit(_mov_r32_mem(_EDI, _EBX, HEADER_OFFSET["command_taken"]))
    code.emit(_cmp_r32_r32(_EAX, _EDI))
    code.jcc(_JE, "return")

    code.emit(_mov_r32_r32(_ECX, _EDI))
    code.emit(_and_r32_imm8(_ECX, _COMMAND_SLOT_MASK))
    code.emit(_shl_r32_imm8(_ECX, _COMMAND_SLOT_SHIFT))
    code.emit(_lea_r32_mem(_ESI, _EBX, COMMAND_REGION_OFFSET, _ECX))

    # Only a record the host marked READY is ours to take. Anything else in that
    # slot is not a command waiting for us.
    code.emit(_cmp_mem_imm8(_ESI, COMMAND_OFFSET["state"], CommandState.READY))
    code.jcc(_JNE, "return")
    code.emit(_mov_mem_imm32(_ESI, COMMAND_OFFSET["state"], CommandState.RUNNING))

    # An operation this payload does not know fails. Each known one replaces both
    # the state and the result below.
    code.emit(_mov_r32_imm32(_EDX, RESULT_UNKNOWN_OPERATION))
    code.emit(_mov_r32_imm32(_ECX, CommandState.FAILED))
    code.emit(_mov_r32_mem(_EAX, _ESI, COMMAND_OFFSET["operation"]))
    for operation, label in _OPERATIONS:
        code.emit(_cmp_r32_imm8(_EAX, operation))
        code.jcc(_JE, label)
    code.jump("store")

    code.label("call")
    if not call_table_address or not module_base or not module_size:
        code.emit(_mov_r32_imm32(_EDX, RESULT_NO_TARGET))
        code.emit(_mov_r32_imm32(_ECX, CommandState.FAILED))
        code.jump("store")
    else:
        _emit_call(code, call_table_address, module_base, module_size)

    code.label("nop")
    code.emit(_xor_r32_r32(_EDX, _EDX))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    code.label("ping")
    code.emit(_mov_r32_imm32(_EDX, PING_RESULT))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    code.label("add")
    code.emit(_mov_r32_mem(_EDX, _ESI, COMMAND_OFFSET["arg0"]))
    code.emit(_add_r32_mem(_EDX, _ESI, COMMAND_OFFSET["arg1"]))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))
    code.jump("store")

    code.label("echo")
    code.emit(_mov_r32_mem(_EDX, _ESI, COMMAND_OFFSET["arg0"]))
    code.emit(_mov_r32_imm32(_ECX, CommandState.DONE))

    # The result and the terminal state land before the counter moves: a host
    # that sees a record taken is entitled to read it as a finished one.
    code.label("store")
    code.emit(_mov_mem_r32(_ESI, COMMAND_OFFSET["result"], _EDX))
    code.emit(_mov_mem_r32(_ESI, COMMAND_OFFSET["state"], _ECX))
    code.emit(_INC_EDI)
    code.emit(_mov_mem_r32(_EBX, HEADER_OFFSET["command_taken"], _EDI))

    # The completion event is a notification, not the answer: the command record
    # above already carries the state and the result. So when the event region is
    # full the event is dropped and the command still completes, and a host that
    # never reads events cannot stall the payload.
    code.emit(_mov_r32_mem(_EAX, _EBX, HEADER_OFFSET["event_written"]))
    code.emit(_mov_r32_mem(_ECX, _EBX, HEADER_OFFSET["event_taken"]))
    code.emit(_mov_r32_r32(_EDX, _EAX))
    code.emit(_sub_r32_r32(_EDX, _ECX))
    code.emit(_cmp_r32_imm8(_EDX, EVENT_DEPTH))
    code.jcc(_JAE, "return")

    code.emit(_mov_r32_r32(_EDX, _EAX))
    code.emit(_and_r32_imm8(_EDX, _EVENT_SLOT_MASK))
    code.emit(_shl_r32_imm8(_EDX, _EVENT_SLOT_SHIFT))
    code.emit(_lea_r32_mem(_EDI, _EBX, EVENT_REGION_OFFSET, _EDX))

    code.emit(_mov_mem_imm32(_EDI, EVENT_OFFSET["kind"], EventKind.COMMAND_COMPLETE))
    for field, source in _EVENT_SOURCES:
        code.emit(_mov_r32_mem(_EDX, _ESI, COMMAND_OFFSET[source]))
        code.emit(_mov_mem_r32(_EDI, EVENT_OFFSET[field], _EDX))
    for field in _EVENT_ZEROES:
        code.emit(_mov_mem_imm32(_EDI, EVENT_OFFSET[field], 0))

    # Publish the event by advancing the counter last, so a host reading below it
    # never sees a half-written record.
    code.emit(_INC_EAX)
    code.emit(_mov_mem_r32(_EBX, HEADER_OFFSET["event_written"], _EAX))

    code.label("return")
    code.emit(_POPAD)
    code.emit(_EPILOGUE)

    return code.assemble()


def dispatcher_size() -> int:
    """Return the dispatcher's length, so it can be allocated before it is built."""

    return len(build_dispatcher())
