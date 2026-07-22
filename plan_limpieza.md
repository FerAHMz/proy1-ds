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

Variables cubiertas: `ESTABLECIMIENTO` y `DIRECCION`. Son campos de **texto
libre**, así que los problemas no están en el dominio sino en el **formato**
(tildes, comillas, puntuación, abreviaturas) y en los **duplicados parciales**
(mismo establecimiento escrito de varias maneras). El diagnóstico está en
[notebooks/01_diagnostico.ipynb](notebooks/01_diagnostico.ipynb), Sección 3.

### 2.1 `ESTABLECIMIENTO`

#### Problema E1: valores faltantes (5 registros, 0.04%)

- **Regla:** no imputar; los faltantes se conservan como `NA`.
- **Por qué funcionará:** el nombre del establecimiento es un nombre propio que
  no puede deducirse con certeza de las demás columnas; inventarlo introduciría
  datos falsos.
- **Riesgos:** 5 registros quedan sin nombre. El grupo lo acepta y lo documenta
  en el informe antes/después. Es un volumen despreciable (0.04%).

#### Problema E2: normalización de texto (comillas/apóstrofos, puntuación, tildes)

El diagnóstico encontró miles de valores con comillas y apóstrofos en varias
variantes (`"`, `'` recto, `´` acento agudo, `` ` `` grave; ~2,987 registros),
además de guiones y paréntesis, y tildes usadas de forma inconsistente (3,227
valores con tilde y el resto sin tilde).

- **Regla:** normalización de texto explícita y conservadora, en este orden:
  1. recortar espacios inicio/fin y colapsar espacios múltiples;
  2. unificar las comillas/apóstrofos tipográficos a una sola forma
     (`´`, `` ` ``, `’` → `'`) y quitar comillas dobles envolventes;
  3. dejar la variable en mayúsculas (ya lo está) y en UTF-8.
  No se eliminan palabras ni se reordenan; solo se uniforma el "ruido" de
  puntuación. **No** se fuerza la restitución de tildes sobre el nombre
  mostrado (ver E3): las tildes se manejan solo en la clave de detección.
- **Por qué funcionará:** los chequeos de formato del diagnóstico (celda 3.1)
  cuantifican exactamente qué caracteres hay; las reglas atacan solo esos
  caracteres con reemplazos deterministas, sin tocar el contenido del nombre.
- **Riesgos:**
  - Alterar un nombre propio legítimo (p. ej. un apóstrofo que sí forma parte
    del nombre). Se mitiga limitando la regla a variantes tipográficas y
    conservando siempre el archivo crudo como fuente de verdad.
  - Problemas de encoding al escribir tildes/caracteres especiales. Se mitiga
    guardando en UTF-8 y documentando el encoding en el libro de códigos.

#### Problema E3: mismo nombre escrito de distintas formas (tildes / prefijo `INED`)

El diagnóstico mostró que ~970 "nombres base" (unos 5,031 registros) aparecen
escritos de más de una forma: con y sin tilde y con o sin el prefijo `INED`
(ej.: `INSTITUTO NACIONAL DE EDUCACION DIVERSIFICADA` /
`INSTITUTO NACIONAL DE EDUCACIÓN DIVERSIFICADA` /
`INED INSTITUTO NACIONAL DE EDUCACIÓN DIVERSIFICADA`).

- **Regla:** **no** unificar automáticamente los nombres mostrados. Se crea una
  **variable derivada auxiliar** `ESTABLECIMIENTO_NORM` (sin tildes, sin
  prefijo `INED`, sin puntuación, espacios colapsados) que se usa **solo como
  clave de detección/agrupación**, no para reemplazar el nombre original. Los
  casos de un mismo nombre base con varias formas se listan y la decisión de
  unificar o no se toma caso por caso y se documenta.
- **Por qué funcionará:** normalizar en una columna aparte permite detectar
  equivalencias sin destruir la escritura original de cada plantel, que puede
  ser la oficial. La lógica de `ESTABLECIMIENTO_NORM` es la misma
  `base_nombre` del diagnóstico, ya validada sobre los datos.
- **Riesgos:**
  - **Falsos positivos:** muchos nombres base son genéricos (institutos
    nacionales, colegios por cooperativa) y corresponden a planteles distintos.
    Por eso E3 **no** fusiona: la equivalencia de nombre se combina con
    `CODIGO`, `DIRECCION` y `TELEFONO` en E7 antes de decidir nada.
  - Que `ESTABLECIMIENTO_NORM` se confunda con el nombre real. Se mitiga
    documentándola en el libro de códigos como variable derivada de uso interno
    (justificación: por qué se creó, cómo se calcula, para qué sirve).

### 2.2 `DIRECCION`

#### Problema E4: faltantes y marcadores de nulo (87 registros, 0.73%)

76 celdas vacías (`NaN`) más 11 marcadores escritos como texto (`-`, `.`).

- **Regla:** unificar los marcadores de nulo a `NA` (usando `MARCADORES_NULO`,
  el mismo patrón del diagnóstico) y **no** imputar: los faltantes se conservan
  como `NA`.
- **Por qué funcionará:** el patrón de marcadores ya está validado en el
  diagnóstico; una dirección no puede deducirse de las demás columnas, así que
  imputarla generaría datos incorrectos.
- **Riesgos:** los faltantes de `DIRECCION` pasan de 76 a 87 al reclasificar los
  11 marcadores. Se reporta así en el informe antes/después.

#### Problema E5: normalización de texto (minúsculas, tildes, puntuación)

10 valores con minúsculas, ~1,160 con tildes y puntuación densa/variable
(guiones, puntos, comas, comillas).

- **Regla:** misma normalización conservadora de E2 aplicada a `DIRECCION`:
  recortar/colapsar espacios, pasar a mayúsculas consistentes, uniformar
  comillas/apóstrofos. La puntuación estructural (guiones y números de casa,
  p. ej. `3-59`) **no** se altera.
- **Por qué funcionará:** son transformaciones deterministas sobre caracteres
  puntuales que el diagnóstico ya cuantificó; el contenido informativo de la
  dirección se conserva.
- **Riesgos:** sobre-normalizar y perder un separador con significado. Se mitiga
  no tocando dígitos ni el guion entre números; solo se uniforma texto.

#### Problema E6: abreviaturas inconsistentes

La misma pieza de dirección se abrevia de varias maneras: `AVENIDA` (2,768) vs
`AVE`/`AVE.` (331); `ZONA` (5,213) vs `Z.` (11); además `CALLE` (3,675), `KM`
(268), `NO`/`NO.` (253) y `#` (23).

- **Regla:** estandarizar mediante un **diccionario explícito** de abreviaturas
  → forma completa (`AVE`/`AVE.` → `AVENIDA`, `Z.` → `ZONA`, `NO`/`NO.` → `NO.`,
  `#` → `NO.`, etc.), aplicado con expresiones regulares ancladas a **límites de
  palabra** (`\b`). No se tocan los números de casa ni de zona.
- **Por qué funcionará:** el diccionario cubre exactamente las variantes
  detectadas en el diagnóstico (celda 3.3) y el uso de `\b` evita reemplazos
  dentro de otras palabras (p. ej. `AVE` en `AVENIDA` no se vuelve a expandir).
- **Riesgos:**
  - **Sobre-corrección**: expandir una abreviatura donde no corresponde. Se
    mitiga con límites de palabra, un diccionario cerrado y revisión de una
    muestra tras aplicar la regla.
  - Direcciones muy libres donde la abreviatura es ambigua. En esos casos se
    conserva el valor y se marca; no se fuerza el reemplazo.

#### Nota (no es error): valores genéricos poco específicos

Direcciones como `CABECERA MUNICIPAL` (325), `BARRIO EL CENTRO`, `CALLE
PRINCIPAL`, `ZONA 1`… son válidas pero poco informativas.

- **Regla:** no se corrigen ni se eliminan; se **documentan** como limitación de
  cobertura/precisión de la variable en el libro de códigos.
- **Por qué:** son datos reales de la fuente; tratarlos como error sería
  inventar información. Solo limitan análisis geoespaciales finos.

### 2.3 Duplicados parciales (`ESTABLECIMIENTO` + `DIRECCION`)

#### Problema E7: pares candidatos por similitud dentro del mismo municipio

El diagnóstico (celda 3.4, RapidFuzz con bloqueo por `(DEPARTAMENTO,
MUNICIPIO)` y umbral de score ≥ 90) encontró +14,000 pares de nombres muy
similares; 5,307 con la **misma dirección** y 6,702 con el **mismo teléfono**.

- **Regla:** analizar los candidatos, **priorizando** los que además comparten
  `DIRECCION` o `TELEFONO` (los verdaderos sospechosos de duplicado real).
  Para cada caso se decide **conservar** (planteles distintos con nombre
  genérico) o **fusionar/anotar** (mismo plantel duplicado), y la decisión se
  documenta. **No se elimina ningún registro de forma automática**, como exige
  el enunciado.
- **Por qué funcionará:** el bloqueo por municipio evita comparaciones
  espurias entre departamentos y el cruce con `CODIGO`/`DIRECCION`/`TELEFONO`
  distingue nombres genéricos legítimos de duplicados reales; `CODIGO` es único
  (diagnóstico 1.5), así que sirve de árbitro.
- **Riesgos:**
  - **Falsos positivos** por nombres genéricos (la mayoría de los 14,000 pares):
    se mitiga con la evidencia de dirección/teléfono y la revisión manual.
  - **Falsos negativos** por debajo del umbral 90: se acepta como limitación y
    se documenta el umbral usado; puede bajarse y revisarse si hace falta.

### 2.4 Resumen de reglas (establecimiento y dirección)

| # | Variable | Problema | Regla | Registros afectados (esperados) |
|---|---|---|---|---|
| E1 | `ESTABLECIMIENTO` | faltantes | conservar `NA`, no imputar | 5 |
| E2 | `ESTABLECIMIENTO` | comillas/apóstrofos/puntuación/espacios | normalización de texto conservadora | ~2,987 |
| E3 | `ESTABLECIMIENTO` | mismo nombre escrito distinto (tildes / `INED`) | derivar `ESTABLECIMIENTO_NORM` para detectar; no unificar automáticamente | ~970 nombres base / 5,031 registros |
| E4 | `DIRECCION` | faltantes + marcadores (`-`, `.`) | unificar marcadores → `NA`, no imputar | 87 |
| E5 | `DIRECCION` | minúsculas / tildes / puntuación | normalización de texto conservadora | ~1,170 |
| E6 | `DIRECCION` | abreviaturas inconsistentes | diccionario explícito con límites de palabra | miles |
| E7 | `ESTABLECIMIENTO` + `DIRECCION` | duplicados parciales | revisión por similitud + `DIRECCION`/`TELEFONO`; decisión caso por caso, sin borrado automático | +14,000 pares candidatos |

Ninguna regla elimina filas de forma automática. Variable nueva:
`ESTABLECIMIENTO_NORM` (derivada, de uso interno para detección; justificada en
el libro de códigos). Los valores genéricos de `DIRECCION` se documentan como
limitación, no se corrigen.

## 3. Teléfono, director y supervisor (P3)

Variables cubiertas: `TELEFONO`, `SUPERVISOR` y `DIRECTOR`. El diagnóstico está
en [notebooks/01_diagnostico.ipynb](notebooks/01_diagnostico.ipynb), Sección 4.
El teléfono es un dato con formato esperado fijo, 8 dígitos según la numeración
de Guatemala, mientras que supervisor y director son nombres propios de
personas, así que sus problemas se parecen a los de la sección 2, tildes
inconsistentes y ruido de formato.

### 3.1 `TELEFONO`

#### Problema T1: valores faltantes (946 registros, 7.97%)

- **Regla:** no imputar, los faltantes se conservan como `NA`.
- **Por qué funcionará:** un número de teléfono no puede deducirse de las demás
  columnas, imputarlo inventaría datos de contacto falsos.
- **Riesgos:** ninguno relevante, solo se documenta la cobertura de la variable
  en el libro de códigos.

#### Problema T2: varios números por celda con separadores inconsistentes (212 registros)

203 celdas traen más de un número separado por guion, coma, espacio, barra o la
palabra Y, y 9 traen texto como `FAX`, `AL` o `ESTX`. También hay rangos
abreviados como `22202870-73`.

- **Regla:** extraer con una expresión regular todos los bloques de exactamente
  8 dígitos de la celda y unirlos con `;` como separador único. El texto
  (`Y`, `FAX`, `AL`) se descarta. Los fragmentos que no formen un número
  completo, como el `73` del rango `22202870-73`, se descartan porque
  reconstruirlos sería adivinar. Si la celda no contiene ningún bloque de 8
  dígitos queda `NA`.
- **Por qué funcionará:** el patrón estructural del diagnóstico (celda 4.2)
  muestra que todos los casos múltiples son combinaciones de bloques de dígitos
  con separadores variados, la extracción por regex los cubre todos con una
  sola regla determinista y el separador `;` deja la columna parseable.
- **Riesgos:**
  - Perder números de fax o extensiones. El grupo lo acepta, el crudo conserva
    el valor original y la decisión queda documentada.
  - Confundir un rango abreviado con dos números. La regla solo toma bloques
    completos de 8 dígitos, así que el fragmento corto se pierde pero nunca se
    inventa un número.

#### Problema T3: números de 7 dígitos o menos (46 registros)

34 celdas traen un número de 7 dígitos, la numeración vieja del país, y hay
valores de hasta 2 caracteres.

- **Regla:** convertir a `NA`. No se intenta completar el número agregando el
  prefijo actual.
- **Por qué funcionará:** el cambio a 8 dígitos en Guatemala no fue agregar un
  dígito fijo para todas las líneas, depende del tipo de línea y operador, así
  que cualquier reconstrucción sería inventar un número que puede pertenecer a
  otra persona.
- **Riesgos:** se pierden 46 teléfonos posiblemente recuperables a mano. Se
  acepta, quedan en el crudo y los faltantes de la variable suben, lo que se
  reporta en el informe antes y después.

#### Problema T4: números inválidos (7 registros)

3 celdas con `00000000` y 4 números de 8 dígitos que inician con 0 o 9,
prefijos que no existen en la numeración nacional.

- **Regla:** convertir a `NA`. La validación final exige que todo número de la
  columna limpia cumpla `^[2-8]\d{7}$`.
- **Por qué funcionará:** los prefijos válidos en Guatemala son 2 a 8
  (fijos 2-7, móviles 3-5, otros servicios 6-8), la regla identifica exactamente
  a los 7 casos sin tocar números legítimos.
- **Riesgos:** ninguno relevante, `00000000` es un relleno evidente y un número
  con prefijo inexistente no es marcable de todas formas.

#### Nota (no es error): números compartidos entre establecimientos

2,165 números se repiten en 6,515 filas, el extremo es `22067425` con 71
registros. Jornadas, planes o sedes del mismo plantel comparten teléfono.

- **Regla:** no se corrige nada, se documenta en el libro de códigos que el
  teléfono no sirve como identificador único de establecimiento, aunque sí como
  evidencia de duplicado parcial en la regla E7.

### 3.2 `SUPERVISOR`

#### Problema S1: valores faltantes (536 registros, 4.52%)

535 celdas vacías más un falso valor hecho de guiones y un espacio interno que
el patrón general de marcadores no captura.

- **Regla:** ampliar el patrón de marcadores para aceptar espacios entre los
  guiones, unificar ese caso a `NA` y no imputar el resto.
- **Por qué funcionará:** el diagnóstico (celda 4.3) ya identificó el único
  valor que se escapa del patrón, con la ampliación la detección queda completa.
- **Riesgos:** ninguno relevante, el nombre de una persona no se puede imputar.

#### Problema S2: mismo nombre con y sin tildes (187 nombres base de 1,093)

El caso más grande es `CARLOS HUMBERTO GONZALEZ DE LEON` con 227 registros sin
tilde y 166 con tilde.

- **Regla:** agrupar por el nombre sin tildes (`sin_tildes`, la misma función
  del diagnóstico) y unificar cada grupo a una sola grafía, la variante con
  tildes cuando existe porque es la forma correcta del nombre, y si hay más de
  una variante con tilde, la más frecuente. La lista de 187 grupos se revisa
  manualmente antes de aplicar el mapeo.
- **Por qué funcionará:** el diagnóstico confirmó que ningún distrito de los
  1,680 tiene más de un supervisor, la relación distrito supervisor es uno a
  uno, así que dos grafías del mismo nombre base son la misma persona y no dos
  personas distintas que se confundan al quitar tildes.
- **Riesgos:**
  - Unificar a dos personas homónimas de distritos distintos. La unificación es
    solo de grafía del texto, no fusiona registros ni distritos, así que el
    riesgo real es mínimo y la revisión manual de la lista lo cubre.
  - Elegir la grafía equivocada como canónica. Se mitiga prefiriendo la forma
    con tildes y documentando el mapeo completo.

#### Problema S3: puntuación colgante y errores puntuales (~35 registros)

25 nombres terminan en punto o coma, 9 usan acento invertido o apóstrofo
(`ORTÌZ`, `O´NELL`) y hay un cero en lugar de la letra O en `ACEVED0`.

- **Regla:** quitar el punto o la coma final con regex, reemplazar los acentos
  invertidos por la tilde correcta (`Ì` → `Í`, `È` → `É`) y el apóstrofo `´`
  por `'`, igual que la regla E2. El caso `ACEVED0` → `ACEVEDO` se corrige con
  un mapeo explícito documentado.
- **Por qué funcionará:** son sustituciones deterministas de caracteres que no
  existen legítimamente al final o dentro de un nombre en español, y el volumen
  es tan pequeño que cada caso se puede verificar a mano.
- **Riesgos:** alterar un apellido extranjero legítimo. Se mitiga revisando los
  casos afectados, que son pocos, antes de aplicar.

### 3.3 `DIRECTOR`

#### Problema D1: faltantes y marcadores de nulo (2,147 registros, 18.1%)

1,732 celdas vacías, 411 marcadores capturados por el patrón general (rachas de
guiones, `SIN DATO`, puntos, `XXX`, `0`) y 4 variantes que se escapan
(`000000`, `0000000`, `SIN DATOS`, `SIN DATOS ( TEMPORAL TITULOS )`).

- **Regla:** ampliar el patrón de marcadores para cubrir ceros repetidos y
  `SIN DATOS` con o sin texto extra, unificar todo a `NA` y no imputar.
- **Por qué funcionará:** el desglose del diagnóstico (celda 4.4) enumeró todas
  las variantes presentes, el patrón ampliado las captura por completo y no hay
  nombres reales que empiecen con ceros o con la frase `SIN DATOS`.
- **Riesgos:** es la variable con más faltantes del dataset y la limpieza lo
  hace visible, los faltantes suben de 1,732 a 2,147. Es el comportamiento
  correcto y se reporta así en el informe antes y después.

#### Problema D2: títulos académicos pegados al nombre (20 registros)

Valores como `LICDA. DORIS ZUNUN CARRERA` o `PEM. JESÚS ÁNGEL TOLEDO`.

- **Regla:** remover el título con una regex anclada al inicio del valor sobre
  una lista cerrada (`PROF`, `LIC`, `LICDA`, `ING`, `PEM`, `DR`, `DRA`, con o
  sin punto), dejando solo el nombre.
- **Por qué funcionará:** la lista sale del propio diagnóstico, el ancla al
  inicio y el límite de palabra evitan tocar apellidos que contengan esas
  letras.
- **Riesgos:** perder la información del título. Se acepta, el título no es
  parte del nombre y la columna gana consistencia, el crudo lo conserva.

#### Problema D3: mismo nombre con y sin tildes (149 nombres base)

- **Regla:** misma unificación de grafía que S2, agrupar por nombre sin tildes
  y llevar cada grupo a una sola forma, con revisión manual de la lista.
- **Por qué funcionará:** la lógica ya está validada en `SUPERVISOR` y aquí
  también se unifica solo la escritura del texto.
- **Riesgos:** a diferencia del supervisor no hay una relación uno a uno con el
  distrito que garantice que dos grafías sean la misma persona, dos directores
  distintos pueden llamarse igual. Por eso la regla no fusiona registros ni
  deduce identidad, solo estandariza la escritura, y así se documenta.

#### Problema D4: ruido puntual (18 registros)

17 valores con acento invertido (`HÈCTOR`, `MARROQUÌN`) y uno con guiones
pegados al nombre (`----MARIA DEL ROSARIO LOPEZ ESCOBAR`).

- **Regla:** reemplazar `Ì` → `Í`, `È` → `É` y demás acentos invertidos por su
  tilde correcta, y quitar los guiones iniciales con una regex anclada al
  inicio.
- **Por qué funcionará:** el acento grave no existe en la ortografía del
  español, así que el reemplazo no tiene falsos positivos, y el patrón de
  guiones iniciales solo afecta al caso detectado.
- **Riesgos:** ninguno relevante, son sustituciones puntuales verificables a
  mano.

### 3.4 Resumen de reglas (teléfono, director y supervisor)

| # | Variable | Problema | Regla | Registros afectados (esperados) |
|---|---|---|---|---|
| T1 | `TELEFONO` | faltantes | conservar `NA`, no imputar | 946 |
| T2 | `TELEFONO` | varios números y separadores inconsistentes | extraer bloques de 8 dígitos, unir con `;` | 212 |
| T3 | `TELEFONO` | números de 7 dígitos o menos | convertir a `NA`, no reconstruir | 46 |
| T4 | `TELEFONO` | inválidos (`00000000`, prefijo 0 o 9) | convertir a `NA`, validar `^[2-8]\d{7}$` | 7 |
| S1 | `SUPERVISOR` | faltantes + marcador de guiones con espacio | ampliar patrón, unificar a `NA` | 536 |
| S2 | `SUPERVISOR` | mismo nombre con y sin tildes | unificar grafía por nombre base, revisión manual | 187 nombres base |
| S3 | `SUPERVISOR` | puntuación colgante, acentos invertidos, `ACEVED0` | sustituciones deterministas + mapeo explícito | ~35 |
| D1 | `DIRECTOR` | faltantes + marcadores (`---`, `SIN DATO`, `000000`...) | ampliar patrón, unificar a `NA`, no imputar | 2,147 |
| D2 | `DIRECTOR` | títulos académicos (`LICDA.`, `PEM.`) | regex anclada con lista cerrada | 20 |
| D3 | `DIRECTOR` | mismo nombre con y sin tildes | unificar grafía por nombre base, revisión manual | 149 nombres base |
| D4 | `DIRECTOR` | acentos invertidos y guiones pegados | sustituciones puntuales | 18 |

Ninguna regla elimina filas y no se crean variables nuevas en esta sección. Los
teléfonos compartidos entre establecimientos se documentan como limitación en
el libro de códigos y sirven de evidencia para los duplicados parciales de la
regla E7.

## 4. Código y variables categóricas (P4)

### 4.1 `CODIGO`

#### Problema C1: validar que el código siga el patrón esperado

El diagnóstico mostró que todos los registros siguen la forma `NN-NN-NNNN-NN`.

- **Regla:** conservar `CODIGO` como texto y validar exactamente el patrón `^\d{2}-\d{2}-\d{4}-\d{2}$`.
- **Por qué funcionará:** el código funciona como llave primaria y no requiere recodificación.
- **Riesgos:** si la fuente cambia de estructura en una nueva extracción, la validación lo detectará de inmediato.

### 4.2 Variables categóricas de dominio cerrado

Variables cubiertas: `SECTOR`, `AREA`, `STATUS`, `MODALIDAD`, `JORNADA`, `PLAN`, `NIVEL`.

- **Regla general:** recortar espacios, colapsar espacios múltiples y mantener mayúsculas consistentes. No se recodifican categorías válidas ni se inventan sinónimos no observados en la fuente.
- **Por qué funcionará:** el diagnóstico mostró que los dominios son cerrados y ya llegan uniformes en la fuente cruda.
- **Riesgos:** mínimos; la única precaución es no alterar valores válidos como `INTERCALADO` en `PLAN`, que se conserva tal como aparece en la fuente.

### 4.3 Resumen de reglas (código y categorías)

| # | Variable | Problema | Regla | Registros afectados (esperados) |
|---|---|---|---|---|
| C1 | `CODIGO` | validar formato | conservar como texto y validar patrón fijo | 0 |
| C2 | `SECTOR` | normalización mínima | recortar/colapsar espacios y preservar categorías válidas | 0 |
| C3 | `AREA` | normalización mínima | recortar/colapsar espacios y preservar categorías válidas | 0 |
| C4 | `STATUS` | normalización mínima | recortar/colapsar espacios y preservar categorías válidas | 0 |
| C5 | `MODALIDAD` | normalización mínima | recortar/colapsar espacios y preservar categorías válidas | 0 |
| C6 | `JORNADA` | normalización mínima | recortar/colapsar espacios y preservar categorías válidas | 0 |
| C7 | `PLAN` | normalización mínima | recortar/colapsar espacios y preservar categorías válidas | 0 |
| C8 | `NIVEL` | valor constante | conservar `DIVERSIFICADO` | 0 |

La implementación reproducible del plan completo está en [src/clean_mineduc.py](src/clean_mineduc.py).
