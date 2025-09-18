import heapq
from collections import defaultdict

# ===========================
# Block / Station Enhancements
# ===========================
class HistoryMixin:
    """Mixin to add history tracking to Blocks and Stations."""
    def __init__(self):
        self.history = []

    def log_event(self, event_type, details):
        self.history.append({"event": event_type, **details})


# ===========================
# Connectivity Analysis
# ===========================
def connectivity_stats(rg):
    """Analyze connectivity statistics of the railway graph."""
    station_ids = list(rg.stations.keys())      # use stations
    edges = rg.adjacency                        # use adjacency dict
    stats = {
        "total_nodes": len(station_ids),
        "total_edges": sum(len(neigh) for neigh in edges.values()) // 2,
        "isolated_nodes": [n for n in station_ids if not edges.get(n)],
        "degree_distribution": {n: len(edges.get(n, [])) for n in station_ids},
    }
    return stats


def busiest_stations(rg, top_k=3):
    """Find the busiest stations based on connection degree."""
    edges = rg.adjacency
    degree = {n: len(edges.get(n, [])) for n in rg.stations.keys()}
    return sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_k]


# ===========================
# Shortest Path (Dijkstra)
# ===========================
def shortest_path(rg, src, dst):
    """Find shortest path between two stations using Dijkstra's algorithm."""
    nodes = list(rg.stations.keys())
    edges = rg.adjacency
    dist = {n: float("inf") for n in nodes}
    prev = {n: None for n in nodes}
    dist[src] = 0
    pq = [(0, src)]

    while pq:
        d, u = heapq.heappop(pq)
        if u == dst:
            break
        if d > dist[u]:
            continue
        for t_id in edges.get(u, []):  # adjacency stores track IDs
            track = rg.get_track(t_id)
            if track:  # Make sure track exists
                # find neighbor and weight
                neighbor = track.to if track.frm == u else track.frm
                weight = getattr(track, 'length_km', 1.0)  # Default weight if no length
                if dist[u] + weight < dist[neighbor]:
                    dist[neighbor] = dist[u] + weight
                    prev[neighbor] = u
                    heapq.heappush(pq, (dist[neighbor], neighbor))

    # reconstruct path
    path = []
    cur = dst
    while cur:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return dist[dst], path


# ===========================
# Block Utilization Analysis
# ===========================
def block_utilization(blocks, total_time=None):
    """
    Analyze block utilization.
    
    Args:
        blocks: List of block objects
        total_time: Optional total simulation time for utilization percentage
    """
    utilization = {}
    for b in blocks:
        total_occupied_time = 0
        count = 0

        for e in getattr(b, "history", []):
            # Handle different history entry formats safely
            if isinstance(e, dict) and e.get("event") == "occupy":
                entry = e.get("entry_time")
                exit_time = e.get("expected_exit_time")
                if entry is not None and exit_time is not None:
                    dur = exit_time - entry
                    total_occupied_time += dur
                    count += 1

        block_id = getattr(b, 'block_id', str(b))
        utilization[block_id] = {
            "usage_count": count,
            "avg_duration": (total_occupied_time / count) if count else 0,
            "total_occupied_time": total_occupied_time,
        }
        
        if total_time:
            utilization[block_id]["utilization_percentage"] = (total_occupied_time / total_time) * 100

    return utilization


def station_utilization(rg, total_time=None):
    """
    Analyze station utilization based on train passages.
    
    Args:
        rg: Railway graph object
        total_time: Optional total simulation time
    """
    utilization = {}
    for station_id, station in rg.stations.items():
        pass_count = sum(1 for e in getattr(station, "history", []) 
                        if isinstance(e, dict) and e.get("event") == "pass")
        
        utilization[station_id] = {
            "pass_count": pass_count,
            "avg_passes_per_hour": (pass_count / (total_time / 3600)) if total_time else 0,
        }
    
    return utilization


def average_delay(rg):
    """
    Calculate average delay across all blocks based on history.
    """
    delays = []
    
    # Collect all blocks from all tracks
    for track in rg.tracks.values():
        for block in track.blocks:
            for e in getattr(block, "history", []):
                if isinstance(e, dict) and e.get("event") == "release":
                    expected_exit = e.get("expected_exit_time")
                    actual_exit = e.get("actual_exit_time")
                    if expected_exit is not None and actual_exit is not None:
                        delay = actual_exit - expected_exit
                        delays.append(delay)
    
    return sum(delays) / len(delays) if delays else 0


def compare_scenarios(rg_before, rg_after):
    """
    Compare two railway graph scenarios.
    
    Args:
        rg_before: Railway graph before changes
        rg_after: Railway graph after changes
    """
    # Collect blocks from both scenarios
    blocks_before = []
    blocks_after = []
    
    for track in rg_before.tracks.values():
        blocks_before.extend(track.blocks)
    
    for track in rg_after.tracks.values():
        blocks_after.extend(track.blocks)
    
    util_before = block_utilization(blocks_before)
    util_after = block_utilization(blocks_after)
    
    delay_before = average_delay(rg_before)
    delay_after = average_delay(rg_after)
    
    return {
        "utilization_before": util_before,
        "utilization_after": util_after,
        "avg_delay_before": delay_before,
        "avg_delay_after": delay_after,
        "delay_improvement": delay_before - delay_after,
    }


def station_pass_counts(stations):
    """Count how many trains passed through each station."""
    counts = {}
    for s in stations:
        station_id = getattr(s, 'station_id', str(s))
        counts[station_id] = sum(1 for e in getattr(s, "history", []) 
                                if isinstance(e, dict) and e.get("event") == "pass")
    return counts


# Simple test function to verify the module is working
def test_module():
    """Test function to verify the analysis module is properly loaded."""
    print("Analysis module loaded successfully!")
    return True