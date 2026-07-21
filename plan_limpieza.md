# Proyecto 1 · Plan de limpieza

**CC3084 – Data Science · Semestre II 2026**

Este documento se elaboró antes de modificar los datos. Para cada variable se
describe: (a) los problemas encontrados en el diagnóstico
([notebooks/01_diagnostico.ipynb](notebooks/01_diagnostico.ipynb)),
(b) la regla que el grupo usará para corregirlos y por qué se espera que
funcione, y (c) los riesgos de aplicar la transformación.

Principios generales:

- `data/raw/` no se modifica; toda transformación genera archivos nuevos en
  `data/processed/`.
- Ninguna regla elimina registros de forma automática; los casos dudosos se
  marcan y la decisión se documenta.
- Toda transformación queda registrada en la tabla de transformaciones
  (variable, problema, transformación, registros afectados, justificación) y
  se valida con pruebas automáticas al final.

---

## 1. Variables geográficas (P1)

Variables cubiertas: `DEPARTAMENTO`, `MUNICIPIO`, `DISTRITO`, `DEPARTAMENTAL`.

### 1.1 `DEPARTAMENTO`

#### Problema G1: `CIUDAD CAPITAL` fuera del catálogo oficial (2,161 registros)

La fuente separa la capital del resto del departamento de Guatemala: la columna
tiene 23 valores y el catálogo oficial tiene 22 departamentos.

- **Regla:** recodificar `CIUDAD CAPITAL` a `GUATEMALA`. Antes de recodificar
  se crea la variable derivada `ZONA_CAPITAL` a partir de `MUNICIPIO` (ver
  regla G3, que se aplica en conjunto) para no perder la distinción
  capital/resto del departamento.
- **Por qué funcionará:** el diagnóstico confirmó que la correspondencia
  `DEPARTAMENTO` ↔ `DEPARTAMENTAL` se cumple en el 100% de los registros y que
  los 2,161 registros de `CIUDAD CAPITAL` caen en las departamentales
  `GUATEMALA NORTE/SUR/OCCIDENTE/ORIENTE`. Todos pertenecen al departamento de
  Guatemala, por lo que la recodificación no tiene casos ambiguos.
- **Riesgos:**
  - Perder la distinción capital/resto del departamento. Se mitiga con la
    variable derivada `ZONA_CAPITAL`, documentada en el libro de códigos.
  - Colisión con registros que ya traen `DEPARTAMENTO = GUATEMALA` y
    `MUNICIPIO = GUATEMALA`: se verificaron 16 casos en el crudo, es decir, la
    fuente no fue consistente al separar la capital. Tras la recodificación
    esos 16 quedan junto a los 2,161 de la capital y se distinguen porque su
    `ZONA_CAPITAL` es `NA`. Esto se documenta en el libro de códigos.

#### Problema G2: nombres sin tilde (6 valores, 2,025 registros)

`PETEN`, `QUICHE`, `SOLOLA`, `SACATEPEQUEZ`, `SUCHITEPEQUEZ` y `TOTONICAPAN` no
coinciden textualmente con el catálogo oficial.

- **Regla:** mapeo explícito (diccionario) de cada valor observado a su forma
  oficial con tilde: `PETEN → PETÉN`, `QUICHE → QUICHÉ`, etc. No se aplica
  ninguna corrección automática.
- **Por qué funcionará:** el dominio es un catálogo cerrado de 22 valores y
  cada valor observado corresponde a un único departamento oficial al ignorar
  tildes (diagnóstico, sección 2.1). No hay ambigüedad.
- **Riesgos:**
  - Errores de codificación al introducir tildes si el CSV se lee con otro
    encoding. Se mitiga guardando en UTF-8 y documentando el encoding en el
    libro de códigos.
  - Inconsistencia con sistemas externos que usan la forma sin tilde. El grupo
    acepta el riesgo: se usa la forma del catálogo oficial y queda documentada.

### 1.2 `MUNICIPIO`

#### Problema G3: zonas de la capital mezcladas con municipios (2,161 registros)

Para `CIUDAD CAPITAL` la columna trae `ZONA 1`…`ZONA 25` en lugar del
municipio, es decir, dos dominios distintos en una misma columna.

- **Regla:** (se aplica junto con G1)
  1. Crear la variable derivada `ZONA_CAPITAL` (entera, 1–25) extrayendo el
     número con el patrón `^ZONA (\d+)$`; `NA` para el resto del país.
  2. Reemplazar esos `MUNICIPIO = ZONA N` por `GUATEMALA`, que es el municipio
     real.
- **Por qué funcionará:** el diagnóstico (sección 2.2) confirmó con una tabla
  cruzada que el patrón `ZONA N` aparece solo cuando
  `DEPARTAMENTO = CIUDAD CAPITAL` y viceversa. La regla captura exactamente a
  los registros afectados, sin falsos positivos.
- **Riesgos:**
  - Que en análisis posteriores se interprete la zona como municipio. Se
    mitiga documentando `ZONA_CAPITAL` como variable derivada en el libro de
    códigos.
  - Que algún municipio del interior contenga la palabra "ZONA" en el nombre.
    El patrón exige la forma exacta `ZONA <número>`, que no corresponde a
    ningún municipio del catálogo oficial.

#### Problema G4: nombres sin tilde respecto al catálogo oficial (mayoría de valores)

- **Regla:** validar y corregir contra el catálogo oficial de 340 municipios
  (INE), emparejando por la clave `(DEPARTAMENTO, MUNICIPIO)` e ignorando
  tildes. Tres casos:
  1. coincidencia exacta ignorando tildes: se sustituye por la forma oficial;
  2. sin coincidencia exacta: se busca candidato por similitud de cadenas
     (RapidFuzz/Levenshtein) solo dentro del mismo departamento, con umbral
     alto (≥ 90) y revisión manual de cada caso;
  3. sin candidato razonable: se conserva el valor, se marca y se documenta.
- **Por qué funcionará:** el dominio es cerrado (340 municipios) y emparejar
  dentro del departamento elimina la ambigüedad de municipios con el mismo
  nombre en departamentos distintos, detectada en el diagnóstico.
- **Riesgos:**
  - Falsos positivos del emparejamiento difuso entre municipios de nombre
    parecido en el mismo departamento. Se mitiga con el umbral alto y revisión
    manual; no se fusiona nada de forma automática.
  - Versión del catálogo: municipios creados o renombrados recientemente
    podrían no aparecer. Se fija y documenta la versión y fecha del catálogo
    usado en el libro de códigos.

### 1.3 `DISTRITO`

#### Problema G5: valores faltantes (532 registros, 4.48%)

- **Regla:** no imputar; los faltantes se conservan como `NA`.
- **Por qué funcionará:** el distrito escolar es un código administrativo que
  no puede deducirse con certeza de las demás columnas, así que imputarlo
  generaría datos incorrectos.
- **Riesgos:** los análisis por distrito pierden ese 4.48% de registros. Se
  documenta la cobertura de la variable en el libro de códigos.

#### Problema G6: códigos truncados `NN-` (70 registros)

Solo conservan el prefijo departamental (`01-`, `16-`, `17-`, `10-`).

- **Regla:** convertir a `NA`. El prefijo no aporta información: el
  departamento ya está en `DEPARTAMENTO`.
- **Por qué funcionará:** el patrón `^\d{2}-$` identifica exactamente a los 70
  casos (diagnóstico, sección 2.3) y la información que se pierde es
  redundante.
- **Riesgos:** pérdida de un dato parcial. El grupo lo acepta y lo documenta:
  los faltantes de `DISTRITO` pasan de 532 a 602 y así se reporta en el
  informe antes/después.

#### Problema G7: dos formatos conviviendo (`NN-NN-NNNN` y `NN-NNN`)

- **Regla:** no convertir entre formatos. Se valida que todo valor no nulo
  cumpla `^\d{2}-\d{2}-\d{4}$` o `^\d{2}-\d{3}$` y ambos formatos se
  documentan en el libro de códigos como codificaciones de la fuente.
- **Por qué funcionará:** no existe una especificación pública de equivalencia
  entre los dos esquemas, así que convertirlos generaría códigos inventados.
  La validación por regex garantiza que no queden valores malformados.
- **Riesgos:** un mismo distrito podría aparecer con dos códigos distintos y
  fragmentar agrupaciones por distrito. Se declara como limitación conocida en
  el libro de códigos.

### 1.4 `DEPARTAMENTAL`

#### Problema G8: inconsistencia de tildes con `DEPARTAMENTO`

`DEPARTAMENTAL` escribe los departamentos con tilde; `DEPARTAMENTO` sin tilde.

- **Regla:** no se modifica `DEPARTAMENTAL`; sus valores ya tienen la forma
  correcta con tilde. La inconsistencia se resuelve del lado de `DEPARTAMENTO`
  (regla G2). Tras la limpieza se agrega una prueba automática de coherencia
  cruzada: para cada registro, `DEPARTAMENTAL` debe corresponder al
  `DEPARTAMENTO` según el mapa de 26 → 22 documentado.
- **Por qué funcionará:** el diagnóstico mostró coherencia cruzada del 100%
  ignorando tildes; al restituir las tildes en `DEPARTAMENTO`, las dos
  columnas quedan en el mismo estándar y la prueba pasa a ser exacta.
- **Riesgos:** ninguno relevante, porque no se transforman valores. Solo hay
  que mantener el mapa 26 → 22 actualizado en el libro de códigos.

#### Nota (no es error): 26 categorías para 22 departamentos

`GUATEMALA` se subdivide en 4 direcciones departamentales y `QUICHÉ` en 2. Es
estructura administrativa del MINEDUC. No se unifica; el mapa completo se
documenta en el libro de códigos.

### 1.5 Resumen de reglas (geografía)

| # | Variable | Problema | Regla | Registros afectados (esperados) |
|---|---|---|---|---|
| G1 | `DEPARTAMENTO` | `CIUDAD CAPITAL` fuera de dominio | recodificar → `GUATEMALA` (con G3) | 2,161 |
| G2 | `DEPARTAMENTO` | sin tildes | diccionario cerrado → forma oficial | 2,025 |
| G3 | `MUNICIPIO` | zonas en vez de municipios | derivar `ZONA_CAPITAL` y recodificar → `GUATEMALA` | 2,161 |
| G4 | `MUNICIPIO` | sin tildes / errores vs catálogo | catálogo INE por `(depto, muni)` + similitud con revisión manual | mayoría de la columna |
| G5 | `DISTRITO` | faltantes | conservar `NA`, no imputar | 532 |
| G6 | `DISTRITO` | truncados `NN-` | convertir a `NA` | 70 |
| G7 | `DISTRITO` | dos formatos | validar por regex, no convertir, documentar | 11,265 |
| G8 | `DEPARTAMENTAL` | tildes inconsistentes con `DEPARTAMENTO` | sin cambio; prueba cruzada tras G2 | 0 (verificación) |

Ninguna regla elimina filas: el total de registros (11,867) no cambia con la
limpieza geográfica. Variable nueva: `ZONA_CAPITAL` (derivada, justificada en
el libro de códigos).

---

## 2. Establecimiento y dirección (P2)

*(pendiente)*

## 3. Teléfono, director y supervisor (P3)

*(pendiente)*

## 4. Código y variables categóricas (P4)

*(pendiente)*
