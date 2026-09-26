"""The GW.dat archive read, ported from Native's ``PyDatReader``.

**Source.** ``src/GW/textures/dat_reader_bindings.cpp`` (46 lines) is the module Reforged's
own Python calls — ``PyDatReader.read_file_by_hash`` and ``PyDatReader.read_file_by_id`` — and
this file ports those two functions and the read path behind them:

```text
ReadDatFile(file_hash)                     gw_dat_reader.cpp:1441-1461
  FileHashToFileId(file_hash)              arenanet_file_parser.cpp:17-23   pure
  OpenFileByFileId(0, id, stream, 1, 0)    gw_dat_reader.h:42               optional first try
  FileHashToRecObj(file_hash, 1, 0)        gw_dat_reader.h:43               the fallback
  ReadDatRecord(rec)                       gw_dat_reader.cpp:135-158
    ReadFileBuffer(rec, &size)             → the bytes and their length
    the bounded copy out
    FreeFileBuffer(rec, bytes)             every path that got a buffer frees it
    CloseRecObj(rec)                       every path closes the record
```

**Where each piece runs.** The five calls are the client's own functions, so each one is
issued on the client's own thread through ``py4gw/game_thread`` — the port of what the
injected runtime gets for free. The pointer arguments are the reason for the block's data
region: the source keeps its ``int size`` and its hash string in its own stack frame and hands
over their addresses, and this process has no frame inside the client, so both live in the
block. The hash string is written there as UTF-16 and the size word is zeroed before the call,
which is what the source's ``int size = 0;`` does.

**What is not here.** ``GWDatReader`` is also a texture manager: image decode, a D3D9 texture
cache, dye blending, upload to a device (``gw_dat_reader.cpp:160-1439``). None of that is
ported, because nothing in this project draws inside the client — it is target-side work with
its own prerequisites, and ``docs/TARGET_SIDE_WORK.md`` records it. What is ported is the part
the archive read needs, which is what the source's own Python binding exposes.

**One bound the source does not have.** ``ReadDatFile`` copies whatever length the client
reports; this port reads it with ``ReadProcessMemory``, so the length is checked against
``MAX_DAT_FILE_BYTES`` first. A length past it is treated as the source treats a failed copy —
freed, closed, and answered with nothing — rather than being handed to an allocation.
"""

from __future__ import annotations

from typing import Optional

from .game_thread.shared_block import CallForm

#: The catalog names every call here resolves. They are ``gw_dat_reader_patterns.cpp``'s
#: eight resolvers' names, whose patterns live in ``offsets/gw_dat_reader.json``.
FILE_HASH_TO_REC_OBJ = "gw_dat_reader.file_hash_to_rec_obj_func"
OPEN_FILE_BY_FILE_ID = "gw_dat_reader.open_file_by_file_id_func"
READ_FILE_BUFFER = "gw_dat_reader.read_file_buffer_func"
FREE_FILE_BUFFER = "gw_dat_reader.free_file_buffer_func"
CLOSE_REC_OBJ = "gw_dat_reader.close_rec_obj_func"

#: ``ReadDatFile``'s own guard: these four have to be there, and ``OpenFileByFileId`` is the
#: one the source calls optional (``gw_dat_reader.cpp:1442-1455`` and the comment at ``1487``).
REQUIRED_FUNCTIONS = (
    FILE_HASH_TO_REC_OBJ,
    READ_FILE_BUFFER,
    FREE_FILE_BUFFER,
    CLOSE_REC_OBJ,
)

#: Where the two pointer arguments live in the block's data region. The hash is four UTF-16
#: code units — the two the encoding produces and a terminator — and the size word follows it.
_HASH_OFFSET = 0
_HASH_CODE_UNITS = 4
_SIZE_OFFSET = _HASH_OFFSET + _HASH_CODE_UNITS * 2

#: The most one archive entry may report itself to be. A string-table chunk is a few hundred
#: kilobytes at most, and generous headroom costs nothing: the check exists so a wrong length
#: is refused before it becomes an allocation, which is the one thing the source's in-process
#: ``memcpy`` could not need.
MAX_DAT_FILE_BYTES = 64 * 1024 * 1024

#: The stream the hash binding reads (``dat_reader_bindings.cpp:14``). The member's own
#: declaration defaults to ``0``; the binding that Reforged's Python calls passes ``1``, and
#: the binding is the surface being ported.
READ_STREAM_ID = 1

_UINT32_MAX = 0xFFFFFFFF

#: ``EnsureHooks``'s idempotence, keyed by the client it was answered for: the sources resolve
#: once per process, and a controller outlives one connection. The optional function's answer
#: is kept with the required ones because the source's own globals are: a pointer ``EnsureHooks``
#: set is never cleared, so every later call reads the same answer.
_hooks_pid = 0
_hooks_ready = False
_open_ready = False


def file_id_to_file_hash(file_id: int) -> str:
    """``ArenaNetFileParser::FileIdToFileHash`` (``arenanet_file_parser.cpp:11-15``).

    Two code units above ``0xFF``, which is why a file hash is a string and not text: the
    low one carries ``(file_id - 1) % 0xFF00`` and the high one ``(file_id - 1) / 0xFF00``.
    The source stores them in a ``wchar_t``, so the high unit truncates to sixteen bits, and
    this does the same.
    """

    if not 1 <= file_id <= _UINT32_MAX:
        raise ValueError("file_id must be a nonzero 32-bit value")

    low = ((file_id - 1) % 0xFF00) + 0x100
    high = (((file_id - 1) // 0xFF00) + 0x100) & 0xFFFF
    return chr(low) + chr(high)


def file_hash_to_file_id(file_hash: str) -> int:
    """``ArenaNetFileParser::FileHashToFileId`` (``arenanet_file_parser.cpp:17-23``).

    ``0`` for anything that is not a hash, which is the source's own answer. The C reads two
    or three characters and then the terminator; a Python string carries no terminator, so
    "the character after it is the terminator" is "the string ends here". The arithmetic
    wraps in ``uint32`` and is kept that way, because that is what makes it the inverse of
    :func:`file_id_to_file_hash` for a low id.
    """

    if len(file_hash) < 2:
        return 0

    first = ord(file_hash[0])
    second = ord(file_hash[1])
    if not (0xFF < first and 0xFF < second):
        return 0

    if len(file_hash) == 2:
        pass
    elif len(file_hash) == 3 and 0xFF < ord(file_hash[2]):
        pass
    else:
        return 0

    return ((first - 0xFF00FF) + second * 0xFF00) & _UINT32_MAX


def ensure_hooks(client) -> bool:
    """``GWDatReader::EnsureHooks`` (``gw_dat_reader.cpp:1472-1497``): resolved, once.

    The source resolves its function pointers once per process and answers from the flags
    afterwards; a resolution that failed leaves the pointer null and every later call answers
    "not there" rather than retrying. This is the same answer, from this project's resolver:
    the names are looked up once per client and the result is remembered — including the
    optional ``OpenFileByFileId``, because the source's own global for it is set once and never
    cleared.
    """

    global _hooks_pid, _hooks_ready, _open_ready

    if _hooks_pid == client.pid:
        return _hooks_ready

    _hooks_pid = client.pid
    _hooks_ready = all(client.resolves(name) for name in REQUIRED_FUNCTIONS)
    _open_ready = client.resolves(OPEN_FILE_BY_FILE_ID)
    return _hooks_ready


def read_file_by_hash(file_hash: str) -> Optional[bytes]:
    """``PyDatReader.read_file_by_hash``: a decompressed entry, or ``None``.

    The binding takes no stream id and passes ``1`` (``dat_reader_bindings.cpp:14``), which is
    why that is this module's own constant rather than a parameter here.
    """

    from .client import require_client

    client = require_client()
    if not file_hash or not file_hash[0]:
        return None
    if not ensure_hooks(client):
        return None

    file_id = file_hash_to_file_id(file_hash)
    rec = 0
    has_subtype = len(file_hash) > 2 and file_hash[2] != "\0"
    if file_id and not has_subtype and _open_ready:
        rec = _open_file_by_file_id(client, file_id, READ_STREAM_ID)
    if not rec:
        rec = _file_hash_to_rec_obj(client, file_hash)
    if not rec:
        return None

    return _read_dat_record(client, rec)


def read_file_by_id(file_id: int, stream_id: int = 1) -> Optional[bytes]:
    """``PyDatReader.read_file_by_id``: the same read, addressed by sequential id."""

    from .client import require_client

    client = require_client()
    if not file_id:
        return None
    if not ensure_hooks(client) or not _open_ready:
        return None

    return _read_dat_record(client, _open_file_by_file_id(client, file_id, stream_id))


def _open_file_by_file_id(client, file_id: int, stream_id: int) -> int:
    """``OpenFileByFileId(archive, file_id, stream_id, flags, error_out)``.

    ``archive`` is the client's own default archive (``0``), the flag is the ``1`` the source
    passes, and ``error_out`` is null there as well — so the fifth word is a zero, not a
    pointer.
    """

    return int(
        client.call_function(
            OPEN_FILE_BY_FILE_ID,
            CallForm.U32_U32_U32_U32_U32,
            0,
            file_id,
            stream_id,
            1,
            0,
        ).value
    )


def _file_hash_to_rec_obj(client, file_hash: str) -> int:
    """``FileHashToRecObj(file_hash, 1, 0)``: the hash string goes into the block first."""

    address = _write_hash(client, file_hash)
    return int(
        client.call_function(
            FILE_HASH_TO_REC_OBJ, CallForm.U32_U32_U32, address, 1, 0
        ).value
    )


def _write_hash(client, file_hash: str) -> int:
    """Place the hash string in the client and return its address.

    ``c_str()`` is what the source passes, so the client reads a NUL-terminated string of the
    code units above; a hash longer than the region holds is refused rather than truncated,
    because a truncated hash resolves to a different file.
    """

    code_units = len(file_hash) + 1
    if code_units > _HASH_CODE_UNITS:
        raise ValueError(
            f"a file hash is at most {_HASH_CODE_UNITS - 1} code units; "
            f"{len(file_hash)} were given."
        )
    return client.bridge.write_data(
        _HASH_OFFSET, file_hash.encode("utf-16-le") + b"\x00\x00"
    )


def _read_dat_record(client, rec: int) -> Optional[bytes]:
    """``ReadDatRecord`` (``gw_dat_reader.cpp:135-158``): the bytes behind one record.

    The order is the source's, including which paths free the buffer: a call that reported no
    buffer and a length that is not positive close the record and nothing else, a copy that
    failed frees the buffer *and* closes, and the path that worked does both before it
    answers. Every one of them leaves the client with nothing of ours outstanding.

    ``bytes_out->resize(size)`` is this port's bounded read, and the copy failure the source
    guards with ``__try`` is the reader's own ``OSError`` here.
    """

    if not rec:
        return None

    # ``int size = 0;`` before the call: the word is an output, and a client that writes
    # nothing must leave it as the source's own stack variable was left.
    bridge = client.bridge
    bridge.write_data(_SIZE_OFFSET, bytes(4))
    buffer = int(
        client.call_function(
            READ_FILE_BUFFER, CallForm.U32_U32, rec, bridge.data_address(_SIZE_OFFSET, 4)
        ).value
    )
    size = int.from_bytes(bridge.read_data(_SIZE_OFFSET, 4), "little")

    if not buffer or size <= 0:
        _close_rec_obj(client, rec)
        return None

    if size > MAX_DAT_FILE_BYTES:
        _free_file_buffer(client, rec, buffer)
        _close_rec_obj(client, rec)
        return None

    try:
        data = client.access.read(buffer, size)
    except OSError:
        _free_file_buffer(client, rec, buffer)
        _close_rec_obj(client, rec)
        return None

    _free_file_buffer(client, rec, buffer)
    _close_rec_obj(client, rec)
    return data


def _free_file_buffer(client, rec: int, buffer: int) -> None:
    """``FreeFileBuffer(rec, bytes)``: give the client's buffer back."""

    client.call_function(FREE_FILE_BUFFER, CallForm.U32_U32, rec, buffer)


def _close_rec_obj(client, rec: int) -> None:
    """``CloseRecObj(rec)``: the record object is the client's, and every path closes it."""

    client.call_function(CLOSE_REC_OBJ, CallForm.U32, rec)
