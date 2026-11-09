import csv
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from Data_storage.precipitation import daily_precipitation, precipitation_series
from Util import recalculate_precipitation_history as migration


def row(day=1, month="January", year=2025, hour="00:00", rate="2"):
    return {"Year": str(year), "Mes": month, "Dia": str(day), "Hora": hour,
            "precipitation (mm/h)": rate}


def write(path, rows, fields):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fixture_files(tmp_path, history, days, months):
    write(tmp_path / migration.FILES[0], history, list(row()))
    write(tmp_path / migration.FILES[1], days,
          ["Year", "Mes", "Dia", "precipitaciones_totales", "precipitacion_max_1h", "temp_max"])
    write(tmp_path / migration.FILES[2], months,
          ["Year", "Mes", "precipitaciones_totales", "temp_max"])


def day_row(day=1, month="January", year=2025, total="10", maximum="10"):
    return {"Year": year, "Mes": month, "Dia": day, "precipitaciones_totales": total,
            "precipitacion_max_1h": maximum, "temp_max": "17.5"}


def month_row(month="January", year=2025):
    return {"Year": year, "Mes": month, "precipitaciones_totales": "10", "temp_max": "21"}


def test_rates_and_hour_window():
    rows = pd.DataFrame([row(rate="2"), row(hour="00:30", rate="4"),
                         row(hour="01:00", rate="6")])
    total, maximum, _, errors = daily_precipitation(rows, 2025, 1, 1)
    assert (total, maximum, errors) == (6, 5, [])
    assert daily_precipitation(pd.DataFrame([row(rate="2")]), 2025, 1, 1)[0] == 1
    assert daily_precipitation(pd.DataFrame([row(rate="0")]), 2025, 1, 1)[0] == 0
    gap = pd.DataFrame([row(rate="2"), row(hour="01:00", rate="4")])
    assert daily_precipitation(gap, 2025, 1, 1)[1] is None


def test_duplicates_and_invalid_values():
    data = pd.DataFrame([row(rate="2"), row(rate="9"), row(hour="00:30", rate="N/A"),
                         row(hour="01:00", rate="-1"), row(hour="01:30", rate="bad")])
    total, maximum, _, errors = daily_precipitation(data, 2025, 1, 1)
    assert total == 1 and maximum is None
    assert len(errors) == 4
    assert precipitation_series(data).sum() == 1


def test_dry_run_repeat_preserves_history_and_other_fields(tmp_path):
    fixture_files(tmp_path, [row(), row(hour="00:30", rate="2")], [day_row()], [month_row()])
    paths = [tmp_path / name for name in migration.FILES]
    before = [path.read_bytes() for path in paths]
    preview = migration.recalculate(tmp_path, dry_run=True)
    assert preview["dias_corregidos"] == 1
    assert [path.read_bytes() for path in paths] == before
    result = migration.recalculate(tmp_path)
    assert len(result["copias_seguridad"]) == 2
    assert paths[0].read_bytes() == before[0]
    daily = pd.read_csv(paths[1]).iloc[0]
    assert daily["precipitaciones_totales"] == 2
    assert daily["precipitacion_max_1h"] == 2
    assert daily["temp_max"] == 17.5
    assert pd.read_csv(paths[2]).iloc[0]["temp_max"] == 21
    assert [Path(path).read_bytes() for path in result["copias_seguridad"]] == before[1:]
    corrected = [path.read_bytes() for path in paths]
    repeat = migration.recalculate(tmp_path)
    assert repeat["cambios"] == [] and repeat["copias_seguridad"] == []
    assert [path.read_bytes() for path in paths] == corrected


def test_month_complete_and_year_boundaries(tmp_path):
    history = [row(day=d, month="February", year=2025, rate="2") for d in range(1, 29)]
    days = [day_row(day=d, month="February", year=2025) for d in range(1, 29)]
    # One sample per day is incomplete: monthly total must remain unchanged.
    fixture_files(tmp_path, history, days, [month_row(month="February", year=2025), month_row(year=2024)])
    report = migration.recalculate(tmp_path)
    assert report["meses_corregidos"] == 0
    assert all(r["precipitaciones_totales"] == "10" for r in csv.DictReader((tmp_path / migration.FILES[2]).open()))
    assert any(item["periodo"] == "2025-02" for item in report["periodos_incompletos"])


def test_dst_expected_slots():
    assert migration.expected_slots(date(2025, 3, 30)) == 46
    assert migration.expected_slots(date(2025, 10, 26)) == 50
    assert migration.expected_slots(date(2025, 3, 29)) == 48


def test_second_replace_failure_rolls_back_both(tmp_path, monkeypatch):
    fixture_files(tmp_path, [row()], [day_row()], [month_row()])
    paths = [tmp_path / name for name in migration.FILES]
    before = [path.read_bytes() for path in paths]
    original_replace = migration.os.replace
    calls = 0
    def fail_second(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        return original_replace(source, target)
    monkeypatch.setattr(migration.os, "replace", fail_second)
    with pytest.raises(OSError, match="simulated"):
        migration.recalculate(tmp_path)
    assert [path.read_bytes() for path in paths] == before


def test_command_dry_run(tmp_path, capsys):
    fixture_files(tmp_path, [row()], [day_row()], [month_row()])
    assert migration.main(["--dry-run", "--directory", str(tmp_path)]) == 0
    assert '"dry_run": true' in capsys.readouterr().out


def test_complete_february_month_is_sum_of_daily_estimates(tmp_path):
    history = [row(day=day, month="February", hour=f"{hour:02d}:{minute:02d}")
               for day in range(1, 29) for hour in range(24) for minute in (0, 30)]
    days = [day_row(day=day, month="February") for day in range(1, 29)]
    fixture_files(tmp_path, history, days, [month_row(month="February")])
    report = migration.recalculate(tmp_path)
    assert report["meses_corregidos"] == 1
    daily = pd.read_csv(tmp_path / migration.FILES[1])
    monthly = pd.read_csv(tmp_path / migration.FILES[2])
    assert monthly.iloc[0]["precipitaciones_totales"] == daily["precipitaciones_totales"].sum() == 1344


def test_day_month_year_boundaries_do_not_form_false_hour_windows():
    samples = pd.DataFrame([row(day=31, month="December", year=2025, hour="23:30"),
                            row(day=1, month="January", year=2026, hour="00:00")])
    a = daily_precipitation(samples.iloc[:1], 2025, 12, 31)
    b = daily_precipitation(samples.iloc[1:], 2026, 1, 1)
    assert (a[0], b[0]) == (1, 1)
    assert a[1] is b[1] is None


def test_dst_spring_nonexistent_clock_is_excluded(tmp_path):
    fixture_files(tmp_path, [row(day=30, month="March", hour="02:00", rate="8"),
                             row(day=30, month="March", hour="03:00", rate="2")],
                  [day_row(day=30, month="March")], [month_row(month="March")])
    report = migration.recalculate(tmp_path)
    assert pd.read_csv(tmp_path / migration.FILES[1]).iloc[0]["precipitaciones_totales"] == 1
    assert any("hora inexistente" in item for item in report["errores"])
