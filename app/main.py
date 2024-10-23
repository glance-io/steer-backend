from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import completion_router, stats_router, users_router, webhooks_router
import sentry_sdk

from app.services.cache.redis_cache import RedisCacheService
from app.services.db.supabase import SupabaseConnectionService
from app.settings import settings

if not settings.debug:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await RedisCacheService().connect()
        await SupabaseConnectionService().connect()
        yield
    finally:
        await RedisCacheService().disconnect()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(completion_router)
app.include_router(users_router)
app.include_router(webhooks_router)
app.include_router(stats_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8123, reload=settings.debug)
