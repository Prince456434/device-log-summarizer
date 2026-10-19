"""
chart_generator.py — Matplotlib bar chart generation for device telemetry.

Implements generate_temperature_chart() which reads the exported JSON summary
and produces a PNG bar chart of average temperatures per device.

Uses the non-interactive 'Agg' backend so the module works in headless
environments (CI, servers, containers, etc.).
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Must be set before importing pyplot.
import matplotlib.pyplot as plt


def generate_temperature_chart(json_path: str, image_path: str) -> None:
    """Generate a bar chart of average temperatures from a device summary JSON.

    Reads ``json_path``, extracts device IDs and average temperatures from the
    ``devices`` array, and saves a bar chart to ``image_path``.

    Args:
        json_path:  Path to the ``device_summary.json`` file.
        image_path: Destination path for the PNG output.

    Raises:
        SystemExit: On fatal I/O or JSON errors, the function prints a clear
            error message and re-raises as SystemExit with code 1.
    """
    # --- Load and validate JSON -------------------------------------------
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"[chart] ERROR: JSON file not found: {json_path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        with json_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"[chart] ERROR: Malformed JSON in {json_path}: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(data, dict) or "devices" not in data:
        print(
            f"[chart] ERROR: JSON missing expected 'devices' key: {json_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    devices = data["devices"]
    if not isinstance(devices, list):
        print("[chart] ERROR: 'devices' is not a list.", file=sys.stderr)
        raise SystemExit(1)

    # --- Handle empty device list -----------------------------------------
    if not devices:
        print(
            "[chart] WARNING: No devices to chart (all devices were filtered out).",
            file=sys.stderr,
        )
        return

    # --- Extract data -------------------------------------------------------
    device_ids: list[str] = []
    avg_temps: list[float] = []

    for entry in devices:
        if not isinstance(entry, dict):
            continue
        dev_id = entry.get("device_id")
        avg_temp = entry.get("average_temperature")
        if dev_id is None or avg_temp is None:
            print(
                f"[chart] WARNING: Skipping device entry with missing fields: {entry}",
                file=sys.stderr,
            )
            continue
        try:
            avg_temps.append(float(avg_temp))
            device_ids.append(str(dev_id))
        except (ValueError, TypeError):
            print(
                f"[chart] WARNING: Non-numeric average_temperature for {dev_id}; skipping.",
                file=sys.stderr,
            )

    if not device_ids:
        print(
            "[chart] WARNING: No valid device entries found; chart not generated.",
            file=sys.stderr,
        )
        return

    # --- Build chart --------------------------------------------------------
    fig, ax = plt.subplots(figsize=(max(6, len(device_ids) * 1.4), 6))

    bar_color = "#4C72B0"
    bars = ax.bar(device_ids, avg_temps, color=bar_color, width=0.55, zorder=3)

    # Value annotations above each bar.
    for bar, temp in zip(bars, avg_temps):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.8,
            f"{temp:.2f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
        )

    # Labels, title, grid.
    ax.set_xlabel("Device ID", fontsize=12, labelpad=8)
    ax.set_ylabel("Average Temperature (degC)", fontsize=12, labelpad=8)
    ax.set_title("Average Temperature by Device (filtered <= 80 degC)", fontsize=13, pad=14)
    ax.yaxis.grid(True, linestyle="--", alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    # Rotate x-axis labels if there are many devices to prevent overlap.
    if len(device_ids) > 4:
        plt.xticks(rotation=30, ha="right", fontsize=10)
    else:
        plt.xticks(fontsize=10)

    # Add a small top margin so value annotations are not clipped.
    y_max = max(avg_temps)
    ax.set_ylim(0, y_max * 1.18 if y_max > 0 else 10)

    plt.tight_layout()

    # --- Save chart ---------------------------------------------------------
    out_path = Path(image_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[chart] Chart saved to: {out_path}")
