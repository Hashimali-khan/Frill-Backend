from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import engine
from app.core.rate_limit import limiter
from app.routers import auth
from app.models.base import Base


app = FastAPI(title="Frill Backend")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def on_shutdown():
    await engine.dispose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="[IP_ADDRESS]", port=8000)