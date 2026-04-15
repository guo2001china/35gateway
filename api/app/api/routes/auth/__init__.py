from .auth import router as auth_router
from .console import router as console_router
from .files import router as files_router
from .me import router as me_router
from .redemption import router as redemption_router

__all__ = ["auth_router", "console_router", "files_router", "me_router", "redemption_router"]
