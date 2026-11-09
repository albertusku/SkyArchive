import pandas as pd
from datetime import datetime

import Data_storage.statistics as statistics
import Data_storage.storage_builder as storage_builder


def test_make_statistics_day_calculates_weather_summary(monkeypatch, tmp_path):
    saved = {}

    def fake_save_csv(df, path):
        saved["df"] = df.copy()
        saved["path"] = path
        return df

    monkeypatch.setattr(storage_builder, "save_csv", fake_save_csv)
    monkeypatch.setattr(statistics, "STATISTICS_DAY_DIR", str(tmp_path / "day.csv"))
    df = pd.DataFrame(
        [
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 11,
                "Hora": "00:00",
                "temp (C)": 10,
                "precipitation (mm/h)": 0.5,
                "wind_speed(m/s)": 1,
                "hum(%)": 40,
                "pres(hPa)": 1010,
                "clouds(%)": 20,
            },
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 11,
                "Hora": "00:30",
                "temp (C)": 14,
                "precipitation (mm/h)": 1.0,
                "wind_speed(m/s)": 4,
                "hum(%)": 50,
                "pres(hPa)": 1012,
                "clouds(%)": 30,
            },
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 11,
                "Hora": "01:00",
                "temp (C)": 8,
                "precipitation (mm/h)": 0.0,
                "wind_speed(m/s)": 2,
                "hum(%)": 60,
                "pres(hPa)": 1014,
                "clouds(%)": 40,
            },
        ]
    )

    result = statistics.make_statistics_day(df, 11, "June", 2026)

    row = result.iloc[0]
    assert saved["path"].endswith("day.csv")
    assert row["temp_max"] == 14
    assert row["temp_min"] == 8
    assert row["temp_mean"] == 32 / 3
    assert row["precipitaciones_totales"] == 0.75
    assert row["precipitacion_max_1h"] == 0.75
    assert row["wind_speed_max"] == 4
    assert row["humidity"] == 50
    assert row["pressure"] == 1012
    assert row["clouds"] == 30


def test_make_statistics_uses_previous_row_to_close_previous_day(monkeypatch):
    calls = []
    monkeypatch.setattr(statistics, "make_statistics_day", lambda df, day, month, year: calls.append((day, month, year)) or pd.DataFrame())
    monkeypatch.setattr(statistics, "make_statistics_month", lambda *args: None)
    monkeypatch.setattr(statistics, "make_model_prediction", lambda: None)
    monkeypatch.setattr(statistics, "now", datetime(2026, 6, 12, 0, 0))
    df = pd.DataFrame(
        [
            {"Year": 2026, "Mes": "June", "Dia": 11, "Hora": "23:30"},
            {"Year": 2026, "Mes": "June", "Dia": 12, "Hora": "00:00"},
        ]
    )

    statistics.make_statistics(df)

    assert calls == [(11, "June", 2026)]


def test_make_statistics_electricity_day_writes_consumption_and_production(monkeypatch):
    writes = []
    monkeypatch.setattr(storage_builder, "save_csv", lambda df, path: writes.append((df.copy(), path)))
    monkeypatch.setattr(statistics, "STATISTICS_ELECTRICITY_DAY_CONSUMPTION_DIR", "consumption.csv")
    monkeypatch.setattr(statistics, "STATISTICS_ELECTRICITY_DAY_PRODUCTION_DIR", "production.csv")
    monkeypatch.setattr(statistics, "now", datetime(2026, 6, 12, 0, 0))
    keys = [
        "nuclear",
        "geothermal",
        "biomass",
        "coal",
        "wind",
        "solar",
        "hydro",
        "gas",
        "oil",
        "unknown",
        "hydro discharge",
        "battery discharge",
    ]

    def electricity_df(multiplier):
        rows = []
        for day, hour, value in [(11, "23:00", 10), (11, "23:30", 20), (12, "00:00", 30)]:
            row = {"Year": 2026, "Mes": "June", "Dia": day, "Hora": hour}
            row.update({key: value * multiplier for key in keys})
            rows.append(row)
        return pd.DataFrame(rows)

    statistics.make_statistics_electricity_day([electricity_df(1), electricity_df(2)])

    assert [path for _, path in writes] == ["consumption.csv", "production.csv"]
    assert writes[0][0].iloc[0]["Dia"] == 11
    assert writes[0][0].iloc[0]["nuclear"] == 15
    assert writes[1][0].iloc[0]["nuclear"] == 30


def test_monthly_precipitation_uses_one_daily_value_per_date():
    data = pd.DataFrame([
        {"Year": 2025, "Mes": "December", "Dia": 31, "temp_max": 10,
         "temp_min": 1, "temp_mean": 5, "precipitaciones_totales": 100, "wind_speed_max": 2},
        {"Year": 2026, "Mes": "January", "Dia": 1, "temp_max": 11,
         "temp_min": 2, "temp_mean": 6, "precipitaciones_totales": 1, "wind_speed_max": 3},
        {"Year": 2026, "Mes": "January", "Dia": 1, "temp_max": 11,
         "temp_min": 2, "temp_mean": 6, "precipitaciones_totales": 2, "wind_speed_max": 3},
        {"Year": 2026, "Mes": "January", "Dia": 2, "temp_max": 12,
         "temp_min": 3, "temp_mean": 7, "precipitaciones_totales": 3, "wind_speed_max": 4},
    ])
    result = statistics.calculate_statistics_month(data, "January", 2026)
    assert result["precipitaciones_totales"] == 5
