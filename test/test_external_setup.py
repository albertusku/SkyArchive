import json
from pathlib import Path


def test_data_example_json_has_minimum_expected_structure():
    repo_dir = Path(__file__).resolve().parents[1]
    example_path = repo_dir / "src" / "API" / "data.example.json"

    with example_path.open("r") as file:
        data = json.load(file)

    assert {"station", "apis", "extra_config"}.issubset(data)
    assert {"name", "latitude", "longitude", "altitude", "zone"}.issubset(data["station"])
    assert {
        "tomorrow_api",
        "tomorrow_forecast_api",
        "electricity_api",
        "water_reserve_api",
    }.issubset(data["apis"])

    for api_config in data["apis"].values():
        assert "enabled" in api_config

    assert data["apis"]["water_reserve_api"]["url"] == "https://www.embalses.net/provincia-3-palencia.html"
    assert {"enabled", "path"}.issubset(data["extra_config"]["backup"])
