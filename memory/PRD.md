# Workflow Bridge - Paperless Transaction System PRD

## Original Problem Statement
Build a paperless transaction system for a company with 10 departments and 80+ paper form types. Super admin creates users, assigns departments and roles (requestor/approver/both), assigns 1-3 sequential approvers per form. Dashboard should look like Outlook. Email + in-app notifications.

## Architecture
- **Frontend**: React + Tailwind + Shadcn UI (3-panel Outlook layout)
- **Backend**: FastAPI + MongoDB
- **Auth**: JWT-based (24h token expiry)
- **Email**: Resend API for notifications

## User Personas
1. **Super Admin** - Creates users, manages departments, assigns approvers, full visibility
2. **Requestor** - Submits requests, tracks status, receives notifications
3. **Approver** - Reviews and approves/rejects requests, sees pending queue
4. **Both** - Can submit and approve requests

## Core Requirements
- 10 departments with 89 pre-seeded form templates
- Dynamic form system (admin configurable)
- Sequential approval chain (1-3 steps)
- Outlook-style 3-panel dashboard
- In-app + email notifications
- User CRUD with role/department assignment

## What's Been Implemented (Feb 7, 2026)
- JWT authentication (login, token validation)
- 10 departments seeded with 89 form templates
- User management (CRUD, role assignment, activate/deactivate)
- Dynamic form creation from templates
- Request submission with priority levels
- Sequential approval workflow (approve/reject with comments)
- In-app notification system
- Email notifications via Resend
- Outlook-style 3-panel dashboard (sidebar, list, detail)
- Admin panel (Users, Forms & Approvers, Departments tabs)
- Department filtering, status filtering, search
- Mobile responsive design

## Prioritized Backlog
### P0 (Critical)
- All core features implemented

### P1 (Important)
- File/attachment uploads on requests
- Bulk approval actions
- Request export to PDF
- Audit trail / activity log per request
- Dashboard analytics charts

### P2 (Nice to have)
- Dark mode toggle
- Custom form template builder (admin drag & drop)
- Request duplication/cloning
- Advanced search & filters (date range, priority)
- User profile page with password change
- Department-specific dashboard views
- Request comments/discussion thread

## Default Credentials
- Super Admin: admin@company.com / admin123
