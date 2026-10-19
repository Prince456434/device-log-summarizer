"""
sanitizer.py — Sensor reading sanitization utilities.

Provides clean_sensor_readings() which converts a mixed list of raw sensor
values into a list of valid, finite, non-negative floats capped at 500.0.
"""

import math
from typing import Any


def clean_sensor_readings(values: list[Any]) -> list[float]:
    """Convert and validate a list of raw sensor readings.

    Rules applied in order:
    1. Booleans are rejected (bool is a subclass of int; we reject them first).
    2. None values are rejected.
    3. Values that cannot be converted to float are rejected.
    4. NaN, +inf, and -inf are rejected.
    5. Negative numbers are rejected.
    6. Values above 500.0 are capped at 500.0.
    7. The original list is never mutated.

    Args:
        values: A list of raw sensor readings in any type.

    Returns:
        A list of valid floats in the range [0.0, 500.0], preserving order.
    """
    result: list[float] = []

    for v in values:
        # Rule 1: Reject booleans explicitly (bool is subclass of int).
        if isinstance(v, bool):
            continue

        # Rule 2: Reject None.
        if v is None:
            continue

        # Rule 3: Attempt float conversion.
        try:
            fv = float(v)
        except (ValueError, TypeError):
            continue

        # Rule 4: Reject non-finite values (NaN, +inf, -inf).
        if not math.isfinite(fv):
            continue

        # Rule 5: Reject negative numbers.
        if fv < 0.0:
            continue

        # Rule 6: Cap at 500.0.
        if fv > 500.0:
            fv = 500.0

        result.append(fv)

    return result
