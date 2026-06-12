from fastapi import APIRouter

from app.api import audit_logs, auth, cart, categories, inventory, orders, payments, products, reports, reviews, vendors, wishlist

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(vendors.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(inventory.router)
api_router.include_router(reviews.router)
api_router.include_router(wishlist.router)
api_router.include_router(reports.router)
api_router.include_router(audit_logs.router)

