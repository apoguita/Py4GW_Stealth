"""``GwAu3_Core_Utils.au3``'s list walkers, over this project's own lists.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the four members are.** GwAu3 walks the client's intrusive ``TList``/``TLink`` chains **by
address**: ``Utils_TList_CreateIterator`` (`GwAu3_Core_Utils.au3:88-95`) builds a three-cell array
holding the list's sentinel link, ``Utils_TList_Iterator_Current`` (`:98-103`) reads the ``ptr`` at the
current link ``+0x4`` and answers the node it names, ``Utils_TList_Iterator_Next`` (`:106-124`) steps
the iterator along the XOR-linked ring with ``Utils_TLink_GetNextLink`` (`:133-141`), and
``Utils_TLink_IsLinked`` (`:127-130`) answers whether a link's ``prev_link`` differs from the link's own
address. Every one of them exists to turn a **TList address** into a sequence of **node addresses** that
the caller then reads with ``Memory_ReadStruct`` -- which is exactly the field the owner's ruling covers:
the facts are this project's, the mechanism is not.

**This project's own list walk, and why the iterator is built on it.** The port reads an intrusive list
through `RemoteGWListView` (`py4gw/context/gw_list.py:45`) over `GWListStruct` (`:28`) -- whose
``offset`` and sentinel ``link`` are the same two fields GwAu3's walk uses -- and the ported classes
expose the **results** of that walk as lists of materialized records:
`AgentLivingStruct.visible_effects` (`py4gw/context/agent_array.py:935`, the very list at ``+0x174``
GwAu3's ``VisibleEffect_Count`` walks, `GwAu3_Data_Agent.au3:1146-1156`),
`PartyContextStruct.request` and `.sending` (`py4gw/context/party_context.py:321`, `:335`), and this
layer's own row readers (`VisibleEffect_GetAll`, `py4gw/gwa3/data_agent.py`). Those records are what a
caller here holds -- the pointers are read and consumed inside the port, and none is handed out.

**So the iterator is over the port's own list and answers the port's records.** The argument is the list
the layer hands out, GwAu3's three cells are kept, and the cells carry what this layer has where GwAu3
carries link addresses. The one thing that is *not* accepted is a bare `GWListStruct` header: the port's
walk materializes each node as a **type** (`RemoteGWListView`, `py4gw/context/gw_list.py:53-64`) and
GwAu3's iterator carries none, because it answers addresses and lets the caller read the node -- so the
layer hands out the walk's answer instead, and the header alone names no element type to materialize.
"""

from __future__ import annotations

from typing import Any

from ..context.gw_list import GWLinkStruct, GWListStruct


def Utils_TList_CreateIterator(a_p_TListPtr: Any) -> list[Any]:
    """An iterator over the list this layer hands out (``GwAu3_Core_Utils.au3:88-95``).

    **GwAu3's own steps and its three cells.** The sentinel is ``$a_p_TListPtr + 0x4`` (`:90`) -- the
    ``GWListStruct.link`` this project declares at ``+0x4`` of the list header
    (`py4gw/context/gw_list.py:32-35`, the ``0x0C`` header asserted at `:39`) -- the first cell is that
    sentinel, the second is the same sentinel (the ``$l_p_FirstTLink`` ``Next`` compares against,
    `:112`), and the third is the count of completed loops (`:93`).

    **What is accepted: the list this layer hands out.** That is the answer of the port's own walk --
    a ``list`` of the port's records, e.g. `AgentLivingStruct.visible_effects`
    (``py4gw/context/agent_array.py:935``) or `PartyContextStruct.request` / ``.sending``
    (``py4gw/context/party_context.py:321``, ``:335``). GwAu3's own empty answers -- a null pointer, and
    a sentinel whose ``next_node`` is zero or marked -- answer the **empty iterator**, which is what its
    first ``Utils_TList_Iterator_Current`` answers for both (`:100-101`).

    **The divergence, in one sentence:** GwAu3's cell 0 is the *link address* whose ``+0x4`` word is the
    current node and its walk is a ring it detects by comparing addresses, while this walks the records
    the port's own list read already produced -- so cell 0 carries the records not yet consumed, cell 1
    the first record (GwAu3's first-link cell, compared the same way) and cell 2 the completed-loop
    count, which stays ``0`` here because a finite, materialized walk cannot wrap.
    """

    records = [record for record in a_p_TListPtr] if a_p_TListPtr else []
    first = records[0] if records else 0
    return [records, first, 0]


def Utils_TList_Iterator_Current(a_a_Iterator: Any) -> Any:
    """The record the iterator is on (``GwAu3_Core_Utils.au3:98-103``).

    GwAu3 reads the ``ptr`` at ``$a_a_Iterator[0] + 0x4`` and answers ``0`` when its low bit is set
    (`:100-101`) -- the sentinel's own end marking, which is the same test the port's walk makes before
    it reads a node at all (`RemoteGWListView.to_list`, `py4gw/context/gw_list.py:69-71`).

    This answers **the port's record** the iterator is on, and ``0`` when there is none: GwAu3's own
    end-of-list answer, and the value its own callers' ``While $l_p_Current <> 0`` tests
    (``GwAu3_Data_Agent.au3:1152``, ``UtilityAI_EffectsCache.au3:124``). The caller's next step in GwAu3
    is ``Memory_ReadStruct($l_p_Current, $l_d_Struct)`` (``UtilityAI_EffectsCache.au3:125``); here the
    record has already been read, so that step is the record itself.
    """

    remaining = a_a_Iterator[0]
    if not remaining:
        return 0
    return remaining[0]


def Utils_TList_Iterator_Next(a_a_Iterator: Any) -> bool:
    """Step the iterator (``GwAu3_Core_Utils.au3:106-124``).

    **GwAu3's order is kept.** It takes the next link (``:109``), counts a completed loop when that link
    *is* the first link (``:112-114``), moves the iterator onto it (``:116``) and answers ``False`` when
    the new node's ``+0x4`` word is zero or has its low bit set (``:119-122``). This is that order over
    the port's own list: the head of the records not yet consumed is dropped, a record that is the first
    record counts a loop -- the comparison of `:112`, which a finite walk never satisfies -- and
    ``False`` is answered exactly when nothing remains, which is GwAu3's own "the next node is not
    valid" (``:120``).
    """

    remaining = a_a_Iterator[0]
    if remaining:
        a_a_Iterator[0] = remaining[1:]
        remaining = a_a_Iterator[0]

    if remaining and remaining[0] is a_a_Iterator[1]:
        a_a_Iterator[2] = int(a_a_Iterator[2]) + 1

    return bool(remaining)


def Utils_TLink_IsLinked(a_p_TLink: Any) -> bool:
    """Whether a link is connected to other links (``GwAu3_Core_Utils.au3:127-130``).

    **GwAu3 reads the link's own first word -- its ``prev_link`` -- and answers whether it differs from
    the link's address** (``:128-129``). Its only caller passes the **sentinel**
    (``Tools_VisibleEffect.au3:405``, on ``$tlistPtr + 0x4``), and there that comparison is "the ring
    holds a node" -- a sentinel's ``prev_link`` is its own address exactly when the list is empty, and
    the last node's link otherwise. So the fact the caller is asking for is the one the port's own walk
    already answers.

    **What is accepted, and what each answers.**

    * a `GWListStruct` header this layer handed out (`AgentLivingStruct.visible_effects_list`,
      ``py4gw/context/agent_array.py:885``; `PartyContextStruct.request_list`/``.sending_list``,
      ``py4gw/context/party_context.py:266``, ``:268``) -- the header whose ``link`` field **is** that
      sentinel -- answers the two tests `RemoteGWListView.to_list` makes before it reads a node: the
      sentinel's ``next_node`` is non-zero and has its low bit clear (``py4gw/context/gw_list.py:69-71``);
    * a `GWLinkStruct` this layer handed out -- the same sentinel on its own -- answers the same two
      tests on its own ``next_node`` word;
    * the port's own list (a ``list`` of its records, what `Utils_TList_CreateIterator` takes) answers
      whether it holds a record.

    **The divergence, in one sentence:** GwAu3 compares a link's ``prev_link`` word against the link's
    own address, which a materialized record does not carry, so this answers the same question through
    the sentinel's ``next_node`` -- the test this project's own walk makes, and the one GwAu3's caller
    is asking for at the sentinel. A null or unrecognised argument answers ``False``, which is GwAu3's
    own answer for a read at address ``0`` (``:128`` reads zero, and ``0 <> 0`` is False).
    """

    if isinstance(a_p_TLink, GWListStruct):
        return _has_first_node(int(a_p_TLink.link.next_node))

    if isinstance(a_p_TLink, GWLinkStruct):
        return _has_first_node(int(a_p_TLink.next_node))

    if isinstance(a_p_TLink, (list, tuple)):
        return bool(a_p_TLink)

    return False


def _has_first_node(next_node: int) -> bool:
    """The port's own "this ring holds a node" test (`py4gw/context/gw_list.py:69-71`).

    ``RemoteGWListView.to_list`` stops before the first read when the sentinel's ``next_node`` word is
    zero or has its low bit set, so those two are the port's own statement that the list is empty.
    """

    return bool(next_node and not next_node & 1)


__all__ = [
    "Utils_TLink_IsLinked",
    "Utils_TList_CreateIterator",
    "Utils_TList_Iterator_Current",
    "Utils_TList_Iterator_Next",
]
