"""
Conector de Google Sheets para ingesta de datos de ventas.

Flujo:
  1. Autenticación via Service Account (sin OAuth interactivo).
  2. Lectura del rango configurado.
  3. Normalización de columnas y tipos según config/schemas.py.
  4. Deduplicación por hash de fila (evita reprocesar en re-runs).
  5. Retorna un DataFrame limpio listo para el ETL.
"""

import hashlib
from datetime import datetime, timezone

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from loguru import logger

from config.schemas import REQUIRED_COLUMNS, SCHEMA_SALES, SHEETS_COLUMN_MAP

load_dotenv()

import os

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetsClient:
    """Lee y normaliza datos de ventas desde Google Sheets."""

    def __init__(
        self,
        credentials_path: str | None = None,
        spreadsheet_id: str | None = None,
        sheet_name: str | None = None,
    ):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.spreadsheet_id = spreadsheet_id or os.getenv("SPREADSHEET_ID")
        self.sheet_name = sheet_name or os.getenv("SHEET_NAME", "Ventas")
        self._client: gspread.Client | None = None

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                import json
                creds = Credentials.from_service_account_info(
                    json.loads(creds_json), scopes=SCOPES
                )
            elif self.credentials_path and os.path.exists(self.credentials_path):
                creds = Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES
                )
            else:
                raise FileNotFoundError(
                    f"Service account JSON no encontrado en: {self.credentials_path}\n"
                    "Configura GOOGLE_CREDENTIALS_JSON en los secrets de Streamlit Cloud."
                )
            self._client = gspread.authorize(creds)
            logger.info("Autenticación con Google Sheets exitosa.")
        return self._client

    # ------------------------------------------------------------------
    # Lectura cruda
    # ------------------------------------------------------------------

    def _fetch_raw(self) -> pd.DataFrame:
        client = self._get_client()
        try:
            sheet = client.open_by_key(self.spreadsheet_id).worksheet(self.sheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet '{self.spreadsheet_id}' no encontrado. Verifica el ID.")
        except gspread.exceptions.WorksheetNotFound:
            raise ValueError(f"Hoja '{self.sheet_name}' no encontrada en el spreadsheet.")

        records = sheet.get_all_records(numericise_ignore=["all"])
        if not records:
            logger.warning("La hoja está vacía o no tiene datos.")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        logger.info(f"Filas crudas leídas: {len(df)}")
        return df

    # ------------------------------------------------------------------
    # Normalización de columnas
    # ------------------------------------------------------------------

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # Lowercase y strip en nombres de columna para tolerancia a variaciones
        df.columns = [c.strip().lower() for c in df.columns]

        # Renombrar según mapa canónico
        df = df.rename(columns=SHEETS_COLUMN_MAP)

        # Eliminar duplicados de columna si el mapa generó colisiones
        df = df.loc[:, ~df.columns.duplicated()]

        # Quedarse solo con las columnas que conocemos
        known_cols = list(SCHEMA_SALES.keys())
        existing = [c for c in known_cols if c in df.columns]
        extra = [c for c in df.columns if c not in known_cols]
        if extra:
            logger.debug(f"Columnas ignoradas (no en schema): {extra}")

        return df[existing]

    # ------------------------------------------------------------------
    # Validación y limpieza de tipos
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_numeric(value: str) -> float:
        # Soporta: "1500", "$2.000", "26.838.00000", "1,500.00", "1.500,00"
        s = str(value).strip()
        s = s.replace(" ", "")
        # Eliminar símbolos de moneda y letras
        s = "".join(c for c in s if c.isdigit() or c in ".,")
        if not s:
            return float("nan")
        # Si hay coma y punto: el último separador es el decimal
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):  # 1.500,00 → europeo
                s = s.replace(".", "").replace(",", ".")
            else:                             # 1,500.00 → anglosajón
                s = s.replace(",", "")
        elif "," in s:
            # Solo coma: puede ser decimal (1,5) o miles (1,500)
            parts = s.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                s = s.replace(",", ".")       # decimal
            else:
                s = s.replace(",", "")        # miles
        elif s.count(".") > 1:
            # Múltiples puntos → separadores de miles: 26.838.00000 → 2683800000
            # Conservar solo el último como decimal si tiene ≤4 dígitos tras él
            parts = s.split(".")
            if len(parts[-1]) <= 4:
                s = "".join(parts[:-1]) + "." + parts[-1]
            else:
                s = "".join(parts)
        try:
            return float(s)
        except ValueError:
            return float("nan")

    @staticmethod
    def _parse_date(value) -> "pd.Timestamp | pd.NaT":
        import re
        s = str(value).strip()
        if not s or s in ("nan", "None", ""):
            return pd.NaT
        # Completar fechas sin año: "25/03" → "25/03/2026"
        if re.fullmatch(r"\d{1,2}/\d{1,2}", s):
            s = f"{s}/{datetime.now().year}"
        # Intentar formatos conocidos en orden
        formats = [
            "%d/%m/%Y", "%d/%m/%y",   # 4/09/2026, 25/03/26
            "%Y-%m-%d",                # 2026-04-18
            "%d-%m-%Y", "%d-%m-%y",   # 18-04-2026
            "%d/%m/%Y %H:%M:%S",       # 4/09/2026 10:30:00
            "%d/%m/%Y %H:%M",          # 4/09/2026 10:30
        ]
        for fmt in formats:
            try:
                return pd.Timestamp(datetime.strptime(s, fmt))
            except ValueError:
                continue
        # Último recurso: dateutil
        try:
            from dateutil import parser as du
            return pd.Timestamp(du.parse(s, dayfirst=True))
        except Exception:
            return pd.NaT

    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        if "valor_venta" in df.columns:
            df["valor_venta"] = df["valor_venta"].apply(self._parse_numeric)

        if "timestamp_venta" in df.columns:
            df["timestamp_venta"] = df["timestamp_venta"].apply(self._parse_date)

        # Strings: strip y manejo de vacíos
        str_cols = ["nombre", "telefono", "chip", "ad_id"]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace({"": None, "nan": None})

        return df

    # ------------------------------------------------------------------
    # Validación de filas requeridas
    # ------------------------------------------------------------------

    def _validate(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        missing_required = REQUIRED_COLUMNS - set(df.columns)
        if missing_required:
            raise ValueError(
                f"Columnas requeridas faltantes en el Sheet: {missing_required}\n"
                f"Columnas presentes: {list(df.columns)}"
            )

        # Eliminar filas sin datos críticos
        df = df.dropna(subset=list(REQUIRED_COLUMNS))
        dropped = before - len(df)
        if dropped:
            logger.warning(f"{dropped} filas eliminadas por campos requeridos nulos.")

        return df

    # ------------------------------------------------------------------
    # Deduplicación por hash de fila
    # ------------------------------------------------------------------

    def _add_row_hash(self, df: pd.DataFrame) -> pd.DataFrame:
        # Hash deterministico basado en los campos que identifican unívocamente una venta
        key_cols = ["ad_id", "telefono", "timestamp_venta", "valor_venta"]
        available = [c for c in key_cols if c in df.columns]

        df["source_row_id"] = df[available].astype(str).apply(
            lambda row: hashlib.md5("_".join(row.values).encode()).hexdigest(),
            axis=1,
        )
        return df

    # ------------------------------------------------------------------
    # Metadata de ingesta
    # ------------------------------------------------------------------

    def _add_ingestion_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        df["ingested_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        return df

    # ------------------------------------------------------------------
    # Punto de entrada principal
    # ------------------------------------------------------------------

    def get_sales(self, deduplicate_against: set[str] | None = None) -> pd.DataFrame:
        """
        Retorna un DataFrame normalizado con las ventas del Sheet.

        Args:
            deduplicate_against: set de source_row_id ya procesados.
                                 Si se pasa, filtra filas ya vistas.

        Returns:
            DataFrame con schema SCHEMA_SALES.
        """
        logger.info(f"Iniciando ingesta desde Sheet: '{self.sheet_name}'")

        df = self._fetch_raw()
        if df.empty:
            return df

        df = self._normalize_columns(df)
        df = self._cast_types(df)
        df = self._validate(df)
        df = self._add_row_hash(df)
        df = self._add_ingestion_metadata(df)

        if deduplicate_against:
            before = len(df)
            df = df[~df["source_row_id"].isin(deduplicate_against)]
            logger.info(f"Deduplicación: {before - len(df)} filas ya procesadas omitidas.")

        logger.success(f"Ingesta completa: {len(df)} filas nuevas listas para ETL.")
        return df.reset_index(drop=True)
