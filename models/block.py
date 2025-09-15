# models/block.py
from dataclasses import dataclass, field
from typing import Optional
import threading

@dataclass
class Block:
    block_id: str
    parent_track: str
    length_km: float
    max_speed_kph: float
    direction: str  # "uni" or "bi"

    # dynamic fields
    occupied_by: Optional[str] = None
    entry_time: Optional[float] = None
    exit_time: Optional[float] = None

    # thread-safety
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def occupy(self, train_id: str, entry_time: float, expected_exit_time: float) -> bool:
        with self.lock:
            if self.occupied_by is not None:
                return False
            self.occupied_by = train_id
            self.entry_time = entry_time
            self.exit_time = expected_exit_time
            return True

    def release(self):
        with self.lock:
            self.occupied_by = None
            self.entry_time = None
            self.exit_time = None

    def is_free(self) -> bool:
        with self.lock:
            return self.occupied_by is None
