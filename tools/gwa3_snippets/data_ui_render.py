"""``GwAu3_Data_Ui.au3``'s two rendering readers: **NOT APPLICABLE**, and the whole module says why.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; this file reproduces the two names and refuses both, because what they
read does not exist in this project.

**Hand-written, not generated, and the reason is the shape of its source file.** The family generator
(`tools/generate_gwa3_family.py`) builds one module per source file whose accessor is a ``Switch`` over
one record's offsets; it requires a ``structure`` and a ``record_call`` for every family. This source
file has neither -- two functions, no arguments, no record and no ``Switch`` -- so a ``Family(...)``
entry for it would have to name a structure GwAu3 does not read, which the cornerstones forbid. It is
kept by hand like ``data_game.py`` and ``data_effect.py``, and its source of record is
``tools/gwa3_snippets/data_ui_render.py``, so the wording exists in one place.

**What they read.** Both functions are one line (``GwAu3_Data_Ui.au3:4-6`` and ``:9-11``): a
``Memory_Read`` of ``$g_b_DisableRendering`` compared to ``1`` and to ``0``. That global is **a 4-byte
slot inside GwAu3's own injected code block**, not a client field:

* it is declared ``Global $g_b_DisableRendering`` in the constant file (``GwAu3_Const_Game.au3:7``);
* the block declares the slot ``_('DisableRendering/4')`` (``GwAu3_Core_Assembler.au3:1920``) and
  GwAu3 binds the AutoIt variable to it at startup (``GwAu3_Core.au3:443``);
* the injected code reads it on the game's own thread inside the block's ``RenderingMod`` detour
  (``GwAu3_Core_Assembler.au3:2056-2061``: ``cmp dword[DisableRendering],1`` then a jump back into the
  original branch), which is the whole of the mechanism -- disabling rendering there means *the
  client's own render-modification branch is made to take the other side*;
* the two writers are members of the same layer: ``Ui_EnableRendering`` writes ``0``
  (``GwAu3_Cmd_Ui.au3:237``) and ``Ui_DisableRendering`` writes ``1`` (``:243``), each after testing
  these very readers (``:236``, ``:242``).

**Why nothing here can answer it, and what was checked.** This project installs no ``RenderingMod``
detour and holds no such slot: connecting installs the capability layer described in ``AGENTS.md`` --
hooks on the game thread and the message sender, a shared block and a dispatcher -- and none of it
touches rendering. **The render-side access this project does have was looked for and it is not this
fact**: one capture hook on the client's ``EndScene`` keeps that call's first argument, the DX context
(`py4gw/game_thread/bridge.py:637`, ``:403-407``), which this project reads as `GwDxContextStruct`
(``py4gw/context/render_context.py:11-37``) -- a record of geometry and per-frame counters
(``viewport_width``/``viewport_height``, ``window_width``/``window_height``, ``framecount``, ``device``,
``gpu_name``) with **no render-disable state in it**; and a capture is not the detour GwAu3's flag needs
in any case, because GwAu3's ``RenderingMod`` stub makes the client's own render-modification branch
take the other side (`GwAu3_Core_Assembler.au3:2056-2061`) and nothing here does that. No client-side
field behind the flag was found either, which is the test this layer applies before it writes a
Pythonic equivalent: the flag's *entire* meaning is the injected block's own state, so answering
``False`` from a controller-side variable of this project's own would be a wrong value of the right type
-- and it would stay ``False`` forever, because the members that would set it refuse for the same reason
(`py4gw/gwa3/cmd_ui.py:382-421`: ``Ui_EnableRendering``, ``Ui_DisableRendering``, ``Ui_ToggleRendering``,
``Ui_PurgeHook`` and their two trailing-underscore twins). ``docs/GWA3_ROUTE_MAP.md`` records both rows
as NOT APPLICABLE for the same reason.

So both members raise, naming the capability that is missing. **What answers the same question here:
nothing** -- and that is the honest answer rather than a stand-in. A caller that wants the game not to
render has no route in this project today; the work, if it is ever wanted, is a render-skip mechanism in
``py4gw/game_thread/`` plus the block slot to hold its flag.
"""

from __future__ import annotations

from typing import NoReturn

__all__ = ["Ui_GetRenderDisabled", "Ui_GetRenderEnabled"]

#: The one rule both members refuse by: what the flag is, where it lives, why no equivalent exists, and
#: what this project's render-side access actually is.
#:
#: Written once because it is one mechanism, not two -- the two functions are the same read compared
#: against two different constants.
_BLOCK_RULE = (
    "reads `$g_b_DisableRendering`, a 4-byte slot in **GwAu3's own injected code block** "
    "(`GwAu3_Core_Assembler.au3:1920`, bound at `GwAu3_Core.au3:443`) which that block's `RenderingMod` "
    "detour tests on the game's thread (`GwAu3_Core_Assembler.au3:2056-2061`) and which "
    "`Ui_DisableRendering`/`Ui_EnableRendering` write (`GwAu3_Cmd_Ui.au3:237`, `:243`). This project "
    "installs no rendering detour and holds no such slot, and the only render-side access it has -- the "
    "`EndScene` capture of the DX context (`py4gw/game_thread/bridge.py:637`, read as "
    "`GwDxContextStruct` in `py4gw/context/render_context.py:11-37`) -- is a record of geometry and "
    "frame counters with no render-disable state in it, so the answer is **NOT APPLICABLE** and this "
    "raises rather than reporting a state it does not have. Nothing in this project answers the same "
    "question; the members that would set the flag refuse for the same reason "
    "(`py4gw/gwa3/cmd_ui.py:382-421`)."
)


def _refuse(line: int) -> NoReturn:
    """Raise the module's one rule, with GwAu3's own line for the member that hit it."""

    raise NotImplementedError(f"GwAu3_Data_Ui.au3:{line} {_BLOCK_RULE}")


def Ui_GetRenderDisabled() -> bool:
    """**NOT APPLICABLE: GwAu3's own injected-block flag.** ``GwAu3_Data_Ui.au3:4-6``.

    GwAu3 answers ``Memory_Read($g_b_DisableRendering) = 1``. See the module docstring for what that
    slot is, what this project's render-side access turned out to be (the ``EndScene`` capture of the DX
    context -- geometry and frame counters, no disable state), and why this project therefore cannot
    report the flag; it is written by ``Ui_DisableRendering`` (``GwAu3_Cmd_Ui.au3:243``) and read on the
    game's thread by the block's ``RenderingMod`` detour (``GwAu3_Core_Assembler.au3:2056-2061``).
    """

    _refuse(5)


def Ui_GetRenderEnabled() -> bool:
    """**NOT APPLICABLE: GwAu3's own injected-block flag.** ``GwAu3_Data_Ui.au3:9-11``.

    GwAu3 answers ``Memory_Read($g_b_DisableRendering) = 0`` -- the same word, the other comparison. See
    the module docstring, including the check that found no client-side render state to answer it from;
    the flag is written by ``Ui_EnableRendering`` (``GwAu3_Cmd_Ui.au3:237``).
    """

    _refuse(10)
