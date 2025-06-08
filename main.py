from class_definition import TransportNet
from visualization import run_with_pygame

def setup_transport_network():
    tn = TransportNet()

    tn.stop_locations = {
        "A": (100, 200),
        "B": (300, 100),
        "C": (500, 200),
        "D": (400, 300),
        "E": (200, 300),
        "F": (200, 450)
    }


    tn.add_connection("A", "B", 5)
    tn.add_connection("B", "C", 7)
    tn.add_connection("C", "D", 4, busy=True)
    tn.add_connection("D", "E", 6)
    tn.add_connection("E", "F", 5)

    tn.add_bus_line("Line1", ["A","B","C","D","E","F"], ["00:05"], wait_time=5)
    tn.add_bus_line("Line2", ["F","E","D","C"], ["00:10"], wait_time=3)

    return tn

if __name__ == "__main__":
    tn = setup_transport_network()
    print("=== TRANSPORT NETWORK SETUP ===")
    print(f"Stops: {sorted(tn.graph.nodes())}")
    print(f"Routes:")
    for line in tn.bus_lines:
        print(f"  {line.name}: {' → '.join(line.stops)}")
    print("=============================\n")

    # tn.run_simulation()
    run_with_pygame(tn=tn, until=60*24)