# utils/graph_ops.py
from models.railway_graph import RailwayGraph
import heapq

def shortest_path(graph: RailwayGraph, start: str, end: str, by="time"):
    """
    Dijkstra-style shortest path between two stations.
    by="time" -> uses length/max_speed
    by="distance" -> uses track length
    """
    pq = [(0, start, [])]  # (cost, current_station, path_so_far)
    visited = set()

    while pq:
        cost, current, path = heapq.heappop(pq)
        if current in visited:
            continue
        visited.add(current)

        if current == end:
            return path, cost

        for neighbor, track in graph.get_neighbors(current):
            if neighbor not in visited:
                if by == "time" and track.max_speed_kph > 0:
                    weight = track.length_km / track.max_speed_kph
                else:
                    weight = track.length_km
                heapq.heappush(pq, (cost + weight, neighbor, path + [track.track_id]))
    return None, float("inf")


def detect_conflict(graph: RailwayGraph, block_id: str, entry_time: float, exit_time: float):
    """
    Check if requested block occupancy conflicts with an existing one.
    """
    for tr in graph.tracks.values():
        for b in tr.blocks:
            if b.block_id == block_id:
                if not b.is_free():
                    # Check time overlap
                    if not (exit_time <= b.entry_time or entry_time >= b.expected_exit_time):
                        return True
    return False


def estimate_travel_time(graph: RailwayGraph, path: list):
    """
    Estimate total travel time along a path of track_ids.
    """
    total = 0.0
    for tid in path:
        tr = graph.get_track(tid)
        if tr and tr.max_speed_kph > 0:
            total += tr.length_km / tr.max_speed_kph
    return total


def get_free_path(graph: RailwayGraph, start: str, end: str):
    """
    Try to get a free path (all blocks unoccupied) between two stations.
    """
    path, cost = shortest_path(graph, start, end, by="time")
    if not path:
        return None, float("inf")

    # Check all blocks are free
    for tid in path:
        tr = graph.get_track(tid)
        free_blocks = [b for b in tr.blocks if b.is_free()]
        if not free_blocks:
            return None, float("inf")
    return path, cost
