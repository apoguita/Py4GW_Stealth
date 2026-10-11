"""``GwAu3_Data_World.au3``'s three remaining readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map_character_info.py`
uses: ``data_world.py`` is rewritten whole on every run.

**Why these three.** ``GwAu3_Data_World.au3`` declares eight functions: ``World_GetWorldInfo`` -- the key
table this family generates -- the four ``World_Mission*`` helpers named at the end of this docstring, and
the three below, which were still absent from this layer. They are exactly the three a script calls and
this layer did not export: ``World_GetWorldContextPtr`` (``:4-8``), ``World_IsSkillLearnt`` (``:214-233``)
and ``World_GetSkillDuplicateCount`` (``:235-256``) -- the three names the ported script's own
"declared but not built" list carries (``tools/autoit/Stealth_GwAu3.au3:7``, written from
``GwAu3_DevTools.au3``'s call sites at ``:2947``, ``:2953`` and ``:3097``).

**All three read the same arrays the address keys of this family refuse**, which is why they are
answerable here and were refused there: ``World_GetWorldInfo`` answers a client pointer for
``UnlockedSkillsArray`` and must refuse it, while this project reads **those arrays as records and
words** -- `WorldContextStruct.unlocked_character_skills`
(``py4gw/context/world_context.py:1897``, declared at ``+0x710``, ``:1511``) and
`duplicated_character_skills` (``:1902``, declared at ``+0x720``, ``:1512``). Both offsets are
GwAu3's own.

**What is deliberately not here.** ``World_MissionGetState`` (``:278-339``),
``World_MissionIsCompleted`` (``:348-350``), ``World_MissionHasExpert`` (``:359-361``) and
``World_MissionHasMaster`` (``:370-372``) are declared in the same file and are still unbuilt. They are
not the three this file answers, and they are named here rather than left to be discovered: the port
has every member they need (`Map_GetAreaInfo`'s ``RegionType``/``Campaign`` keys,
`WorldContextStruct.missions_completed`, `.missions_bonus`, `.missions_completed_hm`,
`.missions_bonus_hm` at ``py4gw/context/world_context.py:1915-1937``), and no script in either project
calls them.
"""


def World_GetWorldContextPtr() -> Any:
    """The world context itself (``GwAu3_Data_World.au3:4-8``).

    GwAu3's body resolves ``BasePointer[0][0x18][0x2C]`` and answers that client *address*. This layer
    hands out no address under any name, so the member answers **the record the same word points at**:
    `py4gw.client.ConnectedClient.read_world_context` (``py4gw/client.py:1582``, on the class at
    ``:205`` -- the layer's prose calls it ``RemoteClient`` in eight places, which is a stale name), the
    port's own on-demand read of it. That is the shape `Agent_GetAgentPtr` and `PreGame_Ptr` already
    record
    (`py4gw/gwa3/data_agent.py:674`; ``py4gw/gwa3/data_pregame.py:19-23``), and it is what the one
    caller in the ported script does with it -- prints it, and would test it.

    GwAu3's ``0`` for a null pointer arrives here as ``None``, which is what this project reads where
    the client holds no world context; a caller that tests the answer treats both the same way.
    """

    return require_client().read_world_context()


def World_IsSkillLearnt(a_i_SkillID: Any) -> bool:
    """Whether the character has learnt a skill (``GwAu3_Data_World.au3:214-233``).

    GwAu3's guard order is kept term for term: no world context answers ``False`` (``:216``), an
    unlocked-skills array that is not there answers ``False`` (``:219``), an index past the end answers
    ``False`` (``:225``), and the answer is the bit test over the word the id lands in --
    ``BitAND(word, 1 << (skill_id % 32)) <> 0`` with ``word = array[Floor(skill_id / 32)]``
    (``:227-232``).

    The array is the same one, read the way this project reads it: GwAu3 takes the ``ptr`` and ``size``
    of the ``Array<dword>`` at ``+0x710`` (``:218``, ``:221``) and this reads that word of the world
    context as the list of ``uint32`` words it holds
    (`WorldContextStruct.unlocked_character_skills`, ``py4gw/context/world_context.py:1897``, declared
    at ``+0x710``, ``:1511``) -- the same bitfield, indexed and masked the same way.
    """

    world = require_client().read_world_context()
    if world is None:
        return False

    unlocked = world.unlocked_character_skills
    if not unlocked:
        return False

    real_index = int(a_i_SkillID) // 32
    if real_index >= len(unlocked):
        return False

    shift = int(a_i_SkillID) % 32
    flag = 1 << shift
    return (int(unlocked[real_index]) & flag) != 0


def World_GetSkillDuplicateCount(a_i_SkillID: Any) -> int:
    """How many copies of a skill the character holds (``GwAu3_Data_World.au3:235-256``).

    GwAu3's guards and its answer are kept: no world context answers ``0`` (``:237``), a duplicate-skill
    array that is not there answers ``0`` (``:240``), a skill id no entry matches answers ``0``
    (``:255``), and a match answers that entry's own count (``:250-251``).

    **One divergence, and it is GwAu3's arithmetic against this project's declared record.** GwAu3's loop
    steps the array by ``0x4`` (``:245``) and then reads a ``long`` id at ``+0x0`` and a ``long`` count
    at ``+0x4`` of each step, so consecutive steps overlap by a word and the count it answers is the *id*
    of the next entry whenever the array really is a list of pairs. This project declares that record as
    ``0x08`` bytes -- `DupeSkillStruct`, ``skill_id`` then ``count``
    (``py4gw/context/world_context.py:1142-1146``) -- and reads the array at ``+0x720`` as those records
    (`WorldContextStruct.duplicated_character_skills`, ``:1902``, declared at ``:1512``), so the count
    answered here is the matching record's own. A live read of the array is what would settle the
    stride; the id and the count are the same two words at the same offset either way.
    """

    world = require_client().read_world_context()
    if world is None:
        return 0

    duplicates = world.duplicated_character_skills
    if not duplicates:
        return 0

    skill_id = int(a_i_SkillID)
    for record in duplicates:
        if int(record.skill_id) == skill_id:
            return int(record.count)
    return 0
