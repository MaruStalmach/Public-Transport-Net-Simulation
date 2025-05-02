from class_definition import TransportNet, Vehicle

def setup_transport_network():
    tn = TransportNet()

    tn.add_connection("A", "B", 5)
    tn.add_connection("B", "C", 7)
    tn.add_connection("C", "D", 4, busy=True)
    tn.add_connection("D", "E", 6)
    tn.add_connection("E", "F", 5)

    tn.add_bus_line("Line1", ["A", "B", "C", "D", "E", "F"], ["00:05", "00:15", "00:30"], wait_time=10)
    tn.add_bus_line("Line2", ["F", "E", "D", "C"], ["00:10", "00:20", "00:40"], wait_time=5)

    return tn

if __name__ == "__main__":
    tn = setup_transport_network()
    print("=== TRANSPORT NETWORK SETUP ===")
    print(f"Stops: {sorted(tn.graph.nodes())}")
    print(f"Routes:")
    for line in tn.bus_lines:
        print(f"  {line.name}: {' → '.join(line.stops)}")
    print("=============================\n")

    tn.run_simulation()
