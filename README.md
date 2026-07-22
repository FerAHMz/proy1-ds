# proy1-ds

## Integrantes

- Jorge Luis Felipe Aguilar Portillo — 23195
- Carlos Nicolas Concua Trujillo — 23197
- Fernando Andree Hernández Martínez — 23645
- Fernando José Rueda Rodas — 23748

## Reproducibilidad

El flujo completo de limpieza y validación se ejecuta con:

```bash
python src/clean_mineduc.py
```

Ese script lee `data/raw/MINEDUC_establecimientos_diversificado.csv`, genera el conjunto limpio en `data/processed/MINEDUC_establecimientos_diversificado_limpio.csv` y escribe dos artefactos de documentación reproducible:

- `data/processed/informe_calidad.md`
- `codebook.md`
- `documentacion_reproducibilidad.pdf`

El detalle de las reglas de limpieza está en `plan_limpieza.md`.
