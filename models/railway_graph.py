# models/railway_graph.py
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import threading

from .station import Station
from .track import Track

try:
    import networkx as nx
except Exception:
    nx = None

class RailwayGraph:
    def __init__(self):
        self.stations: Dict[str, Station] = {}
        self.tracks: Dict[str, Track] = {}
        self.adjacency: Dict[str, List[str]] = {}
        self.lock = threading.RLock()

    def load_from_json(self, json_path: str):
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        # load stations
        for s in payload.get("stations", []):
            st = Station(station_id=s["id"], name=s.get("name", s["id"]), platforms=int(s.get("platforms", 1)))
            self.stations[st.station_id] = st
            self.adjacency.setdefault(st.station_id, [])

        # load tracks and create blocks inside Track
        for t in payload.get("tracks", []):
            tid = t["id"]
            frm = t["from"]
            to = t["to"]
            length = float(t.get("length_km", 0.0))
            max_speed = float(t.get("max_speed_kph", 0.0))
            direction = t.get("direction", "bi")
            block_count = int(t.get("blockCount", 1))
            tr = Track(track_id=tid, frm=frm, to=to, length_km=length,
                       max_speed_kph=max_speed, direction=direction, block_count=block_count)
            self.tracks[tid] = tr

            self.adjacency.setdefault(frm, []).append(tid)
            # For bidirectional, let adjacency include same track id for the reverse node too
            if direction == "bi":
                self.adjacency.setdefault(to, []).append(tid)
            else:
                # unidirectional: only frm->to represented
                pass

    # basic queries
    def get_station(self, station_id: str) -> Optional[Station]:
        return self.stations.get(station_id)

    def get_track(self, track_id: str) -> Optional[Track]:
        return self.tracks.get(track_id)

    def get_neighbors(self, station_id: str) -> List[Tuple[str, Track]]:
        neighbors = []
        for t_id in self.adjacency.get(station_id, []):
            track = self.tracks[t_id]
            neighbor = track.to if track.frm == station_id else track.frm
            neighbors.append((neighbor, track))
        return neighbors

    def get_free_blocks_on_track(self, track_id: str) -> List:
        tr = self.get_track(track_id)
        if not tr:
            return []
        return [b for b in tr.blocks if b.is_free()]

    # block reservation helpers (used by simulation)
    def reserve_block(self, block_id: str, train_id: str, entry_time: float, expected_exit_time: float) -> bool:
        # find block
        for tr in self.tracks.values():
            for b in tr.blocks:
                if b.block_id == block_id:
                    return b.occupy(train_id, entry_time, expected_exit_time)
        return False

    def release_block(self, block_id: str):
        for tr in self.tracks.values():
            for b in tr.blocks:
                if b.block_id == block_id:
                    b.release()
                    return True
        return False

    def print_summary(self):
        print("Stations:")
        for sid, s in self.stations.items():
            print(f"  {sid}: {s.name} (platforms {s.platforms}, available {s.available_platforms})")
        print("\nTracks and Blocks:")
        for tid, tr in self.tracks.items():
            print(f"  {tid}: {tr.frm}->{tr.to} len={tr.length_km} blocks={[b.block_id + ('(free)' if b.is_free() else '(occ)') for b in tr.blocks]}")
