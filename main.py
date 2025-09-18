# main.py
from utils.loader import load_graph_from_default
from utils import analysis
from utils import optimization
from utils.simulation import SimulationEngine, TrainEnterBlockEvent, TrainArriveStationEvent, optimization_conflict_handler
import pprint
import time
import sys

def demo():
    pp = pprint.PrettyPrinter(indent=2)

    # Load the railway graph
    rg = load_graph_from_default()
    rg.print_summary()

    # --- Reservation demo ---
    t1 = rg.get_track("T1")
    if t1:
        b0 = t1.blocks[0]
        print("\nTrying to occupy", b0.block_id)
        ok = b0.occupy("EXP100", entry_time=0.0, expected_exit_time=300.0)
        print("occupied ok:", ok)
        rg.print_summary()

        print("\nReleasing block")
        b0.release(actual_exit_time=305.0)
        rg.print_summary()

        # Populate history for analysis - Add more comprehensive test data
        for i, blk in enumerate(t1.blocks):
            # Multiple occupations per block for better analysis
            for j in range(2):  # 2 trains per block
                train_id = f"EXP{i}_{j}"
                entry_time = i * 50 + j * 25
                expected_exit = (i + 1) * 50 + j * 25
                actual_exit = expected_exit + (5 if i % 2 == 0 else 2)  # Some delay
                
                blk.occupy(train_id, entry_time=entry_time, expected_exit_time=expected_exit)
                blk.release(actual_exit_time=actual_exit)

        # Add some station pass events if stations have history support
        for station_id, station in rg.stations.items():
            if hasattr(station, 'log_event'):
                for i in range(3):  # 3 trains passing through each station
                    station.log_event("pass", {"train_id": f"PASS{i}", "time": i * 100})

    # --- Analysis demo ---
    print("\n" + "="*50)
    print("=== RAILWAY ANALYSIS RESULTS ===")
    print("="*50)

    # Connectivity stats
    try:
        stats = analysis.connectivity_stats(rg)
        print("\n📊 CONNECTIVITY STATISTICS:")
        pp.pprint(stats)
    except Exception as e:
        print(f"❌ Error in connectivity analysis: {e}")

    # Busiest stations
    try:
        busiest = analysis.busiest_stations(rg, top_k=3)
        print(f"\n🚉 TOP 3 BUSIEST STATIONS:")
        for i, (station_id, connections) in enumerate(busiest, 1):
            print(f"  {i}. {station_id}: {connections} connections")
    except Exception as e:
        print(f"❌ Error in busiest stations analysis: {e}")

    # Shortest path example
    try:
        nodes = list(rg.stations.keys())
        if len(nodes) >= 2:
            dist, path = analysis.shortest_path(rg, nodes[0], nodes[-1])
            print(f"\n🛤️  SHORTEST PATH ({nodes[0]} → {nodes[-1]}):")
            print(f"   Route: {' → '.join(path)}")
            print(f"   Distance: {dist:.2f} km")
        else:
            print("\n🛤️  SHORTEST PATH: Not enough stations for path analysis")
    except Exception as e:
        print(f"❌ Error in shortest path analysis: {e}")

    # Block utilization
    try:
        all_blocks = []
        for track in rg.tracks.values():
            all_blocks.extend(track.blocks)
        
        block_util = analysis.block_utilization(all_blocks, total_time=600.0)
        print(f"\n🚦 BLOCK UTILIZATION ANALYSIS ({len(all_blocks)} blocks):")
        
        # Show summary statistics
        if block_util:
            total_usage = sum(data['usage_count'] for data in block_util.values())
            avg_duration = sum(data['avg_duration'] for data in block_util.values()) / len(block_util)
            print(f"   Total block occupations: {total_usage}")
            print(f"   Average occupation duration: {avg_duration:.2f} time units")
            
            # Show top 5 most used blocks
            sorted_blocks = sorted(block_util.items(), key=lambda x: x[1]['usage_count'], reverse=True)[:5]
            print("   Most utilized blocks:")
            for block_id, data in sorted_blocks:
                print(f"     {block_id}: {data['usage_count']} uses, avg {data['avg_duration']:.2f}s")
        else:
            print("   No block utilization data available")
            
    except Exception as e:
        print(f"❌ Error in block utilization analysis: {e}")

    # Station utilization
    try:
        station_util = analysis.station_utilization(rg, total_time=600.0)
        print(f"\n🚉 STATION UTILIZATION ANALYSIS:")
        
        total_passes = sum(data['pass_count'] for data in station_util.values())
        print(f"   Total train passages: {total_passes}")
        
        if any(data['pass_count'] > 0 for data in station_util.values()):
            print("   Station activity:")
            for station_id, data in station_util.items():
                if data['pass_count'] > 0:
                    print(f"     {station_id}: {data['pass_count']} passes, {data['avg_passes_per_hour']:.2f} passes/hour")
        else:
            print("   No station passage data available")
            
    except Exception as e:
        print(f"❌ Error in station utilization analysis: {e}")

    # Average delay
    try:
        avg_delay = analysis.average_delay(rg)
        print(f"\n⏰ AVERAGE DELAY ANALYSIS:")
        if avg_delay > 0:
            print(f"   Average delay: {avg_delay:.2f} time units")
            if avg_delay > 10:
                print("   ⚠️  High delay detected - consider capacity improvements")
            elif avg_delay > 5:
                print("   ⚡ Moderate delay - monitor closely")
            else:
                print("   ✅ Low delay - good performance")
        else:
            print("   No delay data available or no delays detected")
    except Exception as e:
        print(f"❌ Error in delay analysis: {e}")

    # Scenario comparison (comparing current state with itself as demo)
    try:
        comp = analysis.compare_scenarios(rg, rg)
        print(f"\n📈 SCENARIO COMPARISON:")
        print(f"   This is a demo comparison (before vs after identical)")
        print(f"   Average delay before: {comp['avg_delay_before']:.2f}")
        print(f"   Average delay after: {comp['avg_delay_after']:.2f}")
        print(f"   Delay improvement: {comp['delay_improvement']:.2f}")
    except Exception as e:
        print(f"❌ Error in scenario comparison: {e}")

    # Station pass counts
    try:
        passes = analysis.station_pass_counts(rg.stations.values())
        print(f"\n🚂 STATION PASS COUNTS:")
        total_passes = sum(passes.values())
        if total_passes > 0:
            for station_id, count in passes.items():
                if count > 0:
                    print(f"   {station_id}: {count} trains")
        else:
            print("   No train passage data recorded")
    except Exception as e:
        print(f"❌ Error in station pass count analysis: {e}")

    print("\n" + "="*50)
    print("=== ANALYSIS COMPLETE ===")
    print("="*50)

def optimization_demo():
    pp = pprint.PrettyPrinter(indent=2)
    print("\n" + "="*50)
    print("=== OPTIMIZATION DEMO ===")
    print("="*50)
    
    # Load the railway graph
    rg = load_graph_from_default()
    
    try:
        # --- Conflict Resolution Demo ---
        print("\n🔄 CONFLICT RESOLUTION DEMO:")
        
        # Create a conflict scenario with two trains requesting the same block
        train_requests = [
            {
                'train_id': 'EXP101',
                'priority': 3,  # High priority express train
                'requested_blocks': [
                    {'block_id': 'T1_B0', 'entry_time': 100, 'exit_time': 200},
                    {'block_id': 'T1_B1', 'entry_time': 200, 'exit_time': 300}
                ]
            },
            {
                'train_id': 'LOC202',
                'priority': 1,  # Lower priority local train
                'requested_blocks': [
                    {'block_id': 'T1_B0', 'entry_time': 150, 'exit_time': 250},  # Conflict with EXP101
                    {'block_id': 'T2_B0', 'entry_time': 300, 'exit_time': 400}
                ]
            }
        ]
        
        print("Resolving conflicts between trains:")
        for train in train_requests:
            print(f"  {train['train_id']} (Priority {train['priority']}) requesting {len(train['requested_blocks'])} blocks")
        
        start_time = time.time()
        result = optimization.resolve_conflicts(rg, train_requests)
        end_time = time.time()
        
        print(f"\nConflict resolution completed in {end_time - start_time:.2f} seconds")
        print(f"Status: {result['status']}")
        
        if 'allocations' in result:
            print("\nBlock allocations:")
            for train_id, blocks in result['allocations'].items():
                print(f"  {train_id}: {len(blocks)} blocks allocated")
                for block in blocks:
                    print(f"    {block['block_id']}: {block['entry_time']} → {block['exit_time']}")
    
        # --- Schedule Optimization Demo ---
        print("\n📅 SCHEDULE OPTIMIZATION DEMO:")
        
        # Create a scheduling scenario
        trains = [
            {
                'train_id': 'EXP101',
                'priority': 3,
                'route': ['KYN', 'TNA', 'DVL'],  # Route through stations
                'min_dwell_time': 60,  # 60 seconds minimum at each station
                'desired_arrival': {'DVL': 600}  # Desired arrival time at final station
            },
            {
                'train_id': 'LOC202',
                'priority': 1,
                'route': ['TNA', 'DVL', 'ABH'],
                'min_dwell_time': 120,
                'desired_arrival': {'ABH': 900}
            }
        ]
        
        print("Optimizing schedules for trains:")
        for train in trains:
            print(f"  {train['train_id']} (Priority {train['priority']}) route: {' → '.join(train['route'])}")
        
        start_time = time.time()
        result = optimization.optimize_schedule(rg, trains, horizon=1800)  # 30 minute horizon
        end_time = time.time()
        
        print(f"\nSchedule optimization completed in {end_time - start_time:.2f} seconds")
        print(f"Status: {result['status']}")
        
        if 'schedules' in result:
            print("\nOptimized schedules:")
            for train_id, schedule in result['schedules'].items():
                print(f"\n  {train_id} schedule:")
                for stop in schedule:
                    station = stop['station_id']
                    arr = stop['arrival_time']
                    dep = stop['departure_time']
                    delay_info = f" (Delay: {stop['delay']} sec)" if stop['delay'] is not None else ""
                    print(f"    {station}: Arrive {arr} sec, Depart {dep} sec{delay_info}")
            
            if 'stats' in result:
                print(f"\nOptimization stats:")
                print(f"  Objective value: {result['stats']['objective_value']}")
                print(f"  Solver time: {result['stats']['wall_time']:.2f} seconds")
    
    except Exception as e:
        print(f"❌ Error in optimization demo: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    print("=== OPTIMIZATION DEMO COMPLETE ===")
    print("="*50)

def simulation_demo():
    print("\n" + "="*50)
    print("=== RAILWAY SIMULATION DEMO ===")
    print("="*50)
    
    # Load the railway graph
    rg = load_graph_from_default()
    
    # Create simulation engine
    sim = SimulationEngine(rg)
    
    # Register conflict handler that uses optimization
    sim.register_conflict_handler(optimization_conflict_handler)
    
    # Get some blocks and stations for the demo
    blocks = []
    for track_id, track in rg.tracks.items():
        blocks.extend(track.blocks)
    
    if not blocks:
        print("No blocks available for simulation")
        return
    
    # Schedule some train movements
    print("\nScheduling train movements...")
    
    # Train 1: Regular schedule
    train1_id = "EXPRESS_101"
    current_time = 0.0
    
    for i, block in enumerate(blocks[:5]):  # First 5 blocks
        entry_time = current_time
        exit_time = entry_time + 50.0  # 50 time units per block
        
        event = TrainEnterBlockEvent(
            entry_time, train1_id, block.block_id, exit_time
        )
        sim.schedule_event(event)
        
        print(f"  Scheduled {train1_id} to enter {block.block_id} at t={entry_time}")
        current_time = exit_time + 5.0  # 5 time units between blocks
    
    # Train 2: Conflicting schedule (overlaps with Train 1)
    train2_id = "LOCAL_202"
    current_time = 20.0  # Start a bit later to create conflict
    
    for i, block in enumerate(blocks[2:7]):  # Blocks 2-6 (overlapping with train 1)
        entry_time = current_time
        exit_time = entry_time + 60.0  # 60 time units per block (slower train)
        
        event = TrainEnterBlockEvent(
            entry_time, train2_id, block.block_id, exit_time
        )
        sim.schedule_event(event)
        
        print(f"  Scheduled {train2_id} to enter {block.block_id} at t={entry_time}")
        current_time = exit_time + 10.0  # 10 time units between blocks
    
    # Add a station arrival if stations exist
    if rg.stations:
        station_id = next(iter(rg.stations.keys()))
        station_event = TrainArriveStationEvent(
            300.0, "EXPRESS_303", station_id, 350.0
        )
        sim.schedule_event(station_event)
        print(f"  Scheduled EXPRESS_303 to arrive at {station_id} at t=300.0")
    
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
    
    print("\n" + "="*50)
    print("=== SIMULATION COMPLETE ===")
    print("="*50)


if __name__ == "__main__":
    if "--simulation" in sys.argv:
        simulation_demo()
    elif "--optimization" in sys.argv:
        optimization_demo()
    else:
        demo()
        print("\nRun with --simulation or --optimization to see additional demos")