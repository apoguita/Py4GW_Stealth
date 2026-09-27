"""Process-memory access and fixed-width records for external reads."""

from .mailbox import MailboxRecord, MailboxState
from .memory import ProcessMemoryReader
from .memory_manager import MemoryManager

__all__ = ["MailboxRecord", "MailboxState", "MemoryManager", "ProcessMemoryReader"]
