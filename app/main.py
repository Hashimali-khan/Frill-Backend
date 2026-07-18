from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.rate_limit import limiter
from app.routers import auth, designs, orders, products, uploads, ws
from app.security import verify_csrf


# FIX C4 — CSRF middleware (was defined but never wired)
class CSRFMiddleware(BaseHTTPMiddleware):
    """Applies CSRF double-submit check to all state-changing requests.
    Excludes /auth/signup, /auth/login, /auth/forgot-password, /auth/reset-password
    because those endpoints don't have a CSRF cookie yet."""

    EXEMPT_PATHS = {
        "/auth/signup", "/auth/login",
        "/auth/forgot-password", "/auth/reset-password",
    }

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.url.path not in self.EXEMPT_PATHS:
                verify_csrf(request)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Frill API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,   # required for the cookie to be sent cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],  # let frontend read CSRF-related headers
)

# FIX C4 — CSRF middleware MUST be added AFTER CORSMiddleware
# (middleware stack is LIFO, so CORS runs first on the response)
app.add_middleware(CSRFMiddleware)

register_error_handlers(app)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(designs.router)        # FIX C1 — was missing
app.include_router(orders.router)
app.include_router(uploads.router)
app.include_router(ws.router)             # FIX C7 — was missing


@app.get("/health")
async def health():
    return {"status": "ok"}