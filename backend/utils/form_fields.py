from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

TABLE_COLUMN_TYPES = {"text", "number", "date", "time"}


def _as_dict(item):
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if isinstance(item, dict):
        return item
    return {}


def get_table_columns(field):
    field_data = _as_dict(field)
    raw_columns = field_data.get("columns") or []
    if raw_columns:
        columns = []
        for column in raw_columns:
            column_data = _as_dict(column)
            label = str(column_data.get("label") or "").strip() or "Column"
            column_type = str(column_data.get("type") or "text").strip().lower()
            if column_type not in TABLE_COLUMN_TYPES:
                column_type = "text"
            columns.append(
                {
                    "label": label,
                    "type": column_type,
                    "unique": bool(column_data.get("unique", False)),
                }
            )
        return columns

    headers = field_data.get("column_headers") or []
    if isinstance(headers, str):
        headers = [value.strip() for value in headers.split("\n") if value.strip()]
    return [
        {
            "label": str(header).strip() or "Column",
            "type": "text",
            "unique": False,
        }
        for header in headers
    ]


def get_table_column_headers(field):
    return [column["label"] for column in get_table_columns(field)]


def normalize_table_cell_value(value, column_type):
    text = str(value or "").strip()
    if not text:
        return ""

    if column_type == "number":
        try:
            return format(Decimal(text).normalize(), "f")
        except (InvalidOperation, ValueError):
            return text

    return text


def table_row_signature(row, columns, unique_indexes):
    values = []
    for index in unique_indexes:
        column = columns[index] if index < len(columns) else {"type": "text"}
        cell_value = row[index] if index < len(row) else ""
        values.append(normalize_table_cell_value(cell_value, column["type"]))
    return tuple(values)


def validate_table_field_rows(field, value):
    columns = get_table_columns(field)
    unique_indexes = [index for index, column in enumerate(columns) if column["unique"]]
    if not unique_indexes:
        return

    rows = (value or {}).get("rows") if isinstance(value, dict) else []
    seen = set()
    for row in rows or []:
        if not isinstance(row, list):
            continue
        signature = table_row_signature(row, columns, unique_indexes)
        if all(part == "" for part in signature):
            continue
        if signature in seen:
            field_label = _as_dict(field).get("label", "Table")
            raise HTTPException(
                status_code=400,
                detail=f"{field_label} has duplicate rows in the selected columns",
            )
        seen.add(signature)
