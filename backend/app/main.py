from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.events import shutdown, startup
from app.core.exceptions import global_exception_handler
from app.core.logger import get_logger
from app.core.middleware import RequestLoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup(app)
    yield
    await shutdown(app)


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.API_DESCRIPTION,
        version=settings.VERSION,
        lifespan=lifespan,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.DEBUG,
    )

    application.add_middleware(RequestLoggingMiddleware)
    application.add_exception_handler(Exception, global_exception_handler)
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    logger.info("FastAPI application created and routes registered.")

    return application


app = create_application()