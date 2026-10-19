# Device Log Summarizer CLI

A command-line tool that reads device telemetry from a CSV file, sanitizes sensor readings,
computes per-device statistics, filters devices by temperature threshold, exports a JSON
summary, and generates a Matplotlib bar chart.

Built as a software-engineering intern technical assessment project.

---

## Features

| Requirement | Status |
|---|---|
| CSV ingestion with `csv` stdlib | ✅ |
| Sensor sanitization with full edge-case handling | ✅ |
| Per-device aggregation (records, avg temp, error count) | ✅ |
| Temperature threshold filtering (≤ 80.0 °C passes) | ✅ |
| JSON export with metadata | ✅ |
| Terminal-formatted table | ✅ |
| Matplotlib bar chart (PNG) | ✅ |
| Comprehensive `unittest` suite | ✅ |
| Full CLI with `--input`, `--output`, `--chart` | ✅ |
| Graceful error handling (missing file, bad rows, empty data) | ✅ |
| Type hints and docstrings throughout | ✅ |

---

## Requirements

- Python 3.10 or later
- Matplotlib ≥ 3.7.0

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Project Structure

```
device-log-summarizer/
├── main.py               # CLI entry point; ingestion, aggregation, filtering
├── sanitizer.py          # clean_sensor_readings() utility
├── chart_generator.py    # Matplotlib bar chart generator
├── device_telemetry.csv  # Sample telemetry data (20 rows, 5 devices)
├── output/
│   ├── device_summary.json      # Generated JSON summary
│   └── average_temperature.png  # Generated bar chart
├── tests/
│   └── test_sanitizer.py  # 25+ unittest cases for sanitizer.py
├── requirements.txt
├── README.md
└── PROMPT_LOG.md          # AI-collaboration log for chart_generator.py
```

---

## How to Run

Run from the **`device-log-summarizer/`** directory:

```bash
# Default run — reads device_telemetry.csv, writes to output/
python main.py

# Custom input and output paths
python main.py --input path/to/custom.csv \
               --output path/to/summary.json \
               --chart  path/to/chart.png

# Show all CLI options
python main.py --help
```

---

## Running Unit Tests

From the `device-log-summarizer/` directory:

```bash
python -m unittest discover -s tests -v
```

---

## JSON Output Format

```json
{
  "metadata": {
    "total_valid_records": 17,
    "skipped_records": 3,
    "devices_processed": 5,
    "devices_exported": 4,
    "temperature_threshold": 80.0
  },
  "devices": [
    {
      "device_id": "DEV_A",
      "total_records": 4,
      "average_temperature": 48.67,
      "error_count": 1
    }
  ]
}
```

### Field Descriptions

| Field | Description |
|---|---|
| `total_valid_records` | Rows that passed all validation checks |
| `skipped_records` | Rows discarded due to blank/invalid fields |
| `devices_processed` | Distinct device IDs found in valid records |
| `devices_exported` | Devices whose average temperature is ≤ 80.0 °C |
| `temperature_threshold` | Filter threshold (80.0 °C) |
| `device_id` | Device identifier |
| `total_records` | Valid records for this device |
| `average_temperature` | Arithmetic mean, rounded to 2 decimal places |
| `error_count` | Records with status `ERROR` for this device |

---

## Filtering Logic

After aggregation, any device whose **unrounded** average temperature is **strictly greater
than 80.0 °C** is excluded from the JSON and chart.  
A device with an average of exactly **80.0 °C is retained**.

---

## Chart Generation

`chart_generator.py` reads the exported JSON and creates a bar chart:

- Non-interactive `Agg` backend — works in headless environments.
- Title, x-axis ("Device ID"), y-axis ("Average Temperature (°C)").
- Numeric annotation above each bar (2 decimal places).
- Light horizontal grid for readability.
- Labels rotate 30 ° when more than 4 devices are present to prevent overlap.
- Figure is closed after saving to free memory.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Input file not found | Clear error message; exits with code 1 |
| Missing required CSV columns | Error message listing missing columns; exits 1 |
| Blank `device_id` | Row skipped; count incremented |
| Blank or non-numeric `temperature` | Row skipped; count incremented |
| Negative temperature | Row skipped (treated as error flag) |
| Non-finite temperature (NaN, ±inf) | Row skipped |
| No valid records | Warning printed; empty JSON written; exits 0 |
| No devices pass filter | Helpful message instead of empty table |
| Chart JSON missing/malformed | Error printed; exits 1 (JSON already written) |

---

## Expected Output — Sample CSV

With `device_telemetry.csv` (20 rows, 5 devices):

```
Reading telemetry from: device_telemetry.csv
  [skip line 17] Device 'DEV_E': non-numeric temperature 'invalid_temp'.
  [skip line 18] Device 'DEV_E': blank temperature.
  [skip line 19] Device 'DEV_E': negative temperature '-5.2' (error flag).
  Valid records : 17
  Skipped rows  : 3
  Distinct devices: 5
  Devices passing filter (avg ≤ 80.0 °C): 4

---------------------------------------------------------
Device ID    Records    Avg Temp (°C)    Errors
---------------------------------------------------------
DEV_A              4            48.67         1
DEV_C              4            31.07         0
DEV_D              4            74.15         2
DEV_E              1            62.10         1
---------------------------------------------------------

Summary: 17 valid records | 3 skipped | 5 devices processed | 4 exported
JSON summary written to: output/device_summary.json
[chart] Chart saved to: output/average_temperature.png
```

DEV_B is excluded because its average temperature (≈ 81.42 °C) exceeds 80.0 °C.
DEV_D is retained because its average (74.15 °C) is below 80.0 °C.

---

## Limitations

- No streaming support for very large CSV files (entire file is loaded into memory).
- Chart font rendering depends on Matplotlib's bundled fonts; custom fonts require system installation.
- No multi-processing; processes sequentially.
