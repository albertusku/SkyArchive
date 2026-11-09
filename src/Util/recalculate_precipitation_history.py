"""Repair only precipitation statistics from immutable half-hourly history.

Run with --dry-run first. Stop the collector while applying changes so its
normal CSV appends cannot race with this migration.
"""

import argparse
import calendar
import csv
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from zoneinfo import ZoneInfo

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import DATA_DIR, meses
from Data_storage.precipitation import daily_precipitation

import pandas as pd

FILES = ("Historical_weather.csv", "Statistics_day.csv", "Statistics_month.csv")
FIELDS_DAY = ("precipitaciones_totales", "precipitacion_max_1h")
ZONE = ZoneInfo("Europe/Madrid")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV vacío: {path}")
        return reader.fieldnames, list(reader)


def key(row, daily=True):
    try:
        year = int(row["Year"])
        month = meses.index(row["Mes"]) + 1
        day = int(row["Dia"]) if daily else 1
        return date(year, month, day)
    except (KeyError, ValueError, TypeError):
        return None


def expected_slots(day):
    start = datetime(day.year, day.month, day.day, tzinfo=ZONE)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), ZONE)
    hours = (end.astimezone(ZoneInfo("UTC")) - start.astimezone(ZoneInfo("UTC"))).total_seconds() / 3600
    return int(hours * 2)


def clock_time_exists(stamp):
    """Check whether a naive local timestamp exists on the DST spring day."""
    aware = stamp.replace(tzinfo=ZONE)
    return aware.astimezone(timezone.utc).astimezone(ZONE).replace(tzinfo=None) == stamp


def fmt(value):
    return "" if value is None else format(value, ".12g")


def change(row, field, value, period, changes):
    old = row.get(field, "")
    new = fmt(value)
    if old != new:
        try:
            delta = float(new) - float(old)
        except (ValueError, TypeError):
            delta = None
        changes.append({"periodo": str(period), "campo": field, "anterior": old,
                        "nuevo": new, "diferencia": delta})
        row[field] = new


def stage_and_replace(outputs):
    """Stage/validate both outputs, back up originals, roll both back on error."""
    staged = {}
    backups = {}
    original = {path: path.read_bytes() for path in outputs}
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    try:
        for path, (fields, rows) in outputs.items():
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                             prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
                staged[path] = Path(handle.name)
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
            check_fields, check_rows = read_csv(staged[path])
            if check_fields != fields or check_rows != rows:
                raise RuntimeError(f"Validación de salida fallida: {path}")
        for path in outputs:
            backup = path.with_name(path.name + ".bak_" + stamp)
            shutil.copy2(path, backup)
            if backup.read_bytes() != original[path]:
                raise RuntimeError(f"Copia de seguridad inválida: {backup}")
            backups[path] = backup
        for path in outputs:
            os.replace(staged[path], path)
    except Exception:
        for path, contents in original.items():
            if path.read_bytes() != contents:
                with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
                    handle.write(contents)
                    handle.flush()
                    os.fsync(handle.fileno())
                    restore = Path(handle.name)
                os.replace(restore, path)
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)
    return [str(backup) for backup in backups.values()]


def recalculate(directory=DATA_DIR, dry_run=False):
    directory = Path(directory)
    history_path, day_path, month_path = (directory / name for name in FILES)
    history_fields, history = read_csv(history_path)
    day_fields, days = read_csv(day_path)
    month_fields, months = read_csv(month_path)
    for fields, required in ((history_fields, ("Year", "Mes", "Dia", "Hora", "precipitation (mm/h)")),
                             (day_fields, ("Year", "Mes", "Dia", *FIELDS_DAY)),
                             (month_fields, ("Year", "Mes", "precipitaciones_totales"))):
        missing = set(required) - set(fields)
        if missing:
            raise ValueError(f"Faltan columnas: {sorted(missing)}")
    anomalies = []
    grouped = {}
    for number, row in enumerate(history, 2):
        stamp = key(row)
        if stamp is None:
            anomalies.append(f"Histórico línea {number}: fecha inválida")
            continue
        grouped.setdefault(stamp, []).append(row)
    calculated = {}
    incomplete = []
    for stamp, rows in sorted(grouped.items()):
        total, maximum, slots, errors = daily_precipitation(pd.DataFrame(rows), stamp.year, stamp.month, stamp.day)
        for clock in list(slots):
            if not clock_time_exists(clock):
                del slots[clock]
                errors.append(f"hora inexistente por cambio horario: {clock:%H:%M}")
        # Recompute after excluding nonexistent local timestamps.
        if any("hora inexistente" in error for error in errors):
            filtered = [r for r in rows if r.get("Hora") not in {e[-5:] for e in errors if "hora inexistente" in e}]
            total, maximum, slots, other_errors = daily_precipitation(pd.DataFrame(filtered), stamp.year, stamp.month, stamp.day)
            errors = [e for e in errors if "hora inexistente" in e] + other_errors
        anomalies.extend(f"{stamp}: {error}" for error in errors)
        expected = expected_slots(stamp)
        valid_count = sum(rate is not None for rate in slots.values())
        # During autumn DST, repeated 02:00/02:30 lack an offset and are ambiguous.
        complete = valid_count == expected and not errors
        if not complete:
            incomplete.append({"periodo": str(stamp), "intervalos_validos": valid_count,
                               "intervalos_esperados": expected})
        if len(rows) >= 2:
            weather_fields = [field for field in history_fields if field not in ("Year", "Mes", "Dia", "Hora")]
            for previous, current in zip(rows, rows[1:]):
                if previous.get("Hora") != current.get("Hora") and all(previous.get(f) == current.get(f) for f in weather_fields):
                    anomalies.append(f"{stamp}: posible copia artificial entre {previous.get('Hora')} y {current.get('Hora')} (incierto)")
        calculated[stamp] = (total, maximum, complete)
    changes = []
    indexed_days = {}
    for row in days:
        stamp = key(row)
        if stamp is None:
            anomalies.append("Statistics_day.csv: fecha inválida")
        elif stamp in indexed_days:
            anomalies.append(f"Statistics_day.csv: fecha duplicada {stamp}; se omite")
            indexed_days[stamp] = None
        else:
            indexed_days[stamp] = row
    for stamp, (total, maximum, _) in calculated.items():
        row = indexed_days.get(stamp)
        if row is None:
            anomalies.append(f"{stamp}: sin fila diaria única; no se inventan otras estadísticas")
            continue
        if total is not None:
            change(row, FIELDS_DAY[0], total, stamp, changes)
        if total is not None:
            change(row, FIELDS_DAY[1], maximum, stamp, changes)
    indexed_months = {}
    for row in months:
        stamp = key(row, daily=False)
        if stamp is None:
            anomalies.append("Statistics_month.csv: fecha inválida")
        elif stamp in indexed_months:
            anomalies.append(f"Statistics_month.csv: mes duplicado {stamp:%Y-%m}; se omite")
            indexed_months[stamp] = None
        else:
            indexed_months[stamp] = row
    month_candidates = sorted({stamp.replace(day=1) for stamp in calculated})
    for first in month_candidates:
        count = calendar.monthrange(first.year, first.month)[1]
        dates = [first + timedelta(days=offset) for offset in range(count)]
        if not all(stamp in calculated and calculated[stamp][2] and indexed_days.get(stamp) is not None for stamp in dates):
            incomplete.append({"periodo": first.strftime("%Y-%m"), "motivo": "mes incompleto; total mensual sin actualizar"})
            continue
        row = indexed_months.get(first)
        if row is None:
            anomalies.append(f"{first:%Y-%m}: sin fila mensual única; no se inventan otras estadísticas")
            continue
        change(row, "precipitaciones_totales", sum(calculated[stamp][0] for stamp in dates), first.strftime("%Y-%m"), changes)
    report = {"registros_examinados": len(history), "fechas_procesadas": len(calculated),
              "dias_corregidos": len({c['periodo'] for c in changes if c['campo'] in FIELDS_DAY}),
              "meses_corregidos": len({c['periodo'] for c in changes if c['campo'] == 'precipitaciones_totales' and len(c['periodo']) == 7}),
              "cambios": changes, "periodos_incompletos": incomplete, "anomalias": anomalies,
              "registros_duplicados": sum("hora duplicada" in item for item in anomalies),
              "errores": [item for item in anomalies if "inválid" in item or "inexistente" in item],
              "copias_seguridad": [], "dry_run": dry_run}
    if not dry_run and changes:
        report["copias_seguridad"] = stage_and_replace({day_path: (day_fields, days), month_path: (month_fields, months)})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--directory", type=Path, default=DATA_DIR)
    args = parser.parse_args(argv)
    try:
        report = recalculate(args.directory, args.dry_run)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
