# Department Groups And Immediate Supervisor Design

## Goal

Super Admins can define supervisor-led groups inside departments. Forms can use a new `Immediate Supervisor` approval step that routes requests to the requestor's assigned group supervisor before manager approval when applicable.

## Roles

- Add a user role named `supervisor`.
- Supervisors can approve requests assigned to them.
- Supervisors can create requests.
- Supervisors cannot be department managers.
- Existing manager, executive, approver, custodian, requestor, and super admin behavior remains unchanged.

## Department Groups

Departments gain a `department_groups` array:

- `id`: stable group identifier.
- `name`: department-local group name.
- `supervisor_id`: active supervisor user in the same department.
- `member_ids`: active non-manager, non-supervisor users in the same department.

Rules:

- A non-supervisor user can belong to only one group in their department.
- A supervisor can supervise multiple groups.
- A supervisor cannot be listed as a group member.
- Managers and executives cannot be listed as group members.
- Group supervisors and members must belong to the department being edited.
- Department group edits are saved through the department update API.

## Admin UI

In `AdminPage.js`, the Departments tab edit state adds a Groups button. The button opens a dialog for the selected department.

The dialog supports:

- Creating a group with name, supervisor, and members.
- Editing existing group name, supervisor, and members.
- Removing a group.
- Supervisor picker shows only users in that department with role `supervisor`.
- Member picker shows only users in that department who are not supervisors, managers, executives, or super admins and who are not already assigned to another group.

The Users tab role picker includes `Supervisor`.

## Approval Chain

The form approval picker adds a second special approver:

- `Immediate Manager`, stored as `immediate_manager`, keeps current behavior.
- `Immediate Supervisor`, stored as `immediate_supervisor`, resolves at request creation time.

When a request is created and a form step uses `immediate_supervisor`:

- If the requestor is a supervisor, route to the requestor's department manager.
- If the requestor is in a department group, route to that group's assigned supervisor.
- If the requestor is not in a group, route to the requestor's department manager.
- If no applicable supervisor or manager exists, return a validation error explaining what assignment is missing.
- Duplicate approvers are still skipped so the same user appears only once in the final approval chain.

## Backend Validation

Department update validation enforces the group rules above and stores normalized group data.

Request creation resolves `immediate_supervisor` using current department data. `immediate_manager` resolution remains unchanged except for shared helper extraction if useful.

Approver lists include supervisors so they can approve assigned requests, but the `Immediate Supervisor` option is shown as a special placeholder rather than as an individual user.

## Testing

Backend tests cover:

- Supervisor role is approval-capable and request-capable.
- Department update accepts valid groups.
- Department update rejects duplicate group membership.
- Department update rejects invalid supervisors or members.
- `immediate_supervisor` routes a group member to the group supervisor.
- `immediate_supervisor` falls back to manager for supervisor requestors.
- `immediate_supervisor` falls back to manager for non-group members.

Frontend tests cover:

- Supervisor is treated as an approver-capable user.
- Role options include Supervisor.
- Approval picker can assign `Immediate Supervisor`.
- Department group filtering excludes invalid or already-assigned members.
