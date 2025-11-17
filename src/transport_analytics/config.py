# config.py
import json, os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Union

class SimulationConfig:
    def __init__(self, 
                stop_locations: Dict,
                connections: List,
                bus_lines: List,
                ):
        self.stop_locations = stop_locations
        self.connections = connections
        self.bus_lines = bus_lines

        # passenger config params
        self.passenger_generation_interval = 5
        self.peak_hours = (7*60, 9*60, 16*60, 18*60)  # morning and evening peak
        self.peak_multiplier = 2  
        # self.night_interval_range = (10, 30)  # night time passenger interval range
        self.satisfaction_decay_waiting = 0.5  # satisfaction loss per minute waiting
        self.satisfaction_decay_traveling = 0.2  # satisfaction loss per minute traveling

        # simulation config params
        self.simulation_duration = 60*24  
        self.rush_hour_traffic_factor = 1.5 
        self.busy_route_factor = 1.3  # travel time multiplier for busy streets
      
        self.visualize = True
        self.plot_metrics = True
        self.animation_speed = 30  
        
        self.report_directory = "reports"
        self.save_reports = True

    # def set_passenger_generation_interval(self, interval: int):
    #     self.passenger_generation_interval = interval
    
    # def set_peak_hours(self, hours: List[int]):
    #     self.peak_hours = hours
    
    # def set_peak_multiplier(self, multiplier: List[int]):
    #     self.peak_multiplier = multiplier
        
    
    def save(self, filename=None):
        """save configuration to file"""
        if not self.save_reports:
            return
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"config_{timestamp}.json"
            
        os.makedirs(self.report_directory, exist_ok=True)
        filepath = os.path.join(self.report_directory, filename)
        
        with open(filepath, 'w') as f:
            config_dict = self.__dict__.copy()
            if isinstance(self.stop_locations, pd.DataFrame):
                config_dict['stop_locations'] = self.stop_locations.to_dict()
            json.dump(config_dict, f, indent=4)
            
        return filepath
    
    # def load(self, filepath):
    #     """load configuration from file"""
    #     with open(filepath, 'r') as f:
    #         data = json.load(f)
    #         for key, value in data.items():
    #             setattr(self, key, value)
    #     return self
    