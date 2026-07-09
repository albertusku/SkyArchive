import calendar
from html import escape

import pandas as pd


MONTH_MAPPING = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

MONTH_NAMES = {value: key for key, value in MONTH_MAPPING.items()}

SEASON_COLORS = {
    "Winter": "#2f80ed",
    "Spring": "#27ae60",
    "Summer": "#d64545",
    "Autumn": "#c49a6c",
}

UNKNOWN_SEASON_COLOR = "#d9dde3"


def normalize_month(value):
    if pd.isna(value):
        return pd.NA

    if isinstance(value, str):
        cleaned_value = value.strip()
        if cleaned_value in MONTH_MAPPING:
            return MONTH_MAPPING[cleaned_value]
        if cleaned_value.isdigit():
            return int(cleaned_value)
        return pd.NA

    try:
        return int(value)
    except (TypeError, ValueError):
        return pd.NA


def season_color(season):
    if pd.isna(season):
        return UNKNOWN_SEASON_COLOR
    return SEASON_COLORS.get(str(season).strip(), UNKNOWN_SEASON_COLOR)


def prepare_season_predictions(data):
    required_columns = {"Year", "Mes", "Dia", "real_season", "prediction"}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    prepared_data = data.copy()
    prepared_data["Year"] = pd.to_numeric(prepared_data["Year"], errors="coerce").astype("Int64")
    prepared_data["Dia"] = pd.to_numeric(prepared_data["Dia"], errors="coerce").astype("Int64")
    prepared_data["Mes_Num"] = prepared_data["Mes"].apply(normalize_month).astype("Int64")

    prepared_data = prepared_data.dropna(subset=["Year", "Mes_Num", "Dia"])
    prepared_data = prepared_data[
        prepared_data["Mes_Num"].between(1, 12) & prepared_data["Dia"].between(1, 31)
    ].copy()

    if prepared_data.empty:
        prepared_data["Fecha"] = pd.Series(dtype="datetime64[ns]")
        return prepared_data

    prepared_data["Fecha"] = pd.to_datetime(
        {
            "year": prepared_data["Year"].astype(int),
            "month": prepared_data["Mes_Num"].astype(int),
            "day": prepared_data["Dia"].astype(int),
        },
        errors="coerce",
    )
    prepared_data = prepared_data.dropna(subset=["Fecha"])

    prepared_data = prepared_data.drop_duplicates(
        subset=["Year", "Mes_Num", "Dia"],
        keep="last",
    )
    return prepared_data.sort_values("Fecha").reset_index(drop=True)


def available_years(data):
    return sorted(data["Year"].dropna().astype(int).unique())


def available_months(data, year):
    months = data.loc[data["Year"].astype(int) == int(year), "Mes_Num"].dropna().astype(int).unique()
    return sorted(months)


def filter_month(data, year, month):
    return data[
        (data["Year"].astype(int) == int(year))
        & (data["Mes_Num"].astype(int) == int(month))
    ].copy()


def build_month_calendar_html(data, year, month):
    month_data = filter_month(data, year, month)
    rows_by_day = {
        int(row["Dia"]): row
        for _, row in month_data.iterrows()
    }

    weeks = calendar.monthcalendar(int(year), int(month))
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cells = []

    for day_name in weekday_names:
        cells.append(f'<div class="season-weekday">{day_name}</div>')

    for week in weeks:
        for day in week:
            if day == 0:
                cells.append('<div class="season-day season-day-empty"></div>')
                continue

            row = rows_by_day.get(day)
            real_season = row["real_season"] if row is not None else pd.NA
            predicted_season = row["prediction"] if row is not None else pd.NA
            real_label = "" if pd.isna(real_season) else escape(str(real_season))
            prediction_label = "" if pd.isna(predicted_season) else escape(str(predicted_season))

            cells.append(
                "\n".join(
                    [
                        '<div class="season-day">',
                        f'  <div class="season-day-number">{day}</div>',
                        (
                            '  <div class="season-half season-real" '
                            f'style="background:{season_color(real_season)}">{real_label}</div>'
                        ),
                        (
                            '  <div class="season-half season-prediction" '
                            f'style="background:{season_color(predicted_season)}">{prediction_label}</div>'
                        ),
                        "</div>",
                    ]
                )
            )

    return '<div class="season-calendar">' + "\n".join(cells) + "</div>"


def build_legend_html():
    legend_items = [
        *SEASON_COLORS.items(),
        ("Unknown", UNKNOWN_SEASON_COLOR),
    ]
    items_html = "\n".join(
        (
            '<div class="season-legend-item">'
            f'<span style="background:{color}"></span>{escape(label)}'
            "</div>"
        )
        for label, color in legend_items
    )
    return f'<div class="season-legend">{items_html}</div>'
