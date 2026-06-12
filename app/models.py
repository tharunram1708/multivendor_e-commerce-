from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RoleName(str, Enum):
    SUPER_ADMIN = "super_admin"
    VENDOR = "vendor"
    CUSTOMER = "customer"


class VendorStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class InventoryAction(str, Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    ORDER_DEDUCTION = "order_deduction"
    CANCELLATION_RETURN = "cancellation_return"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[RoleName] = mapped_column(String(30), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped[Role] = relationship(back_populates="users")
    vendor_profile: Mapped["Vendor | None"] = relationship(back_populates="user", uselist=False)
    cart: Mapped["Cart | None"] = relationship(back_populates="user", uselist=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    reviews: Mapped[list["Review"]] = relationship(back_populates="user")
    wishlists: Mapped[list["Wishlist"]] = relationship(back_populates="user")


class Vendor(TimestampMixin, Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    business_name: Mapped[str] = mapped_column(String(180), nullable=False)
    gst_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[VendorStatus] = mapped_column(String(30), default=VendorStatus.PENDING, nullable=False)

    user: Mapped[User] = relationship(back_populates="vendor_profile")
    products: Mapped[list["Product"]] = relationship(back_populates="vendor")


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    status: Mapped[ProductStatus] = mapped_column(String(30), default=ProductStatus.ACTIVE, nullable=False)

    category: Mapped[Category] = relationship(back_populates="products")
    vendor: Mapped[Vendor] = relationship(back_populates="products")
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
    reviews: Mapped[list["Review"]] = relationship(back_populates="product")
    wishlists: Mapped[list["Wishlist"]] = relationship(back_populates="product")
    inventory_logs: Mapped[list["InventoryLog"]] = relationship(back_populates="product")


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="cart_items")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(String(30), default=OrderStatus.PENDING, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")
    vendor: Mapped[Vendor] = relationship()


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(String(30), default=PaymentStatus.PENDING, nullable=False)
    transaction_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    order: Mapped[Order] = relationship(back_populates="payments")
    user: Mapped[User] = relationship()


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="reviews")
    product: Mapped[Product] = relationship(back_populates="reviews")


class Wishlist(TimestampMixin, Base):
    __tablename__ = "wishlists"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    user: Mapped[User] = relationship(back_populates="wishlists")
    product: Mapped[Product] = relationship(back_populates="wishlists")


class InventoryLog(TimestampMixin, Base):
    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[InventoryAction] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped[Product] = relationship(back_populates="inventory_logs")
    vendor: Mapped[Vendor] = relationship()


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user: Mapped[User | None] = relationship()

