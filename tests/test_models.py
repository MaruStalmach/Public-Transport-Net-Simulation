import pytest
import networkx as nx
from src.transport_analytics.models import Passenger, TransportNet, Vehicle

@pytest.fixture
def transport_net():
    transport_net = TransportNet(config=None)
    transport_net.graph = nx.DiGraph()
    transport_net.path_cache = {}

    transport_net.graph.add_edge("A", "B", travel_time=10)
    transport_net.graph.add_edge("B", "C", travel_time=15)
    transport_net.graph.add_edge("A", "C", travel_time=25)

    return transport_net

def test_passenger_initialization(transport_net):
    passenger = Passenger(
        id="P1",
        origin="A",
        destination="C",
        spawn_time=0,
        transport_net=transport_net
    )

    assert passenger.id == "P1"
    assert passenger.origin == "A"
    assert passenger.destination == "C"
    assert passenger.spawn_time == 0
    assert passenger.status == "waiting"
    assert passenger.satisfaction == 100

    assert passenger.route == ["A", "C"]

def test_passenger_route_caching(transport_net):
    Passenger(
        id="P1",
        origin="A",
        destination="C",
        spawn_time=0,
        transport_net=transport_net
    )

    assert ("A", "C") in transport_net.path_cache
    assert transport_net.path_cache[("A", "C")] == ["A", "C"]

    passenger = Passenger(
        id="P2",
        origin="A",
        destination="C",
        spawn_time=5,
        transport_net=transport_net
    )

    assert passenger.route == ["A", "C"]

def test_vehicle_initialization(transport_net):
    vehicle = Vehicle(
        id="V1",
        stops=["A", "B", "C"],
        transport_net=transport_net,
        vehicle_capacity=40,
        wait_time=10
    )

    assert vehicle.id == "V1"
    assert vehicle.route == ["A", "B", "C"]
    assert vehicle.current_stop == "A"
    assert vehicle.vehicle_capacity == 40
    assert vehicle.wait_time == 10
    assert vehicle.direction == 1
    assert vehicle.passengers == []
    assert vehicle.position_index == 0
    assert vehicle.progress == 0.0

def test_vehicle_has_delay(transport_net):
    transport_net.graph["A"]["B"]["travel_time"] = 10
    transport_net.graph["A"]["B"]["busy"] = False

    vehicle = Vehicle(
        id="V1",
        stops=["A", "B"],
        transport_net=transport_net
    )

    # Non-rush hour, not busy
    delay = vehicle.has_delay("A", "B", current_minute=300)
    assert delay == 10

    # Rush hour, not busy
    delay = vehicle.has_delay("A", "B", current_minute=450)
    assert delay == 15

    # Non-rush hour, busy
    transport_net.graph["A"]["B"]["busy"] = True
    delay = vehicle.has_delay("A", "B", current_minute=300)
    assert delay == 15

def test_vehicle_record_position(transport_net):
    transport_net.bus_tracks = {"V1": []}
    transport_net.stop_locations = {"A": (0, 0), "B": (10, 10)}

    vehicle = Vehicle(
        id="V1",
        stops=["A", "B"],
        transport_net=transport_net
    )

    vehicle.passengers = [
        Passenger(id="P1", origin="A", destination="B", spawn_time=0, transport_net=transport_net),
        Passenger(id="P2", origin="A", destination="B", spawn_time=0, transport_net=transport_net)
    ]

    vehicle.record_position(
        env=transport_net.env,
        stop_info="A -> B",
        lat=5,
        lon=5,
        next_stop="B",
        in_transit=True,
        progress=0.5
    )

    assert len(transport_net.bus_tracks["V1"]) == 1
    record = transport_net.bus_tracks["V1"][0]
    assert record["time"] == 0
    assert record["stop"] == "A -> B"
    assert record["lat"] == 5
    assert record["lon"] == 5
    assert record["direction"] == 1
    assert record["passenger_count"] == 2
    assert record["vehicle_capacity"] == 30
    assert record["next_stop"] == "B"
    assert record["in_transit"] is True
    assert record["progress"] == 0.5

def test_vehicle_get_coordinates(transport_net):
    transport_net.stop_locations = {"A": (0, 0), "B": (10, 10)}

    vehicle = Vehicle(
        id="V1",
        stops=["A", "B"],
        transport_net=transport_net
    )

    vehicle.position_index = 0
    vehicle.progress = 0.5
    x, y = vehicle.get_coordinates()

    assert x == 5
    assert y == 5

################################################################################
