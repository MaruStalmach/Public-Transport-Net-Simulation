# reporting.py
import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

class SimulationReport:
    def __init__(self, config, metrics_tracker, transport_net):
        self.config = config
        self.metrics = metrics_tracker
        self.tn = transport_net
        self.start_time = None
        self.end_time = None
        self.summary = {}

    def set_start_time(self):
        """Call this when simulation actually starts"""
        self.start_time = datetime.now()

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
        self.summary["simulation_duration"] = self.config.simulation_duration
        
        if self.start_time and self.end_time:
            self.summary["real_duration"] = (self.end_time - self.start_time).total_seconds()
        else:
            self.summary["real_duration"] = 0.0

        # passenger statistics
        total_passengers = sum(len(q) for q in self.tn.passenger_queues.values())
        for vehicle in self.tn.vehicles:
            total_passengers += len(vehicle.passengers)
        self.summary["total_passengers"] = total_passengers

        # average metrics (those with plots)
        def avg(data):
            return sum(data) / len(data) if data else 0

        self.summary["avg_satisfaction"] = avg(self.metrics.satisfaction_data)
        self.summary["avg_total_delay"] = avg(self.metrics.total_delay_data)
        self.summary["avg_wait_time"] = avg(self.metrics.avg_wait_time_data)
        self.summary["avg_vehicle_utilization"] = avg(self.metrics.vehicle_utilization_data)
        self.summary["avg_passengers_in_system"] = avg(self.metrics.passengers_in_system_data)
        # on_time_performance_data and cost_efficiency_data may be empty if not calculated
        if hasattr(self.metrics, "on_time_performance_data"):
            self.summary["avg_on_time_performance"] = avg(self.metrics.on_time_performance_data)
        if hasattr(self.metrics, "cost_efficiency_data"):
            self.summary["avg_cost_efficiency"] = avg(self.metrics.cost_efficiency_data)

        self.summary["final_satisfaction"] = self.metrics.satisfaction_data[-1] if self.metrics.satisfaction_data else None
        self.summary["final_total_delay"] = self.metrics.total_delay_data[-1] if self.metrics.total_delay_data else None

    def save_report(self):
        """Save simplified report to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.json"
        filepath = os.path.join(self.config.report_directory, filename)

        report_data = {
            "config": {
                "simulation_duration": self.config.simulation_duration,
                "passenger_generation_interval": self.config.passenger_generation_interval,
                "peak_hours": self.config.peak_hours,
                "peak_multiplier": self.config.peak_multiplier,
                "satisfaction_decay_waiting": self.config.satisfaction_decay_waiting,
                "satisfaction_decay_traveling": self.config.satisfaction_decay_traveling,
                "rush_hour_traffic_factor": self.config.rush_hour_traffic_factor,
                "busy_route_factor": self.config.busy_route_factor
            },
            "summary": self.summary,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
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
        plt.plot(self.metrics.time_data, self.metrics.cost_efficiency_data, 'g-')
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