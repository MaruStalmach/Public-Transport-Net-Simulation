import simpy
import networkx as nx
import random

def get_time(now):
    '''
    Global - for displaying time in 24h format
    '''
    minutes = int(now) % 1440
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

class Passenger:
    def __init__(self, id, origin, destination, spawn_time):
        self.satisfaction = 100
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
        self.direction = 1  
    
    def has_delay(self, current_stop, next_stop, current_minute):
        '''
        Simulates delays in trafic during rush hours
        TODO: add constraints on certain streets for custom 'main streets'
        '''
        is_rush = (420 <= current_minute <= 540) or (960 <= current_minute <= 1080)
        base_time = self.transport_net.transport_net[current_stop][next_stop]["travel_time"]
        is_busy = self.transport_net.transport_net[current_stop][next_stop]["busy"]
        
        return base_time * 1.5 if is_rush or is_busy else base_time
    
    def vehicle_process(self, env):
        while True:
            # wybór indeksów przystanków w zależności od kierunku 1 normalnie, -1 powrotny
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

                if not self.transport_net.transport_net.has_edge(current_stop, next_stop):
                    raise KeyError(f"no connection between {current_stop} and {next_stop}")
                
                travel_time = self.has_delay(current_stop, next_stop, env.now % 1440)
        
                # symulacja przejazdu między przystankami
                steps = 10
                for step in range(steps):
                    self.position_index = i
                    self.progress = step / steps
                    yield env.timeout(travel_time / steps)

                self.current_stop = next_stop
                print(f"{get_time(env.now)} {self.id} arrived at {next_stop}")

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

    def add_connection(self, A, B, travel_time, busy=False):
        self.transport_net.add_edge(A, B, travel_time=travel_time, busy=busy)
        self.transport_net.add_edge(B, A, travel_time=travel_time, busy=busy)
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
                spawn_interval = random.randint(1, interval)  
            elif is_night:
                spawn_interval = random.randint(20, 40)  
            else:
                spawn_interval = random.randint(5, 10)

            yield self.env.timeout(spawn_interval)

            origin, destination = random.sample(list(self.transport_net.nodes()), 2)
            p = Passenger(f"Passenger{id}", origin, destination, self.env.now)
            self.passenger_queues[origin].append(p)
            print(f"{get_time(self.env.now)} {p.id} appears at {origin} -> {destination}")
            id += 1

        
    def run_simulation(self):
        for v in self.vehicles:
            self.env.process(v.vehicle_process(self.env))
        self.env.process(self.passenger_generator())
        self.env.run()
