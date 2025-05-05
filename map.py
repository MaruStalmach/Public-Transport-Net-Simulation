import json
import folium
from folium.plugins import TimestampedGeoJson
from main import setup_transport_network

LINE_COLORS = {"Line1": "#e74c3c", "Line2": "#3498db"}


def get_line_name(bus_id):
    return bus_id.split('_')[0]


def format_time(iso_time):
    return f"{iso_time.split('T')[1].split(':')[0]}:{iso_time.split('T')[1].split(':')[1]}"


def create_bus_popup(bus_id, bus_data, line_color, time_str):
    line_name = get_line_name(bus_id)
    time_display = format_time(time_str)

    # Basic information
    is_transit = bus_data.get("in_transit", False)
    status = "W drodze" if is_transit else "Na przystanku"

    # Passenger information
    passenger_count = bus_data.get("passenger_count", 0)
    max_capacity = bus_data.get("max_capacity", 30)
    fill_percent = min(100, int(passenger_count / max_capacity * 100))

    # Destination table
    dest_table = "<p style='color:#999; font-style:italic;'>Brak pasażerów</p>"
    if passenger_count > 0 and bus_data.get("destinations"):
        table_rows = ""
        for dest, count in bus_data.get("destinations", {}).items():
            percent = int((count / passenger_count) * 100)
            table_rows += f"<tr><td>{dest}</td><td>{count}</td><td>{percent}%</td></tr>"

        dest_table = f"""
        <table style="width:100%; font-size:12px; border-collapse:collapse;">
            <tr style="background-color:#f5f5f5;"><th>Cel</th><th>Liczba</th><th>%</th></tr>
            {table_rows}
        </table>
        """

    # Create the HTML content
    return f"""
    <div style="font-family: Arial; width: 220px;">
        <h3 style="color: {line_color};">{line_name} - {bus_id.split('_')[1]}</h3>
        <p><b>Czas:</b> {time_display}</p>
        <div style="background-color:#f9f9f9; padding:8px; border-radius:4px;">
            <p><b>Przystanek:</b> {bus_data.get("stop", "")}</p>
            <p><b>Status:</b> {status}</p>
            <p><b>Następny:</b> {bus_data.get("next_stop", "")}</p>
        </div>
        <div style="margin-top:8px;">
            <h4>Pasażerowie: {passenger_count}/{max_capacity}</h4>
            <div style="width:100%; height:8px; background-color:#eee; border-radius:4px;">
                <div style="width:{fill_percent}%; height:8px; background-color:{line_color}; border-radius:4px;"></div>
            </div>
            <div style="margin-top:8px;">{dest_table}</div>
        </div>
    </div>
    """


def create_stop_popup(stop_name, timestamp, stop_data):
    hh, mm = divmod(timestamp, 60)
    dest_str = "<br>".join([f"{dest}: {count}" for dest, count in stop_data["destinations"].items()])

    return f"""
    <div style="font-family: Arial; width: 200px">
        <h3 style="color: #2980b9;">Przystanek {stop_name}</h3>
        <p><b>Czas:</b> {hh:02d}:{mm:02d}</p>
        <p><b>Pasażerowie:</b> {stop_data['count']}</p>
        <p><b>Cel podróży:</b><br>{dest_str}</p>
    </div>
    """


def process_simulation_data(transport_net):
    features = []

    # Process bus data
    for bus_id, trajectory in transport_net.bus_tracks.items():
        # Get the line color
        line_name = get_line_name(bus_id)
        line_color = LINE_COLORS.get(line_name)

        # Filter and transform trajectory data
        filtered_traj = []
        last_time = -1

        for point in sorted(trajectory, key=lambda x: x["time"]):
            if point["time"] > last_time and point["lat"] and point["lon"]:
                filtered_traj.append(point)
                last_time = point["time"]


        # Extract times and coordinates
        times = []
        coords = []

        for point in filtered_traj:
            hh, mm = divmod(point["time"], 60)
            iso = f"2023-01-01T{hh:02d}:{mm:02d}:00.000Z"
            times.append(iso)
            coords.append([point["lon"], point["lat"]])

        # Add bus route line
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "times": times,
                "style": {"color": line_color, "weight": 3, "opacity": 0.3}
            }
        })

        # Add bus markers
        for i, coord in enumerate(coords):
            bus_data = filtered_traj[i]

            # Create popup content
            popup = create_bus_popup(bus_id, bus_data, line_color, times[i])

            # Set marker appearance
            passenger_count = bus_data.get("passenger_count", 0)
            radius = 7 + min(8, passenger_count // 3)

            # Add bus marker
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coord},
                "properties": {
                    "times": [times[i]],
                    "popup": popup,
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": line_color,
                        "fillOpacity": 0.9,
                        "stroke": True,
                        "radius": radius,
                        "strokeColor": "#000000",
                        "strokeWeight": 2
                    }
                }
            })

            # Add passenger count label
            if passenger_count > 0:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": coord},
                    "properties": {
                        "times": [times[i]],
                        "icon": "circle",
                        "iconContent": str(passenger_count),
                        "iconstyle": {
                            "fillOpacity": 0,
                            "stroke": False,
                            "radius": 1,
                            "iconFontFamily": "Arial",
                            "iconFontSize": "11px",
                            "iconFontWeight": "bold",
                            "iconColor": "#ffffff"
                        }
                    }
                })

    # Process bus stop data
    for stop_name, (lat, lon) in transport_net.stop_locations.items():
        for timestamp, stops_data in transport_net.stop_snapshots.items():
            if stop_name not in stops_data:
                continue

            hh, mm = divmod(timestamp, 60)
            iso = f"2023-01-01T{hh:02d}:{mm:02d}:00.000Z"
            stop_data = stops_data[stop_name]

            # Create popup content
            popup = create_stop_popup(stop_name, timestamp, stop_data)

            # Add stop marker
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "times": [iso],
                    "popup": popup,
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": "#4a69bd",
                        "fillOpacity": 0.6,
                        "stroke": "true",
                        "radius": 5
                    }
                }
            })

    return features


def create_base_map(transport_net):
    # Calculate map center
    lats = [loc[0] for loc in transport_net.stop_locations.values()]
    lons = [loc[1] for loc in transport_net.stop_locations.values()]
    center = (sum(lats) / len(lats), sum(lons) / len(lons))

    # Create map
    m = folium.Map(location=list(center), zoom_start=14)

    # Add stops as circle markers
    for stop_name, (lat, lon) in transport_net.stop_locations.items():
        folium.CircleMarker(
            [lat, lon],
            radius=4,
            color='#0077b6',
            fill=True,
            fill_opacity=0.7,
            popup=f"<b>{stop_name}</b>",
            tooltip=stop_name
        ).add_to(m)

    # Add simple route lines
    for line in transport_net.bus_lines:
        line_color = LINE_COLORS.get(line.name, "#3498db")

        # Get route points
        route_points = []
        for stop in line.stops:
            if stop in transport_net.stop_locations:
                lat, lon = transport_net.stop_locations[stop]
                route_points.append([lat, lon])

        # Add route line
        if len(route_points) > 1:
            folium.PolyLine(
                locations=route_points,
                color=line_color,
                weight=2,
                opacity=0.5,
                dash_array='5, 5'
            ).add_to(m)

    return m


def create_animation(transport_net, output_file="bus_animation.html"):
    # Process data
    features = process_simulation_data(transport_net)

    # Create base map
    m = create_base_map(transport_net)

    # Add time animation
    TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period="PT1M",
        duration="PT5S",
        transition_time=100,
        add_last_point=True,
        auto_play=True,
        loop=True,
        max_speed=1.5,
        date_options="HH:mm"
    ).add_to(m)

    # Save the map
    m.save(output_file)
    print(f"Saved {output_file}")


def setup_simulation():
    tn = setup_transport_network()

    tn.stop_locations = {
        "A": (52.2297, 21.0122),
        "B": (52.2300, 21.0150),
        "C": (52.2310, 21.0180),
        "D": (52.2320, 21.0200),
        "E": (52.2330, 21.0220),
        "F": (52.2340, 21.0250),
    }

    return tn


if __name__ == "__main__":
    tn = setup_simulation()
    tn.run_simulation()

    with open("bus_tracks.json", "w") as f:
        json.dump(tn.bus_tracks, f)
    print("Saved bus_tracks.json")

    create_animation(tn, "bus_animation.html")