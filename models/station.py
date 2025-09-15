# models/station.py
from dataclasses import dataclass, field

@dataclass
class Station:
    station_id: str
    name: str
    platforms: int
    available_platforms: int = field(init=False)

    def __post_init__(self):
        self.available_platforms = self.platforms

    def occupy_platform(self):
        if self.available_platforms <= 0:
            raise RuntimeError(f"No available platforms at {self.station_id}")
        self.available_platforms -= 1

    def release_platform(self):
        if self.available_platforms < self.platforms:
            self.available_platforms += 1
