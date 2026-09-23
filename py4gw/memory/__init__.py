"""Process-memory access and fixed-width records for external reads."""

from .mailbox import MailboxRecord, MailboxState
from .memory import ProcessMemoryReader

__all__ = ["MailboxRecord", "MailboxState", "ProcessMemoryReader"]
