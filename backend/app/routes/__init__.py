from .admin import bp as admin_bp
from .ai import bp as ai_bp
from .auth import bp as auth_bp
from .listings import bp as listings_bp
from .messages import bp as messages_bp
from .notifications import bp as notifications_bp
from .orders import bp as orders_bp
from .users import bp as users_bp
from .wishlist import bp as wishlist_bp

ALL_BLUEPRINTS = [
    auth_bp, users_bp, listings_bp, wishlist_bp, orders_bp, messages_bp, notifications_bp, admin_bp, ai_bp,
]
