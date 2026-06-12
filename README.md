# Multi-Vendor E-Commerce Backend

FastAPI backend for a multi-vendor marketplace with JWT authentication, RBAC, products, categories, cart, orders, mock payments, inventory, reviews, wishlist, reports, and audit logs.

## Setup

1. Create and activate the virtual environment.

```powershell
.\.venv\Scripts\activate
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update `DATABASE_URL`.

4. Create the MySQL database.

```sql
CREATE DATABASE multivendor_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

5. Run migrations.

```powershell
alembic upgrade head
```

Alternative: if your task specifically needs plain MySQL code, run `database.sql` directly in MySQL Workbench or the MySQL CLI instead of Alembic.

6. Create the first super admin.

Set these values in `.env` before starting the API:

```env
FIRST_SUPER_ADMIN_EMAIL="admin@example.com"
FIRST_SUPER_ADMIN_PASSWORD="Admin@12345"
```

The app creates this user on startup if it does not already exist.

7. Start the API.

```powershell
uvicorn main:app --reload
```

Swagger documentation will be available at `http://127.0.0.1:8000/docs`.

## Notes

- Login uses OAuth2 password form. In Swagger, use `username` as the email.
- Customers can manage cart, orders, payments, reviews, and wishlist.
- Vendors can create a vendor profile, manage their own products, and update inventory.
- Super admin can manage categories, view reports, and view audit logs.
- Forgot/reset password is mocked: the reset token is returned in the API response instead of sending email.

## Official References

- FastAPI bigger applications and `APIRouter`: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI OAuth2/JWT security flow: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- SQLAlchemy declarative ORM mapping: https://docs.sqlalchemy.org/en/latest/orm/declarative_mapping.html
- Alembic migrations and autogenerate workflow: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
