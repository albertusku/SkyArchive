# meteo_stats

`meteo_stats` recoge, almacena y visualiza datos de una estacion meteorologica casera. Consulta APIs meteorologicas, electricidad y embalses, guarda historicos en CSV, calcula estadisticas y muestra un dashboard con Streamlit.

El uso principal esperado es clonar el repo directamente en una Raspberry Pi y ejecutarlo alli.

## Requisitos

- Python 3
- Acceso a internet para instalar dependencias y consultar APIs
- Credenciales/API keys para los servicios configurados en `src/API/data.json`
- Opcional: `systemd` si quieres ejecutar la recoleccion periodica como servicio

## Instalacion rapida en Raspberry Pi

Desde la raiz del repo:

```bash
TargetEnv/setup_and_run.sh
```

El script:

- detecta la raiz del repo
- carga `deploy.meteo.env` si existe
- crea o reutiliza `meteo_python` o `METEO_VENV_DIR`
- instala `requirements.txt`
- avisa si falta `src/API/data.json`
- instala las unidades `systemd`
- activa `streamlit-dashboard.service` y `30min.timer`

Si quieres usar otro entorno virtual, define `METEO_VENV_DIR` antes de ejecutarlo:

```bash
export METEO_VENV_DIR=/ruta/a/tu/venv
TargetEnv/setup_and_run.sh
```

## Instalacion manual

```bash
python3 -m venv meteo_python
source meteo_python/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuracion

Crea `src/API/data.json` desde la plantilla versionada y sustituye los valores de ejemplo por los de tu estacion y tus credenciales:

```bash
cp src/API/data.example.json src/API/data.json
nano src/API/data.json
```

Las APIs con `"enabled": false` no se llaman. Si una API esta deshabilitada, sus credenciales no son necesarias. `station.zone` es opcional y se usa como parametro `zone` de Electricity Maps para elegir la zona electrica consultada, por ejemplo `"ES"`, `"FR"` o la zona soportada por la API. `extra_config.backup` es opcional; si no existe o `enabled` es `false`, no se hacen backups.

### Credenciales de APIs

Para rellenar `src/API/data.json`, crea las cuentas o tokens necesarios en estas paginas:

- Tomorrow.io Weather API: https://www.tomorrow.io/weather-api/
  - Documentacion de autenticacion: https://docs.tomorrow.io/reference/api-authentication
  - Usa la API key en `apis.tomorrow_api.api_key` y `apis.tomorrow_forecast_api.api_key`.
- Electricity Maps API: https://app.electricitymaps.com/developer-hub/playground
  - Portal/free tier: https://free-tier-signup.pages.dev/
  - Documentacion: https://app.electricitymaps.com/docs
  - Usa el token en `apis.electricity_api.auth-token`.
- Water reserve API: no requiere cuenta externa. Configura la pagina de provincia de Embalses.net en `apis.water_reserve_api.url`, por ejemplo `https://www.embalses.net/provincia-3-palencia.html`.
  - El recolector consulta esa URL directamente los martes a las 16:00.
  - La API Flask local (`src/API/water_reserve_api.py`) queda como compatibilidad legacy y no es necesaria en el flujo recomendado.

No subas `src/API/data.json` a git. El archivo esta ignorado porque contiene credenciales reales.

## Comandos de arranque

Desde la raiz del repo, con el entorno virtual activado:

```bash
source meteo_python/bin/activate
```

Arrancar solo el dashboard:

```bash
PYTHONPATH=src streamlit run src/Visualizer/Today_page.py --server.port 8502
```

Arrancar el dashboard con el script del repo:

```bash
src/Visualizer/start_dashboard.sh
```

Ejecutar una recoleccion manual de datos:

```bash
PYTHONPATH=src python src/main.py
```

Instalar y activar la recoleccion periodica con `systemd`:

```bash
TargetEnv/install_services.sh
sudo systemctl enable --now 30min.timer
```

Si aun no hay CSV generados, el dashboard mostrara avisos en vez de fallar. Para generar datos reales ejecuta el recolector manualmente o activa el timer.

`src/main.py` tiene efectos laterales: consulta APIs, escribe CSV/logs y puede intentar reiniciar el servicio `streamlit-dashboard` si existe.

## Instalar servicios systemd en la Raspberry Pi

El comando recomendado es:

```bash
TargetEnv/setup_and_run.sh
```

Por defecto se usan:

- usuario actual
- raiz actual del repo
- `METEO_VENV_DIR` si existe, o `meteo_python` en la raiz
- dashboard en `0.0.0.0:8502`

Si necesitas sobrescribir valores, crea `deploy.meteo.env` desde la plantilla:

```bash
cp deploy.example.env deploy.meteo.env
```

Edita solo los valores que necesites. `deploy.meteo.env` esta ignorado por git.

Si ya tienes dependencias y configuracion preparadas y solo quieres reinstalar unidades:

```bash
TargetEnv/install_services.sh
sudo systemctl enable --now streamlit-dashboard.service
sudo systemctl enable --now 30min.timer
```

## Scripts opcionales de despliegue remoto

Estos scripts solo son necesarios si despliegas desde otro ordenador a una Raspberry Pi remota:

```bash
./send_data.sh toPC
./send_data.sh toPi
./push_to_raspi.sh
```

Requieren `deploy.meteo.env` con `REMOTE_USER`, `REMOTE_HOST` y `REMOTE_DIR`.

## Tests

```bash
PYTHONPATH=src pytest
```

Si usas el venv recomendado:

```bash
PYTHONPATH=src meteo_python/bin/python -m pytest
```

## Datos generados

No se deben versionar:

- `src/API/data.json`
- `deploy.meteo.env`
- CSV de `src/Data_storage/Storage/`
- logs
- respuestas `api_*_response.json`
- `TargetEnv/generated/`
