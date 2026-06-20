import { buildTableFieldPayload } from "./tableFieldUtils";

describe("BuildFormDialog table payload", () => {
  test("preserves typed columns and unique flags in payload", () => {
    expect(
      buildTableFieldPayload({
        table_title: "Line Items",
        num_rows: 5,
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
      num_rows: 5,
    });
  });
});
