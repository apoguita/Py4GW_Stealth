"""``GwAu3_Data_Account.au3``'s readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map`'s instance and
character-info readers use: ``data_account.py`` is rewritten whole on every run, and this file is
emitted verbatim into it.

**What the file carries.** The account family is two readers a script calls and one that is plumbing:

* ``Account_GetAccountInfo`` (``GwAu3_Data_Account.au3:8-31``) is the **generated accessor's**, because
  every one of its cases is a field read at a fixed offset. GwAu3 resolves the record with
  ``World_GetWorldInfo("AccountInfo")`` (``:9``), guards ``If $l_p_Ptr = 0 Or $a_s_Info = "" Then
  Return 0`` (``:10``), and reads ``wchar[32]`` through the name pointer at ``+0x0`` (``:13-15``) or a
  dword at ``+0x4``/``+0x8``/``+0xC``/``+0x10``/``+0x14``/``+0x18`` (``:16-27``), falling through to
  ``Return 0`` (``:30``).

  This project reads the **same record** as `AccountInfoStruct`
  (`py4gw/context/world_context.py:140`, its size asserted at ``0x1C``, `:2062`) through the same world
  context field -- `WorldContextStruct.account_info` (``:1651``), which follows ``account_info_ptr``
  (``:1452``) -- and the port's seven fields are GwAu3's own seven in GwAu3's own order:
  ``account_name_ptr`` at ``+0x0``, ``wins`` at ``+0x4``, ``losses`` at ``+0x8``, ``rating`` at
  ``+0xC``, ``qualifier_points`` at ``+0x10``, ``rank`` at ``+0x14``, ``tournament_reward_points`` at
  ``+0x18`` (`:145-151`). The offset table therefore resolves all seven keys, and six of them are the
  port's own named attribute.

* ``Account_IsSkillUnlocked`` (``:33-52``) is this file's own function, below.

* ``Account_GetAccountContextPtr`` (``:4-6``) is carried below, and its body is GwAu3's own:
  ``Return Game_GetGameInfo("AccountContext")`` (``:5``). GwAu3's answer is the account context's
  *client address*; this layer hands out no address, and `Game_GetGameInfo`'s ``AccountContext`` key
  already answers **the record** that address holds, so the member answers the record -- or ``0``,
  which is GwAu3's own answer for the null context pointer.

**The one key whose answer is written out rather than offset-resolved is ``AccountName``.** GwAu3
reads a *pointer* at ``+0x0`` and then the wide string at the address it points at (``:14-15``), so an
offset-resolved reader would hand a caller the client address itself -- which this layer never
returns. The family spec declares the key in ``pointer_reads`` as `Player.GetAccountName`
(`py4gw/player.py:573`), the port's own read of that same field and the form a caller can use; GwAu3
returns the raw thirty-two-wide-character buffer where this returns the name as a string (``""``
where GwAu3's buffer would be empty).

**The family spec that carries this file**, recorded here because this file is what the generated
module's hand-written half is:

* ``module="data_account"``, ``structure=("context.world_context", "AccountInfoStruct")``,
  ``record_call="_account_info(client.read_world_context())"`` and ``record_arg=""`` -- GwAu3's own
  signature is ``Func Account_GetAccountInfo($a_s_Info = "")`` (``:8``), the field name and nothing
  else, exactly like ``World_GetWorldInfo``;
* ``extra_exports=("Account_GetAccountContextPtr", "Account_IsSkillUnlocked")`` and
  ``helper_files=("data_account_info.py",)``;
* ``pointer_reads={"AccountName": "Player.GetAccountName()"}`` with
  ``extra_imports=("from ..player import Player", "from .data_game import Game_GetGameInfo")``.
"""


def Account_GetAccountContextPtr() -> Any:
    """The account context record (``GwAu3_Data_Account.au3:4-6``).

    GwAu3's whole body is ``Return Game_GetGameInfo("AccountContext")`` (`:5`), and that is this
    member's body as well -- which is what makes it a one-line divergence rather than a new route:
    `Game_GetGameInfo` answers **the record** its ``AccountContext`` key names
    (`py4gw/gwa3/data_game.py:185`, read through `client.read_account_context`, ``py4gw/client.py:1671``)
    rather than the client address it resolves from, so this answers `AccountContextStruct`
    (`py4gw/context/account_context.py:61`, read on demand by `AccountContext.read`, `:227`) -- the
    record `Account_IsSkillUnlocked` reads its unlocked-skill words from (`:185`). ``0`` when the slot
    holds no pointer, which is GwAu3's own answer for a null context pointer.

    **The divergence, in one sentence:** GwAu3 hands the caller a client address and this hands back the
    record that address holds, the same substitution `World_GetWorldContextPtr`
    (`py4gw/gwa3/data_world.py:429`) and `Agent_GetAgentPtr` record.
    """

    return Game_GetGameInfo("AccountContext")


def _account_info(world: Any) -> Any:
    """The account-summary record GwAu3 resolves before its ``Switch``, or ``None``.

    GwAu3's first line is ``Local $l_p_Ptr = World_GetWorldInfo("AccountInfo")``
    (``GwAu3_Data_Account.au3:9``), and its second answers ``0`` when that pointer is ``0`` (``:10``).
    This is that pair over the port's own reader: `WorldContextStruct.account_info`
    (`py4gw/context/world_context.py:1651`) answers `AccountInfoStruct`, or ``None`` when the client
    holds no world context or no plausible pointer -- and ``None`` is what the generated accessor's own
    missing-record guard turns into GwAu3's ``0``.
    """

    if world is None:
        return None
    return world.account_info


def Account_IsSkillUnlocked(skill_id: Any) -> bool:
    """Whether the account has a skill unlocked (``GwAu3_Data_Account.au3:33-52``).

    GwAu3's own sequence, in GwAu3's own order, over this project's readers: it resolves the account
    context (``:34``) and answers ``False`` when there is none (``:35``); then it takes the
    unlocked-skills array at ``+0x124`` (``:37``), answers ``False`` for a zero array pointer (``:38``),
    forms ``Floor($a_i_SkillID / 32)`` as the word index (``:42``) and answers ``False`` when that index
    is past the array's advertised size (``:44``), and finally tests
    ``BitAND($word, 1 << Mod($a_i_SkillID, 32)) <> 0`` (``:46-51``).

    That whole walk is this port's own member: `AccountContextStruct.is_account_skill_unlocked`
    (`py4gw/context/account_context.py:185`) forms the same ``// 32`` index against
    ``unlocked_account_skill_words`` (``:160``) -- the same array, whose ``0x124`` offset is asserted at
    ``:204`` -- and makes the same single-bit test, answering ``False`` for an array it cannot read,
    which is GwAu3's ``$l_p_UnlockedSkillsArray = 0`` guard (``:38``). The context itself comes from
    the port's reader, `RemoteClient.read_account_context` (`py4gw/client.py:1671`), and its ``None``
    is GwAu3's zero context (``:35``).

    **One divergence, in the guard rather than the answer**: a negative skill id is answered ``False``
    here before anything is read, where GwAu3's arithmetic forms a negative index and reads the word
    before the array -- its flag is zero there, so both answer ``False``, but only one reads.
    """

    account_context = require_client().read_account_context()
    if account_context is None:
        return False
    return bool(account_context.is_account_skill_unlocked(int(skill_id)))
