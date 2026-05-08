# Manager Settings Design

## Goal

Managers get a Settings button that opens a department-scoped management page. They can build, edit, delete, and assign workflow participants only for forms in their own department.

## Roles And Scope

- `super_admin` keeps full Admin Panel access to users, departments, all forms, and global approver/custodian assignment.
- `manager` can open `/admin`, but sees a Manager Settings version of the page.
- A manager's scope is their own `department_id`.
- Managers cannot create, edit, delete, or assign workflow users on forms outside their department.
- Managers cannot manage users or departments from this page.

## Form Management

Managers can:

- List all templates in their department, including inactive records returned by the management endpoint.
- Create a new form in their department.
- Edit form name, description, and fields for forms in their department.
- Delete forms in their department when existing delete rules allow it.
- Assign approvers and custodians for forms in their department.

Managers cannot:

- Change a form's department.
- See forms from other departments in the management view.
- Create forms for another department by crafting a request body.

## Assignment Rules

Approvers assigned by a manager must be either:

- The existing `immediate_manager` placeholder, or
- An active user in the manager's department whose role is `approver`, `both`, `manager`, or `super_admin`.

Custodians assigned by a manager must be:

- An active user in the manager's department, regardless of role.

The backend enforces these rules for create and update requests. The frontend mirrors them in the picker options.

## UI

- Dashboard top bar shows the Settings button for both `super_admin` and `manager`.
- `/admin` allows `super_admin` and `manager`.
- Super Admin sees the current Admin Panel unchanged.
- Manager sees a title such as "Manager Settings", no Users tab, no Departments tab, and only the Forms tab.
- The Build Form dialog receives only the manager's department and defaults to it.

## Testing

- Backend tests cover manager-scoped listing, create, update, delete, approver assignment, custodian assignment, and cross-department denial.
- Frontend build verifies the role-aware React changes compile.
