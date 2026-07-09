import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
import os
import subprocess
import re


import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from Logs.logger import setup_logger

logger=setup_logger("API_connection",os.path.join(LOGS_DIR,"Procces.log"))

app = Flask(__name__)

# Configuración de API Key
API_KEY = ""
DEFAULT_WATER_RESERVE_URL = water_reserve_url
DEFAULT_HEADERS = {
    "User-Agent": "meteo-stats/1.0 (+https://www.embalses.net/)",
}
REQUEST_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1


def fetch_embalses_html(
    url=DEFAULT_WATER_RESERVE_URL,
    timeout=REQUEST_TIMEOUT_SECONDS,
    max_retries=MAX_RETRIES,
):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            if attempt + 1 >= max_retries:
                logger.error(f"Error al acceder a la página de embalses: {e}")
                return None
            time.sleep(RETRY_DELAY_SECONDS)


def _clean_number(value):
    if value is None:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", value.replace("\xa0", " "))
    if not match:
        return None
    return match.group(0).replace(",", ".")


def _extract_province(soup):
    candidates = []
    if soup.title and soup.title.string:
        candidates.append(soup.title.string)
    for tag_name in ("h1", "h2"):
        candidates.extend(tag.get_text(" ", strip=True) for tag in soup.find_all(tag_name))

    for text in candidates:
        match = re.search(
            r"(?:provincia de|embalses de|embalses en)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s-]+)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            province = re.split(r"[-|,.:]", match.group(1).strip())[0].strip()
            return province.title()
    return None


def _extract_data_date(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
    return match.group(0) if match else None


def parse_embalses_html(html):
    soup = BeautifulSoup(html, "html.parser")
    resultado_divs = soup.find_all("div", class_="Resultado")

    if len(resultado_divs) < 2:
        logger.warning("No se encontraron suficientes divs con clase 'Resultado'")
        return {"error": "No se encontraron datos"}

    raw_values = []
    for resultado_div in resultado_divs:
        value_tag = resultado_div.find("strong")
        text = value_tag.get_text(" ", strip=True) if value_tag else resultado_div.get_text(" ", strip=True)
        if text:
            raw_values.append(text)

    agua_embalsada_hm3 = _clean_number(raw_values[0]) if len(raw_values) > 0 else None
    porcentaje_embalsado = _clean_number(raw_values[1]) if len(raw_values) > 1 else None

    if agua_embalsada_hm3 is None or porcentaje_embalsado is None:
        logger.warning("Los datos de embalses no tienen formato numérico válido")
        return {"error": "Datos de embalses inválidos"}

    data = {
        "embalses": {
            "valores": {
                "agua_embalsada_hm3": agua_embalsada_hm3,
                "porcentaje_embalsado": porcentaje_embalsado,
            }
        }
    }
    provincia = _extract_province(soup)
    fecha_dato = _extract_data_date(soup)
    if provincia:
        data["embalses"]["provincia"] = provincia
    if fecha_dato:
        data["embalses"]["fecha_dato"] = fecha_dato
    return data


def obtener_datos(url=DEFAULT_WATER_RESERVE_URL):
    html = fetch_embalses_html(url)
    if html is None:
        return {"error": "No se pudo acceder a la página de embalses."}
    return parse_embalses_html(html)

@app.route("/datos", methods=["GET"])
def datos():
    api_key = request.headers.get("X-API-KEY")
    if api_key != API_KEY:
        return jsonify({"error": "API Key inválida"}), 403
    
    datos = obtener_datos()
    return jsonify(datos)

def check_service_running(service_name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", service_name]
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error al comprobar el servicio: {e}")
        return False

if __name__ == "__main__":

    
    if len(sys.argv) != 2:
        print("Uso: python water_reserve_api.py <API_KEY>")
        sys.exit(1)
    
    API_KEY = sys.argv[1]
    service_name = f"water_reserve_api@{API_KEY}"
    logger.info(f"Esperando a que arranque el servicio {service_name}...")
    time.sleep(10)
    
    result = subprocess.run(["sudo", "systemctl", "status", f"water_reserve_api@{API_KEY}"], capture_output=True, text=True)
    print("result=", result)
    
    if check_service_running(service_name):
        logger.info("Servicio activo. Iniciando servidor Flask.")
        app.run(debug=False)  # Sin debug en producción
    else:
        logger.error("El servicio no está activo. Abortando.")
        print("Error al iniciar API")
        sys.exit(1)

    
