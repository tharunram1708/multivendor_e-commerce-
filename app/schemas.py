from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import InventoryAction, OrderStatus, PaymentStatus, ProductStatus, RoleName, VendorStatus


class Message(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: RoleName = RoleName.CUSTOMER


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)


class RoleOut(BaseModel):
    id: int
    name: RoleName

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    role: RoleOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorBase(BaseModel):
    business_name: str = Field(min_length=2, max_length=180)
    gst_number: str = Field(min_length=5, max_length=30)
    contact_number: str = Field(min_length=7, max_length=20)
    address: str = Field(min_length=5)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=180)
    gst_number: str | None = Field(default=None, min_length=5, max_length=30)
    contact_number: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = Field(default=None, min_length=5)
    status: VendorStatus | None = None


class VendorOut(VendorBase):
    id: int
    user_id: int
    status: VendorStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorDashboard(BaseModel):
    total_products: int
    total_orders: int
    revenue_generated: Decimal


class CategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=3)
    category_id: int
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    quantity: int = Field(ge=0)
    status: ProductStatus = ProductStatus.ACTIVE


class ProductCreate(ProductBase):
    vendor_id: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, min_length=3)
    category_id: int | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    quantity: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None


class ProductOut(ProductBase):
    id: int
    vendor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductOut

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: int
    user_id: int
    items: list[CartItemOut]
    total_amount: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    shipping_address: str = Field(min_length=5)


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    vendor_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_address: str
    items: list[OrderItemOut]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class PaymentCreate(BaseModel):
    order_id: int
    method: str = "mock"
    status: PaymentStatus = PaymentStatus.SUCCESS


class PaymentOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    amount: Decimal
    method: str
    status: PaymentStatus
    transaction_reference: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryChange(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    note: str | None = None


class InventoryLogOut(BaseModel):
    id: int
    product_id: int
    vendor_id: int
    quantity: int
    action: InventoryAction
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RatingSummary(BaseModel):
    product_id: int
    average_rating: float
    total_reviews: int


class WishlistCreate(BaseModel):
    product_id: int


class WishlistOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    product: ProductOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminDashboard(BaseModel):
    total_users: int
    total_vendors: int
    total_products: int
    total_orders: int
    revenue_report: Decimal


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str | None
    entity_id: int | None
    details: str | None
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
