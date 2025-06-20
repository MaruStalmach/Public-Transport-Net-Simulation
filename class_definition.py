import simpy
import networkx as nx
import random
import time
import threading

def get_time(now):
    minutes = int(now) % 1440
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def time_to_minutes(time_str):
    hours, mins = map(int, time_str.split(':'))
    return hours * 60 + mins

class Passenger:
    def __init__(self, id, origin, destination, spawn_time, transport_net):
        self.satisfaction = 100
        self.id = id
        self.origin = origin
        self.destination = destination
        self.spawn_time = spawn_time
        self.status = "waiting"
        self.route = nx.dijkstra_path(transport_net.graph, origin, destination, weight='travel_time')

        path_key = (origin, destination)
        if path_key in transport_net.path_cache:
            self.route = transport_net.path_cache[path_key]
        else:
            self.route = nx.dijkstra_path(transport_net.graph, origin, destination, weight='travel_time')
            transport_net.path_cache[path_key] = self.route

    # def deduct_from_satisfaction(self):
    #     if self.satisfaction > 0:
    #         self.satisfaction -= 1

class Vehicle:
    def __init__(self, id, stops, transport_net, vehicle_capacity=30, wait_time=15):
        self.id = id
        self.route = stops
        self.transport_net = transport_net
        self.current_stop = stops[0]
        self.passengers = []
        self.vehicle_capacity = vehicle_capacity
        self.position_index = 0
        self.progress = 0.0
        self.direction = 1
        self.wait_time = wait_time

        self.distance_traveled = 0
        self.start_time = transport_net.env.now
        self.scheduled_arrivals = {}  # Track scheduled vs actual arrivals
        self.arrival_deviation = []

    def has_delay(self, current_stop, next_stop, current_minute):
        is_rush = (420 <= current_minute <= 540) or (960 <= current_minute <= 1080)
        base_time = self.transport_net.graph[current_stop][next_stop]["travel_time"]
        is_busy = self.transport_net.graph[current_stop][next_stop]["busy"]
        return base_time * 1.5 if is_rush or is_busy else base_time

    def record_position(self, env, stop_info, lat, lon, next_stop, in_transit=False, progress=0):

        destination_counts = {}
        for p in self.passengers:
            if p.destination not in destination_counts:
                destination_counts[p.destination] = 0
            destination_counts[p.destination] += 1

        self.transport_net.bus_tracks[self.id].append({
            "time": int(env.now),
            "stop": stop_info,
            "lat": lat,
            "lon": lon,
            "direction": self.direction,
            "passenger_count": len(self.passengers),
            "vehicle_capacity": self.vehicle_capacity,
            "destinations": dict(sorted(destination_counts.items())),
            "next_stop": next_stop,
            "in_transit": in_transit,
            "progress": progress if in_transit else 0
        })

    def vehicle_process(self, env):
        while True:
            if self.direction == 1:
                path_sequence = range(len(self.route) - 1)
            else:
                path_sequence = range(len(self.route) - 1, 0, -1)
            for i in path_sequence:
                current_stop = self.route[i]
                if self.direction == 1:
                    next_stop = self.route[i + 1]
                else:
                    next_stop = self.route[i - 1]

                if self.direction != 1:
                    self.transport_net.log_event(f"{self.id} departing from {current_stop} -> {next_stop}")
                if not self.transport_net.graph.has_edge(current_stop, next_stop):
                    raise KeyError(f"no connection between {current_stop} and {next_stop}")

                travel_time = self.has_delay(current_stop, next_stop, env.now % 1440)

                steps = 10
                for step in range(steps):
                    self.position_index = i
                    self.progress = step / steps

                    # record position during movement
                    if current_stop in self.transport_net.stop_locations and next_stop in self.transport_net.stop_locations:
                        lat, lon = self.get_coordinates()
                        self.record_position(env,f"{current_stop} -> {next_stop}", lat, lon, next_stop, in_transit=True, progress=self.progress)

                    yield env.timeout(travel_time / steps)

                self.current_stop = next_stop
                self.transport_net.log_event(f"{self.id} arrived at {next_stop}")

                lat, lon = self.transport_net.stop_locations.get(next_stop, (None, None))

                if self.direction == 1 and i + 2 < len(self.route):
                    next_stop_value = self.route[i + 2]
                elif self.direction == -1 and i - 2 >= 0:
                    next_stop_value = self.route[i - 2]
                else:
                    next_stop_value = "Terminal"

                # record position at the stop
                self.record_position(env, next_stop, lat, lon, next_stop_value, in_transit=False)

                exiting = [p for p in self.passengers if p.destination == next_stop]
                exiting_count = len(exiting)
                for p in exiting:
                    self.transport_net.log_event(f"{p.id} gets off at {next_stop}")
                    self.passengers.remove(p)
                    self.transport_net.completed_passengers.append(p)

                waiting = self.transport_net.passenger_queues[next_stop]
                boarding = []

                for p in waiting:
                    if p.destination in self.route:
                        passenger_idx = self.route.index(p.destination)
                        stop_idx = self.route.index(next_stop)
                        if (self.direction == 1 and passenger_idx > stop_idx) or (self.direction == -1 and passenger_idx < stop_idx):
                            if len(self.passengers) < self.vehicle_capacity:
                                boarding.append(p)
                                self.passengers.append(p)
                                self.transport_net.log_event(f"{p.id} boards at {next_stop}")

                for p in boarding:
                    self.transport_net.passenger_queues[next_stop].remove(p)

                boarding_count = len(boarding)
                self.transport_net.log_event(f"{self.id} arrived at {next_stop}: exiting {exiting_count}, boarding {boarding_count}")

                # wait at each stop for one minute
                self.transport_net.log_event(f"{self.id} is at {self.current_stop}")
                yield env.timeout(1)

            # last stop
            if len(self.route) > 1:
                # board up to capacity
                new_board = 0
                q = self.transport_net.passenger_queues[self.current_stop]
                while q and len(self.passengers) < self.vehicle_capacity:
                    p = q.pop(0)
                    self.passengers.append(p)
                    new_board += 1
                    self.transport_net.log_event(f"{p.id} boards at {self.current_stop}")

                # boarding during wait
                remaining_wait = self.wait_time
                while remaining_wait > 0:
                    q = self.transport_net.passenger_queues[self.current_stop]
                    while q and len(self.passengers) < self.vehicle_capacity:
                        p = q.pop(0)
                        self.passengers.append(p)
                        self.transport_net.log_event(f"{p.id} boards bus {self.id} at {self.current_stop} during wait")
                    self.transport_net.log_event(
                        f"{self.id} waiting at {self.current_stop} ({remaining_wait}m left), passengers: {len(self.passengers)}")
                    yield env.timeout(1)
                    remaining_wait -= 1

            self.direction *= -1


    def get_coordinates(self):
        idx = self.position_index
        # get the next stop based on the direction
        if self.direction == 1 and idx < len(self.route) - 1:
            next_idx = idx + 1
        elif self.direction == -1 and idx > 0:
            next_idx = idx - 1
        else:
            next_idx = idx

        a, b = self.route[idx], self.route[next_idx]
        x1, y1 = self.transport_net.stop_locations[a]
        x2, y2 = self.transport_net.stop_locations[b]
        t = self.progress
        
        # approximate the position between stops
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        return x, y

class BusLine:
    def __init__(self, name, stops, schedule, capacity, wait_time=5):
        self.name = name
        self.stops = stops
        self.schedule = [time_to_minutes(t) for t in schedule]
        self.capacity = capacity
        self.wait_time = wait_time
       

class TransportNet:
    def __init__(self, config):
        self.graph = nx.DiGraph()
        self.config = config
        self.vehicles = []
        self.env = simpy.Environment()
        self.passenger_queues = {}
        self.log_buffer = []
        self.last_logged_minute = -1
        self.simulation_running = False
        self.bus_lines = []
        self.stop_locations = {}
        self.bus_tracks = {}
        self.stop_snapshots = {}

        self.completed_passengers = []

        self.completed_passengers = []
        self.path_cache = {}

    def setup_transport_network(self):
        # add stop locations
        self.stop_locations = self.config.stop_locations
        
        # initialise params from config
        self.satisfaction_decay_waiting = self.config.satisfaction_decay_waiting
        self.satisfaction_decay_traveling = self.config.satisfaction_decay_traveling
        self.rush_hour_traffic_factor = self.config.rush_hour_traffic_factor
        self.busy_route_factor = self.config.busy_route_factor
    
        # add connections
        for conn in self.config.connections:
            self.add_connection(conn[0], conn[1], conn[2], busy=conn[3])
        
        # add buslines & capacity
        for line_config in self.config.bus_lines:
            self.add_bus_line(
                name=line_config["name"],
                stops=line_config["stops"],
                schedule=line_config["schedule"],
                capacity=line_config.get("capacity", 60),
                wait_time=line_config["wait_time"]
            )
        

    def add_connection(self, A, B, travel_time, busy=False):
        '''defines a new connection between stops on a busline'''
        self.graph.add_edge(A, B, travel_time=travel_time, busy=busy)
        self.graph.add_edge(B, A, travel_time=travel_time, busy=busy)
        if A not in self.passenger_queues:
            self.passenger_queues[A] = []
        if B not in self.passenger_queues:
            self.passenger_queues[B] = []

    def add_bus_line(self, name, stops, schedule, capacity, wait_time=5):
        '''defines a new busline in the simulation'''
        self.bus_lines.append(BusLine(name, stops, schedule, capacity, wait_time))

    def schedule_vehicles(self):
        for line in self.bus_lines:
            for dep_time in line.schedule:
                self.env.process(self.create_vehicle(line, dep_time))

    def create_vehicle(self, line, departure_time):
        yield self.env.timeout(departure_time)
        vehicle_id = f"{line.name}_{get_time(departure_time)}"

        vehicle = Vehicle(vehicle_id, line.stops, self, wait_time=line.wait_time)
        self.vehicles.append(vehicle)
        self.bus_tracks[vehicle_id] = []
        self.env.process(vehicle.vehicle_process(self.env))

    def passenger_generator(self, interval=5, peak_hours=(7*60, 9*60, 16*60, 18*60)):
        '''generates passengers on the stops; number of generated passengers depends on the hour - rush hours yield more passengers'''
        id = 0

        while True:
            current_minute = self.env.now % 1440
            is_peak = (peak_hours[0] <= current_minute <= peak_hours[1]) or (peak_hours[2] <= current_minute <= peak_hours[3])
            is_night = 0 <= current_minute <= 4 * 60
            
            if is_peak:
                spawn_interval = random.randint(1, max(1, interval // 2))
            elif is_night:
                spawn_interval = random.randint(10, 30)
            else:
                spawn_interval = random.randint(5, 10)
            
            yield self.env.timeout(spawn_interval)

            for _ in range(5):
                origin, destination = random.sample(list(self.graph.nodes()), 2)
                p = Passenger(f"Passenger{id}", origin, destination, self.env.now, transport_net=self)
                self.passenger_queues[origin].append(p)
                self.log_event(f"{p.id} appears at {origin} -> {destination}")
                id += 1

    def report_status(self):
        while True:
            print(f"\n=== Status Report at {get_time(self.env.now)} ===")

            # record passenger queue information for visualization
            current_time = int(self.env.now)
            self.stop_snapshots[current_time] = {}

            # report on bus stops
            for stop in sorted(self.passenger_queues):
                passengers = self.passenger_queues[stop]
                dest_counts = {}
                for p in passengers:
                    if p.destination not in dest_counts:
                        dest_counts[p.destination] = 0
                    dest_counts[p.destination] += 1
                dest_str = ", ".join([f"{k}: {v}" for k, v in dest_counts.items()])
                passengers_info = "No passengers"
                if len(dest_counts) > 0:
                    passengers_info = f"{len(passengers)} waiting - {dest_str}"
                print(f"Bus stop {stop}: {passengers_info}")

                # store for visualization
                self.stop_snapshots[current_time][stop] = {
                    "count": len(passengers),
                    "destinations": dict(sorted(dest_counts.items()))
                }

            # report on vehicles
            for vehicle in self.vehicles:
                print(f"Line {vehicle.id}: {vehicle.current_stop}, direction: {vehicle.direction}, "
                      f"passengers: {len(vehicle.passengers)}/{vehicle.vehicle_capacity}")
            if self.log_buffer:
                print("\n--- Log Buffer ---")
                for msg in self.log_buffer:
                    print(msg)
                self.log_buffer.clear()
            print("================================\n")
            yield self.env.timeout(1)

    def log_event(self, message):
        self.log_buffer.append(message)

    def run_env(self):
        for v in self.vehicles:
            self.env.process(v.vehicle_process(self.env))
        self.env.process(self.passenger_generator())
        self.env.process(self.report_status())
        self.schedule_vehicles()

        def clock_tick():
            while self.simulation_running:
                self.env.run(until=self.env.now + 1)

                print(f"[{get_time(self.env.now)}]", end='')

                if self.log_buffer:
                    print()
                    for msg in self.log_buffer:
                        print(msg)
                    self.log_buffer = []
                else:
                    print(" ...")

                time.sleep(0.5)

        return clock_tick

    def run_simulation(self):
        self.simulation_running = True
        clock_ticker = self.run_env()
        sim_thread = threading.Thread(target=clock_ticker)
        sim_thread.daemon = True
        sim_thread.start()

        try:
            while sim_thread.is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nSimulation stopped by user.")
            self.simulation_running = False
            sim_thread.join(timeout=1.0)