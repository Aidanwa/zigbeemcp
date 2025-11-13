"""FastAPI server main entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import get_config
from .routes import router
from ..mqtt import get_bus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Smart Home API Server")
    config = get_config()
    logger.info(f"API listening on {config.host}:{config.port}")
    logger.info(f"Configured {len(config.api_keys)} API key(s)")

    # Initialize MQTT connection
    try:
        bus = get_bus()
        logger.info("MQTT connection established")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Smart Home API Server")


# Create FastAPI app
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()

    app = FastAPI(
        title="Smart Home API",
        description="REST API for controlling Zigbee smart home devices via Zigbee2MQTT",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware if origins are configured
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {config.cors_origins}")

    # Include API routes
    app.include_router(router)

    # Health check endpoint (no auth required)
    @app.get("/health", tags=["System"])
    async def health_check():
        """Simple health check endpoint."""
        return JSONResponse(
            content={
                "status": "ok",
                "service": "smart-home-api",
                "version": "0.1.0"
            }
        )

    # Root endpoint
    @app.get("/", tags=["System"])
    async def root():
        """Root endpoint with API information."""
        return JSONResponse(
            content={
                "service": "Smart Home API",
                "version": "0.1.0",
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            }
        )

    return app


def main():
    """Main entry point for the API server."""
    try:
        config = get_config()
        app = create_app()

        # Run the server
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
            access_log=True,
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure API_KEYS is set")
        exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        exit(1)


if __name__ == "__main__":
    main()
