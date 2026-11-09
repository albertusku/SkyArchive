# Precipitación: cálculo y reconstrucción manual

Tomorrow.io define `precipitationIntensity` como una **tasa instantánea** en mm/h con `units=metric`. El parámetro `timesteps=30m` da la resolución de la serie; no convierte la tasa en una cantidad observada durante media hora. El recolector consulta `timesteps=current` para obtener condiciones actuales en cada ejecución programada cada 30 minutos. La API ofrece `rainAccumulation` para la **hora anterior**, pero no un acumulado independiente y verificado para cada intervalo de 30 minutos. Los datos históricos de su API proceden de un sistema de reanálisis distinto de la serie reciente y tampoco sustituyen directamente las lecturas guardadas. Fuentes: [campo de intensidad y acumulado](https://docs.tomorrow.io/reference/data-layers-core), [resolución y disponibilidad](https://docs.tomorrow.io/reference/weather-data-layers), [API histórica](https://docs.tomorrow.io/reference/historical).

SkyArchive conserva la intensidad original en `Historical_weather.csv`. Para cada hora local `HH:00` o `HH:30` válida y no duplicada estima `mm = mm/h × 0,5`. La cifra presupone que la tasa instantánea representa toda esa media hora; no es una medición de pluviómetro. Las horas ausentes y las intensidades inválidas no se sustituyen por cero. El máximo de una hora se obtiene de dos medias horas consecutivas del mismo día. El acumulado mensual se actualiza en la migración solo si todos los días y sus intervalos son completos. Los días parciales se informan y sus valores diarios se refieren únicamente a las muestras válidas observadas.

## Uso

Detén temporalmente el recolector antes de aplicar la migración. Desde la raíz del repositorio:

```bash
PYTHONPATH=src meteo_python/bin/python src/Util/recalculate_precipitation_history.py --dry-run
PYTHONPATH=src meteo_python/bin/python src/Util/recalculate_precipitation_history.py
```

Para otro directorio de CSV, añade `--directory /ruta/al/directorio` a cualquiera de los dos comandos. El informe JSON sale por stdout y contiene valores anteriores, nuevos, diferencias, períodos incompletos, duplicados, errores y rutas de copias. Puedes guardarlo con redirección a un archivo externo si necesitas conservarlo.

Antes de sustituir archivos, el script valida los CSV de salida y crea copias `Statistics_day.csv.bak_<marca>` y `Statistics_month.csv.bak_<marca>`. Si una sustitución falla, intenta restaurar ambos CSV a los bytes originales. Para restaurar manualmente una ejecución concreta, usa las dos rutas de copias indicadas en su informe:

```bash
cp -p /ruta/Statistics_day.csv.bak_MARCA /ruta/Statistics_day.csv
cp -p /ruta/Statistics_month.csv.bak_MARCA /ruta/Statistics_month.csv
```

El histórico original no se abre para escritura. No se crea una fila diaria si falta, pues las demás estadísticas no se pueden reconstruir con seguridad. Los registros con la misma hora local se cuentan una sola vez. En el cambio de horario de otoño no se puede distinguir las dos ocurrencias de `02:00` y `02:30` sin un offset UTC, por lo que ese día se informa como incompleto. En el cambio de primavera se descartan las horas locales inexistentes. Una copia artificial de la lectura anterior solo puede sospecharse por igualdad de campos, no demostrarse; se informa como incertidumbre.
