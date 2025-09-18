# utils/simulation.py
from models.railway_graph import RailwayGraph
from typing import Dict, List, Tuple, Optional, Callable
import heapq
import time

class Event:
    """Base class for simulation events."""
    def __init__(self, time: float, event_type: str):
        self.time = time
        self.event_type = event_type
        
    def __lt__(self, other):
        # For priority queue ordering
        return self.time < other.time
    
    def process(self, simulation):
        """Process this event in the simulation context."""
        raise NotImplementedError("Subclasses must implement process()")


class TrainEnterBlockEvent(Event):
    """Event for a train entering a block."""
    def __init__(self, time: float, train_id: str, block_id: str, exit_time: float):
        super().__init__(time, "train_enter_block")
        self.train_id = train_id
        self.block_id = block_id
        self.exit_time = exit_time
        
    def process(self, simulation):
        """Process train entering a block."""
        # Try to reserve the block
        success = simulation.graph.reserve_block(
            self.block_id, self.train_id, self.time, self.exit_time
        )
        
        if success:
            # Schedule the exit event
            exit_event = TrainExitBlockEvent(
                self.exit_time, self.train_id, self.block_id
            )
            simulation.schedule_event(exit_event)
            
            # Log the successful block entry
            simulation.log(f"Train {self.train_id} entered block {self.block_id} at time {self.time}")
            return True
        else:
            # Block reservation failed (conflict)
            simulation.log(f"CONFLICT: Train {self.train_id} could not enter block {self.block_id} at time {self.time}")
            
            # Notify conflict handlers
            simulation.handle_conflict(self.train_id, self.block_id, self.time, self.exit_time)
            return False


class TrainExitBlockEvent(Event):
    """Event for a train exiting a block."""
    def __init__(self, time: float, train_id: str, block_id: str):
        super().__init__(time, "train_exit_block")
        self.train_id = train_id
        self.block_id = block_id
        
    def process(self, simulation):
        """Process train exiting a block."""
        # Release the block
        success = simulation.graph.release_block(self.block_id)
        
        if success:
            simulation.log(f"Train {self.train_id} exited block {self.block_id} at time {self.time}")
        else:
            simulation.log(f"WARNING: Train {self.train_id} failed to exit block {self.block_id} at time {self.time}")
        
        return success


class TrainArriveStationEvent(Event):
    """Event for a train arriving at a station."""
    def __init__(self, time: float, train_id: str, station_id: str, departure_time: float):
        super().__init__(time, "train_arrive_station")
        self.train_id = train_id
        self.station_id = station_id
        self.departure_time = departure_time
        
    def process(self, simulation):
        """Process train arriving at a station."""
        station = simulation.graph.get_station(self.station_id)
        
        if not station:
            simulation.log(f"ERROR: Station {self.station_id} not found for train {self.train_id}")
            return False
        
        try:
            # Try to occupy a platform
            station.occupy_platform()
            
            # Schedule departure
            departure_event = TrainDepartStationEvent(
                self.departure_time, self.train_id, self.station_id
            )
            simulation.schedule_event(departure_event)
            
            # Log arrival
            simulation.log(f"Train {self.train_id} arrived at station {self.station_id} at time {self.time}")
            
            # Record station event if history tracking is available
            if hasattr(station, 'log_event'):
                station.log_event("arrive", {
                    "train_id": self.train_id,
                    "time": self.time,
                    "departure_time": self.departure_time
                })
                
            return True
            
        except RuntimeError as e:
            # No platforms available
            simulation.log(f"CONFLICT: No platforms available at {self.station_id} for train {self.train_id}")
            
            # Notify conflict handlers
            simulation.handle_station_conflict(self.train_id, self.station_id, self.time, self.departure_time)
            return False


class TrainDepartStationEvent(Event):
    """Event for a train departing from a station."""
    def __init__(self, time: float, train_id: str, station_id: str):
        super().__init__(time, "train_depart_station")
        self.train_id = train_id
        self.station_id = station_id
        
    def process(self, simulation):
        """Process train departing from a station."""
        station = simulation.graph.get_station(self.station_id)
        
        if not station:
            simulation.log(f"ERROR: Station {self.station_id} not found for train {self.train_id}")
            return False
        
        # Release the platform
        station.release_platform()
        
        # Log departure
        simulation.log(f"Train {self.train_id} departed from station {self.station_id} at time {self.time}")
        
        # Record station event if history tracking is available
        if hasattr(station, 'log_event'):
            station.log_event("depart", {
                "train_id": self.train_id,
                "time": self.time
            })
            
        return True


class SimulationEngine:
    """Discrete-event simulation engine for railway operations."""
    
    def __init__(self, railway_graph: RailwayGraph):
        self.graph = railway_graph
        self.event_queue = []  # Priority queue of events
        self.current_time = 0.0
        self.trains = {}  # Train ID -> train state
        self.log_entries = []
        self.conflict_handlers = []
        self.station_conflict_handlers = []
        
    def schedule_event(self, event: Event):
        """Add an event to the simulation queue."""
        heapq.heappush(self.event_queue, event)
        
    def schedule_train_journey(self, train_id: str, route: List[Dict]):
        """
        Schedule a complete train journey through multiple blocks and stations.
        
        Args:
            train_id: Unique identifier for the train
            route: List of dictionaries describing the journey:
                [
                    {
                        'type': 'block',  # or 'station'
                        'id': 'block_id',  # or station_id
                        'enter_time': float,
                        'exit_time': float
                    }
                ]
        """
        for step in route:
            if step['type'] == 'block':
                event = TrainEnterBlockEvent(
                    step['enter_time'], train_id, step['id'], step['exit_time']
                )
                self.schedule_event(event)
            elif step['type'] == 'station':
                event = TrainArriveStationEvent(
                    step['enter_time'], train_id, step['id'], step['exit_time']
                )
                self.schedule_event(event)
        
        # Store train information
        self.trains[train_id] = {
            'route': route,
            'current_position': None,
            'status': 'scheduled'
        }
    
    def run_until(self, end_time: float):
        """Run the simulation until the specified end time."""
        while self.event_queue and self.event_queue[0].time <= end_time:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time
            
            # Process the event
            event.process(self)
    
    def run_complete(self):
        """Run the simulation until all events are processed."""
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time
            
            # Process the event
            event.process(self)
    
    def log(self, message: str):
        """Add a log entry."""
        entry = {
            'time': self.current_time,
            'message': message
        }
        self.log_entries.append(entry)
        
    def register_conflict_handler(self, handler: Callable):
        """Register a function to handle block conflicts."""
        self.conflict_handlers.append(handler)
        
    def register_station_conflict_handler(self, handler: Callable):
        """Register a function to handle station conflicts."""
        self.station_conflict_handlers.append(handler)
        
    def handle_conflict(self, train_id: str, block_id: str, entry_time: float, exit_time: float):
        """Call registered conflict handlers."""
        for handler in self.conflict_handlers:
            handler(self, train_id, block_id, entry_time, exit_time)
            
    def handle_station_conflict(self, train_id: str, station_id: str, arrival_time: float, departure_time: float):
        """Call registered station conflict handlers."""
        for handler in self.station_conflict_handlers:
            handler(self, train_id, station_id, arrival_time, departure_time)
    
    def get_train_position(self, train_id: str):
        """Get the current position of a train."""
        return self.trains.get(train_id, {}).get('current_position')
    
    def update_train_position(self, train_id: str, position_type: str, position_id: str):
        """Update the current position of a train."""
        if train_id in self.trains:
            self.trains[train_id]['current_position'] = {
                'type': position_type,  # 'block' or 'station'
                'id': position_id
            }
    
    def get_simulation_stats(self):
        """Get statistics about the simulation."""
        stats = {
            'current_time': self.current_time,
            'events_processed': len(self.log_entries),
            'events_pending': len(self.event_queue),
            'trains': len(self.trains),
            'conflicts': sum(1 for entry in self.log_entries if 'CONFLICT' in entry['message'])
        }
        return stats
    
    def print_logs(self, limit=None):
        """Print simulation logs."""
        for i, entry in enumerate(self.log_entries):
            if limit and i >= limit:
                print(f"... {len(self.log_entries) - limit} more log entries")
                break
            print(f"[{entry['time']:.2f}] {entry['message']}")


# Integration with optimization module
def optimization_conflict_handler(simulation, train_id, block_id, entry_time, exit_time):
    """Handle conflicts by using the optimization solver."""
    from utils.optimization import resolve_conflicts
    
    # Collect information about all trains currently in the simulation
    train_requests = []
    
    # Add the train that just had a conflict
    train_requests.append({
        'train_id': train_id,
        'priority': 1,  # Default priority
        'requested_blocks': [{
            'block_id': block_id,
            'entry_time': entry_time,
            'exit_time': exit_time
        }]
    })
    
    # Add other trains that might be affected
    # This is a simplified example - in a real system, you would need to
    # gather information about all relevant trains and their block requests
    
    # Resolve conflicts using the optimization solver
    result = resolve_conflicts(simulation.graph, train_requests)
    
    if result['status'] == 'Solution found' and 'allocations' in result:
        # Apply the optimized solution
        for train_id, blocks in result['allocations'].items():
            for block in blocks:
                # Reschedule the train with the new block allocation
                new_event = TrainEnterBlockEvent(
                    block['entry_time'], train_id, block['block_id'], block['exit_time']
                )
                simulation.schedule_event(new_event)
                
                simulation.log(f"RESCHEDULED: Train {train_id} for block {block['block_id']} at time {block['entry_time']}")