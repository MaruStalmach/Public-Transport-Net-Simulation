# Public Transport Network Simulation

A system for simulating and analyzing public transportation networks with interactive visualizations and detailed performance metrics

**Course:** System Modeling, CS Data Science 2024/2025

## Overview

This project simulates a dynamic public transport network where buses operate on predefined routes, passengers request rides, and the system optimizes operations to maximize passenger satisfaction. The simulation accounts for real-world factors like peak hour traffic, route congestion, and passenger wait times. There's an option of importing your own configuration if you please.

## Project Structure

```
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project configuration
├── setup.sh / setup.bat             # Setup scripts
├── src/
│   └── transport_analytics/
│       ├── __init__.py
│       ├── config.py                # Simulation configuration
│       ├── models.py                # Core transport network models
│       ├── scenarios.py             # Scenario definitions and data loading
│       ├── visualization.py         # Visualization and animation
│       ├── reporting.py             # Report generation
│       └── utils/
│           └── time                 # Time utility functions
├── scripts/
│   └── run_parameter_test.py        # Parameter testing utilities
├── tests/
│   └── test_models.py               # Unit tests
└── data/
    └── example_data/
        └── stop_locations.json      # Sample stop locations
```

## Installation

### Quick Start

1. **Clone/navigate to the project directory:**

   ```bash
   cd Public-Transport-Net-Simulation
   ```

2. **Install dependencies:**
**Linux/macOS:**
```bash
bash setup.sh
```
**Windows:**
```bash
setup.bat
```

3. **Run the simulation:**
   ```bash
   python main.py
   ```

## Configuration

Edit the configuration in [main.py](main.py) to customize your simulation:

### Network Definition

- **stop_locations**: Dictionary mapping stop names to (x, y) coordinates
- **connections**: List of tuples defining routes: `(from_stop, to_stop, travel_time, is_express)`

### Bus Lines

Define bus lines with the following structure:

```python
{
    "name": "Line1",
    "stops": ["A", "B", "C"],         # Sequence of stops
    "schedule": ["00:05", "12:00"],   # Departure times
    "wait_time": 5,                   # Minutes between stops
    "capacity": 30                    # Passenger capacity
}
```

### Simulation Parameters

In [config.py](src/transport_analytics/config.py):

- `simulation_duration`: Total simulation time in minutes (default: 1440 = 24 hours)
- `passenger_generation_interval`: Time between new passengers in minutes
- `peak_multiplier`: Passenger demand multiplier during peak hours
- `satisfaction_decay_waiting`: Satisfaction loss per minute waiting
- `satisfaction_decay_traveling`: Satisfaction loss per minute traveling
- `rush_hour_traffic_factor`: Travel time multiplier during peak hours
- `visualize`: Enable/disable visualization
- `animation_speed`: Simulation speed multiplier

<!-- ## Usage

### Basic Simulation

```python
from transport_analytics.models import TransportNet
from transport_analytics.config import SimulationConfig
from transport_analytics.visualization import run_simulation_with_plots

# Create configuration
config = SimulationConfig(
    stop_locations=stop_locations,
    connections=connections,
    bus_lines=bus_lines
)

# Initialize and setup network
tn = TransportNet(config)
tn.setup_transport_network()

# Run simulation with visualization
metrics = run_simulation_with_plots(tn=tn, config=config)
```

### Generate Reports

```python
from transport_analytics.reporting import SimulationReport

report = SimulationReport(config, None, tn)
report.set_start_time()
summary = report.finalize()

# Print results
for key, value in summary.items():
    print(f"{key}: {value}")
``` -->

## Output

The simulation generates:

1. **Console Output**: Network structure, simulation statistics, and key metrics
2. **Visualizations**:
   - Interactive route map
   - Real-time bus position animation
   - Passenger flow visualization
3. **Reports**: Saved to `reports/` directory with detailed performance metrics

<!-- ## Testing

Run the test suite:

```bash
pytest tests/
``` -->
<!--
## Example Metrics

The simulation tracks:

- Total passengers served
- Average wait time (minutes)
- Average travel time (minutes)
- System utilization percentage
- Average passenger satisfaction score
- On-time performance percentage -->

## Authorship

MaruStalmach - [GitHub](https://github.com/MaruStalmach)
izabelaszpunar - [GitHub](https://github.com/izabelaszpunar)
