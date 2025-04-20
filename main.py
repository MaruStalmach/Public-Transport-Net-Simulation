from class_definition import TransportNet, Vehicle


tn = TransportNet()

tn.add_connection("A", "B", 5)
tn.add_connection("B", "C", 7)
tn.add_connection("C", "D", 4, busy=True)
tn.add_connection("D", "E", 6)
tn.add_connection("E", "F", 5)

vehicle1 = Vehicle("Bus1", ["A", "B", "C", "D", "E", "F"], tn)
tn.add_vehicle(vehicle1)

tn.run_simulation()
