# Table Column Types And Unique Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let table form fields define per-column input types and optional duplicate-row checks across selected columns.

**Architecture:** Extend the table field schema so each column is a structured object instead of a plain header string. The builder will edit column labels, types, and uniqueness flags; the request entry UI will render each cell with the matching input type; the backend will validate duplicate rows before storing a request so the rule cannot be bypassed.

**Tech Stack:** FastAPI, Pydantic, React, Jest, Pytest

---

### Task 1: Extend table field schema and backend validation

**Files:**
- Modify: `backend/routes/form_templates.py`
- Modify: `backend/routes/requests.py`
- Test: `tests/test_manager_form_templates.py`
- Test: `tests/test_request_table_validation.py`

- [ ] **Step 1: Write the failing test**

```python
def test_template_accepts_table_column_types_and_unique_flags(fake_db):
    req = make_template_create(
        fields=[
            form_templates.FormField(
                name="items",
                label="Items",
                type="table",
                required=True,
                table_title="Line Items",
                columns=[
                    form_templates.TableColumn(label="Date", type="date", unique=False),
                    form_templates.TableColumn(label="Time", type="time", unique=False),
                    form_templates.TableColumn(label="Description", type="text", unique=True),
                    form_templates.TableColumn(label="Qty", type="number", unique=False),
                ],
                num_rows=3,
            )
        ],
    )

    created = run(form_templates.create_template(req, current=manager()))

    table = created["fields"][0]
    assert table["columns"][2]["type"] == "text"
    assert table["columns"][2]["unique"] is True
```

```python
def test_create_request_rejects_duplicate_rows_in_unique_columns(fake_db):
    fake_db.form_templates.items.append(
        {
            "id": "template-table",
            "department_id": "dept-a",
            "name": "Table Form",
            "description": "",
            "fields": [
                {
                    "name": "items",
                    "label": "Items",
                    "type": "table",
                    "required": True,
                    "table_title": "Line Items",
                    "columns": [
                        {"label": "Date", "type": "date", "unique": False},
                        {"label": "Description", "type": "text", "unique": True},
                    ],
                    "num_rows": 3,
                }
            ],
            "approver_chain": [],
            "custodian": None,
            "is_active": True,
        }
    )

    request = requests.RequestCreate(
        form_template_id="template-table",
        form_data={
            "items": {
                "rows": [
                    ["2026-06-20", "Duplicate"],
                    ["2026-06-21", "Duplicate"],
                ]
            }
        },
    )

    with pytest.raises(HTTPException) as exc:
        run(requests.create_request(request, user=requestor()))

    assert exc.value.status_code == 400
    assert "duplicate" in exc.value.detail.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_manager_form_templates.py -k table_column_types -v`

Run: `pytest tests/test_request_table_validation.py -v`

Expected: FAIL because `columns` is not part of the schema and duplicate-row validation does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class TableColumn(BaseModel):
    label: str
    type: str = "text"
    unique: bool = False


class FormField(BaseModel):
    ...
    columns: Optional[List[TableColumn]] = None


def validate_table_rows(field, value):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_manager_form_templates.py -k table_column_types -v`

Run: `pytest tests/test_request_table_validation.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/form_templates.py backend/routes/requests.py tests/test_manager_form_templates.py tests/test_request_table_validation.py
git commit -m "feat: add typed table columns and unique validation"
```

### Task 2: Update form builder to edit typed table columns

**Files:**
- Modify: `frontend/src/components/BuildFormDialog.js`
- Test: `frontend/src/components/BuildFormDialog.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
test("builds table columns with types and unique flags", async () => {
  ...
  expect(payload.fields[0].columns).toEqual([
    { label: "Date", type: "date", unique: false },
    { label: "Description", type: "text", unique: true },
  ]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `yarn test BuildFormDialog.test.js --runInBand`

Expected: FAIL because builder still only saves `column_headers`.

- [ ] **Step 3: Write minimal implementation**

```javascript
const TABLE_COLUMN_TYPES = ["text", "number", "date", "time"];
...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `yarn test BuildFormDialog.test.js --runInBand`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/BuildFormDialog.js frontend/src/components/BuildFormDialog.test.js
git commit -m "feat: edit typed table columns in builder"
```

### Task 3: Render typed table inputs in request creation

**Files:**
- Modify: `frontend/src/components/CreateRequestDialog.js`
- Test: `frontend/src/components/CreateRequestDialog.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
test("renders date, time, number, and text inputs for table columns", () => {
  ...
  expect(screen.getByLabelText("Date")).toHaveAttribute("type", "date");
  expect(screen.getByLabelText("Time")).toHaveAttribute("type", "time");
  expect(screen.getByLabelText("Qty")).toHaveAttribute("type", "number");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `yarn test CreateRequestDialog.test.js --runInBand`

Expected: FAIL because table cells are plain text inputs now.

- [ ] **Step 3: Write minimal implementation**

```javascript
const getTableCellInputType = (columnType) => {
  ...
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `yarn test CreateRequestDialog.test.js --runInBand`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CreateRequestDialog.js frontend/src/components/CreateRequestDialog.test.js
git commit -m "feat: render typed table inputs in request form"
```

### Task 4: Verify full test suite slices

**Files:**
- None

- [ ] **Step 1: Run targeted backend tests**

Run: `pytest tests/test_manager_form_templates.py tests/test_request_table_validation.py -v`

- [ ] **Step 2: Run targeted frontend tests**

Run: `yarn test BuildFormDialog.test.js CreateRequestDialog.test.js --runInBand`

- [ ] **Step 3: Run existing related tests**

Run: `pytest tests/test_approval_hierarchy.py tests/test_manager_request_access.py -v`

Run: `yarn test RequestDetail.test.js --runInBand`

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: verify table column typing and unique validation"
```
