import json

import pandas as pd
import pytest

import Data_storage.storage_builder as storage_builder


def test_create_storage_calls_all_blocks_and_survives_partial_failure(monkeypatch):
    calls = []

    def fail_current(data):
        calls.append("current")
        raise RuntimeError("disk error")

    monkeypatch.setattr(storage_builder, "create_storage_dataframe", fail_current)
    monkeypatch.setattr(storage_builder, "create_storage_forecast", lambda data: calls.append("forecast"))
    monkeypatch.setattr(storage_builder, "create_storage_electricity", lambda data: calls.append("electricity"))
    monkeypatch.setattr(storage_builder, "create_storage_water", lambda data: calls.append("water"))
    monkeypatch.setattr(storage_builder, "create_BK", lambda: calls.append("backup"))
    monkeypatch.setattr(storage_builder, "hour", 12)
    monkeypatch.setattr(storage_builder, "minute", 0)

    storage_builder.create_storage(
        {
            "current_status": {"ok": True, "data": {"temp (C)": 20}},
            "forecast_status": {"ok": False, "data": None},
            "electricity_status": {"ok": False, "data": None},
            "water_reserve_status": {"ok": False, "data": None},
        }
    )

    assert calls == ["current", "forecast", "electricity", "water", "backup"]


def test_failed_forecast_electricity_and_water_are_not_written(monkeypatch):
    writes = []
    monkeypatch.setattr(storage_builder, "save_csv", lambda df, path: writes.append((df, path)))

    failed_response = {"ok": False, "data": None}

    storage_builder.create_storage_forecast(failed_response)
    storage_builder.create_storage_electricity(failed_response)
    storage_builder.create_storage_water(failed_response)

    assert writes == []


def test_read_json_builds_expected_params(monkeypatch, tmp_path):
    config_file = tmp_path / "data.json"
    config_file.write_text(
        json.dumps(
            {
                "station": {
                    "name": "test-station",
                    "latitude": 1,
                    "longitude": 2,
                    "altitude": 750,
                },
                "apis": {
                    "tomorrow_api": {"api_key": "tomorrow"},
                    "electricity_api": {"auth-token": "electricity"},
                    "tomorrow_forecast_api": {"api_key": "forecast"},
                    "water_reserve_api": {
                        "auth-token": "water",
                        "url": "https://www.embalses.net/provincia-3-palencia.html",
                    },
                },
                "extra_config": {},
            }
        )
    )
    monkeypatch.setattr(storage_builder, "CONFIG_DATA", str(config_file))

    params = storage_builder.read_json()

    assert params["tomorrow_api"] == {
        "enabled": True,
        "api_key": "tomorrow",
        "latitude": 1,
        "longitude": 2,
    }
    assert params["tomorrow_forecast_api"] == {
        "enabled": True,
        "api_key": "forecast",
        "latitude": 1,
        "longitude": 2,
    }
    assert params["electricity_api"] == {"enabled": True, "auth-token": "electricity"}
    assert params["water_reserve_api"] == {
        "enabled": True,
        "auth-token": "water",
        "url": "https://www.embalses.net/provincia-3-palencia.html",
    }


def test_read_json_uses_legacy_water_reserve_url_when_missing(monkeypatch, tmp_path):
    config_file = tmp_path / "data.json"
    config_file.write_text(
        json.dumps(
            {
                "station": {
                    "name": "test-station",
                    "latitude": 1,
                    "longitude": 2,
                    "altitude": 750,
                },
                "apis": {
                    "tomorrow_api": {"api_key": "tomorrow"},
                    "electricity_api": {"auth-token": "electricity"},
                    "tomorrow_forecast_api": {"api_key": "forecast"},
                    "water_reserve_api": {"auth-token": "water"},
                },
            }
        )
    )
    monkeypatch.setattr(storage_builder, "CONFIG_DATA", str(config_file))

    params = storage_builder.read_json()

    assert params["water_reserve_api"] == {
        "enabled": True,
        "auth-token": "water",
        "url": storage_builder.water_reserve_url,
    }


def test_read_json_allows_disabled_apis_without_credentials(monkeypatch, tmp_path):
    config_file = tmp_path / "data.json"
    config_file.write_text(
        json.dumps(
            {
                "station": {
                    "name": "test-station",
                    "latitude": 1,
                    "longitude": 2,
                    "altitude": 750,
                },
                "apis": {
                    "tomorrow_api": {"enabled": False},
                    "electricity_api": {"enabled": False},
                    "tomorrow_forecast_api": {"enabled": False},
                    "water_reserve_api": {"enabled": False},
                },
            }
        )
    )
    monkeypatch.setattr(storage_builder, "CONFIG_DATA", str(config_file))

    params = storage_builder.read_json()

    assert params["tomorrow_api"] == {"enabled": False, "latitude": 1, "longitude": 2}
    assert params["tomorrow_forecast_api"] == {"enabled": False, "latitude": 1, "longitude": 2}
    assert params["electricity_api"] == {"enabled": False}
    assert params["water_reserve_api"] == {"enabled": False}


def test_read_json_reports_missing_and_invalid_files(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_builder, "CONFIG_DATA", str(tmp_path / "missing.json"))
    with pytest.raises(RuntimeError, match="Archivo de configuración no encontrado"):
        storage_builder.read_json()

    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid")
    monkeypatch.setattr(storage_builder, "CONFIG_DATA", str(invalid_file))
    with pytest.raises(RuntimeError, match="Archivo de configuración JSON inválido"):
        storage_builder.read_json()


def test_save_csv_appends_rows_and_returns_file_contents(tmp_path):
    csv_file = tmp_path / "weather.csv"
    csv_file.write_text("Year,Mes,Dia,Hora,temp (C)\n2026,June,12,11:30,20.0\n")
    df = pd.DataFrame(
        [
            {"Year": 2026, "Mes": "June", "Dia": 12, "Hora": "12:00", "temp (C)": 20.5},
            {"Year": 2026, "Mes": "June", "Dia": 12, "Hora": "12:30", "temp (C)": 21.0},
        ]
    )

    result = storage_builder.save_csv(df, str(csv_file))

    assert list(result["Hora"]) == ["11:30", "12:00", "12:30"]
    assert list(result["temp (C)"]) == [20.0, 20.5, 21.0]
    assert csv_file.read_text().count("Year,Mes,Dia,Hora,temp (C)") == 1


def test_save_csv_creates_missing_file_with_header_and_keeps_all_rows(tmp_path):
    csv_file = tmp_path / "new_weather.csv"
    first_df = pd.DataFrame(
        [{"Year": 2026, "Mes": "June", "Dia": 12, "Hora": "12:00", "temp (C)": 20.5}]
    )
    second_df = pd.DataFrame(
        [{"Year": 2026, "Mes": "June", "Dia": 12, "Hora": "12:30", "temp (C)": 21.0}]
    )

    first_result = storage_builder.save_csv(first_df, str(csv_file))
    second_result = storage_builder.save_csv(second_df, str(csv_file))

    assert list(first_result.columns) == ["Year", "Mes", "Dia", "Hora", "temp (C)"]
    assert list(second_result["Hora"]) == ["12:00", "12:30"]
    assert list(second_result["temp (C)"]) == [20.5, 21.0]
    assert csv_file.read_text().count("Year,Mes,Dia,Hora,temp (C)") == 1
    assert "2026,June,12,12:00,20.5" in csv_file.read_text()
    assert "2026,June,12,12:30,21.0" in csv_file.read_text()


def test_create_storage_water_adds_optional_columns_to_existing_csv(monkeypatch, tmp_path):
    csv_file = tmp_path / "Water_reserve.csv"
    csv_file.write_text("Year,Mes,Dia,agua_embalsada_hm3,porcentaje_embalsado\n2026,June,1,10,50\n")
    monkeypatch.setattr(storage_builder, "WATER_RESERVE", str(csv_file))

    storage_builder.create_storage_water(
        {
            "ok": True,
            "data": {
                "agua_embalsada_hm3": "12",
                "porcentaje_embalsado": "55",
                "provincia": "Palencia",
                "fecha_dato": "09/07/2026",
            },
        }
    )

    result = pd.read_csv(csv_file)

    assert list(result.columns) == [
        "Year",
        "Mes",
        "Dia",
        "agua_embalsada_hm3",
        "porcentaje_embalsado",
        "provincia",
        "fecha_dato",
    ]
    assert pd.isna(result.loc[0, "provincia"])
    assert result.loc[1, "provincia"] == "Palencia"
    assert result.loc[1, "fecha_dato"] == "09/07/2026"


def test_create_bk_does_nothing_when_backup_is_disabled(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    (storage_dir / "Historical_weather.csv").write_text("data")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    copied = []

    monkeypatch.setattr(storage_builder, "DATA_DIR", str(storage_dir))
    monkeypatch.setattr(
        storage_builder,
        "get_extra_config",
        lambda: {"backup": {"enabled": False, "path": str(backup_dir)}},
    )
    monkeypatch.setattr(storage_builder.shutil, "copy2", lambda source, target: copied.append((source, target)))

    storage_builder.create_BK()

    assert copied == []
    assert not (backup_dir / "Historical_weather.csv").exists()


def test_create_bk_copies_storage_files_to_configured_path(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    source_file = storage_dir / "Historical_weather.csv"
    source_file.write_text("data")
    backup_dir = tmp_path / "backup with spaces"
    backup_dir.mkdir()

    monkeypatch.setattr(storage_builder, "DATA_DIR", str(storage_dir))
    monkeypatch.setattr(
        storage_builder,
        "get_extra_config",
        lambda: {"backup": {"enabled": True, "path": str(backup_dir)}},
    )

    storage_builder.create_BK()

    assert (backup_dir / "Historical_weather.csv").read_text() == "data"


def test_create_bk_skips_copy_when_configured_path_does_not_exist(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    (storage_dir / "Historical_weather.csv").write_text("data")
    missing_backup_dir = tmp_path / "missing"
    copied = []

    monkeypatch.setattr(storage_builder, "DATA_DIR", str(storage_dir))
    monkeypatch.setattr(
        storage_builder,
        "get_extra_config",
        lambda: {"backup": {"enabled": True, "path": str(missing_backup_dir)}},
    )
    monkeypatch.setattr(storage_builder.shutil, "copy2", lambda source, target: copied.append((source, target)))

    storage_builder.create_BK()

    assert copied == []


def test_save_sdr_files_moves_files_inside_configured_backup_path(monkeypatch, tmp_path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    wav_file = tmp_path / "audio.wav"
    png_file = tmp_path / "image.png"
    wav_file.write_text("wav")
    png_file.write_text("png")

    monkeypatch.setattr(
        storage_builder,
        "get_extra_config",
        lambda: {"backup": {"enabled": True, "path": str(backup_dir)}},
    )
    monkeypatch.setattr(storage_builder, "year", 2026)
    monkeypatch.setattr(storage_builder, "current_month", 7)
    monkeypatch.setattr(storage_builder, "current_day", 5)

    storage_builder.save_SDR_files(str(wav_file), str(png_file), "NOAA_18")

    target_dir = backup_dir / "NOAA_18" / "2026" / "7" / "5"
    assert (target_dir / "audio.wav").read_text() == "wav"
    assert (target_dir / "image.png").read_text() == "png"
    assert not wav_file.exists()
    assert not png_file.exists()


def test_save_sdr_files_returns_when_backup_subdirectory_cannot_be_created(monkeypatch, tmp_path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    wav_file = tmp_path / "audio.wav"
    png_file = tmp_path / "image.png"
    wav_file.write_text("wav")
    png_file.write_text("png")

    monkeypatch.setattr(
        storage_builder,
        "get_extra_config",
        lambda: {"backup": {"enabled": True, "path": str(backup_dir)}},
    )
    monkeypatch.setattr(storage_builder.Path, "mkdir", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("denied")))

    storage_builder.save_SDR_files(str(wav_file), str(png_file), "NOAA_18")

    assert wav_file.read_text() == "wav"
    assert png_file.read_text() == "png"
