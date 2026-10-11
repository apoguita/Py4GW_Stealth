"""``GwAu3_Data_Title.au3``'s **title-progress** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism the map and party snippets use: ``data_title.py`` is rewritten whole on every run, so a function
written straight into it would be lost the next time the generator ran.

**What it is.** ``Title_GetTitleInfo`` (``GwAu3_Data_Title.au3:6-48``) answers one field of one title's
progress record. GwAu3 takes the array's address and its size from its own world-info reader
(``World_GetWorldInfo("TitleArray")`` and ``("TitleArraySize")``, ``:7-8``), guards on both (``:9``), and
strides by ``0x2C`` (``:11``) -- the size its own comment records as having changed from ``0x28``
(``:4-5``).

**This project reads the same records with its own readers.** `Player.GetTitleArrayRaw`
(``py4gw/player.py:983-990``) reads the world context's ``titles_array``
(`py4gw/context/world_context.py:1554`) as a list of `TitleStruct` (``:1329-1345``), whose size is asserted
``0x2C`` exactly (``py4gw/context/world_context.py:2088``) -- GwAu3's own stride -- and `Player.GetTitle`
(``py4gw/player.py:998-1005``) answers one record by array index, with GwAu3's own bounds guard as its
``None``. The layer already answers ``World_GetWorldInfo("TitleArraySize")`` from that array's ``m_size``
(`py4gw/gwa3/data_world.py:330`) while its ``TitleArray`` key refuses, naming the address it would have
returned (``py4gw/gwa3/data_world.py:233-236``); this family answers the records themselves, which is the
same convention -- a caller wants the title, not the address of the array it sits in.

**The five middle keys are named one word apart by the two layouts, and this member answers the port's
names.** Both records are eleven words and ``0x2C`` end to end, and they agree about the four leading
fields and the two trailing pointers:

| GwAu3 key | GwAu3's offset | The port's field | The port's offset |
| --- | --- | --- | --- |
| ``Props`` | ``+0x0`` | ``props`` | ``+0x0`` |
| ``CurrentPoints`` | ``+0x4`` | ``current_points`` | ``+0x4`` |
| ``CurrentTitleTierIndex``/``CurrentTitleTier`` | ``+0x8`` | ``current_title_tier_index`` | ``+0x8`` |
| ``PointsNeededCurrentRank`` | ``+0xC`` | ``points_needed_current_rank`` | ``+0xC`` |
| ``Unknown10`` (its own comment: ``dhuum/reforged``) | ``+0x10`` | ``next_title_tier_index`` | ``+0x10`` |
| ``NextTitleTierIndex``/``NextTitleTier`` | ``+0x14`` | ``next_title_tier_index`` | **``+0x10``** |
| ``PointsNeededNextRank`` | ``+0x18`` | ``points_needed_next_rank`` | **``+0x14``** |
| ``MaxTitleRank`` | ``+0x1C`` | ``max_title_rank`` | **``+0x18``** |
| ``MaxTitleTierIndex``/``MaxTitleTier`` | ``+0x20`` | ``max_title_tier_index`` | **``+0x1C``** |
| ``PointsDescriptionEnc``/``PointsDescription`` | ``+0x24`` (a pointer) | ``points_desc_ptr`` | ``+0x24`` |
| ``TitleDescriptionEnc``/``TitleDescription`` | ``+0x28`` (a pointer) | ``h0028_ptr`` | ``+0x28`` |

GwAu3's middle five names are one word later than the port's, which puts its ``Unknown10`` -- the word its
own comment says came with the client update -- exactly on the port's ``next_title_tier_index``, and makes
the port's ``h0020`` (``+0x20``) a word no GwAu3 key names. A name is the fact and an offset is where the
fact stood when the source was written -- `tools/gwa3_snippets/data_map_character_info.py:20-27` records the
same reading for the character context's four middle keys -- so each key answers the port's field **of that
name**, and ``Unknown10``, which names no fact at all, answers the port's word at GwAu3's own ``+0x10``.
The disagreement is written down here and on the member: a live read is what would settle which layout the
client writes, and the port's is the one this project reproduces from its own sources.

**The four text keys decode in GwAu3 and read plainly here.** ``PointsDescriptionEnc`` and
``TitleDescriptionEnc`` hand the pointer at ``+0x24``/``+0x28`` to ``Utils_DecodeEncString``
(``GwAu3_Core_Utils.au3:440-462``), which walks the encoded array's variable-length digits and answers the
**numeric id** they carry; ``PointsDescription`` and ``TitleDescription`` hand the same pointer to
``Utils_DecodeEncStringAsync`` (``:469-498``), the client's own decoder on the game thread, and answer the
text. This project's `TitleStruct` reads those two pointers itself -- ``points_desc_encoded_str`` /
``points_desc_str`` (``py4gw/context/world_context.py:1376``, ``:1380``) and ``h0028_encoded_str`` /
``h0028_str`` (``:1384``, ``:1388``) -- so the pair is answered from the port's own reads of the same bytes,
with the plain key answering the display-safe form. The port's third name for the first pointer,
``points_description`` (``py4gw/context/world_context.py:1370``), is that same read with no formatting.
"""


def Title_GetTitleInfo(title_number: Any = 0, info: str = "") -> Any:
    """One field of one title-progress record (``GwAu3_Data_Title.au3:6-48``).

    GwAu3's guard order is kept, and it is its reader's own: the title is resolved first (`:7-11`), and a
    missing array, a negative index or an index at or past the array's size answers ``0`` (`:9`) before the
    empty key is tested (`:12`). `Player.GetTitle` (`py4gw/player.py:998-1005`) is the port's member with
    exactly that guard -- ``None`` for an index outside the array, and an empty list when the client holds
    no titles at all -- so the two tests are one here, and an empty key answers ``0`` only after the world
    context has been read. An unrecognised key answers ``0``, GwAu3's own ``Return 0`` after its ``Switch``
    (`:47`).

    The twelve scalar keys answer the record's own fields (`:16-32`). The five middle keys' offsets
    disagree with GwAu3's and each answers the port's field of its own name; ``Unknown10``, which names no
    fact, answers the port's word at GwAu3's ``+0x10``. The four text keys answer this project's own reads
    of the two pointers GwAu3 hands to its decoders, so ``PointsDescription``/``TitleDescription`` answer
    the port's display-safe text where GwAu3 answers the client's decoded text, and the ``*Enc`` pair
    answers the encoded string where GwAu3 answers the numeric id its digits carry. The full table and the
    reasons are in the module docstring.
    """

    from ..player import Player

    title = Player.GetTitle(int(title_number))
    if title is None or info == "":
        return 0

    if info == "Props":
        return int(title.props)
    if info == "CurrentPoints":
        return int(title.current_points)
    if info == "CurrentTitleTierIndex":
        return int(title.current_title_tier_index)
    if info == "CurrentTitleTier":
        return int(title.current_title_tier_index)
    if info == "PointsNeededCurrentRank":
        return int(title.points_needed_current_rank)

    # GwAu3's ``Unknown10`` is the word at ``+0x10`` it declines to name (`:23-24`); the port names that
    # same word `next_title_tier_index` (`py4gw/context/world_context.py:1338`), so GwAu3's own offset
    # picks it and the port's name answers it.
    if info == "Unknown10":
        return int(title.next_title_tier_index)

    # The four keys whose GwAu3 offsets are one word later than the port's names: each answers the port's
    # field of that name, and the disagreement is the module docstring's table.
    if info == "NextTitleTierIndex":
        return int(title.next_title_tier_index)
    if info == "NextTitleTier":
        return int(title.next_title_tier_index)
    if info == "PointsNeededNextRank":
        return int(title.points_needed_next_rank)
    if info == "MaxTitleRank":
        return int(title.max_title_rank)
    if info == "MaxTitleTierIndex":
        return int(title.max_title_tier_index)
    if info == "MaxTitleTier":
        return int(title.max_title_tier_index)

    # The two pointers GwAu3 decodes (`:33-44`), answered by the port's own reads of the same bytes. The
    # second pointer is the word the port leaves as `h0028_ptr` (`py4gw/context/world_context.py:1344`).
    if info == "PointsDescriptionEnc":
        return title.points_desc_encoded_str
    if info == "PointsDescription":
        return title.points_desc_str
    if info == "TitleDescriptionEnc":
        return title.h0028_encoded_str
    if info == "TitleDescription":
        return title.h0028_str

    # GwAu3's own `Return 0` for anything its `Switch` does not match (`:47`).
    return 0
