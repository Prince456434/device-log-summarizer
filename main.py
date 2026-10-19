"""
main.py — Device Log Summarizer CLI entry point.

Reads device telemetry from a CSV file, sanitizes and aggregates records,
filters by temperature threshold, exports a JSON summary, and generates a
bar chart PNG via chart_generator.

Usage
-----
    python main.py [--input FILE] [--output FILE] [--chart FILE]

Defaults
--------
    --input   device_telemetry.csv
    --output  output/device_summary.json
    --chart   output/average_temperature.png
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import mean
from typing import Any

from chart_generator import generate_temperature_chart

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {"device_id", "status", "temperature"}
TEMPERATURE_THRESHOLD = 80.0
VALID_STATUSES = {"ACTIVE", "WARNING", "ERROR"}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class DeviceRecord:
    """Holds one validated telemetry record."""

    __slots__ = ("device_id", "status", "temperature")

    def __init__(self, device_id: str, status: str, temperature: float) -> None:
        self.device_id = device_id
        self.status = status
        self.temperature = temperature


class DeviceSummary:
    """Aggregated statistics for a single device."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.temperatures: list[float] = []
        self.error_count: int = 0

    @property
    def total_records(self) -> int:
        return len(self.temperatures)

    @property
    def average_temperature(self) -> float:
        return mean(self.temperatures) if self.temperatures else 0.0

    def add_record(self, record: DeviceRecord) -> None:
        self.temperatures.append(record.temperature)
        if record.status == "ERROR":
            self.error_count += 1


# ---------------------------------------------------------------------------
# CSV ingestion
# ---------------------------------------------------------------------------

def _normalize_headers(raw_headers: list[str]) -> list[str]:
    """Strip and lowercase all header names."""
    return [h.strip().lower() for h in raw_headers]


def load_records(csv_path: Path) -> tuple[list[DeviceRecord], int]:
    """Parse and validate a telemetry CSV file.

    Args:
        csv_path: Path to the input CSV file.

    Returns:
        A tuple of (valid_records, skipped_count).

    Raises:
        SystemExit: If the file is missing or required columns are absent.
    """
    if not csv_path.exists():
        print(f"ERROR: Input file not found: {csv_path}", file=sys.stderr)
        raise SystemExit(1)

    records: list[DeviceRecord] = []
    skipped = 0

    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)

            # Validate headers.
            if reader.fieldnames is None:
                print("ERROR: CSV file is empty or has no headers.", file=sys.stderr)
                raise SystemExit(1)

            normalized_headers = _normalize_headers(list(reader.fieldnames))
            missing = REQUIRED_COLUMNS - set(normalized_headers)
            if missing:
                print(
                    f"ERROR: CSV is missing required columns: {', '.join(sorted(missing))}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            # Build a mapping from normalized header → original key for DictReader rows.
            header_map: dict[str, str] = {
                norm: orig
                for norm, orig in zip(normalized_headers, reader.fieldnames)
            }

            for line_num, row in enumerate(reader, start=2):  # line 1 = header
                device_id, status, temperature = _parse_row(
                    row, header_map, line_num
                )
                if device_id is None:
                    skipped += 1
                    continue
                records.append(DeviceRecord(device_id, status, temperature))  # type: ignore[arg-type]

    except OSError as exc:
        print(f"ERROR: Cannot read CSV file: {exc}", file=sys.stderr)
        raise SystemExit(1)

    return records, skipped


def _parse_row(
    row: dict[str, Any],
    header_map: dict[str, str],
    line_num: int,
) -> tuple[str | None, str | None, float | None]:
    """Validate and normalize a single CSV row.

    Returns a (device_id, status, temperature) triple, or (None, None, None)
    if the row is invalid.  Invalid rows are logged to stderr.
    """
    # --- device_id ---
    raw_device_id = row.get(header_map.get("device_id", "device_id"), "")
    device_id = str(raw_device_id).strip() if raw_device_id is not None else ""
    if not device_id:
        print(f"  [skip line {line_num}] Blank device_id.", file=sys.stderr)
        return None, None, None

    # --- status ---
    raw_status = row.get(header_map.get("status", "status"), "")
    status = str(raw_status).strip().upper() if raw_status is not None else ""
    if not status:
        status = "UNKNOWN"

    # --- temperature ---
    raw_temp = row.get(header_map.get("temperature", "temperature"), "")
    temp_str = str(raw_temp).strip() if raw_temp is not None else ""
    if not temp_str:
        print(
            f"  [skip line {line_num}] Device '{device_id}': blank temperature.",
            file=sys.stderr,
        )
        return None, None, None

    try:
        temperature = float(temp_str)
    except ValueError:
        print(
            f"  [skip line {line_num}] Device '{device_id}': "
            f"non-numeric temperature '{temp_str}'.",
            file=sys.stderr,
        )
        return None, None, None

    if not math.isfinite(temperature):
        print(
            f"  [skip line {line_num}] Device '{device_id}': "
            f"non-finite temperature '{temperature}'.",
            file=sys.stderr,
        )
        return None, None, None

    if temperature < 0:
        print(
            f"  [skip line {line_num}] Device '{device_id}': "
            f"negative temperature '{temperature}' (error flag).",
            file=sys.stderr,
        )
        return None, None, None

    return device_id, status, temperature


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(records: list[DeviceRecord]) -> dict[str, DeviceSummary]:
    """Group records by device_id and compute per-device statistics.

    Args:
        records: List of validated DeviceRecord objects.

    Returns:
        Dict mapping device_id → DeviceSummary.
    """
    summaries: dict[str, DeviceSummary] = {}
    for rec in records:
        if rec.device_id not in summaries:
            summaries[rec.device_id] = DeviceSummary(rec.device_id)
        summaries[rec.device_id].add_record(rec)
    return summaries


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_summaries(
    summaries: dict[str, DeviceSummary],
    threshold: float = TEMPERATURE_THRESHOLD,
) -> list[DeviceSummary]:
    """Exclude devices whose unrounded average temperature exceeds the threshold.

    A device with average_temperature == threshold is retained.

    Args:
        summaries:  Dict of DeviceSummary objects keyed by device_id.
        threshold:  Upper limit (inclusive) for average temperature.

    Returns:
        Sorted list of DeviceSummary objects that pass the filter.
    """
    return sorted(
        [s for s in summaries.values() if s.average_temperature <= threshold],
        key=lambda s: s.device_id,
    )


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(
    filtered: list[DeviceSummary],
    total_valid: int,
    skipped: int,
    total_devices: int,
    output_path: Path,
) -> None:
    """Write the device summary JSON to disk.

    Args:
        filtered:      Devices that passed the temperature filter.
        total_valid:   Total number of valid records processed.
        skipped:       Number of records skipped due to validation errors.
        total_devices: Total distinct devices found before filtering.
        output_path:   Destination path for the JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "metadata": {
            "total_valid_records": total_valid,
            "skipped_records": skipped,
            "devices_processed": total_devices,
            "devices_exported": len(filtered),
            "temperature_threshold": TEMPERATURE_THRESHOLD,
        },
        "devices": [
            {
                "device_id": s.device_id,
                "total_records": s.total_records,
                "average_temperature": round(s.average_temperature, 2),
                "error_count": s.error_count,
            }
            for s in filtered
        ],
    }

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print(f"JSON summary written to: {output_path}")


# ---------------------------------------------------------------------------
# Terminal table
# ---------------------------------------------------------------------------

def print_table(filtered: list[DeviceSummary]) -> None:
    """Print a formatted table of device statistics to stdout."""
    if not filtered:
        print("\nNo devices passed the temperature filter (all averages > 80.0 °C).")
        return

    col_widths = {
        "device_id": max(len("Device ID"), max(len(s.device_id) for s in filtered)),
        "records": len("Records"),
        "avg_temp": len("Avg Temp (degC)"),
        "errors": len("Errors"),
    }

    header = (
        f"{'Device ID':<{col_widths['device_id']}}  "
        f"{'Records':>{col_widths['records']}}  "
        f"{'Avg Temp (degC)':>{col_widths['avg_temp']}}  "
        f"{'Errors':>{col_widths['errors']}}"
    )
    separator = "-" * len(header)

    print(f"\n{separator}")
    print(header)
    print(separator)

    for s in filtered:
        print(
            f"{s.device_id:<{col_widths['device_id']}}  "
            f"{s.total_records:>{col_widths['records']}}  "
            f"{s.average_temperature:>{col_widths['avg_temp']}.2f}  "
            f"{s.error_count:>{col_widths['errors']}}"
        )

    print(separator)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Device Log Summarizer — reads device telemetry CSV, computes "
            "per-device statistics, filters by temperature, exports JSON, "
            "and generates a bar chart."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        metavar="FILE",
        default="device_telemetry.csv",
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default="output/device_summary.json",
        help="Path to write the JSON summary.",
    )
    parser.add_argument(
        "--chart",
        metavar="FILE",
        default="output/average_temperature.png",
        help="Path to write the bar chart PNG.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code: 0 on success, 1 on fatal error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    csv_path = Path(args.input)
    output_path = Path(args.output)
    chart_path = Path(args.chart)

    # --- Ingest ---
    print(f"Reading telemetry from: {csv_path}")
    records, skipped = load_records(csv_path)
    total_valid = len(records)

    print(f"  Valid records : {total_valid}")
    print(f"  Skipped rows  : {skipped}")

    if total_valid == 0:
        print("\nWARNING: No valid records found. Nothing to aggregate.", file=sys.stderr)
        # Write an empty but valid JSON and exit cleanly.
        export_json([], 0, skipped, 0, output_path)
        return 0

    # --- Aggregate ---
    summaries = aggregate(records)
    total_devices = len(summaries)
    print(f"  Distinct devices: {total_devices}")

    # --- Filter ---
    filtered = filter_summaries(summaries)
    print(
        f"  Devices passing filter (avg <= {TEMPERATURE_THRESHOLD} degC): {len(filtered)}"
    )

    # --- Terminal table ---
    print_table(filtered)

    # --- Summary line ---
    print(
        f"\nSummary: {total_valid} valid records | {skipped} skipped | "
        f"{total_devices} devices processed | {len(filtered)} exported"
    )

    # --- JSON export ---
    export_json(filtered, total_valid, skipped, total_devices, output_path)

    # --- Chart generation ---
    try:
        generate_temperature_chart(str(output_path), str(chart_path))
    except SystemExit:
        print(
            "WARNING: Chart generation failed. JSON was still written successfully.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
