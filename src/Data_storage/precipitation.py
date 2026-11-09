"""Estimated precipitation from half-hourly Tomorrow.io intensity samples.

A sample is a rate (mm/h), not an observed interval accumulation. We assume
that a valid rate represents its 30-minute slot; gaps are never interpolated.
"""

from datetime import datetime, timedelta
import math

import pandas as pd

from config import meses

RATE_COLUMN = "precipitation (mm/h)"
SLOT = timedelta(minutes=30)


def valid_rate(value):
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def samples_for_day(rows, year, month, day):
    """Return one valid rate per local slot, plus anomaly descriptions.

    Duplicate local clock times cannot be distinguished at the autumn DST change
    without an offset or UTC timestamp, so only the first is counted.
    """
    slots = {}
    anomalies = []
    for _, row in rows.iterrows():
        hour = row.get("Hora")
        try:
            if not isinstance(hour, str) or len(hour) != 5:
                raise ValueError
            stamp = datetime.strptime(f"{year}-{month:02d}-{day:02d} {hour}", "%Y-%m-%d %H:%M")
            if stamp.minute not in (0, 30):
                raise ValueError
        except ValueError:
            anomalies.append(f"hora inválida: {hour!r}")
            continue
        if stamp in slots:
            anomalies.append(f"hora duplicada: {hour}")
            continue
        rate = valid_rate(row.get(RATE_COLUMN))
        if rate is None:
            anomalies.append(f"intensidad inválida: {hour}={row.get(RATE_COLUMN)!r}")
        slots[stamp] = rate
    return slots, anomalies


def daily_precipitation(rows, year, month, day):
    slots, anomalies = samples_for_day(rows, year, month, day)
    valid = {stamp: rate * 0.5 for stamp, rate in slots.items() if rate is not None}
    total = sum(valid.values()) if valid else None
    pairs = [amount + valid[stamp + SLOT] for stamp, amount in valid.items()
             if stamp + SLOT in valid and (stamp + SLOT).date() == stamp.date()]
    return total, max(pairs) if pairs else None, slots, anomalies


def precipitation_series(data):
    """Estimated mm per valid CSV row, with duplicate slots counted once."""
    result = pd.Series(float("nan"), index=data.index, dtype=float)
    if data.empty or RATE_COLUMN not in data or not {"Year", "Mes", "Dia", "Hora"}.issubset(data):
        return result
    seen = set()
    for index, row in data.iterrows():
        try:
            year = int(row["Year"])
            month = meses.index(str(row["Mes"])) + 1
            day = int(row["Dia"])
            hour = str(row["Hora"])
            if len(hour) != 5:
                continue
            stamp = datetime.strptime(f"{year}-{month:02d}-{day:02d} {hour}", "%Y-%m-%d %H:%M")
            if stamp.minute not in (0, 30) or stamp in seen:
                continue
        except (ValueError, TypeError):
            continue
        seen.add(stamp)
        rate = valid_rate(row[RATE_COLUMN])
        if rate is not None:
            result.loc[index] = rate * 0.5
    return result
