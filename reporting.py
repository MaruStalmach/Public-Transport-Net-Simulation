# reporting.py
import json
import os
import matplotlib.pyplot as plt
from datetime import datetime

class SimulationReport:
    def __init__(self, config, metrics_tracker, transport_net):
        self.config = config
        self.metrics = metrics_tracker
        self.tn = transport_net
        self.start_time = datetime.now()
        self.end_time = None
        self.summary = {}
        

    def finalize(self):
        '''collect final statistics and generate report'''
        self.end_time = datetime.now()
        self.calculate_summary()
        
        if self.config.save_reports:
            self.save_report()
            self.generate_plots()
        
        return self.summary
    
    def calculate_summary(self):
        '''calculate key performance indicators'''
        # basic simulation info
        self.summary["simulation_duration"] = self.config.simulation_duration
        self.summary["real_duration"] = (self.end_time - self.start_time).total_seconds()
        
        # passenger statistics
        total_passengers = sum(len(q) for q in self.tn.passenger_queues.values())
        for vehicle in self.tn.vehicles:
            total_passengers += len(vehicle.passengers)
            
        self.summary["total_passengers"] = total_passengers
        
        # satisfaction metrics
        if self.metrics.satisfaction_data:
            self.summary["avg_satisfaction"] = sum(self.metrics.satisfaction_data) / len(self.metrics.satisfaction_data)
            self.summary["min_satisfaction"] = min(self.metrics.satisfaction_data)
            self.summary["final_satisfaction"] = self.metrics.satisfaction_data[-1]
        
        # delay metrics
        if self.metrics.total_delay_data:
            self.summary["total_delay"] = sum(self.metrics.total_delay_data)
            self.summary["avg_delay_per_passenger"] = (
                self.summary["total_delay"] / total_passengers if total_passengers > 0 else 0
            )
        
        # wait time metrics
        if self.metrics.avg_wait_time_data:
            self.summary["avg_wait_time"] = sum(self.metrics.avg_wait_time_data) / len(self.metrics.avg_wait_time_data)
            
        # vehicle utilization
        if self.metrics.vehicle_utilization_data:
            self.summary["avg_vehicle_utilization"] = (
                sum(self.metrics.vehicle_utilization_data) / len(self.metrics.vehicle_utilization_data))
        
        # system efficiency
        if self.metrics.system_efficiency_data:
            self.summary["avg_system_efficiency"] = (
                sum(self.metrics.system_efficiency_data) / len(self.metrics.system_efficiency_data))
        
        # # cost efficiency estimate
        # self.summary["estimated_cost_per_passenger"] = self.estimate_cost_efficiency()
        
        # # on-time performance
        # self.summary["on_time_performance"] = self.calculate_on_time_performance()
    
    # def estimate_cost_efficiency(self):
    #     """Estimate operational cost per passenger (simplified model)"""
    #     # cost factors
    #     vehicle_cost_per_minute = 0.10  # $0.10 per minute per vehicle
    #     distance_cost_per_km = 0.20  # $0.20 per km
        
    #     total_cost = 0
    #     total_passengers = self.summary["total_passengers"]
        
    #     # talculate costs for each vehicle
    #     for vehicle in self.tn.vehicles:
    #         # Time-based cost
    #         operating_time = self.tn.env.now - vehicle.start_time
    #         time_cost = operating_time * vehicle_cost_per_minute
            
    #         # distance-based cost (simplified - using Euclidean distance)
    #         distance = 0
    #         for i in range(len(vehicle.route) - 1):
    #             x1, y1 = self.tn.stop_locations[vehicle.route[i]]
    #             x2, y2 = self.tn.stop_locations[vehicle.route[i+1]]
    #             distance += ((x2-x1)**2 + (y2-y1)**2)**0.5 / 100  # scale to km
                
    #         distance_cost = distance * distance_cost_per_km
            
    #         total_cost += time_cost + distance_cost
        
    #     return total_cost / total_passengers if total_passengers > 0 else 0
    
    # def calculate_on_time_performance(self):
    #     """Calculate percentage of on-time arrivals"""
    #     on_time_count = 0
    #     total_arrivals = 0
        
    #     for vehicle in self.tn.vehicles:
    #         # for simplicity, we'll assume any delay < 2 minutes is on time
    #         if hasattr(vehicle, "arrival_deviation") and vehicle.arrival_deviation <= 2:
    #             on_time_count += 1
    #         total_arrivals += 1
            
    #     return (on_time_count / total_arrivals) * 100 if total_arrivals > 0 else 100
    
    def save_report(self):
        """Save report to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.json"
        filepath = os.path.join(self.config.report_directory, filename)
        
        report_data = {
            "config": self.config.__dict__,
            "summary": self.summary,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=4)
            
        return filepath
    
    def generate_plots(self):
        """Generate and save metric plots"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_dir = os.path.join(self.config.report_directory, "plots")
        os.makedirs(plot_dir, exist_ok=True)
        
        # create satisfaction plot
        plt.figure(figsize=(10, 6))
        plt.plot(self.metrics.time_data, self.metrics.satisfaction_data, 'b-')
        plt.title("Passenger Satisfaction Over Time")
        plt.xlabel("Time (minutes)")
        plt.ylabel("Satisfaction (%)")
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(plot_dir, f"satisfaction_{timestamp}.png"))
        plt.close()
        
        # create system efficiency plot
        plt.figure(figsize=(10, 6))
        plt.plot(self.metrics.time_data, self.metrics.system_efficiency_data, 'g-')
        plt.title("System Efficiency Over Time")
        plt.xlabel("Time (minutes)")
        plt.ylabel("Efficiency Score")
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(plot_dir, f"efficiency_{timestamp}.png"))
        plt.close()
        
        # create combined metrics plot
        fig, ax1 = plt.subplots(figsize=(12, 8))
        
        color = 'tab:red'
        ax1.set_xlabel('Time (minutes)')
        ax1.set_ylabel('Delay (minutes)', color=color)
        ax1.plot(self.metrics.time_data, self.metrics.total_delay_data, color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Satisfaction (%)', color=color)
        ax2.plot(self.metrics.time_data, self.metrics.satisfaction_data, color=color)
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title("System Performance: Delay vs Satisfaction")
        fig.tight_layout()
        plt.savefig(os.path.join(plot_dir, f"combined_{timestamp}.png"))
        plt.close()