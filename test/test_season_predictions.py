import pandas as pd

from Visualizer.season_predictions_utils import (
    UNKNOWN_SEASON_COLOR,
    available_months,
    build_month_calendar_html,
    filter_month,
    normalize_month,
    prepare_season_predictions,
    season_color,
)


def test_normalize_month_accepts_english_names_and_numbers():
    assert normalize_month("June") == 6
    assert normalize_month(" 6 ") == 6
    assert normalize_month(6) == 6


def test_prepare_season_predictions_builds_dates_and_keeps_last_duplicate():
    data = pd.DataFrame(
        [
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 27,
                "real_season": "Spring",
                "prediction": "Summer",
            },
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 27,
                "real_season": "Summer",
                "prediction": "Autumn",
            },
            {
                "Year": 2026,
                "Mes": "June",
                "Dia": 28,
                "real_season": "Summer",
                "prediction": "Summer",
            },
        ]
    )

    result = prepare_season_predictions(data)

    assert len(result) == 2
    assert result.iloc[0]["Fecha"] == pd.Timestamp("2026-06-27")
    assert result.iloc[0]["real_season"] == "Summer"
    assert result.iloc[0]["prediction"] == "Autumn"


def test_filter_month_uses_year_and_month():
    data = prepare_season_predictions(
        pd.DataFrame(
            [
                {"Year": 2026, "Mes": "June", "Dia": 27, "real_season": "Summer", "prediction": "Summer"},
                {"Year": 2026, "Mes": "July", "Dia": 1, "real_season": "Summer", "prediction": "Autumn"},
                {"Year": 2025, "Mes": "June", "Dia": 27, "real_season": "Spring", "prediction": "Summer"},
            ]
        )
    )

    result = filter_month(data, 2026, 6)

    assert len(result) == 1
    assert result.iloc[0]["Dia"] == 27
    assert available_months(data, 2026) == [6, 7]


def test_season_color_maps_known_values_and_unknown_to_gray():
    assert season_color("Winter") == "#2f80ed"
    assert season_color("Spring") == "#27ae60"
    assert season_color("Summer") == "#d64545"
    assert season_color("Autumn") == "#c49a6c"
    assert season_color("Other") == UNKNOWN_SEASON_COLOR
    assert season_color(pd.NA) == UNKNOWN_SEASON_COLOR


def test_build_month_calendar_html_renders_day_number_and_split_halves():
    data = prepare_season_predictions(
        pd.DataFrame(
            [
                {"Year": 2026, "Mes": "June", "Dia": 27, "real_season": "Summer", "prediction": "Autumn"},
            ]
        )
    )

    html = build_month_calendar_html(data, 2026, 6)

    assert '<div class="season-day-number">27</div>' in html
    assert "season-real" in html
    assert "season-prediction" in html
    assert "Summer" in html
    assert "Autumn" in html
