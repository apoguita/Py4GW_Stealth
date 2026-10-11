"""``GwAu3_Data_Agent.au3``'s **array, effects-block, bond, NPC and player** readers, hand-written
into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_agent_effect_info.py`
uses: ``data_agent.py`` is rewritten whole on every run, and this file is emitted verbatim into it
immediately before its ``__all__``.

**What the file carries, in the source's own order** (``GwAu3_Data_Agent.au3``):

* ``Agent_GetAgentArray`` (``:707-735``) -- the agent array GwAu3 fills from the client's pointer
  buffer, read here from this project's own agent array as **ids**, in GwAu3's own count-prefixed
  shape;
* ``Agent_GetAgentEffectArrayInfo`` (``:834-865``) -- one column of an agent's effects block in the
  world's agent-effects array, read here from the same array through this project's own records;
* ``Agent_GetAgentBondInfo`` (``:914-957``) -- one column of a bond in that block's bond sub-array;
* ``Agent_GetNpcInfo`` (``:963-1007``) -- one field of an NPC table entry, by index;
* ``Agent_GetPlayerInfo`` (``:1019-1069``) -- one field of a player array entry, by agent id;
* ``Agent_GetBestTarget`` (``:1096-1119``) -- GwAu3's own scoring loop over the living-agent array.

**Every record is this project's own and every offset lines up**, which is why this file is a read of
the same client data rather than a re-invention of it:

* the **agent-effects array** GwAu3 reaches at ``BasePointer[0x18][0x2C][0x508]`` is
  `WorldContextStruct.party_effects` (``py4gw/context/world_context.py:1801``) over
  ``party_effects_array``, and each block is `AgentEffectsStruct`
  (``py4gw/context/world_context.py:356``) -- ``0x24`` bytes, ``agent_id`` at ``+0x0``, the bond
  sub-array header at ``+0x4`` and the effect sub-array header at ``+0x14``, which are the four
  offsets GwAu3 reads at ``:852-861``;
* its bond records are `BuffStruct` (``py4gw/context/world_context.py:344``, ``0x10`` bytes) and its
  effect records `EffectStruct` (``:324``, ``0x18``) -- GwAu3's own two strides (``:927``, ``:875``);
* the **NPC array** at ``+0x7FC`` is `WorldContextStruct.npc_models` (``:1813``) over `NPCStruct`
  (``:494``, ``0x30`` bytes, the source's own stride at ``:969``): ``model_file_id`` at ``+0x0``,
  ``scale`` ``+0x8``, ``sex`` ``+0xC``, ``npc_flags`` ``+0x10``, ``primary`` ``+0x14``,
  ``default_level`` ``+0x1C``, ``name_enc_ptr`` ``+0x20``;
* the **player array** at ``+0x80C`` is `WorldContextStruct.players` (``:1819``) over `PlayerStruct`
  (``:616``, ``0x50`` bytes, the source's own stride at ``:1025``) -- every field GwAu3 reads at
  ``:1036-1065`` is a named field of it.

**No client address is ever an answer.** Four of GwAu3's cases return one -- the agent array's slots,
``BondArray`` and ``EffectArray``, and `Agent_GetAgentBondInfo`'s empty-column answer -- and each of
them answers the id, the record, or the list of records instead, with the divergence written on the
member that makes it.

**The family spec that carries this file**, recorded here because this file is what the generated
module's hand-written half is: ``extra_exports`` gains the six names below and ``helper_files`` gains
``("data_agent_npc_player_info.py",)``. No ``extra_imports`` are needed: every import this file makes
is local to the function that needs it (`from ..client import require_client`,
`from ..ui_manager import UIManager`), because the generated module's head imports neither and this
file is emitted verbatim.
"""


def Agent_GetAgentArray(a_i_Type: Any = 0) -> list[int]:
    """The client's agent array, optionally filtered by agent type (``GwAu3_Data_Agent.au3:707-735``).

    GwAu3's steps, kept: it takes the array's capacity (``:708``); answers a one-element array holding
    the count ``0`` when there is nothing to walk (``:709-710``); reads the client's pointer buffer and
    **skips every null slot** (``:714-721``); skips a slot whose ``Type`` is not the one asked for when
    a type was asked for (``:723-725``); and answers an array whose element ``0`` is the count and whose
    elements ``1..count`` are the agents (``:727-734``).

    **The slots hold ids, not addresses.** GwAu3 stores the pointer it read for each slot; this answers
    the agent **id**, because a client address is of no use to a caller here -- the same substitution
    `Agent_GetAgentPtr` records, and a migrating script passes the result straight back into another
    ``Agent_*`` function, which resolves it either way. The **shape is kept**: element ``0`` is the
    count and ``[0]`` alone is the empty answer, which is what `Party_GetMembersArray` keeps for its own
    AutoIt array (``py4gw/gwa3/uai_utils.py:408``) and what a caller like `Agent_GetBestTarget` indexes.

    The array itself is this project's own read: `AgentArray.GetAgentArray` (``py4gw/agent_array.py:43``),
    which traverses the client's array on demand and holds the ids of the populated slots -- so GwAu3's
    capacity read and its null-slot skip are already the array this member is handed.
    """

    agent_ids = AgentArray.GetAgentArray()
    if not agent_ids:
        return [0]

    agent_array: list[int] = [0]
    count = 0

    for agent_id in agent_ids:
        if a_i_Type != 0:
            if Agent_GetAgentInfo(agent_id, "Type") != a_i_Type:
                continue

        count += 1
        agent_array.append(int(agent_id))

    agent_array[0] = count
    return agent_array


def Agent_GetAgentEffectArrayInfo(a_i_AgentID: Any = -2, a_s_Info: Any = "") -> Any:
    """One column of an agent's effects block (``GwAu3_Data_Agent.au3:834-865``).

    GwAu3's steps, kept: it walks the world's agent-effects array in ``0x24`` strides and stops at the
    block whose first dword is ``Agent_ConvertID($a_i_AgentID)`` (``:839-847``); answers ``0`` when no
    block matched or no column was asked for (``:849``); and otherwise switches on the column name
    (``:851-864``), answering ``0`` for anything else (``:862-863``).

    The block is `AgentEffectsStruct` (``py4gw/context/world_context.py:356``), so each column is the
    same field GwAu3 reads: ``AgentID`` is ``agent_id`` at ``+0x0`` (``:852-853``), ``BondArraySize``
    is the bond sub-array header's own ``m_size`` at ``+0xC`` and ``EffectArraySize`` the effect
    header's at ``+0x1C`` (``:856-857``, ``:860-861``).

    **The two pointer columns answer the records the sub-array holds.** GwAu3 answers
    ``BondArray``/``EffectArray`` as a client address (``:854-855``, ``:858-859``); this answers the
    sub-array's records -- `BuffStruct` list and `EffectStruct` list, read through the block's own
    `buffs`/`effects` (``py4gw/context/world_context.py:393``, ``:403``), which are the same two record
    sets `py4gw.effect.get_effects`/`get_buffs` read (``py4gw/effect.py:100-137``) and the ones
    `Agent_GetAgentBondInfo` walks.
    """

    from ..client import require_client

    world = require_client().read_world_context()
    blocks = [] if world is None else list(world.party_effects or [])

    agent_id = Agent_ConvertID(a_i_AgentID)

    record = None
    for block in blocks:
        if int(block.agent_id) == agent_id:
            record = block
            break

    if record is None or a_s_Info == "":
        return 0

    if a_s_Info == "AgentID":
        return int(record.agent_id)
    if a_s_Info == "BondArray":
        return list(record.buffs)
    if a_s_Info == "BondArraySize":
        return int(record.buff_array.m_size)
    if a_s_Info == "EffectArray":
        return list(record.effects)
    if a_s_Info == "EffectArraySize":
        return int(record.effect_array.m_size)

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetAgentBondInfo(
    a_i_AgentID: Any = -2, a_i_SkillID: Any = 0, a_i_TargetID: Any = 0, a_s_Info: Any = ""
) -> Any:
    """One column of a bond on an agent (``GwAu3_Data_Agent.au3:914-957``).

    GwAu3's steps, kept in its own order: it takes the agent's bond array and its size
    (``:915-916``); answers ``0`` for a zero array or an empty one (``:918``); resolves the target id
    through ``Agent_ConvertID`` **only when a target was given** (``:921-924``); walks the array in
    ``0x10`` strides, skipping a record whose skill differs and -- when a target was given -- one whose
    ``+0xC`` differs from it, and stops at the first match (``:926-938``); answers ``0`` when nothing
    matched (``:940``); answers the record when no column was asked for (``:941``); and otherwise
    switches on the column name (``:943-956``), answering ``0`` for anything else (``:954-955``).

    Every column is the port's own field of the same record -- `BuffStruct`
    (``py4gw/context/world_context.py:344``), whose four dwords are the source's four offsets:
    ``h0004`` at ``+0x4`` (``:946-947``), ``BondID`` at ``+0x8`` (``:948-949``) and ``TargetAgentID``
    at ``+0xC`` (``:950-951``), which is also the word the target was compared against.
    ``HasBond`` answers ``True`` once a record matched (``:952-953``), because that is what having
    found one means.

    **The empty-column answer is a record, not a pointer**: ``:941`` answers ``$l_p_BondPtr``, a client
    address, and this answers the `BuffStruct` the walk stopped at -- the same divergence
    `Agent_GetAgentEffectInfo` records for its own empty column.
    """

    bond_array = Agent_GetAgentEffectArrayInfo(a_i_AgentID, "BondArray")
    bond_count = Agent_GetAgentEffectArrayInfo(a_i_AgentID, "BondArraySize")

    if not bond_array or not bond_count:
        return 0

    bond_record = None
    check_target = a_i_TargetID != 0
    target_id = 0

    if check_target:
        target_id = Agent_ConvertID(a_i_TargetID)

    for record in bond_array:
        if int(record.skill_id) != int(a_i_SkillID):
            continue

        if check_target:
            if int(record.target_agent_id) != target_id:
                continue

        bond_record = record
        break

    if bond_record is None:
        return 0
    if a_s_Info == "":
        return bond_record

    if a_s_Info == "h0004":
        return int(bond_record.h0004)
    if a_s_Info == "BondID":
        return int(bond_record.buff_id)
    if a_s_Info == "TargetAgentID":
        return int(bond_record.target_agent_id)
    if a_s_Info == "HasBond":
        return True

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetNpcInfo(a_i_NpcIndex: Any = 0, a_s_Info: Any = "") -> Any:
    """One field of an NPC table entry, by index (``GwAu3_Data_Agent.au3:963-1007``).

    GwAu3's steps, kept: it takes the NPC array and its size (``:964-965``) and answers ``0`` for a
    zero pointer, an empty array or an empty field name (``:966``); answers ``0`` for an index at or
    below ``0``, or at or past the array's size (``:967``); and then switches on the field name over the
    entry at ``index * 0x30`` (``:969-1006``), answering ``0`` for anything else (``:1004-1005``). Its
    own comment names the index: *"Player number of an npc"* (``:961``), which is the index this
    project's `Agent.GetNPCFlags` passes to its NPC-model reader too (``py4gw/agent.py:1975``).

    The entry is `NPCStruct` (``py4gw/context/world_context.py:494``), so each field is the port's own
    name at the source's own offset: ``ModelFileID`` ``+0x0`` (``:972-973``), ``Scale`` ``+0x8``
    (``:974-975``), ``Sex`` ``+0xC`` (``:976-977``), ``NpcFlags`` ``+0x10`` (``:978-979``),
    ``Primary`` ``+0x14`` (``:980-981``) and ``DefaultLevel``/``Level`` the byte at ``+0x1C``
    (``:982-983``). The four flag questions are the record's own members, each the same mask GwAu3
    applies: `is_henchman` ``0x10`` (``:984-986``), `is_hero` ``0x20`` (``:987-989``), `is_spirit`
    ``0x4000`` (``:990-992``) and `is_minion` ``0x100`` (``:993-995``).

    ``Level`` is answered from the byte too, because **AutoIt's ``Switch`` runs the first matching
    ``Case``** and ``:982`` matches ``"Level"`` before the dword case at ``:996-997`` does; that second
    case is unreachable in GwAu3 and stays unreachable here.

    The two name fields are the port's own members for the same two GwAu3 utils, over the same pointer
    at ``+0x20`` (`NPC_ModelStruct.name_encoded_str`, ``py4gw/context/world_context.py:568``):
    ``NameEnc`` is ``Utils_DecodeEncString`` (``GwAu3_Core_Utils.au3:440-462``), which decodes the
    encoded name to its **string id** -- answered here by `UIManager.EncStrToUInt32`
    (``py4gw/ui_manager.py:760``), the ported ``GW::ui::EncStrToUInt32`` -- with that util's own
    zero-pointer answer ``0`` (``:441``); and ``Name`` is ``Utils_DecodeEncStringAsync``
    (``:469-498``), which hands the encoded name to the client's decoder and answers the text, kept here
    by `UIManager.AsyncDecodeStr` (``py4gw/ui_manager.py:672``), the ported ``GW::ui::AsyncDecodeStr``,
    with that util's own zero-pointer answer ``""`` (``:470``).
    """

    from ..client import require_client
    from ..ui_manager import UIManager

    world = require_client().read_world_context()
    models = [] if world is None else list(world.npc_models or [])

    if not models or a_s_Info == "":
        return 0

    npc_index = int(a_i_NpcIndex)
    if npc_index <= 0 or npc_index >= len(models):
        return 0

    record = models[npc_index]

    if a_s_Info == "ModelFileID":
        return int(record.model_file_id)
    if a_s_Info == "Scale":
        return int(record.scale)
    if a_s_Info == "Sex":
        return int(record.sex)
    if a_s_Info == "NpcFlags":
        return int(record.npc_flags)
    if a_s_Info == "Primary":
        return int(record.primary)
    if a_s_Info == "DefaultLevel" or a_s_Info == "Level":
        return int(record.default_level)
    if a_s_Info == "IsHenchman":
        return bool(record.is_henchman)
    if a_s_Info == "IsHero":
        return bool(record.is_hero)
    if a_s_Info == "IsSpirit":
        return bool(record.is_spirit)
    if a_s_Info == "IsMinion":
        return bool(record.is_minion)
    if a_s_Info == "NameEnc":
        encoded = record.name_encoded_str
        if encoded is None:
            return 0
        return int(UIManager.EncStrToUInt32(encoded))
    if a_s_Info == "Name":
        encoded = record.name_encoded_str
        if encoded is None:
            return ""
        return str(UIManager.AsyncDecodeStr(encoded))

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetPlayerInfo(a_i_AgentID: Any = 0, a_s_Info: Any = "") -> Any:
    """One field of a player array entry, by agent id (``GwAu3_Data_Agent.au3:1019-1069``).

    GwAu3's steps, kept: it walks the player array from index ``1`` to its size (``:1024-1030``) --
    ``:1024`` starts past the array's own first slot -- comparing each entry's first dword with
    ``Agent_ConvertID($a_i_AgentID)``; answers ``0`` when no entry matched (``:1032``); and then switches
    on the field name (``:1034-1068``), answering ``0`` for anything else (``:1066-1067``).

    **There is no empty-field guard in this function**, unlike its neighbours, and none is added: an
    empty field name falls through GwAu3's own ``Case Else`` to ``0``.

    The entry is `PlayerStruct` (``py4gw/context/world_context.py:616``, ``0x50`` bytes), so each field
    is the port's own name at the source's own offset: ``AgentID`` ``+0x0`` (``:1035-1036``),
    ``AppearanceBitmap`` ``+0x10`` (``:1037-1038``), ``Flags`` ``+0x14`` (``:1039-1040``), ``Primary``
    ``+0x18`` (``:1041-1042``), ``Secondary`` ``+0x1C`` (``:1043-1044``),
    ``PartyLeaderPlayerNumber`` ``+0x2C`` (``:1048-1049``), ``ActiveTitle`` ``+0x30`` (``:1050-1051``),
    ``ActiveChallenge`` ``+0x34`` (``:1053-1054``), ``PlayerNumber`` ``+0x38`` (``:1062-1063``) and
    ``PartySize`` ``+0x3C`` (``:1064-1065``). The three flag questions are the record's own members over
    the same word: `is_melandrus_accord` (``:1055-1056``), `is_dhuums_covenant` (``:1057-1058``) and
    `is_reforged` (``:1059-1060``).

    **One disagreement between those three bits is recorded rather than smoothed over.** GwAu3 masks
    ``0x1`` for Melandru's Accord and ``0x2`` for Dhuum's Covenant; this project's two members of those
    names mask ``0x2`` and ``0x1`` respectively (``py4gw/context/world_context.py:655-664``), so each
    key answers the port's own member of its name and the bit disagreement is a finding a live read
    would settle. ``ActiveChallenge``'s word is the port's `reforged_or_dhuums_flags` under a different
    name, the same offset ``+0x34``.

    ``Name`` is a string either way: GwAu3 reads a fixed ``wchar[20]`` at the pointer in ``+0x28``
    (``:1045-1047``) and this answers the port's own bounded read of that same pointer,
    `PlayerStruct.name_encoded_str` (``py4gw/context/world_context.py:685``) -- the display name, read
    to its terminator instead of to twenty wide characters.
    """

    from ..client import require_client

    world = require_client().read_world_context()
    players = [] if world is None else list(world.players or [])

    agent_id = Agent_ConvertID(a_i_AgentID)

    record = None
    for index in range(1, len(players)):
        if int(players[index].agent_id) == agent_id:
            record = players[index]
            break

    if record is None:
        return 0

    if a_s_Info == "AgentID":
        return int(record.agent_id)
    if a_s_Info == "AppearanceBitmap":
        return int(record.appearance_bitmap)
    if a_s_Info == "Flags":
        return int(record.flags)
    if a_s_Info == "Primary":
        return int(record.primary)
    if a_s_Info == "Secondary":
        return int(record.secondary)
    if a_s_Info == "Name":
        return str(record.name_encoded_str or "")
    if a_s_Info == "PartyLeaderPlayerNumber":
        return int(record.party_leader_player_number)
    if a_s_Info == "ActiveTitle":
        return int(record.active_title_tier)
    if a_s_Info == "ActiveChallenge":
        return int(record.reforged_or_dhuums_flags)
    if a_s_Info == "ActiveMelandrusAccord":
        return bool(record.is_melandrus_accord)
    if a_s_Info == "ActiveDhuumsCovenant":
        return bool(record.is_dhuums_covenant)
    if a_s_Info == "ActiveReforgedMode":
        return bool(record.is_reforged)
    if a_s_Info == "PlayerNumber":
        return int(record.player_number)
    if a_s_Info == "PartySize":
        return int(record.party_size)

    # GwAu3's own `Case Else`.
    return 0


def Agent_GetBestTarget(a_i_Range: Any = 1320) -> int:
    """The enemy worth attacking most, by GwAu3's own score (``GwAu3_Data_Agent.au3:1096-1119``).

    GwAu3's steps, kept: it takes the living-agent array (``:1098``, ``0xDB`` being the living type, as
    its own comment at ``:753`` records) and, for each agent, skips one whose ``Allegiance`` is not
    ``3`` (enemy), whose ``HP`` is not above ``0``, that is the controlled character, or that is further
    than ``$a_i_Range`` from the player (``:1101-1104``); then sums that agent's distance to **every**
    agent passing the same four tests, itself included (``:1105-1112``); and keeps the agent with the
    lowest sum, ties going to the first one reached (``:1113-1116``).

    The four guard pairs and the two loops are the source's, in the source's order, over this project's
    own reads: `Agent_GetAgentArray` for the array (ids where GwAu3 holds pointers), `Agent_GetAgentInfo`
    for the four columns, `Agent_GetMyID` for the controlled character and `Agent_GetDistance` for both
    the range test (the player, its own default) and the pairwise sum.

    **The no-match answer is ``0``, and GwAu3's is not.** ``:1097`` declares ``$l_i_BestTarget`` with no
    value, so a client with nothing matching answers AutoIt's uninitialised ``""``; this answers ``0``,
    the id no agent has, which is how every other member of this layer tells "nothing found".
    """

    best_target = 0
    lowest_sum = 100000000

    agent_array = Agent_GetAgentArray(0xDB)

    for index in range(1, agent_array[0] + 1):
        this_id = agent_array[index]
        sum_distances = 0

        if Agent_GetAgentInfo(this_id, "Allegiance") != 3:
            continue
        if Agent_GetAgentInfo(this_id, "HP") <= 0:
            continue
        if Agent_GetAgentInfo(this_id, "ID") == Agent_GetMyID():
            continue
        if Agent_GetDistance(this_id) > a_i_Range:
            continue

        for sub_index in range(1, agent_array[0] + 1):
            other_id = agent_array[sub_index]

            if Agent_GetAgentInfo(other_id, "Allegiance") != 3:
                continue
            if Agent_GetAgentInfo(other_id, "HP") <= 0:
                continue
            if Agent_GetAgentInfo(other_id, "ID") == Agent_GetMyID():
                continue
            if Agent_GetDistance(other_id) > a_i_Range:
                continue

            sum_distances += Agent_GetDistance(this_id, other_id)

        if sum_distances < lowest_sum:
            lowest_sum = sum_distances
            best_target = this_id

    return best_target
