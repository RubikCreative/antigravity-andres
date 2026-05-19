"""
Esquemas canónicos de datos. Fuente de verdad para tipos y columnas esperadas.
Modifica aquí si el nombre de columnas en el Sheet cambia.
"""

# Mapa: nombre de columna en el Sheet → nombre interno del sistema
SHEETS_COLUMN_MAP = {
    # Columnas originales
    "nombre":               "nombre",
    "teléfono":             "telefono",
    "telefono":             "telefono",
    "chip":                 "chip",
    "ad_id":                "ad_id",
    "id ad":                "ad_id",
    "valor_venta":          "valor_venta",
    "valor":                "valor_venta",
    "timestamp":            "timestamp_venta",
    "data":                 "timestamp_venta",
    # Variantes (Andres y otros clientes)
    "numero de telefono":   "telefono",
    "número de teléfono":   "telefono",
    "valor de la venta":    "valor_venta",
    "fecha de compra":      "timestamp_venta",
    "fecha":                "timestamp_venta",
    "anuncio de origen":    "ad_id",
    "post id":              "ad_id",
    "whatsapp origen":      "chip",
    "whatsapp":             "chip",
}

# Tipos finales luego de normalización
SCHEMA_SALES = {
    "nombre":          "str",
    "telefono":        "str",
    "chip":            "str",
    "ad_id":           "str",
    "valor_venta":     "float64",
    "timestamp_venta": "datetime64[ns]",
    "source_row_id":   "str",
    "ingested_at":     "datetime64[ns]",
}

# Columnas mínimas requeridas para que una fila sea válida
REQUIRED_COLUMNS = {"ad_id", "valor_venta", "chip"}

# Schema de Meta Ads (referencia)
SCHEMA_META_ADS = {
    "date_start":             "datetime64[ns]",
    "date_stop":              "datetime64[ns]",
    "campaign_id":            "str",
    "campaign_name":          "str",
    "adset_id":               "str",
    "adset_name":             "str",
    "ad_id":                  "str",
    "ad_name":                "str",
    "spend":                  "float64",
    "impressions":            "int64",
    "clicks":                 "int64",
    "cpc":                    "float64",
    "cpm":                    "float64",
    "ctr":                    "float64",
    "reach":                  "int64",
    "conversations_started":  "int64",
    "cost_per_conversation":  "float64",
    "ingested_at":            "datetime64[ns]",
}
