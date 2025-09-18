from dataclasses import dataclass, field
from typing import Optional, List, Dict
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
    expected_exit_time: Optional[float] = None

    # keep a history of occupancy for analysis
    history: List[Dict] = field(default_factory=list, repr=False)

    # thread-safety
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def occupy(self, train_id: str, entry_time: float, expected_exit_time: float) -> bool:
        with self.lock:
            if self.occupied_by is not None:
                return False
            self.occupied_by = train_id
            self.entry_time = entry_time
            self.expected_exit_time = expected_exit_time
            return True

    def release(self, actual_exit_time: Optional[float] = None) -> bool:
        """
        Release the block and record delay/utilization history.
        """
        with self.lock:
            if self.occupied_by is None:
                return False

            delay = 0.0
            if actual_exit_time is not None and self.expected_exit_time is not None:
                delay = actual_exit_time - self.expected_exit_time

            # record history for analysis
            self.history.append({
                "train_id": self.occupied_by,
                "entry_time": self.entry_time,
                "expected_exit_time": self.expected_exit_time,
                "actual_exit_time": actual_exit_time,
                "delay": delay,
            })

            # reset dynamic fields
            self.occupied_by = None
            self.entry_time = None
            self.expected_exit_time = None
            return True

    def is_free(self) -> bool:
        with self.lock:
            return self.occupied_by is None
