# utils/optimization.py
from ortools.sat.python import cp_model
from models.railway_graph import RailwayGraph
from typing import Dict, List, Tuple, Optional
import time

class OptimizationSolver:
    """Optimization solver for railway conflicts and disruptions using OR-Tools CP-SAT."""
    
    def __init__(self, railway_graph: RailwayGraph):
        self.graph = railway_graph
        self.model = None
        self.solver = None
        self.variables = {}
        self.solution = None
        
    def setup_model(self):
        """Initialize a new CP-SAT model."""
        self.model = cp_model.CpModel()
        self.variables = {}
        
    def solve(self, time_limit_seconds=30):
        """Solve the model with a time limit."""
        self.solver = cp_model.CpSolver()
        self.solver.parameters.max_time_in_seconds = time_limit_seconds
        status = self.solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.solution = self.solver
            return True
        return False
    
    def get_solution_info(self):
        """Get information about the solution."""
        if not self.solution:
            return {"status": "No solution found"}
            
        return {
            "status": "Solution found",
            "objective_value": self.solver.ObjectiveValue(),
            "wall_time": self.solver.WallTime(),
        }


class ConflictResolver(OptimizationSolver):
    """Resolves conflicts between trains requesting the same blocks."""
    
    def __init__(self, railway_graph: RailwayGraph):
        super().__init__(railway_graph)
        
    def resolve_conflicts(self, train_requests: List[Dict]):
        """
        Resolve conflicts between multiple trains requesting blocks.
        
        Args:
            train_requests: List of dictionaries with train information:
                [
                    {
                        'train_id': str,
                        'priority': int,  # Higher number = higher priority
                        'requested_blocks': [
                            {'block_id': str, 'entry_time': float, 'exit_time': float}
                        ]
                    }
                ]
                
        Returns:
            Dictionary mapping train_id to list of allocated blocks with times
        """
        self.setup_model()
        
        # Create variables for each train's block allocation
        # 1 means block is allocated to train, 0 means it's not
        for train in train_requests:
            train_id = train['train_id']
            self.variables[train_id] = {}
            
            for block_req in train['requested_blocks']:
                block_id = block_req['block_id']
                self.variables[train_id][block_id] = self.model.NewBoolVar(f"{train_id}_{block_id}")
        
        # Add constraints to prevent conflicts (no two trains can use the same block at overlapping times)
        for i, train1 in enumerate(train_requests):
            for j, train2 in enumerate(train_requests):
                if i >= j:  # Skip duplicate pairs and self-comparisons
                    continue
                    
                train1_id = train1['train_id']
                train2_id = train2['train_id']
                
                # Find overlapping block requests
                for block1 in train1['requested_blocks']:
                    for block2 in train2['requested_blocks']:
                        if block1['block_id'] == block2['block_id']:
                            # Check if times overlap
                            if not (block1['exit_time'] <= block2['entry_time'] or 
                                    block1['entry_time'] >= block2['exit_time']):
                                # Times overlap, so both trains can't use this block
                                block_id = block1['block_id']
                                # At least one of the trains must not use this block
                                self.model.Add(
                                    self.variables[train1_id][block_id] + 
                                    self.variables[train2_id][block_id] <= 1
                                )
        
        # Objective: Maximize priority-weighted allocation
        objective_terms = []
        for train in train_requests:
            train_id = train['train_id']
            priority = train['priority']
            
            for block_req in train['requested_blocks']:
                block_id = block_req['block_id']
                # Multiply by priority to favor high-priority trains
                objective_terms.append(
                    priority * self.variables[train_id][block_id]
                )
        
        self.model.Maximize(sum(objective_terms))
        
        # Solve the model
        solved = self.solve()
        if not solved:
            return {"status": "No solution found"}
        
        # Extract solution
        result = {"status": "Solution found", "allocations": {}}
        for train in train_requests:
            train_id = train['train_id']
            result["allocations"][train_id] = []
            
            for block_req in train['requested_blocks']:
                block_id = block_req['block_id']
                if self.solution.Value(self.variables[train_id][block_id]) == 1:
                    result["allocations"][train_id].append({
                        "block_id": block_id,
                        "entry_time": block_req['entry_time'],
                        "exit_time": block_req['exit_time']
                    })
        
        return result


class ScheduleOptimizer(OptimizationSolver):
    """Optimizes train schedules to minimize delays and maximize throughput."""
    
    def __init__(self, railway_graph: RailwayGraph):
        super().__init__(railway_graph)
        
    def optimize_schedule(self, trains: List[Dict], horizon: int = 3600):
        """
        Optimize train schedules to minimize delays and maximize throughput.
        
        Args:
            trains: List of dictionaries with train information:
                [
                    {
                        'train_id': str,
                        'priority': int,  # Higher number = higher priority
                        'route': List[str],  # List of station IDs in order
                        'min_dwell_time': int,  # Minimum time to spend at each station
                        'desired_arrival': Dict[str, int]  # Station ID -> desired arrival time
                    }
                ]
            horizon: Time horizon for scheduling in seconds
            
        Returns:
            Dictionary with optimized schedule
        """
        self.setup_model()
        
        # Create variables for arrival and departure times at each station
        for train in trains:
            train_id = train['train_id']
            route = train['route']
            self.variables[train_id] = {}
            
            for i, station_id in enumerate(route):
                # Arrival time at station
                self.variables[train_id][f"arr_{station_id}"] = self.model.NewIntVar(
                    0, horizon, f"{train_id}_arr_{station_id}"
                )
                
                # Departure time from station
                self.variables[train_id][f"dep_{station_id}"] = self.model.NewIntVar(
                    0, horizon, f"{train_id}_dep_{station_id}"
                )
                
                # Minimum dwell time constraint
                min_dwell = train['min_dwell_time']
                self.model.Add(
                    self.variables[train_id][f"dep_{station_id}"] >= 
                    self.variables[train_id][f"arr_{station_id}"] + min_dwell
                )
                
                # Travel time to next station
                if i < len(route) - 1:
                    next_station = route[i + 1]
                    # Find track between stations
                    travel_time = self._get_travel_time(station_id, next_station)
                    
                    # Arrival at next station >= departure from current + travel time
                    self.model.Add(
                        self.variables[train_id][f"arr_{next_station}"] >= 
                        self.variables[train_id][f"dep_{station_id}"] + travel_time
                    )
        
        # Add constraints for platform capacity
        self._add_platform_constraints(trains)
        
        # Add constraints to prevent track conflicts
        self._add_track_conflict_constraints(trains)
        
        # Objective: Minimize weighted sum of delays
        objective_terms = []
        for train in trains:
            train_id = train['train_id']
            priority = train['priority']
            
            for station_id, desired_time in train.get('desired_arrival', {}).items():
                if station_id in train['route']:
                    # Create a delay variable
                    delay_var = self.model.NewIntVar(
                        0, horizon, f"{train_id}_delay_{station_id}"
                    )
                    
                    # Delay = max(0, actual_arrival - desired_arrival)
                    self.model.Add(
                        delay_var >= 
                        self.variables[train_id][f"arr_{station_id}"] - desired_time
                    )
                    
                    # Weight by priority (higher priority = more important to minimize delay)
                    objective_terms.append(priority * delay_var)
        
        self.model.Minimize(sum(objective_terms))
        
        # Solve the model
        solved = self.solve(time_limit_seconds=60)  # Allow more time for complex schedules
        if not solved:
            return {"status": "No solution found"}
        
        # Extract solution
        result = {"status": "Solution found", "schedules": {}}
        for train in trains:
            train_id = train['train_id']
            route = train['route']
            result["schedules"][train_id] = []
            
            for i, station_id in enumerate(route):
                arr_time = self.solution.Value(self.variables[train_id][f"arr_{station_id}"])
                dep_time = self.solution.Value(self.variables[train_id][f"dep_{station_id}"])
                
                # Calculate delay if there's a desired arrival time
                delay = None
                if station_id in train.get('desired_arrival', {}):
                    desired = train['desired_arrival'][station_id]
                    delay = max(0, arr_time - desired)
                
                result["schedules"][train_id].append({
                    "station_id": station_id,
                    "arrival_time": arr_time,
                    "departure_time": dep_time,
                    "delay": delay
                })
        
        # Add solution statistics
        result["stats"] = {
            "objective_value": self.solver.ObjectiveValue(),
            "wall_time": self.solver.WallTime(),
        }
        
        return result
    
    def _get_travel_time(self, from_station: str, to_station: str) -> int:
        """Calculate travel time between two stations."""
        # Try to find a direct track between stations
        for neighbor, track in self.graph.get_neighbors(from_station):
            if neighbor == to_station:
                # Calculate time based on length and speed
                if track.max_speed_kph > 0:
                    # Convert to seconds
                    return int((track.length_km / track.max_speed_kph) * 3600)
        
        # If no direct track, use shortest path
        from utils.graph_ops import shortest_path
        path, cost = shortest_path(self.graph, from_station, to_station, by="time")
        if path:
            # Convert to seconds (cost is in hours)
            return int(cost * 3600)
        
        # Default fallback
        return 600  # 10 minutes default
    
    def _add_platform_constraints(self, trains: List[Dict]):
        """Add constraints for station platform capacity."""
        # Group trains by station
        station_trains = {}
        for train in trains:
            train_id = train['train_id']
            for station_id in train['route']:
                if station_id not in station_trains:
                    station_trains[station_id] = []
                station_trains[station_id].append({
                    'train_id': train_id,
                    'arr_var': self.variables[train_id][f"arr_{station_id}"],
                    'dep_var': self.variables[train_id][f"dep_{station_id}"]
                })
        
        # For each station, ensure platform capacity is not exceeded
        for station_id, trains_at_station in station_trains.items():
            station = self.graph.get_station(station_id)
            if not station:
                continue
                
            max_platforms = station.platforms
            
            # For each pair of trains, either they don't overlap in time
            # or we need to ensure total concurrent trains <= platform count
            for i, train1 in enumerate(trains_at_station):
                for j, train2 in enumerate(trains_at_station):
                    if i >= j:  # Skip duplicate pairs and self-comparisons
                        continue
                    
                    # Create a boolean variable indicating if trains overlap
                    overlap_var = self.model.NewBoolVar(f"overlap_{train1['train_id']}_{train2['train_id']}_{station_id}")
                    
                    # Train 2 arrives before Train 1 departs AND Train 1 arrives before Train 2 departs
                    self.model.Add(train2['arr_var'] < train1['dep_var']).OnlyEnforceIf(overlap_var)
                    self.model.Add(train1['arr_var'] < train2['dep_var']).OnlyEnforceIf(overlap_var)
                    
                    # If more than max_platforms trains would overlap, prevent this solution
                    if len(trains_at_station) > max_platforms:
                        # This is a simplified approach - for a complete solution, we would need
                        # to track all overlapping trains and ensure the count never exceeds max_platforms
                        # But that requires more complex constraints beyond this example
                        pass
    
    def _add_track_conflict_constraints(self, trains: List[Dict]):
        """Add constraints to prevent track conflicts between trains."""
        # For each pair of trains, check if they share track segments
        for i, train1 in enumerate(trains):
            for j, train2 in enumerate(trains):
                if i >= j:  # Skip duplicate pairs and self-comparisons
                    continue
                
                train1_id = train1['train_id']
                train2_id = train2['train_id']
                
                # Find common track segments
                for idx1 in range(len(train1['route']) - 1):
                    from1 = train1['route'][idx1]
                    to1 = train1['route'][idx1 + 1]
                    
                    for idx2 in range(len(train2['route']) - 1):
                        from2 = train2['route'][idx2]
                        to2 = train2['route'][idx2 + 1]
                        
                        # Check if segments overlap
                        if (from1 == from2 and to1 == to2) or (from1 == to2 and to1 == from2):
                            # These trains use the same track segment
                            # Train 1 must exit segment before Train 2 enters, or vice versa
                            
                            # Train 1 exit time = departure from to1
                            # Train 2 entry time = arrival at from2 (or to2 if direction is reversed)
                            
                            # Create a boolean variable for ordering
                            t1_before_t2 = self.model.NewBoolVar(f"{train1_id}_before_{train2_id}_seg_{from1}_{to1}")
                            
                            # Either Train 1 finishes before Train 2 starts
                            self.model.Add(
                                self.variables[train1_id][f"dep_{to1}"] <= 
                                self.variables[train2_id][f"arr_{from2}"]
                            ).OnlyEnforceIf(t1_before_t2)
                            
                            # Or Train 2 finishes before Train 1 starts
                            self.model.Add(
                                self.variables[train2_id][f"dep_{to2}"] <= 
                                self.variables[train1_id][f"arr_{from1}"]
                            ).OnlyEnforceIf(t1_before_t2.Not())


def resolve_conflicts(graph: RailwayGraph, train_requests: List[Dict]):
    """Convenience function to resolve conflicts."""
    resolver = ConflictResolver(graph)
    return resolver.resolve_conflicts(train_requests)


def optimize_schedule(graph: RailwayGraph, trains: List[Dict], horizon: int = 3600):
    """Convenience function to optimize schedules."""
    optimizer = ScheduleOptimizer(graph)
    return optimizer.optimize_schedule(trains, horizon)