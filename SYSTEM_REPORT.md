# Justino Online Forms System Report

## Executive Summary

Justino Online Forms is a paperless transaction and approval management system designed to replace manual form routing with a centralized online workflow. The system allows employees to submit department-specific requests, lets approvers review and act on requests in sequence, and provides administrators with tools to manage users, departments, form templates, approver chains, and custodians.

The platform supports real-time request and notification updates, email alerts, role-based access, configurable forms, and request status tracking. It is built as a modern web application with a React frontend and a FastAPI/MongoDB backend.

## System Purpose

The system was created to streamline internal company requests across departments such as General, Service, Marketing, CIEG/TCG Sales, Davao Service Center, MCG, Accounting, Purchasing, HR and Admin, and Warehouse.

Its main purpose is to:

- Digitize request forms and reduce paper-based transactions.
- Standardize request submission across departments.
- Automate approval routing and status tracking.
- Improve visibility for requestors, approvers, custodians, and administrators.
- Provide a centralized record of requests, actions, comments, and notifications.

## Technologies Used

| Layer | Technologies | Purpose |
| --- | --- | --- |
| Frontend | React 19, React Router, Axios, Zustand | User interface, routing, API communication, local auth state |
| UI and Styling | Tailwind CSS, Radix UI components, shadcn-style UI components, Lucide React, Sonner | Responsive interface, reusable controls, icons, toast notifications |
| Backend | Python, FastAPI, Uvicorn | REST API, authentication endpoints, business logic, WebSocket service |
| Database | MongoDB, Motor async driver | Persistent storage for users, departments, forms, requests, approvals, and notifications |
| Authentication | JWT, HTTP Bearer tokens, Argon2 password hashing | Secure login, session handling, protected API access |
| Real-Time Updates | WebSockets, optional Redis pub/sub | Live request and notification updates across connected clients |
| Email Notifications | Resend API | Optional email alerts for approvals, rejections, fulfillment, and completed requests |
| Deployment | Vercel frontend, separate backend hosting, MongoDB Atlas recommended | Cloud deployment model for frontend and backend |
| Tooling | CRACO, Yarn, pytest, Black, Flake8, isort, mypy | Build process, dependency management, testing, and code quality |

## System Architecture

The application uses a separated frontend and backend architecture.

1. The React frontend runs as a single-page application.
2. Users authenticate through the backend and receive a JWT token.
3. API requests are sent through Axios to the FastAPI backend under the `/api` route prefix.
4. The backend validates permissions, processes workflow logic, and stores data in MongoDB.
5. The frontend opens a WebSocket connection for live updates.
6. Redis can be enabled so real-time events work across multiple backend instances.
7. Email delivery can be enabled through Resend when credentials are configured.

## Main User Roles

| Role | Main Responsibilities |
| --- | --- |
| Super Admin | Full access to users, departments, forms, approver assignments, dashboard totals, and request records |
| Requestor | Creates and tracks their own requests |
| Approver | Reviews, approves, or rejects requests assigned to them |
| Manager | Can act as an immediate manager approver and can also create requests |
| Both | Combined requestor and approver permissions |
| Custodian | Confirms fulfillment after approval when assigned to a form |

## Core Functions

### 1. User Authentication

The system includes secure login through email and password. Passwords are hashed using Argon2, and authenticated users receive JWT tokens for protected API access. Disabled accounts are blocked from using the system.

### 2. Dashboard

The dashboard gives users a working view of their request activity. It includes request counts, pending requests, approved requests, rejected requests, cancelled requests, pending approvals, unread notifications, and request lists.

Users can filter requests by:

- All requests
- My requests
- Pending my approval
- Pending status
- Approved status
- Rejected status
- Cancelled status
- Search text
- Department, for super admin users

### 3. Request Creation

Users with request creation permissions can submit new requests by selecting a department, selecting a form template, and filling in required fields.

Supported form field types include:

- Text
- Text area
- Number
- Date
- Dropdown/select
- Table
- File dropzone for images, PDF, Excel, and Word files up to 2 MB

### 4. Approval Workflow

Each form can have an approval chain. When a request is submitted, the system determines the approver sequence and sets the first approval step to pending.

Approvers can:

- Approve a request
- Reject a request
- Add comments
- Move the request to the next approval step

The workflow supports up to three configured approval steps in the admin interface. It also supports an "Immediate Manager" option, which dynamically assigns the manager from the requestor's department.

### 5. Custodian Fulfillment

Forms can include a custodian assignment. After approvals are completed, the request can move to a custodian fulfillment stage. The assigned custodian confirms fulfillment, after which the request is marked approved and completed.

### 6. Request Cancellation

Requestors and super admins can cancel requests while they are still in progress. Cancellation updates the request state and broadcasts live updates to connected users.

### 7. Notifications

The system creates notifications for important workflow events, including:

- New approval required
- Request approved
- Request rejected
- Request completed
- Custodian action required
- Notification read and clear-all events

Users can view unread notifications, mark individual notifications as read, and mark all notifications as read.

### 8. Email Alerts

When Resend is configured, the backend can send email notifications for workflow actions such as approval requests, rejection notices, fulfillment requests, and completed requests.

### 9. Real-Time Updates

The frontend listens for WebSocket events so request lists, request details, dashboard stats, and notifications can refresh when another user acts on a request.

Real-time events include:

- Request created
- Request updated
- Request approved
- Request rejected
- Request cancelled
- Request state changed
- Notification created
- Notification read
- Notifications cleared

### 10. Admin Management

The admin panel provides tools for:

- Creating, editing, activating, deactivating, and deleting users
- Assigning roles and departments
- Creating, editing, and deleting departments
- Creating and editing form templates
- Adding custom fields to forms
- Reordering form fields
- Assigning approvers by approval step
- Assigning custodians
- Viewing user, form, and request totals

The system also prevents unsafe deletion in key areas, such as blocking department deletion when users or forms are still assigned and blocking form deletion when active requests still depend on the form.

### 11. First-Login Tutorial

New users see a guided tutorial on first login. The tutorial uses images stored in the frontend public folder and records completion in the user profile.

## Key Features

- Paperless request submission and approval.
- Department-based form organization.
- Configurable form templates.
- Dynamic approval chain assignment.
- Immediate manager approval support.
- Custodian fulfillment stage.
- Role-based access control.
- JWT-secured API endpoints.
- Real-time dashboard, request, and notification updates.
- Search, filtering, and pagination/load-more behavior.
- Responsive layout for desktop and mobile use.
- Admin panel for system configuration.
- Email notification support.
- Seed data for departments, users, forms, sample requests, and notifications.
- Deployment-ready frontend configuration for Vercel.

## Benefits and Impact

### Operational Efficiency

The system reduces manual routing, printing, scanning, and follow-up work. Requests can be submitted, reviewed, approved, rejected, cancelled, or fulfilled from a browser.

### Faster Approvals

Approvers receive notifications when action is required. The system automatically advances approved requests to the next step, which reduces delays caused by manual handoffs.

### Better Accountability

Each request stores its request number, requester, department, form data, approval history, comments, timestamps, status, and custodian fulfillment details. This creates a clear audit trail.

### Improved Visibility

Requestors can track request progress. Approvers can see pending work. Administrators can view totals and manage system records from one place.

### Standardized Processes

Form templates help departments collect consistent information. Required fields, dropdowns, date fields, tables, and file uploads reduce incomplete submissions.

### Scalability

The frontend and backend are deployed separately, allowing independent scaling. Optional Redis pub/sub supports real-time updates across multiple backend instances.

### Reduced Administrative Burden

Admins can update users, departments, forms, approvers, and custodians without code changes. This makes the system adaptable as company workflows change.

## Security and Control Measures

- Passwords are hashed before storage.
- JWT tokens protect backend routes.
- Inactive users cannot access the system.
- Admin routes require super admin privileges.
- Non-admin users are restricted to requests they created, approve, or fulfill.
- Department and form deletion rules prevent breaking active workflows.
- Email sender validation is included when Resend is enabled.
- CORS origins can be configured for deployment.

## Deployment Overview

The project is prepared for a split deployment model:

- Frontend: Vercel, using the `frontend` folder as the root directory.
- Backend: Render, Railway, Fly.io, or another provider that supports long-running FastAPI services.
- Database: MongoDB Atlas or another MongoDB deployment.
- Environment variables: `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `JWT_SECRET`, optional `REDIS_URL`, optional `RESEND_API_KEY`, and sender email settings.

## Current System Scope

Based on the seeded configuration and current interface, the system covers 10 departments and a broad set of department-specific request forms. The login page presents the system as supporting 89 form types and a 3-step approval model.

The system currently focuses on internal request workflows, approval routing, notifications, and administrative configuration.

## Recommended Future Enhancements

- Add downloadable PDF or Excel reports for requests and approvals.
- Add dashboard charts for request trends by department, status, and turnaround time.
- Add attachment storage backed by cloud object storage instead of base64 form payloads.
- Add configurable service-level targets and overdue request alerts.
- Add audit log screens for admin and compliance review.
- Add multi-factor authentication for administrator accounts.
- Add password reset and account recovery flow.
- Add finer-grained permissions for department-level administrators.
- Add automated test coverage for request approval, custodian fulfillment, and admin workflows.

## Conclusion

Justino Online Forms provides a centralized, configurable, and real-time paperless transaction system for internal company workflows. It improves request visibility, reduces manual processing, standardizes department forms, and gives administrators direct control over users, forms, departments, approver chains, and custodians.

By combining a modern React frontend with a FastAPI and MongoDB backend, the system is flexible enough for current departmental workflows and can be expanded for reporting, analytics, stronger compliance controls, and larger-scale deployment.
