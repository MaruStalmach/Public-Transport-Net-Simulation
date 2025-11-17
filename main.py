from src.transport_analytics.models import TransportNet
from src.transport_analytics.visualization import run_simulation_with_plots
from src.transport_analytics.config import SimulationConfig
from src.transport_analytics.reporting import SimulationReport
import pandas as pd

stop_locations = pd.read_json(r"example_data/stop_locations.json")

connections = [
    ("A", "B", 5, False),
    ("B", "C", 7, False),
    ("C", "D", 4, True),
    ("D", "E", 6, False),
    ("E", "F", 5, False),
    
    ("A", "I", 4, True),
    ("F", "J", 3, False),
    ("F", "O", 2, True),
    ("O", "E", 3, False),
    ("D", "G", 5, True),
    ("G", "H", 6, False),
    ("C", "M", 4, False),
    ("M", "H", 5, True),
    ("D", "K", 4, False),
    ("K", "N", 3, False),
    ("J", "N", 2, True),
    ("N", "L", 4, False),
    ("L", "F", 3, False),
    ("O", "L", 3, True),
    ("B", "I", 5, False),
    ("K", "G", 6, True),
    ("H", "M", 4, False),
    ("I", "O", 4, False),
    ("J", "K", 5, True),
    
    # Direct route between B and M
    ("B", "M", 8, False),
    ("M", "B", 8, False)
]

bus_lines = [
    {
        "name": "Line1",
        "stops": ["A","B","C","D","E","F"],
        "schedule": ["00:05"],
        "wait_time": 5,
        "capacity": 30
    },
    {
        "name": "Line2",
        "stops": ["F","E","D","C"],
        "schedule": ["00:10"],
        "wait_time": 3,
        "capacity": 25
    },
    {
        "name": "Line3",
        "stops": ["I","A","B","M","H","G","D"],
        "schedule": ["00:15", "08:30", "16:45"],
        "wait_time": 4,
        "capacity": 35
    },
    {
        "name": "Line4",
        "stops": ["O","F","J","N","K","D","G"],
        "schedule": ["00:20", "09:15", "18:00"],
        "wait_time": 3,
        "capacity": 40
    },
    {
        "name": "Line5",
        "stops": ["L","O","E","D","C","M","H"],
        "schedule": ["00:25", "07:00", "14:30", "21:15"],
        "wait_time": 2,
        "capacity": 28
    },
    {
        "name": "Line6",
        "stops": ["N","J","F","L","O","I","B","C"],
        "schedule": ["00:35", "12:00"],
        "wait_time": 5,
        "capacity": 32
    },
    {
        "name": "Line7",
        "stops": ["H","G","K","N","L","F","E","D"],
        "schedule": ["00:40", "10:10", "15:20", "19:55"],
        "wait_time": 4,
        "capacity": 45
    }
]

if __name__ == "__main__":
    config = SimulationConfig(stop_locations=stop_locations, connections=connections, bus_lines=bus_lines)
    config.save()
    
    tn = TransportNet(config)
    tn.setup_transport_network()

    print("=== TRANSPORT NETWORK SETUP ===")
    print(f"Stops: {sorted(tn.graph.nodes())}")
    print(f"Routes:")
    for line in tn.bus_lines:
        print(f"  {line.name}: {' -> '.join(line.stops)}")
    print("=============================\n")

    # run
    if config.visualize:
        report = SimulationReport(config, None, tn)
        report.set_start_time()
        metrics_tracker = run_simulation_with_plots(tn=tn, config=config)
        report.metrics = metrics_tracker
    else:
        metrics_tracker = None
        report = None
    
    # generate report
    if metrics_tracker and report:
        summary = report.finalize()
        
        print("\n=== SIMULATION REPORT ===")
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
        print("========================")