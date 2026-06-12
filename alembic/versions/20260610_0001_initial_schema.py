"""initial schema

Revision ID: 20260610_0001
Revises:
Create Date: 2026-06-10 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260610_0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=30), nullable=False, unique=True),
    )
    roles_table = sa.table("roles", sa.column("name", sa.String))
    op.bulk_insert(
        roles_table,
        [{"name": "super_admin"}, {"name": "vendor"}, {"name": "customer"}],
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("reset_token_hash", sa.String(length=255), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("business_name", sa.String(length=180), nullable=False),
        sa.Column("gst_number", sa.String(length=30), nullable=False, unique=True),
        sa.Column("contact_number", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        *timestamps(),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_categories_name", "categories", ["name"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        *timestamps(),
    )
    op.create_index("ix_products_name", "products", ["name"])

    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        *timestamps(),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=False),
        *timestamps(),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False, server_default="mock"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("transaction_reference", sa.String(length=120), nullable=True),
        *timestamps(),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
    )

    op.create_table(
        "wishlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )

    op.create_table(
        "inventory_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        *timestamps(),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        *timestamps(),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("inventory_logs")
    op.drop_table("wishlists")
    op.drop_table("reviews")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")
    op.drop_table("vendors")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")

