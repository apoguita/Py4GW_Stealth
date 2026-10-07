"""Port of Reforged's ``Py4GWCoreLib/Quest.py`` (245 lines) — the ``Quest`` class, whole.

**The class is a delegation surface and nothing else.** Every one of its 26 members returns or calls
one method of ``PyQuest`` (the injected binding module), so the port's work is split exactly as the
source splits it:

* **this file** — the class, member for member, in the source's own order, with the source's own
  bodies (``Quest.quest_instance().<member>(...)``) and the source's own argument defaults;
* **``native_src/quest/py_quest.py``** — the binding the source's members reach, where the real
  behaviour lives (the quest log walk, the five decoders, the two quest-changing calls). Its module
  docstring records, against the native source lines, where each member's behaviour comes from and
  the three divergences this execution model forces.

Sources: ``Py4GWCoreLib/Quest.py`` (the class), ``src/GW/quest/quest_bindings.cpp`` (``PyQuest`` and
``QuestData``), ``src/GW/quest/quest_methods.cpp`` and ``src/GW/quest/quest.cpp`` (what the binding
calls), ``include/GW/context/quest.h`` (the ``0x34`` record this port already reads as
``context/world_context.py``'s ``QuestStruct``).

**Nothing here is target-side work and no member raises**: every call the source makes has a ported
home, and the two members that change the game (``SetActiveQuest``, ``AbandonQuest``) **call the
client's own quest functions** behind the source's guards — which is what the source's inner layer
does and what a live run on 2026-10-06 proved moves the client, after the hook's UI message was tried
and did nothing (``docs/QUEST_PORT.md`` §3 and §6b). Every one of the 26 members has been run against
a live client whose log held 23 quests.
"""

from __future__ import annotations

from .native_src.quest.py_quest import PyQuest, QuestData

#: ``Quest.quest_instance()``'s answer in the source is ``PyQuest.PyQuest()`` — the binding's own
#: module-level class, whose methods are static. The port's ``PyQuest`` is that class.
__all__ = ["Quest", "QuestData"]


class Quest:
    """``class Quest`` (``Quest.py:3-245``): 26 members, each one line into ``PyQuest``."""

    @staticmethod
    def quest_instance() -> type[PyQuest]:
        """``Quest.py:4-6`` — ``return PyQuest.PyQuest()``."""

        return PyQuest

    @staticmethod
    def GetActiveQuest() -> int:
        """``Quest.py:8-15`` — the active quest's id."""

        return Quest.quest_instance().get_active_quest_id()

    @staticmethod
    def SetActiveQuest(quest_id: int) -> None:
        """``Quest.py:17-25`` — set the active quest."""

        Quest.quest_instance().set_active_quest_id(quest_id)

    @staticmethod
    def AbandonQuest(quest_id: int) -> None:
        """``Quest.py:27-35`` — abandon a quest."""

        Quest.quest_instance().abandon_quest_id(quest_id)

    @staticmethod
    def IsQuestCompleted(quest_id: int) -> bool:
        """``Quest.py:37-45`` — whether the quest's ``log_state`` carries the completed bit."""

        return Quest.quest_instance().is_quest_completed(quest_id)

    @staticmethod
    def IsQuestPrimary(quest_id: int) -> bool:
        """``Quest.py:47-55`` — whether the quest's ``log_state`` carries the primary bit."""

        return Quest.quest_instance().is_quest_primary(quest_id)

    @staticmethod
    def IsMissionMapQuestAvailable() -> bool:
        """``Quest.py:57-64`` — whether the mission-objective array holds anything."""

        return Quest.quest_instance().is_mission_map_quest_available()

    @staticmethod
    def GetQuestData(quest_id: int) -> QuestData:
        """``Quest.py:66-74`` — the quest's record, as ``QuestData``."""

        return Quest.quest_instance().get_quest_data(quest_id)

    @staticmethod
    def GetQuestLog() -> list[QuestData]:
        """``Quest.py:76-83`` — every entry of the quest log."""

        return Quest.quest_instance().get_quest_log()

    @staticmethod
    def GetQuestLogIds() -> list[int]:
        """``Quest.py:85-92`` — the quest log's ids."""

        return Quest.quest_instance().get_quest_log_ids()

    @staticmethod
    def RequestQuestInfo(quest_id: int, update_marker: bool = False) -> None:
        """``Quest.py:94-103`` — ask the client for the quest's information.

        The source's parameter is named ``update_marker`` here and ``update_markers`` in the binding
        it passes through; both spellings are the sources' own (``quest_bindings.cpp:397``).
        """

        Quest.quest_instance().request_quest_info(quest_id, update_marker)

    @staticmethod
    def RequestQuestName(quest_id: int) -> None:
        """``Quest.py:105-113``."""

        Quest.quest_instance().request_quest_name(quest_id)

    @staticmethod
    def IsQuestNameReady(quest_id: int) -> bool:
        """``Quest.py:115-122``."""

        return Quest.quest_instance().is_quest_name_ready(quest_id)

    @staticmethod
    def GetQuestName(quest_id: int) -> str:
        """``Quest.py:124-131``."""

        return Quest.quest_instance().get_quest_name(quest_id)

    @staticmethod
    def RequestQuestDescription(quest_id: int) -> None:
        """``Quest.py:133-141``."""

        Quest.quest_instance().request_quest_description(quest_id)

    @staticmethod
    def IsQuestDescriptionReady(quest_id: int) -> bool:
        """``Quest.py:143-150``."""

        return Quest.quest_instance().is_quest_description_ready(quest_id)

    @staticmethod
    def GetQuestDescription(quest_id: int) -> str:
        """``Quest.py:152-159``."""

        return Quest.quest_instance().get_quest_description(quest_id)

    @staticmethod
    def RequestQuestObjectives(quest_id: int) -> None:
        """``Quest.py:161-169``."""

        Quest.quest_instance().request_quest_objectives(quest_id)

    @staticmethod
    def IsQuestObjectivesReady(quest_id: int) -> bool:
        """``Quest.py:171-178``."""

        return Quest.quest_instance().is_quest_objectives_ready(quest_id)

    @staticmethod
    def GetQuestObjectives(quest_id: int) -> str:
        """``Quest.py:180-187``."""

        return Quest.quest_instance().get_quest_objectives(quest_id)

    @staticmethod
    def RequestQuestLocation(quest_id: int) -> None:
        """``Quest.py:189-197``."""

        Quest.quest_instance().request_quest_location(quest_id)

    @staticmethod
    def IsQuestLocationReady(quest_id: int) -> bool:
        """``Quest.py:199-206``."""

        return Quest.quest_instance().is_quest_location_ready(quest_id)

    @staticmethod
    def GetQuestLocation(quest_id: int) -> str:
        """``Quest.py:208-215``."""

        return Quest.quest_instance().get_quest_location(quest_id)

    @staticmethod
    def RequestQuestNPC(quest_id: int) -> None:
        """``Quest.py:217-225``."""

        Quest.quest_instance().request_quest_npc(quest_id)

    @staticmethod
    def IsQuestNPCReady(quest_id: int) -> bool:
        """``Quest.py:227-234``."""

        return Quest.quest_instance().is_quest_npc_ready(quest_id)

    @staticmethod
    def GetQuestNPC(quest_id: int) -> str:
        """``Quest.py:236-243``."""

        return Quest.quest_instance().get_quest_npc(quest_id)
