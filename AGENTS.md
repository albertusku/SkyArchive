# AGENTS.md

Guia para agentes que trabajen en este repositorio.

## Proyecto

`meteo_stats` recoge, almacena y visualiza datos de una estacion meteorologica casera. El flujo principal consulta APIs meteorologicas, electricidad y embalses, guarda resultados en CSV, calcula estadisticas y muestra historicos mediante Streamlit. Tambien genera predicciones de estacion meteorologica a partir de un modelo `joblib` entrenado externamente. El modulo SDR/NOAA sigue en el repo, pero actualmente la llamada a `get_satellite_info()` esta comentada en `src/main.py`.

El proyecto esta orientado a ejecutarse en una Raspberry Pi con servicios `systemd`. Las rutas locales se calculan desde el repo siempre que es posible. Las copias de seguridad se configuran en `src/API/data.json` bajo `extra_config.backup`, y las unidades `systemd` se generan desde plantillas de `TargetEnv/`.

## Estructura

- `src/main.py`: ciclo principal de recoleccion. Lee configuracion, consulta APIs, actualiza CSV y reinicia el dashboard. Importa SDR, pero la ejecucion de `get_satellite_info()` esta comentada.
- `src/config.py`: fuente central de rutas, URLs, ubicacion, modelo de prediccion y constantes temporales. Mantener aqui las rutas compartidas.
- `src/API/`: clientes de APIs externas y API Flask local para embalses. `API_connection.py` usa clases por API y un agregador `get_data_from_api`.
- `src/Data_storage/`: escritura de CSV, estadisticas diarias/mensuales, predicciones estacionales y backups.
- `src/Models/`: modelos locales, actualmente `season_pred.joblib` para prediccion de estaciones.
- `src/Visualizer/`: dashboard Streamlit, paginas y utilidades de visualizacion. Las paginas deben ser capas finas sobre helpers testeables. Incluye `dashboard_data.py`, `dashboard_charts.py`, `Season_predictions.py` y `season_predictions_utils.py`.
- `src/SDR/`: calculo de pases NOAA y gestion de captura SDR.
- `src/Util/`: utilidades manuales para reparar datos, generar estadisticas, crear datasets diarios con Open-Meteo y completar campos historicos.
- `src/Logs/`: configuracion del logger.
- `TargetEnv/`: plantillas, generador e instalador de unidades `systemd` para la Raspberry Pi. `TargetEnv/install_services.sh` es el flujo recomendado cuando el repo se clona directamente en la Pi.
- `send_data.sh` y `push_to_raspi.sh`: sincronizacion y despliegue remoto opcional desde otra maquina. Requieren `deploy.meteo.env`.
- `test/`: tests pytest para APIs, almacenamiento, estadisticas, logger, SDR, visualizacion de predicciones y utilidades. La suite actual se ejecuta con `PYTHONPATH=src pytest`.

## Entorno y dependencias

El repo versiona `requirements.txt` con las dependencias Python necesarias para ejecutar la aplicacion y los tests. Por imports del codigo, el entorno Python necesita al menos:

- `requests`
- `pandas`
- `streamlit`
- `plotly`
- `matplotlib`
- `flask`
- `beautifulsoup4`
- `skyfield`
- `psutil`
- `numpy`
- `joblib`
- `scikit-learn` probablemente necesario para cargar `src/Models/season_pred.joblib`
- `pytest` para tests

Usar `PYTHONPATH=src` al ejecutar modulos desde la raiz, porque los imports del proyecto asumen que `src` esta en el path.

Entorno virtual recomendado desde la raiz:

```bash
python3 -m venv meteo_python
source meteo_python/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

El nombre/ruta del entorno virtual puede sobrescribirse con `METEO_VENV_DIR`. Si no se define, los scripts asumen `meteo_python` en la raiz del repo.

Si aparecen dependencias adicionales por entorno, anadirlas a `requirements.txt` e instalarlas en el venv.

## Comandos utiles

Desde la raiz del repo:

```bash
PYTHONPATH=src python src/main.py
```

Ejecuta el ciclo principal. Tiene efectos laterales: consulta red, escribe CSV/JSON/logs e intenta reiniciar `streamlit-dashboard` con `systemctl`. En el estado actual no procesa SDR porque `get_satellite_info()` esta comentado.

```bash
PYTHONPATH=src streamlit run src/Visualizer/Today_page.py --server.port 8502
```

Arranca el dashboard Streamlit local.

```bash
src/Visualizer/start_dashboard.sh
```

Arranca el dashboard usando rutas relativas al propio repo. Usa `METEO_VENV_DIR` si esta definido; si no, usa `meteo_python` en la raiz.

```bash
TargetEnv/install_services.sh
```

Genera e instala localmente las unidades `systemd` en una Raspberry Pi donde el repo ya esta clonado. Usa por defecto el usuario actual, la raiz actual del repo, `METEO_VENV_DIR` o `meteo_python`, y el dashboard en `0.0.0.0:8502`.

```bash
PYTHONPATH=src python src/API/water_reserve_api.py <API_KEY>
```

Arranca la API Flask local de embalses. El codigo comprueba el estado del servicio `water_reserve_api@<API_KEY>`, por lo que en desarrollo puede requerir mocks o adaptacion.

```bash
PYTHONPATH=src python src/Util/create_open_meteo_training_csv.py
```

Descarga datos diarios historicos de Open-Meteo para 2000-2023, los alinea con el esquema de `Statistics_day.csv` y genera `open_meteo_daily_2000_2023.csv` y `training_weather_daily_2000_2026.csv` en la raiz. Consulta red y puede tardar por reintentos de la API.

```bash
PYTHONPATH=src python src/Util/backfill_statistics_day_weather_fields.py
```

Completa en `Statistics_day.csv` las columnas `humidity`, `pressure` y `clouds` a partir de medias diarias de `Historical_weather.csv`. Crea una copia `.bak_<timestamp>` antes de sobrescribir el CSV.

```bash
./send_data.sh toPC
./send_data.sh toPi
```

Sincroniza CSV entre la Raspberry Pi y el PC. Requiere direccion explicita: `toPC` descarga desde la Pi y `toPi` sube desde local. Tambien sincroniza `Season_prediction.csv` si existe.
Es un flujo opcional de despliegue remoto y requiere `deploy.meteo.env`.

```bash
PYTHONPATH=src pytest
```

Punto de entrada de tests. `pytest.ini` limita la busqueda a `test/` y excluye `BK`, `.git` y `meteo_python`.

## Contratos internos actuales

- `Data_storage.storage_builder.read_json()` devuelve un diccionario anidado por API: `tomorrow_api`, `tomorrow_forecast_api`, `electricity_api`, `water_reserve_api`, etc.
- Cada clase de `src/API/API_connection.py` recibe solo su subdiccionario plano. Por ejemplo, `TomorrowAPIConnection.get_current_data()` espera `{"api_key": ..., "latitude": ..., "longitude": ...}`.
- `ElectricityAPIConnection.get_current_data()` usa `auth-token` de `params` y consulta Electricity Maps con `zone` leida desde `src/API/data.json` bajo `station.zone` mediante `get_zone_config()`. La URL base no debe llevar `?zone=...`; el codigo lo pasa como parametro query `params={"zone": zone}` si existe.
- `get_data_from_api(params)` es el adaptador entre `read_json()` y las clases: toma `params[api_connection.name]` y devuelve las claves que consume `create_storage()`: `current_status`, `forecast_status`, `electricity_status` y `water_reserve_status`. Cada valor es un wrapper `{"ok": true, "data": ...}` o `{"ok": false, "data": None}`.
- `FAILED_RESPONSE` es `None`. `create_storage_*()` desempaqueta cada wrapper con `response_data()` y no escribe CSV cuando la API fallo, esta deshabilitada o devolvio `None`.
- `create_storage()` siempre intenta guardar datos actuales, forecast, electricidad y embalses; luego a las 23:30 ejecuta `get_today_data()` y finalmente llama a `create_BK()`.
- `create_BK()` solo copia si `extra_config.backup.enabled` es `true` y `extra_config.backup.path` existe y es un directorio. Si falta la seccion `extra_config`, el backup queda desactivado.
- `save_SDR_files()` usa el mismo path de backup configurado y crea subdirectorios por satelite/fecha.
- A las 00:00, `create_storage_dataframe()` calcula estadisticas del dia anterior con `make_statistics()`. Esta funcion actualiza `Statistics_day.csv`, calcula estadistica mensual si empieza mes nuevo y llama a `make_model_prediction()`.
- `make_model_prediction()` carga `src/Models/season_pred.joblib`, usa las columnas `temp_max`, `temp_min`, `temp_mean`, `precipitaciones_totales`, `wind_speed_max`, `humidity`, `pressure` y `clouds`, y anade filas a `Season_prediction.csv`.
- `src/Visualizer/pages/Season_predictions.py` espera `Season_prediction.csv` con columnas `Year`, `Mes`, `Dia`, `real_season`, `prediction` y opcionalmente columnas `prob_<clase>`.

## Arquitectura del Visualizer

La interfaz Streamlit debe mantenerse separada de la logica de datos y graficos:

- `src/Visualizer/Today_page.py` es la pagina principal que lanza Streamlit.
- `src/Visualizer/pages/` contiene las paginas secundarias que Streamlit descubre automaticamente.
- `src/Visualizer/dashboard_data.py` contiene funciones puras o casi puras para preparar datos: normalizar meses, filtrar historicos, preparar estadisticas, forecast, electricidad, reservas de agua, satelites, logs y TODO.
- `src/Visualizer/dashboard_charts.py` contiene la construccion de figuras Plotly/Matplotlib.
- `src/Visualizer/season_predictions_utils.py` contiene la logica especifica de la pagina de predicciones estacionales.

Al implementar una pagina nueva o una funcionalidad nueva en una pagina existente:

- Mantener la pagina Streamlit como capa fina: `st.set_page_config`, titulo, widgets, llamadas a helpers y render de tablas/graficos.
- No meter transformaciones largas de `pandas`, calculos de fechas, filtros complejos ni construccion detallada de figuras directamente en la pagina.
- Si la funcionalidad prepara o filtra datos, anadirla a `dashboard_data.py` o a un helper especifico si el dominio lo justifica.
- Para leer CSV desde paginas Streamlit, usar `load_csv_file()` de `dashboard_data.py` para convertir ficheros inexistentes o vacios en avisos controlados.
- Si la funcionalidad crea un grafico, anadir una funcion en `dashboard_charts.py` que reciba un `DataFrame` ya preparado y devuelva la figura.
- Usar rutas de `src/config.py`; no duplicar paths ni nombres de ficheros CSV en paginas.
- Evitar `print()` de depuracion en Streamlit. Usar mensajes `st.warning`, `st.error` o logging si hace falta.
- Evitar `sys.path.append` duplicado por pagina. Si una pagina necesita robustez al ejecutarse desde Streamlit sin `PYTHONPATH`, usar el patron actual con `Path(__file__).resolve().parents` para insertar `src`.
- Mantener los textos, widgets y layout visibles salvo que la tarea pida explicitamente cambiar la UI.
- Cuando se extraiga logica nueva, anadir tests unitarios en `test/` contra los helpers, sin arrancar Streamlit.

Ejemplo de patron recomendado:

```python
data = prepare_daily_statistics(load_stats_data())
filtered_data = filter_recent_days(data, num_days, datetime.now())
st.plotly_chart(temperature_statistics_chart(filtered_data, "Fecha"))
```

El objetivo es que las paginas sean faciles de leer y que la logica importante pueda probarse con `pytest` sin abrir el dashboard.

## Configuracion, datos y secretos

- `src/API/data.json` contiene credenciales, parametros de APIs, la seccion `station` (`name`, `latitude`, `longitude`, `altitude` y opcionalmente `zone`) y opcionalmente `extra_config.backup`. `station.zone` se usa para la zona de Electricity Maps. Esta ignorado por git y no debe versionarse.
- `deploy.meteo.env` contiene configuracion local de despliegue remoto o overrides de systemd (`REMOTE_USER`, `REMOTE_HOST`, `REMOTE_DIR`, `SERVICE_USER`, `APP_DIR`, `METEO_VENV_DIR`, etc.). Esta ignorado por git. Versionar solo `deploy.example.env`.
- Los CSV de `src/Data_storage/Storage/`, logs, TXT generados y respuestas JSON de APIs son datos generados y no deben versionarse. Comprobar `git status` antes de commit si aparece algun `api_*_response.json`.
- `open_meteo_daily_2000_2023.csv`, `training_weather_daily_2000_2026.csv` y copias `*.bak_<timestamp>` de utilidades son artefactos generados; versionarlos solo si se decide explicitamente usarlos como dataset fuente.
- No incluir API keys, tokens, datos reales sensibles ni logs completos en commits.
- Si se anaden ejemplos de configuracion, usar valores ficticios y documentar el formato esperado.

## Efectos laterales importantes

Evitar ejecutar estos comandos sin intencion explicita:

- `push_to_raspi.sh`: usa SSH/rsync/scp, crea un backup local de la Raspberry Pi, sincroniza datos y despliega todo el repo al host configurado en `deploy.meteo.env`. No es necesario para usuarios que clonan directamente en la Raspberry Pi.
- `send_data.sh toPC|toPi`: sincroniza CSV entre la maquina local y la Raspberry Pi configurada en `deploy.meteo.env`.
- `src/main.py`: escribe datos, consulta APIs y reinicia servicios. Si se reactiva `get_satellite_info()`, tambien puede activar logicamente el flujo SDR.
- `src/Util/create_open_meteo_training_csv.py`: consulta Open-Meteo y escribe CSV generados en la raiz.
- `src/Util/backfill_statistics_day_weather_fields.py`: modifica `Statistics_day.csv` y crea backup local.
- `src/SDR/satellites_info.py`: usa `systemctl`, `rtl_fm`, `sox`, `at`, `noaa-apt` y mueve ficheros al path de backup configurado en `src/API/data.json`.

En tests o cambios de logica, aislar red, sistema de archivos, `systemctl`, `os.system`, `subprocess`, `time.sleep` y dispositivos SDR mediante mocks.

## Convenciones de desarrollo

- Mantener cambios pequenos y ligados al comportamiento solicitado.
- Preferir las rutas de `src/config.py` antes que duplicar strings de paths.
- Conservar compatibilidad de columnas CSV: las paginas Streamlit dependen de nombres como `Year`, `Mes`, `Dia`, `Hora`, `temp (C)`, `precipitation (mm/h)`, `wind_speed(m/s)`, `hum(%)`, `pres(hPa)` y `clouds(%)`. Las estadisticas diarias y el modelo usan ademas `season`, `humidity`, `pressure` y `clouds`.
- Evitar refactors amplios de imports o estructura salvo que sean necesarios para la tarea.
- Si se cambia el flujo de APIs o almacenamiento, revisar tambien `create_storage()`, las paginas de `src/Visualizer/pages/`, `src/Visualizer/season_predictions_utils.py` y las estadisticas de `src/Data_storage/statistics.py`.
- Si se modifica el Visualizer, mantener el patron `pagina Streamlit fina -> dashboard_data/dashboard_charts -> tests`. La suite actual incluye `test/test_visualizer_dashboard.py` para los helpers del dashboard.
- Mantener el contrato `read_json()` -> `get_data_from_api()` -> `create_storage()` descrito arriba, o actualizar tests y consumidores a la vez.
- Si se cambian las columnas de `Statistics_day.csv`, revisar `make_model_prediction()`, `src/Util/create_open_meteo_training_csv.py`, `src/Util/backfill_statistics_day_weather_fields.py`, `src/Visualizer/pages/Season_predictions.py` y sus tests.
- Si se cambia codigo con efectos externos, anadir o actualizar tests que mockeen APIs, comandos de sistema y ficheros.
- Mantener el estilo existente cuando el cambio sea local. No introducir formateadores globales sin acuerdo previo.

## Notas para despliegue

Flujo recomendado en una Raspberry Pi:

```bash
python3 -m venv meteo_python
source meteo_python/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp deploy.example.env deploy.meteo.env  # opcional, solo para sobrescribir defaults
TargetEnv/install_services.sh
sudo systemctl enable --now 30min.timer
```

Las unidades `systemd` versionadas son plantillas (`*.service.template`). `TargetEnv/render_services.sh` genera los `.service` en `TargetEnv/generated/`, que esta ignorado por git porque contiene rutas reales de la maquina. Por defecto usa el usuario actual, la raiz del repo, `METEO_VENV_DIR` o `meteo_python`, y el dashboard en `0.0.0.0:8502`.

`src/Visualizer/start_dashboard.sh` calcula la raiz del repo de forma relativa al script y usa `METEO_VENV_DIR` si esta definido. Si no, usa `meteo_python` en la raiz.
