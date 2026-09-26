# Chat port (`GW::chat`)

**Source:** `src/GW/chat/chat_methods.cpp` and `include/GW/chat/chat.h`, with the channel
constants from `include/GW/common/constants/chat.h`. `chat.cpp` is the module's hooking and
callback half; `chat_patterns.cpp` resolves its function pointers. The port's file is
`py4gw/chat.py`.

**Verdict: INCOMPLETE.** What is ported is the send path, because that is what the ported
`Player` members reach; the rest of the module is named below with what each piece needs.

## Ported

| Member | Source | Where |
| --- | --- | --- |
| `ChatChannel` | `Channel` (`common/constants/chat.h:17-35`); Reforged's Python spells it `ChatChannel` (`enums_src/UI_enums.py:35-55`) | `py4gw/chat.py`, re-exported as `Player.ChatChannel` — one declaration, so the two names cannot drift |
| `GetChannel(opcode)` | the `char` overload and the `wchar_t` one that casts to it (`chat_methods.cpp:53-68`) | seven opcodes, `CHANNEL_UNKNOWN` otherwise |
| `SendChat(channel, message)` | `bool SendChat(char, const wchar_t*)` and `bool SendChat(char, const char*)` (`88-113`) | the buffer is the opcode then the text, clamped to 120 code units, placed in the block's data region; the call is `g_send_chat_func(buffer, 0)`, two words |
| `SendChat(name, message)` | `bool SendChat(const wchar_t*, const wchar_t*)` and its `char` sibling (`115-142`) | the whisper form, `L"\"%s,%s"`, bounded at the source's 140 code units |
| `GetChatLog()` | `Context::ChatBuffer* GetChatLog()` (`70-73`) — `*chat_buffer_addr`, or null | the ported `ChatBuffer` context's struct, whose `messages` ring and per-record encoded line are what `Player.RequestChatHistory` walks; landed with the chat-history trio (2026-09-26) |
| the watched history | `OnUICallback_ChatLogLine` (`chat.cpp:205-230`) registers the module's own callback for `kWriteToChatLog` — for the transient marker and its subscribers | the same message is watched by the connection, and `py4gw/chat.py` decodes each announced line as it arrives into the buffer `Player.GetChatHistory` answers from. **This is the one deliberate divergence in the module, at the owner's direction**: native's callback does not keep the lines (its history is filled only by a request), while a post-mortem read here needs no request. The decode is *started* on the listener and completed by the `STRING_DECODED` event, so nothing blocks that thread. |

**The one adaptation, and it is the execution model rather than a choice.** The source builds
`wchar_t buffer[140]` on its own stack and passes its address; nothing of this project's runs in
the client, so the buffer is built with the same contents in the block's data region
(`shared_block.DATA_REGION_OFFSET`, which exists for exactly this) and its address is passed as
the call's first word. `py4gw/dat_reader.py` already hands the client a UTF-16 string the same way
for the GW.dat chain, live-verified, so this is the established mechanism and not a new one.

**One divergence, in the overload dispatch.** C++ resolves `SendChat("A", "hi")` to the *whisper*
overload, because a string literal is a pointer; a one-character Python string is read as a channel
opcode here instead. Character names in this game are at least three characters, so nothing
reachable is lost.

## Not ported

| Surface | Source | What it needs |
| --- | --- | --- |
| `WriteChat`, `WriteChatEnc` | `156-202` — the line is encoded (`L"\x108\x107%s\x1"`) and handed to the client in a `ui::UIChatMessage` packet over `kWriteToChatLog` | the encoding is pure string work; the packet needs the block's data region (available) **and** `g_transient_chat_message`, the client global the source sets around the send — that address is not in the offsets catalog yet, and without it the transient flag cannot be raised |
| `SendFakeChat`, `SendFakeChatColored` | `262-275`, through `WriteChat` | the two members above; `Player`'s two members wait on them, and `FormatChatMessage` (the colour half) is already ported and works |
| `AddToChatLog` | `75-81` — a `kLogChatMessage` packet over `ui::SendUIMessage` | `chat.add_to_chat_log_func` is in the catalog and the UI message form exists; the member is not wired yet |
| `GetChatLog` and the `ChatBuffer` it walks | `70-73` | **ported 2026-09-26** — `py4gw.chat.GetChatLog()` answers the ported `ChatBuffer` struct, and `Player.RequestChatHistory`/`IsChatHistoryReady`/`GetChatHistory` are its first consumers (`player_bindings.cpp:276-325`, `docs/PLAYER_PORT.md`) |
| `RecvWhisper` | `chat.cpp`'s handler | the receive side, and the callback it needs |
| the channel colours, `ToggleTimestamps`, `SetTimestampsFormat`, `SetTimestampsColor`, `ForceRedrawChatLog` | `204-249` | `chat.get_sender_color_func`/`get_message_color_func` are in the catalog; the patch-and-preference parts are not ported |
| the command registry (`CreateCommand`, `DeleteCommand`) | `251-260` | the command callback ABI, and the runtime's callback table — `py4gw/game_thread/callbacks` is this project's own and not a substitute |

## The sender's resolver: found, and it was this port's own fault

`chat.send_chat_func` **resolved to an address in the middle of an instruction.** A live run on
2026-09-25 called what it answered and killed the client (`eip=462fd617`); the host then refused any
target outside the client's code section before writing a descriptor, which stopped that crash from
being possible without explaining it.

**The pattern was never stale — the walk back to the function start was this port's own.**
`tools/resolve_offline.py` runs the port's resolver engine against `Gw.exe` on disk and prints the
step trace, and the trace *was* the diagnosis:

```text
chat.send_chat_func   0x0082D64F (rva 0x42d64f)  e9 c3 ff 8b 45 0c 83 c4 0c …
  scan_target        in 0x00000000 -> out 0x0082D65E  ok      ← the pattern matches here
  to_function_start  in 0x0082D65E -> out 0x0082D64F  ok      ← and walks back fifteen bytes
```

The real prologue is at `0x0082D620`, and the byte `e9` at `0x0082D64F` belongs to **the instruction
before the match site** — its displacement merely happens to leave the module. The port's
`to_function_start` had grown a second candidate for that shape (a `jmp` leaving the module, meant to
survive a function whose entry this project had patched) and took whichever candidate was *nearest*.
The source has no such candidate: ``Scanner::ToFunctionStart`` is three lines that scan backward for
``55 8B EC`` (``scanner.cpp:205-210``), and the member is the source's again.

**Fixed 2026-09-26**, in two places, and the second is where the inference belonged:
`py4gw/scanner/remote.py` is the source's prologue search, and the recovery that needs the patched
entry is `py4gw/client.py`'s `_stale_patch_before`, which looks for the leftover jump *ahead* of the
address the walk answered and verifies the restore by writing the bytes it expects — instead of
guessing from a byte that may be mid-instruction. `tests/test_remote_scanner.py` pins the source's
behaviour with the chat shape as its regression case.

What it costs to be wrong, measured: the same sweep went from **15 of 143 function resolvers**
answering something that does not begin like a function to **4**, and
``chat.send_chat_func`` now answers ``0x0082D620`` — which is the client's chat send, decompiled
here: two arguments (the source's ``void __cdecl (wchar_t* message, uint32_t agent_id)``), a
``0x11C``-byte packet built from the message, and the send call at the end.

The three ported senders are therefore **ported and unblocked**; what they still lack is a live
verification, which is the next step rather than the resolver. `tests/probe_resolver_targets.py`
remains the live, cross-checking diagnostic; the offline run is the one that can be repeated without
a client, an elevation prompt or a risk.

## The log write path: crashed once, fixed, and **live-verified 2026-09-26**

`chat.WriteChatEnc` / `WriteChat` and the two `Player` members that reach them are ported **and
verified live**. The verification run (`tests/probe_chat_log_write.py`, pid 46544, one line on
channel 1):

```json
{ "log_before": 14, "log_after": 15, "marker_in_log": true,
  "newest_lines": ["ÄˆÄ‡py4gw port smoke test\u0001"] }
```

That single line proves the whole path: the `kWriteToChatLog` send reached the client's chat log,
the client accepted the packet, and what it stores is **exactly the source's encoding** — `U+0108`,
`U+0107`, the literal text, `U+0001` (the `\x108\x107%s\x1` wrap of `chat_methods.cpp:159`, shown as
mojibake only because the probe prints the raw stored string rather than asking the client's UI to
render it). No assert, no crash, and the connection restored the client on exit.

**The one crash on this path, and what it was** — kept because the fix is a lesson about this
port's call form, not about the build:

```text
Assertion: text   P:\Code\Gw\Chat\CtChatLog.cpp(765)   Build: 38888
Pc:0085ce74  Arg: 251ecf54 1000007f ...   ← kWriteToChatLog and the packet pointer
```

Ghidra (headless, `tools/ghidra_scripts/DisassembleAt.java` for a routine auto-analysis never
turned into a function) identified `FUN_00825830` = **`AddToChatLog`** — the function the catalog
resolves as `chat.add_to_chat_log_func` — whose first check is `if (message == 0) assert(0x2fd)`, and
the dump's `eax=0` is that null. The port had passed a *pointer to* a `UIChatMessage` where this
port's UI-message form hands the client two payload **words** (`payload.py:645-669`:
`SendUIMessage(arg1, &payload, 0)`, `payload[0] = arg2`, `payload[1] = arg3`). Native can pass
`&param` because it calls `SendUIMessage` itself; the port cannot forward a pointer through that
form. The crash's own arguments settled the field order — the client had entered `AddToChatLog` with
`text = 0` and `channel = 0x07010E40`, i.e. **payload word 0 is the channel and word 1 is the
message** — and the call now passes exactly those two words.

**One divergence stays, and it is the call form's**: `param.channel2 = param.channel`
(`chat_methods.cpp:175`) has no third word in a two-word payload, so it arrives zero. Nothing in the
verified run depended on it; if a future member needs it, the form grows rather than the member
guessing.

The recipe below is what the port was built from and what the verification checks against.

`chat.WriteChatEnc` / `WriteChat` and the two `Player` members that reach them are written and
offline-tested, and a **live run crashed the client** on the first attempt to use them:

```text
Assertion: text
P:\Code\Gw\Chat\CtChatLog.cpp(765)
App: Gw.exe   Build: 38888   BaseAddr: 00610000
Trace (innermost first), the packet's own message id visible in the frames:
Pc:0085ce74  Arg: 251ecf54 1000007f 0676f940 00000000      ← kWriteToChatLog and the pointer
Pc:0085cea8  Arg: 1000007f ...
Stack: 1000007f ... 251ecf54 ... 251ecf4c ... 251ecf58
```

So the message *reached* the client's chat log and the client rejected what it was handed. The
assert is on `text` at `CtChatLog.cpp:765` — the line the log was asked to hold — and the
candidates, in the order they should be eliminated, are the things this port *chose* rather than
read:

1. **the `UIChatMessage` layout** — `{channel, message, channel2}` is native's own struct
   (`context/ui.h:325-329`) for *its* build; if build 38888's packet has the pointer at a different
   offset, the client reads an integer as a `wchar_t*`, which is exactly a `text` assert. Two
   pointers four bytes apart (`251ecf54`, `251ecf58`) sit in the stack beside the message id, which
   is consistent with our 12-byte struct being read with a different field order;
2. **the wrap** — `\x108\x107…\x1` is the source's own encoding of a line (`chat_methods.cpp:159`),
   and the log may validate it (`EncStrValidate`) before storing it;
3. **which message id carries a *line*** — `kWriteToChatLog` (`0x1000007F`) against
   `kWriteToChatLogWithSender` (`0x10000080`), where the source's sender path may be the second.

**The three candidates were all eliminated by the verification run**, and in the order they were
listed: the payload order was the fault (1); the wrap is stored verbatim and is correct (2); and the
message id was right from the start — the client's log path was reached on the first attempt (3). The
candidate list is kept because it is the shape of the next question if this path ever breaks again.

The recipe below is what the port was built from and what the verification checks against.

## The chat-log write path (`WriteChat` / `WriteChatEnc`): the source recipe

The other half of the module — writing a line into the client's own chat log, which is what
`Player.SendFakeChat` and `Player.SendFakeChatColored` need — is scoped from the source, and every
fact it needs is now in hand:

| the source | what it is, and where |
| --- | --- |
| `void WriteChat(Channel, const wchar_t* message, const wchar_t* sender = nullptr, bool transient = false)` | `chat_methods.cpp:156-171`. The message is **wrapped before it is sent**: `swprintf(L"\x108\x107%s\x1", message)` — codepoints `0x0108`, `0x0107`, the text, `0x0001` — and a sender gets the same wrap |
| `void WriteChatEnc(Channel, const wchar_t* message_encoded, const wchar_t* sender_encoded, bool transient)` | `chat_methods.cpp:173-202`. It fills a `ui::UIChatMessage` and sends `ui::UIMessage::kWriteToChatLog` with a pointer to it |
| `UIChatMessage` | `context/ui.h:325-329`, 12 bytes in the client: `{uint32_t channel; wchar_t* message; uint32_t channel2;}`, both channel fields set to the same value |
| `kWriteToChatLog` | `constants/ui.h:62` = **`0x1000007F`** (`kWriteToChatLogWithSender` is `0x10000080`; the source uses the first) |
| the sender form | three formats, chosen by markup: `L"\x76b\x10a%s\x1\x10b%s\x1"`, or the `<a=1>`/`<a=2>` link variants (`:183-191`); the buffer length is `wcslen(m) + wcslen(s) + 6`, `+19` when markup is present |
| the transient marker | `GW::chat::g_transient_chat_message` (`chat.cpp:93`) is **Native's own** state, set around the send and read by Native's own `OnUICallback_ChatLogLine` hook (`chat.cpp:284`) to recognise a line it wrote itself; the port has no such hook yet, so the marker's consumer arrives with that member, not with this one |
| the callers | Native's `SendFakeChat` / `SendFakeChatColored` build the wide string and `Enqueue` the write onto the game thread (`chat_methods.cpp:262-275`); `SendFakeChatColored` first runs `FormatChatMessage` (already ported, `<c=#RRGGBB>…</c>`) |

**The one piece of new plumbing it needs**: the message string, the sender form and the 12-byte
`UIChatMessage` all have to live where the client can read them — the block's data region
(`DATA_SIZE = 4096`, with the GW.dat chain at 0..12 and the chat send buffer at
`BUFFER_OFFSET = 16`), and the send is the **UI-message call form**, which `client.call_function`
refuses by design (`client.py:702-706`: *"a UI message carries a packed payload and is published with
`publish_call` instead"*).

**The form's words are settled** (`payload.py:645-669`): the emitted dispatcher builds a zeroed
two-word payload from `arg2`/`arg3` and calls ``SendUIMessage(arg1, &payload, 0)`` — so `arg1` is the
message id (`0x1000007F`), **`arg2` is `wparam`** (the address of the `UIChatMessage` in the block's
data region, which is what the source passes: `ui::SendUIMessage(kWriteToChatLog, &param)`), and
`arg3` is `lparam`, which the source leaves null.

**What that leaves**: one public way to publish the UI-message form — `Bridge.publish_call`
(`bridge.py:513`, a live-verified form) reached after `Client._descriptor_slot((name,
CallForm.UI_MESSAGE), address, form)`, which is private today and has no public caller anywhere in
the port. That entry point is the last piece: with it, `chat.WriteChatEnc` is a direct transcription
of `chat_methods.cpp:173-202` (fill the 12-byte struct, set the transient marker, send, clear it),
`chat.WriteChat` is `:156-171` (the `\x108\x107…\x1` wrap), and `Player.SendFakeChat` /
`SendFakeChatColored` are `:262-275` on top — no client address is invented anywhere in the chain.
