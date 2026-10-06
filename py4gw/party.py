"""External port of Reforged's ``Py4GWCoreLib/Party.py``, started at the gate.

Reforged's ``Party`` is 810 lines: a main class plus nested ``Players``,
``Heroes``, ``Henchmen`` and ``Pets``. This file exists first because
``Party`` owns the most load-bearing check in the library.

**``Party.IsPlayerLoaded`` is the priority.** In the native runtime it gates the
entire player-context refresh (``PyPlayer::GetContext``,
``player_bindings.cpp:151``), and Reforged's Python calls it from seventeen
sites across eight modules — ``Party``, ``PartyCache``, ``Player``,
``AccountStruct``, ``AgentPartyStruct``, ``agents``, ``interaction`` and
``controller``. Nothing else is worth porting until this works.

Note the two defects this port does **not** reproduce:

* Reforged's ``Party.IsPlayerLoaded`` is a bare ``pass``, so it returns ``None``
  rather than a bool. Implemented here properly.
* Reforged's ``Player.IsPlayerLoaded`` adds a tail — world context, agent
  validity, and ``Agent.GetInstanceUptime(agent_id) > 750`` — that runs only when
  no party member matches, and can return ``True`` where native returns
  ``False``. The native version is used here instead; see
  ``docs/PLAYER_PORT.md``.

Everything not implemented is recorded at the bottom of this module rather than
stubbed into a shape that would lie about working.
"""

from __future__ import annotations

from typing import Any

from .client import ConnectedClient, require_client
from .context.party_context import (
    HenchmanPartyMember,
    HeroPartyMember,
    PartyContextStruct,
    PartyInfoStruct,
    PlayerPartyMember,
)
from .context.world_context import PetInfoStruct, WorldContextStruct


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member that is not ported yet."""

    return NotImplementedError(
        f"Party.{member} is not ported yet: {requirement}. "
        "It exists for source parity so a ported script fails at the call site "
        "and names what it still needs instead of returning a wrong value."
    )


#: ``HeroType`` is Reforged's, and it lives where Reforged keeps it: ``Party.py:4`` imports it
#: from ``enums_src/Hero_enums.py``, and so does this port. The class itself is not redefined
#: here — a second copy is a second chance for the two to drift apart.
from .enums_src.hero_enums import HeroType

#: ``Constants::ControlAction`` is Reforged's ``enums_src/UI_enums.py`` table, which is where the
#: hero control actions `UseSkill` presses live (``Heroes.UseSkill`` → ``PyParty::UseHeroSkill``).
from .enums_src.ui_enums import ControlAction

#: The resolver ``GW::party::set_hard_mode`` calls (``party_methods.cpp:32``, ``:109-117``). Its
#: prototype is ``DoActionFn = void __cdecl(uint32_t identifier)`` (``party_methods.cpp:21``), which
#: this port has measured against the client: the function ends with a bare ``ret`` and ``cc``
#: padding, so its caller releases the word — the ``U32`` call form.
SET_DIFFICULTY_FUNC = "party.set_difficulty_func"

#: The party's own **button callbacks** — native's `PartySearchButtonCallbackFn`
#: (``party_methods.cpp:20``) and the window's (``:30``). Both are called with a *context* array in
#: ECX, a small integer in EDX, and a *`wparam`* array pushed; the client's handler reads them to
#: decide which button was pressed. Their ABIs were measured on this build
#: (``tests/probe_party_abi.py``): the search callback ends ``ret 4`` and the window callback ends
#: with a bare ``ret``, so they need different call forms even though the sources declare one typedef
#: for both.
PARTY_SEARCH_BUTTON_CALLBACK = "party.party_search_button_callback_func"
PARTY_WINDOW_BUTTON_CALLBACK = "party.party_window_button_callback_func"

#: The two functions the flag group calls (``party_methods.cpp:33-34``): ``FlagHeroAgentFn =
#: void __cdecl(uint32_t agent_id, GW::GamePos* pos)`` (``:22``) and ``FlagAllFn = void
#: __cdecl(GW::GamePos* pos)`` (``:23``). The first is the ``U32_FLOAT_PTR`` form — a word and a
#: pointer to the record the payload builds in its own frame — and the second is ``FLOAT_PTR``, the
#: same record with no word. ``GW::GamePos`` is ``{float x; float y; uint32_t zplane;}``
#: (``game_pos.h:255-267``), which is the four-word record both forms build.
FLAG_HERO_AGENT_FUNC = "party.flag_hero_agent_func"
FLAG_ALL_FUNC = "party.flag_all_func"

#: The three functions the behaviour and pet members call, all ``void __cdecl`` two-word calls
#: (``SetHeroBehaviorFn``/``LockPetTargetFn``/``CommandHotKeyDisableAiFn``, ``party_methods.cpp:24-26``;
#: ``lock_pet_target_func`` is declared ``bool`` but nothing reads its answer):
#: ``set_hero_behavior_func`` takes ``(agent_id, Constants::HeroBehavior)``, ``lock_pet_target_func``
#: ``(pet_agent_id, target_id)``, and ``command_hotkey_disable_ai_func`` the hero's agent id with a
#: **zero-based** skill slot (``party_methods.cpp:369``).
SET_HERO_BEHAVIOR_FUNC = "party.set_hero_behavior_func"
LOCK_PET_TARGET_FUNC = "party.lock_pet_target_func"
COMMAND_HOTKEY_DISABLE_AI_FUNC = "party.command_hotkey_disable_ai_func"

#: ``party.party_search_seek_func``: ``void __cdecl(uint32_t search_type, const wchar_t* advertisement,
#: uint32_t)`` (``party_methods.cpp:19``, called at ``:467-472``). Three words — the type, the address
#: of the wide advertisement, and native's own ``0``.
PARTY_SEARCH_SEEK_FUNC = "party.party_search_seek_func"

#: Where the advertisement is placed before the client reads it, in the block's data region: the gap
#: between the party-button arrays (``0x040`` + ``0x50``) and the merchant's records (``0x100``).
#: Native hands the client ``wad.c_str()``, a buffer of its own (``party_bindings.cpp:410-412``); this
#: port has no such buffer inside the client, so the text goes where a pointer argument can reach it —
#: the substitution the merchant's records and the frame layer's label already make. 48 UTF-16 code
#: units, terminator included, which is the bound ``chat.py``'s own buffer note describes for a chat
#: message and far more than a search advertisement carries.
PARTY_ADVERTISEMENT_OFFSET = 0x0A0
PARTY_ADVERTISEMENT_CODE_UNITS = 48

#: The hero control actions ``PyParty::UseHeroSkill`` switches on (``party_bindings.cpp:428-437``).
#: The seven bases are **not** an arithmetic series — ``Hero3Skill1`` is ``0xF5`` and ``Hero4Skill1``
#: is ``0x106`` — which is exactly why the source writes a switch, so this keeps a mapping rather than
#: a formula. The slot is added to the base: ``hero_action + (skill_slot - 1)``.
HERO_SKILL_ACTION_BASE: dict[int, int] = {
    0: int(ControlAction.ControlAction_Hero1Skill1),
    1: int(ControlAction.ControlAction_Hero2Skill1),
    2: int(ControlAction.ControlAction_Hero3Skill1),
    3: int(ControlAction.ControlAction_Hero4Skill1),
    4: int(ControlAction.ControlAction_Hero5Skill1),
    5: int(ControlAction.ControlAction_Hero6Skill1),
    6: int(ControlAction.ControlAction_Hero7Skill1),
}

#: The seven control actions ``Hero::FlagHero`` presses (``party_bindings.cpp:238-247``). A **different**
#: set from the skill actions above — these are the ``CommandHero{N}`` keybinds — and again not an
#: arithmetic series (``0xD7``, ``0xD8``, ``0xD9``, then ``0x102``…), which is why the source writes a
#: switch. The index is the switch's own: ``1..7``, and anything else is ``false``.
HERO_COMMAND_ACTION: dict[int, int] = {
    1: int(ControlAction.ControlAction_CommandHero1),
    2: int(ControlAction.ControlAction_CommandHero2),
    3: int(ControlAction.ControlAction_CommandHero3),
    4: int(ControlAction.ControlAction_CommandHero4),
    5: int(ControlAction.ControlAction_CommandHero5),
    6: int(ControlAction.ControlAction_CommandHero6),
    7: int(ControlAction.ControlAction_CommandHero7),
}

#: ``HUGE_VALF`` (``<math.h>``), the sentinel ``unflag_hero``/``unflag_all`` pass as both coordinates
#: (``party_methods.cpp:334-344``). A position of ``(+inf, +inf, 0)`` is how the party's own flag
#: state spells "unset" — the same value the reads behind `IsAllFlagged`/`GetAllFlag` report.
HUGE_VALF = float("inf")

#: Where the two arrays a callback is handed are built, in the block's data region. Native builds
#: them on its own stack (``uint32_t ctx[13]`` and ``uint32_t wparam[4]``, ``party_methods.cpp:206``);
#: this port has no stack in the client, so they go in the region that exists for exactly this — the
#: same substitution the merchant records make. The span is free space between the dat reader's block
#: at ``0x000`` and the merchant's records at ``0x100``.
PARTY_CTX_OFFSET = 0x040
PARTY_WPARAM_OFFSET = 0x090

#: Native's array sizes, which are the sizes its writes assume: ``ctx[13]`` for every callback and
#: ``ctx[14]`` for the window's `leave_party` (``party_methods.cpp:206``, ``:221``, ``:237``,
#: ``:257``, ``:273``, ``:479``), and ``wparam[4]`` (``:216``). The port's region holds 20 words, so
#: every index the source writes — including the computed ``ctx[ctx[0xb] + 8]`` — is inside it.
PARTY_CTX_WORDS = 20
PARTY_WPARAM_WORDS = 4

#: Native's ``g_tick_work_as_toggle`` (``party.cpp:31``), which ``GW::party::set_tick_toggle``
#: writes and nothing in this port reads yet: in the source its reader is the injected runtime's own
#: tick-button hook (``party.cpp``), which this port does not have. It lives here rather than on
#: ``Party`` because that is where the sources keep it — a global of the ``GW::party`` namespace, not
#: a member of Reforged's class — and the reader is the named work item.
tick_work_as_toggle = False


def set_tick_toggle(enable: bool) -> None:
    """``GW::party::set_tick_toggle`` (``party_methods.cpp:40-42``)."""

    global tick_work_as_toggle
    tick_work_as_toggle = bool(enable)



def _place_words(offset: int, words: list[int]) -> int:
    """Write words into the block's data region and return the address they now sit at."""

    import struct

    from .client import require_client

    payload = b"".join(struct.pack("<I", int(word)) for word in words)
    return require_client().bridge.write_data(offset, payload)


def _press_party_button(
    context: dict[int, int],
    wparam: dict[int, int],
    edx: int,
    *,
    window: bool = False,
) -> bool:
    """The one call behind every party-button member, with native's own arrays.

    ``party_methods.cpp`` builds ``uint32_t ctx[13]`` (``:206`` for the window's, ``:221`` and the
    rest for the search button's) and ``uint32_t wparam[4]``, sets the fields the client reads, and
    calls the callback. This does the same with the same indices, and the two arrays go in the
    block's data region because the port has no frame in the client to build them in — the addresses
    handed over are the region's, exactly as the merchant's records are.

    ``window`` picks the callback **and its measured ABI**: the party-window handler
    (``leave_party``'s) ends with a bare ``ret`` and leaves its word for the caller, where the search
    handler ends ``ret 4``. The two forms exist for that difference; using the wrong one leaves four
    bytes on the client's stack.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    resolver = (
        PARTY_WINDOW_BUTTON_CALLBACK if window else PARTY_SEARCH_BUTTON_CALLBACK
    )
    if not client.resolves(resolver):
        return False

    ctx = [0] * PARTY_CTX_WORDS
    for index, value in context.items():
        ctx[index] = int(value)
    button = [0] * PARTY_WPARAM_WORDS
    for index, value in wparam.items():
        button[index] = int(value)

    ctx_address = _place_words(PARTY_CTX_OFFSET, ctx)
    wparam_address = _place_words(PARTY_WPARAM_OFFSET, button)
    client.call_function(
        resolver,
        CallForm.FASTCALL_U32_CALLER_RELEASES if window else CallForm.FASTCALL_U32,
        ctx_address,
        int(edx),
        wparam_address,
    )
    return True


def _call_difficulty(flag: bool) -> None:
    """``GW::party::set_hard_mode`` (``party_methods.cpp:109-117``), the body behind the member.

    Native's own order and its own guards: the function must be there, the party context must have a
    player party, and the client is told **only when the mode is not already the one asked for** —
    ``if (p->InHardMode() != flag) g_set_difficulty_func(flag);``. The call runs on the game thread,
    which is this port's call path.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    context = Party._context()
    if context is None or context.player_party is None:
        return
    if not client.resolves(SET_DIFFICULTY_FUNC):
        return
    if bool(context.in_hard_mode) != bool(flag):
        client.call_function(
            SET_DIFFICULTY_FUNC, CallForm.U32, 1 if flag else 0
        )


def _flag_hero_agent(agent_id: int, x: float, y: float) -> bool:
    """``GW::party::flag_hero_agent`` (``party_methods.cpp:325-332``), the body behind three members.

    Native's own order and its own guards: the function must be there, the agent id must not be zero,
    and it must **not** be the controlled character — the client refuses to flag the player — before
    ``g_flag_hero_agent_func(agent_id, &pos)`` is called with a ``GamePos`` built from the caller's
    two floats. That record is what the ``U32_FLOAT_PTR`` form builds in the payload's own frame, so
    the two coordinates travel as their bit patterns (``shared_block.float_bits``).
    """

    from .game_thread.shared_block import CallForm, float_bits

    client = require_client()
    if not client.resolves(FLAG_HERO_AGENT_FUNC):
        return False
    if agent_id == 0:
        return False
    if agent_id == _controlled_character_id():
        return False
    client.call_function(
        FLAG_HERO_AGENT_FUNC,
        CallForm.U32_FLOAT_PTR,
        int(agent_id),
        float_bits(x),
        float_bits(y),
        float_bits(0.0),
    )
    return True


def _controlled_character_id() -> int:
    """``agent::GetControlledCharacterId`` (``agent_methods.cpp:60-63``), through the ported member.

    The native line is ``world && world->playerControlledChar ? world->playerControlledChar->agent_id
    : 0``; this is ``Player.GetAgentID()``, which reads that same field — the third module here to
    express it that way (``py4gw/skillbar.py:368-373``, ``py4gw/native_src/item/py_inventory.py:173-178``), because
    one scheme is the point. The port's member gates on ``Player.IsPlayerLoaded`` first, which the
    native line does not: when that gate refuses, this answers ``0`` and the guard below then passes
    for any nonzero agent id — the same outcome native's own ``0`` produces.
    """

    from .player import Player

    return int(Player.GetAgentID())


def _flag_hero(hero_index: int, x: float, y: float) -> bool:
    """``GW::party::flag_hero`` (``party_methods.cpp:321-323``): the index resolves first.

    ``return flag_hero_agent(agent::GetHeroAgentID(hero_index), pos);`` — and ``GetHeroAgentID`` is
    ``party::get_hero_agent_id`` (``agent_methods.cpp:240-247``), the walk the port already carries as
    ``Party.Heroes.GetHeroAgentIDByPartyPosition`` (position ``0`` is the controlled character, which
    is what makes the guard above refuse an unflag of the player).
    """

    return _flag_hero_agent(
        Party.Heroes.GetHeroAgentIDByPartyPosition(int(hero_index)), x, y
    )


def _flag_all(x: float, y: float) -> bool:
    """``GW::party::flag_all`` (``party_methods.cpp:338-340``).

    The whole body is the guard and the call: ``return g_flag_all_func ? g_flag_all_func(&pos), true
    : false;`` — one ``FLOAT_PTR`` call over the same record, with no agent id.
    """

    from .game_thread.shared_block import CallForm, float_bits

    client = require_client()
    if not client.resolves(FLAG_ALL_FUNC):
        return False
    client.call_function(
        FLAG_ALL_FUNC,
        CallForm.FLOAT_PTR,
        float_bits(x),
        float_bits(y),
        float_bits(0.0),
    )
    return True


def _set_hero_behavior(agent_id: int, behavior: int) -> bool:
    """``GW::party::set_hero_behavior`` (``party_methods.cpp:346-358``).

    Native's own order: the world context, the function and a **non-empty** ``hero_flags`` array are
    one guard; then the array is walked for the record whose ``agent_id`` matches, the client is told
    **only when the record's own ``hero_behavior`` differs** from the one asked for, and a record that
    is not in the array ends the member with ``false``. The comparison is between words: the record's
    field and the caller's argument.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    world = Party._world()
    if world is None:
        return False
    if not client.resolves(SET_HERO_BEHAVIOR_FUNC):
        return False
    flags = world.hero_flags or []
    if not flags:
        return False
    for flag in flags:
        if int(flag.agent_id) == int(agent_id):
            if int(flag.hero_behavior) != int(behavior):
                client.call_function(
                    SET_HERO_BEHAVIOR_FUNC,
                    CallForm.U32_U32,
                    int(agent_id),
                    int(behavior),
                )
            return True
    return False


def _set_hero_skill_ai_enabled(
    hero_agent_id: int, skill_slot: int, enabled: bool
) -> bool:
    """``GW::party::set_hero_skill_ai_enabled`` (``party_methods.cpp:361-389``).

    Four guards in the source's own order — the function, a non-zero hero agent, a slot inside
    ``1..8``, and the party's skillbar array (``Context::GetSkillbarArray``, ``context_methods.cpp:234-236``,
    which is null unless the world holds one) — then the hero's own skillbar is found by ``agent_id``,
    the slot's bit is read out of the record's ``disabled`` word, and **the call happens only when the
    client's state is not already the one asked for**: ``if (is_disabled == !enabled) return true;``.

    Native wraps the call in ``game_thread::Enqueue``; the port's call path **is** the game thread, and
    ``Enqueue`` runs its callable inline when it is already on that thread
    (``game_thread_methods.cpp:33-45``) — the same note `UIManager.Keypress` carries.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    if not client.resolves(COMMAND_HOTKEY_DISABLE_AI_FUNC):
        return False
    if not hero_agent_id:
        return False
    if int(skill_slot) < 1 or int(skill_slot) > 8:
        return False
    world = Party._world()
    if world is None:
        return False
    skillbars = world.skillbars
    if skillbars is None:
        return False

    zero_based_slot = int(skill_slot) - 1
    disabled_bit = 1 << zero_based_slot
    hero_skillbar = None
    for skillbar in skillbars:
        if int(skillbar.agent_id) == int(hero_agent_id):
            hero_skillbar = skillbar
            break
    if hero_skillbar is None:
        return False

    is_disabled = (int(hero_skillbar.disabled) & disabled_bit) != 0
    if is_disabled == (not enabled):
        return True
    client.call_function(
        COMMAND_HOTKEY_DISABLE_AI_FUNC,
        CallForm.U32_U32,
        int(hero_agent_id),
        zero_based_slot,
    )
    return True


def _set_pet_behavior(behavior: int, lock_target_id: int) -> bool:
    """``GW::party::set_pet_behavior`` (``party_methods.cpp:391-413``).

    The guard is the world, **both** functions and a non-empty ``pets`` array; the pet is the
    controlled character's own (``get_pet_info()`` with no owner walks ``world->pets`` for
    ``agent::GetControlledCharacterId()``, which is `Party.Pets._pet_info(0)`). For the **Fight**
    behaviour only, native resolves a target — ``lock_target_id ? agent::GetAgentByID(lock_target_id) :
    agent::GetTarget()``, and ``GetTarget()`` is ``GetAgentByID(GetTargetId())`` — and requires it to
    be a **living enemy**; any other behaviour locks no target. Then, each on its own test, the locked
    target is written when it differs (``g_lock_pet_target_func``) and the behaviour is set when it
    differs (``g_set_hero_behavior_func``).

    ``Constants::HeroBehavior::Fight`` is the only constant this body needs, and the port's ported
    enum for it is Reforged's ``PetBehavior`` (``enums_src/hero_enums.py``), whose ``Fight`` is the
    same ``0``. The two sources disagree on the *third* member's name — Reforged's ``Heel`` against
    Native's ``AvoidCombat`` — which is recorded rather than resolved: no member here compares it.
    """

    from .agent import Agent
    from .enums_src.game_data_enums import Allegiance
    from .enums_src.hero_enums import PetBehavior
    from .game_thread.shared_block import CallForm
    from .player import Player

    client = require_client()
    world = Party._world()
    if world is None:
        return False
    if not client.resolves(SET_HERO_BEHAVIOR_FUNC):
        return False
    if not client.resolves(LOCK_PET_TARGET_FUNC):
        return False
    if not (world.pets or []):
        return False

    pet_info = Party.Pets._pet_info(0)
    if pet_info is None:
        return False

    target_agent_id = 0
    if int(behavior) == int(PetBehavior.Fight):
        looked_up = int(lock_target_id) or Player.GetTargetID()
        target = Agent.GetLivingAgentByID(looked_up)
        if (
            target is None
            or not Agent.IsLiving(looked_up)
            or int(target.allegiance) != int(Allegiance.Enemy)
        ):
            return False
        target_agent_id = int(target.agent_id)

    if int(pet_info.locked_target_id) != target_agent_id:
        client.call_function(
            LOCK_PET_TARGET_FUNC,
            CallForm.U32_U32,
            int(pet_info.agent_id),
            target_agent_id,
        )
    if int(pet_info.behavior) != int(behavior):
        client.call_function(
            SET_HERO_BEHAVIOR_FUNC,
            CallForm.U32_U32,
            int(pet_info.agent_id),
            int(behavior),
        )
    return True


def _search_party(search_type: int, advertisement: str) -> bool:
    """``GW::party::search_party`` (``party_methods.cpp:467-472``).

    ``if (!g_party_search_seek_func) return false; g_party_search_seek_func(search_type,
    advertisement ? advertisement : L"", 0); return true;`` — the empty advertisement is native's own
    ``L""`` rather than a null pointer, because the binding only passes null for an empty Python
    string and the methods layer replaces that with an empty wide string anyway
    (``party_bindings.cpp:410-412``). The text is placed in the block and its address handed over,
    which is what ``wad.c_str()`` is for native.
    """

    from .game_thread.shared_block import CallForm

    client = require_client()
    if not client.resolves(PARTY_SEARCH_SEEK_FUNC):
        return False
    address = client.bridge.write_data(
        PARTY_ADVERTISEMENT_OFFSET, _wide_text(advertisement)
    )
    client.call_function(
        PARTY_SEARCH_SEEK_FUNC, CallForm.U32_U32_U32, int(search_type), address, 0
    )
    return True


def _wide_text(text: str) -> bytes:
    """One string as the wide, terminated bytes the client's own readers walk.

    A ``std::wstring`` conversion hands the client UTF-16 code units and ``c_str()`` adds the
    terminator; the same shape is what the frame layer's label lookup places, and the bound here is
    the region's own (``PARTY_ADVERTISEMENT_CODE_UNITS``). Native's ``swprintf(buf, 32, ...)`` bounds
    the two chat commands at 32 units, which is inside this one.
    """

    units = text.encode("utf-16-le")[: PARTY_ADVERTISEMENT_CODE_UNITS * 2 - 2]
    return units + b"\x00\x00"


def _player_record(login_number: int) -> Any:
    """``player::GetPlayerByID`` (``player_methods.cpp:105-112``), the walk the name/chat members share.

    ``if (!player_id) player_id = GetPlayerNumber();`` — **zero means the caller's own player
    number** — then ``players && player_id < players->size() ? &players->at(player_id) : nullptr``.
    ``None`` is that nullptr.
    """

    from .player import Player

    player_id = int(login_number)
    if not player_id:
        player_id = int(Player.GetPlayerNumber() or 0)
    world = Party._world()
    if world is None:
        return None
    players = world.players
    if players is None or player_id >= len(players):
        return None
    return players[player_id]


def _player_name(login_number: int) -> str:
    """``player::GetPlayerName`` (``player_methods.cpp:114-117``): the record's own ``name`` pointer.

    ``return player ? player->name : nullptr;`` — an absent player is the empty string the binding
    answers for a null name (``party_bindings.cpp:404-405``).
    """

    record = _player_record(login_number)
    if record is None:
        return ""
    return record.name_encoded_str or ""


def _send_chat_command(command: str) -> bool:
    """``chat::SendChat('/', buf)`` — the channel command both party-chat members send.

    Native formats into a 32-unit buffer with ``swprintf`` and refuses when it does not fit; the port
    formats the same text and hands it to the ported `chat.SendChat` on the **command** channel
    (``'/'``), which is the client's own ``/invite`` and ``/kick`` syntax. The length test is native's
    own bound, kept where the source keeps it: at the buffer, before the send.
    """

    from .native_src.chat.chat import SendChat

    if len(command) >= 32:
        return False
    return bool(SendChat("/", command))


def _use_hero_skill(hero_id: int, skill_slot: int, target_id: int) -> None:
    """``PyParty::UseHeroSkill`` (``party_bindings.cpp:424-447``), the body behind `Heroes.UseSkill`.

    Native's own arithmetic and its own order: the slot is made zero-based and the hero number is
    looked up in a **switch** of the seven ``ControlAction_Hero{N}Skill1`` bases — anything else
    returns without doing anything — the current target is remembered, and then the enqueued body
    changes the target (only if the caller asked for one and it is not already the target), presses
    ``hero_action + skill_idx``, and puts the previous target back (only if there was one and the
    caller's differs). ``game_thread::Enqueue`` runs inline on the game thread, which the port's call
    path already is, so the three steps happen in the source's order.

    ``ChangeTarget`` and ``Keypress`` are the port's own members for ``agent::ChangeTarget`` and
    ``ui::Keypress`` (``py4gw/player.py``, ``py4gw/ui_manager.py``) — the same two the source calls.
    """

    from .player import Player
    from .ui_manager import UIManager

    skill_idx = int(skill_slot) - 1
    hero_action = HERO_SKILL_ACTION_BASE.get(int(hero_id) - 1)
    if hero_action is None:
        return
    current_target = Player.GetTargetID()
    if target_id and int(target_id) != int(current_target):
        Player.ChangeTarget(int(target_id))
    UIManager.Keypress(hero_action + skill_idx, 0)
    if current_target and int(target_id) != int(current_target):
        Player.ChangeTarget(int(current_target))



#: Native ``kHeroNameMap`` (``party_bindings.cpp:173``): display name to id.
#: ``Devona`` and ``GhostOfAlthea`` have no entry in the source table.
HERO_NAME_TO_ID: dict[str, HeroType] = {
    "": HeroType.None_,
    "Norgu": HeroType.Norgu,
    "Goren": HeroType.Goren,
    "Tahlkora": HeroType.Tahlkora,
    "Master Of Whispers": HeroType.MasterOfWhispers,
    "Acolyte Jin": HeroType.AcolyteJin,
    "Koss": HeroType.Koss,
    "Dunkoro": HeroType.Dunkoro,
    "Acolyte Sousuke": HeroType.AcolyteSousuke,
    "Melonni": HeroType.Melonni,
    "Zhed Shadowhoof": HeroType.ZhedShadowhoof,
    "General Morgahn": HeroType.GeneralMorgahn,
    "Magrid The Sly": HeroType.MagridTheSly,
    "Zenmai": HeroType.Zenmai,
    "Olias": HeroType.Olias,
    "Razah": HeroType.Razah,
    "M.O.X.": HeroType.MOX,
    "Keiran Thackeray": HeroType.KeiranThackeray,
    "Jora": HeroType.Jora,
    "Pyre Fierceshot": HeroType.PyreFierceshot,
    "Anton": HeroType.Anton,
    "Livia": HeroType.Livia,
    "Hayda": HeroType.Hayda,
    "Kahmu": HeroType.Kahmu,
    "Gwen": HeroType.Gwen,
    "Xandra": HeroType.Xandra,
    "Vekk": HeroType.Vekk,
    "Ogden Stonehealer": HeroType.Ogden,
    "Mercenary Hero 1": HeroType.MercenaryHero1,
    "Mercenary Hero 2": HeroType.MercenaryHero2,
    "Mercenary Hero 3": HeroType.MercenaryHero3,
    "Mercenary Hero 4": HeroType.MercenaryHero4,
    "Mercenary Hero 5": HeroType.MercenaryHero5,
    "Mercenary Hero 6": HeroType.MercenaryHero6,
    "Mercenary Hero 7": HeroType.MercenaryHero7,
    "Mercenary Hero 8": HeroType.MercenaryHero8,
    "Miku": HeroType.Miku,
    "Zei Ri": HeroType.ZeiRi,
}


class Hero:
    """Native ``PyParty.Hero``, ported from ``party_bindings.cpp:214``.

    The source keeps a hero id and two fields (``hero_name``,
    ``hero_profession``) that neither constructor assigns, so ``GetName`` always
    returns an empty string and ``GetProfession`` always returns ``0``.
    """

    _MAX_ID = int(HeroType.ZeiRi)

    def __init__(self, value: int | str = 0) -> None:
        """Resolve a hero from an id or a display name."""

        if isinstance(value, str):
            self._hero_id = HERO_NAME_TO_ID.get(value, HeroType.None_)
        elif 0 <= int(value) <= Hero._MAX_ID:
            self._hero_id = HeroType(int(value))
        else:
            self._hero_id = HeroType.None_

    def GetID(self) -> int:
        """Return the hero id."""

        return int(self._hero_id)

    def GetName(self) -> str:
        """Return the hero name, which the source never populates."""

        return ""

    def GetProfession(self) -> int:
        """Return the hero profession, which the source never populates."""

        return 0

    def FlagHero(self, idx: int) -> bool:
        """``Hero::FlagHero`` (``party_bindings.cpp:235-250``): press the hero's command keybind.

        The source's whole body is a **switch on ``idx``**: ``1..7`` select the matching
        ``ControlAction_CommandHero{N}`` and anything else answers ``false`` without pressing
        anything. The press is ``GW::ui::Keypress(key)``, which is the port's
        ``UIManager.Keypress(key, 0)`` — ``0`` being the frame the client's own ``Keydown`` uses when
        no target is given (``ui_methods.cpp:1408-1426``). Note the argument is the **hero's number**,
        not an agent id: the switch is what makes that explicit, and it is a different set of control
        actions from the skill ones `Heroes.UseSkill` presses.
        """

        from .ui_manager import UIManager

        key = HERO_COMMAND_ACTION.get(int(idx))
        if key is None:
            return False
        UIManager.Keypress(key, 0)
        return True

    def __eq__(self, other: object) -> bool:
        """``Hero::operator==`` (``party_bindings.cpp:49``): the hero ids compare, nothing else."""

        if not isinstance(other, Hero):
            return NotImplemented
        return self._hero_id == other._hero_id

    def __ne__(self, other: object) -> bool:
        """``Hero::operator!=`` (``party_bindings.cpp:50``), the ids' own inequality."""

        if not isinstance(other, Hero):
            return NotImplemented
        return self._hero_id != other._hero_id

    def __hash__(self) -> int:
        """Keep the class usable as a key, as the port's other bound value classes are."""

        return hash(self._hero_id)

    def __repr__(self) -> str:
        """``.def("__repr__", ...)`` (``party_bindings.cpp:491-492``), character for character."""

        return f"<Hero name='{self.GetName()}' id={self.GetID()}>"


class Party:
    """Read-only port of the Reforged ``Party`` namespace class.

    **The members below are in Reforged's own declaration order**, namespaces included, and round 17
    moved them there: the port had grouped them by subject (identity, state, actions), which reads
    well and is not the source's shape. `tests/test_party_offline.py` now compares this module's
    declaration order against ``Py4GWCoreLib/Party.py``'s, so it cannot drift back. The port's own
    private helpers — ``_context``, ``_party``, ``_world`` and ``_is_party_connected`` — sit first
    because the source has no members of that kind to place them by.
    """

    @staticmethod
    def _context() -> PartyContextStruct | None:
        """Return the party context, or ``None`` while it is unavailable."""

        try:
            return require_client().read_party_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _party() -> PartyInfoStruct | None:
        """Return the party record, or ``None`` while it is unavailable."""

        context = Party._context()
        return context.player_party if context is not None else None

    @staticmethod
    def _world() -> WorldContextStruct | None:
        """Return the world context, or ``None`` while it is unavailable."""

        try:
            return require_client().read_world_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _is_party_connected() -> bool:
        """Return whether every player-party member reports ``connected()``.

        Native ``get_is_party_loaded``, which the binding exposes as the
        ``is_party_loaded`` property that ``Party.IsPartyLoaded`` reads last. It
        requires a readable player array; an unreadable or empty one is ``False``
        rather than a vacuous ``True``.

        Private because Reforged's Python surface has no member for it; the
        public member is the composite :meth:`IsPartyLoaded`.
        """

        players = Party.GetPlayers()
        if not players:
            return False
        return all(bool(member.is_connected) for member in players)

    @staticmethod
    def party_instance() -> Any:
        """Reforged's ``party_instance()`` (``Party.py:13-18``): **the in-process artifact**.

        ``return PyParty.PyParty()`` — a native binding object, constructed **inside the client**, with
        the whole ``GW::party`` surface hanging off it. An external port has nothing to construct and
        no object to hand back, and every member that used it here does what its own source line does
        instead: the reads go to the party context, and the actions call the functions the binding
        called. That makes this the third member of the artifact kind in this project, with
        ``Player.player_instance`` and ``Agent.GetProfessionsTexturePaths``; it is reported and never
        stood in for.
        """

        raise _unported(
            "party_instance",
            "it returns a PyParty native binding object, which only exists "
            "inside the client",
        )

    @staticmethod
    def GetPartyID() -> int:
        """Return the party's id, or ``0``."""

        party = Party._party()
        return int(party.party_id) if party is not None else 0

    @staticmethod
    def GetPartyLeaderID() -> int:
        """Return the party leader's agent id (``Party.py:28-38``).

        **The source's own two lines, with its own assumption left in**: ``players = Party.GetPlayers()``
        then ``leader = players[0]`` — a party with no player-party entry raises ``IndexError`` there,
        and an earlier version of this member quietly answered ``0`` instead. That default was this
        port's, not the source's, and round 10 removed it: the member reads the first entry, exactly as
        the source does, and its agent id comes from the world context (``GetAgentIDByLoginNumber``).
        """

        players = Party.GetPlayers()
        leader = players[0]
        return Party.Players.GetAgentIDByLoginNumber(int(leader.login_number))

    @staticmethod
    def GetOwnPartyNumber() -> int:
        """Return this player's zero-based index in the party, or ``-1``."""

        from .player import Player

        agent_id = Player.GetAgentID()
        for index, member in enumerate(Party.GetPlayers()):
            if Party.Players.GetAgentIDByLoginNumber(
                int(member.login_number)
            ) == agent_id:
                return index
        return -1

    @staticmethod
    def GetPartyTarget() -> int:
        """Return the party's called target agent id, or ``0`` (``Party.py:56-66``).

        Reforged's own body, call for call: ``if not Party.IsPartyLoaded(): return 0``, then the first
        player-party entry's ``called_target_id``, accepted only when ``Agent.IsValid`` says the agent
        resolves. **Round 10 corrected two of those calls**: this member used ``Party.IsPlayerLoaded``
        and ``Player.IsAgentIDValid`` — both of them *different members* from the two the source names,
        answering nearly the same thing and neither of them what the source actually calls.
        """

        if not Party.IsPartyLoaded():
            return 0
        players = Party.GetPlayers()
        target = int(players[0].called_target_id)
        from .agent import Agent

        return target if Agent.IsValid(target) else 0

    @staticmethod
    def GetPlayers() -> list[PlayerPartyMember]:
        """Return the current player-party members, or an empty list.

        Reforged returns the native binding's ``players`` list; this returns the
        same records decoded from the party context.
        """

        party = Party._party()
        if party is None:
            return []
        return list(party.players or [])

    @staticmethod
    def GetHeroes() -> list[HeroPartyMember]:
        """Return the current hero-party members, or an empty list."""

        party = Party._party()
        if party is None:
            return []
        return list(party.heroes or [])

    @staticmethod
    def GetHenchmen() -> list[HenchmanPartyMember]:
        """Return the current henchman-party members, or an empty list."""

        party = Party._party()
        if party is None:
            return []
        return list(party.henchmen or [])

    @staticmethod
    def GetOthers() -> list[int]:
        """Return the agent ids of allies, minions and pets in the party.

        Two different things are called ``others`` in the source. The binding
        owns a ``std::vector<uint32_t> others`` that ``PyParty::GetContext``
        clears and never fills, so the binding's copy is always empty.
        ``GW::Context::PartyInfo::others`` is the game's own array, described
        there as "agent id of allies, minions, pets", and Reforged reads that
        one in ``native_src/context/PartyContext.py:78``. The array is the one
        that carries data, so this reads it.
        """

        party = Party._party()
        if party is None:
            return []
        return [int(value) for value in (party.others or [])]

    @staticmethod
    def IsHardModeUnlocked() -> bool:
        """Return whether hard mode is unlocked on this account."""

        world = Party._world()
        return bool(world is not None and int(world.is_hard_mode_unlocked))

    @staticmethod
    def IsHardMode() -> bool:
        """Return whether the party is in hard mode.

        Native ``get_is_party_in_hard_mode`` is
        ``PartyContext::InHardMode()``: bit 4 of the context flag.
        """

        context = Party._context()
        return bool(context is not None and context.in_hard_mode)

    @staticmethod
    def IsNormalMode() -> bool:
        """Return whether the party is in normal mode."""

        return not Party.IsHardMode()

    @staticmethod
    def GetPartySize() -> int:
        """Return the party size: players, heroes and henchmen together.

        Native ``get_party_size`` is
        ``players.size() + heroes.size() + henchmen.size()``, not the player
        count.
        """

        return (
            len(Party.GetPlayers())
            + len(Party.GetHeroes())
            + len(Party.GetHenchmen())
        )

    @staticmethod
    def GetPlayerCount() -> int:
        """Return how many players are in the party."""

        return len(Party.GetPlayers())

    @staticmethod
    def GetHeroIndex(hero_id: HeroType | int) -> int:
        """Return a hero's one-based position in the party, or ``0``.

        Native matches on both the hero id and the owning player, and returns
        ``index + 1`` so that ``0`` stays free to mean "not found".
        """

        from .player import Player

        heroes = Party.GetHeroes()
        login_number = Player.GetLoginNumber()
        for index, hero in enumerate(heroes):
            if (
                int(hero.hero_id) == int(hero_id)
                and int(hero.owner_player_id) == login_number
            ):
                return index + 1
        return 0

    @staticmethod
    def GetHeroCount() -> int:
        """Return how many heroes are in the party.

        Native ``get_party_hero_count`` is ``heroes.size()`` on the party info,
        not the party context's ``hero_count`` field.
        """

        return len(Party.GetHeroes())

    @staticmethod
    def GetHenchmanCount() -> int:
        """Return how many henchmen are in the party."""

        return len(Party.GetHenchmen())

    @staticmethod
    def IsPartyDefeated() -> bool:
        """Return whether the party has been defeated."""

        context = Party._context()
        return bool(context is not None and context.is_defeated)

    @staticmethod
    def IsPartyLoaded() -> bool:
        """Return whether the party is loaded.

        Reforged checks the map gate, then ``Player.IsPlayerLoaded``, then the
        native ``is_party_loaded``, which is every player-party member reporting
        ``connected()``. All three are now ported.
        """

        from .map import Map
        from .player import Player

        if not Map.IsMapReady():
            return False
        if not Player.IsPlayerLoaded():
            return False
        return Party._is_party_connected()

    @staticmethod
    def GetPartyMorale() -> list[tuple[int, int]]:
        """Return ``(agent_id, morale)`` per party member, skipping invalid ones.

        Reforged walks ``world->party_morale`` links, follows each link's
        ``party_member_info`` pointer, and skips entries whose agent id does not
        resolve.
        """

        from .player import Player

        world = Party._world()
        if world is None:
            return []
        morale: list[tuple[int, int]] = []
        for link in world.party_morale or []:
            member = link.party_member_info
            if member is None:
                continue
            agent_id = int(member.agent_id)
            if not Player.IsAgentIDValid(agent_id):
                continue
            morale.append((agent_id, int(member.morale)))
        return morale

    @staticmethod
    def IsPlayerLoaded() -> bool:
        """Return whether this player is connected in a ready map.

        The native implementation (``player_bindings.cpp:30``), which the source
        describes as "parity with legacy ``GW::PartyMgr::GetIsPlayerLoaded(-1)``":

        1. the map is ready — contexts exist and the map is not loading;
        2. the player number is readable;
        3. the party member whose ``login_number`` matches it reports
           ``connected()``;
        4. otherwise ``False``.

        **Reforged's Python version is a bare ``pass``** — the member answers ``None`` — so this is the
        one member of the class whose body is not the source's Python at all: it is the native function
        that body was written to reach (``PyPlayer::IsPlayerLoaded``, ``player_bindings.cpp:30``, which
        the source's own docstring names as "parity with legacy
        ``GW::PartyMgr::GetIsPlayerLoaded(-1)``"). Recorded as a divergence in
        ``docs/PARTY_PORT.md``: the port chose the function the source names over the stub it wrote,
        because a member that answers ``None`` where Native answers a bool is not a port of anything.
        """

        client = require_client()
        from .map import Map

        if not Map.IsMapReady():
            return False

        from .player import Player

        player_number = Player.GetPlayerNumber()
        if player_number is None:
            return False
        for member in Party.GetPlayers():
            if int(member.login_number) == player_number:
                return bool(member.is_connected)
        return False

    @staticmethod
    def IsPartyLeader() -> bool:
        """Return whether this client is the party leader.

        Native ``get_is_leader`` takes the first *connected* player in the party
        and returns whether its login number is this player's. That is a
        different computation from ``PartyContext::IsPartyLeader()``, which
        reads bit 7 of the context flag, and the binding uses the former.
        """

        from .player import Player

        players = Party.GetPlayers()
        if not players:
            return False
        player_number = Player.GetPlayerNumber()
        for member in players:
            if bool(member.is_connected):
                return int(member.login_number) == player_number
        return False

    @staticmethod
    def SetTickasToggle(enable: bool) -> None:
        """``Party.SetTickasToggle`` (``Party.py:269-275``) → ``PyParty().tick.SetTickToggle``.

        Native's ``PartyTick::SetTickToggle`` is one line: ``GW::party::set_tick_toggle(enable)``
        (``party_bindings.cpp:92``), which writes the runtime's ``g_tick_work_as_toggle``
        (``party_methods.cpp:40-42``). No client call is made, so this needs nothing but the flag.
        """

        set_tick_toggle(enable)

    @staticmethod
    def IsAllTicked() -> bool:
        """Return whether every player-party member is ticked.

        Native ``get_is_party_ticked``: all players ticked, with an unreadable or
        empty player array reporting ``False``.
        """

        players = Party.GetPlayers()
        if not players:
            return False
        return all(bool(member.is_ticked) for member in players)

    @staticmethod
    def IsPlayerTicked(login_number: int) -> bool:
        """Return whether one player-party member is ticked.

        Native ``get_is_player_ticked`` treats its argument as an **index** into
        the player array, with ``0xFFFFFFFF`` meaning "this player", found by
        login number. Reforged's Python names the parameter ``login_number`` and
        passes it straight through, so the name and the meaning disagree in the
        source; the native meaning is kept here.
        """

        from .player import Player

        players = Party.GetPlayers()
        if not players:
            return False
        if login_number == 0xFFFFFFFF:
            player_number = Player.GetPlayerNumber()
            for member in players:
                if int(member.login_number) == player_number:
                    return bool(member.is_ticked)
            return False
        if login_number >= len(players):
            return False
        return bool(players[login_number].is_ticked)

    @staticmethod
    def SetTicked(ticked: bool) -> None:
        """``Party.SetTicked`` (``Party.py:296-302``) → ``PyParty().tick.SetTicked(ticked)``.

        **The source's own body reaches no client state, and this is a finding rather than a
        shortcut.** ``party_instance()`` builds a **new** ``PyParty`` on every call
        (``Party.py:13-18``), whose ``GetContext`` copies the client's ready state into the object
        (``party_bindings.cpp:166-180``), and ``PartyTick::SetTicked`` writes that object's own bool
        (``party_bindings.cpp:90``). The object is discarded with the call, so the client is never
        told anything — ``Party.SetTicked`` cannot ready the party, and neither can
        ``ToggleTicked``, which composes it. What *does* ready the party is the ready-status function
        the runtime calls for its tick button (``party.set_ready_status_func``, ``party_methods.cpp:44-52``);
        nothing in ``Party.py`` reaches it.
        """

    @staticmethod
    def ToggleTicked() -> None:
        """``Party.ToggleTicked`` (``Party.py:305-317``): the source's own two reads, then ``SetTicked``.

        The reads run — the login number by the player's agent id, then the party number for it, then
        whether that member is ticked — and the write is whatever ``SetTicked`` is, which the source's
        own body makes nothing at all. Kept in the source's order so the reads happen as written.
        """

        from .player import Player

        login_number = Party.Players.GetLoginNumberByAgentID(Player.GetAgentID())
        party_number = Party.Players.GetPartyNumberFromLoginNumber(login_number)

        if Party.IsPlayerTicked(party_number):
            Party.SetTicked(False)
        else:
            Party.SetTicked(True)

    @staticmethod
    def SetHardMode() -> None:
        """``Party.SetHardMode`` (``Party.py:322-328``).

        The source's own guard first — *"if Party.IsHardModeUnlocked() and Party.IsNormalMode()"* —
        and then ``PyParty::SetHardMode(True)``, which is ``GW::party::set_hard_mode(true)``:
        ``g_set_difficulty_func(flag)`` when the party context has a player party and the mode is not
        already the one asked for (``party_methods.cpp:109-117``).
        """

        if Party.IsHardModeUnlocked() and Party.IsNormalMode():
            _call_difficulty(True)

    @staticmethod
    def SetNormalMode() -> None:
        """``Party.SetNormalMode`` (``Party.py:331-338``)."""

        if Party.IsHardMode():
            _call_difficulty(False)

    @staticmethod
    def SearchParty(search_type: int, advertisement: str) -> bool:
        """``Party.SearchParty`` (``Party.py:340-349``) → ``GW::party::search_party``.

        Reforged's member **returns** the binding's value and the binding is
        ``return GW::party::search_party(type, ad.empty() ? nullptr : wad.c_str());``
        (``party_bindings.cpp:410-412``), so this answers a bool. Native's body is
        `_search_party`: the function resolved, the advertisement placed in the block as the wide
        string the client reads, and three words on the call — the type, that address, and native's
        own ``0``.
        """

        return _search_party(int(search_type), str(advertisement))

    @staticmethod
    def SearchPartyCancel() -> None:
        """``Party.SearchPartyCancel`` (``Party.py:352-358``) → ``GW::party::search_party_cancel``.

        ``unsigned ctx[13] = {0}; wparam[2] = 0x8;`` and the callback is called with ``edx = 0``
        (``party_methods.cpp:474-482``).
        """

        _press_party_button({}, {2: 0x8}, 0)

    @staticmethod
    def SearchPartyReply(accept: bool = True) -> bool:
        """``Party.SearchPartyReply`` (``Party.py:361-368``) → ``GW::party::search_party_reply``.

        ``ctx[0xb] = 0; ctx[8] = accept; wparam[1] = 0x3; wparam[2] = 0x6;`` (``party_methods.cpp:484-498``).
        **This one answers a bool** — Reforged's member is ``return ...SearchPartyReply(accept)``
        (``Party.py:368``) and native's body is ``false`` when the callback is not resolved, ``true``
        once it has been called — so the port returns the callback helper's own answer rather than
        discarding it, which is what ``SearchPartyCancel`` one line above it does with its own.
        """

        return _press_party_button(
            {0xB: 0, 8: 1 if accept else 0}, {1: 0x3, 2: 0x6}, 0
        )

    @staticmethod
    def RespondToPartyRequest(party_id: int, accept: bool) -> None:
        """``Party.RespondToPartyRequest`` (``Party.py:371-379``) → ``PyParty::RespondToPartyRequest``.

        **Native's body does nothing with either argument** — ``party_methods.cpp:194-198`` is
        ``(void)party_id; (void)accept; return true;`` — so there is nothing for this port to do
        either, and that is the source rather than a divergence. Reforged's member discards the
        return value as well.
        """

    @staticmethod
    def ReturnToOutpost() -> bool:
        """``Party.ReturnToOutpost`` (``Party.py:382-388``) → ``GW::party::return_to_outpost``.

        Native's whole body is one line (``party_methods.cpp:119-121``)::

            return ui::ButtonClick(ui::GetChildFrame(ui::GetFrameByLabel(L"DlgRedirect"), 0));

        Each step is the source's own member here, in the source's own order:

        | native | the port |
        | --- | --- |
        | ``ui::GetFrameByLabel(L"DlgRedirect")`` (``ui_methods.cpp:556-568``) | ``_FrameTree.by_label`` — the client hashes the label (``GetHashByLabel``, ``:542-546``) and the array is scanned for that hash |
        | ``ui::GetChildFrame(frame, 0)`` (``:444-449``) | ``Frame.child_native(0)`` — ``GetFrameById``'s validity test, then one ``U32_U32`` call to the client's own ``g_get_child_frame_id_func`` |
        | ``ui::ButtonClick(child)`` (``:1249-1274``) | ``Frame.click()`` |

        The value is native's: ``GetFrameByLabel`` answering nothing is ``ButtonClick(nullptr)`` —
        ``false`` — and a child that is not there is the same, because the port's ``Frame.click``
        refuses a frame that does not resolve exactly as ``ui::ButtonClick`` refuses a null one. What
        the click answers for a live button is ``ui::ButtonClick``'s own bool, which is the divergence
        recorded on that member in ``docs/FRAME_TREE_PORT.md``; Reforged's member returns the binding's
        value (``Party.py:388``), so this one answers a bool rather than nothing.
        """

        from .frame_tree.frame import FrameTree

        frame = FrameTree.by_label("DlgRedirect")
        if not frame.exists:
            return False
        return bool(frame.child_native(0).click())

    @staticmethod
    def LeaveParty() -> None:
        """``Party.LeaveParty`` (``Party.py:391-396``) → ``GW::party::leave_party``.

        Native's own guards and its own array: a party size of zero answers **without calling**
        (``if (!get_party_size()) return true;``), the context is fourteen words with ``ctx[0xd] = 1``,
        and the **window** callback is the one called — the measured bare-``ret`` one
        (``party_methods.cpp:200-211``).
        """

        if not Party.GetPartySize():
            return
        _press_party_button({0xD: 1}, {}, 0, window=True)

    class Players:
        """Reforged's ``Party.Players`` namespace."""

        @staticmethod
        def GetAgentIDByLoginNumber(login_number: int) -> int:
            """Return the agent id registered for a login number, or ``0``.

            Native's chain is ``PyParty::GetAgentIDByLoginNumber`` → ``agent::GetAgentIdByLoginNumber``
            → ``player::GetPlayerByID(login)->agent_id`` (``agent_methods.cpp:235-238``), and
            `_player_record` is that lookup — an **array index** with native's own
            ``if (!player_id) player_id = GetPlayerNumber();`` in front of it.

            **This member used to answer ``0`` for login ``0``, and round 7's live read is what showed
            it**: it went through ``WorldContextStruct.GetPlayerById``, which is Reforged's own helper
            (a search by ``player_number``), where the source indexes the array and maps a zero login to
            the caller's own player number. Live, login ``0`` answered ``0`` while
            ``GetPlayerNameByLoginNumber(0)`` answered the player's name — the two members disagreed
            about what zero means, and the name member was right.
            """

            record = _player_record(int(login_number))
            return int(record.agent_id) if record is not None else 0

        @staticmethod
        def GetPlayerNameByLoginNumber(login_number: int) -> str:
            """``Party.Players.GetPlayerNameByLoginNumber`` (``Party.py:410-419``) → the binding.

            The chain is ``PyParty::GetPlayerNameByLoginNumber`` → ``agent::GetPlayerNameByLoginNumber``
            → ``player::GetPlayerName`` → ``GetPlayerByID(login)->name`` (``player_methods.cpp:105-117``),
            and the binding then **narrows** it: every code unit below 128 is kept and everything else
            becomes ``'?'`` (``party_bindings.cpp:403-409``) — the name arrives as the client's own wide
            string and leaves as ASCII. Both steps are here, in that order, which is why a name with a
            non-ASCII character answers the question marks the source's binding produces rather than the
            character itself.

            Reforged decorates the member with ``@frame_cache``; this port drops the decorator and reads
            when it is called, for the reason `AGENTS.md` records for every cached member here.
            """

            name = _player_name(int(login_number))
            if not name:
                return ""
            return "".join(
                character if ord(character) < 128 else "?" for character in name
            )

        @staticmethod
        def GetPartyNumberFromLoginNumber(login_number: int) -> int:
            """Return a login number's index in the party, or ``-1``."""

            for index, member in enumerate(Party.GetPlayers()):
                if int(member.login_number) == int(login_number):
                    return index
            return -1

        @staticmethod
        def GetLoginNumberByAgentID(agent_id: int) -> int:
            """Return the login number whose agent id matches, or ``0``."""

            for member in Party.GetPlayers():
                if (
                    Party.Players.GetAgentIDByLoginNumber(int(member.login_number))
                    == int(agent_id)
                ):
                    return int(member.login_number)
            return 0

        @staticmethod
        def InvitePlayer(agent_id_or_name: object) -> None:
            """``Party.Players.InvitePlayer`` (``Party.py:455-470``): native by id, chat by name.

            Reforged's own two branches, and its own ``TypeError`` for anything else:

            * an ``int`` goes to the binding — ``GW::party::invite_player(player_id)``
              (``party_bindings.cpp:357``), which takes ``player::GetPlayerByID``'s record, requires its
              ``name``, formats ``L"invite %s"`` into a 32-unit buffer and sends it to the client on the
              command channel (``party_methods.cpp:299-315``);
            * a ``str`` is sent by the **caller**, through ``Player.SendChatCommand`` with
              ``"invite " + require_real_name(name)`` — the comment in the source says why: *"``/invite``
              needs the REAL name; name obfuscation shows aliases. Resolve it back."* The resolver is
              Reforged's own ``name_obfuscation.resolve``, ported beside this file; with the injected
              ``PyNameObfuscator`` unavailable (this port's case) its own fallback returns the name
              unchanged.
            """

            from .player import Player
            from .py4gwcorelib_src.system_settings.name_obfuscation.resolve import (
                require_real_name,
            )

            if isinstance(agent_id_or_name, int):
                record = _player_record(int(agent_id_or_name))
                if record is None or not record.name_encoded_str:
                    return
                _send_chat_command("invite " + record.name_encoded_str)
            elif isinstance(agent_id_or_name, str):
                Player.SendChatCommand("invite " + require_real_name(agent_id_or_name))
            else:
                raise TypeError(
                    "Invalid argument type. Must be int (ID) or str (name)."
                )

        @staticmethod
        def KickPlayer(login_number: int) -> None:
            """``Party.Players.KickPlayer`` (``Party.py:472-479``) → ``GW::party::kick_player``.

            ``kick_player(player_id)`` is ``invite_player``'s twin (``party_methods.cpp:292-297``):
            ``player::GetPlayerByID``'s record, its ``name`` required, ``L"kick %s"`` into a 32-unit
            buffer, and ``chat::SendChat('/', buf)``.
            """

            record = _player_record(int(login_number))
            if record is None or not record.name_encoded_str:
                return
            _send_chat_command("kick " + record.name_encoded_str)

    class Heroes:
        """Reforged's ``Party.Heroes`` namespace."""

        @staticmethod
        def GetHeroAgentIDByPartyPosition(hero_position: int) -> int:
            """Return a hero's agent id by party position.

            Native ``get_hero_agent_id``: position ``0`` is the controlled
            character, and ``1..n`` are one-based into the hero array.
            """

            if hero_position == 0:
                from .player import Player

                return Player.GetAgentID()
            heroes = Party.GetHeroes()
            index = hero_position - 1
            if index < 0 or index >= len(heroes):
                return 0
            return int(heroes[index].agent_id)

        @staticmethod
        def GetHeroIDByAgentID(agent_id: int) -> int | None:
            """Return a hero's id by agent id.

            The source returns nothing when no hero matches, which is ``None``
            here rather than a fabricated ``0``.
            """

            for hero in Party.GetHeroes():
                if int(hero.agent_id) == agent_id:
                    return int(hero.hero_id)
            return None

        @staticmethod
        def GetHeroIDByPartyPosition(hero_position: int) -> int | None:
            """Return a hero's id by party position, or ``None``."""

            for index, hero in enumerate(Party.GetHeroes()):
                if index == hero_position:
                    return int(hero.hero_id)
            return None

        @staticmethod
        def GetHeroIdByName(hero_name: str) -> int:
            """Return a hero's id by display name.

            ``Hero(name).GetID()`` resolves against the source's name table
            (``party_bindings.cpp:173``). An unknown name is ``HeroType.None_``.
            """

            hero = Hero(hero_name)
            return hero.GetID()

        @staticmethod
        def GetHeroNameById(hero_id: int) -> str:
            """Return a hero's display name by id.

            **Always empty.** ``Hero::GetName`` returns the ``hero_name`` member
            (``party_bindings.cpp:232``), and neither ``Hero`` constructor ever
            assigns it, so the source cannot produce a name here.
            """

            return Hero(hero_id).GetName()

        @staticmethod
        def GetNameByAgentID(agent_id: int) -> str:
            """Return a hero's display name by agent id.

            **Always empty**, for the same reason as
            :meth:`GetHeroNameById`: the name walk succeeds but the name it asks
            for is never populated.
            """

            for hero in Party.GetHeroes():
                if int(hero.agent_id) == agent_id:
                    return Hero(int(hero.hero_id)).GetName()
            return ""

        @staticmethod
        def GetHeroPartyPositionByAgentID(agent_id: int) -> int:
            """Return a hero's zero-based party position, or ``-1``."""

            for index, hero in enumerate(Party.GetHeroes()):
                if int(hero.agent_id) == agent_id:
                    return index
            return -1

        @staticmethod
        def GetTargetIDByAgentID(agent_id: int) -> int:
            """Return a hero's locked target id, or ``0``.

            The source first requires the agent to be a hero in the party, then
            walks ``world->hero_flags`` for its ``locked_target_id``.
            """

            if Party.Heroes.GetHeroPartyPositionByAgentID(agent_id) < 0:
                return 0
            world = Party._world()
            if world is None:
                return 0
            for hero_flag in world.hero_flags or []:
                if int(hero_flag.agent_id) == agent_id:
                    return int(hero_flag.locked_target_id)
            return 0

        @staticmethod
        def AddHero(hero_id: int) -> None:
            """``Party.Heroes.AddHero`` (``Party.py:602-608``) → ``GW::party::add_hero``.

            Native's own array and its own EDX: ``ctx[0xb] = 1; ctx[9] = hero_id; wparam[1] = 0x1;
            wparam[2] = 0x7;`` and the callback is called with ``edx = 2`` (``party_methods.cpp:213-227``)
            — the only member of this family that passes a second word in EDX.
            """

            _press_party_button({0xB: 1, 9: int(hero_id)}, {1: 0x1, 2: 0x7}, 2)

        @staticmethod
        def AddHeroByName(hero_name: str) -> None:
            """``Party.Heroes.AddHeroByName`` (``Party.py:611-618``): ``PyParty.Hero(name).GetID()``.

            The name resolves through the ported table (``Hero.GetID``), then the same call the id
            form makes — the source's own two lines.
            """

            Party.Heroes.AddHero(Hero(hero_name).GetID())

        @staticmethod
        def KickHero(hero_id: int) -> None:
            """``Party.Heroes.KickHero`` (``Party.py:621-627``) → ``GW::party::kick_hero``.

            ``ctx[0xb] = 1; ctx[ctx[0xb] + 8] = hero_id;`` — the index is the **value** at
            ``ctx[0xb]`` (1) plus eight, so it lands at ``ctx[9]``, the same slot ``add_hero`` writes
            (``party_methods.cpp:229-243``) — with ``wparam[1] = 0x6; wparam[2] = 0x7;`` and ``edx = 0``.
            """

            _press_party_button(
                {0xB: 1, 1 + 8: int(hero_id)}, {1: 0x6, 2: 0x7}, 0
            )

        @staticmethod
        def KickHeroByName(hero_name: str) -> None:
            """``Party.Heroes.KickHeroByName`` (``Party.py:630-637``)."""

            Party.Heroes.KickHero(Hero(hero_name).GetID())

        @staticmethod
        def KickAllHeroes() -> None:
            """``Party.Heroes.KickAllHeroes`` (``Party.py:640-645``) → ``kick_hero(0x26)``.

            Native's whole body is one call with the hero id ``0x26`` (``party_methods.cpp:245-247``),
            which is how the client's button spells "all heroes".
            """

            Party.Heroes.KickHero(0x26)

        @staticmethod
        def UseSkill(hero_agent_id: int, slot: int, target_id: int) -> None:
            """``Party.Heroes.UseSkill`` (``Party.py:647-656``) → ``PyParty::UseHeroSkill``.

            ``party_bindings.cpp:424-447``: the slot and the hero number are made zero-based, the hero
            number selects one of the seven ``ControlAction_Hero{N}Skill1`` bases (**a switch**, because
            the bases are not evenly spaced), the current target is remembered, and the enqueued body
            changes the target if one was asked for, presses ``base + slot - 1``, and restores the
            previous target. `_use_hero_skill` is that body.

            Reforged's member carries its own comment — *"``#return #function is not working atm``*" —
            above the call, so the source itself says the member has been reported as not working; the
            line is commented out and the call is what runs, so the port makes the same call. The
            argument is named ``hero_agent_id`` by Reforged and used as a **hero number** (``hero_id - 1``
            indexes the control-action switch) by the binding, the same kind of name-versus-meaning
            disagreement `FlagHero` carries.
            """

            _use_hero_skill(int(hero_agent_id), int(slot), int(target_id))

        @staticmethod
        def SetSkillAIEnabled(hero_agent_id: int, slot: int, enabled: bool) -> bool:
            """``Party.Heroes.SetSkillAIEnabled`` (``Party.py:658-667``) → ``set_hero_skill_ai_enabled``.

            Reforged's member **returns** the binding's value (``Party.py:667``) and Native's binding
            is ``return GW::party::set_hero_skill_ai_enabled(agent_id, slot, enabled);``
            (``party_bindings.cpp:448-450``), so this answers a bool. The body behind it — the four
            guards, the skillbar walk, the ``disabled`` bit and the zero-based slot — is
            `_set_hero_skill_ai_enabled`, in the source's own order.
            """

            return _set_hero_skill_ai_enabled(int(hero_agent_id), int(slot), bool(enabled))

        @staticmethod
        def FlagHero(hero_id: int, x: float, y: float) -> None:
            """``Party.Heroes.FlagHero`` (``Party.py:669-678``) → ``PyParty::FlagHero``.

            The binding is ``return GW::party::flag_hero_agent(static_cast<AgentID>(agent_id),
            GW::GamePos(x, y));`` (``party_bindings.cpp:359-361``), so the member's argument reaches
            ``flag_hero_agent`` as the **agent id** — the same name-versus-meaning disagreement the
            binding carries for `Players.IsPlayerTicked` and `UnflagHero` below: Reforged's parameter
            is called ``hero_id`` and Native's is called ``agent_id``, and Reforged passes it straight
            through. Kept as the sources have it.
            """

            _flag_hero_agent(int(hero_id), x, y)

        @staticmethod
        def FlagAllHeroes(x: float, y: float) -> None:
            """``Party.Heroes.FlagAllHeroes`` (``Party.py:680-688``) → ``flag_all(GamePos(x, y))``
            (``party_bindings.cpp:362``)."""

            _flag_all(x, y)

        @staticmethod
        def UnflagHero(hero_id: int) -> None:
            """``Party.Heroes.UnflagHero`` (``Party.py:690-697``) → ``PyParty::UnflagHero``.

            ``return GW::party::unflag_hero(agent_id);`` (``party_bindings.cpp:363``) and
            ``unflag_hero(hero_index)`` is ``flag_hero(hero_index, GamePos(HUGE_VALF, HUGE_VALF, 0))``
            (``party_methods.cpp:334-336``) — the position form, not the agent form, so the argument
            is resolved through ``agent::GetHeroAgentID`` on the way in. Same disagreement as
            `FlagHero`, in the other direction.
            """

            _flag_hero(int(hero_id), HUGE_VALF, HUGE_VALF)

        @staticmethod
        def UnflagAllHeroes() -> None:
            """``Party.Heroes.UnflagAllHeroes`` (``Party.py:699-705``) → ``unflag_all()``.

            ``return flag_all(GamePos(HUGE_VALF, HUGE_VALF, 0));`` (``party_methods.cpp:342-344``).
            """

            _flag_all(HUGE_VALF, HUGE_VALF)

        @staticmethod
        def IsHeroFlagged(hero_party_number: int) -> bool:
            """Return whether a hero is flagged.

            Native ``PyParty::IsHeroFlagged`` handles **only** position ``0``,
            where it reports whether the all-flag is set; every other position
            returns ``False``, because the source notes that per-hero flags are
            not reachable through the context it has. That limitation is the
            source's, not this port's.
            """

            if hero_party_number != 0:
                return False
            return Party.Heroes.IsAllFlagged()

        @staticmethod
        def IsAllFlagged() -> bool:
            """Return whether the all-flag is set.

            Native reads ``world->all_flag`` raw and treats a non-zero x or y as
            flagged, so this reads the same three floats directly rather than
            going through ``WorldContextStruct.all_flag``, which withholds
            non-finite values.

            **Finding:** Guild Wars stores an *unset* all-flag as
            ``(+inf, +inf, 0.0)``, and ``inf != 0.0``, so Native's own
            comparison reports ``True`` when nothing is flagged. This port
            reproduces that; it is the source's behaviour, not a read error. The
            flag position is the trustworthy signal - see :meth:`GetAllFlag`.
            """

            world = Party._world()
            if world is None:
                return False
            x = float(world.all_flag_array[0])
            y = float(world.all_flag_array[1])
            return x != 0.0 or y != 0.0

        @staticmethod
        def GetAllFlag() -> tuple[float, float]:
            """Return the all-flag position as ``(x, y)``.

            An unset flag reads back as ``(+inf, +inf)``, the value the game
            stores; ``(0.0, 0.0)`` is only returned when there is no world
            context to read.
            """

            world = Party._world()
            if world is None:
                return (0.0, 0.0)
            return (float(world.all_flag_array[0]), float(world.all_flag_array[1]))

        @staticmethod
        def SetHeroBehavior(hero_agent_id: int, behavior: int) -> None:
            """``Party.Heroes.SetHeroBehavior`` (``Party.py:736-744``) → ``PyParty::SetHeroBehavior``.

            ``GW::party::set_hero_behavior(agent_id, static_cast<GW::Constants::HeroBehavior>(behaviour))``
            (``party_bindings.cpp:416-418``), whose body is `_set_hero_behavior` — the world, the
            function and a non-empty ``hero_flags`` array, then the record's own ``hero_behavior``
            compared word for word. Reforged's member discards the binding's answer (it is ``void`` in
            Native), so this answers ``None``.
            """

            _set_hero_behavior(int(hero_agent_id), int(behavior))

    class Henchmen:
        """Reforged's ``Party.Henchmen`` namespace."""

        @staticmethod
        def AddHenchman(henchman_id: int) -> None:
            """``Party.Henchmen.AddHenchman`` (``Party.py:748-754``) → ``GW::party::add_henchman``.

            ``ctx[0xb] = 2; ctx[10] = henchman_id; wparam[1] = 0x2; wparam[2] = 0x7; edx = 0``
            (``party_methods.cpp:249-263``) — the tag in ``ctx[0xb]`` is what makes the client read
            ``ctx[10]`` rather than ``ctx[9]``.
            """

            _press_party_button({0xB: 2, 10: int(henchman_id)}, {1: 0x2, 2: 0x7}, 0)

        @staticmethod
        def KickHenchman(henchman_id: int) -> None:
            """``Party.Henchmen.KickHenchman`` (``Party.py:757-763``) → ``kick_henchman``.

            ``ctx[0xb] = 2; ctx[ctx[0xb] + 8] = henchman_id;`` — the value at ``ctx[0xb]`` (2) plus
            eight is ``ctx[10]``, the same slot the add writes (``party_methods.cpp:265-279``).
            """

            _press_party_button(
                {0xB: 2, 2 + 8: int(henchman_id)}, {1: 0x6, 2: 0x7}, 0
            )

    class Pets:
        """Reforged's ``Party.Pets`` namespace."""

        @staticmethod
        def _pet_info(owner_id: int) -> PetInfoStruct | None:
            """Return the world pet record for an owner, or ``None``.

            Native ``get_pet_info`` walks ``world->pets`` for a matching
            ``owner_agent_id``, and treats owner ``0`` as the controlled
            character.
            """

            world = Party._world()
            if world is None:
                return None
            if owner_id == 0:
                from .player import Player

                owner_id = Player.GetAgentID()
            for pet in world.pets or []:
                if int(pet.owner_agent_id) == owner_id:
                    return pet
            return None

        @staticmethod
        def SetPetBehavior(behavior: int, lock_target_id: int) -> None:
            """``Party.Pets.SetPetBehavior`` (``Party.py:766-774``) → ``PyParty::SetPetBehaviour``.

            ``GW::party::set_pet_behavior(static_cast<GW::Constants::HeroBehavior>(behaviour),
            lock_target_id)`` (``party_bindings.cpp:419-421``), whose body is `_set_pet_behavior`: the
            controlled character's own pet, a target only for the **Fight** behaviour, and that target
            required to be a living **enemy** before either the lock or the behaviour is written.
            Reforged's member discards the binding's answer (``void`` in Native), so this answers
            ``None``.
            """

            _set_pet_behavior(int(behavior), int(lock_target_id))

        @staticmethod
        def GetPetBehavior(owner_id: int) -> int:
            """Return a pet's behavior, or ``0`` when it has none."""

            return int(Party.Pets.GetPetInfo(owner_id).behavior)

        @staticmethod
        def GetPetInfo(owner_id: int) -> PetInfoStruct:
            """Return the pet record for an owner.

            Native returns the record by value with every field zeroed when the
            owner has no pet, so an absent pet is a zeroed record rather than a
            missing one.
            """

            return Party.Pets._pet_info(owner_id) or PetInfoStruct()

        @staticmethod
        def GetPetID(owner_id: int) -> int:
            """Return a pet's agent id, or ``0`` when it has none."""

            return int(Party.Pets.GetPetInfo(owner_id).agent_id)



# ── pending Reforged members, recorded rather than faked ──────────────────
#
# None. Every member of Reforged's ``Party``, ``Party.Players``,
# ``Party.Heroes``, ``Party.Henchmen`` and ``Party.Pets`` is present: the ones
# that read a context are implemented, and the actions raise
# ``NotImplementedError`` naming the mechanism they would need.
#
# Two members return a documented constant because the source's own
# implementation can only produce that constant:
#   Party.GetOthers            -- native PyParty::others is never populated
#   Heroes.GetHeroNameById,
#   Heroes.GetNameByAgentID    -- Hero::GetName reads a field no constructor sets
#
# Two members are limited by the source rather than by this port:
#   Heroes.IsHeroFlagged       -- native handles position 0 only, False otherwise
#   Players.IsPlayerTicked     -- native treats its argument as an array index
#
# ``Frame``-based helpers are deferred with the frame-tree work in ``py4gw/ui``.
