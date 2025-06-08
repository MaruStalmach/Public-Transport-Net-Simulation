import pygame
import threading
from class_definition import TransportNet, get_time
from collections import deque
from config import SimulationConfig

class RealTimeMetrics:
    def __init__(self, transport_network, max_points=100):
        self.tn = transport_network
        self.max_points = max_points
        
        self.time_data = deque(maxlen=max_points)
        self.satisfaction_data = deque(maxlen=max_points)
        self.total_delay_data = deque(maxlen=max_points)
        self.avg_wait_time_data = deque(maxlen=max_points)
        self.vehicle_utilization_data = deque(maxlen=max_points)
        self.passengers_in_system_data = deque(maxlen=max_points)
        self.on_time_performance_data = deque(maxlen=max_points)
        self.cost_efficiency_data = deque(maxlen=max_points)
        
        self.data_lock = threading.Lock()
        
    def calculate_satisfaction(self):
        '''calculates customer satisfaction using params for decay settable in config'''
        total_satisfaction = 0
        passenger_count = 0
        
        for stop, queue in self.tn.passenger_queues.items():
            for passenger in queue:
                wait_time = self.tn.env.now - passenger.spawn_time
                satisfaction = max(0, 100 - wait_time * self.tn.satisfaction_decay_waiting)  
                total_satisfaction += satisfaction
                passenger_count += 1
        
        for vehicle in self.tn.vehicles:
            for passenger in vehicle.passengers:
                travel_time = self.tn.env.now - passenger.spawn_time
                satisfaction = max(0, 100 - travel_time * self.tn.satisfaction_decay_traveling)  
                total_satisfaction += satisfaction
                passenger_count += 1
                
        return total_satisfaction / passenger_count if passenger_count > 0 else 100

    def calculate_total_delay(self):
        '''calculates total delay in the system'''
        total_delay = 0
        
        for stop, queue in self.tn.passenger_queues.items():
            for passenger in queue:
                total_delay += max(0, self.tn.env.now - passenger.spawn_time)
        
        for vehicle in self.tn.vehicles:
            for passenger in vehicle.passengers:
                total_delay += max(0, self.tn.env.now - passenger.spawn_time)
                
        return total_delay
    
    def calculate_avg_wait_time(self):
        '''calculates avg wait time of a passenger'''
        total_wait = 0
        passenger_count = 0
        
        for stop, queue in self.tn.passenger_queues.items():
            for passenger in queue:
                total_wait += self.tn.env.now - passenger.spawn_time
                passenger_count += 1
                
        for vehicle in self.tn.vehicles:
            for passenger in vehicle.passengers:
                total_wait += self.tn.env.now - passenger.spawn_time
                passenger_count += 1
                
        return total_wait / passenger_count if passenger_count > 0 else 0

    def calculate_vehicle_utilization(self):
        '''calculates % of usage of vehicle capacity'''
        if not self.tn.vehicles:
            return 0
            
        total_utilization = 0
        for vehicle in self.tn.vehicles:
            utilization = len(vehicle.passengers) / vehicle.vehicle_capacity * 100
            total_utilization += utilization
            
        return total_utilization / len(self.tn.vehicles)
    
    def calculate_passengers_in_system(self):
        '''counts total number of passengers currently en route'''
        total = 0
        for queue in self.tn.passenger_queues.values():
            total += len(queue)
        for vehicle in self.tn.vehicles:
            total += len(vehicle.passengers)
        return total
    
    def calculate_on_time_performance(self):
        """Calculate percentage of on-time arrivals"""
        on_time_count = 0
        total_arrivals = 0
        
        for vehicle in self.tn.vehicles:
            # assuming any delay < 2 minutes is on time
            if hasattr(vehicle, "arrival_deviation") and vehicle.arrival_deviation <= 2:
                on_time_count += 1
            total_arrivals += 1
            
        return (on_time_count / total_arrivals) * 100 if total_arrivals > 0 else 100


    def update_metrics(self):
        """Update all metrics for current simulation time"""
        with self.data_lock:
            current_time = self.tn.env.now
            satisfaction = self.calculate_satisfaction()
            total_delay = self.calculate_total_delay()
            avg_wait = self.calculate_avg_wait_time()
            utilization = self.calculate_vehicle_utilization()
            passengers = self.calculate_passengers_in_system()
            on_time = self.calculate_on_time_performance()
            
            self.time_data.append(current_time)
            self.satisfaction_data.append(satisfaction)
            self.total_delay_data.append(total_delay)
            self.avg_wait_time_data.append(avg_wait)
            self.vehicle_utilization_data.append(utilization)
            self.passengers_in_system_data.append(passengers)
            self.on_time_performance_data.append(on_time)


def count_destinations(passengers):
    counts = {}
    for p in passengers:
        if p.destination in counts:
            counts[p.destination] += 1
        else:
            counts[p.destination] = 1
    return counts

def show_destinations(dest_counts, font, surface, position, color):
    x, y = position
    for dest, count in dest_counts.items():
        y += 15
        label = font.render(f"{dest}: {count}", True, color)
        surface.blit(label, (x, y))

def draw_plot(surface, x, y, width, height, time_data, value_data, title, color, max_value=None):
    """Draw a simple line plot within the specified area"""
    if len(time_data) < 2:
        return
    

    pygame.draw.rect(surface, (200, 200, 200), (x, y, width, height), 1)

    min_time = min(time_data)
    max_time = max(time_data)
    time_range = max_time - min_time if max_time > min_time else 1
    
    if not max_value:
        max_value = max(value_data) if value_data else 1
    
   
    if max_value == 0:
        max_value = 1  
 
    for i in range(5):
        pygame.draw.line(surface, (220, 220, 220), 
                         (x, y + i * height//5),
                         (x + width, y + i * height//5), 1)
    

    points = []
    for i, (t, v) in enumerate(zip(time_data, value_data)):
        px = x + width * (t - min_time) / time_range
        py = y + height - height * v / max_value
        points.append((px, py))
    
    if len(points) > 1:
        pygame.draw.lines(surface, color, False, points, 2)
    
    font = pygame.font.SysFont("Arial", 14)
    title_label = font.render(title, True, (0, 0, 0))
    surface.blit(title_label, (x + 5, y + 5))
    
    value_label = font.render(f"{value_data[-1]:.1f}", True, color)
    surface.blit(value_label, (x + width - 50, y + 5))


def run_simulation_with_plots(
        tn: TransportNet, 
        config: SimulationConfig
    ) -> RealTimeMetrics:

    """Run simulation with both pygame visualization and embedded plots"""
    
    metrics_tracker = RealTimeMetrics(tn)
    
    pygame.init()
    screen = pygame.display.set_mode((1400, 700))  
    pygame.display.set_caption("Transport Network Simulation with Metrics")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 14)
    
    stops_coords = tn.stop_locations 

    for line in tn.bus_lines:
        for departure in line.schedule:
            tn.env.process(tn.create_vehicle(line, departure))

    tn.env.process(tn.passenger_generator(interval=5))
    tn.env.process(tn.report_status())

    paused = False
    selected_stop = None
    selected_bus = None
    minute = 0

    print("Simulation started! Press SPACE to pause/resume. Close window to stop.")

    try:
        while minute < config.simulation_duration:
            if not paused:
                tn.env.run(until=minute + 1)
                minute += 1
                
                metrics_tracker.update_metrics()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return metrics_tracker

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos

                    for name, (x, y) in stops_coords.items():
                        if (mx-x)**2 + (my-y)**2 <= 8**2:
                            selected_stop = name
                            selected_bus = None
                            paused = True
                            break

                    for vehicle in tn.vehicles:
                        x, y = vehicle.get_coordinates()
                        if (mx-x)**2 + (my-y)**2 <= 6**2:
                            selected_bus = vehicle
                            selected_stop = None
                            paused = True
                            break

                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    paused = not paused

            screen.fill((255, 255, 255))

            network_width = 600
            network_surface = pygame.Surface((network_width, 700))
            network_surface.fill((255, 255, 255))
            
            for start_stop, end_stop, data in tn.graph.edges(data=True):
                color = (0, 0, 0)
                if data.get("busy"):
                    color = (255, 0, 0)
                pygame.draw.line(network_surface, color, 
                                stops_coords[start_stop], 
                                stops_coords[end_stop], 2)

            for name, position in stops_coords.items():
                x, y = position
                pygame.draw.circle(network_surface, (0, 0, 255), position, 8)
                label = font.render(f"{name} ({len(tn.passenger_queues.get(name, []))})", True, (0, 0, 0))
                network_surface.blit(label, (x+10, y-15))

                if selected_stop == name:
                    count = count_destinations(tn.passenger_queues[name])
                    show_destinations(count, font, network_surface, 
                                     (position[0] + 10, position[1]), (100, 100, 100))

            for vehicle in tn.vehicles:
                x, y = vehicle.get_coordinates()

                if vehicle.id.startswith("Line1"):
                    color = (255, 0, 0)
                elif vehicle.id.startswith("Line2"):
                    color = (0, 255, 0)
                else:
                    color = (128, 128, 128)

                pygame.draw.circle(network_surface, color, (int(x), int(y)), 6)
                name = vehicle.id.split("_")[0]
                label = font.render(f"{name}: {len(vehicle.passengers)}", True, (0, 0, 0))
                network_surface.blit(label, (int(x)+8, int(y)-5))

                if vehicle == selected_bus:
                    count = count_destinations(vehicle.passengers)
                    show_destinations(count, font, network_surface, 
                                     (int(x) + 8, int(y) - 5), (50, 50, 50))

            time_text = f"Time: {get_time(minute)}"
            time_font = pygame.font.SysFont("Arial", 20)
            time_label = time_font.render(time_text, True, (0, 0, 0))
            network_surface.blit(time_label, (10, 10))
            
            status_text = "PAUSED" if paused else "RUNNING"
            status_color = (255, 0, 0) if paused else (0, 128, 0)
            status_label = font.render(status_text, True, status_color)
            network_surface.blit(status_label, (10, 35))
            
            screen.blit(network_surface, (0, 0))
            
            plot_x = network_width + 10
            plot_width = 380
            plot_height = 200
            vertical_spacing = 10
            horizontal_spacing = 10
            
        
            plot_positions = [
                (plot_x, 20),  # Row 1, Col 1
                (plot_x + plot_width + horizontal_spacing, 20),  # Row 1, Col 2
                (plot_x, 20 + plot_height + vertical_spacing),  # Row 2, Col 1
                (plot_x + plot_width + horizontal_spacing, 20 + plot_height + vertical_spacing),  # Row 2, Col 2
                (plot_x, 20 + 2*(plot_height + vertical_spacing)),  # Row 3, Col 1
                (plot_x + plot_width + horizontal_spacing, 20 + 2*(plot_height + vertical_spacing))  # Row 3, Col 2
            ]
            
            metrics = [
                ("Passenger Satisfaction (%)", metrics_tracker.satisfaction_data, (0, 100, 200), 100),
                ("Total System Delay (min)", metrics_tracker.total_delay_data, (200, 0, 50), None),
                ("Avg Wait Time (min)", metrics_tracker.avg_wait_time_data, (0, 150, 0), None),
                ("Vehicle Utilization (%)", metrics_tracker.vehicle_utilization_data, (128, 0, 128), 100),
                ("Passengers in System", metrics_tracker.passengers_in_system_data, (0, 200, 200), None),
                ("On-Time Performance (%)", metrics_tracker.on_time_performance_data, (255, 165, 0), 100)
            ]
            
            with metrics_tracker.data_lock:
                if metrics_tracker.time_data:
                    for i, (title, data, color, max_val) in enumerate(metrics):
                        if data:
                            x, y = plot_positions[i]
                            # calculate max value if not provided
                            actual_max = max_val if max_val else max(data) * 1.1
                            draw_plot(screen, x, y, plot_width, plot_height,
                                     list(metrics_tracker.time_data),
                                     list(data),
                                     title, color,
                                     max_value=actual_max)

            pygame.display.flip()
            clock.tick(30) # cap at 30 fps
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        
    finally:
        pygame.quit()
    
    return metrics_tracker