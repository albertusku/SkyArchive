import pandas as pd

from Visualizer.dashboard_charts import (
    TEMP_MAX_COLOR,
    TEMP_MIN_COLOR,
    daily_precipitation_total_chart,
    daily_weather_summary_chart,
    electricity_mix_chart,
    forecast_rain_accuracy_chart,
    forecast_temperature_chart,
    forecast_temperature_accuracy_chart,
    historical_temperature_chart,
    monthly_temperature_chart,
    precipitation_statistics_chart,
    temperature_statistics_chart,
    temperature_humidity_scatter_chart,
    water_reserve_chart,
)
from Visualizer.dashboard_data import (
    add_accumulated_precipitation,
    advanced_weather_insights,
    cloud_cover_icon_key,
    count_log_levels,
    current_weather_summary,
    dashboard_page_availability,
    daily_weather_breakdown,
    daily_rain_total_from_historical,
    filter_current_electricity_day,
    filter_historical_weather,
    filter_latest_days,
    filter_log_lines,
    filter_monthly_year,
    filter_recent_days,
    forecast_accuracy_summary,
    format_log_message,
    format_metric,
    load_csv_file,
    latest_weather_reading,
    normalize_month,
    prepare_forecast_horizons,
    prepare_forecast_accuracy,
    prepare_historical_weather,
    prepare_daily_statistics,
    prepare_forecast_row,
    prepare_monthly_statistics,
    prepare_water_reserve,
    read_text_file,
    satellite_state_counts,
    satellite_state_style,
    statistics_summary,
    water_reserve_summary,
    weather_summary,
    write_text_file,
)


def test_load_csv_file_reports_missing_and_empty_files(tmp_path):
    missing_file = tmp_path / "missing.csv"
    try:
        load_csv_file(missing_file, "missing.csv")
    except ValueError as exc:
        assert "No existe missing.csv" in str(exc)
    else:
        raise AssertionError("load_csv_file should fail for missing files")

    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    try:
        load_csv_file(empty_file, "empty.csv")
    except ValueError as exc:
        assert "empty.csv existe, pero esta vacio" in str(exc)
    else:
        raise AssertionError("load_csv_file should fail for empty files")


def test_load_csv_file_reads_existing_csv(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b\n1,2\n")

    data = load_csv_file(csv_file)

    assert data.to_dict("records") == [{"a": 1, "b": 2}]


def test_dashboard_pages_hide_forecast_when_forecast_csv_is_missing(tmp_path):
    paths = {
        "forecast": tmp_path / "Historical_weather_forecast.csv",
        "daily_stats": tmp_path / "Statistics_day.csv",
        "monthly_stats": tmp_path / "Statistics_month.csv",
        "electricity_consumption": tmp_path / "Electricity_consumption.csv",
        "electricity_production": tmp_path / "Electricity_production.csv",
        "water_reservoir": tmp_path / "Water_reserve.csv",
        "satellites": tmp_path / "Satellite_status.csv",
        "season_predictions": tmp_path / "Season_prediction.csv",
    }

    pages = dashboard_page_availability(paths)

    assert "forecast" not in pages
    assert "home" in pages
    assert "logs" in pages
    assert "todo" in pages


def test_dashboard_pages_show_electricity_when_consumption_or_production_exists(tmp_path):
    paths = {
        "forecast": tmp_path / "Historical_weather_forecast.csv",
        "daily_stats": tmp_path / "Statistics_day.csv",
        "monthly_stats": tmp_path / "Statistics_month.csv",
        "electricity_consumption": tmp_path / "Electricity_consumption.csv",
        "electricity_production": tmp_path / "Electricity_production.csv",
        "water_reservoir": tmp_path / "Water_reserve.csv",
        "satellites": tmp_path / "Satellite_status.csv",
        "season_predictions": tmp_path / "Season_prediction.csv",
    }
    paths["electricity_consumption"].write_text("Mes,Dia,solar\nJuly,9,1\n")

    assert "electricity" in dashboard_page_availability(paths)

    paths["electricity_consumption"].unlink()
    paths["electricity_production"].write_text("Mes,Dia,solar\nJuly,9,1\n")

    assert "electricity" in dashboard_page_availability(paths)


def test_dashboard_pages_keep_logs_and_todo_visible_without_csvs(tmp_path):
    paths = {
        "forecast": tmp_path / "Historical_weather_forecast.csv",
        "daily_stats": tmp_path / "Statistics_day.csv",
        "monthly_stats": tmp_path / "Statistics_month.csv",
        "electricity_consumption": tmp_path / "Electricity_consumption.csv",
        "electricity_production": tmp_path / "Electricity_production.csv",
        "water_reservoir": tmp_path / "Water_reserve.csv",
        "satellites": tmp_path / "Satellite_status.csv",
        "season_predictions": tmp_path / "Season_prediction.csv",
    }

    pages = dashboard_page_availability(paths)

    assert pages == ["home", "logs", "todo"]


def test_normalize_month_accepts_names_numbers_and_invalid_values():
    assert normalize_month("June") == 6
    assert normalize_month(" 6 ") == 6
    assert normalize_month(6) == 6
    assert pd.isna(normalize_month("bad-month"))


def test_filter_historical_weather_keeps_requested_period_and_adds_label():
    data = pd.DataFrame(
        [
            {"Year": 2026, "Mes": "June", "Dia": 27, "Hora": "10:00", "temp (C)": 21},
            {"Year": 2026, "Mes": "July", "Dia": 1, "Hora": "11:00", "temp (C)": 22},
        ]
    )

    result = filter_historical_weather(data, [2026], ["June"], [27])

    assert len(result) == 1
    assert result.iloc[0]["Año_Mes_Dia_Hora"] == "June/27 - 10:00 (2026)"


def test_prepare_historical_weather_and_summaries_build_comparable_data():
    data = pd.DataFrame(
        [
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 27,
                "Hora": "10:00",
                "temp (C)": 21,
                "precipitation (mm/h)": 1.5,
                "wind_speed(m/s)": 4,
                "hum(%)": 60,
                "pres(hPa)": 1010,
                "clouds(%)": 30,
            },
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 27,
                "Hora": "11:00",
                "temp (C)": 23,
                "precipitation (mm/h)": 0.5,
                "wind_speed(m/s)": 6,
                "hum(%)": 50,
                "pres(hPa)": 1012,
                "clouds(%)": 40,
            },
        ]
    )

    prepared = prepare_historical_weather(data)
    summary = weather_summary(prepared)
    daily = daily_weather_breakdown(prepared)

    assert prepared.iloc[0]["Periodo"] == "2026-06-27"
    assert summary["records"] == 2
    assert summary["rain_total"] == 1.0
    assert daily.iloc[0]["temp_max"] == 23
    assert daily.iloc[0]["precipitation_total"] == 1.0


def test_latest_weather_reading_uses_latest_valid_date_and_hour():
    data = pd.DataFrame(
        [
            {"Year": 2026, "Mes": "July", "Dia": 1, "Hora": "09:00", "temp (C)": 22},
            {"Year": 2026, "Mes": "June", "Dia": 30, "Hora": "23:00", "temp (C)": 20},
            {"Year": 2026, "Mes": "July", "Dia": 1, "Hora": "11:00", "temp (C)": 24},
        ]
    )

    latest = latest_weather_reading(data)

    assert latest["Dia"] == 1
    assert latest["Hora"] == "11:00"
    assert latest["temp (C)"] == 24


def test_current_weather_summary_uses_latest_reading_and_current_day_rain_total():
    data = pd.DataFrame(
        [
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 30,
                "Hora": "23:00",
                "temp (C)": 20,
                "precipitation (mm/h)": 9,
                "wind_speed(m/s)": 2,
                "hum(%)": 60,
                "pres(hPa)": 1010,
                "clouds(%)": 30,
            },
            {
                "Year": 2026,
                "Mes": "July",
                "Dia": 1,
                "Hora": "10:00",
                "temp (C)": 23,
                "precipitation (mm/h)": 1.5,
                "wind_speed(m/s)": 4,
                "hum(%)": 55,
                "pres(hPa)": 1011,
                "clouds(%)": 40,
            },
            {
                "Year": 2026,
                "Mes": "July",
                "Dia": 1,
                "Hora": "11:00",
                "temp (C)": 25,
                "precipitation (mm/h)": 0.5,
                "wind_speed(m/s)": 6,
                "hum(%)": 50,
                "pres(hPa)": 1012,
                "clouds(%)": 60,
            },
        ]
    )

    latest = latest_weather_reading(data)
    summary = current_weather_summary(data)

    assert daily_rain_total_from_historical(data, latest) == 1.0
    assert summary["temperature"] == 25
    assert summary["humidity"] == 50
    assert summary["rain_today"] == 1.0
    assert summary["wind_speed"] == 6
    assert summary["pressure"] == 1012


def test_cloud_cover_icon_key_maps_cloud_ranges():
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 0})) == "sun"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 25})) == "sun"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 26})) == "sun_few_clouds"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 50})) == "sun_few_clouds"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 51})) == "sun_mostly_cloudy"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 75})) == "sun_mostly_cloudy"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 76})) == "clouds"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": 100})) == "clouds"


def test_cloud_cover_icon_key_prioritizes_rain_and_handles_missing_clouds():
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0.1, "clouds(%)": 10})) == "rain"
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0})) is None
    assert cloud_cover_icon_key(pd.Series({"precipitation (mm/h)": 0, "clouds(%)": pd.NA})) is None


def test_advanced_weather_insights_extracts_hidden_signals():
    data = prepare_historical_weather(
        pd.DataFrame(
            [
                {
                    "Year": 2026,
                    "Mes": "June",
                    "Dia": 27,
                    "Hora": "10:00",
                    "temp (C)": 20,
                    "precipitation (mm/h)": 0,
                    "pres(hPa)": 1010,
                    "hum(%)": 80,
                    "clouds(%)": 40,
                },
                {
                    "Year": 2026,
                    "Mes": "June",
                    "Dia": 27,
                    "Hora": "11:00",
                    "temp (C)": 25,
                    "precipitation (mm/h)": 2,
                    "pres(hPa)": 1008,
                    "hum(%)": 60,
                    "clouds(%)": 60,
                },
            ]
        )
    )

    result = advanced_weather_insights(data)

    assert result["thermal_amplitude"] == 5
    assert result["rain_hours"] == 1
    assert result["max_rain_rate"] == 2
    assert result["pressure_trend"] == -2
    assert result["cloud_cover_mean"] == 50


def test_prepare_daily_statistics_builds_fecha_and_filters_invalid_rows():
    data = pd.DataFrame(
        [
            {"Year": "2026", "Mes": "June", "Dia": "27", "precipitaciones_totales": 2},
            {"Year": "bad", "Mes": "June", "Dia": "28", "precipitaciones_totales": 3},
        ]
    )

    result = prepare_daily_statistics(data)

    assert len(result) == 1
    assert result.iloc[0]["Fecha"] == pd.Timestamp("2026-06-27")


def test_filter_recent_days_and_accumulated_precipitation():
    data = prepare_daily_statistics(
        pd.DataFrame(
            [
                {"Year": 2026, "Mes": "June", "Dia": 25, "precipitaciones_totales": 1},
                {"Year": 2026, "Mes": "June", "Dia": 27, "precipitaciones_totales": 3},
            ]
        )
    )

    recent = filter_recent_days(data, 1, pd.Timestamp("2026-06-27 12:00:00"))
    accumulated = add_accumulated_precipitation(recent)

    assert len(accumulated) == 1
    assert accumulated.iloc[0]["precipitacion_acumulada"] == 3


def test_filter_latest_days_returns_requested_available_rows():
    data = prepare_daily_statistics(
        pd.DataFrame(
            [
                {"Year": 2026, "Mes": "June", "Dia": 24, "precipitaciones_totales": 1},
                {"Year": 2026, "Mes": "June", "Dia": 25, "precipitaciones_totales": 2},
                {"Year": 2026, "Mes": "June", "Dia": 26, "precipitaciones_totales": 3},
                {"Year": 2026, "Mes": "June", "Dia": 27, "precipitaciones_totales": 4},
            ]
        )
    )

    result = filter_latest_days(data, 3)

    assert len(result) == 3
    assert result["Dia"].tolist() == [25, 26, 27]


def test_statistics_summary_and_format_metric_handle_optional_values():
    data = pd.DataFrame(
        [
            {"temp_max": 30, "temp_min": 12, "temp_mean": 21, "precipitaciones_totales": 1, "wind_speed_max": 5},
            {"temp_max": 32, "temp_min": 10, "temp_mean": 22, "precipitaciones_totales": 2, "wind_speed_max": 7},
        ]
    )

    summary = statistics_summary(data)

    assert summary["days"] == 2
    assert summary["temp_max"] == 32
    assert summary["rain_total"] == 3
    assert format_metric(summary["temp_min"], " °C") == "10.0 °C"
    assert format_metric(pd.NA) == "--"


def test_prepare_monthly_statistics_and_filter_year_order_months():
    data = pd.DataFrame(
        [
            {"Year": 2026, "Mes": "February", "precipitaciones_totales": 2},
            {"Year": 2026, "Mes": "January", "precipitaciones_totales": 1},
            {"Year": 2025, "Mes": "December", "precipitaciones_totales": 9},
        ]
    )

    prepared = prepare_monthly_statistics(data)
    result = filter_monthly_year(prepared, 2026)

    assert result["Mes"].tolist() == ["January", "February"]
    assert result["precipitacion_acumulada"].tolist() == [1, 3]


def test_prepare_forecast_row_renames_future_columns_from_latest_row():
    forecast = pd.DataFrame(
        [
            {
                "Fecha Actual": "2026-06-27",
                "Tmax mañana": 20,
                "Tmin mañana": 10,
                "Rain acum. mañana": 1,
                "Tmax 3_dias": 23,
                "Tmin 3_dias": 12,
                "Rain acum. 3_dias": 2,
                "Tmax 5_dias": 25,
                "Tmin 5_dias": 13,
                "Rain acum. 5_dias": 3,
            }
        ]
    )

    row, renamed = prepare_forecast_row(forecast)

    assert row["Fecha Actual"] == "2026-06-27"
    assert "Tmax 2026-06-28" in renamed.columns
    assert "Rain acum. 2026-07-02" in renamed.columns


def test_prepare_forecast_horizons_creates_three_rows():
    forecast = pd.DataFrame(
        [
            {
                "Fecha Actual": "2026-06-27",
                "Tmax mañana": 20,
                "Tmin mañana": 10,
                "Rain acum. mañana": 1,
                "Tmax 3_dias": 23,
                "Tmin 3_dias": 12,
                "Rain acum. 3_dias": 2,
                "Tmax 5_dias": 25,
                "Tmin 5_dias": 13,
                "Rain acum. 5_dias": 3,
            }
        ]
    )

    result = prepare_forecast_horizons(forecast)

    assert result["horizonte"].tolist() == ["Mañana", "3 días", "5 días"]
    assert result.iloc[-1]["fecha"] == pd.Timestamp("2026-07-02")


def test_prepare_forecast_horizons_accepts_legacy_capitalized_manana_rain_column():
    forecast = pd.DataFrame(
        [
            {
                "Fecha Actual": "2026-06-27",
                "Tmax mañana": 20,
                "Tmin mañana": 10,
                "Rain acum. Mañana": 1,
                "Tmax 3_dias": 23,
                "Tmin 3_dias": 12,
                "Rain acum. 3_dias": 2,
                "Tmax 5_dias": 25,
                "Tmin 5_dias": 13,
                "Rain acum. 5_dias": 3,
            }
        ]
    )

    row, renamed = prepare_forecast_row(forecast)
    result = prepare_forecast_horizons(forecast)

    assert row["Rain acum. Mañana"] == 1
    assert "Rain acum. 2026-06-28" in renamed.columns
    assert result.iloc[0]["rain_total"] == 1


def test_prepare_forecast_accuracy_compares_predictions_with_real_days():
    forecast = pd.DataFrame(
        [
            {
                "Fecha Actual": "2026-06-27",
                "Tmax mañana": 20,
                "Tmin mañana": 10,
                "Rain acum. mañana": 1,
                "Tmax 3_dias": 23,
                "Tmin 3_dias": 12,
                "Rain acum. 3_dias": 2,
                "Tmax 5_dias": 25,
                "Tmin 5_dias": 13,
                "Rain acum. 5_dias": 3,
            }
        ]
    )
    daily = prepare_daily_statistics(
        pd.DataFrame(
            [
                {
                    "Year": 2026,
                    "Mes": "June",
                    "Dia": 28,
                    "temp_max": 22,
                    "temp_min": 9,
                    "precipitaciones_totales": 4,
                }
            ]
        )
    )

    accuracy = prepare_forecast_accuracy(forecast, daily)
    summary = forecast_accuracy_summary(accuracy)

    assert len(accuracy) == 1
    assert accuracy.iloc[0]["horizonte"] == "Mañana"
    assert accuracy.iloc[0]["error_temp_max"] == -2
    assert accuracy.iloc[0]["error_temp_min"] == 1
    assert accuracy.iloc[0]["error_rain_total"] == -3
    assert summary.iloc[0]["mae_temp_max"] == 2
    assert summary.iloc[0]["mae_rain_total"] == 3


def test_forecast_helpers_allow_horizons_without_daily_statistics():
    forecast = pd.DataFrame(
        [
            {
                "Fecha Actual": "2026-06-27",
                "Tmax mañana": 20,
                "Tmin mañana": 10,
                "Rain acum. mañana": 1,
                "Tmax 3_dias": 23,
                "Tmin 3_dias": 12,
                "Rain acum. 3_dias": 2,
                "Tmax 5_dias": 25,
                "Tmin 5_dias": 13,
                "Rain acum. 5_dias": 3,
            }
        ]
    )

    row, renamed = prepare_forecast_row(forecast)
    horizons = prepare_forecast_horizons(forecast)

    assert row["Fecha Actual"] == "2026-06-27"
    assert "Tmax 2026-06-28" in renamed.columns
    assert len(horizons) == 3


def test_electricity_current_day_filters_by_month_name():
    data = pd.DataFrame(
        [
            {"Mes": "June", "Dia": 27, "solar": 10},
            {"Mes": "June", "Dia": 26, "solar": 5},
        ]
    )

    result = filter_current_electricity_day(data, 6, 27)

    assert len(result) == 1
    assert result.iloc[0]["solar"] == 10


def test_prepare_water_reserve_adds_axis_label():
    data = pd.DataFrame([{"Mes": "June", "Dia": 27, "agua_embalsada_hm3": 10}])

    result = prepare_water_reserve(data)

    assert result.iloc[0]["Mes_Dia"] == "June-27"


def test_water_reserve_summary_reports_latest_and_delta():
    data = prepare_water_reserve(
        pd.DataFrame(
            [
                {"Year": 2026, "Mes": "June", "Dia": 26, "agua_embalsada_hm3": "10", "porcentaje_embalsado": "50"},
                {"Year": 2026, "Mes": "June", "Dia": 27, "agua_embalsada_hm3": "12", "porcentaje_embalsado": "55"},
            ]
        )
    )

    summary = water_reserve_summary(data)

    assert summary["last_hm3"] == 12
    assert summary["hm3_change"] == 2
    assert summary["percent_change"] == 5


def test_satellite_state_style_maps_known_states():
    assert satellite_state_style("active") == "background-color: green"
    assert satellite_state_style("inactive") == "background-color: grey"
    assert satellite_state_style("waiting") == "background-color: yellow"
    assert satellite_state_style("blocked") == "background-color: red"
    assert satellite_state_style("unknown") == ""


def test_satellite_state_counts_returns_state_totals():
    data = pd.DataFrame([{"state": "active"}, {"state": "active"}, {"state": "waiting"}])

    assert satellite_state_counts(data) == {"active": 2, "waiting": 1}


def test_log_helpers_count_filter_and_escape_html():
    lines = [
        "INFO <ok>\n",
        "ERROR failed\n",
        "WARNING maybe\n",
        "DEBUG details\n",
        "plain\n",
    ]

    assert count_log_levels(lines) == {"INFO": 1, "ERROR": 1, "WARNING": 1, "DEBUG": 1}
    assert filter_log_lines(lines, show_info=True, show_error=False, show_warning=False, show_debug=False) == [
        "INFO <ok>\n"
    ]
    assert "&lt;ok&gt;" in format_log_message(lines[0])


def test_text_file_helpers_return_default_and_write_content(tmp_path):
    path = tmp_path / "TODO.txt"

    assert read_text_file(path, default="") == ""

    write_text_file(path, "task")

    assert read_text_file(path) == "task"


def test_chart_builders_return_figures():
    historical_data = pd.DataFrame(
        [{"Hora": "10:00", "temp (C)": 21, "Dia": 27}]
    )
    monthly_data = pd.DataFrame(
        [{"Mes": "June", "temp_max": 30, "temp_min": 12, "temp_mean": 20}]
    )
    precip_data = pd.DataFrame(
        [{"Fecha": pd.Timestamp("2026-06-27"), "precipitacion_acumulada": 3, "precipitaciones_totales": 3}]
    )
    daily_data = pd.DataFrame(
        [{"Periodo": "2026-06-27", "temp_max": 30, "temp_min": 12, "temp_mean": 20, "precipitation_total": 3}]
    )
    forecast_data = pd.DataFrame(
        [{"horizonte": "Mañana", "temp_max": 20, "temp_min": 10, "rain_total": 1}]
    )
    accuracy_summary = pd.DataFrame(
        [{"horizonte": "Mañana", "mae_temp_max": 2, "mae_temp_min": 1, "mae_rain_total": 3}]
    )
    electricity_values = pd.Series({"solar": 10, "wind": 5})
    water_data = pd.DataFrame(
        [{"Mes_Dia": "June-27", "agua_embalsada_hm3": 10, "porcentaje_embalsado": 50}]
    )

    assert historical_temperature_chart(historical_data).data
    assert monthly_temperature_chart(monthly_data, 2026).data
    assert precipitation_statistics_chart(precip_data, "Fecha").data
    assert daily_weather_summary_chart(daily_data).data
    assert daily_precipitation_total_chart(daily_data).data
    assert forecast_temperature_chart(forecast_data).data
    assert forecast_temperature_accuracy_chart(accuracy_summary).data
    assert forecast_rain_accuracy_chart(accuracy_summary).data
    assert electricity_mix_chart(electricity_values).data
    assert water_reserve_chart(water_data).data
    assert temperature_humidity_scatter_chart(
        pd.DataFrame([{"Hora": "10:00", "temp (C)": 20, "hum(%)": 60, "wind_speed(m/s)": 3, "Periodo": "2026-06-27"}])
    ).data


def test_temperature_humidity_scatter_ignores_nan_marker_sizes():
    data = pd.DataFrame(
        [
            {"Hora": "10:00", "temp (C)": 20, "hum(%)": 60, "wind_speed(m/s)": float("nan"), "Periodo": "2026-06-27"},
            {"Hora": "10:30", "temp (C)": 21, "hum(%)": 58, "wind_speed(m/s)": 3, "Periodo": "2026-06-27"},
        ]
    )

    fig = temperature_humidity_scatter_chart(data)

    assert fig.data
    assert all(trace.marker.size is None for trace in fig.data)


def test_temperature_max_min_charts_use_consistent_colors():
    daily_data = pd.DataFrame(
        [{"Periodo": "2026-06-27", "temp_max": 30, "temp_min": 12, "temp_mean": 20}]
    )
    stats_data = pd.DataFrame(
        [{"Fecha": pd.Timestamp("2026-06-27"), "temp_max": 30, "temp_min": 12, "temp_mean": 20}]
    )
    monthly_data = pd.DataFrame(
        [{"Mes": "June", "temp_max": 30, "temp_min": 12, "temp_mean": 20}]
    )
    forecast_data = pd.DataFrame(
        [{"horizonte": "Mañana", "temp_max": 20, "temp_min": 10}]
    )

    figures = [
        daily_weather_summary_chart(daily_data),
        temperature_statistics_chart(stats_data, "Fecha"),
        monthly_temperature_chart(monthly_data, 2026),
        forecast_temperature_chart(forecast_data),
    ]

    for fig in figures:
        max_trace = next(trace for trace in fig.data if trace.name in ("Temp max", "Temperatura Máxima", "Max Temp"))
        min_trace = next(trace for trace in fig.data if trace.name in ("Temp min", "Temperatura Mínima", "Min Temp"))
        assert max_trace.marker.color == TEMP_MAX_COLOR
        assert min_trace.marker.color == TEMP_MIN_COLOR
