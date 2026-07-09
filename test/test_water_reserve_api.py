import requests

import API.water_reserve_api as water_reserve_api


class FakeResponse:
    def __init__(self, content=b"", exc=None):
        self.content = content
        self.exc = exc

    def raise_for_status(self):
        if self.exc:
            raise self.exc


def test_obtener_datos_extracts_reservoir_values(monkeypatch):
    html = b"""
    <html>
      <head><title>Embalses de Palencia</title></head>
      <div class="Resultado"><strong>123 hm3</strong></div>
      <div class="Resultado"><strong>45%</strong></div>
      <p>Datos del 09/07/2026</p>
    </html>
    """
    monkeypatch.setattr(water_reserve_api.requests, "get", lambda *_, **__: FakeResponse(html))

    data = water_reserve_api.obtener_datos()

    assert data["embalses"]["provincia"] == "Palencia"
    assert data["embalses"]["fecha_dato"] == "09/07/2026"
    assert data["embalses"]["valores"]["agua_embalsada_hm3"] == "123"
    assert data["embalses"]["valores"]["porcentaje_embalsado"] == "45"


def test_parse_embalses_html_extracts_other_province_with_decimal_comma():
    html = b"""
    <html>
      <h1>Embalses de Leon</h1>
      <div class="Resultado"><strong>74,79 hm3</strong></div>
      <div class="Resultado"><strong>62,5 %</strong></div>
    </html>
    """

    data = water_reserve_api.parse_embalses_html(html)

    assert data["embalses"]["provincia"] == "Leon"
    assert data["embalses"]["valores"]["agua_embalsada_hm3"] == "74.79"
    assert data["embalses"]["valores"]["porcentaje_embalsado"] == "62.5"


def test_obtener_datos_returns_error_when_expected_divs_are_missing(monkeypatch):
    monkeypatch.setattr(water_reserve_api.requests, "get", lambda *_, **__: FakeResponse(b"<html></html>"))

    assert water_reserve_api.obtener_datos() == {"error": "No se encontraron datos"}


def test_obtener_datos_returns_error_on_http_failure(monkeypatch):
    monkeypatch.setattr(water_reserve_api.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        water_reserve_api.requests,
        "get",
        lambda *_, **__: FakeResponse(exc=requests.RequestException("down")),
    )

    assert water_reserve_api.obtener_datos() == {"error": "No se pudo acceder a la página de embalses."}


def test_parse_embalses_html_rejects_non_numeric_values():
    html = b"""
    <html>
      <div class="Resultado"><strong>sin dato</strong></div>
      <div class="Resultado"><strong>tampoco</strong></div>
    </html>
    """

    assert water_reserve_api.parse_embalses_html(html) == {"error": "Datos de embalses inválidos"}


def test_datos_endpoint_checks_api_key(monkeypatch):
    monkeypatch.setattr(water_reserve_api, "API_KEY", "valid-key")
    monkeypatch.setattr(water_reserve_api, "obtener_datos", lambda: {"embalses": {"valores": {"agua_embalsada_hm3": "1"}}})
    client = water_reserve_api.app.test_client()

    forbidden = client.get("/datos", headers={"X-API-KEY": "wrong"})
    ok = client.get("/datos", headers={"X-API-KEY": "valid-key"})

    assert forbidden.status_code == 403
    assert ok.status_code == 200
    assert ok.get_json()["embalses"]["valores"]["agua_embalsada_hm3"] == "1"
