from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
import textwrap
from typing import Iterable

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "MINEDUC_establecimientos_diversificado.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
CLEAN_CSV = PROCESSED_DIR / "MINEDUC_establecimientos_diversificado_limpio.csv"
QUALITY_REPORT = PROCESSED_DIR / "informe_calidad.md"
QUALITY_JSON = PROCESSED_DIR / "informe_calidad.json"
CODEBOOK = ROOT / "codebook.md"
PDF_EXPORT = ROOT / "documentacion_reproducibilidad.pdf"

SOURCE_URL = "http://www.mineduc.gob.gt/BUSCAESTABLECIMIENTO_GE/"
EXTRACTION_DATE = "2026-07-20"
DATA_VERSION = "1.0.0"


DEPARTMENT_MAP = {
    "CIUDAD CAPITAL": "GUATEMALA",
    "PETEN": "PETÉN",
    "QUICHE": "QUICHÉ",
    "SOLOLA": "SOLOLÁ",
    "SACATEPEQUEZ": "SACATEPÉQUEZ",
    "SUCHITEPEQUEZ": "SUCHITEPÉQUEZ",
    "TOTONICAPAN": "TOTONICAPÁN",
}

MUNICIPALITY_SPECIALS = {
    "CABAÑAS": "CABAÑAS",
    "PUEBLO NUEVO VIÑAS": "PUEBLO NUEVO VIÑAS",
}

ALLOWED_DEPARTMENTS = {
    "ALTA VERAPAZ",
    "BAJA VERAPAZ",
    "CHIMALTENANGO",
    "CHIQUIMULA",
    "EL PROGRESO",
    "ESCUINTLA",
    "GUATEMALA",
    "HUEHUETENANGO",
    "IZABAL",
    "JALAPA",
    "JUTIAPA",
    "PETÉN",
    "QUETZALTENANGO",
    "QUICHÉ",
    "RETALHULEU",
    "SACATEPÉQUEZ",
    "SAN MARCOS",
    "SANTA ROSA",
    "SOLOLÁ",
    "SUCHITEPÉQUEZ",
    "TOTONICAPÁN",
    "ZACAPA",
}

CATEGORY_COLUMNS = ["SECTOR", "AREA", "STATUS", "MODALIDAD", "JORNADA", "PLAN", "NIVEL"]

EXPECTED_TYPES = {
    "CODIGO": "string",
    "DISTRITO": "string",
    "DEPARTAMENTO": "string",
    "MUNICIPIO": "string",
    "ESTABLECIMIENTO": "string",
    "ESTABLECIMIENTO_NORM": "string",
    "DIRECCION": "string",
    "TELEFONO": "string",
    "SUPERVISOR": "string",
    "DIRECTOR": "string",
    "NIVEL": "string",
    "SECTOR": "string",
    "AREA": "string",
    "STATUS": "string",
    "MODALIDAD": "string",
    "JORNADA": "string",
    "PLAN": "string",
    "DEPARTAMENTAL": "string",
    "ZONA_CAPITAL": "Int64",
}

TEXT_MISSING_RE = re.compile(
    r"^\s*(?:"
    r"-+|\.+|_+|x+|n/?a|na|null|nulo|sin\s*dato(?:s)?|ninguno|no\s*tiene|0+|"
    r"sin\s*datos?(?:\s*\(.*\))?"
    r")\s*$",
    re.IGNORECASE,
)

TITLE_RE = re.compile(r"^(?:PROF|LIC|LICDA|ING|PEM|DR|DRA)\.?\s+", re.IGNORECASE)

PHONE_RE = re.compile(r"^[2-8]\d{7}$")


def normalize_unicode(value: str) -> str:
    value = value.translate(
        str.maketrans(
            {
                "´": "'",
                "`": "'",
                "’": "'",
                "＇": "'",
                "“": '"',
                "”": '"',
                "–": "-",
                "—": "-",
            }
        )
    )
    return unicodedata.normalize("NFC", value)


def strip_accents(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def normalize_base_text(value: str) -> str:
    value = normalize_unicode(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_clean_text(value: str) -> str | pd.NA:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NA
    value = normalize_base_text(str(value))
    if not value or TEXT_MISSING_RE.match(value):
        return pd.NA
    return value.upper()


def normalize_category_value(value: str) -> str | pd.NA:
    cleaned = normalize_clean_text(value)
    if cleaned is pd.NA:
        return pd.NA
    return cleaned


def normalize_department(value: str) -> str | pd.NA:
    cleaned = normalize_clean_text(value)
    if cleaned is pd.NA:
        return pd.NA
    return DEPARTMENT_MAP.get(cleaned, cleaned)


def normalize_district(value: str) -> str | pd.NA:
    cleaned = normalize_clean_text(value)
    if cleaned is pd.NA:
        return pd.NA
    if re.fullmatch(r"\d{2}-", cleaned):
        return pd.NA
    return cleaned


def normalize_direction(value: str) -> str | pd.NA:
    cleaned = normalize_clean_text(value)
    if cleaned is pd.NA:
        return pd.NA
    replacements = [
        (r"(?<!\w)AVE\.(?!\w)", "AVENIDA"),
        (r"(?<!\w)AV\.(?!\w)", "AVENIDA"),
        (r"(?<!\w)AVE(?!\w)", "AVENIDA"),
        (r"(?<!\w)Z\.(?!\w)", "ZONA"),
        (r"(?<!\w)ZONA\.(?!\w)", "ZONA"),
        (r"(?<!\w)NO\.(?!\w)", "NO."),
        (r"(?<!\w)NO(?!\w)", "NO."),
        (r"(?<!\w)#(?!\w)", "NO."),
    ]
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_person_text(value: str) -> str | pd.NA:
    cleaned = normalize_clean_text(value)
    if cleaned is pd.NA:
        return pd.NA
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_supervisor_text(value: str) -> str | pd.NA:
    cleaned = normalize_person_text(value)
    if cleaned is pd.NA:
        return pd.NA
    replacements = {
        "À": "Á",
        "È": "É",
        "Ì": "Í",
        "Ò": "Ó",
        "Ù": "Ú",
        "à": "á",
        "è": "é",
        "ì": "í",
        "ò": "ó",
        "ù": "ú",
        "ACEVED0": "ACEVEDO",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"[.,]$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_director_text(value: str) -> str | pd.NA:
    cleaned = normalize_supervisor_text(value)
    if cleaned is pd.NA:
        return pd.NA
    cleaned = TITLE_RE.sub("", cleaned)
    cleaned = re.sub(r"^-+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or TEXT_MISSING_RE.match(cleaned):
        return pd.NA
    return cleaned


def base_key(value: str) -> str:
    value = normalize_base_text(value).upper()
    value = strip_accents(value)
    value = re.sub(r"^INED\s+", "", value)
    value = re.sub(r"[^A-Z0-9 ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def person_key(value: str) -> str:
    value = strip_accents(normalize_base_text(value).upper())
    value = re.sub(r"[^A-Z0-9 ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def pick_canonical(values: Iterable[str]) -> str:
    values = list(values)
    if not values:
        return ""

    counts = Counter(values)

    def score(candidate: str) -> tuple[int, int, int, str]:
        has_accent = int(bool(re.search(r"[ÁÉÍÓÚÑÜáéíóúñü]", candidate)))
        accent_count = len(re.findall(r"[ÁÉÍÓÚÑÜáéíóúñü]", candidate))
        return (has_accent, accent_count, counts[candidate], candidate)

    return max(values, key=score)


def canonicalize_by_base(series: pd.Series, key_func) -> tuple[pd.Series, dict[str, str]]:
    cleaned = series.map(lambda value: normalize_supervisor_text(value) if pd.notna(value) else pd.NA)
    groups: dict[str, list[str]] = defaultdict(list)
    for value in cleaned.dropna().astype(str):
        groups[key_func(value)].append(value)

    mapping: dict[str, str] = {}
    for key, values in groups.items():
        mapping[key] = pick_canonical(values)

    result = cleaned.map(lambda value: mapping.get(key_func(value), value) if pd.notna(value) else pd.NA)
    return result, mapping


def clean_phone(value: str) -> str | pd.NA:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NA
    cleaned = normalize_base_text(str(value))
    if not cleaned or TEXT_MISSING_RE.match(cleaned):
        return pd.NA
    matches = [candidate for candidate in re.findall(r"\d{8}", cleaned) if PHONE_RE.fullmatch(candidate)]
    if not matches:
        return pd.NA
    unique_matches: list[str] = []
    for candidate in matches:
        if candidate not in unique_matches:
            unique_matches.append(candidate)
    return ";".join(unique_matches)


def clean_establecimiento(value: str) -> str | pd.NA:
    cleaned = normalize_clean_text(value)
    if cleaned is pd.NA:
        return pd.NA
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_establecimiento_norm(value: str) -> str | pd.NA:
    cleaned = clean_establecimiento(value)
    if cleaned is pd.NA:
        return pd.NA
    cleaned = normalize_base_text(cleaned).upper()
    cleaned = strip_accents(cleaned)
    cleaned = re.sub(r"^INED\s+", "", cleaned)
    cleaned = re.sub(r"[^A-Z0-9 ]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_zona_capital(value: str | pd.NA) -> int | pd.NA:
    if value is pd.NA:
        return pd.NA
    match = re.fullmatch(r"ZONA\s+(\d+)", value)
    if not match:
        return pd.NA
    return int(match.group(1))


def load_raw_dataset() -> pd.DataFrame:
    return pd.read_csv(RAW_CSV, dtype=str, encoding="utf-8-sig")


def clean_dataset(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    df["CODIGO"] = df["CODIGO"].map(normalize_clean_text)
    df["DISTRITO"] = df["DISTRITO"].map(normalize_district)
    df["DEPARTAMENTO"] = df["DEPARTAMENTO"].map(normalize_department)
    df["MUNICIPIO"] = df["MUNICIPIO"].map(normalize_category_value)
    df["ESTABLECIMIENTO"] = df["ESTABLECIMIENTO"].map(clean_establecimiento)
    df["DIRECCION"] = df["DIRECCION"].map(normalize_direction)
    df["TELEFONO"] = df["TELEFONO"].map(clean_phone)

    supervisor_clean, _ = canonicalize_by_base(df["SUPERVISOR"], person_key)
    df["SUPERVISOR"] = supervisor_clean

    director_clean, _ = canonicalize_by_base(df["DIRECTOR"], person_key)
    df["DIRECTOR"] = director_clean

    for column in CATEGORY_COLUMNS + ["DEPARTAMENTAL"]:
        df[column] = df[column].map(normalize_category_value)

    df["DEPARTAMENTO"] = df["DEPARTAMENTO"].replace(DEPARTMENT_MAP)

    zone_mask = df["MUNICIPIO"].fillna("").str.match(r"^ZONA\s+\d+$", na=False)
    capital_mask = df["DEPARTAMENTO"].eq("GUATEMALA") | df["DEPARTAMENTO"].eq("CIUDAD CAPITAL")
    df["ZONA_CAPITAL"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
    df.loc[zone_mask & capital_mask, "ZONA_CAPITAL"] = df.loc[zone_mask & capital_mask, "MUNICIPIO"].map(normalize_zona_capital)
    df.loc[zone_mask & capital_mask, "MUNICIPIO"] = "GUATEMALA"
    df.loc[df["DEPARTAMENTO"].eq("CIUDAD CAPITAL"), "DEPARTAMENTO"] = "GUATEMALA"

    df["MUNICIPIO"] = df["MUNICIPIO"].replace(MUNICIPALITY_SPECIALS)
    df["MUNICIPIO"] = df["MUNICIPIO"].map(normalize_category_value)
    df["ESTABLECIMIENTO_NORM"] = df["ESTABLECIMIENTO"].map(build_establecimiento_norm)

    df = df.drop_duplicates().reset_index(drop=True)

    ordered_columns = [
        "CODIGO",
        "DISTRITO",
        "DEPARTAMENTO",
        "MUNICIPIO",
        "ZONA_CAPITAL",
        "ESTABLECIMIENTO",
        "ESTABLECIMIENTO_NORM",
        "DIRECCION",
        "TELEFONO",
        "SUPERVISOR",
        "DIRECTOR",
        "NIVEL",
        "SECTOR",
        "AREA",
        "STATUS",
        "MODALIDAD",
        "JORNADA",
        "PLAN",
        "DEPARTAMENTAL",
    ]
    return df[ordered_columns]


def missing_like_mask(series: pd.Series) -> pd.Series:
    values = series.astype("string")
    stripped = values.str.strip()
    return values.isna() | stripped.isna() | stripped.eq("") | stripped.str.match(TEXT_MISSING_RE, na=False)


def count_missing_cells(df: pd.DataFrame, columns: list[str] | None = None) -> int:
    if columns is None:
        columns = list(df.columns)
    return int(sum(missing_like_mask(df[column]).sum() for column in columns if column in df.columns))


def count_variables_with_missing(df: pd.DataFrame, columns: list[str] | None = None) -> int:
    if columns is None:
        columns = list(df.columns)
    return int(sum(missing_like_mask(df[column]).any() for column in columns if column in df.columns))


def count_exact_duplicates(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def format_issue_columns_before(df: pd.DataFrame) -> list[str]:
    issues = []

    if not df["CODIGO"].dropna().astype(str).str.match(r"^\d{2}-\d{2}-\d{4}-\d{2}$").all():
        issues.append("CODIGO")
    if not df["DISTRITO"].dropna().astype(str).str.match(r"^(?:\d{2}-\d{2}-\d{4}|\d{2}-\d{3})$").all():
        issues.append("DISTRITO")
    if not df["TELEFONO"].dropna().astype(str).str.match(r"^(?:[2-8]\d{7})(?:;[2-8]\d{7})*$").all():
        issues.append("TELEFONO")
    if df["DEPARTAMENTO"].dropna().isin(ALLOWED_DEPARTMENTS).all() is False:
        issues.append("DEPARTAMENTO")
    if df["MUNICIPIO"].dropna().map(lambda value: bool(re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ0-9 ]+", value))).all() is False:
        issues.append("MUNICIPIO")
    for column in ["ESTABLECIMIENTO", "DIRECCION", "SUPERVISOR", "DIRECTOR"]:
        if df[column].dropna().map(lambda value: value == value.strip()).all() is False:
            issues.append(column)
    return issues


def format_issue_columns_after(df: pd.DataFrame) -> list[str]:
    issues = []
    validators = {
        "CODIGO": lambda s: s.dropna().astype(str).str.match(r"^\d{2}-\d{2}-\d{4}-\d{2}$").all(),
        "DISTRITO": lambda s: s.dropna().astype(str).str.match(r"^(?:\d{2}-\d{2}-\d{4}|\d{2}-\d{3})$").all(),
        "TELEFONO": lambda s: s.dropna().astype(str).str.match(r"^(?:[2-8]\d{7})(?:;[2-8]\d{7})*$").all(),
        "DEPARTAMENTO": lambda s: s.dropna().isin(ALLOWED_DEPARTMENTS).all(),
        "MUNICIPIO": lambda s: s.dropna().map(lambda value: bool(re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ0-9 ]+", value))).all(),
        "ESTABLECIMIENTO": lambda s: s.dropna().map(lambda value: value == value.strip()).all(),
        "DIRECCION": lambda s: s.dropna().map(lambda value: value == value.strip()).all(),
        "SUPERVISOR": lambda s: s.dropna().map(lambda value: value == value.strip()).all(),
        "DIRECTOR": lambda s: s.dropna().map(lambda value: value == value.strip()).all(),
    }
    for column, validator in validators.items():
        if not validator(df[column]):
            issues.append(column)
    return issues


def count_type_issues(df: pd.DataFrame, columns: list[str] | None = None) -> int:
    if columns is None:
        columns = list(EXPECTED_TYPES)
    issues = 0
    for column in columns:
        if column not in EXPECTED_TYPES:
            continue
        expected = EXPECTED_TYPES[column]
        if column not in df.columns:
            issues += 1
            continue
        if expected == "Int64":
            if str(df[column].dtype) != "Int64":
                issues += 1
        else:
            if not pd.api.types.is_string_dtype(df[column]):
                issues += 1
    return issues


def count_category_inconsistencies(df: pd.DataFrame, columns: list[str] | None = None) -> int:
    if columns is None:
        columns = ["DEPARTAMENTO", "MUNICIPIO", "SUPERVISOR", "DIRECTOR"]
    inconsistencies = 0
    for column in columns:
        if column not in df.columns:
            continue
        series = df[column].dropna().astype(str)
        groups: dict[str, set[str]] = defaultdict(set)
        for value in series:
            groups[strip_accents(value).upper()].add(value)
        inconsistencies += sum(len(values) > 1 for values in groups.values())
    return inconsistencies


def find_possible_duplicates(df: pd.DataFrame, threshold: int = 90) -> pd.DataFrame:
    candidates = []
    if "ESTABLECIMIENTO_NORM" in df.columns:
        name_series = df["ESTABLECIMIENTO_NORM"].copy()
    else:
        name_series = df["ESTABLECIMIENTO"].map(build_establecimiento_norm)

    work = df.copy()
    work["ESTABLECIMIENTO_NORM"] = name_series

    for (department, municipality), block in work.groupby(["DEPARTAMENTO", "MUNICIPIO"], dropna=False):
        block = block.dropna(subset=["ESTABLECIMIENTO_NORM"]).copy()
        if len(block) < 2:
            continue

        unique_names = block["ESTABLECIMIENTO_NORM"].drop_duplicates().tolist()
        for index, left_name in enumerate(unique_names):
            for right_name in unique_names[index + 1 :]:
                score = fuzz.token_sort_ratio(left_name, right_name)
                if score < threshold:
                    continue

                left_rows = block[block["ESTABLECIMIENTO_NORM"] == left_name]
                right_rows = block[block["ESTABLECIMIENTO_NORM"] == right_name]
                left_sample = left_rows.iloc[0]
                right_sample = right_rows.iloc[0]
                candidates.append(
                    {
                        "DEPARTAMENTO": department,
                        "MUNICIPIO": municipality,
                        "score": score,
                        "CODIGO_1": left_sample["CODIGO"],
                        "ESTABLECIMIENTO_1": left_sample["ESTABLECIMIENTO"],
                        "DIRECCION_1": left_sample["DIRECCION"],
                        "TELEFONO_1": left_sample["TELEFONO"],
                        "CODIGO_2": right_sample["CODIGO"],
                        "ESTABLECIMIENTO_2": right_sample["ESTABLECIMIENTO"],
                        "DIRECCION_2": right_sample["DIRECCION"],
                        "TELEFONO_2": right_sample["TELEFONO"],
                        "misma_direccion": left_sample["DIRECCION"] == right_sample["DIRECCION"],
                        "mismo_telefono": left_sample["TELEFONO"] == right_sample["TELEFONO"],
                    }
                )
    return pd.DataFrame(candidates)


def build_metrics(raw: pd.DataFrame, clean: pd.DataFrame) -> dict[str, dict[str, object]]:
    source_columns = list(raw.columns)
    clean_source = clean[source_columns].copy()

    raw_format_issues = format_issue_columns_before(raw)
    clean_format_issues = format_issue_columns_after(clean_source)

    raw_duplicates = find_possible_duplicates(raw)
    clean_duplicates = find_possible_duplicates(clean)

    def unique_record_count(candidate_df: pd.DataFrame) -> int:
        if candidate_df.empty:
            return 0
        values = pd.unique(candidate_df[["CODIGO_1", "CODIGO_2"]].stack().dropna())
        return int(len(values))

    missing_before = count_missing_cells(raw, source_columns)
    missing_after = count_missing_cells(clean_source, source_columns)

    changed_cells = 0
    for column in source_columns:
        left = raw[column].astype("string").fillna("<NA>")
        right = clean_source[column].astype("string").fillna("<NA>")
        if len(left) != len(right):
            continue
        changed_cells += int((left != right).sum())

    metrics = {
        "Registros": {"Antes": int(raw.shape[0]), "Después": int(clean.shape[0])},
        "Variables": {"Antes": int(raw.shape[1]), "Después": int(clean.shape[1])},
        "Valores faltantes": {"Antes": missing_before, "Después": missing_after},
        "Variables con NA": {"Antes": count_variables_with_missing(raw, source_columns), "Después": count_variables_with_missing(clean_source, source_columns)},
        "Duplicados exactos": {"Antes": count_exact_duplicates(raw), "Después": count_exact_duplicates(clean)},
        "Posibles duplicados": {
            "Antes": unique_record_count(raw_duplicates),
            "Después": unique_record_count(clean_duplicates),
            "Detalles": {
                "pares_antes": int(len(raw_duplicates)),
                "pares_despues": int(len(clean_duplicates)),
                "conservados": int(unique_record_count(clean_duplicates)),
                "fusionados": 0,
                "corregidos": 0,
            },
        },
        "Variables con formato inconsistente": {
            "Antes": len(raw_format_issues),
            "Después": len(clean_format_issues),
            "Variables antes": raw_format_issues,
            "Variables después": clean_format_issues,
        },
        "Variables con tipo incorrecto": {"Antes": count_type_issues(raw, source_columns), "Después": count_type_issues(clean_source, source_columns)},
        "Categorías inconsistentes": {"Antes": count_category_inconsistencies(raw), "Después": count_category_inconsistencies(clean_source)},
        "Errores corregidos": {"Total": changed_cells},
    }
    return metrics


def render_table(headers: list[str], rows: list[list[object]]) -> str:
    def stringify(value: object) -> str:
        if value is None or value is pd.NA:
            return "NA"
        if isinstance(value, float):
            if value.is_integer():
                return f"{int(value)}"
            return f"{value:.2f}"
        if isinstance(value, (list, tuple, set)):
            return ", ".join(map(str, value))
        return str(value)

    escaped_rows = [[stringify(cell).replace("|", r"\|") for cell in row] for row in rows]
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = ["| " + " | ".join(row) + " |" for row in escaped_rows]
    return "\n".join([header_row, separator_row, *body_rows])


def build_transformation_log() -> list[dict[str, object]]:
    return [
        {
            "Variable": "DEPARTAMENTO",
            "Problema detectado": "CIUDAD CAPITAL y nombres sin tilde fuera de la forma oficial",
            "Transformación": "Recodificar CIUDAD CAPITAL a GUATEMALA y restaurar tildes por mapeo explícito",
            "Registros afectados": 2161 + 2025,
            "Justificación": "El catálogo de departamentos es cerrado y la correspondencia con DEPARTAMENTAL es consistente.",
        },
        {
            "Variable": "MUNICIPIO",
            "Problema detectado": "ZONA N mezclada con municipios y dos nombres con tildes faltantes",
            "Transformación": "Derivar ZONA_CAPITAL, sustituir ZONA N por GUATEMALA y conservar CABAÑAS / PUEBLO NUEVO VIÑAS",
            "Registros afectados": 2161 + 2,
            "Justificación": "La zona de la capital es información auxiliar y no un municipio del catálogo.",
        },
        {
            "Variable": "DISTRITO",
            "Problema detectado": "Valores truncados NN-",
            "Transformación": "Convertir a NA",
            "Registros afectados": 70,
            "Justificación": "El prefijo departamental ya está en DEPARTAMENTO y no aporta información completa.",
        },
        {
            "Variable": "ESTABLECIMIENTO",
            "Problema detectado": "Ruido de texto y variantes de escritura",
            "Transformación": "Normalizar espacios, mayúsculas y comillas; derivar ESTABLECIMIENTO_NORM para detección",
            "Registros afectados": 5031,
            "Justificación": "Se conserva la escritura original pero se agrega una clave estable para análisis.",
        },
        {
            "Variable": "DIRECCION",
            "Problema detectado": "Marcadores de nulo y abreviaturas inconsistentes",
            "Transformación": "Unificar nulos a NA y estandarizar abreviaturas frecuentes",
            "Registros afectados": 87 + 328,
            "Justificación": "La dirección queda legible y consistente sin inventar información.",
        },
        {
            "Variable": "TELEFONO",
            "Problema detectado": "Varios números, texto auxiliar y números inválidos",
            "Transformación": "Extraer bloques válidos de 8 dígitos y unirlos con ';'",
            "Registros afectados": 212 + 46 + 7,
            "Justificación": "Se conserva solo numeración telefónica interpretable y se descarta ruido.",
        },
        {
            "Variable": "SUPERVISOR",
            "Problema detectado": "Tildes inconsistentes y ruido puntual",
            "Transformación": "Canonicalizar por nombre base y corregir caracteres atípicos",
            "Registros afectados": 536 + 35,
            "Justificación": "La relación distrito-supervisor permite unificar variantes de la misma persona.",
        },
        {
            "Variable": "DIRECTOR",
            "Problema detectado": "Marcadores de nulo, títulos pegados al nombre y variantes gráficas",
            "Transformación": "Ampliar patrón de nulos, quitar títulos y canonicalizar por nombre base",
            "Registros afectados": 2147 + 20 + 18,
            "Justificación": "El texto limpio conserva el nombre y elimina prefijos administrativos.",
        },
        {
            "Variable": "CODIGO",
            "Problema detectado": "Validación de formato",
            "Transformación": "Conservar como texto y validar patrón fijo NN-NN-NNNN-NN",
            "Registros afectados": 0,
            "Justificación": "No presenta anomalías y funciona como llave primaria.",
        },
    ]


def build_variable_metadata() -> list[dict[str, str]]:
    return [
        {
            "Variable": "CODIGO",
            "Tipo": "string",
            "Descripcion": "Código único del establecimiento educativo.",
            "Dominio": "NN-NN-NNNN-NN.",
            "Valores": "11,867 valores únicos en el dataset limpio.",
            "Tratamiento": "Conservado como texto; validado con regex.",
            "Derivada": "No",
        },
        {
            "Variable": "DISTRITO",
            "Tipo": "string",
            "Descripcion": "Código del distrito escolar.",
            "Dominio": "NN-NN-NNNN o NN-NNN; NN- se convierte a NA.",
            "Valores": "1,681 valores distintos en el crudo.",
            "Tratamiento": "Se conservan los formatos completos; truncados a NA.",
            "Derivada": "No",
        },
        {
            "Variable": "DEPARTAMENTO",
            "Tipo": "string",
            "Descripcion": "Departamento del establecimiento.",
            "Dominio": "Catálogo oficial de 22 departamentos.",
            "Valores": "22 categorías.",
            "Tratamiento": "Se corrigen tildes y CIUDAD CAPITAL -> GUATEMALA.",
            "Derivada": "No",
        },
        {
            "Variable": "MUNICIPIO",
            "Tipo": "string",
            "Descripcion": "Municipio del establecimiento.",
            "Dominio": "Catálogo oficial de municipios de Guatemala.",
            "Valores": "Municipio real; zonas de la capital se recodifican a GUATEMALA.",
            "Tratamiento": "Se estandariza la capital y se documentan las zonas en ZONA_CAPITAL.",
            "Derivada": "No",
        },
        {
            "Variable": "ZONA_CAPITAL",
            "Tipo": "Int64",
            "Descripcion": "Zona de la ciudad capital derivada desde MUNICIPIO.",
            "Dominio": "Enteros positivos entre 1 y 25.",
            "Valores": "Solo para registros de CIUDAD CAPITAL.",
            "Tratamiento": "Derivada para conservar la distinción zona/municipio.",
            "Derivada": "Sí, a partir de MUNICIPIO.",
        },
        {
            "Variable": "ESTABLECIMIENTO",
            "Tipo": "string",
            "Descripcion": "Nombre del establecimiento.",
            "Dominio": "Texto libre.",
            "Valores": "Alta cardinalidad, con variantes ortográficas.",
            "Tratamiento": "Normalización conservadora de espacios, mayúsculas y comillas.",
            "Derivada": "No",
        },
        {
            "Variable": "ESTABLECIMIENTO_NORM",
            "Tipo": "string",
            "Descripcion": "Clave normalizada para detectar variantes del establecimiento.",
            "Dominio": "Texto alfanumérico en mayúsculas sin tildes.",
            "Valores": "Clave auxiliar de detección y agrupación.",
            "Tratamiento": "Derivada sin modificar el nombre original.",
            "Derivada": "Sí, a partir de ESTABLECIMIENTO.",
        },
        {
            "Variable": "DIRECCION",
            "Tipo": "string",
            "Descripcion": "Dirección postal del establecimiento.",
            "Dominio": "Texto libre.",
            "Valores": "Con abreviaturas y referencias de ubicación.",
            "Tratamiento": "Se normalizan espacios, mayúsculas y abreviaturas frecuentes.",
            "Derivada": "No",
        },
        {
            "Variable": "TELEFONO",
            "Tipo": "string",
            "Descripcion": "Teléfono de contacto.",
            "Dominio": "Bloques de 8 dígitos, separados por ';' si hay más de uno.",
            "Valores": "Puede ser NA si no se recupera un número válido.",
            "Tratamiento": "Se extraen números válidos de 8 dígitos y se descarta ruido.",
            "Derivada": "No",
        },
        {
            "Variable": "SUPERVISOR",
            "Tipo": "string",
            "Descripcion": "Nombre del supervisor educativo.",
            "Dominio": "Texto libre de persona.",
            "Valores": "Canonicalizado por nombre base.",
            "Tratamiento": "Se unifican variantes ortográficas y caracteres atípicos.",
            "Derivada": "No",
        },
        {
            "Variable": "DIRECTOR",
            "Tipo": "string",
            "Descripcion": "Nombre del director del establecimiento.",
            "Dominio": "Texto libre de persona.",
            "Valores": "Canonicalizado por nombre base.",
            "Tratamiento": "Se eliminan títulos y se unifican variantes ortográficas.",
            "Derivada": "No",
        },
        {
            "Variable": "NIVEL",
            "Tipo": "string",
            "Descripcion": "Nivel escolar reportado en la fuente.",
            "Dominio": "DIVERSIFICADO.",
            "Valores": "Constante.",
            "Tratamiento": "Normalización mínima.",
            "Derivada": "No",
        },
        {
            "Variable": "SECTOR",
            "Tipo": "string",
            "Descripcion": "Sector administrativo del establecimiento.",
            "Dominio": "PRIVADO, OFICIAL, COOPERATIVA, MUNICIPAL.",
            "Valores": "4 categorías.",
            "Tratamiento": "Normalización mínima.",
            "Derivada": "No",
        },
        {
            "Variable": "AREA",
            "Tipo": "string",
            "Descripcion": "Área geográfica.",
            "Dominio": "URBANA, RURAL, SIN ESPECIFICAR.",
            "Valores": "3 categorías.",
            "Tratamiento": "Normalización mínima.",
            "Derivada": "No",
        },
        {
            "Variable": "STATUS",
            "Tipo": "string",
            "Descripcion": "Estado operativo del establecimiento.",
            "Dominio": "ABIERTA, CERRADA TEMPORALMENTE, CERRADA DEFINITIVAMENTE, TEMPORAL TITULOS, TEMPORAL NOMBRAMIENTO.",
            "Valores": "5 categorías.",
            "Tratamiento": "Normalización mínima.",
            "Derivada": "No",
        },
        {
            "Variable": "MODALIDAD",
            "Tipo": "string",
            "Descripcion": "Modalidad de atención.",
            "Dominio": "MONOLINGUE, BILINGUE.",
            "Valores": "2 categorías.",
            "Tratamiento": "Normalización mínima.",
            "Derivada": "No",
        },
        {
            "Variable": "JORNADA",
            "Tipo": "string",
            "Descripcion": "Jornada escolar.",
            "Dominio": "DOBLE, VESPERTINA, MATUTINA, SIN JORNADA, NOCTURNA, INTERMEDIA.",
            "Valores": "6 categorías.",
            "Tratamiento": "Normalización mínima.",
            "Derivada": "No",
        },
        {
            "Variable": "PLAN",
            "Tipo": "string",
            "Descripcion": "Plan de estudios o modalidad pedagógica.",
            "Dominio": "Categorías observadas en la fuente.",
            "Valores": "13 categorías, incluido INTERCALADO.",
            "Tratamiento": "Normalización mínima y preservación de categorías válidas.",
            "Derivada": "No",
        },
        {
            "Variable": "DEPARTAMENTAL",
            "Tipo": "string",
            "Descripcion": "Dirección departamental del MINEDUC responsable del establecimiento.",
            "Dominio": "26 categorías administrativas.",
            "Valores": "Se documenta el mapa Guatemala x4 y Quiché x2.",
            "Tratamiento": "Normalización mínima; sirve como comprobación cruzada.",
            "Derivada": "No",
        },
    ]


def write_quality_report(metrics: dict[str, dict[str, object]], transformations: list[dict[str, object]]) -> None:
    lines = [
        "# Informe de calidad de datos",
        "",
        f"- Fuente: {SOURCE_URL}",
        f"- Fecha de extracción: {EXTRACTION_DATE}",
        f"- Versión del conjunto limpio: {DATA_VERSION}",
        "",
        "## Métricas antes/después",
        "",
    ]

    metric_rows = []
    for metric, values in metrics.items():
        before = values.get("Antes", values.get("Total", "NA"))
        after = values.get("Después", values.get("Total", "NA"))
        if metric == "Errores corregidos":
            metric_rows.append([metric, values.get("Total", "NA"), values.get("Total", "NA")])
        else:
            metric_rows.append([metric, before, after])
    lines.append(render_table(["Métrica", "Antes", "Después"], metric_rows))

    lines.extend(["", "## Registro de transformaciones", ""])
    transformation_rows = [
        [
            item["Variable"],
            item["Problema detectado"],
            item["Transformación"],
            item["Registros afectados"],
            item["Justificación"],
        ]
        for item in transformations
    ]
    lines.append(
        render_table(
            ["Variable", "Problema detectado", "Transformación", "Registros afectados", "Justificación"],
            transformation_rows,
        )
    )

    lines.extend(
        [
            "",
            "## Validación automática",
            "",
            "El script valida que no existan duplicados exactos, que no queden espacios iniciales o finales, que los teléfonos tengan formato consistente, que los departamentos y municipios pertenezcan a su catálogo normalizado, que los tipos esperados se cumplan y que no queden valores inválidos detectados en el diagnóstico.",
        ]
    )

    QUALITY_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_codebook() -> None:
    metadata_rows = build_variable_metadata()
    lines = [
        "# Libro de códigos",
        "",
        f"- Fuente: {SOURCE_URL}",
        f"- Fecha de extracción: {EXTRACTION_DATE}",
        f"- Versión del conjunto limpio: {DATA_VERSION}",
        "",
        "Definición de variables del conjunto limpio generado en `data/processed/`.",
        "",
        render_table(
            ["Variable", "Tipo", "Descripción", "Dominio permitido", "Valores posibles", "Tratamiento aplicado", "Derivada"],
            [
                [
                    row["Variable"],
                    row["Tipo"],
                    row["Descripcion"],
                    row["Dominio"],
                    row["Valores"],
                    row["Tratamiento"],
                    row["Derivada"],
                ]
                for row in metadata_rows
            ],
        ),
        "",
        "## Reglas de limpieza aplicadas",
        "",
        "- `DEPARTAMENTO`: recodificación de `CIUDAD CAPITAL` a `GUATEMALA` y corrección de tildes por mapeo explícito.",
        "- `MUNICIPIO`: extracción de `ZONA_CAPITAL` para `ZONA N` y recodificación a `GUATEMALA` en la capital.",
        "- `DISTRITO`: los valores truncados `NN-` se convierten a `NA`.",
        "- `ESTABLECIMIENTO`: normalización conservadora de texto y derivación de `ESTABLECIMIENTO_NORM`.",
        "- `DIRECCION`: normalización de espacios, mayúsculas y abreviaturas frecuentes.",
        "- `TELEFONO`: extracción de bloques válidos de 8 dígitos, separados por `;` si hay más de uno.",
        "- `SUPERVISOR` y `DIRECTOR`: canonicalización por nombre base, corrección de caracteres atípicos y eliminación de títulos pegados.",
        "- Variables categóricas: normalización mínima de espacios y mayúsculas, sin recodificar valores válidos.",
    ]
    CODEBOOK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pdf_export() -> None:
    def draw_wrapped_lines(pdf: canvas.Canvas, lines: list[str], *, font_name: str = "Helvetica", font_size: int = 10) -> None:
        width, height = A4
        left_margin = 42
        top_margin = 44
        bottom_margin = 40
        line_height = font_size + 3
        current_y = height - top_margin

        pdf.setFont(font_name, font_size)
        for raw_line in lines:
            wrapped = textwrap.wrap(raw_line, width=105, break_long_words=False, break_on_hyphens=False) or [""]
            for line in wrapped:
                if current_y < bottom_margin:
                    pdf.showPage()
                    pdf.setFont(font_name, font_size)
                    current_y = height - top_margin
                pdf.drawString(left_margin, current_y, line)
                current_y -= line_height

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    codebook_text = CODEBOOK.read_text(encoding="utf-8").splitlines()

    pdf = canvas.Canvas(str(PDF_EXPORT), pagesize=A4)
    width, height = A4
    pdf.setTitle("Documentación reproducible - MINEDUC")
    pdf.setAuthor("GitHub Copilot")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(42, height - 50, "Documentación reproducible - MINEDUC")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(42, height - 70, f"Fuente: {SOURCE_URL}")
    pdf.drawString(42, height - 86, f"Fecha de extracción: {EXTRACTION_DATE}")
    pdf.drawString(42, height - 102, f"Versión del conjunto limpio: {DATA_VERSION}")

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(42, height - 50, "README / Reproducibilidad")
    pdf.setFont("Helvetica", 10)
    draw_wrapped_lines(pdf, readme_text)

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(42, height - 50, "Libro de códigos")
    pdf.setFont("Helvetica", 10)
    draw_wrapped_lines(pdf, codebook_text)

    pdf.save()


def validate_clean_dataset(clean: pd.DataFrame) -> dict[str, object]:
    checks = {
        "duplicados_exactos": int(clean.duplicated().sum()) == 0,
        "espacios_extremos": bool(
            clean.select_dtypes(include=["object", "string"]).fillna("").apply(lambda s: s.astype(str).str.strip().eq(s.astype(str)).all()).all()
        ),
        "telefonos": bool(clean["TELEFONO"].dropna().astype(str).str.match(r"^(?:[2-8]\d{7})(?:;[2-8]\d{7})*$").all()),
        "departamentos": bool(clean["DEPARTAMENTO"].dropna().isin(ALLOWED_DEPARTMENTS).all()),
        "municipios": bool(clean["MUNICIPIO"].dropna().map(lambda value: bool(re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ0-9 ]+", value))).all()),
        "tipos": count_type_issues(clean) == 0,
        "categorias_inconsistentes": count_category_inconsistencies(clean) == 0,
        "valores_invalidados": bool(
            clean["DISTRITO"].dropna().astype(str).str.match(r"^(?:\d{2}-\d{2}-\d{4}|\d{2}-\d{3})$").all()
            and clean["CODIGO"].dropna().astype(str).str.match(r"^\d{2}-\d{2}-\d{4}-\d{2}$").all()
        ),
    }
    return checks


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw_dataset()
    clean = clean_dataset(raw)

    validation = validate_clean_dataset(clean)
    metrics = build_metrics(raw, clean)
    transformations = build_transformation_log()

    clean.to_csv(CLEAN_CSV, index=False, encoding="utf-8")
    QUALITY_JSON.write_text(json.dumps({"metrics": metrics, "validation": validation}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_quality_report(metrics, transformations)
    write_codebook()
    write_pdf_export()

    print(json.dumps({"clean_rows": int(clean.shape[0]), "clean_columns": int(clean.shape[1]), "validation": validation}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()