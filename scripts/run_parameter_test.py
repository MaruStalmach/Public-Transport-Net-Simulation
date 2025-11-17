import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from src.transport_analytics.models import TransportNet
from src.transport_analytics.config import SimulationConfig
from src.transport_analytics.reporting import SimulationReport
from src.transport_analytics.visualization import RealTimeMetrics
from main import stop_locations, connections, bus_lines


def create_simulation_config(config_params):
    config = SimulationConfig(
        stop_locations=stop_locations,
        connections=connections,
        bus_lines=bus_lines
    )
    
    for param, value in config_params.items():
        setattr(config, param, value)
    
    config.visualize = False
    config.simulation_duration = 6 * 60
    
    return config


def run_simulation(config):
    transport_net = TransportNet(config)
    transport_net.setup_transport_network()
    
    metrics_tracker = RealTimeMetrics(transport_net)
    
    for line in transport_net.bus_lines:
        for departure in line.schedule:
            transport_net.env.process(
                transport_net.create_vehicle(line, departure)
            )
    
    interval = config.passenger_generation_interval
    transport_net.env.process(
        transport_net.passenger_generator(interval=interval)
    )
    
    minute = 0
    while minute < config.simulation_duration:
        transport_net.env.run(until=minute + 1)
        minute += 1
        if minute % 10 == 0:
            metrics_tracker.update_metrics()
    
    return transport_net, metrics_tracker


def generate_simulation_report(config, metrics_tracker, transport_net):
    report = SimulationReport(config, metrics_tracker, transport_net)
    report.set_start_time()
    return report.finalize()


def run_test_scenario(config_params, scenario_name):
    config = create_simulation_config(config_params)
    transport_net, metrics_tracker = run_simulation(config)
    summary = generate_simulation_report(config, metrics_tracker, transport_net)
    
    summary["scenario_name"] = scenario_name
    summary["config_params"] = config_params
    
    return summary


def prepare_results_dataframe(results):
    flat_results = []
    for res in results:
        row = res['config_params'].copy()
        row['avg_satisfaction'] = res.get('avg_satisfaction')
        row['avg_total_delay'] = res.get('avg_total_delay')
        row['avg_wait_time'] = res.get('avg_wait_time')
        row['avg_vehicle_utilization'] = res.get('avg_vehicle_utilization')
        flat_results.append(row)
    
    return pd.DataFrame(flat_results)


def create_correlation_heatmap(dataframe, param_grid, plot_dir):
    plt.figure(figsize=(12, 10))
    metrics = [
        'avg_satisfaction', 'avg_total_delay', 
        'avg_wait_time', 'avg_vehicle_utilization'
    ]
    numeric_df = dataframe[list(param_grid.keys()) + metrics]
    corr = numeric_df.corr()
    
    sns.heatmap(
        corr, annot=True, cmap='coolwarm', 
        fmt=".2f", linewidths=.5
    )
    plt.title(
        'Correlation Heatmap of Parameters and Metrics',
        fontsize=16
    )
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    heatmap_filename = os.path.join(plot_dir, 'correlation_heatmap.png')
    plt.savefig(heatmap_filename)
    plt.close()
    print(f"Saved correlation heatmap to: {heatmap_filename}")


def create_boxplots_for_metric(dataframe, metric, param_grid, 
                               param_headers_map, plot_dir):
    num_params = len(param_grid)
    ncols = 3
    nrows = (num_params + ncols - 1) // ncols
    
    fig, axes = plt.subplots(
        nrows=nrows, ncols=ncols, 
        figsize=(18, 5 * nrows), constrained_layout=True
    )
    fig.suptitle(
        f'Impact of Parameters on {metric.replace("_", " ").title()}',
        fontsize=20, y=1.03
    )
    
    axes = axes.flatten()
    
    for i, param in enumerate(param_grid.keys()):
        sns.boxplot(
            x=param, y=metric, data=dataframe, 
            ax=axes[i], palette="viridis", hue=param, legend=False
        )
        axes[i].set_title(
            f'{param_headers_map.get(param, param)}', fontsize=14
        )
        axes[i].set_xlabel('')
        axes[i].set_ylabel('')
        axes[i].tick_params(axis='x', rotation=15)
    
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    
    plot_filename = os.path.join(plot_dir, f'boxplot_impact_on_{metric}.png')
    plt.savefig(plot_filename)
    plt.close(fig)
    print(f"Saved boxplots for {metric} to: {plot_filename}")


def create_boxplots(dataframe, param_grid, param_headers_map, plot_dir):
    metrics_to_plot = [
        'avg_satisfaction', 'avg_total_delay', 
        'avg_wait_time', 'avg_vehicle_utilization'
    ]
    
    for metric in metrics_to_plot:
        create_boxplots_for_metric(
            dataframe, metric, param_grid, param_headers_map, plot_dir
        )


def analyze_and_plot_results(results, param_grid, param_headers_map, 
                           output_dir):
    dataframe = prepare_results_dataframe(results)
    
    plot_dir = os.path.join(output_dir, "plots_analysis")
    os.makedirs(plot_dir, exist_ok=True)
    
    print("\n" + "="*60)
    print("GENEROWANIE ZAAWANSOWANYCH WYKRESÓW ANALIZY")
    print("="*60)

    create_correlation_heatmap(dataframe, param_grid, plot_dir)
    create_boxplots(dataframe, param_grid, param_headers_map, plot_dir)


def generate_parameter_combinations(param_grid):
    keys = list(param_grid.keys())
    values_list = list(param_grid.values())
    scenarios_params_list = []
    
    def generate_combinations(index, current_combination):
        if index == len(keys):
            scenarios_params_list.append(dict(zip(keys, current_combination)))
            return
        
        for value in values_list[index]:
            generate_combinations(index + 1, current_combination + [value])
    
    generate_combinations(0, [])
    return scenarios_params_list


def execute_grid_search(scenarios_params_list):
    results = []
    for i, params in enumerate(scenarios_params_list):
        param_str_parts = []
        for k, v in params.items():
            param_str_parts.append(f"{k}={v}")
        scenario_name = f"Scenario_{i+1}: {'_'.join(param_str_parts)}"
        
        result = run_test_scenario(params, scenario_name)
        results.append(result)
    
    return results


def save_results_to_file(results):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = f"reports/parameter_comparison_{timestamp}.json"
    
    os.makedirs("reports", exist_ok=True)
    with open(comparison_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    return comparison_file


def get_parameter_headers_map():
    return {
        "passenger_generation_interval": "Passenger Interval",
        "peak_multiplier": "Peak Multiplier",
        "rush_hour_traffic_factor": "Rush Hour Factor",
        "satisfaction_decay_waiting": "Satisfaction Decay Waiting",
        "satisfaction_decay_traveling": "Satisfaction Decay Traveling",
        "busy_route_factor": "Busy Route Factor",
    }


def format_results_header(keys, param_headers_map):
    param_col_width = 14
    header_parts = [
        f"{param_headers_map.get(k, k):<{param_col_width}}" 
        for k in keys
    ]
    header_parts.extend([
        f"{'Satisfaction':<12}", f"{'Delay':<10}", 
        f"{'Wait Time':<10}", f"{'Utilization':<12}"
    ])
    return " ".join(header_parts)


def format_result_row(result, keys):
    param_col_width = 14
    params = result.get('config_params', {})
    row_parts = [
        f"{params.get(k, 'N/A'):<{param_col_width}}" 
        for k in keys
    ]
    
    satisfaction = result.get('avg_satisfaction', 0)
    delay = result.get('avg_total_delay', 0)
    wait_time = result.get('avg_wait_time', 0)
    utilization = result.get('avg_vehicle_utilization', 0)
    
    row_parts.extend([
        f"{satisfaction:<12.2f}",
        f"{delay:<10.2f}",
        f"{wait_time:<10.2f}",
        f"{utilization:<12.2f}"
    ])
    
    return " ".join(row_parts)


def display_results_summary(results, keys, param_headers_map):
    print("\n" + "="*60)
    print("PARAMETER TESTING RESULTS")
    print("="*60)
    
    if not results:
        print("No results to analyze.")
        return None
    
    results_sorted = sorted(
        results, key=lambda x: x.get('avg_satisfaction', 0), reverse=True
    )
    
    header = format_results_header(keys, param_headers_map)
    print(f"\n{header}")
    print("-" * len(header))
    
    print("\nTop 5 Best Scenarios:")
    for result in results_sorted[:5]:
        print(format_result_row(result, keys))
    
    print("\nTop 5 Worst Scenarios:")
    for result in results_sorted[-5:]:
        print(format_result_row(result, keys))
    
    return results_sorted[0]


def display_best_scenario(best_scenario):
    print("\n" + "="*60)
    print("BEST SCENARIO")
    print("="*60)
    print(f"Parameters: {best_scenario.get('config_params')}")
    print(f"Avg Satisfaction: {best_scenario.get('avg_satisfaction', 0):.2f}%")
    print(f"Avg Delay: {best_scenario.get('avg_total_delay', 0):.2f} min")
    print(f"Avg Wait Time: {best_scenario.get('avg_wait_time', 0):.2f} min")


def main():
    param_grid = {
        "passenger_generation_interval": [8, 12],
        "peak_multiplier": [1.5, 2.0],
        "rush_hour_traffic_factor": [1.5, 2.0],
        "satisfaction_decay_waiting": [0.25, 0.5],
        "satisfaction_decay_traveling": [0.1, 0.2],
        "busy_route_factor": [1.3, 1.6]
    }
    
    scenarios_params_list = generate_parameter_combinations(param_grid)
    total_scenarios = len(scenarios_params_list)
    print(f"Starting grid search with {total_scenarios} scenarios...")
    
    results = execute_grid_search(scenarios_params_list)
    comparison_file = save_results_to_file(results)
    
    param_headers_map = get_parameter_headers_map()
    keys = list(param_grid.keys())
    
    best_scenario = display_results_summary(results, keys, param_headers_map)
    
    if best_scenario:
        display_best_scenario(best_scenario)
    
    print(f"\nDetailed results saved to: {comparison_file}")
    
    analyze_and_plot_results(results, param_grid, param_headers_map, "reports")


if __name__ == "__main__":
    main()