"""The client's asynchronous string decoder, as the sources call it.

``GW::ui::AsyncDecodeStr`` (``ui_methods.cpp:2582-2607``) is how every piece of encoded text in
the game becomes readable, and dialog text is what this project needed it for:

```cpp
void AsyncDecodeStr(const wchar_t* enc_str, DecodeStr_Callback callback, void* callback_param,
                    GW::Constants::Language language_id) {
    if (!(g_validate_async_decode_str_func && enc_str && callback)) {
        if (callback) callback(callback_param, L"");
        return;
    }
    if (!IsValidEncStr(enc_str)) { callback(callback_param, L"!!!"); return; }
    Context::TextParser* text_parser = Context::GetTextParser();
    if (!text_parser) { callback(callback_param, L""); return; }
    ...
    g_validate_async_decode_str_func(enc_str, callback, callback_param);
}
```

and ``dialog.cpp``'s own wrapper around it, which is the shape its callers use:

```cpp
bool SafeAsyncDecodeStr(const wchar_t* encoded, GW::ui::DecodeStr_Callback callback,
                        void* callback_param) {
    if (!encoded || !callback) return false;
    __try { GW::ui::AsyncDecodeStr(encoded, callback, callback_param); return true; }
    __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}
```

This module is that pair, ported to a controller that runs outside the client.

**What changes, and only this.** The callback native passes is its own function, called inside
the client, so it reads the decoded text where it lies. Nothing of this project's runs in that
address space, so the callback is the emitted decoder stub (``payload.build_decoder_stub``):
the client calls it with the text, it copies the text into the decode slot this side named, and
the host reads it from there. The three refusals above are made here, before any call, and the
answer each of them gives is written into that same slot — the callback's answer, arriving the
way it would have arrived.
"""

from __future__ import annotations

from ..game_thread.shared_block import CallForm, DecodeState

#: The catalog name of the function native reaches through ``g_validate_async_decode_str_func``
#: (``ui_patterns.cpp:41``): ``void __cdecl(const wchar_t* value, DecodeStr_Callback callback,
#: void* wparam)`` — three words, so the call vocabulary already expresses it.
ASYNC_DECODE_STR = "ui.validate_async_decode_str_func"

#: What the source answers a string that is not an encoded one with (``ui_methods.cpp:2591``).
NOT_ENCODED = "!!!"


def begin_string_decode(encoded: bytes) -> int:
    """Place one encoded string for the client's decoder, and return the slot holding it.

    This is the port's ``param`` — what native allocates before it calls the decoder, fills with
    the request's fields, and passes to ``AsyncDecodeStr`` (`dialog.cpp:857-887` for the body,
    ``1239`` for the catalog). It is separate from the call **because the source's callers do it
    separately**: they prepare the request first, so a completion can never arrive before the
    record of what it belongs to exists. A caller here records its own request against this slot
    and only then calls :func:`async_decode_str`.
    """

    from ..client import require_client

    return require_client().bridge.begin_decode(encoded)


def async_decode_str(encoded: bytes, slot: int) -> bool:
    """Hand a placed string to the client's decoder: ``AsyncDecodeStr``, as its callers use it.

    ``encoded`` is the wide string's bytes, terminator included, exactly as it stands in the
    client, and ``slot`` is the ``param`` :func:`begin_string_decode` returned.

    **``False`` means the decode was not started**, which is ``SafeAsyncDecodeStr`` answering
    false — the same answer its ``__except`` gives when the call itself faults. Its callers do
    what native does with a false: release the request and take the branch they already had. The
    slot is given back, so nothing is left in flight.

    Three of the wrapper's own refusals answer the callback instead of calling the client
    (``ui_methods.cpp:2583-2598``): no decoder, not an encoded string, no text parser. Each of
    them *completes the slot*, which is that callback's answer arriving the way it arrives for
    native — immediately, in the same call — and the caller's request must already be recorded
    for it, which is why the slot is the caller's to hold first.

    A decode that *is* started finishes later: the client calls the stub, the stub fills the
    slot, and the completion arrives as a ``STRING_DECODED`` event on the listener.
    """

    from ..client import require_client
    from .encoded_str import is_valid_enc_str

    client = require_client()
    bridge = client.bridge

    try:
        if not encoded or not bridge.decoder_address:
            # ``ui_methods.cpp:2583-2586``: no decoder, no string, or no callback — the
            # callback is given the empty string.
            bridge.complete_decode(slot, "")
            return True

        codepoints = _codepoints(encoded)
        if not is_valid_enc_str(codepoints):
            # ``ui_methods.cpp:2590-2592``: not an encoded string, and the answer says so.
            bridge.complete_decode(slot, NOT_ENCODED)
            return True

        if not _has_text_parser():
            # ``ui_methods.cpp:2595-2598``: no text parser to decode with.
            bridge.complete_decode(slot, "")
            return True

        if not client.resolves(ASYNC_DECODE_STR):
            # The wrapper's own first check: a decoder that is not there answers empty.
            bridge.complete_decode(slot, "")
            return True

        try:
            client.call_function(
                ASYNC_DECODE_STR,
                CallForm.U32_U32_U32,
                bridge.decode_input_address(slot),
                bridge.decoder_address,
                bridge.decode_slot_address(slot),
            )
        except (OSError, RuntimeError, TimeoutError):
            # ``SafeAsyncDecodeStr``'s ``__except``: the call did not go through, so the decode
            # did not start. The text the client was never asked for is not invented here.
            bridge.release_decode(slot)
            return False
    except BaseException:
        bridge.release_decode(slot)
        raise
    return True


def _codepoints(encoded: bytes) -> list[int]:
    """Return a wide string's code units, as the grammar the sources check takes them."""

    usable = len(encoded) - (len(encoded) % 2)
    return [
        int.from_bytes(encoded[index : index + 2], "little")
        for index in range(0, usable, 2)
    ]


def _has_text_parser() -> bool:
    """Return whether the client has the text parser native refuses to decode without.

    ``Context::GetTextParser()`` is native's own *accessor* for the context it runs beside, and
    that is what this asks: the ported context object resolves its address, and a null one is
    the source's third refusal rather than a reason to call anyway.

    It deliberately does not go through ``TextParser._update_ptr``: that is Reforged's per-frame
    refresh, and in this port it also starts the string-table load, which is a read of every
    file of one language — work the client's own decoder does not need, because it decodes with
    its own table.
    """

    from ..client import require_client

    try:
        return bool(require_client().text_parser.resolve_address())
    except (OSError, RuntimeError):
        return False


def decoded_text(slot: int) -> tuple[str, bool]:
    """Take the text one decode produced, and free the slot it was waiting in."""

    from ..client import require_client

    return require_client().bridge.take_decoded_string(slot)


def decode_state(slot: int) -> DecodeState:
    """Return what has happened to one decode slot, without taking anything from it."""

    from ..client import require_client

    return require_client().bridge.decode_state(slot)
