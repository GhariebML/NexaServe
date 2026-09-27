# Admin dashboard

The deployment builds the repository FastAPI/static dashboard, which is absent from the root Compose file. The package includes pinned Python dependencies and an additive `admin_users` migration missing from the base schema. It also fixes the dashboard's Redis host for container DNS, removes wildcard CORS, and corrects the password-change function reference in the deployment copy only.

Create the first administrator with `scripts/create_dashboard_admin.sh`; credentials are entered interactively and password hash uses the dashboard Argon2 implementation. The user must validate all dashboard endpoints and RBAC on target; application-specific SQL compatibility needs review.
