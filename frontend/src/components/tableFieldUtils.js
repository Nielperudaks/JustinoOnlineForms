export const TABLE_COLUMN_TYPES = ["text", "number", "date", "time"];

function normalizeColumnType(type) {
  const candidate = String(type || "text").toLowerCase();
  return TABLE_COLUMN_TYPES.includes(candidate) ? candidate : "text";
}

export function normalizeTableColumns(field, fallbackCount = 2) {
  const rawColumns = Array.isArray(field?.columns) ? field.columns : [];
  if (rawColumns.length > 0) {
    return rawColumns.map((column, index) => ({
      label: String(column?.label || `Column ${index + 1}`).trim() || `Column ${index + 1}`,
      type: normalizeColumnType(column?.type),
      unique: column?.unique === true,
    }));
  }

  const rawHeaders = Array.isArray(field?.column_headers)
    ? field.column_headers
    : typeof field?.column_headers === "string"
      ? String(field.column_headers)
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean)
      : [];

  if (rawHeaders.length > 0) {
    return rawHeaders.map((header, index) => ({
      label: String(header || `Column ${index + 1}`).trim() || `Column ${index + 1}`,
      type: "text",
      unique: false,
    }));
  }

  return Array.from({ length: Math.max(1, fallbackCount) }, (_, index) => ({
    label: `Column ${index + 1}`,
    type: "text",
    unique: false,
  }));
}

export function buildTableFieldPayload(field) {
  const columns = normalizeTableColumns(field);
  return {
    table_title: String(field?.table_title || "").trim(),
    columns,
    column_headers: columns.map((column) => column.label),
    num_rows: Number.isInteger(field?.num_rows) ? field.num_rows : 3,
  };
}

export function getTableCellInputType(columnType) {
  return normalizeColumnType(columnType);
}

function normalizeTableCellValue(value, columnType) {
  const text = String(value ?? "").trim();
  if (!text) {
    return "";
  }

  if (normalizeColumnType(columnType) === "number") {
    const numeric = Number(text);
    if (!Number.isNaN(numeric)) {
      return String(numeric);
    }
  }

  return text;
}

export function hasDuplicateTableRows(field, tableValue) {
  const columns = normalizeTableColumns(field);
  const uniqueIndexes = columns
    .map((column, index) => (column.unique ? index : -1))
    .filter((index) => index >= 0);

  if (uniqueIndexes.length === 0) {
    return false;
  }

  const rows = Array.isArray(tableValue?.rows) ? tableValue.rows : [];
  const seen = new Set();

  for (const row of rows) {
    if (!Array.isArray(row)) {
      continue;
    }

    const signature = uniqueIndexes.map((index) =>
      normalizeTableCellValue(row[index], columns[index]?.type),
    );

    if (signature.every((value) => value === "")) {
      continue;
    }

    const key = JSON.stringify(signature);
    if (seen.has(key)) {
      return true;
    }
    seen.add(key);
  }

  return false;
}
