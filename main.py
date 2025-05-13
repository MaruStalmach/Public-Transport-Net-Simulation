import config
from class_definition import TransportNet
from visualization import run_with_pygame

def setup_transport_network():
    tn = TransportNet()

    for A, B, tt, busy in config.CONNECTIONS:
        tn.add_connection(A, B, tt, busy)

    for line_data in config.BUS_LINES:
        tn.add_bus_line(*line_data)

    return tn

if __name__ == "__main__":
    tn = setup_transport_network()
    print("=== TRANSPORT NETWORK SETUP ===")
    print(f"Stops: {sorted(tn.graph.nodes())}")
    print(f"Routes:")
    for line in tn.bus_lines:
        print(f"  {line.name}: {' → '.join(line.stops)}")
    print("=============================\n")

    tn.stop_locations = config.STOP_COORDS

    tn.schedule_vehicles()
    tn.env.process(tn.passenger_generator())
    tn.env.process(tn.report_status())
    run_with_pygame(tn, until=60*24)
