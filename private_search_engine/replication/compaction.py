from __future__ import annotations
from dataclasses import dataclass
from .consensus import LogEntry
from .snapshot import ConsensusSnapshotStore, compact_log

@dataclass(frozen=True)
class CompactionResult:
    snapshot_index: int
    snapshot_term: int
    removed_entries: int
    remaining_entries: int
    checksum: str

class SnapshotCompactor:
    """Creates a verified snapshot and removes only entries covered by it."""
    def __init__(self, store: ConsensusSnapshotStore):
        self.store = store

    def compact(self, *, node_id: str, term: int, commit_index: int,
                log: list[LogEntry], state: dict[str, str]) -> tuple[list[LogEntry], CompactionResult]:
        if commit_index <= 0:
            raise ValueError("commit_index must be positive")
        covered = [e for e in log if e.index <= commit_index]
        if not covered:
            raise ValueError("no committed entries available for compaction")
        included_term = covered[-1].term
        checksum = self.store.save(
            node_id=node_id, term=term, last_included_index=commit_index,
            last_included_term=included_term, commit_index=commit_index, state=state,
        )
        remaining = compact_log(log, commit_index)
        return remaining, CompactionResult(commit_index, included_term, len(covered), len(remaining), checksum)
