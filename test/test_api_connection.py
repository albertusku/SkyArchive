from datetime import datetime

import pytest
import requests

import API.API_connection as api_connection


class DummyConnection(api_connection.APIConnection):
    def get_current_data(self, params):
        return {}


class FakeLogger:
    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


def test_request_data_from_api_returns_json_and_writes_file(monkeypatch, tmp_path):
    calls = []
    payload = {"ok": True}

    class FakeResponse:
        url = "https://example.test/data?apikey=secret&zone=ES"

        def raise_for_status(self):
            pass

        def json(self):
            return payload

    def fake_get(url, params=None, headers=None):
        calls.append({"url": url, "params": params, "headers": headers})
        return FakeResponse()

    monkeypatch.setattr(api_connection.requests, "get", fake_get)

    output_file = tmp_path / "response.json"
    data = DummyConnection().request_data_from_api(
        "https://example.test/data",
        params={"zone": "ES"},
        headers={"auth-token": "token"},
        file_json=str(output_file),
    )

    assert data == payload
    assert output_file.read_text() == '{\n    "ok": true\n}'
    assert calls == [
        {
            "url": "https://example.test/data",
            "params": {"zone": "ES"},
            "headers": {"auth-token": "token"},
        }
    ]


def test_request_data_from_api_retries_then_returns_failed_response(monkeypatch, tmp_path):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        raise requests.exceptions.RequestException("network down")

    monkeypatch.setattr(api_connection.requests, "get", fake_get)
    monkeypatch.setattr(api_connection.time, "sleep", lambda seconds: None)

    data = DummyConnection().request_data_from_api(
        "https://example.test", file_json=str(tmp_path / "response.json")
    )

    assert data == api_connection.FAILED_RESPONSE
    assert len(calls) == 2


@pytest.mark.parametrize("key", ["apikey", "api_key", "appid", "auth-token", "token"])
def test_sanitize_url_hides_sensitive_query_values(key):
    url = f"https://example.test/data?{key}=secret&zone=ES"

    sanitized = DummyConnection().sanitize_url(url)

    assert "secret" not in sanitized
    assert f"{key}=%2A%2A%2A" in sanitized or f"{key}=***" in sanitized
    assert "zone=ES" in sanitized


def test_tomorrow_current_response_is_mapped_to_storage_columns(monkeypatch):
    api_payload = {
        "data": {
            "timelines": [
                {
                    "intervals": [
                        {
                            "values": {
                                "precipitationIntensity": 1.5,
                                "temperature": 21.2,
                                "humidity": 64,
                                "windSpeed": 3.4,
                                "visibility": 10000,
                                "cloudCover": 40,
                                "pressureSurfaceLevel": 1012,
                                "windDirection": 180,
                            }
                        }
                    ]
                }
            ]
        }
    }
    monkeypatch.setattr(
        api_connection.APIConnection,
        "request_data_from_api",
        lambda *_, **__: api_payload,
    )

    data = api_connection.TomorrowAPIConnection(FakeLogger()).get_current_data(
        {"api_key": "secret", "latitude": 42.0, "longitude": -4.5}
    )

    assert data == {
        "temp (C)": 21.2,
        "precipitation (mm/h)": 1.5,
        "wind_direction(º)": 180,
        "wind_speed(m/s)": 3.4,
        "hum(%)": 64,
        "pres(hPa)": 1012,
        "clouds(%)": 40,
        "visibility(m)": 10000,
    }


def test_forecast_outside_midnight_returns_failed_response(monkeypatch):
    monkeypatch.setattr(api_connection, "now", datetime(2026, 6, 12, 1, 30))

    data = api_connection.TomorrowForecastAPIConnection(FakeLogger()).get_current_data(
        {"api_key": "secret", "latitude": 42.0, "longitude": -4.5}
    )

    assert data == api_connection.FAILED_RESPONSE


def test_forecast_at_midnight_maps_daily_values(monkeypatch):
    monkeypatch.setattr(api_connection, "now", datetime(2026, 6, 12, 0, 0))
    daily = [
        {"values": {"temperatureMax": i, "temperatureMin": -i, "rainAccumulationSum": i / 10}}
        for i in range(6)
    ]
    monkeypatch.setattr(
        api_connection.APIConnection,
        "request_data_from_api",
        lambda *_, **__: {"timelines": {"daily": daily}},
    )

    data = api_connection.TomorrowForecastAPIConnection(FakeLogger()).get_current_data(
        {"api_key": "secret", "latitude": 42.0, "longitude": -4.5}
    )

    assert data["Fecha Actual"] == "2026-06-12"
    assert data["Tmax mañana"] == 1
    assert data["Tmin 3_dias"] == -3
    assert data["Rain acum. 5_dias"] == 0.5


def test_electricity_valid_response_is_filtered(monkeypatch):
    api_payload = {
        "powerConsumptionBreakdown": {"gas": 1},
        "powerProductionBreakdown": {"solar": 2},
        "extra": "ignored",
    }
    monkeypatch.setattr(
        api_connection.APIConnection,
        "request_data_from_api",
        lambda *_, **__: api_payload,
    )

    data = api_connection.ElectricityAPIConnection(FakeLogger()).get_current_data(
        {"auth-token": "fake-token"}
    )

    assert data == {"consumption": {"gas": 1}, "production": {"solar": 2}}


def test_electricity_invalid_response_returns_failed_response(monkeypatch):
    monkeypatch.setattr(
        api_connection.APIConnection,
        "request_data_from_api",
        lambda *_, **__: {"cero": 0},
    )

    data = api_connection.ElectricityAPIConnection(FakeLogger()).get_current_data(
        {"auth-token": "fake-token"}
    )

    assert data == api_connection.FAILED_RESPONSE


def test_water_reserve_outside_schedule_returns_failed_response(monkeypatch):
    monkeypatch.setattr(api_connection, "day_name", "Monday")
    monkeypatch.setattr(api_connection, "hour", 16)
    monkeypatch.setattr(api_connection, "minute", 0)

    data = api_connection.WaterReserveAPIConnection(FakeLogger()).get_current_data(
        {"auth-token": "fake-token"}
    )

    assert data == api_connection.FAILED_RESPONSE


def test_water_reserve_on_schedule_queries_configured_url_and_maps_data(monkeypatch):
    calls = []
    api_payload = {
        "embalses": {
            "provincia": "Palencia",
            "fecha_dato": "09/07/2026",
            "valores": {
                "agua_embalsada_hm3": "12",
                "porcentaje_embalsado": "34",
            }
        }
    }

    monkeypatch.setattr(api_connection, "day_name", "Tuesday")
    monkeypatch.setattr(api_connection, "hour", 16)
    monkeypatch.setattr(api_connection, "minute", 0)
    monkeypatch.setattr(
        api_connection,
        "obtener_datos",
        lambda url: calls.append(url) or api_payload,
    )

    data = api_connection.WaterReserveAPIConnection(FakeLogger()).get_current_data(
        {"url": "https://www.embalses.net/provincia-3-palencia.html"}
    )

    assert data == {
        "agua_embalsada_hm3": "12",
        "porcentaje_embalsado": "34",
        "provincia": "Palencia",
        "fecha_dato": "09/07/2026",
    }
    assert calls == ["https://www.embalses.net/provincia-3-palencia.html"]


def test_water_reserve_on_schedule_uses_legacy_url_when_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(api_connection, "day_name", "Tuesday")
    monkeypatch.setattr(api_connection, "hour", 16)
    monkeypatch.setattr(api_connection, "minute", 0)
    monkeypatch.setattr(
        api_connection,
        "obtener_datos",
        lambda url: calls.append(url)
        or {"embalses": {"valores": {"agua_embalsada_hm3": "12", "porcentaje_embalsado": "34"}}},
    )

    data = api_connection.WaterReserveAPIConnection(FakeLogger()).get_current_data({})

    assert data == {"agua_embalsada_hm3": "12", "porcentaje_embalsado": "34"}
    assert calls == [api_connection.water_reserve_url]


@pytest.mark.parametrize(
    "payload",
    [
        {"error": "No se encontraron datos"},
        {"embalses": {}},
        {"unexpected": True},
        None,
    ],
)
def test_water_reserve_invalid_payload_returns_failed_response(monkeypatch, payload):
    monkeypatch.setattr(api_connection, "day_name", "Tuesday")
    monkeypatch.setattr(api_connection, "hour", 16)
    monkeypatch.setattr(api_connection, "minute", 0)
    monkeypatch.setattr(api_connection, "obtener_datos", lambda url: payload)

    data = api_connection.WaterReserveAPIConnection(FakeLogger()).get_current_data(
        {"url": "https://www.embalses.net/provincia-3-palencia.html"}
    )

    assert data == api_connection.FAILED_RESPONSE


def test_get_data_from_api_aggregates_each_connection_and_isolates_failures(monkeypatch):
    received_params = {}

    class SuccessConnection(api_connection.APIConnection):
        name = "tomorrow_api"

        def __init__(self, logger):
            pass

        def get_current_data(self, params):
            received_params[self.name] = params
            return {"temp (C)": 20}

    class FailingConnection(api_connection.APIConnection):
        name = "electricity_api"

        def __init__(self, logger):
            pass

        def get_current_data(self, params):
            received_params[self.name] = params
            raise KeyError("powerConsumptionBreakdown")

    class EmptyForecastConnection(api_connection.APIConnection):
        name = "tomorrow_forecast_api"

        def __init__(self, logger):
            pass

        def get_current_data(self, params):
            received_params[self.name] = params
            return api_connection.FAILED_RESPONSE

    class EmptyWaterConnection(EmptyForecastConnection):
        name = "water_reserve_api"

    monkeypatch.setattr(api_connection, "TomorrowAPIConnection", SuccessConnection)
    monkeypatch.setattr(api_connection, "TomorrowForecastAPIConnection", EmptyForecastConnection)
    monkeypatch.setattr(api_connection, "ElectricityAPIConnection", FailingConnection)
    monkeypatch.setattr(api_connection, "WaterReserveAPIConnection", EmptyWaterConnection)

    params = {
        "tomorrow_api": {"api_key": "secret", "latitude": 42.0, "longitude": -4.5},
        "tomorrow_forecast_api": {"api_key": "forecast", "latitude": 42.0, "longitude": -4.5},
        "electricity_api": {"auth-token": "fake-token"},
        "water_reserve_api": {"auth-token": "water-token"},
    }

    data = api_connection.get_data_from_api(params)

    assert data == {
        "current_status": {"ok": True, "data": {"temp (C)": 20}},
        "forecast_status": {"ok": False, "data": api_connection.FAILED_RESPONSE},
        "electricity_status": {"ok": False, "data": api_connection.FAILED_RESPONSE},
        "water_reserve_status": {"ok": False, "data": api_connection.FAILED_RESPONSE},
    }
    assert received_params == params


def test_get_data_from_api_marks_missing_api_params_as_failed(monkeypatch):
    class SuccessConnection(api_connection.APIConnection):
        name = "tomorrow_api"

        def __init__(self, logger):
            pass

        def get_current_data(self, params):
            return {"temp (C)": 20}

    class EmptyConnection(api_connection.APIConnection):
        name = ""

        def __init__(self, logger):
            pass

        def get_current_data(self, params):
            return api_connection.FAILED_RESPONSE

    class EmptyForecastConnection(EmptyConnection):
        name = "tomorrow_forecast_api"

    class EmptyElectricityConnection(EmptyConnection):
        name = "electricity_api"

    class EmptyWaterConnection(EmptyConnection):
        name = "water_reserve_api"

    monkeypatch.setattr(api_connection, "TomorrowAPIConnection", SuccessConnection)
    monkeypatch.setattr(api_connection, "TomorrowForecastAPIConnection", EmptyForecastConnection)
    monkeypatch.setattr(api_connection, "ElectricityAPIConnection", EmptyElectricityConnection)
    monkeypatch.setattr(api_connection, "WaterReserveAPIConnection", EmptyWaterConnection)

    data = api_connection.get_data_from_api(
        {"tomorrow_api": {"api_key": "secret", "latitude": 42.0, "longitude": -4.5}}
    )

    assert data["current_status"] == {"ok": True, "data": {"temp (C)": 20}}
    assert data["forecast_status"] == {"ok": False, "data": api_connection.FAILED_RESPONSE}
    assert data["electricity_status"] == {"ok": False, "data": api_connection.FAILED_RESPONSE}
    assert data["water_reserve_status"] == {"ok": False, "data": api_connection.FAILED_RESPONSE}


def test_get_data_from_api_skips_disabled_apis(monkeypatch):
    calls = []

    class CurrentConnection(api_connection.APIConnection):
        name = "tomorrow_api"

        def __init__(self, logger):
            pass

        def get_current_data(self, params):
            calls.append(self.name)
            return {"temp (C)": 20}

    class DisabledConnection(CurrentConnection):
        def get_current_data(self, params):
            calls.append(self.name)
            return {"unexpected": True}

    class ForecastConnection(DisabledConnection):
        name = "tomorrow_forecast_api"

    class ElectricityConnection(DisabledConnection):
        name = "electricity_api"

    class WaterConnection(DisabledConnection):
        name = "water_reserve_api"

    monkeypatch.setattr(api_connection, "TomorrowAPIConnection", CurrentConnection)
    monkeypatch.setattr(api_connection, "TomorrowForecastAPIConnection", ForecastConnection)
    monkeypatch.setattr(api_connection, "ElectricityAPIConnection", ElectricityConnection)
    monkeypatch.setattr(api_connection, "WaterReserveAPIConnection", WaterConnection)

    data = api_connection.get_data_from_api(
        {
            "tomorrow_api": {"enabled": True, "api_key": "secret", "latitude": 42.0, "longitude": -4.5},
            "tomorrow_forecast_api": {"enabled": False},
            "electricity_api": {"enabled": False},
            "water_reserve_api": {"enabled": False},
        }
    )

    assert calls == ["tomorrow_api"]
    assert data == {
        "current_status": {"ok": True, "data": {"temp (C)": 20}},
        "forecast_status": {"ok": False, "data": api_connection.FAILED_RESPONSE},
        "electricity_status": {"ok": False, "data": api_connection.FAILED_RESPONSE},
        "water_reserve_status": {"ok": False, "data": api_connection.FAILED_RESPONSE},
    }
