# Department Groups Immediate Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add department groups, a Supervisor role, and an `Immediate Supervisor` approval placeholder that routes to a group supervisor with manager fallback.

**Architecture:** Store `department_groups` on department documents and validate them in the department route before saving. Add role constants/helpers in backend and frontend role modules, then resolve `immediate_supervisor` during request creation using the requestor's department group membership. Keep `AdminPage.js` as the integration point, but put reusable filtering helpers in `frontend/src/pages/adminState.js` so they can be tested without rendering the whole page.

**Tech Stack:** FastAPI/Pydantic, Mongo-style async collections, pytest, React, Jest, existing shadcn-style UI components.

---

## File Structure

- Modify `backend/utils/roles.py`: add `SUPERVISOR`, include it in requestor and approver role sets, add `is_supervisor_role`.
- Modify `backend/routes/departments.py`: extend department update payload with `department_groups`, add validation/normalization helpers.
- Modify `backend/routes/requests.py`: resolve `immediate_supervisor` and share manager fallback behavior.
- Modify `backend/routes/form_templates.py`: allow `immediate_supervisor` as a special approver.
- Modify `backend/routes/users.py`: supervisors automatically appear in `/users/approvers`.
- Modify `frontend/src/lib/roles.js`: add Supervisor role and helper.
- Modify `frontend/src/pages/adminState.js`: add group filtering and special approver helpers.
- Modify `frontend/src/pages/AdminPage.js`: add picker option and department group dialog.
- Test `tests/test_department_groups.py`: backend department group validation.
- Test `tests/test_approval_hierarchy.py`: request routing for `immediate_supervisor`.
- Test `tests/test_manager_form_templates.py`: template validation accepts `immediate_supervisor`.
- Test `frontend/src/pages/adminState.test.js`: role/group helper behavior.

---

### Task 1: Backend Role Constants

**Files:**
- Modify: `backend/utils/roles.py`
- Test: `tests/test_approval_hierarchy.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_approval_hierarchy.py`:

```python
from backend.utils.roles import APPROVER_ROLES, REQUESTOR_ROLES


def test_supervisor_role_can_request_and_approve():
    assert "supervisor" in REQUESTOR_ROLES
    assert "supervisor" in APPROVER_ROLES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_approval_hierarchy.py::test_supervisor_role_can_request_and_approve -q`

Expected: FAIL because `supervisor` is not in one or both role sets.

- [ ] **Step 3: Write minimal implementation**

In `backend/utils/roles.py`, add:

```python
SUPERVISOR = "supervisor"
```

Update role sets:

```python
REQUESTOR_ROLES = {"requestor", "both", MANAGER_OPS, MANAGER_SUP, SUPERVISOR, SUPER_ADMIN}
APPROVER_ROLES = {"approver", "both", SUPERVISOR, SUPER_ADMIN} | FORM_MANAGER_ROLES | EXECUTIVE_ROLES
```

Add helper:

```python
def is_supervisor_role(role):
    return role == SUPERVISOR
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_approval_hierarchy.py::test_supervisor_role_can_request_and_approve -q`

Expected: PASS.

---

### Task 2: Department Group Validation

**Files:**
- Modify: `backend/routes/departments.py`
- Create: `tests/test_department_groups.py`

- [ ] **Step 1: Write failing validation tests**

Create `tests/test_department_groups.py` with `FakeCursor`, `FakeResult`, `FakeCollection`, `FakeDb`, `run`, and `admin` helpers. `FakeDb` must include one department `dept-a`, supervisors `supervisor-a` and `supervisor-b`, requestors `requestor-a` and `both-a`, and manager `manager-a`. Include these tests:

```python
def test_update_department_accepts_valid_department_groups(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {
                "name": "Purchasing Team",
                "supervisor_id": "supervisor-a",
                "member_ids": ["requestor-a", "both-a"],
            }
        ]
    )

    updated = run(departments.update_department("dept-a", req, admin=admin()))

    assert updated["department_groups"][0]["name"] == "Purchasing Team"
    assert updated["department_groups"][0]["supervisor_id"] == "supervisor-a"
    assert updated["department_groups"][0]["member_ids"] == ["requestor-a", "both-a"]
    assert updated["department_groups"][0]["id"]
```

```python
def test_update_department_rejects_duplicate_group_member(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {"name": "One", "supervisor_id": "supervisor-a", "member_ids": ["requestor-a"]},
            {"name": "Two", "supervisor_id": "supervisor-b", "member_ids": ["requestor-a"]},
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "one department group" in exc.value.detail.lower()
```

```python
def test_update_department_rejects_non_supervisor_group_supervisor(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {"name": "Purchasing", "supervisor_id": "requestor-a", "member_ids": ["both-a"]},
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "supervisor" in exc.value.detail.lower()
```

```python
def test_update_department_rejects_manager_as_group_member(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {"name": "Purchasing", "supervisor_id": "supervisor-a", "member_ids": ["manager-a"]},
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "member" in exc.value.detail.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_department_groups.py -q`

Expected: FAIL because `DepartmentUpdate` does not accept `department_groups` and no validation exists.

- [ ] **Step 3: Write minimal implementation**

In `backend/routes/departments.py`, add imports:

```python
from typing import Optional, List
from utils.roles import FORM_MANAGER_ROLES, EXECUTIVE_ROLES, SUPER_ADMIN, SUPERVISOR
```

Add models:

```python
class DepartmentGroup(BaseModel):
    id: Optional[str] = None
    name: str
    supervisor_id: str
    member_ids: List[str] = []
```

Update `DepartmentUpdate`:

```python
department_groups: Optional[List[DepartmentGroup]] = None
```

Add helper:

```python
async def normalize_department_groups(dept_id: str, groups: List[DepartmentGroup]):
    user_ids = set()
    for group in groups:
        user_ids.add(group.supervisor_id)
        user_ids.update(group.member_ids)

    users = await db.users.find(
        {"id": {"$in": list(user_ids)}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(user_ids) or 1)
    users_by_id = {user["id"]: user for user in users}
    seen_members = set()
    normalized = []

    for group in groups:
        name = group.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Department group name is required")

        supervisor = users_by_id.get(group.supervisor_id)
        if not supervisor or supervisor.get("department_id") != dept_id or supervisor.get("role") != SUPERVISOR:
            raise HTTPException(status_code=400, detail="Department group supervisor must be an active supervisor in this department")

        member_ids = []
        for member_id in group.member_ids:
            if member_id in seen_members:
                raise HTTPException(status_code=400, detail="A user can belong to only one department group")
            member = users_by_id.get(member_id)
            if (
                not member
                or member.get("department_id") != dept_id
                or member.get("role") in FORM_MANAGER_ROLES
                or member.get("role") in EXECUTIVE_ROLES
                or member.get("role") in {SUPERVISOR, SUPER_ADMIN}
            ):
                raise HTTPException(status_code=400, detail="Department group members must be non-manager department users")
            seen_members.add(member_id)
            member_ids.append(member_id)

        normalized.append({
            "id": group.id or str(uuid.uuid4()),
            "name": name,
            "supervisor_id": group.supervisor_id,
            "member_ids": member_ids,
        })

    return normalized
```

In `update_department`, replace update construction with a branch that normalizes `department_groups` before `$set`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_department_groups.py -q`

Expected: PASS.

---

### Task 3: Immediate Supervisor Request Routing

**Files:**
- Modify: `backend/routes/requests.py`
- Test: `tests/test_approval_hierarchy.py`

- [ ] **Step 1: Write failing routing tests**

Extend the fake database in `tests/test_approval_hierarchy.py` with a department containing groups and users:

```python
self.departments = FakeCollection([
    {
        "id": "dept-a",
        "department_groups": [
            {
                "id": "group-a",
                "name": "Team A",
                "supervisor_id": "supervisor-a",
                "member_ids": ["requestor-a"],
            }
        ],
    }
])
```

Add users:

```python
{
    "id": "supervisor-a",
    "name": "Supervisor A",
    "email": "supervisor@example.com",
    "role": "supervisor",
    "department_id": "dept-a",
    "is_active": True,
}
```

Add a helper that changes the template step to `immediate_supervisor`, then tests:

```python
def test_group_member_routes_immediate_supervisor_to_group_supervisor(monkeypatch):
    created = submit_as(
        {
            "id": "requestor-a",
            "name": "Requestor A",
            "email": "requestor@example.com",
            "role": "requestor",
            "department_id": "dept-a",
        },
        monkeypatch,
        approver_id="immediate_supervisor",
    )

    assert created["approvals"][0]["approver_id"] == "supervisor-a"
    assert created["approvals"][0]["approver_name"] == "Supervisor A"
```

```python
def test_supervisor_requestor_routes_immediate_supervisor_to_manager(monkeypatch):
    created = submit_as(
        {
            "id": "supervisor-a",
            "name": "Supervisor A",
            "email": "supervisor@example.com",
            "role": "supervisor",
            "department_id": "dept-a",
        },
        monkeypatch,
        approver_id="immediate_supervisor",
    )

    assert created["approvals"][0]["approver_id"] == "manager-ops-a"
```

```python
def test_non_group_member_routes_immediate_supervisor_to_manager(monkeypatch):
    created = submit_as(
        {
            "id": "requestor-b",
            "name": "Requestor B",
            "email": "requestor.b@example.com",
            "role": "requestor",
            "department_id": "dept-a",
        },
        monkeypatch,
        approver_id="immediate_supervisor",
    )

    assert created["approvals"][0]["approver_id"] == "manager-ops-a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_approval_hierarchy.py -q`

Expected: FAIL because `immediate_supervisor` is treated as a literal user id.

- [ ] **Step 3: Write minimal implementation**

In `backend/routes/requests.py`, import `SUPERVISOR`.

Extract current manager lookup into:

```python
async def resolve_immediate_manager(user, requester_dept_id):
    if not requester_dept_id:
        raise HTTPException(
            status_code=400,
            detail="Requestor has no department assigned. Immediate Manager requires the requestor to have a department.",
        )
    executive_role = executive_role_for_manager(user)
    if executive_role:
        query = {"role": executive_role, "is_active": True}
        missing = f"No Immediate Manager ({executive_role.replace('_', ' ').title()}) found. Please assign the executive officer role."
    else:
        query = {"role": {"$in": list(MANAGER_ROLES)}, "department_id": requester_dept_id, "is_active": True}
        missing = "No Immediate Manager found in requestor's department. Please assign Manager (OPS) or Manager (SUP) to the requestor's department."
    manager_user = await db.users.find_one(query, {"_id": 0})
    if not manager_user:
        raise HTTPException(status_code=400, detail=missing)
    return manager_user["id"], manager_user.get("name", "Immediate Manager")
```

Add:

```python
async def resolve_immediate_supervisor(user, requester_dept_id):
    if user.get("role") == SUPERVISOR:
        return await resolve_immediate_manager(user, requester_dept_id)
    department = await db.departments.find_one({"id": requester_dept_id}, {"_id": 0})
    for group in (department or {}).get("department_groups", []):
        if user.get("id") in group.get("member_ids", []):
            supervisor = await db.users.find_one(
                {"id": group.get("supervisor_id"), "role": SUPERVISOR, "department_id": requester_dept_id, "is_active": True},
                {"_id": 0},
            )
            if not supervisor:
                raise HTTPException(status_code=400, detail="No Immediate Supervisor found for the requestor's department group. Please assign an active supervisor.")
            return supervisor["id"], supervisor.get("name", "Immediate Supervisor")
    return await resolve_immediate_manager(user, requester_dept_id)
```

Use these helpers inside the approver chain loop for `immediate_manager` and `immediate_supervisor`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_approval_hierarchy.py -q`

Expected: PASS.

---

### Task 4: Template Special Approver Validation

**Files:**
- Modify: `backend/routes/form_templates.py`
- Test: `tests/test_manager_form_templates.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_manager_form_templates.py`:

```python
def test_manager_can_assign_immediate_supervisor_placeholder(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=1, user_id="immediate_supervisor", user_name="Immediate Supervisor"),
        ]
    )

    created = run(form_templates.create_template(req, current=manager()))

    assert created["approver_chain"][0]["user_id"] == "immediate_supervisor"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_manager_form_templates.py::test_manager_can_assign_immediate_supervisor_placeholder -q`

Expected: FAIL because only `immediate_manager` is special-cased.

- [ ] **Step 3: Write minimal implementation**

In `backend/routes/form_templates.py`, add `immediate_supervisor` anywhere `immediate_manager` is accepted as a special approver. Prefer a small constant:

```python
SPECIAL_APPROVER_IDS = {"immediate_manager", "immediate_supervisor"}
```

Use `if step.user_id in SPECIAL_APPROVER_IDS` in validation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_manager_form_templates.py::test_manager_can_assign_immediate_supervisor_placeholder -q`

Expected: PASS.

---

### Task 5: Frontend Role And Group Helpers

**Files:**
- Modify: `frontend/src/lib/roles.js`
- Modify: `frontend/src/pages/adminState.js`
- Test: `frontend/src/pages/adminState.test.js`

- [ ] **Step 1: Write failing frontend tests**

Add to `frontend/src/pages/adminState.test.js`:

```javascript
test("treats supervisor as an approver user", () => {
  expect(isApproverUser({ role: "supervisor" })).toBe(true);
});
```

Import and test new helper:

```javascript
import { getAvailableDepartmentGroupMembers } from "./adminState";
```

```javascript
test("filters department group members to eligible unassigned users", () => {
  const users = [
    { id: "requestor-a", role: "requestor", department_id: "dept-a" },
    { id: "requestor-b", role: "requestor", department_id: "dept-a" },
    { id: "supervisor-a", role: "supervisor", department_id: "dept-a" },
    { id: "manager-a", role: "manager_ops", department_id: "dept-a" },
    { id: "requestor-c", role: "requestor", department_id: "dept-b" },
  ];
  const groups = [{ id: "group-1", member_ids: ["requestor-a"] }];

  expect(getAvailableDepartmentGroupMembers(users, "dept-a", groups).map((user) => user.id)).toEqual(["requestor-b"]);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend; yarn test src/pages/adminState.test.js --watchAll=false`

Expected: FAIL because Supervisor is missing and helper is undefined.

- [ ] **Step 3: Write minimal implementation**

In `frontend/src/lib/roles.js`, add:

```javascript
{ value: "supervisor", label: "Supervisor" },
```

Add `"supervisor"` to `APPROVER_ROLES` and `REQUESTOR_ROLES`.

In `frontend/src/pages/adminState.js`, add:

```javascript
const GROUP_MEMBER_EXCLUDED_ROLES = new Set([
  "supervisor",
  "manager",
  "manager_ops",
  "manager_sup",
  "executive_ops",
  "executive_sup",
  "super_admin",
]);

export function getAvailableDepartmentGroupMembers(users, departmentId, groups, currentGroupId = null) {
  const assigned = new Set();
  for (const group of groups || []) {
    if (currentGroupId && group.id === currentGroupId) continue;
    for (const memberId of group.member_ids || []) {
      assigned.add(memberId);
    }
  }
  return (users || []).filter(
    (user) =>
      user.department_id === departmentId &&
      !GROUP_MEMBER_EXCLUDED_ROLES.has(user.role) &&
      !assigned.has(user.id),
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend; yarn test src/pages/adminState.test.js --watchAll=false`

Expected: PASS.

---

### Task 6: Frontend Approval Picker Placeholder

**Files:**
- Modify: `frontend/src/pages/AdminPage.js`
- Test: `frontend/src/pages/adminState.test.js`

- [ ] **Step 1: Add helper test**

In `frontend/src/pages/adminState.js`, plan to export:

```javascript
export function getSpecialApproverLabel(userId) {
  if (userId === "immediate_manager") return "Immediate Manager";
  if (userId === "immediate_supervisor") return "Immediate Supervisor";
  return "";
}
```

Test:

```javascript
test("labels special approver placeholders", () => {
  expect(getSpecialApproverLabel("immediate_manager")).toBe("Immediate Manager");
  expect(getSpecialApproverLabel("immediate_supervisor")).toBe("Immediate Supervisor");
  expect(getSpecialApproverLabel("user-1")).toBe("");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; yarn test src/pages/adminState.test.js --watchAll=false`

Expected: FAIL because helper is missing.

- [ ] **Step 3: Implement helper and wire UI**

In `AdminPage.js`, import `getSpecialApproverLabel`. Update `ApproverPicker`:

```javascript
const specialLabel = getSpecialApproverLabel(assigned?.user_id);
const selectedLabel = specialLabel || (selectedApprover ? `${selectedApprover.name} (${selectedApprover.email})` : assigned?.user_name || "");
```

Render a second `CommandItem`:

```jsx
<CommandItem
  value="Immediate Supervisor"
  onSelect={() => handleSelect("immediate_supervisor")}
  className="text-xs"
>
  <Check className={`w-3.5 h-3.5 ${assigned?.user_id === "immediate_supervisor" ? "opacity-100" : "opacity-0"}`} />
  <div className="min-w-0">
    <div className="font-medium text-slate-700">Immediate Supervisor</div>
    <div className="text-[11px] text-slate-400">
      Routes to the requester's department group supervisor
    </div>
  </div>
</CommandItem>
```

Update `handleAssignApprover`:

```javascript
const specialName = getSpecialApproverLabel(userId);
const isSpecialApprover = Boolean(specialName);
const approver = approvers.find((a) => a.id === userId);
const displayName = specialName || approver?.name || "";
if (!isSpecialApprover && !approver) return;
```

- [ ] **Step 4: Run frontend tests**

Run: `cd frontend; yarn test src/pages/adminState.test.js --watchAll=false`

Expected: PASS.

---

### Task 7: Department Group Dialog

**Files:**
- Modify: `frontend/src/pages/AdminPage.js`

- [ ] **Step 1: Add component state**

Add state near department edit state:

```javascript
const [groupDialogDepartment, setGroupDialogDepartment] = useState(null);
const [editingGroups, setEditingGroups] = useState([]);
const [isSavingGroups, setIsSavingGroups] = useState(false);
```

- [ ] **Step 2: Add open/save handlers**

```javascript
const openDepartmentGroupsDialog = (dept) => {
  setGroupDialogDepartment(dept);
  setEditingGroups((dept.department_groups || []).map((group) => ({
    ...group,
    member_ids: [...(group.member_ids || [])],
  })));
};

const handleSaveDepartmentGroups = async () => {
  if (!groupDialogDepartment) return;
  setIsSavingGroups(true);
  try {
    const { data: savedDepartment } = await updateDepartment(groupDialogDepartment.id, {
      department_groups: editingGroups,
    });
    rememberLocalChange("departments", savedDepartment);
    setDepartments((prev) => upsertById(prev, savedDepartment));
    setGroupDialogDepartment(null);
    toast.success("Department groups updated");
  } catch (err) {
    toast.error(err.response?.data?.detail || "Failed to update department groups");
  } finally {
    setIsSavingGroups(false);
  }
};
```

- [ ] **Step 3: Add Groups button in edit department controls**

Add next to Save/Cancel:

```jsx
<Button
  type="button"
  variant="outline"
  size="sm"
  onClick={() => openDepartmentGroupsDialog(dept)}
  className="h-8 px-3 text-xs"
>
  <Users className="w-3.5 h-3.5 mr-1" />
  Groups
</Button>
```

- [ ] **Step 4: Render dialog**

Use existing dialog UI components if available, or import from `@/components/ui/dialog`. The dialog must list `editingGroups`, allow add/remove group, supervisor select filtered to `users.filter((u) => u.department_id === groupDialogDepartment.id && u.role === "supervisor")`, and member checkboxes sourced from `getAvailableDepartmentGroupMembers(users, groupDialogDepartment.id, editingGroups, group.id)` plus the current group's selected members.

- [ ] **Step 5: Manual UI verification**

Run: `cd frontend; yarn start`

Open Admin > Departments, edit a department, open Groups. Verify group add/edit/remove and save error toasts.

---

### Task 8: Full Verification

**Files:**
- All modified files

- [ ] **Step 1: Backend test suite**

Run: `pytest tests/test_department_groups.py tests/test_approval_hierarchy.py tests/test_manager_form_templates.py -q`

Expected: PASS.

- [ ] **Step 2: Frontend focused tests**

Run: `cd frontend; yarn test src/pages/adminState.test.js --watchAll=false`

Expected: PASS.

- [ ] **Step 3: Build frontend**

Run: `cd frontend; yarn build`

Expected: PASS.

- [ ] **Step 4: Review git diff**

Run: `git diff --check`

Expected: no whitespace errors.

Run: `git status --short`

Expected: only files from this feature changed.
