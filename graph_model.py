"""
graph_model.py
Person 1: Graph Data Model & Loader for Kalyan section prototype.

Features:
- Station and Track classes (static properties)
- In-memory graph (adjacency list)
- Track status (dynamic fields for real-time system)
- Loader from JSON
- Convenience APIs: query stations/tracks, reserve/release track status
- Optional export to networkx for visualization/debug
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import threading

# Optional: only if you plan to visualize quickly
try:
    import networkx as nx
except Exception:
    nx = None


@dataclass
class Station:
    station_id: str
    name: str
    platforms: int
    # dynamic
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


@dataclass
class Track:
    track_id: str
    frm: str
    to: str
    length_km: float
    max_speed_kph: float
    direction: str  # "uni" or "bi"

    # dynamic / runtime fields (default)
    status_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    occupied: bool = False
    current_train_id: Optional[str] = None
    entry_time: Optional[float] = None     # epoch or simulation time
    expected_exit_time: Optional[float] = None
    reserved_until: Optional[float] = None

    def reserve(self, train_id: str, entry_time: float, expected_exit_time: float) -> bool:
        """Attempt to reserve the track for a train. Thread-safe."""
        with self.status_lock:
            if self.occupied:
                return False
            # additional checks can be added here (reserved_until)
            self.occupied = True
            self.current_train_id = train_id
            self.entry_time = entry_time
            self.expected_exit_time = expected_exit_time
            return True

    def release(self):
        with self.status_lock:
            self.occupied = False
            self.current_train_id = None
            self.entry_time = None
            self.expected_exit_time = None
            self.reserved_until = None


class RailwayGraph:
    """
    In-memory adjacency-based railway graph.
    Nodes = station ids (strings)
    Edges = Track objects
    """

    def __init__(self):
        # adjacency: station_id -> list of track ids leaving that station
        self.adjacency: Dict[str, List[str]] = {}
        self.stations: Dict[str, Station] = {}
        self.tracks: Dict[str, Track] = {}
        self.lock = threading.RLock()  # coarse-grain operations lock

    # -------------------------
    # Loader / builder methods
    # -------------------------
    def load_from_json(self, json_path: str):
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        # stations
        for s in payload.get("stations", []):
            st = Station(station_id=s["id"], name=s.get("name", s["id"]), platforms=int(s.get("platforms", 1)))
            self.stations[st.station_id] = st
            if st.station_id not in self.adjacency:
                self.adjacency[st.station_id] = []

        # tracks
        for t in payload.get("tracks", []):
            tid = t["id"]
            frm = t["from"]
            to = t["to"]
            length = float(t.get("length_km", 0.0))
            max_speed = float(t.get("max_speed_kph", 0.0))
            direction = t.get("direction", "bi")
            tr = Track(track_id=tid, frm=frm, to=to, length_km=length, max_speed_kph=max_speed, direction=direction)
            self.tracks[tid] = tr

            # add adjacency (directed edge frm->to)
            if frm not in self.adjacency:
                self.adjacency[frm] = []
            self.adjacency[frm].append(tid)

            # for bidirectional tracks, add reverse pseudo-edge with same track id or create new id
            if direction == "bi":
                # create a virtual reverse mapping by adding track id to to-node too
                if to not in self.adjacency:
                    self.adjacency[to] = []
                # To preserve unique track id semantics, we'll still store single Track object but allow adjacency both ways.
                self.adjacency[to].append(tid)

    # -------------------------
    # Query / utility methods
    # -------------------------
    def get_station(self, station_id: str) -> Optional[Station]:
        return self.stations.get(station_id)

    def get_track(self, track_id: str) -> Optional[Track]:
        return self.tracks.get(track_id)

    def get_neighbors(self, station_id: str) -> List[Tuple[str, Track]]:
        """
        Returns list of (neighbor_station_id, Track object) for outgoing edges
        Note: for bi-directional tracks both nodes will list the same track id.
        """
        neighbors = []
        for t_id in self.adjacency.get(station_id, []):
            track = self.tracks[t_id]
            # determine neighbor station id (if this track's frm == station -> neighbor is to; else neighbor is frm)
            neighbor = track.to if track.frm == station_id else track.frm
            neighbors.append((neighbor, track))
        return neighbors

    def get_available_tracks_from(self, station_id: str) -> List[Track]:
        """Return tracks leaving station that are currently not occupied."""
        res = []
        for t_id in self.adjacency.get(station_id, []):
            track = self.tracks[t_id]
            if not track.occupied:
                res.append(track)
        return res

    # -------------------------
    # Reservation helpers used by simulation
    # -------------------------
    def reserve_track(self, track_id: str, train_id: str, entry_time: float, expected_exit_time: float) -> bool:
        track = self.get_track(track_id)
        if track is None:
            return False
        return track.reserve(train_id, entry_time, expected_exit_time)

    def release_track(self, track_id: str):
        track = self.get_track(track_id)
        if track:
            track.release()

    # -------------------------
    # Export / debug
    # -------------------------
    def print_graph_summary(self):
        print("Stations:")
        for sid, s in self.stations.items():
            print(f"  {sid} - {s.name} (platforms: {s.platforms}, avail: {s.available_platforms})")
        print("\nTracks / adjacency:")
        for sid, tlist in self.adjacency.items():
            print(f"  {sid} -> {[self.tracks[t].track_id for t in tlist]}")
        print("\nTrack status:")
        for tid, tr in self.tracks.items():
            print(f"  {tid}: {tr.frm} -> {tr.to} | occupied={tr.occupied} train={tr.current_train_id}")

    def to_networkx(self):
        """Optional: export a networkx Graph for visualization (if networkx is installed)."""
        if nx is None:
            raise ImportError("networkx not available")
        G = nx.Graph()
        for sid, st in self.stations.items():
            G.add_node(sid, label=st.name, platforms=st.platforms)
        for tid, tr in self.tracks.items():
            # add edge with attributes
            G.add_edge(tr.frm, tr.to, track_id=tid, length_km=tr.length_km, max_speed_kph=tr.max_speed_kph)
        return G


# -------------------------
# Quick test-run if executed as script
# -------------------------
if __name__ == "__main__":
    import os, time
    json_path = os.path.join(os.path.dirname(__file__), "kalyan_network.json")
    json_path = os.path.abspath(json_path)
    rg = RailwayGraph()
    rg.load_from_json(json_path)
    rg.print_graph_summary()

    # simulate a simple reservation
    print("\nAttempting to reserve T2 by train EXP100 at time 0 for 300 sec")
    ok = rg.reserve_track("T2", "EXP100", entry_time=0.0, expected_exit_time=300.0)
    print("reserve ok:", ok)
    rg.print_graph_summary()

    # release and show
    rg.release_track("T2")
    print("\nAfter release:")
    rg.print_graph_summary()
