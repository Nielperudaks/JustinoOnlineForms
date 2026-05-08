# Manager Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a department-scoped Settings/admin capability for users with the `manager` role.

**Architecture:** Reuse the existing `/admin` React page and form template API, but add role-aware backend authorization helpers that treat `super_admin` as global and `manager` as department-scoped. The frontend renders a restricted Manager Settings mode while the backend remains the source of truth for all scope and assignment checks.

**Tech Stack:** FastAPI, Motor/MongoDB-style async collections, Pytest, React, Axios, Tailwind/shadcn UI components.

---

## File Structure

- Modify `backend/utils/helpers.py`: add `require_form_manager` to admit `super_admin` and `manager`.
- Modify `backend/routes/form_templates.py`: add manager-aware list/create/update/delete behavior and assignment validation helpers.
- Modify `backend/routes/users.py`: allow managers to read department-scoped users and expose a custodian candidate endpoint.
- Create `tests/test_manager_form_templates.py`: focused async unit tests with fake collections for manager scope and assignment rules.
- Modify `frontend/src/pages/DashboardPage.js`: show Settings for managers.
- Modify `frontend/src/pages/AdminPage.js`: allow managers, restrict tabs/data/actions to department-scoped form management.
- Modify `frontend/src/components/BuildFormDialog.js`: support a locked department for Manager Settings.
- Modify `frontend/src/lib/api.js`: allow params for all-template listing and add custodian candidate API.

## Tasks

### Task 1: Backend Tests

- [ ] Create `tests/test_manager_form_templates.py` with fake async Mongo-style collections.
- [ ] Add tests proving managers only list their department's templates from `/form-templates/all`.
- [ ] Add tests proving manager create/update/delete is denied outside their department.
- [ ] Add tests proving manager approvers must be active approval-capable users in their department.
- [ ] Add tests proving manager custodians can be any active user in their department.
- [ ] Run `pytest tests/test_manager_form_templates.py -q` and confirm failures are for missing manager support.

### Task 2: Backend Implementation

- [ ] Add `require_form_manager` in `backend/utils/helpers.py`.
- [ ] Add role helpers in `backend/routes/form_templates.py`.
- [ ] Change `/form-templates/all`, `POST /form-templates`, `PUT /form-templates/{id}`, and `DELETE /form-templates/{id}` to use manager-aware access.
- [ ] Validate approver and custodian assignments during create/update.
- [ ] Update `backend/routes/users.py` so managers can list only their department users and get custodian candidates.
- [ ] Run `pytest tests/test_manager_form_templates.py -q` and confirm pass.

### Task 3: Frontend Manager Settings UI

- [ ] Show Settings button for `manager` and `super_admin` in `frontend/src/pages/DashboardPage.js`.
- [ ] Allow `/admin` for `manager` in `frontend/src/pages/AdminPage.js`.
- [ ] Make manager mode default to the forms tab and render no Users or Departments tabs.
- [ ] Fetch manager-scoped templates, approvers, custodians, and department data.
- [ ] Filter approver picker to approval-capable department users and custodian picker to all department users.
- [ ] Lock Build Form department to the manager's department.
- [ ] Run `yarn build` from `frontend`.

### Task 4: Full Verification

- [ ] Run backend focused tests.
- [ ] Run frontend build.
- [ ] Review `git diff --check`.
- [ ] Summarize changed files and any verification limitations.
