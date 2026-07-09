import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import SEASON_PREDICTION_DIR
from Visualizer.season_predictions_utils import (
    MONTH_NAMES,
    available_months,
    available_years,
    build_legend_html,
    build_month_calendar_html,
    prepare_season_predictions,
)
from Visualizer.dashboard_data import load_csv_file


st.set_page_config(page_title="Season Predictions", layout="wide")
st.title("Season predictions")


@st.cache_data
def load_season_predictions():
    return load_csv_file(SEASON_PREDICTION_DIR, "Season_prediction.csv")


def show_unavailable_message(message):
    st.warning(message)
    st.stop()


try:
    data = load_season_predictions()
except ValueError as exc:
    show_unavailable_message(str(exc))

if data.empty:
    show_unavailable_message("Season_prediction.csv no contiene datos.")

try:
    data = prepare_season_predictions(data)
except ValueError as exc:
    show_unavailable_message(str(exc))

if data.empty:
    show_unavailable_message("No hay fechas validas disponibles en Season_prediction.csv.")

years = available_years(data)
selected_year = st.sidebar.selectbox("Seleccionar Año", years, index=len(years) - 1)

months = available_months(data, selected_year)
selected_month = st.sidebar.selectbox(
    "Seleccionar Mes",
    months,
    index=len(months) - 1,
    format_func=lambda month: MONTH_NAMES.get(month, str(month)),
)

st.subheader(f"{MONTH_NAMES.get(selected_month, selected_month)} {selected_year}")

st.markdown(
    """
    <style>
    .season-calendar {
        display: grid;
        grid-template-columns: repeat(7, minmax(42px, 1fr));
        gap: 6px;
        width: 100%;
    }
    .season-weekday {
        color: #475467;
        font-size: 0.85rem;
        font-weight: 700;
        text-align: center;
        padding: 0.25rem 0;
    }
    .season-day {
        border: 1px solid #d0d5dd;
        border-radius: 8px;
        min-height: 96px;
        overflow: hidden;
        position: relative;
        background: #f2f4f7;
    }
    .season-day-empty {
        border-color: transparent;
        background: transparent;
    }
    .season-day-number {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(16, 24, 40, 0.18);
        border-radius: 999px;
        color: #101828;
        font-size: 0.78rem;
        font-weight: 800;
        left: 6px;
        line-height: 1;
        min-width: 1.55rem;
        padding: 0.25rem 0.35rem;
        position: absolute;
        text-align: center;
        top: 6px;
        z-index: 2;
    }
    .season-half {
        align-items: center;
        color: #ffffff;
        display: flex;
        font-size: 0.8rem;
        font-weight: 700;
        height: 50%;
        justify-content: center;
        overflow: hidden;
        padding: 0 0.25rem;
        text-align: center;
        text-shadow: 0 1px 2px rgba(16, 24, 40, 0.4);
        white-space: nowrap;
    }
    .season-real {
        padding-top: 1.75rem;
    }
    .season-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.85rem;
        margin: 0.75rem 0 1rem;
    }
    .season-legend-item {
        align-items: center;
        color: #344054;
        display: flex;
        font-size: 0.9rem;
        gap: 0.35rem;
    }
    .season-legend-item span {
        border: 1px solid rgba(16, 24, 40, 0.18);
        border-radius: 4px;
        display: inline-block;
        height: 0.9rem;
        width: 0.9rem;
    }
    @media (max-width: 700px) {
        .season-calendar {
            gap: 3px;
            grid-template-columns: repeat(7, minmax(38px, 1fr));
        }
        .season-day {
            min-height: 74px;
        }
        .season-half {
            font-size: 0;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(build_legend_html(), unsafe_allow_html=True)
st.markdown(build_month_calendar_html(data, selected_year, selected_month), unsafe_allow_html=True)
