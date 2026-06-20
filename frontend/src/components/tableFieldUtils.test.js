import {
  buildTableFieldPayload,
  getTableCellInputType,
  hasDuplicateTableRows,
  normalizeTableColumns,
} from "./tableFieldUtils";

describe("table field utils", () => {
  test("normalizes typed columns and falls back to text columns", () => {
    expect(
      normalizeTableColumns({
        columns: [
          { label: "Date", type: "date", unique: false },
          { label: "Amount", type: "number", unique: true },
        ],
      }),
    ).toEqual([
      { label: "Date", type: "date", unique: false },
      { label: "Amount", type: "number", unique: true },
    ]);

    expect(
      normalizeTableColumns({
        column_headers: ["One", "Two"],
      }),
    ).toEqual([
      { label: "One", type: "text", unique: false },
      { label: "Two", type: "text", unique: false },
    ]);
  });

  test("builds table payload with derived headers from typed columns", () => {
    expect(
      buildTableFieldPayload({
        table_title: "Line Items",
        num_rows: 4,
        columns: [
          { label: "Date", type: "date", unique: false },
          { label: "Description", type: "text", unique: true },
        ],
      }),
    ).toEqual({
      table_title: "Line Items",
      columns: [
        { label: "Date", type: "date", unique: false },
        { label: "Description", type: "text", unique: true },
      ],
      column_headers: ["Date", "Description"],
      num_rows: 4,
    });
  });

  test("detects duplicate rows only across selected unique columns", () => {
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

  test("maps table column types to input types", () => {
    expect(getTableCellInputType("date")).toBe("date");
    expect(getTableCellInputType("time")).toBe("time");
    expect(getTableCellInputType("number")).toBe("number");
    expect(getTableCellInputType("text")).toBe("text");
    expect(getTableCellInputType("anything-else")).toBe("text");
  });
});
