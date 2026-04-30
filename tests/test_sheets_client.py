"""
Tests del SheetsClient usando datos mock (sin llamadas reales a la API).
Ejecutar con: pytest tests/test_sheets_client.py -v
"""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.connectors.sheets_client import SheetsClient


MOCK_RECORDS = [
    {"nombre": "Ana López",    "teléfono": "5491112345678", "chip": "CHIP_A", "ad_id": "120210001", "valor_venta": "1500",   "timestamp": "01/04/2026 10:30"},
    {"nombre": "Juan Pérez",   "teléfono": "5491187654321", "chip": "CHIP_B", "ad_id": "120210002", "valor_venta": "$2.000",  "timestamp": "02/04/2026 14:00"},
    {"nombre": "Sin Ad",       "teléfono": "5491100000000", "chip": "CHIP_A", "ad_id": "",           "valor_venta": "500",    "timestamp": "03/04/2026 09:00"},  # debe eliminarse
    {"nombre": "  María  ",    "teléfono": "5491199999999", "chip": "CHIP_C", "ad_id": "120210003", "valor_venta": "3000",   "timestamp": "04/04/2026 16:45"},
]


@pytest.fixture
def client():
    c = SheetsClient(
        credentials_path="config/service_account.json",
        spreadsheet_id="fake_id",
        sheet_name="Ventas",
    )
    return c


def _mock_get_all_records(client, records):
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = records
    mock_ws = MagicMock()
    mock_ws.worksheet.return_value = mock_sheet
    client._client = MagicMock()
    client._client.open_by_key.return_value = mock_ws


class TestNormalization:
    def test_columnas_renombradas(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df = client.get_sales()
        assert "telefono" in df.columns
        assert "teléfono" not in df.columns

    def test_valor_venta_numerico(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df = client.get_sales()
        assert df["valor_venta"].dtype == "float64"
        # $2.000 debe parsearse como 2000.0
        assert df[df["ad_id"] == "120210002"]["valor_venta"].iloc[0] == 2000.0

    def test_timestamp_como_datetime(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df = client.get_sales()
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp_venta"])

    def test_nombre_strip(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df = client.get_sales()
        assert df[df["ad_id"] == "120210003"]["nombre"].iloc[0] == "María"


class TestValidation:
    def test_fila_sin_ad_id_eliminada(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df = client.get_sales()
        assert len(df) == 3  # 4 filas - 1 sin ad_id

    def test_columnas_requeridas_faltantes_lanza_error(self, client):
        records_sin_chip = [{"nombre": "X", "ad_id": "1", "valor_venta": "100"}]
        _mock_get_all_records(client, records_sin_chip)
        with pytest.raises(ValueError, match="Columnas requeridas faltantes"):
            client.get_sales()


class TestDeduplication:
    def test_dedup_por_source_row_id(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df_first = client.get_sales()
        seen_ids = set(df_first["source_row_id"])

        _mock_get_all_records(client, MOCK_RECORDS)
        df_second = client.get_sales(deduplicate_against=seen_ids)
        assert len(df_second) == 0

    def test_source_row_id_deterministico(self, client):
        _mock_get_all_records(client, MOCK_RECORDS)
        df1 = client.get_sales()
        _mock_get_all_records(client, MOCK_RECORDS)
        df2 = client.get_sales()
        assert list(df1["source_row_id"]) == list(df2["source_row_id"])
