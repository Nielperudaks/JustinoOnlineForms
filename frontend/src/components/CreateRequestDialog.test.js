import { act } from "react";
import { createRoot } from "react-dom/client";
import CreateRequestDialog from "./CreateRequestDialog";
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

describe("CreateRequestDialog form search", () => {
  let container;
  let root;
  let originalScrollTo;

  beforeEach(() => {
    global.IS_REACT_ACT_ENVIRONMENT = true;
    originalScrollTo = HTMLElement.prototype.scrollTo;
    HTMLElement.prototype.scrollTo = jest.fn();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    HTMLElement.prototype.scrollTo = originalScrollTo;
  });

  test("shows only forms whose names match the search case-insensitively", () => {
    act(() => {
      root.render(
        <CreateRequestDialog
          departments={[{ id: 1, code: "HR", name: "Human Resources" }]}
          templates={[
            { id: 1, department_id: 1, name: "Leave Request", fields: [] },
            { id: 2, department_id: 1, name: "Overtime Authorization", fields: [] },
          ]}
          onSubmit={() => {}}
          onClose={() => {}}
        />,
      );
    });

    act(() => {
      container.querySelector('[data-testid="select-dept-HR"]').click();
    });

    const search = container.querySelector('[data-testid="search-forms"]');
    expect(search).not.toBeNull();
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(
        search,
        "LEAVE",
      );
      search.dispatchEvent(new Event("input", { bubbles: true }));
    });

    expect(container.textContent).toContain("Leave Request");
    expect(container.textContent).not.toContain("Overtime Authorization");
  });
});
