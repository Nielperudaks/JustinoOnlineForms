import {
  getTableCellInputType,
  hasDuplicateTableRows,
  normalizeTableColumns,
} from "./tableFieldUtils";

describe("CreateRequestDialog table behavior", () => {
  test("renders the right input types for typed table columns", () => {
    const columns = normalizeTableColumns({
      columns: [
        { label: "Date", type: "date", unique: false },
        { label: "Time", type: "time", unique: false },
        { label: "Qty", type: "number", unique: false },
        { label: "Description", type: "text", unique: false },
      ],
    });

    expect(columns.map((column) => getTableCellInputType(column.type))).toEqual([
      "date",
      "time",
      "number",
      "text",
    ]);
  });

  test("rejects duplicate rows only when selected columns match", () => {
    const field = {
      columns: [
        { label: "Date", type: "date", unique: false },
        { label: "Description", type: "text", unique: true },
        { label: "Qty", type: "number", unique: false },
      ],
    };

    expect(
      hasDuplicateTableRows(field, {
        rows: [
          ["2026-06-20", "Duplicate", "1"],
          ["2026-06-21", "Duplicate", "2"],
        ],
      }),
    ).toBe(true);

    expect(
      hasDuplicateTableRows(field, {
        rows: [
          ["2026-06-20", "Alpha", "1"],
          ["2026-06-20", "Beta", "1"],
        ],
      }),
    ).toBe(false);
  });
});
