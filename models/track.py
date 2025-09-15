# models/track.py
from dataclasses import dataclass, field
from typing import List
from .block import Block

@dataclass
class Track:
    track_id: str
    frm: str
    to: str
    length_km: float
    max_speed_kph: float
    direction: str  # "uni" or "bi"
    block_count: int = 1
    blocks: List[Block] = field(init=False)

    def __post_init__(self):
        # create blocks evenly spaced
        block_len = max(self.length_km / max(1, self.block_count), 0.001)
        self.blocks = []
        for i in range(self.block_count):
            bid = f"{self.track_id}_B{i+1}"
            self.blocks.append(Block(block_id=bid,
                                     parent_track=self.track_id,
                                     length_km=block_len,
                                     max_speed_kph=self.max_speed_kph,
                                     direction=self.direction))
