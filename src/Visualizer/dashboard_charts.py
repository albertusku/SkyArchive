import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from Visualizer.dashboard_data import MONTH_MAPPING, WEATHER_PERIOD_COLUMN, autopct_format


PLOT_TEMPLATE = "plotly_white"
TEMP_MAX_COLOR = "red"
TEMP_MIN_COLOR = "blue"
TEMP_MEAN_COLOR = "green"


def apply_common_layout(fig, title=None, height=360):
    layout = {
        "template": PLOT_TEMPLATE,
        "height": height,
        "margin": dict(l=20, r=20, t=55, b=35),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    }
    if title is not None:
        layout["title"] = title

    fig.update_layout(
        **layout,
    )
    return fig


def historical_temperature_chart(data):
    fig = px.line(
        data,
        x="Hora",
        y="temp (C)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in data.columns else "Dia",
        title="Comparación de Temperatura (°C) entre Días/Años",
        labels={"Hora": "Hora", "temp (C)": "Temperatura (°C)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Hora", yaxis_title="Temperatura (°C)")
    return apply_common_layout(fig)


def historical_precipitation_chart(data):
    fig = px.bar(
        data,
        x="Hora",
        y="precipitation (mm/h)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in data.columns else "Dia",
        title="Comparación de intensidad de precipitación (mm/h) entre Días/Años",
        labels={"Hora": "Hora", "precipitation (mm/h)": "Intensidad de precipitación (mm/h)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Hora", yaxis_title="Intensidad de precipitación (mm/h)")
    return apply_common_layout(fig)


def historical_wind_chart(data):
    fig = px.line(
        data,
        x="Hora",
        y="wind_speed(m/s)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in data.columns else "Dia",
        title="Comparación de Velocidad del Viento entre Días/Años",
        labels={"Hora": "Hora", "wind_speed(m/s)": "Viento (m/s)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Hora", yaxis_title="Viento (m/s)")
    return apply_common_layout(fig)


def historical_humidity_chart(data):
    fig = px.line(
        data,
        x="Hora",
        y="hum(%)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in data.columns else "Dia",
        title="Comparación de Humedad (%) entre Días/Años",
        labels={"Hora": "Hora", "hum(%)": "Humedad (%)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Hora", yaxis_title="Humedad (%)")
    return apply_common_layout(fig)


def historical_pressure_chart(data):
    fig = px.line(
        data,
        x="Hora",
        y="pres(hPa)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in data.columns else "Dia",
        title="Comparación de Presión (hPa) entre Días/Años",
        labels={"Hora": "Hora", "pres(hPa)": "Presión (hPa)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Hora", yaxis_title="Presión (hPa)")
    return apply_common_layout(fig)


def historical_cloud_chart(data):
    fig = px.line(
        data,
        x="Hora",
        y="clouds(%)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in data.columns else "Dia",
        title="Nubosidad (%) por hora",
        labels={"Hora": "Hora", "clouds(%)": "Nubosidad (%)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Hora", yaxis_title="Nubosidad (%)")
    return apply_common_layout(fig)


def temperature_humidity_scatter_chart(data):
    chart_data = data.copy()
    for column in ("temp (C)", "hum(%)"):
        chart_data[column] = pd.to_numeric(chart_data[column], errors="coerce")
    chart_data = chart_data[
        np.isfinite(chart_data["temp (C)"])
        & np.isfinite(chart_data["hum(%)"])
    ]

    size_column = None
    if "wind_speed(m/s)" in chart_data.columns:
        chart_data["wind_speed(m/s)"] = pd.to_numeric(chart_data["wind_speed(m/s)"], errors="coerce")
        chart_data.loc[chart_data["wind_speed(m/s)"] < 0, "wind_speed(m/s)"] = 0
        if np.isfinite(chart_data["wind_speed(m/s)"]).all():
            size_column = "wind_speed(m/s)"

    fig = px.scatter(
        chart_data,
        x="temp (C)",
        y="hum(%)",
        color=WEATHER_PERIOD_COLUMN if WEATHER_PERIOD_COLUMN in chart_data.columns else "Dia",
        size=size_column,
        hover_data=["Hora"] if "Hora" in chart_data.columns else None,
        title="Relación temperatura-humedad",
        labels={
            "temp (C)": "Temperatura (°C)",
            "hum(%)": "Humedad (%)",
            "wind_speed(m/s)": "Viento (m/s)",
            WEATHER_PERIOD_COLUMN: "Día",
            "Hora": "Hora",
        },
    )
    fig.update_layout(xaxis_title="Temperatura (°C)", yaxis_title="Humedad (%)")
    return apply_common_layout(fig)


def daily_weather_summary_chart(data):
    if data.empty:
        return apply_common_layout(go.Figure(), "Resumen diario")

    fig = go.Figure()
    if "temp_max" in data:
        fig.add_trace(
            go.Bar(
                x=data[WEATHER_PERIOD_COLUMN],
                y=data["temp_max"],
                name="Temp max",
                marker_color=TEMP_MAX_COLOR,
            )
        )
    if "temp_min" in data:
        fig.add_trace(
            go.Bar(
                x=data[WEATHER_PERIOD_COLUMN],
                y=data["temp_min"],
                name="Temp min",
                marker_color=TEMP_MIN_COLOR,
            )
        )
    if "temp_mean" in data:
        fig.add_trace(
            go.Scatter(
                x=data[WEATHER_PERIOD_COLUMN],
                y=data["temp_mean"],
                mode="lines+markers",
                name="Temp media",
                line=dict(color=TEMP_MEAN_COLOR),
            )
        )
    fig.update_layout(yaxis_title="Temperatura (°C)", barmode="group")
    fig.update_xaxes(title_text="Día")
    return apply_common_layout(fig, "Resumen térmico por día")


def daily_precipitation_total_chart(data):
    fig = px.bar(
        data,
        x=WEATHER_PERIOD_COLUMN,
        y="precipitation_total",
        title="Lluvia total por día seleccionado",
        labels={"precipitation_total": "Precipitación estimada (mm)", WEATHER_PERIOD_COLUMN: "Día"},
    )
    fig.update_layout(xaxis_title="Día", yaxis_title="Precipitación estimada (mm)")
    return apply_common_layout(fig)


def temperature_statistics_chart(data, x_column, title="Temperaturas Máxima, Mínima y Media"):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=data[x_column],
            y=data["temp_max"],
            name="Temperatura Máxima",
            marker_color=TEMP_MAX_COLOR,
        )
    )
    fig.add_trace(
        go.Bar(
            x=data[x_column],
            y=data["temp_min"],
            name="Temperatura Mínima",
            marker_color=TEMP_MIN_COLOR,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data[x_column],
            y=data["temp_mean"],
            mode="lines+markers",
            name="Temperatura Media",
            marker=dict(size=8, color=TEMP_MEAN_COLOR),
            line=dict(color=TEMP_MEAN_COLOR),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x_column,
        yaxis_title="Temperatura (°C)",
        barmode="group",
    )
    return apply_common_layout(fig, title)


def precipitation_statistics_chart(data, x_column, daily_name="Precipitación Diaria"):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data[x_column],
            y=data["precipitacion_acumulada"],
            mode="markers+lines",
            name="Precipitación Acumulada",
            marker=dict(size=8, color="blue"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=data[x_column],
            y=data["precipitaciones_totales"],
            name=daily_name,
            marker_color="cyan",
            opacity=0.6,
        )
    )
    fig.update_layout(
        title="Precipitación Acumulada y Diaria",
        xaxis_title="Mes" if x_column == "Mes" else "Fecha",
        yaxis_title="Precipitación estimada (mm)",
        barmode="overlay",
    )
    return apply_common_layout(fig, "Precipitación acumulada y diaria")


def align_monthly_statistics_chart(fig, month_order):
    fig.update_layout(
        height=390,
        margin=dict(l=20, r=20, t=55, b=75),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
        ),
    )
    fig.update_xaxes(categoryorder="array", categoryarray=list(month_order))
    return fig


def monthly_temperature_chart(data, selected_year):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=data["Mes"],
            y=data["temp_max"],
            name="Max Temp",
            marker_color=TEMP_MAX_COLOR,
        )
    )
    fig.add_trace(
        go.Bar(
            x=data["Mes"],
            y=data["temp_min"],
            name="Min Temp",
            marker_color=TEMP_MIN_COLOR,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["Mes"],
            y=data["temp_mean"],
            mode="lines+markers",
            name="Mean Temp",
            line=dict(color=TEMP_MEAN_COLOR),
        )
    )
    fig.update_layout(
        title=f"Monthly Temperature Statistics ({selected_year})",
        xaxis=dict(title="Mes", categoryorder="array", categoryarray=list(MONTH_MAPPING.keys())),
        yaxis=dict(title="Temperatura (°C)"),
        barmode="group",
    )
    return apply_common_layout(fig, f"Temperatura mensual ({selected_year})")


def statistics_metric_chart(data, x_column, y_column, title, yaxis_title):
    fig = px.line(
        data,
        x=x_column,
        y=y_column,
        markers=True,
        title=title,
        labels={y_column: yaxis_title, x_column: x_column},
    )
    fig.update_layout(xaxis_title=x_column, yaxis_title=yaxis_title)
    return apply_common_layout(fig)


def forecast_temperature_chart(data):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=data["horizonte"],
            y=data["temp_max"],
            name="Temp max",
            marker_color=TEMP_MAX_COLOR,
        )
    )
    fig.add_trace(
        go.Bar(
            x=data["horizonte"],
            y=data["temp_min"],
            name="Temp min",
            marker_color=TEMP_MIN_COLOR,
        )
    )
    fig.update_layout(barmode="group", xaxis_title="Horizonte", yaxis_title="Temperatura (°C)")
    return apply_common_layout(fig, "Temperatura prevista por horizonte")


def forecast_rain_chart(data):
    fig = px.bar(
        data,
        x="horizonte",
        y="rain_total",
        text="rain_total",
        title="Lluvia acumulada prevista",
        labels={"rain_total": "Precipitación estimada (mm)", "horizonte": "Horizonte"},
    )
    fig.update_layout(xaxis_title="Horizonte", yaxis_title="Precipitación estimada (mm)")
    return apply_common_layout(fig)


def forecast_temperature_accuracy_chart(data):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=data["horizonte"],
            y=data["mae_temp_max"],
            name="Error Tmax",
            marker_color=TEMP_MAX_COLOR,
        )
    )
    fig.add_trace(
        go.Bar(
            x=data["horizonte"],
            y=data["mae_temp_min"],
            name="Error Tmin",
            marker_color=TEMP_MIN_COLOR,
        )
    )
    fig.update_layout(
        barmode="group",
        xaxis_title="Horizonte",
        yaxis_title="Error absoluto medio (°C)",
    )
    return apply_common_layout(fig, "Error medio de temperatura")


def forecast_rain_accuracy_chart(data):
    fig = px.bar(
        data,
        x="horizonte",
        y="mae_rain_total",
        text="mae_rain_total",
        title="Error medio de lluvia",
        labels={"horizonte": "Horizonte", "mae_rain_total": "Error absoluto medio (mm)"},
    )
    fig.update_layout(xaxis_title="Horizonte", yaxis_title="Error absoluto medio (mm)")
    return apply_common_layout(fig)


def electricity_pie_chart(values):
    fig, ax = plt.subplots()
    ax.pie(values, labels=values.index, autopct=autopct_format, startangle=90)
    ax.axis("equal")
    return fig


def electricity_mix_chart(values):
    chart_data = values.rename_axis("Fuente").reset_index(name="Total (MW)")
    fig = px.bar(
        chart_data,
        x="Total (MW)",
        y="Fuente",
        orientation="h",
        title="Mix eléctrico por fuente",
        labels={"Total (MW)": "Total (MW)", "Fuente": "Fuente"},
    )
    fig.update_layout(xaxis_title="Total (MW)", yaxis_title="Fuente", yaxis=dict(categoryorder="total ascending"))
    return apply_common_layout(fig, height=420)


def water_reserve_chart(data):
    x_column = "Fecha" if "Fecha" in data.columns and data["Fecha"].notna().any() else "Mes_Dia"
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data[x_column],
            y=data["agua_embalsada_hm3"],
            mode="lines+markers",
            name="hm3",
        )
    )
    if "porcentaje_embalsado" in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data[x_column],
                y=data["porcentaje_embalsado"],
                mode="lines+markers",
                name="% embalsado",
                yaxis="y2",
            )
        )
        fig.update_layout(
            yaxis2=dict(title="% embalsado", overlaying="y", side="right"),
        )
    fig.update_layout(yaxis_title="Agua embalsada (hm3)")
    fig.update_xaxes(title_text="Fecha")
    return apply_common_layout(fig, "Reservas de agua")
