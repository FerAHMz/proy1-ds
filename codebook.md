# Libro de códigos

- Fuente: http://www.mineduc.gob.gt/BUSCAESTABLECIMIENTO_GE/
- Fecha de extracción: 2026-07-20
- Versión del conjunto limpio: 1.0.0

Definición de variables del conjunto limpio generado en `data/processed/`.

| Variable | Tipo | Descripción | Dominio permitido | Valores posibles | Tratamiento aplicado | Derivada |
| --- | --- | --- | --- | --- | --- | --- |
| CODIGO | string | Código único del establecimiento educativo. | NN-NN-NNNN-NN. | 11,867 valores únicos en el dataset limpio. | Conservado como texto; validado con regex. | No |
| DISTRITO | string | Código del distrito escolar. | NN-NN-NNNN o NN-NNN; NN- se convierte a NA. | 1,681 valores distintos en el crudo. | Se conservan los formatos completos; truncados a NA. | No |
| DEPARTAMENTO | string | Departamento del establecimiento. | Catálogo oficial de 22 departamentos. | 22 categorías. | Se corrigen tildes y CIUDAD CAPITAL -> GUATEMALA. | No |
| MUNICIPIO | string | Municipio del establecimiento. | Catálogo oficial de municipios de Guatemala. | Municipio real; zonas de la capital se recodifican a GUATEMALA. | Se estandariza la capital y se documentan las zonas en ZONA_CAPITAL. | No |
| ZONA_CAPITAL | Int64 | Zona de la ciudad capital derivada desde MUNICIPIO. | Enteros positivos entre 1 y 25. | Solo para registros de CIUDAD CAPITAL. | Derivada para conservar la distinción zona/municipio. | Sí, a partir de MUNICIPIO. |
| ESTABLECIMIENTO | string | Nombre del establecimiento. | Texto libre. | Alta cardinalidad, con variantes ortográficas. | Normalización conservadora de espacios, mayúsculas y comillas. | No |
| ESTABLECIMIENTO_NORM | string | Clave normalizada para detectar variantes del establecimiento. | Texto alfanumérico en mayúsculas sin tildes. | Clave auxiliar de detección y agrupación. | Derivada sin modificar el nombre original. | Sí, a partir de ESTABLECIMIENTO. |
| DIRECCION | string | Dirección postal del establecimiento. | Texto libre. | Con abreviaturas y referencias de ubicación. | Se normalizan espacios, mayúsculas y abreviaturas frecuentes. | No |
| TELEFONO | string | Teléfono de contacto. | Bloques de 8 dígitos, separados por ';' si hay más de uno. | Puede ser NA si no se recupera un número válido. | Se extraen números válidos de 8 dígitos y se descarta ruido. | No |
| SUPERVISOR | string | Nombre del supervisor educativo. | Texto libre de persona. | Canonicalizado por nombre base. | Se unifican variantes ortográficas y caracteres atípicos. | No |
| DIRECTOR | string | Nombre del director del establecimiento. | Texto libre de persona. | Canonicalizado por nombre base. | Se eliminan títulos y se unifican variantes ortográficas. | No |
| NIVEL | string | Nivel escolar reportado en la fuente. | DIVERSIFICADO. | Constante. | Normalización mínima. | No |
| SECTOR | string | Sector administrativo del establecimiento. | PRIVADO, OFICIAL, COOPERATIVA, MUNICIPAL. | 4 categorías. | Normalización mínima. | No |
| AREA | string | Área geográfica. | URBANA, RURAL, SIN ESPECIFICAR. | 3 categorías. | Normalización mínima. | No |
| STATUS | string | Estado operativo del establecimiento. | ABIERTA, CERRADA TEMPORALMENTE, CERRADA DEFINITIVAMENTE, TEMPORAL TITULOS, TEMPORAL NOMBRAMIENTO. | 5 categorías. | Normalización mínima. | No |
| MODALIDAD | string | Modalidad de atención. | MONOLINGUE, BILINGUE. | 2 categorías. | Normalización mínima. | No |
| JORNADA | string | Jornada escolar. | DOBLE, VESPERTINA, MATUTINA, SIN JORNADA, NOCTURNA, INTERMEDIA. | 6 categorías. | Normalización mínima. | No |
| PLAN | string | Plan de estudios o modalidad pedagógica. | Categorías observadas en la fuente. | 13 categorías, incluido INTERCALADO. | Normalización mínima y preservación de categorías válidas. | No |
| DEPARTAMENTAL | string | Dirección departamental del MINEDUC responsable del establecimiento. | 26 categorías administrativas. | Se documenta el mapa Guatemala x4 y Quiché x2. | Normalización mínima; sirve como comprobación cruzada. | No |

## Reglas de limpieza aplicadas

- `DEPARTAMENTO`: recodificación de `CIUDAD CAPITAL` a `GUATEMALA` y corrección de tildes por mapeo explícito.
- `MUNICIPIO`: extracción de `ZONA_CAPITAL` para `ZONA N` y recodificación a `GUATEMALA` en la capital.
- `DISTRITO`: los valores truncados `NN-` se convierten a `NA`.
- `ESTABLECIMIENTO`: normalización conservadora de texto y derivación de `ESTABLECIMIENTO_NORM`.
- `DIRECCION`: normalización de espacios, mayúsculas y abreviaturas frecuentes.
- `TELEFONO`: extracción de bloques válidos de 8 dígitos, separados por `;` si hay más de uno.
- `SUPERVISOR` y `DIRECTOR`: canonicalización por nombre base, corrección de caracteres atípicos y eliminación de títulos pegados.
- Variables categóricas: normalización mínima de espacios y mayúsculas, sin recodificar valores válidos.
