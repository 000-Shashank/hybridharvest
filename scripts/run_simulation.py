#!/usr/bin/env python3
"""Run a HybridHarvest simulation from the command line."""
import argparse
import os
import sys

# Add the src directory to the path so we can import hybridharvest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hybridharvest.reporting import plot_all_source_details, plot_results
from hybridharvest.simulation import run_simulation, save_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a HybridHarvest simulation and report each source "
                    "as its own category."
    )
    parser.add_argument(
        "--hours", type=float, default=24.0, help="Simulation duration in hours"
    )
    parser.add_argument(
        "--dt", type=float, default=1.0, help="Timestep in seconds"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed"
    )
    parser.add_argument(
        "--out", type=str, default="output", help="Output directory"
    )
    parser.add_argument(
        "--solar", action="store_true",
        help="Include the optional solar PV source",
    )
    parser.add_argument(
        "--piezo-config", type=str, default="parallel",
        choices=["single", "series", "parallel"],
        help="Piezoelectric array wiring (default: parallel)",
    )
    parser.add_argument(
        "--piezo-elements", type=int, default=4,
        help="Number of piezo elements (default: 4)",
    )
    parser.add_argument(
        "--ai", action="store_true",
        help="Enable AI summarization (requires API key)",
    )
    args = parser.parse_args()

    result = run_simulation(
        duration_hours=args.hours,
        dt=args.dt,
        seed=args.seed,
        enable_solar=args.solar,
        piezo_config=args.piezo_config,
        piezo_elements=args.piezo_elements,
    )

    csv_path = os.path.join(args.out, "csv", "simulation.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    save_csv(result, csv_path)

    plot_dir = os.path.join(args.out, "plots")
    plot_results(result, plot_dir)
    plot_all_source_details(result, plot_dir)

    source_wh = result.source_energy_wh(args.dt)
    print(f"[ok] steps: {len(result.time)}")
    print("[ok] per-source contribution:")
    print(f"       {'source':<14}{'peak (W)':>12}{'mean (W)':>12}"
          f"{'energy (Wh)':>14}{'share':>9}")
    for sid, series in result.sources.items():
        print(
            f"       {sid:<14}{series.peak_power():>12.4f}"
            f"{series.mean_power():>12.4f}"
            f"{series.total_energy_wh(args.dt):>14.4f}"
            f"{series.share_pct(source_wh, args.dt):>8.2f}%"
        )
    print(f"[ok] total harvested (after conversion): "
          f"{result.total_energy_wh(args.dt):.4f} Wh")
    print(f"[ok] csv: {csv_path}")
    print(f"[ok] plots: {plot_dir}")

    if args.ai:
        # Placeholder for AI summarization
        print("[ok] AI summarization: enabled (requires AI_API_KEY)")

    return 0


if __name__ == "__main__":
    sys.exit(main())