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

class Vehicle:
    def __init__(self, id, stops, transport_net, max_capacity=30, wait_time=15):
        self.id = id
        self.route = stops
        self.transport_net = transport_net
        self.current_stop = stops[0]
        self.passengers = []
        self.max_capacity = max_capacity
        self.position_index = 0
        self.progress = 0.0
        self.direction = 1
        self.wait_time = wait_time

    def has_delay(self, current_stop, next_stop, current_minute):
        is_rush = (420 <= current_minute <= 540) or (960 <= current_minute <= 1080)
        base_time = self.transport_net.graph[current_stop][next_stop]["travel_time"]
        is_busy = self.transport_net.graph[current_stop][next_stop]["busy"]
        return base_time * 1.5 if is_rush or is_busy else base_time

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
                    yield env.timeout(travel_time / steps)

                self.current_stop = next_stop
                self.transport_net.log_event(f"{self.id} arrived at {next_stop}")

                exiting = [p for p in self.passengers if p.destination == next_stop]
                exiting_count = len(exiting)
                for p in exiting:
                    self.transport_net.log_event(f"{p.id} gets off at {next_stop}")
                    self.passengers.remove(p)

                waiting = self.transport_net.passenger_queues[next_stop]
                boarding = []

                for p in waiting:
                    if p.destination in self.route:
                        passenger_idx = self.route.index(p.destination)
                        stop_idx = self.route.index(next_stop)
                        if (self.direction == 1 and passenger_idx > stop_idx) or (self.direction == -1 and passenger_idx < stop_idx):
                            if len(self.passengers) < self.max_capacity:
                                boarding.append(p)
                                self.passengers.append(p)
                                self.transport_net.log_event(f"{p.id} boards at {next_stop}")

                for p in boarding:
                    self.transport_net.passenger_queues[next_stop].remove(p)

                boarding_count = len(boarding)
                self.transport_net.log_event(f"{self.id} arrived at {next_stop}: exiting {exiting_count}, boarding {boarding_count}")

            # last stop
            if len(self.route) > 1:
                # board up to capacity
                new_board = 0
                q = self.transport_net.passenger_queues[self.current_stop]
                while q and len(self.passengers) < self.max_capacity:
                    p = q.pop(0)
                    self.passengers.append(p)
                    new_board += 1
                    self.transport_net.log_event(f"{p.id} boards at {self.current_stop}")

                # boarding during wait
                remaining_wait = self.wait_time
                while remaining_wait > 0:
                    q = self.transport_net.passenger_queues[self.current_stop]
                    while q and len(self.passengers) < self.max_capacity:
                        p = q.pop(0)
                        self.passengers.append(p)
                        self.transport_net.log_event(f"{p.id} boards bus {self.id} at {self.current_stop} during wait")
                    self.transport_net.log_event(
                        f"{self.id} waiting at {self.current_stop} ({remaining_wait}m left), passengers: {len(self.passengers)}")
                    yield env.timeout(1)
                    remaining_wait -= 1

            self.direction *= -1


class BusLine:
    def __init__(self, name, stops, schedule, wait_time=5):
        self.name = name
        self.stops = stops
        self.schedule = [time_to_minutes(t) for t in schedule]
        self.wait_time = wait_time


class TransportNet:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.vehicles = []
        self.env = simpy.Environment()
        self.passenger_queues = {}
        self.log_buffer = []
        self.last_logged_minute = -1
        self.simulation_running = False
        self.bus_lines = []

    def add_connection(self, A, B, travel_time, busy=False):
        self.graph.add_edge(A, B, travel_time=travel_time, busy=busy)
        self.graph.add_edge(B, A, travel_time=travel_time, busy=busy)
        if A not in self.passenger_queues:
            self.passenger_queues[A] = []
        if B not in self.passenger_queues:
            self.passenger_queues[B] = []

    def add_bus_line(self, name, stops, schedule, wait_time=5):
        self.bus_lines.append(BusLine(name, stops, schedule, wait_time))

    def schedule_vehicles(self):
        for line in self.bus_lines:
            for dep_time in line.schedule:
                self.env.process(self.create_vehicle(line, dep_time))

    def create_vehicle(self, line, departure_time):
        yield self.env.timeout(departure_time)
        vehicle_id = f"{line.name}_{get_time(departure_time)}"
        vehicle = Vehicle(vehicle_id, line.stops, self, wait_time=line.wait_time)
        self.vehicles.append(vehicle)
        self.env.process(vehicle.vehicle_process(self.env))

    def passenger_generator(self, interval=5, peak_hours=(7*60, 9*60, 16*60, 18*60)):
        id = 0
        while True:
            # current_minute = self.env.now % 1440
            # is_peak = (peak_hours[0] <= current_minute <= peak_hours[1]) or \
            #           (peak_hours[2] <= current_minute <= peak_hours[3])
            # is_night = 0 <= current_minute <= 4 * 60
            #
            # if is_peak:
            #     spawn_interval = random.randint(1, max(1, interval // 2))
            # elif is_night:
            #     spawn_interval = random.randint(10, 30)
            # else:
            #     spawn_interval = random.randint(5, 10)
            #
            # yield self.env.timeout(spawn_interval)

            yield self.env.timeout(1)
            for _ in range(5):
                origin, destination = random.sample(list(self.graph.nodes()), 2)
                p = Passenger(f"Passenger{id}", origin, destination, self.env.now, transport_net=self)
                self.passenger_queues[origin].append(p)
                self.log_event(f"{p.id} appears at {origin} -> {destination}")
                id += 1

    def report_status(self):
        while True:
            print(f"\n=== Status Report at {get_time(self.env.now)} ===")

            # Report on bus stops
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

            # Report on vehicles
            for vehicle in self.vehicles:
                print(f"Line {vehicle.id}: {vehicle.current_stop}, direction: {vehicle.direction}, "
                      f"passengers: {len(vehicle.passengers)}/{vehicle.max_capacity}")
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