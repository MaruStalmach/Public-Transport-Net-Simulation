import simpy
import networkx as nx
import random

class Passenger:
    def __init__(self, id, origin, destination, spawn_time):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.spawn_time = spawn_time
        self.status = "waiting"

class Vehicle:
    def __init__(self, id, stops, transport_net, max_capacity=40):
        self.id = id
        self.route = stops
        self.transport_net = transport_net
        self.current_stop = stops[0]
        self.passengers = []
        self.max_capacity = max_capacity
        self.position_index = 0
        self.progress = 0.0
        self.direction = 1  # 1 = do przodu, -1 = w tył

    def vehicle_process(self, env):
        while True:
            # wybór indeksów przystanków w zależności od kierunku
            if self.direction == 1:
                route_indices = list(range(len(self.route) - 1))
            else:
                route_indices = list(range(len(self.route) - 1, 0, -1))

            for i in route_indices:
                if self.direction == 1:
                    current_stop = self.route[i]
                    next_stop = self.route[i + 1]
                else:
                    current_stop = self.route[i]
                    next_stop = self.route[i - 1]

                # sprawdzenie połączenia
                if not self.transport_net.transport_net.has_edge(current_stop, next_stop):
                    raise KeyError(f"no connection between {current_stop} and {next_stop}")

                travel_time = self.transport_net.transport_net[current_stop][next_stop]["travel_time"]

                # symulacja przejazdu między przystankami
                steps = 10
                for step in range(steps):
                    self.position_index = i
                    self.progress = step / steps
                    yield env.timeout(travel_time / steps)

                self.current_stop = next_stop
                print(f"[{env.now}] {self.id} arrived at {next_stop}")

                # wysiadający pasażerowie
                exiting = [p for p in self.passengers if p.destination == next_stop]
                for p in exiting:
                    print(f"{p.id} gets off at {next_stop}")
                    self.passengers.remove(p)

                # wsiadający pasażerowie
                waiting = self.transport_net.passenger_queues[next_stop]
                boarding = []

                for p in waiting:
                    if p.destination in self.route:
                        passenger_idx = self.route.index(p.destination)
                        stop_idx = self.route.index(next_stop)

                        # kierunek zgodny z jazdą pojazdu
                        if (self.direction == 1 and passenger_idx > stop_idx) or \
                           (self.direction == -1 and passenger_idx < stop_idx):
                            if len(self.passengers) < self.max_capacity:
                                boarding.append(p)
                                self.passengers.append(p)
                                print(f"{p.id} boards {self.id} at {next_stop}")

                for p in boarding:
                    self.transport_net.passenger_queues[next_stop].remove(p)

            # zmiana kierunku jazdy po dotarciu do końca trasy
            self.direction *= -1

class TransportNet:
    def __init__(self):
        self.transport_net = nx.DiGraph()
        self.vehicles = []
        self.env = simpy.Environment()
        self.passenger_queues = {}

    def add_connection(self, A, B, travel_time):
        self.transport_net.add_edge(A, B, travel_time=travel_time)
        self.transport_net.add_edge(B, A, travel_time=travel_time)

        if A not in self.passenger_queues:
            self.passenger_queues[A] = []
        if B not in self.passenger_queues:
            self.passenger_queues[B] = []

    def add_vehicle(self, vehicle):
        self.vehicles.append(vehicle)

    def passenger_generator(self, interval=5):
        id = 0
        while True:
            yield self.env.timeout(random.randint(1, interval))
            nodes_list = list(self.transport_net.nodes())
            origin, destination = random.sample(nodes_list, 2)
            p = Passenger(f"Passenger{id}", origin, destination, self.env.now)

            if origin not in self.passenger_queues:
                self.passenger_queues[origin] = []
            self.passenger_queues[origin].append(p)

            print(f"[{self.env.now}] {p.id} appears at {origin} -> {destination}")
            id += 1

    def run_simulation(self, until=30):
        for v in self.vehicles:
            self.env.process(v.vehicle_process(self.env))
        self.env.process(self.passenger_generator())
        self.env.run(until=until)
