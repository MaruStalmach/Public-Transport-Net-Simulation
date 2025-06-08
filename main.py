from class_definition import TransportNet
from visualization import run_simulation_with_plots
from config import SimulationConfig
from reporting import SimulationReport

stop_locations = {
    "A": (100, 200),
    "B": (300, 100),
    "C": (500, 200),
    "D": (400, 300),
    "E": (200, 300),
    "F": (200, 450)
}

connections = [
    ("A", "B", 5, False),
    ("B", "C", 7, False),
    ("C", "D", 4, True),
    ("D", "E", 6, False),
    ("E", "F", 5, False)
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
        metrics_tracker = run_simulation_with_plots(tn=tn, config=config)
    else:
        metrics_tracker = None
    
    # generate report
    if metrics_tracker:
        report = SimulationReport(config, metrics_tracker, tn)
        summary = report.finalize()
        
        print("\n=== SIMULATION REPORT ===")
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
        print("========================")