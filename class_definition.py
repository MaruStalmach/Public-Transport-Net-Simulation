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
    def __init__(self, id, stops, transport_net, max_capacity=30):
        self.id = id
        self.route = stops
        self.transport_net = transport_net
        self.current_stop = stops[0]
        self.passengers = []
        self.max_capacity = max_capacity
        self.position_index = 0
        self.progress = 0.0
        self.direction = 1

    def has_delay(self, current_stop, next_stop, current_minute):
        is_rush = (420 <= current_minute <= 540) or (960 <= current_minute <= 1080)
        base_time = self.transport_net.graph[current_stop][next_stop]["travel_time"]
        is_busy = self.transport_net.graph[current_stop][next_stop]["busy"]
        return base_time * 1.5 if is_rush or is_busy else base_time

    def vehicle_process(self, env):
        while True:
            if self.direction == 1:
                route_indices = list(range(len(self.route) - 1))
            else:
                route_indices = list(range(len(self.route) - 1, 0, -1))

            for i in route_indices:
                current_stop = self.route[i]
                next_stop = self.route[i + 1] if self.direction == 1 else self.route[i - 1]

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

                # Passengers get off
                exiting = [p for p in self.passengers if p.destination == next_stop]
                for p in exiting:
                    self.transport_net.log_event(f"{p.id} gets off at {next_stop}")
                    self.passengers.remove(p)

                # Passengers board
                waiting = self.transport_net.passenger_queues[next_stop]
                boarding = []

                for p in waiting:
                    if p.destination in self.route:
                        passenger_idx = self.route.index(p.destination)
                        stop_idx = self.route.index(next_stop)

                        if (self.direction == 1 and passenger_idx > stop_idx) or \
                           (self.direction == -1 and passenger_idx < stop_idx):
                            if len(self.passengers) < self.max_capacity:
                                boarding.append(p)
                                self.passengers.append(p)
                                self.transport_net.log_event(f"{p.id} boards at {next_stop}")
                            else:
                                raise ValueError

                for p in boarding:
                    self.transport_net.passenger_queues[next_stop].remove(p)

            self.direction *= -1

class TransportNet:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.vehicles = []
        self.env = simpy.Environment()
        self.passenger_queues = {}
        self.log_buffer = []
        self.last_logged_minute = -1

    def add_connection(self, A, B, travel_time, busy=False):
        self.graph.add_edge(A, B, travel_time=travel_time, busy=busy)
        self.graph.add_edge(B, A, travel_time=travel_time, busy=busy)
        if A not in self.passenger_queues:
            self.passenger_queues[A] = []
        if B not in self.passenger_queues:
            self.passenger_queues[B] = []

    def add_vehicle(self, vehicle):
        self.vehicles.append(vehicle)

    def passenger_generator(self, interval=5, peak_hours=(7*60, 9*60, 16*60, 18*60)):
        id = 0
        while True:
            current_minute = self.env.now % 1440
            is_peak = (peak_hours[0] <= current_minute <= peak_hours[1]) or \
                      (peak_hours[2] <= current_minute <= peak_hours[3])
            is_night = 0 <= current_minute <= 4 * 60

            if is_peak:
                spawn_interval = random.randint(1, max(1, interval // 2))
            elif is_night:
                spawn_interval = random.randint(10, 30)
            else:
                spawn_interval = random.randint(5, 10)

            yield self.env.timeout(spawn_interval)

            origin, destination = random.sample(list(self.graph.nodes()), 2)
            p = Passenger(f"Passenger{id}", origin, destination, self.env.now, transport_net=self)
            self.passenger_queues[origin].append(p)
            self.log_event(f"{p.id} appears at {origin} -> {destination}")
            id += 1

    def log_event(self, message):
        self.log_buffer.append(message)

    def run_env(self):
        for v in self.vehicles:
            self.env.process(v.vehicle_process(self.env))
        self.env.process(self.passenger_generator())

        def tick():
            while True:
                yield self.env.timeout(1)

        self.env.process(tick())
        self.env.run()

    def run_simulation(self):
        sim_thread = threading.Thread(target=self.run_env)
        sim_thread.start()

        while sim_thread.is_alive():
            current_minute = int(self.env.now % 1440)

            if current_minute != self.last_logged_minute:
                print(f"[{get_time(self.env.now)}]", end='')

                if self.log_buffer:
                    print()
                    for msg in self.log_buffer:
                        print(msg)
                    self.log_buffer = []
                else:
                    print(" ...")

                self.last_logged_minute = current_minute

            time.sleep(1)  # always sleep a real second
