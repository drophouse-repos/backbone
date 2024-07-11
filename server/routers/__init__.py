from routers.imagen import imagen_router
from routers.favorites import favorite_router
from .shipping_info import shipping_info_router
from .order_info import order_info_router
from routers.auth import auth_router
from routers.cart import cart_router
from routers.stripe import stripe_router
from routers.email import email_router
from routers.static import static_router
from routers.prices import prices_router

__all__ = [
    "imagen_router",
    "favorite_router",
    "shipping_info_router",
    "order_info_router",
    "static_router",
    "auth_router",
    "cart_router",
    "stripe_router",
    "email_router",
    "prices_router"
]
