# kalyan_demo.py
from utils.loader import load_graph_from_default
from utils.simulation import SimulationEngine, TrainEnterBlockEvent, TrainArriveStationEvent
from utils.optimization import resolve_conflicts, optimize_schedule
import json
import time
import sys

def load_kalyan_data():
    """Load the Kalyan network data from the JSON file."""
    with open('data/kalyan_network.json', 'r') as f:
        return json.load(f)

def print_kalyan_info():
    """Print information about the Kalyan network."""
    data = load_kalyan_data()
    print("\n" + "="*50)
    print("=== KALYAN NETWORK INFORMATION ===")
    print("="*50)
    
    # Print basic statistics
    print(f"\nStations: {len(data.get('stations', []))}")
    print(f"Tracks: {len(data.get('tracks', []))}")
    
    # Print station details
    print("\nStations:")
    for station in data.get('stations', []):
        print(f"  {station['id']}: {station.get('name', 'Unnamed')}")
        print(f"    Platforms: {station.get('platforms', 0)}")
    
    # Print track details
    print("\nTracks:")
    for track in data.get('tracks', []):
        print(f"  {track['id']}: From {track.get('from', 'Unknown')} to {track.get('to', 'Unknown')}")
        print(f"    Length: {track.get('length_km', 0)} km")
        print(f"    Max Speed: {track.get('max_speed_kph', 0)} kph")
        print(f"    Direction: {track.get('direction', 'Unknown')}")
        print(f"    Block Count: {track.get('blockCount', 0)}")

def run_kalyan_simulation():
    """Run a simulation on the Kalyan network."""
    # Load the railway graph
    rg = load_graph_from_default()
    
    # Create simulation engine
    sim = SimulationEngine(rg)
    
    print("\n" + "="*50)
    print("=== KALYAN NETWORK SIMULATION ===")
    print("="*50)
    
    # Get all stations for scheduling trains
    stations = list(rg.stations.keys())
    if len(stations) < 2:
        print("Not enough stations for simulation")
        return
    
    # Schedule some train journeys between stations
    print("\nScheduling train journeys:")
    
    # Get tracks for each station pair
    journeys = []
    for i in range(len(stations) - 1):
        from_station = stations[i]
        to_station = stations[i + 1]
        
        # Find tracks connecting these stations
        connecting_tracks = []
        for track_id, track in rg.tracks.items():
            if (track.from_station == from_station and track.to_station == to_station) or \
               (track.from_station == to_station and track.to_station == from_station):
                connecting_tracks.append(track)
        
        if connecting_tracks:
            # Create a journey using the first connecting track
            track = connecting_tracks[0]
            journey = {
                'train_id': f"TRAIN_{from_station}_{to_station}",
                'from_station': from_station,
                'to_station': to_station,
                'track': track,
                'departure_time': i * 100,  # Stagger departures
                'blocks': track.blocks if hasattr(track, 'blocks') else []
            }
            journeys.append(journey)
            print(f"  {journey['train_id']}: {from_station} → {to_station} at t={journey['departure_time']}")
    
    # Schedule the journeys in the simulation
    for journey in journeys:
        # Schedule station arrival
        arrival_time = journey['departure_time']
        departure_time = arrival_time + 30  # 30 time units at the station
        
        event = TrainArriveStationEvent(
            arrival_time, journey['train_id'], journey['from_station'], departure_time
        )
        sim.schedule_event(event)
        
        # Schedule block movements
        current_time = departure_time
        for i, block in enumerate(journey['blocks']):
            entry_time = current_time
            exit_time = entry_time + 50  # 50 time units per block
            
            event = TrainEnterBlockEvent(
                entry_time, journey['train_id'], block.block_id, exit_time
            )
            sim.schedule_event(event)
            
            current_time = exit_time + 10  # 10 time units between blocks
        
        # Schedule arrival at destination
        event = TrainArriveStationEvent(
            current_time, journey['train_id'], journey['to_station'], current_time + 30
        )
        sim.schedule_event(event)
    
    # Run the simulation
    print("\nRunning simulation...")
    sim.run_complete()
    
    # Print simulation logs
    print("\nSimulation logs:")
    sim.print_logs(limit=20)  # Show first 20 logs
    
    # Print simulation statistics
    print("\nSimulation statistics:")
    stats = sim.get_simulation_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

def optimize_kalyan_schedule():
    """Optimize a schedule for the Kalyan network."""
    # Load the railway graph
    rg = load_graph_from_default()
    
    print("\n" + "="*50)
    print("=== KALYAN NETWORK SCHEDULE OPTIMIZATION ===")
    print("="*50)
    
    # Get all stations for creating a schedule
    stations = list(rg.stations.keys())
    if len(stations) < 3:
        print("Not enough stations for schedule optimization")
        return
    
    # Create a schedule to optimize
    schedule = {
        'trains': [
            {
                'train_id': 'EXPRESS_KALYAN',
                'priority': 3,  # High priority express train
                'route': stations[:3],  # First 3 stations
                'min_travel_times': [0, 60, 75],  # Minutes between stations
                'dwell_times': [5, 3]  # Minutes at each intermediate station
            },
            {
                'train_id': 'LOCAL_KALYAN',
                'priority': 1,  # Lower priority local train
                'route': stations[:3],  # Same route as express
                'min_travel_times': [0, 80, 95],  # Slower than express
                'dwell_times': [10, 8]  # Longer stops
            },
            {
                'train_id': 'FREIGHT_KALYAN',
                'priority': 2,  # Medium priority freight train
                'route': stations[1:4] if len(stations) >= 4 else stations[1:],  # Different route
                'min_travel_times': [0, 90, 100] if len(stations) >= 4 else [0, 90],
                'dwell_times': [15, 10] if len(stations) >= 4 else [15]
            }
        ],
        'constraints': {
            'min_headway': 10,  # Minimum time between trains
            'max_delay': 30  # Maximum allowed delay
        }
    }
    
    # Optimize the schedule
    print("\nOptimizing train schedule...")
    start_time = time.time()
    result = optimize_schedule(schedule)
    end_time = time.time()
    
    # Print results
    print(f"\nSchedule optimization completed in {end_time - start_time:.4f} seconds")
    print(f"Status: {result['status']}")
    
    if 'schedule' in result:
        print("\nOptimized schedule:")
        for train_id, stops in result['schedule'].items():
            print(f"\n  {train_id}:")
            for stop in stops:
                print(f"    {stop['station']}: arrive={stop.get('arrival_time', 'N/A')}, depart={stop.get('departure_time', 'N/A')}")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--info":
            print_kalyan_info()
        elif sys.argv[1] == "--simulation":
            run_kalyan_simulation()
        elif sys.argv[1] == "--optimization":
            optimize_kalyan_schedule()
        else:
            print("Unknown option. Use --info, --simulation, or --optimization")
    else:
        print_kalyan_info()
        print("\nRun with --simulation or --optimization to see additional demos")

if __name__ == "__main__":
    main()