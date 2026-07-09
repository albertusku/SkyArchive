import importlib
import sys
import types
from datetime import datetime, timedelta, timezone

import pandas as pd


def import_sdr_with_fake_skyfield(monkeypatch):
    fake_api = types.ModuleType("skyfield.api")
    fake_api.Topos = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    fake_api.load = types.SimpleNamespace(
        tle_file=lambda url: [],
        timescale=lambda: types.SimpleNamespace(utc=lambda *args: None),
    )
    fake_skyfield = types.ModuleType("skyfield")
    fake_skyfield.api = fake_api
    monkeypatch.setitem(sys.modules, "skyfield", fake_skyfield)
    monkeypatch.setitem(sys.modules, "skyfield.api", fake_api)
    sys.modules.pop("SDR.satellites_info", None)
    return importlib.import_module("SDR.satellites_info")


def test_satellite_transition_updates_valid_states_and_ignores_invalid_events(monkeypatch, tmp_path):
    sdr = import_sdr_with_fake_skyfield(monkeypatch)
    monkeypatch.setattr(sdr, "SATELLITE_OUTPUT", str(tmp_path / "satellite.txt"))
    monkeypatch.setattr(sdr, "SATELLITE_STATUS", str(tmp_path / "satellite.csv"))
    satellite = sdr.Satellite("NOAA 15", 137.62)

    satellite.transicion("Service_started")
    assert satellite.state == "waiting"

    satellite.transicion("invalid")
    assert satellite.state == "waiting"


def test_satellite_save_and_load_preserves_state_and_passes(monkeypatch, tmp_path):
    sdr = import_sdr_with_fake_skyfield(monkeypatch)
    path = tmp_path / "satellite.txt"
    satellite = sdr.Satellite("NOAA 18", 137.9125)
    satellite.state = "active"
    satellite.update_passes([sdr.Pass("aos", "max", "los")])

    satellite.save_to_file(str(path))
    loaded = sdr.Satellite.load_from_file(str(path))

    assert loaded.name == "NOAA_18"
    assert loaded.frequency == "137.9125"
    assert loaded.state == "active"
    assert loaded.service_name == "rtl_sdr@NOAA_18.service"
    assert [(p.aos, p.max, p.los) for p in loaded.passes] == [("aos", "max", "los")]


def test_save_to_csv_creates_and_updates_satellite_row(monkeypatch, tmp_path):
    sdr = import_sdr_with_fake_skyfield(monkeypatch)
    csv_file = tmp_path / "satellite_status.csv"
    satellite = sdr.Satellite("NOAA 19", 137.1)
    satellite.update_passes([sdr.Pass("soon", "max", "los")])
    satellite.save_to_csv(str(csv_file))

    satellite.state = "waiting"
    satellite.update_passes([sdr.Pass("later", "max", "los")])
    satellite.save_to_csv(str(csv_file))

    df = pd.read_csv(csv_file)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "NOAA_19"
    assert df.iloc[0]["status"] == "waiting"
    assert df.iloc[0]["next_pass"] == "later"


def test_check_conditions_returns_false_when_another_service_is_active(monkeypatch):
    sdr = import_sdr_with_fake_skyfield(monkeypatch)

    def fake_run(command, capture_output, text):
        service = command[-1]
        stdout = "Active: active (running)" if service == "rtl_sdr@NOAA_18.service" else "inactive"
        return types.SimpleNamespace(stdout=stdout)

    monkeypatch.setattr(sdr.subprocess, "run", fake_run)

    assert sdr.check_conditions("rtl_sdr@NOAA_15.service") is False


def test_passes_info_returns_only_future_passes_inside_interval(monkeypatch):
    sdr = import_sdr_with_fake_skyfield(monkeypatch)
    satellite = sdr.Satellite("NOAA 15", 137.62)
    local_now = datetime.now(timezone.utc) + timedelta(hours=1)
    satellite.update_passes(
        [
            sdr.Pass(local_now - timedelta(minutes=1), local_now, local_now),
            sdr.Pass(local_now + timedelta(minutes=30), local_now, local_now),
            sdr.Pass(local_now + timedelta(minutes=240), local_now, local_now),
        ]
    )

    result = sdr.passes_info([satellite], interval=180)

    assert len(result) == 1
    assert result[0][0] is satellite
